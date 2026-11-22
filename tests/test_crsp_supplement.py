"""Step 10: CRSP supplement keeps v1.0 intact, follows the cluster rule and the H2 tiers."""
import importlib.util
import json
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("s10", ROOT / "pipeline" / "10_crsp_supplement.py")
s10 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s10)


def rec(id_, tag, tk, day0, cl, exch="XNAS", src=None, group="rival", tier="tier1", outcome="failure", car=0.01, var=0.0004):
    r = {"id": id_, "group": group, "launch_tag": tag, "ticker": tk, "exchange": exch, "firm": tk, "vehicle": "V",
         "tier": tier, "outcome": outcome, "day0": day0, "cluster": cl,
         "windows": {w: {"car": car, "var": var, "L": 2} for w in ("primary", "robust", "descriptive")}}
    if src:
        r["source"] = src
    return r


def test_recluster_keeps_v10_and_joins_by_rule():
    base = [rec("A|RKLB|rival", "A", "RKLB", "2022-06-13", 7), rec("B|RKLB|rival", "B", "RKLB", "2022-06-15", 7)]
    crsp = [rec("A|VORB|rival", "A", "VORB", "2022-06-13", None, src="crsp"),
            rec("C|VORB|provider", "C", "VORB", "2022-06-16", None, src="crsp", group="provider_failure"),
            rec("D|VORB|rival", "D", "VORB", "2023-01-11", None, src="crsp")]
    cl = s10.recluster(base, crsp)
    assert cl["A"] == cl["B"] == 7          # v1.0 cluster kept
    assert cl["C"] == 7                      # VORB failure 3 sessions later joins via the shared firm
    assert cl["D"] not in (7,) and cl["D"] > 7


def test_cross_source_rho_uses_imputed_corr_and_overlap():
    a = rec("A|RKLB|rival", "A", "RKLB", "2022-06-13", 1)
    b = rec("A|VORB|rival", "A", "VORB", "2022-06-14", 1, src="crsp")
    rho = s10.combined_rho([a, b], {w: [] for w in ("primary", "robust", "descriptive")}, pd.DataFrame(columns=["key_i", "key_j", "resid_corr"]), 0.2)
    assert rho["primary"][0][2] == pytest.approx(0.2 * 1 / 2)   # one common day in [0,+1]


def test_h2_excludes_tier3():
    base = [rec(f"T{i}|RKLB|rival", f"T{i}", "RKLB", "2022-06-13", i) for i in range(1, 5)]
    extra = [rec("X|ORB|rival", "X", "ORB", "2010-01-05", 99, exch="XNYS", src="crsp", tier="tier3", car=0.5)]
    rho = {w: [] for w in ("primary", "robust", "descriptive")}
    out = s10.run_tests(base + extra, rho, 99, "t")
    assert out["n"] == 4


def test_crsp_folder_is_gitignored():
    assert "data/crsp/" in (ROOT / ".gitignore").read_text()
