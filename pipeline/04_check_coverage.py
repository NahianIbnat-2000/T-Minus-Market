"""Step 04: coverage, clusters, power and the feasibility gate.

Writes reports/04_feasibility_report.md. Reads no event-window returns.
"""
import numpy as np
import pandas as pd

import config as C
from coverage import assign_clusters, check_one, load_disclosures, mde


def main():
    events = pd.read_csv(C.INTERIM / "firm_events.csv", dtype=str, keep_default_na=False)
    events["launch_utc"] = pd.to_datetime(events["launch_utc"], utc=True)
    rets = pd.read_parquet(C.INTERIM / "returns.parquet")
    rets["date"] = pd.to_datetime(rets["date"]).dt.tz_localize(None)

    fm = pd.read_csv(C.MANUAL / "firm_map.csv", dtype=str, keep_default_na=False)
    events = events.merge(fm[["map_id", "listing_start"]], on="map_id", how="left")
    events["listing_start"] = pd.to_datetime(events["listing_start"].replace("", pd.NA), errors="coerce")

    disc = load_disclosures(C.MANUAL / "disclosure_times.csv", events)
    events = events.merge(disc[["launch_tag", "disclosure_utc", "disclosure_source", "disclosure_confidence"]],
                          on="launch_tag", how="left")

    checks = []
    for _, ev in events.iterrows():
        bench = C.BENCHMARKS.get(ev["exchange"])
        b = rets[rets["ticker"] == bench][["date", "ret"]] if bench else pd.DataFrame(columns=["date", "ret"])
        checks.append(check_one(ev, rets, b))
    cov = pd.concat([events.reset_index(drop=True), pd.DataFrame(checks)], axis=1)
    cov["usable"] = cov["coverage_reason"].isna()
    cov.to_csv(C.INTERIM / "coverage.csv", index=False)

    fail = cov[cov["outcome"] == "failure"]
    usable_fail = fail[fail["usable"]].copy()
    if not usable_fail.empty:
        usable_fail["cluster"] = assign_clusters(usable_fail)
        cov = cov.merge(usable_fail[["launch_tag", "ticker", "role", "cluster"]],
                        on=["launch_tag", "ticker", "role"], how="left")
        cov.to_csv(C.INTERIM / "coverage.csv", index=False)

    write_report(cov, usable_fail)


def _group_stats(df):
    if df.empty:
        return 0, 0, np.nan
    return df["launch_tag"].nunique(), df["cluster"].nunique(), float(df["sigma"].median())


