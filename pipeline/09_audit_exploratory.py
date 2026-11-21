"""Step 09 (EXPLORATORY): analyses added after the 22 Nov 2026 audit that need price data.

R9b: the placebo benchmark with ONE shared pseudo-date per failure cluster (R9 draws a separate date
for each firm-event, which understates how rivals move together on the same day). Results are
reported next to R9, never instead of it. Logged in docs/ANALYSIS_PLAN.md as plan v1.1.

Adds 'exploratory_audit' to data/processed/results.json and writes reports/09_audit_exploratory.md.
Usage:  python pipeline/09_audit_exploratory.py [--quick]
"""
import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np

import config as C
from analysis import placebo_shared


def _step05():
    spec = importlib.util.spec_from_file_location("step05", Path(__file__).with_name("05_event_study.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def pct(x, d=2):
    return f"{x * 100:+.{d}f}%"


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="100 draws instead of 1000 (testing only)")
    args = ap.parse_args(argv)
    s5 = _step05()
    cov, returns_by, benches, _ = s5.load()
    fail = cov[cov["outcome"] == "failure"]
    rival_rows = fail[(fail["role"] == "rival") & fail["tier"].isin(["tier1", "tier2"])]
    rival = s5.build(rival_rows, returns_by, benches)
    f_day0 = {t: list(g["day0"]) for t, g in fail.groupby("ticker")}
    print("Running R9b (shared-date placebo) ...")
    r9b = placebo_shared(rival, rival_rows, returns_by, lambda ex: benches[ex], f_day0, n_draws=100 if args.quick else 1000)

    res_path = C.PROCESSED / "results.json"
    res = json.loads(res_path.read_text())
    res["exploratory_audit"] = {"note": "added after the 22 Nov 2026 audit; exploratory; plan v1.1", "placebo_shared": r9b}
    res_path.write_text(json.dumps(res, indent=2, default=str))

    r9 = res.get("placebo", {})
    sd9 = float(np.std(r9.get("distribution", [np.nan]), ddof=1))
    L = ["# Step 09: exploratory checks added after the audit", "",
         "Designed after the results were seen (audit of 22 Nov 2026). Exploratory: reported next to the",
         "prespecified results, never instead of them. Logged as plan v1.1.", "",
         "## R9b: placebo with one shared pseudo-date per failure cluster", "",
         "| | R9 (prespecified) | R9b (exploratory) |", "| --- | --- | --- |",
         f"| Pseudo-dates | one per firm-event | one per cluster ({r9b['clusters_with_common_date']} of {r9b['clusters']} clusters had a date eligible for all members) |",
         f"| Draws | {r9.get('draws')} | {r9b['draws']} |",
         f"| Real mean CAR[0,+1] | {pct(r9b['actual_mean_car'])} | {pct(r9b['actual_mean_car'])} |",
         f"| Placebo mean | {pct(r9.get('placebo_mean', np.nan))} | {pct(r9b['placebo_mean'])} |",
         f"| Placebo standard deviation | {pct(sd9)} | {pct(r9b['placebo_sd'])} |",
         f"| Middle 95% of placebo averages | {pct(r9.get('placebo_2.5pct', np.nan))} to {pct(r9.get('placebo_97.5pct', np.nan))} | {pct(r9b['placebo_2.5pct'])} to {pct(r9b['placebo_97.5pct'])} |",
         f"| Percentile of the real result | {r9.get('actual_percentile', float('nan')):.1f} | {r9b['actual_percentile']:.1f} |",
         f"| Two-sided share | {r9.get('two_sided_share', float('nan')):.3f} | {r9b['two_sided_share']:.3f} (Monte Carlo s.e. {r9b['monte_carlo_se']:.3f}) |",
         "", "A wider R9b spread than R9 means the original placebo understated how much ordinary-day averages vary",
         "when rivals share dates. Neither is an exact permutation test."]
    C.REPORTS.mkdir(parents=True, exist_ok=True)
    (C.REPORTS / "09_audit_exploratory.md").write_text("\n".join(L) + "\n")
    print(f"R9b: percentile {r9b['actual_percentile']:.1f}, two-sided share {r9b['two_sided_share']:.3f}, sd {pct(r9b['placebo_sd'])} (R9 sd {pct(sd9)})")
    print("Wrote reports/09_audit_exploratory.md and updated data/processed/results.json")


if __name__ == "__main__":
    main()
