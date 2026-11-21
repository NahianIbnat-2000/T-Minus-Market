"""Step 01: download GCAT and build the failure list.

Usage:
    python pipeline/01_ingest_launches.py            # download fresh copy
    python pipeline/01_ingest_launches.py --offline  # use data/raw/launch.tsv as is
"""
import argparse
import json

import config as C
from gcat import read_launch_tsv
from ingest import classify, download, manifest_entry, summary_markdown


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="use the existing local file")
    args = ap.parse_args()

    if args.offline:
        if not C.GCAT_LOCAL_FILE.exists():
            raise SystemExit(f"--offline given but {C.GCAT_LOCAL_FILE} does not exist")
        manifest = manifest_entry(C.GCAT_LAUNCH_URL, C.GCAT_LOCAL_FILE)
        manifest["note"] = "offline: retrieved_utc is when the checksum was taken, not the download time"
    else:
        print(f"Downloading {C.GCAT_LAUNCH_URL} ...")
        manifest = download(C.GCAT_LAUNCH_URL, C.GCAT_LOCAL_FILE)

    raw = read_launch_tsv(C.GCAT_LOCAL_FILE)
    orbital, failures, ground, excl, funnel = classify(raw)

    C.INTERIM.mkdir(parents=True, exist_ok=True)
    C.REPORTS.mkdir(parents=True, exist_ok=True)
    orbital.to_csv(C.INTERIM / "orbital_launches.csv", index=False)
    failures.to_csv(C.INTERIM / "failures.csv", index=False)
    ground.to_csv(C.INTERIM / "ground_anomalies.csv", index=False)
    excl.to_csv(C.INTERIM / "exclusion_log_01.csv", index=False)
    (C.RAW / "manifest_gcat.json").write_text(json.dumps(manifest, indent=2))
    (C.REPORTS / "01_ingest_summary.md").write_text(summary_markdown(orbital, failures, ground, excl, funnel, manifest))

    for k, v in funnel:
        print(f"{v:>7}  {k}")
    src = orbital["launch_time_source"].value_counts().to_dict()
    print(f"Launch times taken from: {src}  (Launch_Date = exact minute; Launch_JD = rounded fallback)")
    print(f"Wrote reports/01_ingest_summary.md and data/interim/*.csv")


if __name__ == "__main__":
    main()
