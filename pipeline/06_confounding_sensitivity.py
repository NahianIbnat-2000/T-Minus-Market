"""Step 06 (EXPLORATORY): re-estimate H2 without rival firm-events that have confounding news.

This analysis was designed AFTER the Phase 2 results were seen. It is exploratory and can never
replace the confirmatory H2 result in step 05. The flagged events and the reasons are listed,
with sources, in data/manual/confounded_events.csv.

Specifications (all reported, whatever they show):
  E1  drop events with verdict 'confounded'
  E2  drop 'confounded' and 'possibly_confounded'
  E3  drop every flagged event (also 'sector_move')
Each uses the primary test (BMP with Kolari-Pynnonen cluster adjustment) and the R1 portfolio test.

Writes reports/06_confounding_sensitivity.md and adds 'exploratory_confounding' to
data/processed/results.json.
"""
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

import config as C
from analysis import PRIMARY
from eventstudy import bmp_kp_test, portfolio_test

SPECS = [
    ("E1", "drop 'confounded'", {"confounded"}),
    ("E2", "drop 'confounded' and 'possibly_confounded'", {"confounded", "possibly_confounded"}),
    ("E3", "drop every flagged event", {"confounded", "possibly_confounded", "sector_move"}),
]


def _step05():
    spec = importlib.util.spec_from_file_location("step05", Path(__file__).with_name("05_event_study.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run():
    s5 = _step05()
    cov, returns_by, benches, _ = s5.load()
    fail = cov[cov["outcome"] == "failure"]
    rival_rows = fail[(fail["role"] == "rival") & fail["tier"].isin(["tier1", "tier2"])]
    rival = s5.build(rival_rows, returns_by, benches)

    flags = pd.read_csv(C.MANUAL / "confounded_events.csv", dtype=str, keep_default_na=False)
    flag_of = {(r.launch_tag, r.ticker): r.verdict for r in flags.itertuples()}
    unmatched = [k for k in flag_of if k not in {(fe.launch_tag, fe.ticker) for fe in rival}]

    base = bmp_kp_test(rival, PRIMARY, name="H2 primary (confirmatory, all events)")
    out = [{"id": "H2", "label": base.name, "dropped": [], **base.as_dict()}]
    for sid, label, verdicts in SPECS:
        drop = [(fe.launch_tag, fe.ticker) for fe in rival if flag_of.get((fe.launch_tag, fe.ticker)) in verdicts]
        keep = [fe for fe in rival if (fe.launch_tag, fe.ticker) not in set(drop)]
        r = bmp_kp_test(keep, PRIMARY, name=f"{sid} {label} [exploratory]")
        out.append({"id": sid, "label": r.name, "dropped": [f"{a} {b}" for a, b in drop], **r.as_dict()})
        for p in portfolio_test(keep, PRIMARY, name=f"{sid} portfolio"):
            out.append({"id": sid + "-R1", "label": p.name + " [exploratory]", "dropped": [], **p.as_dict()})

    res_path = C.PROCESSED / "results.json"
    if res_path.exists():
        res = json.loads(res_path.read_text())
        res["exploratory_confounding"] = {"note": "designed after results; exploratory only",
                                          "flags_file": "data/manual/confounded_events.csv",
                                          "unmatched_flags": [f"{a} {b}" for a, b in unmatched],
                                          "results": out}
        res_path.write_text(json.dumps(res, indent=2, default=str))
    write_report(out, flags, unmatched)
    return out


def pct(x):
    return "n/a" if x is None or not np.isfinite(x) else f"{100 * x:+.2f}%"


def write_report(out, flags, unmatched):
    L = ["# Step 06: Confounding sensitivity (EXPLORATORY)", "",
         "**Designed after the Phase 2 results were seen. Exploratory only: the confirmatory result is H2 in "
         "reports/05_results.md and does not change.**", "",
         "## Flagged rival firm-events", "", "| Launch | Ticker | Verdict | Reason |", "| --- | --- | --- | --- |"]
    L += [f"| {r.launch_tag} | {r.ticker} | {r.verdict} | {r.reason} |" for r in flags.itertuples()]
    if unmatched:
        L += ["", f"Flags that matched no usable rival firm-event: {', '.join(f'{a} {b}' for a, b in unmatched)}"]
    L += ["", "## Results (CAR[0,+1])", "",
          "| Spec | Mean CAR | 95% CI | Statistic | p | Firm-events | Clusters | Dropped |",
          "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for r in out:
        ci = "n/a" if r.get("ci_low") is None else f"{pct(r['ci_low'])} to {pct(r['ci_high'])}"
        stat = "n/a" if r.get("stat") is None else f"{r['stat']:.3f}"
        p = "n/a" if r.get("p") is None else f"{r['p']:.4f}"
        L.append(f"| {r['label']} | {pct(r['mean_car'])} | {ci} | {stat} | {p} | {r['n_firm_events']} | "
                 f"{r['n_clusters']} | {'; '.join(r['dropped']) or '-'} |")
    L += ["", "No multiple-testing correction is applied across E1 to E3; none of them is a confirmatory test."]
    (C.REPORTS / "06_confounding_sensitivity.md").write_text("\n".join(L) + "\n")


if __name__ == "__main__":
    for r in run():
        if r["id"] in ("H2", "E1", "E2", "E3"):
            print(f"{r['id']:<3} mean CAR[0,+1] = {pct(r['mean_car'])}  p = {r['p']:.4f}  n = {r['n_firm_events']}")
    print("Wrote reports/06_confounding_sensitivity.md and updated data/processed/results.json")
