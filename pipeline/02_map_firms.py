"""Step 02: link launches to listed firms (point in time) and assign rival tiers.

Inputs (hand-verified research files):
    data/manual/firm_map.csv
    data/manual/vehicle_segments.csv
    data/manual/rival_overrides.csv   (optional, Tier 2 with sources)
"""
import pandas as pd

import config as C
from mapping import build_firm_events, load_firm_map


def main():
    orbital = pd.read_csv(C.INTERIM / "orbital_launches.csv", dtype=str, keep_default_na=False)
    orbital["launch_utc"] = pd.to_datetime(orbital["launch_utc"], utc=True)
    failures = orbital[orbital["outcome"] == "failure"].copy()

    fm = load_firm_map(C.MANUAL / "firm_map.csv")
    segments = pd.read_csv(C.MANUAL / "vehicle_segments.csv", dtype=str, keep_default_na=False)
    ov_path = C.MANUAL / "rival_overrides.csv"
    overrides = pd.read_csv(ov_path, dtype=str, keep_default_na=False) if ov_path.exists() else None

    events, excl = build_firm_events(orbital, failures, fm, segments, overrides)
    events.to_csv(C.INTERIM / "firm_events.csv", index=False)
    excl.to_csv(C.INTERIM / "exclusion_log_02.csv", index=False)

    write_summary(events, excl, failures)
    f = events[events["outcome"] == "failure"] if not events.empty else events
    print(f"Failures in sample:                 {len(failures)}")
    print(f"Failures with a listed provider:    {f[f['role'] == 'provider']['launch_tag'].nunique() if len(f) else 0}")
    print(f"Failures with a Tier 1 rival:       {f[f['tier'] == 'tier1']['launch_tag'].nunique() if len(f) else 0}")
    print(f"Provider success events (C5):       {len(events[(events['role'] == 'provider') & (events['outcome'] != 'failure')]) if len(events) else 0}")
    print(f"Unverified firm-map rows in use:    {(events['verification_status'] != 'verified').sum() if len(events) else 0}")


def write_summary(events, excl, failures):
    L = ["# Step 02: Mapping summary", "",
         "All counts use the firm map as it stands, including unverified rows.", ""]
    if events.empty:
        L.append("No firm-events.")
    else:
        f = events[events["outcome"] == "failure"]
        L += ["## Failure firm-events by role and tier", "", "| Role | Tier | Failures | Firm-events |", "| --- | --- | --- | --- |"]
        for (r, t), g in f.groupby(["role", "tier"]):
            L.append(f"| {r} | {t} | {g['launch_tag'].nunique()} | {len(g)} |")
        L += ["", "## Failures with a Tier 1 rival", "", "| Launch | Date | Vehicle | Tier 1 rivals |", "| --- | --- | --- | --- |"]
        t1 = f[f["tier"] == "tier1"].groupby(["launch_tag", "lv_type"]).agg(
            date=("launch_utc", "min"), rivals=("ticker", lambda x: ", ".join(sorted(set(x))))).reset_index()
        for r in t1.sort_values("date").itertuples():
            L.append(f"| {r.launch_tag} | {str(r.date)[:10]} | {r.lv_type} | {r.rivals} |")
        L += ["", "## Failures with a listed provider", "", "| Launch | Date | Vehicle | Provider | Tier |", "| --- | --- | --- | --- | --- |"]
        pv = f[f["role"] == "provider"].sort_values("launch_utc")
        for r in pv.itertuples():
            L.append(f"| {r.launch_tag} | {str(r.launch_utc)[:10]} | {r.lv_type} | {r.firm_name} ({r.ticker}) | {r.tier} |")
    L += ["", "## Failures not linked to any listed provider, by vehicle", "", "| Vehicle | Reason | Failures |", "| --- | --- | --- |"]
    if not excl.empty:
        for (v, why), g in excl.groupby(["lv_type", "reason"]):
            L.append(f"| {v} | {why} | {len(g)} |")
    (C.REPORTS / "02_mapping_summary.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
