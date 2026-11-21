"""Step 04 logic: day 0, data coverage, clusters, power and the feasibility gate.

This step reads ONLY estimation-window returns (to measure normal volatility)
and checks whether event-window prices EXIST. It never computes an abnormal
return inside an event window, so no result can influence the sample rules.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

import config as C
from eventtime import day_zero, get_calendar


def load_disclosures(path, events: pd.DataFrame) -> pd.DataFrame:
    """One disclosure time per launch. Missing -> launch time, flagged provisional."""
    base = events[["launch_tag", "launch_utc"]].drop_duplicates("launch_tag").copy()
    base["disclosure_utc"] = pd.to_datetime(base["launch_utc"], utc=True)
    base["disclosure_source"] = "GCAT launch time (provisional)"
    base["disclosure_confidence"] = "provisional"
    if path is not None and path.exists():
        d = pd.read_csv(path, dtype=str, keep_default_na=False)
        d = d[(d["disclosure_utc"] != "") | (d["confidence"] != "")]
        d["disclosure_utc"] = pd.to_datetime(d["disclosure_utc"].replace("", pd.NA), utc=True)
        base = base.merge(d, on="launch_tag", how="left", suffixes=("", "_manual"))
        has = base["disclosure_utc_manual"].notna()
        base.loc[has, "disclosure_utc"] = base.loc[has, "disclosure_utc_manual"]
        noted = base["confidence"].fillna("") != ""
        base.loc[noted, "disclosure_source"] = base.loc[noted, "source"]
        base.loc[noted, "disclosure_confidence"] = base.loc[noted, "confidence"]
        base = base[["launch_tag", "launch_utc", "disclosure_utc", "disclosure_source", "disclosure_confidence"]]
    return base


def timing_sensitive(disclosure_utc, exchange: str) -> bool:
    """True if day 0 would change for a disclosure slightly earlier or up to a few hours later."""
    t = pd.Timestamp(disclosure_utc)
    shifts = [-C.TIMING_EARLY_MIN, 0, 30, 60, C.TIMING_LATE_MIN]
    return len({day_zero(t + pd.Timedelta(minutes=m), exchange) for m in shifts}) > 1


def _market_model_sigma(r: np.ndarray, m: np.ndarray) -> float:
    X = np.column_stack([np.ones_like(m), m])
    beta, *_ = np.linalg.lstsq(X, r, rcond=None)
    resid = r - X @ beta
    return float(np.sqrt(resid @ resid / (len(r) - 2)))


def check_one(ev: pd.Series, returns: pd.DataFrame, bench_returns: pd.DataFrame) -> dict:
    out = {"day0": pd.NaT, "est_obs": 0, "model": None, "sigma": np.nan, "coverage_reason": None}
    if ev["exchange"] not in C.BENCHMARKS:
        out["coverage_reason"] = f"no_benchmark_for_exchange_{ev['exchange']}"
        return out
    d0 = day_zero(ev["disclosure_utc"], ev["exchange"])
    out["day0"] = d0
    out["timing_sensitive"] = timing_sensitive(ev["disclosure_utc"], ev["exchange"])
    cal = get_calendar(ev["exchange"])
    sessions = cal.sessions
    if d0 not in sessions:
        out["coverage_reason"] = "day0_not_a_session"
        return out
    i0 = sessions.get_loc(d0)
    lo, hi = C.EST_WINDOW
    if i0 + lo < 0:
        out["coverage_reason"] = "calendar_starts_too_late"
        return out
    est_days = sessions[i0 + lo: i0 + hi + 1].tz_localize(None) if sessions.tz is not None else sessions[i0 + lo: i0 + hi + 1]
    ew_lo = min(w[0] for w in C.EVENT_WINDOWS.values())
    ew_hi = max(w[1] for w in C.EVENT_WINDOWS.values())
    if i0 + ew_hi >= len(sessions):
        out["coverage_reason"] = "event_window_in_future"
        return out
    ev_days = sessions[i0 + ew_lo: i0 + ew_hi + 1]
    ev_days = ev_days.tz_localize(None) if getattr(ev_days, "tz", None) is not None else ev_days

    r = returns[returns["ticker"] == ev["ticker"]].set_index("date")["ret"]
    # Drop prices from before the firm itself was listed (e.g. a SPAC shell under the same ticker).
    # The first day's return compares with the shell's price, so it is dropped too.
    ls = ev.get("listing_start")
    if ls is not None and pd.notna(ls) and str(ls) != "":
        r = r[r.index > pd.Timestamp(ls).tz_localize(None) if pd.Timestamp(ls).tzinfo else r.index > pd.Timestamp(ls)]
    b = bench_returns.set_index("date")["ret"]
    if r.empty:
        out["coverage_reason"] = "no_price_data_for_ticker"
        return out
    # Event window: prices must exist on every primary-window day; full [-1, +20] reported separately.
    p_lo, p_hi = C.EVENT_WINDOWS[C.PRIMARY_WINDOW]
    prim_days = sessions[i0 + p_lo: i0 + p_hi + 1]
    prim_days = prim_days.tz_localize(None) if getattr(prim_days, "tz", None) is not None else prim_days
    if r.reindex(prim_days).isna().any() or b.reindex(prim_days).isna().any():
        out["coverage_reason"] = "missing_price_in_primary_window"
        return out
    out["full_window_complete"] = bool(r.reindex(ev_days).notna().all())

    joint = pd.concat([r.reindex(est_days), b.reindex(est_days)], axis=1, keys=["r", "m"]).dropna()
    out["est_obs"] = len(joint)
    if len(joint) >= C.EST_MIN_OBS:
        out["model"] = "market_model"
        out["sigma"] = _market_model_sigma(joint["r"].values, joint["m"].values)
    elif len(joint) >= 30:
        out["model"] = "market_adjusted_fallback"
        out["sigma"] = float((joint["r"] - joint["m"]).std(ddof=1))
    else:
        out["coverage_reason"] = "insufficient_estimation_history"
    return out


def assign_clusters(usable: pd.DataFrame) -> pd.Series:
    """Union failures that share any ticker with day 0s within CLUSTER_GAP_TRADING_DAYS sessions."""
    tags = list(usable["launch_tag"].unique())
    parent = {t: t for t in tags}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for (tic, exch), g in usable.groupby(["ticker", "exchange"]):
        sessions = get_calendar(exch).sessions
        g = g.sort_values("day0")
        pos = [sessions.get_loc(d) for d in g["day0"]]
        tg = list(g["launch_tag"])
        for k in range(1, len(tg)):
            if pos[k] - pos[k - 1] <= C.CLUSTER_GAP_TRADING_DAYS and tg[k] != tg[k - 1]:
                parent[find(tg[k])] = find(tg[k - 1])
    roots = {t: find(t) for t in tags}
    ids = {r: i + 1 for i, r in enumerate(sorted(set(roots.values())))}
    return usable["launch_tag"].map(lambda t: ids[roots[t]])


def mde(sigma: float, n: int, window_len: int = 2) -> float:
    """Minimum detectable mean CAR: 5% two-sided, 80% power, t critical values with n-1 df."""
    if n < 2 or not np.isfinite(sigma):
        return float("nan")
    from scipy.stats import t
    df = n - 1
    mult = t.ppf(0.975, df) + t.ppf(0.80, df)
    return mult * sigma * math.sqrt(window_len) / math.sqrt(n)
