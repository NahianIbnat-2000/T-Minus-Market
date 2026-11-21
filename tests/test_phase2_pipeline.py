"""End-to-end check of step 05 on synthetic interim files with a planted effect."""
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

import config as C
from eventtime import get_calendar

PIPE = Path(__file__).resolve().parents[1] / "pipeline"


def _sessions(ex, a, b):
    s = pd.DatetimeIndex(get_calendar(ex).sessions_in_range(a, b))
    return s.tz_localize(None) if s.tz is not None else s


def make_interim(root: Path, rival_effect=0.03, provider_effect=-0.10, seed=11):
    rng = np.random.default_rng(seed)
    nys, mil = _sessions("XNYS", "2012-01-03", "2024-12-30"), _sessions("XMIL", "2012-01-02", "2024-12-30")
    m_us, m_it = rng.normal(0, .01, len(nys)), rng.normal(0, .01, len(mil))
    rUS = 0.0003 + 1.2 * m_us + rng.normal(0, .04, len(nys))
    rIT = 0.0002 + 0.8 * m_it + rng.normal(0, .02, len(mil))
    rows, k = [], 0
    # 14 failures, each with both firms as rivals (shared day 0 -> cluster), spaced 60 sessions apart
    for i in range(14):
        d_us, d_it = nys[600 + 160 * i], mil[600 + 160 * i]
        rUS[600 + 160 * i] += rival_effect
        rIT[600 + 160 * i] += rival_effect
        tag = f"F{i:02d}"
        for tic, ex, d in [("USCO", "XNYS", d_us), ("ITCO", "XMIL", d_it)]:
            rows.append(dict(launch_tag=tag, role="rival", tier="tier1", outcome="failure", ticker=tic,
                             exchange=ex, day0=d, cluster=i + 1, usable=True, firm_name=tic, lv_type="Rocket X",
                             listing_start="", disclosure_confidence="low" if i == 0 else "provisional"))
    # two provider failures for USCO, eight provider successes
    for j, idx in enumerate([3000 - 150, 3000 - 70]):
        rUS[idx] += provider_effect
        rows.append(dict(launch_tag=f"P{j}", role="provider", tier="provider", outcome="failure", ticker="USCO",
                         exchange="XNYS", day0=nys[idx], cluster=100 + j, usable=True, firm_name="USCO",
                         lv_type="Rocket U", listing_start="", disclosure_confidence="provisional"))
    for j in range(8):
        idx = 700 + 250 * j + 37
        rows.append(dict(launch_tag=f"S{j}", role="provider", tier="provider", outcome="success", ticker="USCO",
                         exchange="XNYS", day0=nys[idx], cluster=np.nan, usable=True, firm_name="USCO",
                         lv_type="Rocket U", listing_start="", disclosure_confidence="provisional"))
    inter = root / "interim"
    inter.mkdir(parents=True)
    pd.DataFrame(rows).to_csv(inter / "coverage.csv", index=False)
    rets = pd.concat([
        pd.DataFrame({"date": nys, "ticker": "^GSPC", "ret": m_us}),
        pd.DataFrame({"date": mil, "ticker": "FTSEMIB.MI", "ret": m_it}),
        pd.DataFrame({"date": nys, "ticker": "USCO", "ret": rUS}),
        pd.DataFrame({"date": mil, "ticker": "ITCO", "ret": rIT})])
    rets.to_parquet(inter / "returns.parquet", index=False)
    orb = pd.DataFrame({"Launch_Tag": [f"F{i:02d}" for i in range(14)],
                        "launch_utc": pd.to_datetime(nys[[600 + 160 * i for i in range(14)]]).tz_localize("UTC"),
                        "LV_Type": ["Rocket X"] * 7 + [f"New{i}" for i in range(7)],
                        "outcome": "failure"})
    orb.to_csv(inter / "orbital_launches.csv", index=False)


def test_step05_end_to_end(tmp_path, monkeypatch):
    make_interim(tmp_path)
    monkeypatch.setattr(C, "INTERIM", tmp_path / "interim")
    monkeypatch.setattr(C, "PROCESSED", tmp_path / "processed")
    monkeypatch.setattr(C, "REPORTS", tmp_path / "reports")
    (tmp_path / "reports").mkdir()
    spec = importlib.util.spec_from_file_location("step05", PIPE / "05_event_study.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    monkeypatch.setattr(sys, "argv", ["05", "--quick"])
    mod.main()

    res = json.loads((tmp_path / "processed" / "results.json").read_text())
    p = res["primary"]
    assert p["n_firm_events"] == 28 and p["n_clusters"] == 14 and p["n_firms"] == 2
    assert abs(p["mean_car"] - 0.03) < 0.02            # planted +3% recovered
    assert p["ci_low"] < 0.03 < p["ci_high"]
    names = [r["name"] for r in res["robustness"]]
    for must in ["R1 portfolio t-test", "R2 plain t", "R3 rank (simulated p)", "R4 window [-1,+3]",
                 "R5a drop low-confidence timing", "R5b low-confidence day 0 + 1 session",
                 "R6 drop fallback-model events", "R7 drop multi-failure clusters", "R8 without USCO"]:
        assert must in names
    r5a = next(r for r in res["robustness"] if r["name"].startswith("R5a"))
    assert r5a["n_firm_events"] == 26                   # the low-confidence failure (2 firm-events) dropped
    assert res["placebo"]["draws"] == 100 and res["placebo"]["actual_percentile"] > 90
    cases = res["provider_case_series"]
    assert len(cases) == 2 and all(c["car_primary"] < -0.05 for c in cases)   # planted -10%
    ids = {e["id"] for e in res["exploratory"]}
    assert {"H3a", "H3b", "H3c"} <= ids
    assert all(e["p_holm"] >= e["p_raw"] for e in res["exploratory"])
    report = (tmp_path / "reports" / "05_results.md").read_text()
    assert "Primary result (H2, confirmatory)" in report and "Quick run" in report
    cars = pd.read_csv(tmp_path / "processed" / "firm_event_cars.csv")
    assert set(cars["group"]) == {"rival", "provider_failure", "provider_success"}
