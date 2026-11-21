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


def estimand_tests(firm_events, primary, draws=9999, seed=20261121):
    """Inference aligned to each estimand (descriptive companions to the prespecified BMP-KP test).

    A  equal-weighted mean CAR: cluster-robust t (G-1 df), the test that matches the published interval,
       plus a wild cluster bootstrap (Webb six-point weights, null imposed).
    F  firm level: the mean of the per-firm mean CARs with a t interval on 2 df (three firms): shows how
       little firm-level inference is possible.
    """
    riv = _rows(firm_events)
    car = np.array([r["windows"]["primary"]["car"] for r in riv])
    cl = [r["cluster"] for r in riv]
    ids = {c: i for i, c in enumerate(sorted(set(cl)))}
    ci = np.array([ids[c] for c in cl])
    N, G, mu = len(car), len(ids), car.mean()

    def crt(y):
        m = y.mean()
        u = np.bincount(ci, weights=y - m, minlength=G)
        return m / (np.sqrt(G / (G - 1) * np.sum(u ** 2)) / N)

    t_a = crt(car)
    p_a = float(2 * stats.t.sf(abs(t_a), G - 1))
    rng = np.random.default_rng(seed)
    webb = np.array([-np.sqrt(1.5), -1.0, -np.sqrt(0.5), np.sqrt(0.5), 1.0, np.sqrt(1.5)])
    ts = np.array([crt(car * webb[rng.integers(0, 6, G)][ci]) for _ in range(draws)])
    p_boot = float(np.mean(np.abs(ts) >= abs(t_a)))
    by_f = defaultdict(list)
    for r, c in zip(riv, car):
        by_f[r["firm"]].append(c)
    fm = np.array([np.mean(v) for v in by_f.values()])
    k = len(fm)
    if k >= 2:
        se_f = fm.std(ddof=1) / np.sqrt(k)
        q = stats.t.ppf(0.975, k - 1)
        firm = {"k": k, "mean": float(fm.mean()), "ci": (float(fm.mean() - q * se_f), float(fm.mean() + q * se_f)),
                "p": float(2 * stats.t.sf(abs(fm.mean() / se_f), k - 1)) if se_f > 0 else None}
    else:
        firm = {"k": k, "mean": float(fm.mean()) if k else None, "ci": (None, None), "p": None}
    contrib = [{"firm": f, "n": len(v), "share": len(v) / N, "contribution": float(np.sum(v) / N)} for f, v in
               sorted(by_f.items(), key=lambda kv: -len(kv[1]))]
    return {"A": {"estimate": float(mu), "t": float(t_a), "p": p_a, "p_wild": p_boot, "draws": draws, "G": G},
            "B": {"mean_scar": float(np.mean(car / np.sqrt([r["windows"]["primary"]["var"] for r in riv]))),
                  "t": primary.get("stat"), "p": primary.get("p")},
            "firm": firm, "contrib": contrib}


def timing(firm_events):
    """How each event's disclosure time is sourced: 'high'/'low' = sourced company statement (confidence),
    'provisional' = GCAT launch time, used where day 0 does not change within -10 to +180 minutes."""
    from collections import Counter
    out = {}
    for grp, sel in (("rival_reactions", lambda r: r["group"] == "rival"), ("maker_cases", lambda r: r["group"] != "rival")):
        rows = [r for r in firm_events if sel(r)]
        c = Counter(r.get("disclosure_confidence") or "unknown" for r in rows)
        out[grp] = {"n": len(rows), "counts": dict(c), "shares": {k: v / len(rows) for k, v in c.items()} if rows else {}}
    fails = {r["launch_tag"]: r for r in firm_events if r["group"] == "rival"}
    c = Counter(r.get("disclosure_confidence") or "unknown" for r in fails.values())
    out["rival_failures"] = {"n": len(fails), "counts": dict(c)}
    return out
