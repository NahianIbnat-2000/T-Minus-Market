"""Audit diagnostics computed from the published derived data only (no prices).

Descriptive: they describe how the prespecified estimate depends on weighting, firms and outliers,
and how much the sample can detect. None of them is a new test of H2.
"""
from __future__ import annotations

from collections import defaultdict

import numpy as np
from scipy import stats


def _rows(firm_events, drop=()):
    return [r for r in firm_events if r["group"] == "rival" and r["windows"]["primary"]["car"] is not None
            and f"{r['launch_tag']} {r['ticker']}" not in set(drop)]


def weighting(firm_events, drop=()):
    riv = _rows(firm_events, drop)
    car = np.array([r["windows"]["primary"]["car"] for r in riv])
    sd = np.sqrt([r["windows"]["primary"]["var"] for r in riv])
    by_c, by_f = defaultdict(list), defaultdict(list)
    for r, c in zip(riv, car):
        by_c[r["cluster"]].append(c)
        by_f[r["firm"]].append(c)
    return {
        "observation_weighted": float(car.mean()),
        "event_weighted": float(np.mean([np.mean(v) for v in by_c.values()])),
        "precision_weighted": float(np.sum(car / sd) / np.sum(1 / sd)),
        "firm_balanced": float(np.mean([np.mean(v) for v in by_f.values()])),
        "median": float(np.median(car)),
        "share_negative": float(np.mean(car < 0)),
        "mean_standardized": float(np.mean(car / sd)),
        "n": len(riv),
    }


def per_firm(firm_events):
    riv = _rows(firm_events)
    out = defaultdict(lambda: {"cars": [], "failures": set(), "clusters": set(), "ticker": ""})
    for r in riv:
        d = out[r["firm"]]
        d["cars"].append(r["windows"]["primary"]["car"]); d["failures"].add(r["launch_tag"]); d["clusters"].add(r["cluster"])
        d["ticker"] = r["ticker"]
    res = []
    for firm, d in sorted(out.items(), key=lambda kv: -len(kv[1]["cars"])):
        c = np.array(d["cars"])
        res.append({"firm": firm, "ticker": d["ticker"], "n": len(c), "failures": len(d["failures"]), "clusters": len(d["clusters"]),
                    "mean": float(c.mean()), "median": float(np.median(c)), "min": float(c.min()), "max": float(c.max())})
    return res


def exposure_matrix(firm_events):
    """Clusters (rows, in date order) x firms: number of firm-events."""
    riv = _rows(firm_events)
    firms = [f["firm"] for f in per_firm(firm_events)]
    first = {}
    for r in riv:
        first[r["cluster"]] = min(first.get(r["cluster"], r["day0"]), r["day0"])
    rows = []
    for cl in sorted(first, key=lambda c: first[c]):
        mem = [r for r in riv if r["cluster"] == cl]
        rows.append({"cluster": cl, "date": first[cl], "vehicles": sorted({r["vehicle"] for r in mem}),
                     "counts": {f: sum(r["firm"] == f for r in mem) for f in firms}})
    return firms, rows


def power(primary):
    """MDE and power for the equal-weighted mean, from the published cluster-robust interval (t, G-1 df)."""
    G = primary["n_clusters"]
    q = stats.t.ppf(0.975, G - 1)
    se = (primary["ci_high"] - primary["ci_low"]) / (2 * q)
    q90 = stats.t.ppf(0.95, G - 1)

    def pw(d):
        ncp = d / se
        return float(1 - stats.nct.cdf(q, G - 1, ncp) + stats.nct.cdf(-q, G - 1, ncp))

    return {"se": float(se), "df": G - 1, "mde80": float((q + stats.t.ppf(0.80, G - 1)) * se),
            "mde90": float((q + stats.t.ppf(0.90, G - 1)) * se),
            "power": {d: pw(d) for d in (0.01, 0.02, 0.03)},
            "ci90": (float(primary["mean_car"] - q90 * se), float(primary["mean_car"] + q90 * se))}
