"""Step 07: export the data the website reads, into site/data/.

Writes (all derived statistics; no raw prices or returns):
  site/data/manifest.json      plan version, run time, sources, licence notes, parity tolerances
  site/data/failures.json      all failures since 2000, for the Failure Timeline
  site/data/firm_events.json   rival and provider firm-events: CARs and variances per window,
                               abnormal-return paths T-5..T+20, flags
  site/data/rho.json           same-cluster CAR correlations per window (for the live test)
  site/data/results.json       every reported result (copy of data/processed/results.json)
"""
import importlib.util
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

import config as C
from siteexport import rho_pairs, to_record

SITE_DATA = C.ROOT / "site" / "data"
TOLERANCES = {"car_and_ci_abs": 1e-9, "t_stat_abs": 1e-8, "p_value_abs": 1e-8,
              "units": "CARs are fractions (0.01 = 1%); tolerance applies to the raw numbers"}


def _step05():
    spec = importlib.util.spec_from_file_location("step05", Path(__file__).with_name("05_event_study.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_flags():
    p = C.MANUAL / "confounded_events.csv"
    if not p.exists():
        return {}
    f = pd.read_csv(p, dtype=str, keep_default_na=False)
    return {(r.launch_tag, r.ticker): {"verdict": r.verdict, "reason": r.reason, "source": r.source_url}
            for r in f.itertuples()}


def failures_table(cov: pd.DataFrame) -> list[dict]:
    orb = pd.read_csv(C.INTERIM / "orbital_launches.csv", dtype=str, keep_default_na=False)
    fail = orb[orb["outcome"] == "failure"].copy()
    fe = pd.read_csv(C.INTERIM / "firm_events.csv", dtype=str, keep_default_na=False) \
        if (C.INTERIM / "firm_events.csv").exists() else pd.DataFrame()
    usable = cov[cov["outcome"] == "failure"]
    excl = pd.read_csv(C.INTERIM / "exclusion_log_02.csv", dtype=str, keep_default_na=False) \
        if (C.INTERIM / "exclusion_log_02.csv").exists() else pd.DataFrame(columns=["launch_tag", "reason"])
    out = []
    for r in fail.to_dict("records"):
        tag = r["Launch_Tag"]
        u = usable[usable["launch_tag"] == tag]
        prov = u[(u["role"] == "provider") & (u["tier"] == "provider")]
        riv = u[(u["role"] == "rival") & u["tier"].isin(["tier1", "tier2"])]
        listed = fe[(fe["launch_tag"] == tag) & (fe["role"] == "provider")]["ticker"].unique().tolist() if len(fe) else []
        out.append({
            "launch_tag": tag, "launch_utc": r.get("launch_utc"), "vehicle": r.get("LV_Type"),
            "agency": r.get("Launch_Agency", ""), "site": r.get("Launch_Site", ""),
            "gcat_code": r.get("LaunchCode", ""), "score": float(r["score"]) if r.get("score") else None,
            "listed_providers": listed,
            "in_provider_case_series": bool(len(prov)), "in_rival_test": bool(len(riv)),
            "rival_tickers": sorted(riv["ticker"].unique().tolist()),
            "why_not_in_sample": "; ".join(sorted(set(excl[excl["launch_tag"] == tag]["reason"]))) or None,
        })
    return out


def git_state() -> dict:
    """Commit the export was made from, and whether the working tree had uncommitted changes."""
    import subprocess
    try:
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=C.ROOT, capture_output=True, text=True, timeout=20).stdout.strip()
        dirty = bool(subprocess.run(["git", "status", "--porcelain"], cwd=C.ROOT, capture_output=True, text=True, timeout=20).stdout.strip())
        return {"commit": head or None, "uncommitted_changes": dirty}
    except (OSError, subprocess.SubprocessError):
        return {"commit": None, "uncommitted_changes": None}


def sample_funnel(cov, records) -> dict:
    """Counts for the sample-construction funnel, from the pipeline's own interim files (no typed numbers)."""
    from collections import Counter

    def nrows(name):
        f = C.INTERIM / name
        return int(len(pd.read_csv(f))) if f.exists() else None

    fail = cov[cov["outcome"] == "failure"]
    dropped = fail[fail["usable"] != True] if "usable" in fail else fail.iloc[0:0]
    riv = [r for r in records if r["group"] == "rival"]
    prov = [r for r in records if r["group"] != "rival"]
    return {
        "launch_attempts": nrows("orbital_launches.csv"),
        "failures": nrows("failures.csv"),
        "pad_explosions": nrows("ground_anomalies.csv"),
        "failures_in_study": len({r["launch_tag"] for r in records}),     # listed maker or Tier 1-2 rival
        "failures_with_any_mapped_firm": int(fail["launch_tag"].nunique()),  # includes descriptive Tier 3 (diversified groups)
        "failure_firm_events_mapped": int(len(fail)),
        "failure_firm_events_dropped": ({str(k): int(v) for k, v in Counter(dropped["coverage_reason"].fillna("other")).items()}
                                        if "coverage_reason" in dropped else {}),
        "provider_cases": len(prov), "provider_firms": len({r["ticker"] for r in prov}),
        "rival_failures": len({r["launch_tag"] for r in riv}), "rival_firm_events": len(riv),
        "rival_firms": len({r["ticker"] for r in riv}), "rival_clusters": len({r["cluster"] for r in riv}),
        "rival_firm_events_by_firm": dict(Counter(r["firm"] for r in riv)),
    }


def main(site_data: Path = SITE_DATA):
    s5 = _step05()
    cov, returns_by, benches, _ = s5.load()
    fail = cov[cov["outcome"] == "failure"]
    rival = s5.build(fail[(fail["role"] == "rival") & fail["tier"].isin(["tier1", "tier2"])], returns_by, benches)
    prov = s5.build(fail[(fail["role"] == "provider") & (fail["tier"] == "provider")], returns_by, benches)
    flags = load_flags()

    records = [to_record(fe, "rival", flags.get((fe.launch_tag, fe.ticker))) for fe in rival] + \
              [to_record(fe, "provider_failure", None) for fe in prov]
    site_data.mkdir(parents=True, exist_ok=True)
    (site_data / "firm_events.json").write_text(json.dumps(records, indent=1))
    (site_data / "rho.json").write_text(json.dumps(rho_pairs(rival)))
    (site_data / "failures.json").write_text(json.dumps(failures_table(cov), indent=1))
    shutil.copy(C.PROCESSED / "results.json", site_data / "results.json")
    res = json.loads((C.PROCESSED / "results.json").read_text())
    (site_data / "manifest.json").write_text(json.dumps({
        "project": "T-Minus Markets", "author": "Nahian Ibnat",
        "plan_version": res.get("plan_version"), "results_run_utc": res.get("run_utc"),
        "exported_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "windows": C.EVENT_WINDOWS, "path_range": [-5, 20], "min_rival_clusters": C.GATE_MIN_RIVAL_EVENTS, "returns": C.RETURN_TYPE,
        "sources": {"launches": C.GCAT_CITATION, "prices": "Yahoo Finance via yfinance (used locally only)"},
        "data_policy": "Only derived statistics are published: CARs, CAR variances, abnormal returns, "
                       "residual volatility and CAR correlations. No raw prices, raw returns, alphas or betas.",
        "parity_tolerances": TOLERANCES,
        "sample": sample_funnel(cov, records),
        "git": git_state(),
    }, indent=2))
    n_r = sum(r["group"] == "rival" for r in records)
    print(f"Exported {n_r} rival and {len(records) - n_r} provider firm-events to {site_data}")


if __name__ == "__main__":
    main()
