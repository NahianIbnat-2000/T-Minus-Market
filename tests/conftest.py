import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "pipeline"))


def jd(ts: str) -> str:
    t = pd.Timestamp(ts, tz="UTC")
    return f"{t.value / 1e9 / 86400 + 2440587.5:.6f}"


# Synthetic launches. Names and outcomes are invented test cases, not real history.
ROWS = [
    # tag, utc, LV_Type, agency, code
    ("1999-001", "1999-06-01 12:00", "Antares 100", "OSC", "OF"),        # before start date
    ("2014-001", "2014-07-13 16:52", "Antares 120", "OSC", "OS"),
    ("2014-F01", "2014-10-28 22:22", "Antares 130", "OSC", "OF"),        # after US close
    ("2015-F01", "2015-06-28 14:21", "Falcon 9", "SPX", "OF"),            # private provider
    ("2020-F01", "2020-07-04 21:19", "Electron", "RL", "OF"),             # before listing
    ("2021-001", "2021-03-22 22:30", "Electron", "RL", "OS"),
    ("2022-001", "2022-06-28 09:55", "Electron", "RL", "OS"),
    ("2022-F01", "2022-12-21 01:47", "Vega", "AE", "OF"),                 # small segment, RKLB rival
    ("2023-F01", "2023-09-19 06:55", "Electron", "RL", "OF"),
    ("2023-002", "2023-10-01 10:00", "Atlas V 551", "ULA", "OS85"),       # partial success
    ("2023-F02", "2023-11-01 10:00", "Atlas V 401", "ULA", "OS55"),       # partial -> failure
    ("2016-E01", "2016-09-01 13:07", "Falcon 9", "SPX", "OE"),            # pad explosion
    ("2018-U01", "2018-01-01 00:00", "Zenit", "X", "OU"),                 # unknown
    ("2019-S01", "2019-05-05 05:00", "Test Rocket", "T", "TS"),           # suborbital category
    ("2019-B01", "2019-05-06 05:00", "Mystery", "X", "Q?"),               # bad code
]


@pytest.fixture
def gcat_file(tmp_path):
    cols = ["Launch_Tag", "Launch_JD", "Launch_Date", "LV_Type", "LV_Variant", "Launch_Agency",
            "Launch_Site", "LaunchCode", "FailCode", "Flight_ID", "Mission", "LTCite"]
    lines = ["#" + "\t".join(cols), "# Updated 2026 Nov 1 (synthetic)"]
    for tag, utc, lv, ag, code in ROWS:
        lines.append("\t".join([tag, jd(utc), utc, lv, "", ag, "SITE", code, "", "", "", "test"]))
    p = tmp_path / "launch.tsv"
    p.write_text("\n".join(lines) + "\n")
    return p


@pytest.fixture
def firm_map_file(tmp_path):
    text = """map_id,lv_pattern,firm_name,entity_role,ticker,exchange,listing_start,listing_end,relation_start,relation_end,segment,market,control_type,launch_exposure,verification_status,source_url,source_date,notes
T1,^Electron,Rocket Lab,manufacturer_operator,RKLB,XNAS,2021-08-25,,,,small,global_commercial,listed_private_owned,pure_play,verified,x,2026-11-21,test
T2,^Vega$,Avio SpA,manufacturer,AVIO.MI,XMIL,2017-04-10,,,,small,global_commercial,listed_private_owned,major,verified,x,2026-11-21,test
T3,^Antares,Orbital Sciences Corp,manufacturer_operator,ORB,XNYS,,2015-02-09,,2015-02-09,medium,global_commercial,listed_private_owned,major,verified,x,2026-11-21,test
T4,^Atlas,Boeing Co,corporate_parent,BA,XNYS,,,,,heavy,global_commercial,diversified_parent,minor,unverified,,,test
T5,^Atlas,Rejected Corp,corporate_parent,REJ,XNYS,,,,,heavy,global_commercial,diversified_parent,minor,rejected,,,test
"""
    p = tmp_path / "firm_map.csv"
    p.write_text(text)
    return p


@pytest.fixture
def segments():
    return pd.DataFrame({"lv_pattern": ["^Electron", "^Vega$", "^Antares", "^Falcon ?9", "^Atlas", "^Zhuque"],
                         "segment": ["small", "small", "medium", "heavy", "heavy", "small"],
                         "market": ["global_commercial"] * 5 + ["china"],
                         "valid_from": [""] * 6, "valid_to": [""] * 6, "notes": [""] * 6})


@pytest.fixture
def synthetic_returns():
    """Ticker returns = 0.0005 + 1.2 * market + noise(sd 3%), on XNYS sessions."""
    import exchange_calendars as xc
    rng = np.random.default_rng(7)
    sess = xc.get_calendar("XNYS", start="2013-01-01").sessions_in_range("2013-01-02", "2015-12-31")
    m = rng.normal(0.0003, 0.01, len(sess))
    e = rng.normal(0, 0.03, len(sess))
    r = 0.0005 + 1.2 * m + e
    dates = pd.DatetimeIndex(sess).tz_localize(None) if getattr(sess, "tz", None) else pd.DatetimeIndex(sess)
    df = pd.concat([pd.DataFrame({"date": dates, "ticker": "ORB", "ret": r}),
                    pd.DataFrame({"date": dates, "ticker": "^GSPC", "ret": m})], ignore_index=True)
    return df
