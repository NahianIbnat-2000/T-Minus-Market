"""Step 05: run the event study exactly as docs/ANALYSIS_PLAN.md (v1.0) specifies.

Reads:  data/interim/coverage.csv, data/interim/returns.parquet,
        data/interim/orbital_launches.csv, data/manual/firm_map.csv
Writes: data/processed/firm_event_cars.csv  (one row per firm-event, all windows)
        data/processed/results.json          (every number the report, paper and site use)
        reports/05_results.md                (human-readable summary)

Usage:  python pipeline/05_event_study.py            # full run, 1,000 placebo draws
        python pipeline/05_event_study.py --quick    # 100 placebo draws (for testing)
"""
import argparse
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

import config as C
from analysis import case_series, exploratory, placebo, rival_robustness, PRIMARY, ROBUST, LONG
from eventstudy import bmp_kp_test, build_firm_event, car

PLAN_VERSION = "1.0"


def load():
    cov = pd.read_csv(C.INTERIM / "coverage.csv", dtype={"cluster": "float"}, keep_default_na=False,
                      na_values=[""])
    cov = cov[cov["usable"].astype(str) == "True"].copy()
    cov["day0"] = pd.to_datetime(cov["day0"])
    if "listing_start" in cov.columns:
        cov["listing_start"] = pd.to_datetime(cov["listing_start"], errors="coerce")
    rets = pd.read_parquet(C.INTERIM / "returns.parquet")
    rets["date"] = pd.to_datetime(rets["date"]).dt.tz_localize(None)
    returns_by = {t: g[["date", "ticker", "ret"]] for t, g in rets.groupby("ticker")}
    benches = {ex: returns_by[b][["date", "ret"]] for ex, b in C.BENCHMARKS.items() if b in returns_by}
    orbital = pd.read_csv(C.INTERIM / "orbital_launches.csv", parse_dates=["launch_utc"])
    return cov, returns_by, benches, orbital


def first_flight_flags(orbital: pd.DataFrame) -> dict:
    """True if a failure was the first orbital launch of that exact vehicle version (GCAT LV_Type)."""
    o = orbital.sort_values("launch_utc")
    first_tags = set(o.drop_duplicates("LV_Type", keep="first")["Launch_Tag"])
    return {t: t in first_tags for t in o.loc[o["outcome"] == "failure", "Launch_Tag"]}


def build(rows, returns_by, benches):
    out = []
    for _, r in rows.iterrows():
        if r["ticker"] not in returns_by or r["exchange"] not in benches:
            continue
        fe = build_firm_event(r, returns_by[r["ticker"]], benches[r["exchange"]])
        if fe is not None:
            out.append(fe)
    return out


def fe_table(fes, group):
    recs = []
    for fe in fes:
        rec = {"group": group, "launch_tag": fe.launch_tag, "ticker": fe.ticker, "tier": fe.tier,
               "cluster": fe.cluster, "day0": fe.day0.date(), "model": fe.model, "est_obs": len(fe.est_r),
               "alpha": fe.alpha, "beta": fe.beta, "sigma": fe.sigma,
               "disclosure_confidence": fe.meta.get("disclosure_confidence"), "vehicle": fe.meta.get("lv_type")}
        for nm, w in [("primary", PRIMARY), ("robust", ROBUST), ("long", LONG)]:
            c, v, _ = car(fe, w)
            rec[f"car_{nm}"] = c
            rec[f"car_{nm}_se"] = np.sqrt(v) if np.isfinite(v) else np.nan
        recs.append(rec)
    return pd.DataFrame(recs)


def pct(x, d=2):
    return "n/a" if x is None or not np.isfinite(x) else f"{100 * x:+.{d}f}%"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    args = ap.parse_args()
    draws = 100 if args.quick else 1000

    cov, returns_by, benches, orbital = load()
    bench_for = lambda ex: benches[ex]
    fail = cov[cov["outcome"] == "failure"]
    rival_rows = fail[(fail["role"] == "rival") & fail["tier"].isin(["tier1", "tier2"])]
    prov_rows = fail[(fail["role"] == "provider") & (fail["tier"] == "provider")]
    succ_rows = cov[(cov["role"] == "provider") & (cov["tier"] == "provider") & (cov["outcome"] != "failure")]

    rival = build(rival_rows, returns_by, benches)
    prov = build(prov_rows, returns_by, benches)
    succ = build(succ_rows, returns_by, benches)
    print(f"Firm-events built: rivals {len(rival)}, provider failures {len(prov)}, provider successes {len(succ)}")

    # ---------------- primary (H2)
    main_res = bmp_kp_test(rival, PRIMARY, name="H2 primary: BMP with Kolari-Pynnonen cluster adjustment")
    print(f"H2 mean rival CAR[0,+1] = {pct(main_res.mean_car)}  p = {main_res.p:.4f}")

    # ---------------- robustness
    robust = rival_robustness(rival, rival_rows, returns_by, bench_for)
    print("Running placebo benchmark ...")
    f_day0 = {t: list(g["day0"]) for t, g in fail.groupby("ticker")}
    plc = placebo(rival, rival_rows, returns_by, bench_for, f_day0, n_draws=draws)

    # ---------------- providers and exploratory
    cases = case_series(prov)
    expl = exploratory(rival, prov, succ, first_flight_flags(orbital))

    # ---------------- outputs
    C.PROCESSED.mkdir(parents=True, exist_ok=True)
    pd.concat([fe_table(rival, "rival"), fe_table(prov, "provider_failure"), fe_table(succ, "provider_success")]) \
        .to_csv(C.PROCESSED / "firm_event_cars.csv", index=False)
    results = {
        "plan_version": PLAN_VERSION, "run_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "settings": {"estimation_window": C.EST_WINDOW, "windows": C.EVENT_WINDOWS, "returns": C.RETURN_TYPE,
                     "min_obs": C.EST_MIN_OBS, "cluster_gap": C.CLUSTER_GAP_TRADING_DAYS, "seed": C.RANDOM_SEED},
        "primary": main_res.as_dict(),
        "robustness": [r.as_dict() for r in robust],
        "placebo": plc,
        "provider_case_series": cases,
        "exploratory": expl,
    }
    (C.PROCESSED / "results.json").write_text(json.dumps(results, indent=2, default=str))
    write_report(main_res, robust, plc, cases, expl, draws)
    print("Wrote reports/05_results.md, data/processed/results.json, data/processed/firm_event_cars.csv")


