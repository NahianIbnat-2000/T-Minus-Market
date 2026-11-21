"""Phase 2: robustness checks R4-R9, provider case series and H3 exploratory analyses.

The main test and R1-R3 live in eventstudy.py. Every function here returns plain
records so step 05 can write one results file used by the report, paper and website.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

import config as C
from eventstudy import (FirmEvent, abnormal, bmp_kp_test, build_firm_event, car, plain_t_test,
                        portfolio_test, rank_test, _cluster_ci)
from eventtime import get_calendar

PRIMARY = C.EVENT_WINDOWS["primary"]
ROBUST = C.EVENT_WINDOWS["robust"]
LONG = C.EVENT_WINDOWS["descriptive"]

# The one low-confidence timing event recorded in disclosure_times.csv
LOW_CONFIDENCE = "low"


def rival_robustness(fes: list[FirmEvent], rows: pd.DataFrame, returns_by: dict, bench_for) -> list:
    """R1 to R8 for the rival test. R9 (placebo) is separate because it is slow."""
    out = []
    out += portfolio_test(fes, PRIMARY)
    out.append(plain_t_test(fes, PRIMARY))
    out.append(rank_test(fes, PRIMARY))
    r4 = bmp_kp_test(fes, ROBUST, name="R4 window [-1,+3]")
    out.append(r4)

    # R5a: drop low-confidence timing events
    keep = [fe for fe in fes if fe.meta.get("disclosure_confidence") != LOW_CONFIDENCE]
    out.append(bmp_kp_test(keep, PRIMARY, name="R5a drop low-confidence timing"))
    # R5b: move day 0 one session later for low-confidence events
    shifted = []
    for fe in fes:
        if fe.meta.get("disclosure_confidence") == LOW_CONFIDENCE:
            row = rows[(rows["launch_tag"] == fe.launch_tag) & (rows["ticker"] == fe.ticker)].iloc[0]
            alt = build_firm_event(row, returns_by[row["ticker"]], bench_for(row["exchange"]), day0_shift=1)
            shifted.append(alt if alt is not None else fe)
        else:
            shifted.append(fe)
    out.append(bmp_kp_test(shifted, PRIMARY, name="R5b low-confidence day 0 + 1 session"))

    # R6: drop market-adjusted fallback events
    out.append(bmp_kp_test([fe for fe in fes if fe.model == "market_model"], PRIMARY,
                           name="R6 drop fallback-model events"))
    # R7: drop clusters with more than one failure
    per = pd.Series([fe.launch_tag for fe in fes]).groupby([fe.cluster for fe in fes]).nunique()
    single = set(per[per == 1].index)
    out.append(bmp_kp_test([fe for fe in fes if fe.cluster in single], PRIMARY,
                           name="R7 drop multi-failure clusters"))
    # R8: leave one firm out
    for tic in sorted({fe.ticker for fe in fes}):
        out.append(bmp_kp_test([fe for fe in fes if fe.ticker != tic], PRIMARY, name=f"R8 without {tic}"))
    return out


def placebo(fes: list[FirmEvent], rows, returns_by: dict, bench_for, failure_day0s: dict, n_draws=1000,
            seed=C.RANDOM_SEED) -> dict:
    """R9: mean CAR[0,+1] at random non-event days for the same firm-events.

    Eligible pseudo day 0: a session of the firm's exchange with a full estimation window inside
    the firm's listed price history, at least 10 sessions away from any failure day 0 for that
    ticker. This is a benchmark for context, not an exact permutation test.
    """
    rng = np.random.default_rng(seed)
    pools = []
    for fe in fes:
        row = rows[(rows["launch_tag"] == fe.launch_tag) & (rows["ticker"] == fe.ticker)].iloc[0]
        sessions = pd.DatetimeIndex(get_calendar(row["exchange"]).sessions)
        sessions = sessions.tz_localize(None) if sessions.tz is not None else sessions
        r = returns_by[row["ticker"]].set_index("date")["ret"]
        ls = row.get("listing_start")
        first = max(r.index.min(), pd.Timestamp(ls)) if pd.notna(ls) and str(ls) != "" else r.index.min()
        valid = sessions[(sessions > first) & (sessions <= r.index.max())]
        idx = np.arange(len(valid))
        ok = (idx >= 260) & (idx < len(valid) - 2)
        bad = set()
        for d in failure_day0s.get(row["ticker"], []):
            if d in valid:
                k = valid.get_loc(d)
                bad.update(range(k - 10, k + 11))
        cand = [valid[i] for i in idx[ok] if i not in bad]
        pools.append((row, cand))
    eligible = [len(c) for _, c in pools]
    actual = np.nanmean([car(fe, PRIMARY)[0] for fe in fes])
    means = np.empty(n_draws)
    cache = {}
    for d in range(n_draws):
        vals = []
        for (row, cand) in pools:
            day = cand[rng.integers(0, len(cand))]
            key = (row["ticker"], day)
            if key not in cache:
                r2 = row.copy()
                r2["day0"] = day
                fe = build_firm_event(r2, returns_by[row["ticker"]], bench_for(row["exchange"]), rel_range=(0, 1))
                cache[key] = car(fe, PRIMARY)[0] if fe is not None else np.nan
            vals.append(cache[key])
        means[d] = np.nanmean(vals)
    pct = float(np.mean(means <= actual) * 100)
    lo, hi = np.percentile(means, [2.5, 97.5])
    # Monte Carlo s.e. of a tail share p estimated from n draws
    p_two = float(2 * min(np.mean(means <= actual), np.mean(means >= actual)))
    mc_se = float(np.sqrt(max(p_two * (1 - p_two), 1e-12) / n_draws))
    return {"name": "R9 placebo benchmark", "actual_mean_car": float(actual), "draws": n_draws, "seed": seed,
            "placebo_mean": float(means.mean()), "placebo_2.5pct": float(lo), "placebo_97.5pct": float(hi),
            "actual_percentile": pct, "two_sided_share": p_two, "monte_carlo_se": mc_se,
            "eligible_dates_min": int(min(eligible)), "eligible_dates_median": int(np.median(eligible)),
            "note": "benchmark for context, not an exact permutation test", "distribution": means.tolist()}


def case_series(fes: list[FirmEvent]) -> list[dict]:
    """Provider failures: one record per firm-event, with its own 95% interval and path."""
    out = []
    for fe in fes:
        rec = {"launch_tag": fe.launch_tag, "ticker": fe.ticker, "firm": fe.meta.get("firm_name"),
               "vehicle": fe.meta.get("lv_type"), "day0": str(fe.day0.date()), "model": fe.model,
               "sigma_daily": fe.sigma}
        for nm, w in [("primary", PRIMARY), ("robust", ROBUST)]:
            c, v, _ = car(fe, w)
            se = np.sqrt(v) if np.isfinite(v) else np.nan
            rec[f"car_{nm}"] = c
            rec[f"car_{nm}_ci"] = [c - 1.96 * se, c + 1.96 * se] if np.isfinite(c) else None
        ar = abnormal(fe)
        rec["path"] = [{"t": int(t), "ar": None if np.isnan(a) else float(a)} for t, a in zip(fe.rel_days, ar)]
        out.append(rec)
    return out


def holm(pvals: list[float]) -> list[float]:
    m = len(pvals)
    order = np.argsort(pvals)
    adj = np.empty(m)
    running = 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (m - rank) * pvals[i]))
        adj[i] = running
    return adj.tolist()


def exploratory(rival_fes, provider_fail_fes, provider_success_fes, first_flight: dict) -> list[dict]:
    """H3a-H3c. Estimates with cluster-robust intervals; Holm-adjusted p-values across the family."""
    res = []
    # H3a: rival CAR after first-flight failures vs failures of flown rockets
    cars = pd.DataFrame([{"car": car(fe, PRIMARY)[0], "cluster": fe.cluster,
                          "first": bool(first_flight.get(fe.launch_tag, False))} for fe in rival_fes]).dropna()
    if cars["first"].nunique() == 2:
        a, b = cars[cars["first"]], cars[~cars["first"]]
        diff = a["car"].mean() - b["car"].mean()
        t, p = stats.ttest_ind(a["car"], b["car"], equal_var=False)
        res.append({"id": "H3a", "label": "Rival CAR[0,+1]: first-flight failures minus others",
                    "estimate": float(diff), "n": [len(a), len(b)], "p_raw": float(p)})
    # H3b: provider success vs failure (exploratory, uses success launches as comparison group)
    s = np.array([car(fe, PRIMARY)[0] for fe in provider_success_fes])
    s = s[np.isfinite(s)]
    f = np.array([car(fe, PRIMARY)[0] for fe in provider_fail_fes])
    f = f[np.isfinite(f)]
    if len(s) >= 3 and len(f) >= 2:
        t, p = stats.ttest_ind(f, s, equal_var=False)
        res.append({"id": "H3b", "label": "Provider CAR[0,+1]: failures minus successes",
                    "estimate": float(f.mean() - s.mean()), "n": [len(f), len(s)], "p_raw": float(p),
                    "success_mean": float(s.mean()), "failure_mean": float(f.mean())})
    # H3c: does the rival effect last? CAR[0,+20] vs CAR[0,+1]
    long = np.array([car(fe, LONG)[0] for fe in rival_fes])
    short = np.array([car(fe, PRIMARY)[0] for fe in rival_fes])
    ok = np.isfinite(long) & np.isfinite(short)
    if ok.sum() >= 3:
        cl = np.array([fe.cluster for fe in rival_fes])[ok]
        mu, lo, hi, se, G = _cluster_ci(long[ok], cl)
        t = mu / se if se else np.nan
        p = float(2 * stats.t.sf(abs(t), G - 1)) if np.isfinite(t) else np.nan
        res.append({"id": "H3c", "label": "Rival CAR[0,+20] (descriptive)", "estimate": float(mu),
                    "ci": [float(lo), float(hi)], "n": int(ok.sum()), "p_raw": p,
                    "car_0_1_same_sample": float(short[ok].mean())})
    adj = holm([r["p_raw"] for r in res]) if res else []
    for r, a in zip(res, adj):
        r["p_holm"] = a
        r["label"] += " [exploratory]"
    return res


def placebo_shared(fes: list[FirmEvent], rows, returns_by: dict, bench_for, failure_day0s: dict, n_draws=1000,
                   seed=C.RANDOM_SEED) -> dict:
    """R9b (EXPLORATORY, added after the 22 Nov 2026 audit): placebo with ONE shared pseudo-date per cluster.

    R9 draws an independent random day for every firm-event, which breaks the same-day co-movement of
    rivals hit by one failure and so understates the spread of the placebo averages. Here each draw
    picks one calendar date per cluster; every firm-event in that cluster uses the first eligible
    session of its own exchange on or after that date. Eligibility per firm-event is the same as R9.
    A benchmark for context, not an exact permutation test.
    """
    rng = np.random.default_rng(seed)
    members = {}
    for fe in fes:
        row = rows[(rows["launch_tag"] == fe.launch_tag) & (rows["ticker"] == fe.ticker)].iloc[0]
        sessions = pd.DatetimeIndex(get_calendar(row["exchange"]).sessions)
        sessions = sessions.tz_localize(None) if sessions.tz is not None else sessions
        r = returns_by[row["ticker"]].set_index("date")["ret"]
        ls = row.get("listing_start")
        first = max(r.index.min(), pd.Timestamp(ls)) if pd.notna(ls) and str(ls) != "" else r.index.min()
        valid = sessions[(sessions > first) & (sessions <= r.index.max())]
        idx = np.arange(len(valid))
        ok = (idx >= 260) & (idx < len(valid) - 2)
        bad = set()
        for d in failure_day0s.get(row["ticker"], []):
            if d in valid:
                k = valid.get_loc(d)
                bad.update(range(k - 10, k + 11))
        cand = pd.DatetimeIndex([valid[i] for i in idx[ok] if i not in bad])
        members.setdefault(fe.cluster, []).append((fe, row, cand))
    plans, n_common = [], 0
    for cl, mem in members.items():
        common = mem[0][2]
        for _, _, c in mem[1:]:
            common = common.intersection(c)
        if len(common):
            n_common += 1
            dates = common
        else:                                   # no calendar date eligible for all: use the union, map forward
            dates = mem[0][2]
            for _, _, c in mem[1:]:
                dates = dates.union(c)
        plans.append((dates, mem))
    actual = np.nanmean([car(fe, PRIMARY)[0] for fe in fes])
    means, cache = np.empty(n_draws), {}
    for d in range(n_draws):
        vals = []
        for dates, mem in plans:
            pick = dates[rng.integers(0, len(dates))]
            for fe, row, cand in mem:
                k = cand.searchsorted(pick)
                if k >= len(cand):
                    vals.append(np.nan)
                    continue
                day = cand[k]
                key = (row["ticker"], day)
                if key not in cache:
                    r2 = row.copy()
                    r2["day0"] = day
                    f2 = build_firm_event(r2, returns_by[row["ticker"]], bench_for(row["exchange"]), rel_range=(0, 1))
                    cache[key] = car(f2, PRIMARY)[0] if f2 is not None else np.nan
                vals.append(cache[key])
        means[d] = np.nanmean(vals)
    pct = float(np.mean(means <= actual) * 100)
    lo, hi = np.percentile(means, [2.5, 97.5])
    p_two = float(2 * min(np.mean(means <= actual), np.mean(means >= actual)))
    return {"name": "R9b placebo, shared date per cluster [exploratory]", "actual_mean_car": float(actual), "draws": n_draws,
            "seed": seed, "placebo_mean": float(means.mean()), "placebo_sd": float(means.std(ddof=1)),
            "placebo_2.5pct": float(lo), "placebo_97.5pct": float(hi), "actual_percentile": pct, "two_sided_share": p_two,
            "monte_carlo_se": float(np.sqrt(max(p_two * (1 - p_two), 1e-12) / n_draws)),
            "clusters": len(plans), "clusters_with_common_date": n_common,
            "note": "exploratory, added after the audit; one pseudo-date per cluster; benchmark, not a permutation test",
            "distribution": means.tolist()}