def write_report(cov, uf):
    prov = uf[(uf["role"] == "provider") & (uf["tier"] == "provider")] if not uf.empty else uf
    riv1 = uf[(uf["role"] == "rival") & (uf["tier"].isin(["tier1", "tier2"]))] if not uf.empty else uf
    riv3 = uf[(uf["role"] == "rival") & (uf["tier"] == "tier3")] if not uf.empty else uf
    succ = cov[(cov["role"] == "provider") & (cov["tier"] == "provider")
               & (cov["outcome"] != "failure") & cov["usable"]]

    n_p, k_p, s_p = _group_stats(prov)
    n_r, k_r, s_r = _group_stats(riv1)
    n_3, k_3, s_3 = _group_stats(riv3)
    mde_p, mde_r = mde(s_p, k_p), mde(s_r, k_r)

    gate_a = k_p >= C.GATE_MIN_PROVIDER_CLUSTERS and np.isfinite(mde_p) and mde_p <= C.GATE_MAX_PROVIDER_MDE
    gate_b = k_r >= C.GATE_MIN_RIVAL_EVENTS
    main_rows = uf[uf["tier"].isin(["provider", "tier1", "tier2"])] if not uf.empty else uf
    unverified = int((main_rows["verification_status"] != "verified").sum()) if not main_rows.empty else 0
    unverified_t3 = int((uf["verification_status"] != "verified").sum()) - unverified if not uf.empty else 0
    main = uf[uf["tier"].isin(["provider", "tier1", "tier2"])] if not uf.empty else uf
    open_timing = main[(main["disclosure_confidence"] == "provisional") & main["timing_sensitive"].astype(bool)] \
        if not main.empty else main
    provisional = len(open_timing)

    pct = lambda x: "n/a" if not np.isfinite(x) else f"{100 * x:.1f}%"
    L = ["# Step 04: Feasibility report", "",
         "This report uses estimation-window volatility only. No event-window abnormal return has been computed.", "",
         "## Gate decision", "",
         f"- (a) Provider test: >= {C.GATE_MIN_PROVIDER_CLUSTERS} independent failures AND MDE for CAR[0,+1] <= {pct(C.GATE_MAX_PROVIDER_MDE)}: "
         f"**{'PASS' if gate_a else 'FAIL'}** ({k_p} failures, MDE = {pct(mde_p)})",
         f"- (b) Independent failure clusters with a Tier 1/2 rival >= {C.GATE_MIN_RIVAL_EVENTS}: **{'PASS' if gate_b else 'FAIL'}** ({k_r})",
         f"- Overall: **{'PASS: confirmatory tests for providers and rivals' if gate_a and gate_b else ('PARTIAL: confirmatory rival test; providers as case series' if gate_b else 'FAIL: case-series format')}**", "",
         f"Not final while provider/Tier 1-2 firm-events use unverified firm-map rows ({unverified}) "
         f"or timing-sensitive events lack a sourced disclosure time ({provisional}).  ",
         f"Status: **{'FINAL for the current sample' if unverified == 0 and provisional == 0 else 'NOT FINAL'}**. "
         f"(Tier 3 descriptive firm-events on unverified rows: {unverified_t3}; these do not enter any test.)", "",
         "Timing-sensitive = day 0 would change if the disclosure came "
         f"{C.TIMING_EARLY_MIN} min earlier or up to {C.TIMING_LATE_MIN} min later than recorded.", ""]
    if provisional:
        L += ["| Launch | Ticker | Recorded time (UTC) |", "| --- | --- | --- |"]
        L += [f"| {r.launch_tag} | {r.ticker} | {str(r.disclosure_utc)[:16]} |" for r in open_timing.itertuples()]
    L += ["",
         "## Usable sample", "",
         "| Group | Failures | Independent clusters | Firm-events | Median daily AR std. dev. | MDE CAR[0,+1] |",
         "| --- | --- | --- | --- | --- | --- |",
         f"| Providers (pure-play or major exposure) | {n_p} | {k_p} | {len(prov)} | {pct(s_p)} | {pct(mde_p)} |",
         f"| Rivals Tier 1-2 | {n_r} | {k_r} | {len(riv1)} | {pct(s_r)} | {pct(mde_r)} |",
         f"| Rivals Tier 3 (descriptive) | {n_3} | {k_3} | {len(riv3)} | {pct(s_3)} | {pct(mde(s_3, k_3))} |",
         f"| Provider successes (comparison group) | n/a | n/a | {len(succ)} | {pct(float(succ['sigma'].median()) if len(succ) else np.nan)} | n/a |",
         "", "MDE: 5% two-sided, 80% power, t critical values, independent clusters, no event-induced variance (a lower bound).", "",
         "## Firm-events dropped at the coverage step", "", "| Reason | Firm-events |", "| --- | --- |"]
    dropped = cov[~cov["usable"]]["coverage_reason"].value_counts()
    L += [f"| {k} | {v} |" for k, v in dropped.items()] or ["| none | 0 |"]
    L += ["", "## Usable failure firm-events by firm", "", "| Firm | Ticker | Role/tier | Events | Model |", "| --- | --- | --- | --- | --- |"]
    if not uf.empty:
        g = uf.groupby(["firm_name", "ticker", "tier", "model"]).size().reset_index(name="n")
        L += [f"| {r.firm_name} | {r.ticker} | {r.tier} | {r.n} | {r.model} |" for r in g.itertuples()]
    L += ["", "## Usable failures by year", "", "| Year | Failures with any usable firm |", "| --- | --- |"]
    if not uf.empty:
        y = uf.drop_duplicates("launch_tag")["launch_utc"].dt.year.value_counts().sort_index()
        L += [f"| {k} | {v} |" for k, v in y.items()]
    (C.REPORTS / "04_feasibility_report.md").write_text("\n".join(L) + "\n")
    print("\n".join(L[:12]))


if __name__ == "__main__":
    main()