def write_report(m, robust, plc, cases, expl, draws):
    verdict = ("detectable at the 5% level" if m.p < 0.05 else
               "not detectable at the 5% level at this sample size (this is not evidence of no effect)")
    L = [f"# Step 05: Event study results (analysis plan v{PLAN_VERSION})", "",
         "## Primary result (H2, confirmatory)", "",
         "When a rival's small rocket fails, the mean two-day abnormal return of listed small-launch firms "
         f"(CAR[0,+1]) is **{pct(m.mean_car)}** (95% CI {pct(m.ci_low)} to {pct(m.ci_high)}), {verdict}.", "",
         "| Statistic | Value |", "| --- | --- |",
         f"| Mean CAR[0,+1] | {pct(m.mean_car)} |",
         f"| 95% CI (cluster-robust) | {pct(m.ci_low)} to {pct(m.ci_high)} |",
         f"| Adjusted BMP t | {m.stat:.3f} |", f"| p-value (two-sided) | {m.p:.4f} |",
         f"| Failures / firms / firm-events / clusters | {m.n_failures} / {m.n_firms} / {m.n_firm_events} / {m.n_clusters} |",
         f"| Mean within-cluster CAR correlation | {m.mean_within_cluster_corr:.3f} |",
         f"| Notes | {m.note} |", "",
         "Returns are simple daily returns; market model on [-250, -30]; local index benchmark.", "",
         "## Robustness (all prespecified, all reported)", "",
         "| Check | Mean CAR | 95% CI | Statistic | p | Firm-events | Clusters | Note |",
         "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in robust:
        ci = "n/a" if r.ci_low is None or not np.isfinite(r.ci_low) else f"{pct(r.ci_low)} to {pct(r.ci_high)}"
        stat = "n/a" if r.stat is None or not np.isfinite(r.stat) else f"{r.stat:.3f}"
        p = "n/a" if r.p is None or not np.isfinite(r.p) else f"{r.p:.4f}"
        L.append(f"| {r.name} | {pct(r.mean_car)} | {ci} | {stat} | {p} | {r.n_firm_events} | {r.n_clusters} | {r.note} |")
    L += ["", "## R9 Placebo benchmark", "",
          f"{plc['draws']} draws (seed {plc['seed']}). Real mean CAR[0,+1] = {pct(plc['actual_mean_car'])}; "
          f"placebo middle 95% = {pct(plc['placebo_2.5pct'])} to {pct(plc['placebo_97.5pct'])}; "
          f"real value sits at the {plc['actual_percentile']:.1f}th percentile "
          f"(two-sided share {plc['two_sided_share']:.3f}, Monte Carlo s.e. {plc['monte_carlo_se']:.3f}). "
          f"Eligible pseudo-dates per firm-event: min {plc['eligible_dates_min']}, median {plc['eligible_dates_median']}. "
          "This is a benchmark for context, not an exact permutation test.", "",
          "## Provider failures (case series, not a pooled test)", "",
          "| Failure | Firm | Day 0 | CAR[0,+1] | 95% interval | CAR[-1,+3] | Model |", "| --- | --- | --- | --- | --- | --- | --- |"]
    for c in cases:
        ci = "n/a" if not c["car_primary_ci"] else f"{pct(c['car_primary_ci'][0])} to {pct(c['car_primary_ci'][1])}"
        L.append(f"| {c['launch_tag']} {c['vehicle']} | {c['firm']} ({c['ticker']}) | {c['day0']} | "
                 f"{pct(c['car_primary'])} | {ci} | {pct(c['car_robust'])} | {c['model']} |")
    L += ["", "## Exploratory (not confirmatory; Holm-adjusted p across this family)", "",
          "| ID | Question | Estimate | n | p (raw) | p (Holm) |", "| --- | --- | --- | --- | --- | --- |"]
    for e in expl:
        L.append(f"| {e['id']} | {e['label']} | {pct(e['estimate'])} | {e['n']} | {e['p_raw']:.4f} | {e['p_holm']:.4f} |")
    if draws < 1000:
        L += ["", f"**Quick run: placebo used {draws} draws. Rerun without --quick for the reported results.**"]
    (C.REPORTS / "05_results.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
