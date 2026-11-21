"""Independent verification of the published T-Minus Markets statistics.

Reads ONLY the published derived data (site/data/*.json) and the published results
(data/processed/results.json). Does not import any pipeline module: every statistic is
recomputed here from first principles, then compared with the published value.

What can be verified from published data: every test statistic, interval and p-value built
from CARs, CAR variances and CAR correlations (all R-checks except R3/R9, which need prices).
What cannot: the CARs themselves (they need licensed prices; the owner re-runs step 05 locally).

Usage:  python audit/verify_published.py [repo_root]   -> prints a table, writes audit/verification.json
"""
from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

ROOT = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
TOL = {"estimate": 1e-9, "ci": 1e-9, "stat": 1e-8, "p": 1e-8}
PATH_TOL = 1e-7      # daily abnormal returns are exported rounded to 8 decimals


def load():
    fe = json.loads((ROOT / "site/data/firm_events.json").read_text())
    rho = json.loads((ROOT / "site/data/rho.json").read_text())
    res = json.loads((ROOT / "data/processed/results.json").read_text())
    return fe, rho, res


def cluster_ci(cars, clusters, level=0.95):
    cars, clusters = np.asarray(cars), np.asarray(clusters)
    N, mu = len(cars), cars.mean()
    groups = defaultdict(float)
    for c, v in zip(clusters, cars - mu):
        groups[c] += v
    G = len(groups)
    se = np.sqrt(G / (G - 1) * sum(v * v for v in groups.values())) / N
    q = stats.t.ppf(0.5 + level / 2, G - 1)
    return mu, mu - q * se, mu + q * se, se, G


def bmp_kp(rows, rho_pairs, window):
    """Boehmer-Musumeci-Poulsen t on standardized CARs, Kolari-Pynnonen adjusted with within-cluster rho."""
    rows = [r for r in rows if r["windows"][window]["car"] is not None]
    ids = {r["id"] for r in rows}
    cars = np.array([r["windows"][window]["car"] for r in rows])
    scar = cars / np.sqrt([r["windows"][window]["var"] for r in rows])
    N = len(rows)
    t = scar.mean() * np.sqrt(N) / scar.std(ddof=1)
    S = sum(2 * v for a, b, v in rho_pairs if a in ids and b in ids)          # ordered pairs
    adj = np.sqrt(max(1 - S / (N * (N - 1)), 1e-12) / (1 + S / N))
    mu, lo, hi, se, G = cluster_ci(cars, [r["cluster"] for r in rows])
    t_adj = t * adj
    return dict(mean=mu, ci_low=lo, ci_high=hi, stat=t_adj, p=2 * stats.t.sf(abs(t_adj), G - 1), N=N, G=G,
                failures=len({r["launch_tag"] for r in rows}), firms=len({r["ticker"] for r in rows}), se=se,
                t_unadj=t, adj=adj, mean_scar=scar.mean())


def portfolio(rows, window):
    by = defaultdict(list)
    for r in rows:
        if r["windows"][window]["car"] is not None:
            by[r["cluster"]].append(r["windows"][window]["car"])
    pc = np.array([np.mean(v) for v in by.values()])
    G = len(pc)
    t, p = stats.ttest_1samp(pc, 0.0)
    se = pc.std(ddof=1) / np.sqrt(G); q = stats.t.ppf(0.975, G - 1)
    pos, nz = int((pc > 0).sum()), int((pc != 0).sum())
    return dict(mean=pc.mean(), ci_low=pc.mean() - q * se, ci_high=pc.mean() + q * se, stat=t, p=p,
                sign_p=stats.binomtest(pos, nz, 0.5).pvalue, pos=pos, G=G)


def plain(rows, window):
    c = np.array([r["windows"][window]["car"] for r in rows if r["windows"][window]["car"] is not None])
    t, p = stats.ttest_1samp(c, 0.0)
    se = c.std(ddof=1) / np.sqrt(len(c)); q = stats.t.ppf(0.975, len(c) - 1)
    return dict(mean=c.mean(), ci_low=c.mean() - q * se, ci_high=c.mean() + q * se, stat=t, p=p)


