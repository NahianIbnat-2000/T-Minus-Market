"""The WRDS script must reproduce the pipeline's event-study arithmetic, and write no raw data."""
import importlib.util
import json
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import config as C
from eventstudy import build_firm_event, car
from eventtime import get_calendar

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("wx", ROOT / "wrds" / "tminus_crsp_extract.py")
wx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wx)


def _world(seed=3):
    s = get_calendar("XNYS").sessions
    sessions = pd.DatetimeIndex(s.tz_localize(None) if s.tz is not None else s)
    sessions = sessions[(sessions >= "2014-01-01") & (sessions <= "2016-12-31")]
    rng = np.random.default_rng(seed)
    m = pd.Series(rng.normal(0, 0.01, len(sessions)), index=sessions)
    r = pd.Series(0.0004 + 1.3 * m.values + rng.normal(0, 0.02, len(sessions)), index=sessions)
    r.iloc[200] = np.nan                                   # a missing day inside an estimation window
    return sessions, r, m


@pytest.mark.parametrize("day0", ["2015-06-29", "2015-10-12", "2016-03-01"])
def test_matches_pipeline(day0):
    sessions, r, m = _world()
    row = pd.Series({"launch_tag": "X", "ticker": "TST", "exchange": "XNYS", "day0": day0, "role": "rival", "tier": "tier1", "cluster": 1})
    rets = pd.DataFrame({"date": r.index, "ticker": "TST", "ret": r.values})
    bench = pd.DataFrame({"date": m.index, "ret": m.values})
    fe = build_firm_event(row, rets, bench)
    out, _, _ = wx.event_stats(sessions, r, m, day0)
    assert out["model"] == fe.model and out["est_obs"] == len(fe.est_r)
    assert abs(out["sigma"] - fe.sigma) < 1e-12
    for name, w in C.EVENT_WINDOWS.items():
        c, v, _ = car(fe, w)
        assert abs(out[f"car_{name}"] - c) < 1e-12 and abs(out[f"var_{name}"] - v) < 1e-15


def test_end_to_end_with_fake_wrds(tmp_path, monkeypatch):
    s = get_calendar("XNYS").sessions
    sessions = pd.DatetimeIndex(s.tz_localize(None) if s.tz is not None else s)
    sessions = sessions[(sessions >= "1998-01-01") & (sessions <= "2024-12-31")]
    rng = np.random.default_rng(1)
    mk = rng.normal(0, 0.01, len(sessions))
    perm = {"ORB": 1, "OA": 2, "ASTR": 3, "VORB": 4}
    dsf = pd.concat([pd.DataFrame({"permno": p, "date": sessions, "ret": 1.1 * mk + rng.normal(0, 0.02, len(sessions))}) for p in perm.values()])

    class FakeDB:
        def raw_sql(self, q, date_cols=None):
            q = " ".join(q.split())
            if "crsp.stocknames" in q:
                tk = q.split("ticker = '")[1].split("'")[0]
                return pd.DataFrame({"permno": [perm[tk]], "ticker": [tk], "comnam": ["X"], "namedt": ["1990-01-01"], "nameenddt": ["2024-12-31"]})
            if "crsp.dsf " in q:
                d = dsf.copy(); d["ret"] = d["ret"].astype("Float64"); d["permno"] = d["permno"].astype("Int64")
                return d                                   # WRDS gives nullable dtypes
            if "crsp.dsedelist" in q:
                return pd.DataFrame({"permno": [4], "date": [pd.Timestamp("2023-04-03")], "dlret": [-0.5]})
            if "crsp.dsi" in q:
                return pd.DataFrame({"date": sessions, "sprtrn": pd.array(mk, dtype="Float64")})
            raise AssertionError(q)

    monkeypatch.setattr(wx, "connect", lambda: FakeDB())
    monkeypatch.setattr(wx, "PERMNO_OVERRIDE", {})
    monkeypatch.chdir(tmp_path)
    wx.main()
    fe = pd.read_csv(tmp_path / "tminus_crsp_firm_events.csv")
    info = json.loads((tmp_path / "tminus_crsp_run_info.json").read_text())
    assert len(fe) == len(pd.read_csv(__import__("io").StringIO(wx.EVENTS_CSV)))
    assert info["contains_raw_data"] is False and fe["car_primary"].notna().sum() > 100
    raw_like = {"ret", "retx", "prc", "vol", "shrout", "alpha", "beta"}
    assert not raw_like & set(c.lower() for c in fe.columns)
    pairs = pd.read_csv(tmp_path / "tminus_crsp_pairs.csv")
    assert {"key_i", "key_j", "resid_corr", "common_event_days"} <= set(pairs.columns)
