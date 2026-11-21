"""R9b shared-date placebo (exploratory, step 09) on the synthetic world."""
import importlib.util
import json
import sys
from pathlib import Path

import pytest

import config as C
from test_phase3_parity import make_world

PIPE = Path(__file__).resolve().parents[1] / "pipeline"


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, PIPE / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_step09_adds_exploratory_r9b(tmp_path, monkeypatch):
    make_world(tmp_path)
    for attr, sub in [("INTERIM", "interim"), ("PROCESSED", "processed"), ("REPORTS", "reports"), ("MANUAL", "manual")]:
        monkeypatch.setattr(C, attr, tmp_path / sub)
    (tmp_path / "reports").mkdir()
    monkeypatch.setattr(sys, "argv", ["05", "--quick"])
    _load("s5", "05_event_study.py").main()
    before = json.loads((tmp_path / "processed" / "results.json").read_text())
    _load("s9", "09_audit_exploratory.py").main(["--quick"])
    after = json.loads((tmp_path / "processed" / "results.json").read_text())
    r9b = after["exploratory_audit"]["placebo_shared"]
    assert len(r9b["distribution"]) == 100 and 0 <= r9b["actual_percentile"] <= 100
    assert r9b["clusters_with_common_date"] <= r9b["clusters"]
    assert abs(r9b["actual_mean_car"] - before["placebo"]["actual_mean_car"]) < 1e-12   # same real result
    for k in ("primary", "robustness", "placebo"):                                       # prespecified results untouched
        assert after[k] == before[k]
    assert (tmp_path / "reports" / "09_audit_exploratory.md").exists()
