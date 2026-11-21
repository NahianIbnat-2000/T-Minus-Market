"""Step 06 on synthetic data: flagged events are dropped exactly as specified."""
import importlib.util
import json
import sys
from pathlib import Path

import config as C
from test_phase2_pipeline import make_interim

PIPE = Path(__file__).resolve().parents[1] / "pipeline"


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, PIPE / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_step06_drops_flagged_events(tmp_path, monkeypatch):
    make_interim(tmp_path)
    (tmp_path / "manual").mkdir()
    (tmp_path / "manual" / "confounded_events.csv").write_text(
        "launch_tag,ticker,verdict,reason,source_url\n"
        "F03,USCO,confounded,test,x\n"
        "F05,ITCO,possibly_confounded,test,x\n"
        "F07,USCO,sector_move,test,x\n"
        "F99,USCO,confounded,no such event,x\n")
    for attr, sub in [("INTERIM", "interim"), ("PROCESSED", "processed"), ("REPORTS", "reports"), ("MANUAL", "manual")]:
        monkeypatch.setattr(C, attr, tmp_path / sub)
    (tmp_path / "reports").mkdir()
    monkeypatch.setattr(sys, "argv", ["05", "--quick"])
    _load("s5", "05_event_study.py").main()
    out = _load("s6", "06_confounding_sensitivity.py").run()

    n = {r["id"]: r["n_firm_events"] for r in out}
    assert n["H2"] == 28 and n["E1"] == 27 and n["E2"] == 26 and n["E3"] == 25
    res = json.loads((tmp_path / "processed" / "results.json").read_text())
    ec = res["exploratory_confounding"]
    assert ec["unmatched_flags"] == ["F99 USCO"]
    assert res["primary"]["n_firm_events"] == 28          # confirmatory result untouched
    rep = (tmp_path / "reports" / "06_confounding_sensitivity.md").read_text()
    assert "EXPLORATORY" in rep and "F03 USCO" in rep
