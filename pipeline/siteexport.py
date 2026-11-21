"""Phase 3: turn FirmEvent objects into website records, and a reference test that works
only from those records.

The website receives DERIVED statistics only: CARs, their variances, daily abnormal-return
paths and same-cluster CAR correlations. No raw prices, raw returns, alphas or betas are
exported, so the site never republishes Yahoo data (audit risk 8).

`bmp_kp_from_records` re-implements the primary test from exported records. It must equal
eventstudy.bmp_kp_test exactly (checked by tests), and the browser module must equal it
within the documented tolerance (checked by the Python-JS parity test).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

import config as C
from eventstudy import FirmEvent, abnormal, car, car_corr

WINDOWS = C.EVENT_WINDOWS                      # primary, robust, descriptive
PATH_RANGE = (-5, 20)


def record_id(fe: FirmEvent) -> str:
    return f"{fe.launch_tag}|{fe.ticker}|{fe.meta.get('role', '')}"


def to_record(fe: FirmEvent, group: str, flag: dict | None) -> dict:
    rec = {
        "id": record_id(fe), "group": group, "launch_tag": fe.launch_tag, "ticker": fe.ticker,
        "exchange": fe.exchange, "firm": fe.meta.get("firm_name"), "vehicle": fe.meta.get("lv_type"),
        "role": fe.meta.get("role"), "tier": fe.tier, "cluster": int(fe.cluster),
        "day0": str(fe.day0.date()), "model": fe.model, "est_obs": int(len(fe.est_r)),
        "sigma": float(fe.sigma), "disclosure_confidence": fe.meta.get("disclosure_confidence"),
        "flag": flag, "windows": {}, "path": [],
    }
    for name, w in WINDOWS.items():
        c, v, L = car(fe, w)
        rec["windows"][name] = {"car": None if not np.isfinite(c) else float(c),
                                "var": None if not np.isfinite(v) else float(v), "L": int(L)}
    ar = abnormal(fe)
    for t, a in zip(fe.rel_days, ar):
        if PATH_RANGE[0] <= t <= PATH_RANGE[1]:
            rec["path"].append({"t": int(t), "ar": None if np.isnan(a) else round(float(a), 8)})
    return rec


def rho_pairs(fes: list[FirmEvent]) -> dict:
    """For each window: [id_i, id_j, rho] for every unordered same-cluster pair (i < j)."""
    out = {}
    for name, w in WINDOWS.items():
        pairs = []
        for i in range(len(fes)):
            for j in range(i + 1, len(fes)):
                if fes[i].cluster == fes[j].cluster and fes[i].cluster >= 0:
                    pairs.append([record_id(fes[i]), record_id(fes[j]), float(car_corr(fes[i], fes[j], w))])
        out[name] = pairs
    return out


# --------------------------------------------------------------------------- reference test from records
def bmp_kp_from_records(records: list[dict], rho: dict, window: str) -> dict:
    """Primary test computed only from exported numbers (mirrors eventstudy.bmp_kp_test)."""
    rows = [r for r in records if r["windows"][window]["car"] is not None]
    ids = [r["id"] for r in rows]
    cars = np.array([r["windows"][window]["car"] for r in rows])
    var = np.array([r["windows"][window]["var"] for r in rows])
    cl = np.array([r["cluster"] for r in rows])
    N = len(rows)
    G = len(np.unique(cl)) if N else 0
    mu = float(cars.mean()) if N else float("nan")
    res = {"mean": mu, "ci_low": None, "ci_high": None, "stat": None, "p": None, "n": N,
           "clusters": G, "failures": len({r["launch_tag"] for r in rows}),
           "firms": len({r["ticker"] for r in rows}), "mean_corr": None}
    if G >= 2:
        u = pd.Series(cars - mu).groupby(cl).sum().values
        se = np.sqrt(G / (G - 1) * np.sum(u ** 2)) / N
        q = stats.t.ppf(0.975, G - 1)
        res["ci_low"], res["ci_high"] = float(mu - q * se), float(mu + q * se)
    if N < 3:
        return res
    scar = cars / np.sqrt(var)
    t = scar.mean() * np.sqrt(N) / scar.std(ddof=1)
    keep = set(ids)
    pr = [p for p in rho[window] if p[0] in keep and p[1] in keep]
    S = 2 * sum(p[2] for p in pr)
    adj = np.sqrt(max(1 - S / (N * (N - 1)), 1e-12) / (1 + S / N))
    t_adj = t * adj
    res["stat"] = float(t_adj)
    res["p"] = float(2 * stats.t.sf(abs(t_adj), max(G - 1, 1)))
    res["mean_corr"] = float(np.mean([p[2] for p in pr])) if pr else 0.0
    return res
