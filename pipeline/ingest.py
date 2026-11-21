"""Step 01 logic: download GCAT, classify orbital launches since 2000."""
from __future__ import annotations

import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import config as C
from gcat import jd_to_utc, parse_launch_code, read_launch_tsv, validate_schema, vague_date_to_utc


def download(url: str, dest: Path) -> dict:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "t-minus-markets research pipeline"})
    with urllib.request.urlopen(req, timeout=120) as r:
        data = r.read()
    dest.write_bytes(data)
    return manifest_entry(url, dest)


def manifest_entry(url: str, path: Path) -> dict:
    data = Path(path).read_bytes()
    return {
        "source_url": url,
        "local_file": str(Path(path).relative_to(C.ROOT)) if Path(path).is_relative_to(C.ROOT) else str(path),
        "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "citation": C.GCAT_CITATION,
    }


def classify(raw: pd.DataFrame, start: str = C.START_DATE):
    """Return (orbital, failures, ground, exclusions, funnel)."""
    missing = validate_schema(raw)
    if missing:
        raise ValueError(f"GCAT file is missing columns: {missing}")

    df = raw.copy()
    parsed = df["LaunchCode"].apply(parse_launch_code).apply(pd.Series)
    df = pd.concat([df, parsed], axis=1)
    # Launch_Date carries the minute; Launch_JD can be rounded. Prefer Launch_Date, fall back to JD.
    exact = df["Launch_Date"].apply(vague_date_to_utc)
    df["launch_time_source"] = exact.notna().map({True: "Launch_Date", False: "Launch_JD"})
    df["launch_utc"] = exact.where(exact.notna(), df["Launch_JD"].apply(jd_to_utc))

    funnel = [("all rows in GCAT launch list", len(df))]
    exclusions = []

    bad_time = df["launch_utc"].isna()
    for _, r in df[bad_time].iterrows():
        exclusions.append((r["Launch_Tag"], r["LV_Type"], "unparseable_launch_jd", r["Launch_JD"]))
    df = df[~bad_time]

    df = df[df["launch_utc"] >= pd.Timestamp(start, tz="UTC")]
    funnel.append((f"launches on or after {start}", len(df)))

    bad_code = ~df["code_ok"].astype(bool)
    for _, r in df[bad_code].iterrows():
        exclusions.append((r["Launch_Tag"], r["LV_Type"], "unparseable_launch_code", r["LaunchCode"]))
    df = df[~bad_code]

    df = df[df["category"].isin(C.ORBITAL_CATEGORIES)]
    funnel.append(("orbital or deep-space launch category (O, D)", len(df)))

    dup = df["Launch_Tag"].duplicated(keep=False)
    if dup.any():
        for _, r in df[dup].iterrows():
            exclusions.append((r["Launch_Tag"], r["LV_Type"], "duplicate_launch_tag_kept_first", r["LaunchCode"]))
        df = df.drop_duplicates("Launch_Tag", keep="first")
    funnel.append(("unique launch tags", len(df)))

    ground = df[df["result"].isin(C.GROUND_ANOMALY_LETTERS)].copy()
    df = df[~df["result"].isin(C.GROUND_ANOMALY_LETTERS)]

    unknown = df["score"].isna()
    for _, r in df[unknown].iterrows():
        reason = {"U": "outcome_unknown", "Z": "not_a_launch", "A": "pad_abort"}.get(r["result"], "no_success_score")
        exclusions.append((r["Launch_Tag"], r["LV_Type"], reason, r["LaunchCode"]))
    df = df[~unknown]
    funnel.append(("orbital launches with a known outcome", len(df)))

    df["outcome"] = "success"
    df.loc[df["score"] < 1.0, "outcome"] = "partial_success"
    df.loc[df["score"] < C.FAILURE_THRESHOLD, "outcome"] = "failure"

    keep = ["Launch_Tag", "launch_utc", "launch_time_source", "Launch_Date", "LV_Type", "LV_Variant", "Launch_Agency",
            "Launch_Site", "LaunchCode", "score", "outcome", "FailCode", "Flight_ID", "Mission", "LTCite"]
    keep = [k for k in keep if k in df.columns]
    orbital = df[keep].sort_values("launch_utc").reset_index(drop=True)
    failures = orbital[orbital["outcome"] == "failure"].reset_index(drop=True)
    funnel.append((f"failures (score below {C.FAILURE_THRESHOLD})", len(failures)))

    ground_keep = [k for k in keep if k in ground.columns and k not in ("score", "outcome")]
    ground = ground[ground_keep].sort_values("launch_utc").reset_index(drop=True)

    excl = pd.DataFrame(exclusions, columns=["launch_tag", "lv_type", "reason", "detail"])
    return orbital, failures, ground, excl, funnel


def summary_markdown(orbital, failures, ground, excl, funnel, manifest) -> str:
    f = failures.copy()
    f["year"] = f["launch_utc"].dt.year
    lines = ["# Step 01: GCAT ingest summary", "",
             f"Source: {manifest.get('source_url')}  ",
             f"Retrieved: {manifest.get('retrieved_utc')}  ",
             f"SHA-256: `{manifest.get('sha256')}`", "",
             "## Sample funnel", "", "| Step | Count |", "| --- | --- |"]
    lines += [f"| {k} | {v} |" for k, v in funnel]
    lines += ["", f"Partial successes kept as successes (score 0.75 to 0.99): "
              f"{(orbital['outcome'] == 'partial_success').sum()}",
              f"Ground anomalies (pad explosions, separate set): {len(ground)}",
              f"Rows in exclusion log: {len(excl)}", ""]
    for title, col in [("Failures by year", "year"), ("Failures by vehicle", "LV_Type"),
                       ("Failures by launch agency", "Launch_Agency")]:
        if col not in f.columns:
            continue
        counts = f[col].value_counts().sort_index() if col == "year" else f[col].value_counts()
        lines += [f"## {title}", "", "| Value | Failures |", "| --- | --- |"]
        lines += [f"| {k} | {v} |" for k, v in counts.items()]
        lines.append("")
    return "\n".join(lines)
