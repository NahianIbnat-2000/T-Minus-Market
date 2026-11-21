"""Phase 2 core: market model, abnormal returns, CARs and the primary test.

Everything here follows docs/ANALYSIS_PLAN.md (frozen v1.0). Formulas:

  Market model on the estimation window E (T days):
      R_it = a_i + b_i R_mt + e_it,  sigma_i^2 = SSR / (T - 2)
  AR_it = R_it - (a_i + b_i R_mt) in the event window W (L days)
  CAR_i = sum_{t in W} AR_it
  Var(CAR_i) = sigma_i^2 * [ L + L^2/T + (sum_W (R_mt - mean_E R_m))^2 / sum_E (R_mt - mean_E R_m)^2 ]
      (prediction-error adjusted; Campbell, Lo and MacKinlay 1997, ch. 4)
  Market-adjusted fallback: AR = R - R_m, Var(CAR) = sigma_i^2 * L

  SCAR_i = CAR_i / sqrt(Var(CAR_i))
  BMP (Boehmer, Musumeci and Poulsen 1991): t = mean(SCAR) * sqrt(N) / sd(SCAR)
  Kolari and Pynnonen (2010) adjustment, extended to clusters:
      S = sum over ordered pairs (i != j) in the same cluster of rho_ij
      t_adj = t * sqrt( (1 - S / (N (N - 1))) / (1 + S / N) )
      With a single cluster and equal rho this is KP's
      sqrt((1 - r) / (1 + (N - 1) r)).
      rho_ij = corr of CAR_i and CAR_j = resid_corr_ij * common_days_ij / L
      (resid_corr = 1 for the same stock; 0 days in common -> 0)
  p-value: Student t with (clusters - 1) degrees of freedom (conservative).
  95% CI for mean CAR: cluster-robust standard error, t with (clusters - 1) df.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy import stats

import config as C
from eventtime import get_calendar


# --------------------------------------------------------------------------- data for one firm-event
@dataclass
class FirmEvent:
    key: str
    launch_tag: str
    ticker: str
    exchange: str
    tier: str
    cluster: int
    day0: pd.Timestamp
    model: str
    est_dates: pd.DatetimeIndex
    est_r: np.ndarray
    est_m: np.ndarray
    rel_days: np.ndarray            # relative day numbers available around day 0
    ev_dates: pd.DatetimeIndex      # matching calendar dates
    ev_r: np.ndarray                # firm returns (nan if missing)
    ev_m: np.ndarray
    alpha: float = 0.0
    beta: float = 1.0
    sigma: float = np.nan
    resid: pd.Series = field(default_factory=pd.Series)
    meta: dict = field(default_factory=dict)


def _naive(idx):
    idx = pd.DatetimeIndex(idx)
    return idx.tz_localize(None) if idx.tz is not None else idx


def build_firm_event(row, returns: pd.DataFrame, bench: pd.DataFrame, rel_range=(-5, 20),
                     day0_shift: int = 0) -> FirmEvent | None:
    """Assemble estimation and event data. `day0_shift` moves day 0 by whole sessions (robustness R5)."""
    sessions = _naive(get_calendar(row["exchange"]).sessions)
    d0 = pd.Timestamp(row["day0"]).tz_localize(None) if pd.Timestamp(row["day0"]).tzinfo else pd.Timestamp(row["day0"])
    if d0 not in sessions:
        return None
    i0 = sessions.get_loc(d0) + day0_shift
    lo, hi = C.EST_WINDOW
    r = returns.loc[returns["ticker"] == row["ticker"]].set_index("date")["ret"]
    ls = row.get("listing_start")
    if ls is not None and pd.notna(ls) and str(ls) != "":
        r = r[r.index > pd.Timestamp(ls).tz_localize(None) if pd.Timestamp(ls).tzinfo else r.index > pd.Timestamp(ls)]
    m = bench.set_index("date")["ret"]
    est_days = sessions[max(i0 + lo, 0): i0 + hi + 1]
    joint = pd.concat([r.reindex(est_days), m.reindex(est_days)], axis=1, keys=["r", "m"]).dropna()
    rel = np.arange(rel_range[0], rel_range[1] + 1)
    rel = rel[(i0 + rel >= 0) & (i0 + rel < len(sessions))]
    ev_days = sessions[i0 + rel]
    fe = FirmEvent(key=f"{row['launch_tag']}|{row['ticker']}|{row.get('role', '')}",
                   launch_tag=row["launch_tag"], ticker=row["ticker"], exchange=row["exchange"],
                   tier=row.get("tier", ""), cluster=int(row["cluster"]) if pd.notna(row.get("cluster")) else -1,
                   day0=sessions[i0], model="",
                   est_dates=joint.index, est_r=joint["r"].values, est_m=joint["m"].values,
                   rel_days=rel, ev_dates=ev_days,
                   ev_r=r.reindex(ev_days).values, ev_m=m.reindex(ev_days).values,
                   meta={k: row.get(k) for k in ("role", "tier", "firm_name", "lv_type", "launch_utc",
                                                 "disclosure_confidence", "outcome")})
    n = len(joint)
    if n >= C.EST_MIN_OBS:
        fe.model = "market_model"
        X = np.column_stack([np.ones(n), fe.est_m])
        (a, b), *_ = np.linalg.lstsq(X, fe.est_r, rcond=None)
        res = fe.est_r - (a + b * fe.est_m)
        fe.alpha, fe.beta = float(a), float(b)
        fe.sigma = float(np.sqrt(res @ res / (n - 2)))
    elif n >= 30:
        fe.model = "market_adjusted_fallback"
        res = fe.est_r - fe.est_m
        fe.alpha, fe.beta = 0.0, 1.0
        fe.sigma = float(np.std(res, ddof=1))
    else:
        return None
    fe.resid = pd.Series(res, index=fe.est_dates)
    return fe


def abnormal(fe: FirmEvent) -> np.ndarray:
    return fe.ev_r - (fe.alpha + fe.beta * fe.ev_m)


def car(fe: FirmEvent, window) -> tuple[float, float, int]:
    """(CAR, Var(CAR), L). NaN if any return in the window is missing."""
    a, b = window
    mask = (fe.rel_days >= a) & (fe.rel_days <= b)
    ar = abnormal(fe)[mask]
    L = int(mask.sum())
    if L != b - a + 1 or np.isnan(ar).any():
        return np.nan, np.nan, L
    if fe.model == "market_model":
        T = len(fe.est_m)
        dm = fe.est_m - fe.est_m.mean()
        sw = np.sum(fe.ev_m[mask] - fe.est_m.mean())
        var = fe.sigma ** 2 * (L + L ** 2 / T + sw ** 2 / np.sum(dm ** 2))
    else:
        var = fe.sigma ** 2 * L
    return float(ar.sum()), float(var), L


def window_dates(fe: FirmEvent, window) -> pd.DatetimeIndex:
    a, b = window
    return fe.ev_dates[(fe.rel_days >= a) & (fe.rel_days <= b)]


# --------------------------------------------------------------------------- cross-correlation between firm-events
def car_corr(fi: FirmEvent, fj: FirmEvent, window) -> float:
    """Correlation of two CARs: residual correlation times share of common calendar days."""
    L = window[1] - window[0] + 1
    common = len(set(window_dates(fi, window)) & set(window_dates(fj, window)))
    if common == 0:
        return 0.0
    if fi.ticker == fj.ticker:
        rc = 1.0
    else:
        both = pd.concat([fi.resid, fj.resid], axis=1, join="inner").dropna()
        if len(both) < 30:
            return 0.0
        rc = float(np.corrcoef(both.iloc[:, 0], both.iloc[:, 1])[0, 1])
    return rc * common / L


# --------------------------------------------------------------------------- tests
@dataclass
class TestResult:
    name: str
    mean_car: float
    ci_low: float
    ci_high: float
    stat: float
    p: float
    n_firm_events: int
    n_failures: int
    n_firms: int
    n_clusters: int
    mean_within_cluster_corr: float = np.nan
    note: str = ""

    def as_dict(self):
        return {k: (None if isinstance(v, float) and not np.isfinite(v) else v) for k, v in self.__dict__.items()}


def _cluster_ci(cars: np.ndarray, clusters: np.ndarray, level=0.95):
    """Mean with cluster-robust SE; t with G-1 df."""
    N = len(cars)
    G = len(np.unique(clusters))
    mu = cars.mean()
    if G < 2:
        return mu, np.nan, np.nan, np.nan, G
    u = pd.Series(cars - mu).groupby(clusters).sum().values
    se = np.sqrt(G / (G - 1) * np.sum(u ** 2)) / N
    q = stats.t.ppf(0.5 + level / 2, G - 1)
    return mu, mu - q * se, mu + q * se, se, G


def bmp_kp_test(fes: list[FirmEvent], window, name="BMP-KP") -> TestResult:
    rows = [(fe, *car(fe, window)) for fe in fes]
    rows = [r for r in rows if np.isfinite(r[1])]
    fes_ok = [r[0] for r in rows]
    cars = np.array([r[1] for r in rows])
    scar = cars / np.sqrt(np.array([r[2] for r in rows]))
    clusters = np.array([fe.cluster for fe in fes_ok])
    N = len(scar)
    mu, lo, hi, _, G = _cluster_ci(cars, clusters)
    if N < 3:
        return TestResult(name, mu, lo, hi, np.nan, np.nan, N, 0, 0, G, note="too few firm-events")
    t = scar.mean() * np.sqrt(N) / scar.std(ddof=1)
    S, pairs, rhos = 0.0, 0, []
    for i in range(N):
        for j in range(N):
            if i != j and clusters[i] == clusters[j]:
                rho = car_corr(fes_ok[i], fes_ok[j], window)
                S += rho
                pairs += 1
                if i < j:
                    rhos.append(rho)
    adj = np.sqrt(max(1 - S / (N * (N - 1)), 1e-12) / (1 + S / N))
    t_adj = t * adj
    p = 2 * stats.t.sf(abs(t_adj), max(G - 1, 1))
    return TestResult(name, mu, lo, hi, float(t_adj), float(p), N,
                      len({fe.launch_tag for fe in fes_ok}), len({fe.ticker for fe in fes_ok}), G,
                      float(np.mean(rhos)) if rhos else 0.0,
                      note=f"unadjusted BMP t = {t:.3f}; adjustment factor = {adj:.3f}; df = {G - 1}")


def portfolio_test(fes, window, name="R1 portfolio") -> list[TestResult]:
    """One equal-weighted CAR per cluster; t-test and exact sign test across clusters."""
    rows = [(fe.cluster, car(fe, window)[0], fe) for fe in fes]
    rows = [r for r in rows if np.isfinite(r[1])]
    df = pd.DataFrame({"cluster": [r[0] for r in rows], "car": [r[1] for r in rows]})
    pc = df.groupby("cluster")["car"].mean().values
    G = len(pc)
    base = dict(n_firm_events=len(rows), n_failures=len({r[2].launch_tag for r in rows}),
                n_firms=len({r[2].ticker for r in rows}), n_clusters=G)
    if G < 3:
        return [TestResult(name, np.nan, np.nan, np.nan, np.nan, np.nan, **base, note="too few clusters")]
    t, p = stats.ttest_1samp(pc, 0.0)
    se = pc.std(ddof=1) / np.sqrt(G)
    q = stats.t.ppf(0.975, G - 1)
    pos = int((pc > 0).sum())
    nz = int((pc != 0).sum())
    sign_p = stats.binomtest(pos, nz, 0.5).pvalue
    return [TestResult(f"{name} t-test", pc.mean(), pc.mean() - q * se, pc.mean() + q * se, float(t), float(p), **base),
            TestResult(f"{name} sign test", pc.mean(), np.nan, np.nan, pos, float(sign_p), **base,
                       note=f"{pos} of {nz} cluster CARs positive")]


def plain_t_test(fes, window, name="R2 plain t") -> TestResult:
    cars = np.array([car(fe, window)[0] for fe in fes])
    keep = np.isfinite(cars)
    cars, fe_ok = cars[keep], [fe for fe, k in zip(fes, keep) if k]
    N = len(cars)
    t, p = stats.ttest_1samp(cars, 0.0)
    se = cars.std(ddof=1) / np.sqrt(N)
    q = stats.t.ppf(0.975, N - 1)
    return TestResult(name, cars.mean(), cars.mean() - q * se, cars.mean() + q * se, float(t), float(p), N,
                      len({fe.launch_tag for fe in fe_ok}), len({fe.ticker for fe in fe_ok}),
                      len({fe.cluster for fe in fe_ok}), note="ignores cross-correlation (literature baseline)")


def rank_test(fes, window, n_sim=5000, seed=C.RANDOM_SEED, name="R3 rank (simulated p)") -> TestResult:
    """Multi-day rank statistic (Corrado 1989 style) with a simulated null.

    For each firm-event, abnormal returns over estimation + event days are ranked;
    U = rank / (M + 1) - 0.5. Statistic = mean over firm-events of the sum of U over the window.
    Null: the same statistic with the window placed at a random spot in each estimation window.
    """
    rng = np.random.default_rng(seed)
    a, b = window
    L = b - a + 1
    obs, nulls, used = [], [], []
    for fe in fes:
        mask = (fe.rel_days >= a) & (fe.rel_days <= b)
        ev_ar = abnormal(fe)[mask]
        if mask.sum() != L or np.isnan(ev_ar).any():
            continue
        est_ar = fe.resid.values
        allar = np.concatenate([est_ar, ev_ar])
        u = stats.rankdata(allar) / (len(allar) + 1) - 0.5
        obs.append(u[-L:].sum())
        nulls.append(u[:len(est_ar)])
        used.append(fe)
    if len(obs) < 3:
        return TestResult(name, np.nan, np.nan, np.nan, np.nan, np.nan, len(obs), 0, 0, 0, note="too few")
    stat_obs = float(np.mean(obs))
    sims = np.empty(n_sim)
    for s in range(n_sim):
        tot = 0.0
        for u in nulls:
            k = rng.integers(0, len(u) - L + 1)
            tot += u[k:k + L].sum()
        sims[s] = tot / len(nulls)
    p = float((np.sum(np.abs(sims) >= abs(stat_obs)) + 1) / (n_sim + 1))
    cars = np.array([car(fe, window)[0] for fe in used])
    return TestResult(name, float(cars.mean()), np.nan, np.nan, stat_obs, p, len(used),
                      len({fe.launch_tag for fe in used}), len({fe.ticker for fe in used}),
                      len({fe.cluster for fe in used}), note=f"{n_sim} simulations, seed {seed}; ignores cross-correlation")
