"""Step 10 (SUPPLEMENT, plan v1.2): add four delisted US launch firms from CRSP.

Orbital Sciences (ORB), Orbital ATK (OA), Astra Space (ASTR) and Virgin Orbit (VORB) have no free price
history, so they were outside the v1.0 sample. A WRDS subscriber ran wrds/tminus_crsp_extract.py, which
returns derived statistics only (CARs, CAR variances, residual correlations). This step merges them with
the published v1.0 records and reruns the same tests. The v1.0 result stays the headline; everything
here is reported next to it, never instead of it. Rules: docs/ANALYSIS_PLAN.md, change log v1.2.

Inputs   data/crsp/tminus_crsp_firm_events.csv, tminus_crsp_pairs.csv, tminus_crsp_run_info.json (not in git)
         site/data/firm_events.json, rho.json, results.json (step 07)
         data/manual/crsp_confounded_events.csv
Outputs  data/processed/crsp_supplement.json (aggregates and maker cases only)
         reports/10_crsp_supplement.md
Usage    python pipeline/10_crsp_supplement.py [--draws 9999]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

import config as C
from diagnostics import estimand_tests
from eventtime import get_calendar
from siteexport import bmp_kp_from_records

CRSP = C.ROOT / "data" / "crsp"
SITE_DATA = C.ROOT / "site" / "data"
FIRM_NAMES = {"ORB": "Orbital Sciences Corp", "OA": "Orbital ATK Inc", "ASTR": "Astra Space", "VORB": "Virgin Orbit"}
WINDOW_KEYS = {"primary": ("car_primary", "var_primary"), "robust": ("car_robust", "var_robust"),
               "descriptive": ("car_descriptive", "var_descriptive")}
H2_TIERS = {"tier1", "tier2"}        # as in steps 05 and 09; CRSP tier 3 rows are never tested
RHO_SENSITIVITY = (0.0, 0.5)          # cross-source residual correlation: imputed value plus these bounds


def _sessions(exchange):
    s = get_calendar(exchange).sessions
    return pd.DatetimeIndex(s.tz_localize(None) if s.tz is not None else s)


def window_days(exchange, day0, window):
    s = _sessions(exchange)
    k = s.get_loc(pd.Timestamp(day0))
    a, b = C.EVENT_WINDOWS[window]
    return set(s[max(k + a, 0): k + b + 1])


# ------------------------------------------------------------------ loading
def load_crsp(folder=CRSP):
    fe = pd.read_csv(folder / "tminus_crsp_firm_events.csv")
    pairs = pd.read_csv(folder / "tminus_crsp_pairs.csv")
    info = json.loads((folder / "tminus_crsp_run_info.json").read_text())
    if info.get("contains_raw_data") is not False:
        raise SystemExit("run_info does not confirm derived-only output; stop.")
    return fe, pairs, info


def crsp_records(fe: pd.DataFrame) -> list[dict]:
    """CRSP rows with a CAR, in the same shape as site/data/firm_events.json."""
    recs = []
    for r in fe[fe["model"].isin(["market_model", "market_adjusted_fallback"])].itertuples():
        exch = "XNYS" if r.ticker in ("ORB", "OA") else "XNAS"
        group = "rival" if r.role == "rival" else f"provider_{r.outcome}"
        recs.append({
            "id": f"{r.launch_tag}|{r.ticker}|{r.role}", "group": group, "launch_tag": r.launch_tag,
            "ticker": r.ticker, "exchange": exch, "firm": FIRM_NAMES[r.ticker], "vehicle": r.lv_type,
            "role": r.role, "tier": r.tier, "outcome": r.outcome, "day0": r.day0_used, "model": r.model,
            "est_obs": int(r.est_obs), "sigma": float(r.sigma), "disclosure_confidence": r.disclosure_confidence,
            "source": "crsp",
            "windows": {w: {"car": None if pd.isna(getattr(r, c)) else float(getattr(r, c)),
                            "var": None if pd.isna(getattr(r, v)) else float(getattr(r, v)),
                            "L": C.EVENT_WINDOWS[w][1] - C.EVENT_WINDOWS[w][0] + 1}
                        for w, (c, v) in WINDOW_KEYS.items()},
        })
    return recs


# ------------------------------------------------------------------ clusters (same rule as step 04)
def recluster(base: list[dict], crsp: list[dict]) -> dict:
    """Launch tag -> cluster id. v1.0 clusters are kept as they are; CRSP failures join by the step 04
    rule (failures that share a firm with day 0s within CLUSTER_GAP_TRADING_DAYS sessions)."""
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        parent[find(a)] = find(b)

    by_cl = {}
    for r in base:
        find(r["launch_tag"])
        by_cl.setdefault(r["cluster"], []).append(r["launch_tag"])
    for tags in by_cl.values():
        for t in tags[1:]:
            union(t, tags[0])
    fails = [r for r in crsp if r["outcome"] == "failure"]
    for tk in {r["ticker"] for r in fails}:
        g = sorted((r for r in fails if r["ticker"] == tk), key=lambda r: r["day0"])
        s = _sessions(g[0]["exchange"])
        pos = [s.get_loc(pd.Timestamp(r["day0"])) for r in g]
        for k in range(len(g)):
            find(g[k]["launch_tag"])
            if k and pos[k] - pos[k - 1] <= C.CLUSTER_GAP_TRADING_DAYS and g[k]["launch_tag"] != g[k - 1]["launch_tag"]:
                union(g[k]["launch_tag"], g[k - 1]["launch_tag"])
    # keep v1.0 cluster numbers; new clusters get numbers after the largest one
    root_to_id = {}
    for cl, tags in by_cl.items():
        root_to_id.setdefault(find(tags[0]), cl)
    nxt = max(by_cl) + 1 if by_cl else 1
    out = {}
    for t in sorted(parent):
        r = find(t)
        if r not in root_to_id:
            root_to_id[r] = nxt
            nxt += 1
        out[t] = root_to_id[r]
    return out


# ------------------------------------------------------------------ correlations
def imputed_resid_corr(base: list[dict], rho: dict) -> float:
    """Mean residual correlation of observed different-firm pairs that share day 0 (overlap = L)."""
    by_id = {r["id"]: r for r in base}
    vals = [p[2] for p in rho["primary"]
            if p[0] in by_id and p[1] in by_id and by_id[p[0]]["ticker"] != by_id[p[1]]["ticker"]
            and by_id[p[0]]["day0"] == by_id[p[1]]["day0"]]
    return float(np.mean(vals)) if vals else 0.0


def combined_rho(recs: list[dict], base_rho: dict, crsp_pairs: pd.DataFrame, r_cross: float) -> dict:
    """rho for every same-cluster pair: v1.0 pairs as published; pairs with a CRSP firm recomputed as
    residual correlation x common window days / L. CRSP-CRSP residual correlations come from the WRDS run;
    pairs mixing a CRSP firm with a v1.0 firm cannot be observed and use r_cross."""
    pc = {}
    for p in crsp_pairs.itertuples():
        pc[(p.key_i, p.key_j)] = pc[(p.key_j, p.key_i)] = float(p.resid_corr)
    out = {}
    for w in C.EVENT_WINDOWS:
        L = C.EVENT_WINDOWS[w][1] - C.EVENT_WINDOWS[w][0] + 1
        known = {(a, b): v for a, b, v in base_rho[w]}
        pairs = []
        for i in range(len(recs)):
            for j in range(i + 1, len(recs)):
                a, b = recs[i], recs[j]
                if a["cluster"] != b["cluster"]:
                    continue
                if a.get("source") != "crsp" and b.get("source") != "crsp":
                    v = known.get((a["id"], b["id"]), known.get((b["id"], a["id"])))
                    if v is not None:
                        pairs.append([a["id"], b["id"], v])
                    continue
                common = len(window_days(a["exchange"], a["day0"], w) & window_days(b["exchange"], b["day0"], w))
                if common == 0:
                    rc = 0.0
                elif a["ticker"] == b["ticker"]:
                    rc = 1.0
                elif a.get("source") == "crsp" and b.get("source") == "crsp":
                    rc = pc.get((a["id"], b["id"]), 0.0)
                else:
                    rc = r_cross
                pairs.append([a["id"], b["id"], rc * common / L])
        out[w] = pairs
    return out


# ------------------------------------------------------------------ tests
def run_tests(recs, rho, draws, label):
    riv = [r for r in recs if r["group"] == "rival" and r["tier"] in H2_TIERS and r["windows"]["primary"]["car"] is not None]
    bmp = {w: bmp_kp_from_records(riv, rho, w) for w in C.EVENT_WINDOWS}
    est = estimand_tests(riv, {"stat": bmp["primary"]["stat"], "p": bmp["primary"]["p"]}, draws=draws)
    return {"label": label, "n": bmp["primary"]["n"], "clusters": bmp["primary"]["clusters"],
            "failures": bmp["primary"]["failures"], "firms": bmp["primary"]["firms"],
            "bmp_kp": bmp, "cluster_robust": est["A"], "firm_level": est["firm"], "contrib": est["contrib"]}


def maker_cases(base, crsp):
    rows = [r for r in base + crsp if r["group"] == "provider_failure" and r["windows"]["primary"]["car"] is not None]
    out = []
    for r in sorted(rows, key=lambda r: r["day0"]):
        w = r["windows"]["primary"]
        z = w["car"] / np.sqrt(w["var"])
        out.append({"launch_tag": r["launch_tag"], "ticker": r["ticker"], "firm": r["firm"], "vehicle": r["vehicle"],
                    "day0": r["day0"], "car": w["car"], "z": float(z), "p": float(2 * stats.norm.sf(abs(z))),
                    "source": r.get("source", "v1.0")})
    cars = np.array([c["car"] for c in out])
    neg = int((cars < 0).sum())
    return {"cases": out, "n": len(out), "firms": len({c["ticker"] for c in out}), "negative": neg,
            "mean": float(cars.mean()), "median": float(np.median(cars)),
            "sign_test_p": float(stats.binomtest(neg, len(out), 0.5).pvalue)}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--draws", type=int, default=9999)
    ap.add_argument("--crsp", type=Path, default=CRSP)
    ap.add_argument("--site-data", type=Path, default=SITE_DATA)
    args = ap.parse_args(argv)

    fe, pairs, info = load_crsp(args.crsp)
    base = json.loads((args.site_data / "firm_events.json").read_text())
    base_rho = json.loads((args.site_data / "rho.json").read_text())
    published = json.loads((args.site_data / "results.json").read_text())["primary"]
    crsp = crsp_records(fe)
    cl = recluster(base, crsp)
    for r in crsp:
        r["cluster"] = cl.get(r["launch_tag"], -1) if r["outcome"] == "failure" else -1
    assert all(cl[r["launch_tag"]] == r["cluster"] for r in base), "v1.0 clusters changed"

    r_cross = imputed_resid_corr(base, base_rho)
    flags = pd.read_csv(C.MANUAL / "crsp_confounded_events.csv", dtype=str, keep_default_na=False)
    v1_flags = pd.read_csv(C.MANUAL / "confounded_events.csv", dtype=str, keep_default_na=False)
    drop = {(f.launch_tag, f.ticker) for f in pd.concat([flags, v1_flags]).itertuples() if f.verdict == "confounded"}

    v10 = run_tests(base, base_rho, args.draws, "v1.0 sample (headline, unchanged)")
    s1_recs = base + crsp
    s1 = run_tests(s1_recs, combined_rho(s1_recs, base_rho, pairs, r_cross), args.draws, "S1: v1.0 + CRSP firms")
    s2_recs = [r for r in s1_recs if (r["launch_tag"], r["ticker"]) not in drop]
    s2 = run_tests(s2_recs, combined_rho(s2_recs, base_rho, pairs, r_cross), args.draws,
                   "S2 (exploratory): S1 without events flagged 'confounded'")
    # robustness runs from the same WRDS download (script v1.2); skipped if the files are absent
    robust = {}
    vw_path, atk_path = args.crsp / "tminus_crsp_firm_events_vwretd.csv", args.crsp / "tminus_crsp_firm_events_oa_atk.csv"
    if vw_path.exists():
        vw = crsp_records(pd.read_csv(vw_path))
        for r in vw:
            r["cluster"] = cl.get(r["launch_tag"], -1) if r["outcome"] == "failure" else -1
        vw_pairs = pd.read_csv(args.crsp / "tminus_crsp_pairs_vwretd.csv")
        recs = base + vw
        robust["vwretd"] = {"rival": run_tests(recs, combined_rho(recs, base_rho, vw_pairs, r_cross), args.draws,
                                               "S1 with CRSP value-weighted benchmark"),
                            "makers": maker_cases(base, vw)}
    if atk_path.exists():
        atk_fe = pd.read_csv(atk_path)
        merged = pd.concat([fe[fe["ticker"] != "OA"], atk_fe], ignore_index=True)
        atk = crsp_records(merged)
        cl_atk = recluster(base, atk)
        for r in atk:
            r["cluster"] = cl_atk.get(r["launch_tag"], -1) if r["outcome"] == "failure" else -1
        atk_pairs = pd.concat([pairs[~pairs["key_i"].str.contains(r"\|OA\|") & ~pairs["key_j"].str.contains(r"\|OA\|")],
                               pd.read_csv(args.crsp / "tminus_crsp_pairs_oa_atk.csv")], ignore_index=True)
        recs = base + atk
        robust["oa_atk"] = {"rival": run_tests(recs, combined_rho(recs, base_rho, atk_pairs, r_cross), args.draws,
                                               "S1 with Orbital ATK estimated on ATK history"),
                            "oa_events_with_car": int(atk_fe["car_primary"].notna().sum()),
                            "oa_events_with_car_main": int(fe[fe["ticker"] == "OA"]["car_primary"].notna().sum())}

    sens = {}
    for v in RHO_SENSITIVITY:
        b = bmp_kp_from_records([r for r in s1_recs if r["group"] == "rival" and r["tier"] in H2_TIERS], combined_rho(s1_recs, base_rho, pairs, v), "primary")
        sens[str(v)] = {"stat": b["stat"], "p": b["p"]}

    # the v1.0 reconstruction must match the published headline exactly
    assert abs(v10["bmp_kp"]["primary"]["stat"] - published["stat"]) < 1e-9, "v1.0 BMP-KP not reproduced"

    new_riv = [r for r in crsp if r["group"] == "rival" and r["tier"] in H2_TIERS and r["windows"]["primary"]["car"] is not None]
    out = {
        "plan_version": "1.2", "status": "supplement: reported next to the v1.0 result, never instead",
        "crsp_run": {k: info[k] for k in ("script_version", "run_utc", "permnos", "crsp_tables", "benchmark")},
        "coverage": {"crsp_events": len(fe), "with_car": int(fe["car_primary"].notna().sum()),
                     "dropped_short_history": int((~fe["model"].isin(["market_model", "market_adjusted_fallback"])).sum()),
                     "new_rival_reactions": len(new_riv),
                     "fallback_model": int((fe["model"] == "market_adjusted_fallback").sum())},
        "imputed_cross_source_corr": r_cross, "rho_sensitivity": sens,
        "dropped_in_S2": sorted(f"{a} {b}" for a, b in drop),
        "rival": {"v1_0": v10, "S1": s1, "S2": s2},
        "makers": maker_cases(base, crsp),
        "robustness": robust,
    }
    C.PROCESSED.mkdir(parents=True, exist_ok=True)
    (C.PROCESSED / "crsp_supplement.json").write_text(json.dumps(out, indent=2, default=float))
    C.REPORTS.mkdir(parents=True, exist_ok=True)
    (C.REPORTS / "10_crsp_supplement.md").write_text(report(out))
    print(report(out))
    return out


def pct(x, d=2):
    return "n/a" if x is None else f"{x * 100:+.{d}f}%"


def report(o):
    L = ["# Step 10: CRSP supplement (plan v1.2)", "",
         "Four delisted US launch firms added from CRSP (derived statistics only, run by a WRDS subscriber). "
         "The v1.0 result is the headline and is unchanged; S1 and S2 are reported next to it.", "",
         f"CRSP run: script {o['crsp_run']['script_version']}, {o['crsp_run']['run_utc']}, PERMNOs "
         + ", ".join(f"{k} {v}" for k, v in o["crsp_run"]["permnos"].items()) + ".", "",
         f"Coverage: {o['coverage']['with_car']} of {o['coverage']['crsp_events']} CRSP events have a CAR; "
         f"{o['coverage']['dropped_short_history']} dropped (fewer than 30 estimation returns); "
         f"{o['coverage']['new_rival_reactions']} new rival reactions enter H2.", "",
         "## Rival test (H2), window [0,+1]", "",
         "| Sample | Reactions | Clusters | Firms | Mean CAR | 95% CI | cluster-robust p | wild bootstrap p | BMP-KP t | BMP-KP p |",
         "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"]
    for k in ("v1_0", "S1", "S2"):
        s = o["rival"][k]
        b, a = s["bmp_kp"]["primary"], s["cluster_robust"]
        L.append(f"| {s['label']} | {s['n']} | {s['clusters']} | {s['firms']} | {pct(b['mean'])} | "
                 f"{pct(b['ci_low'])} to {pct(b['ci_high'])} | {a['p']:.3f} | {a['p_wild']:.3f} | {b['stat']:.3f} | {b['p']:.3f} |")
    L += ["", "Other windows (BMP-KP p): " + "; ".join(
        f"{k} {w} {o['rival'][k]['bmp_kp'][w]['p']:.3f}" for k in ("S1", "S2") for w in ("robust", "descriptive")), "",
          f"Firm level (S1): {o['rival']['S1']['firm_level']['k']} firms, mean of firm means "
          f"{pct(o['rival']['S1']['firm_level']['mean'])}, 95% CI {pct(o['rival']['S1']['firm_level']['ci'][0])} to "
          f"{pct(o['rival']['S1']['firm_level']['ci'][1])}.", "",
          f"Cross-source residual correlation (a CRSP firm and a v1.0 firm in one cluster) is not observable; it is set to "
          f"{o['imputed_cross_source_corr']:.3f}, the mean of observed different-firm pairs with the same day 0. "
          "BMP-KP p for S1 with other values: " + ", ".join(f"{k}: {v['p']:.3f}" for k, v in o["rho_sensitivity"].items()) + ".", "",
          "Dropped in S2: " + ", ".join(o["dropped_in_S2"]) + ".", ""]
    if o.get("robustness"):
        L += ["## Robustness of S1", "", "| Run | Reactions | Clusters | Mean CAR | 95% CI | cluster-robust p | BMP-KP p |",
              "| --- | --- | --- | --- | --- | --- | --- |"]
        s1 = o["rival"]["S1"]
        for s in [s1] + [v["rival"] for v in o["robustness"].values()]:
            b = s["bmp_kp"]["primary"]
            L.append(f"| {s['label']} | {s['n']} | {s['clusters']} | {pct(b['mean'])} | {pct(b['ci_low'])} to {pct(b['ci_high'])} | "
                     f"{s['cluster_robust']['p']:.3f} | {b['p']:.3f} |")
        if "vwretd" in o["robustness"]:
            mv = o["robustness"]["vwretd"]["makers"]
            L += ["", f"Maker failures with the value-weighted benchmark: {mv['negative']} of {mv['n']} negative, mean {pct(mv['mean'])}."]
        if "oa_atk" in o["robustness"]:
            a = o["robustness"]["oa_atk"]
            L += ["", f"Orbital ATK events with a CAR: {a['oa_events_with_car_main']} (main rule) and {a['oa_events_with_car']} (with ATK history)."]
        L += [""]
    L += [
          "## Maker failures (case series)", "",
          "| Day 0 | Firm | Vehicle | CAR [0,+1] | z | Source |", "| --- | --- | --- | --- | --- | --- |"]
    for c in o["makers"]["cases"]:
        L.append(f"| {c['day0']} | {c['ticker']} | {c['vehicle']} | {pct(c['car'])} | {c['z']:.2f} | {c['source']} |")
    m = o["makers"]
    L += ["", f"{m['negative']} of {m['n']} negative ({m['firms']} firms); mean {pct(m['mean'])}, median {pct(m['median'])}; "
              f"exact sign test p = {m['sign_test_p']:.4f} (descriptive: cases are few and not independent draws).", "",
          "## Caveats", "",
          "- S2 is exploratory. The VORB flag (2023-F04) was found after the CRSP CARs were seen, by checking the largest "
          "new reaction. The same news check has not yet been done for every new reaction, so S2 may be tilted.",
          "- CRSP returns (RET, with delisting returns) and Yahoo adjusted closes are different sources; the S&P 500 "
          "benchmark is the same index in both.",
          "- 2001-U01 ORB (maker case) is flagged possibly confounded: the first week of US trading after 11 Sep 2001.",
          "- 2017-051 OA: the Northrop Grumman takeover (announced 18 Sep 2017, day +11) lies inside the [0,+20] window only. "
          "After it, OA traded close to the cash offer, so OA events from late 2017 on (tier 3 and successes, none in H2) carry no information.",
          "- The ATK-history run uses Alliant Techsystems returns, a defence and ammunition firm, to estimate Orbital ATK's model: "
          "a sensitivity check, not a better estimate.", ""]
    return "\n".join(L)


if __name__ == "__main__":
    main()
