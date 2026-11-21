"""Known-answer tests for the Phase 2 core. Synthetic data only."""
import numpy as np
import pandas as pd
import pytest

import config as C
from eventstudy import bmp_kp_test, build_firm_event, car, car_corr, plain_t_test
from eventtime import get_calendar

SESS = pd.DatetimeIndex(get_calendar("XNYS").sessions_in_range("2010-01-04", "2019-12-31"))
SESS = SESS.tz_localize(None) if SESS.tz is not None else SESS


def make_world(n_clusters=20, firms_per_cluster=2, rho=0.5, sd=0.03, effect=0.0, seed=1, shared_firms=False):
    """Clusters of firms sharing a day 0. Firm noise has common factor with correlation rho within a cluster.

    effect is added to each firm's return on day 0 (a known abnormal return)."""
    rng = np.random.default_rng(seed)
    T = len(SESS)
    m = rng.normal(0.0003, 0.01, T)
    frames = [pd.DataFrame({"date": SESS, "ticker": "MKT", "ret": m})]
    rows = []
    gap = (T - 400) // n_clusters
    for c in range(n_clusters):
        common = rng.normal(0, 1, T)
        i0 = 300 + c * gap
        for f in range(firms_per_cluster):
            tic = f"F{f}" if shared_firms else f"C{c}F{f}"
            idio = rng.normal(0, 1, T)
            e = sd * (np.sqrt(rho) * common + np.sqrt(1 - rho) * idio)
            r = 0.0002 + 1.1 * m + e
            r[i0] += effect
            if not shared_firms:
                frames.append(pd.DataFrame({"date": SESS, "ticker": tic, "ret": r}))
            rows.append({"launch_tag": f"L{c}", "ticker": tic, "exchange": "XNYS", "day0": SESS[i0],
                         "cluster": c + 1, "tier": "tier1", "role": "rival", "_r": r})
    if shared_firms:  # one return series per firm, effects at every cluster's day 0
        for f in range(firms_per_cluster):
            base = rows[f]["_r"]
            frames.append(pd.DataFrame({"date": SESS, "ticker": f"F{f}", "ret": base}))
    rets = pd.concat(frames, ignore_index=True)
    bench = rets[rets["ticker"] == "MKT"][["date", "ret"]]
    return [build_firm_event(pd.Series(r), rets, bench) for r in rows]


def test_market_model_recovers_beta_and_sigma():
    fes = make_world(n_clusters=20, firms_per_cluster=1, rho=0.0, seed=3)
    assert all(fe.model == "market_model" and len(fe.est_r) == 221 for fe in fes)
    # beta s.e. per firm is about 0.03 / 0.01 / sqrt(221) = 0.2; the mean of 20 has s.e. about 0.045
    assert abs(np.mean([fe.beta for fe in fes]) - 1.1) < 0.15
    assert abs(np.mean([fe.sigma for fe in fes]) - 0.03) < 0.002


def test_injected_effect_is_recovered():
    fes = make_world(n_clusters=30, firms_per_cluster=1, rho=0.0, effect=0.05, seed=4)
    cars = np.array([car(fe, (0, 1))[0] for fe in fes])
    assert abs(cars.mean() - 0.05) < 0.015
    res = bmp_kp_test(fes, (0, 1))
    assert res.p < 0.001 and res.ci_low < 0.05 < res.ci_high


def test_car_variance_formula_matches_simulation():
    """Var(CAR) from the formula should match the spread of CARs under the null."""
    fes = make_world(n_clusters=60, firms_per_cluster=1, rho=0.0, seed=5)
    v = np.array([car(fe, (0, 1))[1] for fe in fes])
    c = np.array([car(fe, (0, 1))[0] for fe in fes])
    assert 0.6 < np.var(c) / v.mean() < 1.6


def test_kp_adjustment_reduces_to_single_cluster_formula():
    fes = make_world(n_clusters=1, firms_per_cluster=6, rho=0.4, seed=6)
    res = bmp_kp_test(fes, (0, 1))
    r = res.mean_within_cluster_corr
    N = res.n_firm_events
    expected = np.sqrt((1 - r) / (1 + (N - 1) * r))
    assert f"adjustment factor = {expected:.3f}" in res.note


def test_same_stock_overlapping_windows_correlation_is_overlap_share():
    fe = make_world(n_clusters=1, firms_per_cluster=1, seed=7)[0]
    import copy
    fe2 = copy.copy(fe)
    fe2.ev_dates = fe.ev_dates + pd.offsets.BDay(0)  # same dates
    fe2.ev_dates = pd.DatetimeIndex(list(fe.ev_dates[1:]) + [fe.ev_dates[-1] + pd.Timedelta(days=1)])
    assert car_corr(fe, fe2, (0, 1)) == pytest.approx(0.5)


def test_size_under_correlated_null():
    """With correlated firms in each cluster and no true effect, the adjusted test
    should reject about 5% of the time; the plain t-test should reject more often."""
    rej_kp, rej_plain, n = 0, 0, 120
    for s in range(n):
        fes = make_world(n_clusters=15, firms_per_cluster=3, rho=0.6, seed=100 + s)
        rej_kp += bmp_kp_test(fes, (0, 1)).p < 0.05
        rej_plain += plain_t_test(fes, (0, 1)).p < 0.05
    assert rej_kp / n < 0.10           # close to 5% (allowing simulation noise)
    assert rej_plain / n > rej_kp / n  # ignoring correlation over-rejects
