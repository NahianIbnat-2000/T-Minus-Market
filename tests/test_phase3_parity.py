"""Phase 3: exported site data + browser module reproduce the Python results.

Three-way check on synthetic data with correlated rivals:
  (A) eventstudy.bmp_kp_test on FirmEvents built from raw returns
  (B) siteexport.bmp_kp_from_records on the exported JSON only
  (C) site/src/stats/eventstudy.js on the exported JSON (run with Node)
A == B exactly (1e-12); C == B within the tolerances written to site/data/manifest.json.
"""
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import stats

import config as C
from eventstudy import bmp_kp_test, portfolio_test
from eventtime import get_calendar
from siteexport import bmp_kp_from_records

ROOT = Path(__file__).resolve().parents[1]
PIPE = ROOT / "pipeline"
NODE = shutil.which("node")


def _load(name, file):
    spec = importlib.util.spec_from_file_location(name, PIPE / file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _sessions(ex, a, b):
    s = pd.DatetimeIndex(get_calendar(ex).sessions_in_range(a, b))
    return s.tz_localize(None) if s.tz is not None else s


def make_world(root: Path, seed=21):
    """Three rivals: two US firms with correlated noise (same calendar), one Italian firm."""
    rng = np.random.default_rng(seed)
    nys, mil = _sessions("XNYS", "2012-01-03", "2024-12-30"), _sessions("XMIL", "2012-01-02", "2024-12-30")
    m_us, m_it = rng.normal(0, .01, len(nys)), rng.normal(0, .01, len(mil))
    common = rng.normal(0, 1, len(nys))
    rA = 0.0003 + 1.2 * m_us + 0.04 * (np.sqrt(.5) * common + np.sqrt(.5) * rng.normal(0, 1, len(nys)))
    rB = 0.0001 + 0.9 * m_us + 0.03 * (np.sqrt(.5) * common + np.sqrt(.5) * rng.normal(0, 1, len(nys)))
    rI = 0.0002 + 0.8 * m_it + rng.normal(0, .02, len(mil))
    rows = []
    for i in range(12):
        k = 600 + 170 * i
        tag = f"F{i:02d}"
        conf = "low" if i == 0 else "provisional"
        for tic, ex, d in [("AAA", "XNYS", nys[k]), ("BBB", "XNYS", nys[k]), ("III", "XMIL", mil[k])]:
            rows.append(dict(launch_tag=tag, role="rival", tier="tier1", outcome="failure", ticker=tic,
                             exchange=ex, day0=d, cluster=i + 1, usable=True, firm_name=tic,
                             lv_type="Rocket X", listing_start="", disclosure_confidence=conf))
    # BBB listed late for the last event -> fallback model
    rows[-2]["listing_start"] = str(nys[600 + 170 * 11 - 60].date())
    inter = root / "interim"
    inter.mkdir(parents=True)
    pd.DataFrame(rows).to_csv(inter / "coverage.csv", index=False)
    pd.concat([pd.DataFrame({"date": nys, "ticker": "^GSPC", "ret": m_us}),
               pd.DataFrame({"date": mil, "ticker": "FTSEMIB.MI", "ret": m_it}),
               pd.DataFrame({"date": nys, "ticker": "AAA", "ret": rA}),
               pd.DataFrame({"date": nys, "ticker": "BBB", "ret": rB}),
               pd.DataFrame({"date": mil, "ticker": "III", "ret": rI})]).to_parquet(inter / "returns.parquet", index=False)
    pd.DataFrame({"Launch_Tag": [f"F{i:02d}" for i in range(12)],
                  "launch_utc": [str(nys[600 + 170 * i].date()) for i in range(12)],
                  "LV_Type": "Rocket X", "outcome": "failure"}).to_csv(inter / "orbital_launches.csv", index=False)
    man = root / "manual"
    man.mkdir()
    (man / "confounded_events.csv").write_text("launch_tag,ticker,verdict,reason,source_url\n"
                                               "F02,AAA,confounded,test,x\nF05,III,sector_move,test,x\n")


CASES = [
    ("all primary", "primary", {}),
    ("all robust", "robust", {}),
    ("all descriptive", "descriptive", {}),
    ("US only", "primary", {"tickers": ["AAA", "BBB"]}),
    ("drop confounded", "primary", {"dropFlags": ["confounded"]}),
    ("drop all flags", "primary", {"dropFlags": ["confounded", "sector_move"]}),
    ("drop low confidence", "primary", {"dropLowConfidence": True}),
    ("drop fallback", "primary", {"dropFallback": True}),
    ("III only robust", "robust", {"tickers": ["III"]}),
]


def _py_select(fes, opts, flags):
    keep = []
    for fe in fes:
        if opts.get("tickers") and fe.ticker not in opts["tickers"]:
            continue
        if flags.get((fe.launch_tag, fe.ticker)) in opts.get("dropFlags", []):
            continue
        if opts.get("dropLowConfidence") and fe.meta.get("disclosure_confidence") == "low":
            continue
        if opts.get("dropFallback") and fe.model != "market_model":
            continue
        keep.append(fe)
    return keep


@pytest.fixture(scope="module")
def world(tmp_path_factory):
    root = tmp_path_factory.mktemp("p3")
    make_world(root)
    mp = pytest.MonkeyPatch()
    for attr, sub in [("INTERIM", "interim"), ("PROCESSED", "processed"), ("REPORTS", "reports"), ("MANUAL", "manual")]:
        mp.setattr(C, attr, root / sub)
    (root / "reports").mkdir()
    mp.setattr(sys, "argv", ["05", "--quick"])
    s5 = _load("s5", "05_event_study.py")
    s5.main()
    _load("s7", "07_export_site_data.py").main(site_data=root / "site_data")
    cov, rb, bn, _ = s5.load()
    fes = s5.build(cov[cov["role"] == "rival"], rb, bn)
    flags = {("F02", "AAA"): "confounded", ("F05", "III"): "sector_move"}
    yield root, fes, flags
    mp.undo()


def test_fallback_and_correlation_are_exercised(world):
    root, fes, _ = world
    assert any(fe.model == "market_adjusted_fallback" for fe in fes)
    rho = json.loads((root / "site_data" / "rho.json").read_text())
    vals = [p[2] for p in rho["primary"]]
    assert max(vals) > 0.2          # AAA-BBB share dates and correlated noise


def test_export_reference_equals_raw_data_test(world):
    root, fes, flags = world
    recs = [r for r in json.loads((root / "site_data" / "firm_events.json").read_text()) if r["group"] == "rival"]
    rho = json.loads((root / "site_data" / "rho.json").read_text())
    by_id = {r["id"]: r for r in recs}
    for name, w, opts in CASES:
        sub = _py_select(fes, opts, flags)
        a = bmp_kp_test(sub, C.EVENT_WINDOWS[w])
        b = bmp_kp_from_records([by_id[f"{fe.launch_tag}|{fe.ticker}|rival"] for fe in sub], rho, w)
        assert a.n_firm_events == b["n"], name
        assert a.mean_car == pytest.approx(b["mean"], abs=1e-12), name
        if a.ci_low is not None and np.isfinite(a.ci_low):
            assert a.ci_low == pytest.approx(b["ci_low"], abs=1e-12), name
        if np.isfinite(a.stat):
            assert a.stat == pytest.approx(b["stat"], abs=1e-12), name
            assert a.p == pytest.approx(b["p"], abs=1e-12), name


def _numeric_under(obj, forbidden, path=""):
    """Yield paths where a forbidden key holds numbers (a text label is allowed)."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in forbidden and not isinstance(v, str):
                yield f"{path}/{k}"
            yield from _numeric_under(v, forbidden, f"{path}/{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj[:50]):
            yield from _numeric_under(v, forbidden, f"{path}[{i}]")


def test_no_raw_market_data_exported(world):
    root, _, _ = world
    forbidden = {"ret", "returns", "price", "prices", "adj_close", "close", "alpha", "beta", "est_r", "est_m"}
    for f in (root / "site_data").glob("*.json"):
        bad = list(_numeric_under(json.loads(f.read_text()), forbidden))
        assert not bad, f"raw market data in {f.name}: {bad[:3]}"
    recs = json.loads((root / "site_data" / "firm_events.json").read_text())
    assert all(len(r["path"]) <= 26 for r in recs)


@pytest.mark.skipif(NODE is None, reason="Node.js not installed")
def test_browser_module_matches_python(world, tmp_path):
    root, fes, flags = world
    data = root / "site_data"
    tol = json.loads((data / "manifest.json").read_text())["parity_tolerances"]
    recs = [r for r in json.loads((data / "firm_events.json").read_text()) if r["group"] == "rival"]
    rho = json.loads((data / "rho.json").read_text())
    by_id = {r["id"]: r for r in recs}
    t_points = [[x, df] for df in (1, 2, 5, 13, 21, 60) for x in (-3.1, -0.5, 0.0, 0.854, 2.2, 7.0)]
    sign_points = [[k, n] for n in (5, 14, 22) for k in range(0, n + 1, 3)]
    cases = {"tests": [{"name": n, "window": w, "opts": {"group": "rival", **o}} for n, w, o in CASES],
             "t_points": t_points, "sign_points": sign_points}
    (tmp_path / "cases.json").write_text(json.dumps(cases))
    subprocess.run([NODE, str(ROOT / "site" / "tests" / "parity.mjs"), str(data),
                    str(tmp_path / "cases.json"), str(tmp_path / "out.json")], check=True)
    js = json.loads((tmp_path / "out.json").read_text())

    for (name, w, opts), got in zip(CASES, js["tests"]):
        sub = _py_select(fes, opts, flags)
        ref = bmp_kp_from_records([by_id[f"{fe.launch_tag}|{fe.ticker}|rival"] for fe in sub], rho, w)
        assert got["n"] == ref["n"] and got["clusters"] == ref["clusters"], name
        assert abs(got["mean"] - ref["mean"]) <= tol["car_and_ci_abs"], name
        for k in ("ci_low", "ci_high"):
            if ref[k] is not None:
                assert abs(got[k] - ref[k]) <= tol["car_and_ci_abs"], (name, k)
        if ref["stat"] is not None:
            assert abs(got["stat"] - ref["stat"]) <= tol["t_stat_abs"], name
            assert abs(got["p"] - ref["p"]) <= tol["p_value_abs"], name
            assert abs(got["mean_corr"] - ref["mean_corr"]) <= 1e-12, name

    for (name, w, opts), got in zip(CASES, js["portfolio"]):
        res = portfolio_test(_py_select(fes, opts, flags), C.EVENT_WINDOWS[w])
        if got["t"] is None:
            continue
        assert abs(got["mean"] - res[0].mean_car) <= tol["car_and_ci_abs"], name
        assert abs(got["t"] - res[0].stat) <= tol["t_stat_abs"], name
        assert abs(got["p"] - res[0].p) <= tol["p_value_abs"], name
        assert abs(got["sign_p"] - res[1].p) <= tol["p_value_abs"], name

    for r in js["t"]:
        assert abs(r["sf"] - stats.t.sf(r["x"], r["df"])) <= 1e-10
        assert abs(r["ppf975"] - stats.t.ppf(0.975, r["df"])) <= 1e-9
    for r in js["sign"]:
        assert abs(r["p"] - stats.binomtest(r["k"], r["n"], 0.5).pvalue) <= 1e-10