def main():
    fe, rho, res = load()
    riv = [r for r in fe if r["group"] == "rival"]
    checks = []

    def compare(label, mine, pub, keys=("mean", "ci_low", "ci_high", "stat", "p")):
        pmap = {"mean": "mean_car"}
        for k in keys:
            a, b = mine.get(k), pub.get(pmap.get(k, k))
            if b is None or a is None:
                continue
            tol = TOL["p"] if k == "p" else TOL["stat"] if k == "stat" else TOL["ci"]
            checks.append(dict(item=label, quantity=k, published=b, recomputed=float(a), diff=abs(a - b), ok=abs(a - b) <= tol))

    prim = bmp_kp(riv, rho["primary"], "primary")
    compare("H2 primary (BMP-KP)", prim, res["primary"])
    rob = {r["name"]: r for r in res["robustness"]}
    pf = portfolio(riv, "primary")
    compare("R1 portfolio t-test", pf, rob["R1 portfolio t-test"])
    checks.append(dict(item="R1 portfolio sign test", quantity="p", published=rob["R1 portfolio sign test"]["p"],
                       recomputed=pf["sign_p"], diff=abs(pf["sign_p"] - rob["R1 portfolio sign test"]["p"]),
                       ok=abs(pf["sign_p"] - rob["R1 portfolio sign test"]["p"]) <= TOL["p"]))
    compare("R2 plain t", plain(riv, "primary"), rob["R2 plain t"])
    compare("R4 window [-1,+3]", bmp_kp(riv, rho["robust"], "robust"), rob["R4 window [-1,+3]"])
    compare("R5a drop low-confidence timing", bmp_kp([r for r in riv if r["disclosure_confidence"] != "low"], rho["primary"], "primary"),
            rob["R5a drop low-confidence timing"])
    compare("R6 drop fallback-model events", bmp_kp([r for r in riv if r["model"] == "market_model"], rho["primary"], "primary"),
            rob["R6 drop fallback-model events"])
    sizes = defaultdict(set)
    for r in riv:
        sizes[r["cluster"]].add(r["launch_tag"])
    compare("R7 drop multi-failure clusters", bmp_kp([r for r in riv if len(sizes[r["cluster"]]) == 1], rho["primary"], "primary"),
            rob["R7 drop multi-failure clusters"])
    for tk in sorted({r["ticker"] for r in riv}):
        compare(f"R8 without {tk}", bmp_kp([r for r in riv if r["ticker"] != tk], rho["primary"], "primary"), rob[f"R8 without {tk}"])
    for spec in res["exploratory_confounding"]["results"]:
        if spec["id"] in ("E1", "E2", "E3"):
            drop = set(spec["dropped"])
            compare(f"{spec['id']} (exploratory)", bmp_kp([r for r in riv if f"{r['launch_tag']} {r['ticker']}" not in drop],
                                                         rho["primary"], "primary"), spec)
    # provider cases: CI = CAR +/- 1.96 sqrt(Var)
    for c in res["provider_case_series"]:
        rec = next(r for r in fe if r["group"] != "rival" and r["launch_tag"] == c["launch_tag"] and r["ticker"] == c["ticker"])
        w = rec["windows"]["primary"]
        se = np.sqrt(w["var"])
        lo, hi = w["car"] - 1.96 * se, w["car"] + 1.96 * se          # the pipeline uses the constant 1.96
        checks.append(dict(item=f"Maker {c['vehicle']} {c['day0']} CAR", quantity="mean", published=c["car_primary"], recomputed=w["car"],
                           diff=abs(w["car"] - c["car_primary"]), ok=abs(w["car"] - c["car_primary"]) <= TOL["estimate"]))
        checks.append(dict(item=f"Maker {c['vehicle']} {c['day0']} CI low", quantity="ci_low", published=c["car_primary_ci"][0], recomputed=lo,
                           diff=abs(lo - c["car_primary_ci"][0]), ok=abs(lo - c["car_primary_ci"][0]) <= TOL["ci"]))
        path_sum = sum(p["ar"] for p in rec["path"] if p["t"] in (0, 1))
        checks.append(dict(item=f"Maker {c['vehicle']} {c['day0']} path AR[0]+AR[1] = CAR", quantity="mean", published=c["car_primary"],
                           recomputed=path_sum, diff=abs(path_sum - c["car_primary"]), ok=abs(path_sum - c["car_primary"]) <= PATH_TOL))
    # placebo percentile from the stored distribution
    pl = res["placebo"]; d = np.array(pl["distribution"])
    for k, v in (("actual_percentile", float(np.mean(d <= pl["actual_mean_car"]) * 100)),
                 ("two_sided_share", float(2 * min(np.mean(d <= pl["actual_mean_car"]), np.mean(d >= pl["actual_mean_car"]))))):
        checks.append(dict(item="R9 placebo", quantity=k, published=pl[k], recomputed=v, diff=abs(v - pl[k]), ok=abs(v - pl[k]) <= 1e-9))
    # rival path consistency: AR[0]+AR[1] equals CAR[0,+1] for every rival record
    bad = [r["id"] for r in riv if abs(sum(p["ar"] for p in r["path"] if p["t"] in (0, 1)) - r["windows"]["primary"]["car"]) > PATH_TOL]
    checks.append(dict(item="All rival paths: AR[0]+AR[1] = CAR[0,+1]", quantity="count mismatches", published=0, recomputed=len(bad),
                       diff=len(bad), ok=not bad))

    out = ROOT / "audit"
    out.mkdir(exist_ok=True)
    (out / "verification.json").write_text(json.dumps(dict(primary_detail=prim, checks=checks), indent=1, default=float))
    w = max(len(c["item"]) for c in checks)
    for c in checks:
        print(f"{'PASS' if c['ok'] else 'FAIL'}  {c['item']:<{w}}  {c['quantity']:<18} published {c['published']:+.10f}  recomputed {c['recomputed']:+.10f}")
    n_ok = sum(c["ok"] for c in checks)
    print(f"\n{n_ok} of {len(checks)} published quantities reproduced within tolerance.")
    return 0 if n_ok == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
