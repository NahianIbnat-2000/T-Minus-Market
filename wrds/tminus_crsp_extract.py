"""T-Minus Markets: CRSP extension, run by a WRDS subscriber.

WHAT IT DOES
  Reads CRSP daily stock and index data for four delisted launch firms (Orbital Sciences, Orbital ATK,
  Astra Space, Virgin Orbit) through your own WRDS login, and computes the event-study statistics for the
  launch events listed below, using exactly the rules of the T-Minus Markets pipeline.

WHAT IT WRITES (in the folder you run it from)
  tminus_crsp_firm_events.csv   one row per event: CARs, CAR variances, daily abnormal returns T-5..T+20,
                                residual volatility, model used, number of estimation days
  tminus_crsp_pairs.csv         correlation of model residuals for events close in time (for the cluster test)
  tminus_crsp_run_info.json     PERMNOs used, CRSP tables used, row counts, version of this script

  It writes NO prices, NO raw returns, NO volumes, NO shares outstanding and NO model coefficients.
  Only derived statistics leave your machine. Please look at the three files before sending them.

HOW TO RUN
  Option A, WRDS Jupyter (easiest): wrds-jupyter.wharton.upenn.edu -> upload this file -> open a terminal ->
      python tminus_crsp_extract.py
  Option B, your laptop:  pip install wrds pandas numpy  ->  python tminus_crsp_extract.py
  You will be asked for your WRDS username and password (and Duo approval) by the wrds package.
  Run time: about a minute.

RULES COPIED FROM THE PIPELINE (pipeline/eventstudy.py)
  Day 0: the trading day given below (already computed from the disclosure time on the exchange calendar).
  Estimation window: trading days -250 to -30 before day 0; market model by OLS if >= 100 returns,
  market-adjusted model (alpha 0, beta 1) if 30-99, event dropped if fewer.
  Benchmark: S&P 500 return (CRSP SPRTRN), matching the pipeline's ^GSPC benchmark for US listings.
  Stock returns: CRSP RET (total return); a delisting return is added on the delisting day.
  Returns before the firm's real listing (SPAC shell periods) are dropped.
  A window with any missing return gets no CAR.
"""
from __future__ import annotations

import io
import json
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

VERSION = "1.1 (22 Nov 2026)"
EST_WINDOW, MIN_OBS, MIN_FALLBACK = (-250, -30), 100, 30
WINDOWS = {"primary": (0, 1), "robust": (-1, 3), "descriptive": (0, 20)}
PATH = (-5, 20)
PAIR_GAP_DAYS = 30            # residual correlations for events whose day 0 are at most this many calendar days apart

# Firm periods (from data/manual/firm_map.csv). listing_start trims SPAC-shell history.
FIRMS = {
    "ORB":  {"name": "Orbital Sciences", "listing_start": None,         "end": "2015-02-09"},
    "OA":   {"name": "Orbital ATK",      "listing_start": "2015-02-10", "end": "2018-06-06"},
    "ASTR": {"name": "Astra Space",      "listing_start": "2021-07-01", "end": "2024-07-18"},
    "VORB": {"name": "Virgin Orbit",     "listing_start": "2021-12-29", "end": "2023-04-04"},
}
# If the automatic PERMNO lookup picks the wrong security, put the right PERMNO here, e.g. {"OA": 12345}.
PERMNO_OVERRIDE: dict[str, int] = {"ORB": 76139, "OA": 76477, "ASTR": 19835, "VORB": 21321}   # confirmed on the first WRDS run

EVENTS_CSV = """launch_tag,ticker,exchange,role,tier,outcome,lv_type,day0,disclosure_confidence
2000-004,ORB,XNYS,provider,provider,success,Minotaur I,2000-01-27,provisional
2000-U01,ORB,XNYS,rival,tier3,failure,M-V,2000-02-10,provisional
2000-014,ORB,XNYS,provider,provider,success,Taurus 1110,2000-03-13,provisional
2000-F02,ORB,XNYS,rival,tier3,failure,Zenit-3SL,2000-03-13,provisional
2000-030,ORB,XNYS,provider,provider,success,Pegasus XL,2000-06-07,provisional
2000-042,ORB,XNYS,provider,provider,success,Minotaur I,2000-07-20,provisional
2000-061,ORB,XNYS,provider,provider,success,Pegasus H,2000-10-09,provisional
2000-074,ORB,XNYS,rival,tier3,failure,Kosmos 11K65M,2000-11-21,provisional
2000-F03,ORB,XNYS,rival,tier3,failure,Tsiklon-3,2000-12-27,provisional
2001-029,ORB,XNYS,rival,tier3,failure,Ariane 5G,2001-07-13,provisional
2001-U01,ORB,XNYS,provider,provider,failure,Taurus 2110,2001-09-21,provisional
2002-004,ORB,XNYS,provider,provider,success,Pegasus XL,2002-02-05,provisional
2002-F01,ORB,XNYS,rival,tier3,failure,KT-1,2002-09-16,provisional
2002-F02,ORB,XNYS,rival,tier3,failure,Soyuz-U-PVB,2002-10-15,provisional
2002-053,ORB,XNYS,rival,tier3,failure,Proton-K/DM-2M,2002-11-26,provisional
2002-F03,ORB,XNYS,rival,tier3,failure,Ariane 5ECA,2002-12-12,provisional
2003-004,ORB,XNYS,provider,provider,success,Pegasus XL,2003-01-27,provisional
2003-017,ORB,XNYS,provider,provider,success,Pegasus XL,2003-04-28,provisional
2003-030,ORB,XNYS,provider,provider,success,Pegasus XL,2003-06-26,provisional
2003-036,ORB,XNYS,provider,provider,success,Pegasus XL,2003-08-13,provisional
2003-U01,ORB,XNYS,rival,tier3,failure,KT-1,2003-09-16,provisional
2003-F02,ORB,XNYS,rival,tier3,failure,H-IIA 2024,2003-12-01,provisional
2004-018,ORB,XNYS,provider,provider,success,Taurus 3210,2004-05-20,provisional
2004-F01,ORB,XNYS,rival,tier3,failure,Shavit 1,2004-09-07,provisional
2004-050,ORB,XNYS,rival,tier3,failure,Delta 4H,2004-12-22,provisional
2004-052,ORB,XNYS,rival,tier3,failure,Tsiklon-3,2004-12-27,provisional
2005-011,ORB,XNYS,provider,provider,success,Minotaur I,2005-04-11,provisional
2005-014,ORB,XNYS,provider,provider,success,Pegasus XL/HAPS,2005-04-15,provisional
2005-F04,ORB,XNYS,rival,tier3,failure,KT-1,2005-06-09,provisional
2005-F01,ORB,XNYS,rival,tier3,failure,Molniya 8K78M,2005-06-21,provisional
2005-F02,ORB,XNYS,rival,tier3,failure,Volna,2005-06-21,provisional
2005-037,ORB,XNYS,provider,provider,success,Minotaur I,2005-09-23,provisional
2005-F03,ORB,XNYS,rival,tier1,failure,Rokot,2005-10-10,provisional
2006-006,ORB,XNYS,rival,tier3,failure,Proton-M/Briz-M,2006-02-28,provisional
2006-008,ORB,XNYS,provider,provider,success,Pegasus XL,2006-03-22,provisional
2006-F01,ORB,XNYS,rival,tier1,failure,Falcon 1,2006-03-27,provisional
2006-011,ORB,XNYS,provider,provider,success,Minotaur I,2006-04-17,provisional
2006-F02,ORB,XNYS,rival,tier3,failure,GSLV Mk I,2006-07-10,provisional
2006-F03,ORB,XNYS,rival,tier1,failure,Dnepr,2006-07-26,provisional
2006-058,ORB,XNYS,provider,provider,success,Minotaur I,2006-12-18,provisional
2007-F01,ORB,XNYS,rival,tier3,failure,Zenit-3SL,2007-01-31,provisional
2007-F02,ORB,XNYS,rival,tier1,failure,Falcon 1,2007-03-21,provisional
2007-014,ORB,XNYS,provider,provider,success,Minotaur I,2007-04-24,provisional
2007-015,ORB,XNYS,provider,provider,success,Pegasus XL,2007-04-26,provisional
2007-F03,ORB,XNYS,rival,tier3,failure,Proton-M/Briz-M,2007-09-06,provisional
2008-011,ORB,XNYS,rival,tier3,failure,Proton-M/Briz-M,2008-03-17,provisional
2008-017,ORB,XNYS,provider,provider,success,Pegasus XL,2008-04-16,provisional
2008-F01,ORB,XNYS,rival,tier1,failure,Falcon 1,2008-08-04,provisional
2008-F02,ORB,XNYS,rival,tier3,failure,Safir,2008-08-18,provisional
2008-051,ORB,XNYS,provider,provider,success,Pegasus XL,2008-10-20,provisional
2009-F01,ORB,XNYS,provider,provider,failure,Taurus 3110,2009-02-24,provisional
2009-F02,ORB,XNYS,rival,tier3,failure,Unha-2,2009-04-06,provisional
2009-028,ORB,XNYS,provider,provider,success,Minotaur I,2009-05-20,provisional
2009-F03,ORB,XNYS,rival,tier3,failure,Naro-1,2009-08-25,provisional
2009-046,ORB,XNYS,rival,tier3,failure,Chang Zheng 3B,2009-08-31,provisional
2010-F01,ORB,XNYS,rival,tier3,failure,GSLV Mk II,2010-04-15,provisional
2010-F02,ORB,XNYS,rival,tier3,failure,Naro-1,2010-06-10,provisional
2010-048,ORB,XNYS,provider,provider,success,Minotaur IV,2010-09-27,provisional
2010-062,ORB,XNYS,provider,provider,success,Minotaur IV,2010-11-22,provisional
2010-F03,ORB,XNYS,rival,tier3,failure,Proton-M/DM-3,2010-12-06,provisional
2010-F04,ORB,XNYS,rival,tier3,failure,GSLV Mk I,2010-12-27,provisional
2011-005,ORB,XNYS,rival,tier1,failure,Rokot,2011-02-01,provisional
2011-006,ORB,XNYS,provider,provider,success,Minotaur I,2011-02-07,provisional
2011-F01,ORB,XNYS,provider,provider,failure,Taurus 3110,2011-03-04,provisional
2011-029,ORB,XNYS,provider,provider,success,Minotaur I,2011-06-30,provisional
2011-045,ORB,XNYS,rival,tier3,failure,Proton-M/Briz-M,2011-08-18,provisional
2011-F02,ORB,XNYS,rival,tier3,failure,Chang Zheng 2C,2011-08-18,provisional
2011-F03,ORB,XNYS,rival,tier3,failure,Soyuz-U-PVB,2011-08-24,provisional
2011-052,ORB,XNYS,provider,provider,success,Minotaur IV+,2011-09-27,provisional
2011-F04,ORB,XNYS,rival,tier3,failure,Soyuz-2-1B,2011-12-23,provisional
2012-F01,ORB,XNYS,rival,tier3,failure,Unha-3,2012-04-13,provisional
2012-F02,ORB,XNYS,rival,tier3,failure,Safir,2012-05-23,provisional
2012-031,ORB,XNYS,provider,provider,success,Pegasus XL,2012-06-13,provisional
2012-044,ORB,XNYS,rival,tier3,failure,Proton-M/Briz-M,2012-08-06,provisional
2012-F03,ORB,XNYS,rival,tier3,failure,Safir,2012-09-24,provisional
2012-070,ORB,XNYS,rival,tier3,failure,Proton-M/Briz-M,2012-12-10,provisional
2013-F01,ORB,XNYS,rival,tier3,failure,Zenit-3SL,2013-02-01,provisional
2013-016,ORB,XNYS,provider,provider,success,Antares 110,2013-04-22,provisional
2013-033,ORB,XNYS,provider,provider,success,Pegasus XL,2013-06-28,provisional
2013-F02,ORB,XNYS,rival,tier3,failure,Proton-M/DM-3,2013-07-02,provisional
2013-047,ORB,XNYS,provider,provider,success,Minotaur V,2013-09-09,provisional
2013-051,ORB,XNYS,provider,provider,success,Antares 110,2013-09-18,provisional
2013-064,ORB,XNYS,provider,provider,success,Minotaur I,2013-11-20,provisional
2013-F03,ORB,XNYS,rival,tier3,failure,Chang Zheng 4B,2013-12-09,provisional
2014-003,ORB,XNYS,provider,provider,success,Antares 120,2014-01-09,provisional
2014-F01,ORB,XNYS,rival,tier3,failure,Proton-M/Briz-M,2014-05-16,provisional
2014-039,ORB,XNYS,provider,provider,success,Antares 120,2014-07-14,provisional
2014-050,ORB,XNYS,rival,tier1,failure,Soyuz-ST-B,2014-08-22,provisional
2014-F02,ORB,XNYS,provider,provider,failure,Antares 130,2014-10-29,provisional
2015-024,OA,XNYS,rival,tier3,failure,Soyuz-2-1A,2015-04-28,provisional
2015-F01,OA,XNYS,rival,tier3,failure,Proton-M/Briz-M,2015-05-18,provisional
2015-F02,OA,XNYS,rival,tier3,failure,Falcon 9,2015-06-29,provisional
2015-F03,OA,XNYS,rival,tier3,failure,Super Strypi,2015-11-04,provisional
2015-071,OA,XNYS,rival,tier3,failure,Soyuz-2-1V,2015-12-07,provisional
2016-F01,OA,XNYS,rival,tier3,failure,Chang Zheng 4C,2016-08-31,provisional
2016-062,OA,XNYS,provider,provider,success,Antares 230,2016-10-18,provisional
2016-F02,OA,XNYS,rival,tier3,failure,Soyuz-U-PVB,2016-12-01,provisional
2016-078,OA,XNYS,provider,provider,success,Pegasus XL,2016-12-15,provisional
2017-F01,OA,XNYS,rival,tier3,failure,SS-520,2017-01-17,provisional
2017-F02,OA,XNYS,rival,tier1,failure,Electron,2017-05-25,provisional
2017-035,OA,XNYS,rival,tier3,failure,Chang Zheng 3B,2017-06-19,provisional
2017-F03,OA,XNYS,rival,tier3,failure,Chang Zheng 5,2017-07-03,provisional
2017-050,OA,XNYS,provider,provider,success,Minotaur IV,2017-08-28,provisional
2017-051,OA,XNYS,rival,tier1,failure,PSLV-XL,2017-08-31,high
2017-068,OA,XNYS,provider,provider,success,Minotaur-C 3210,2017-11-01,provisional
2017-071,OA,XNYS,provider,provider,success,Antares 230,2017-11-13,provisional
2017-F05,OA,XNYS,rival,tier3,failure,Soyuz-2-1B,2017-11-28,provisional
2018-012,OA,XNYS,rival,tier3,failure,Ariane 5ECA,2018-01-26,provisional
2018-046,OA,XNYS,provider,provider,success,Antares 230,2018-05-21,provisional
2021-F05,ASTR,XNAS,rival,tier3,failure,Shuang Quxian 1,2021-08-03,provisional
2021-F06,ASTR,XNAS,rival,tier3,failure,GSLV Mk II,2021-08-12,provisional
2021-F07,ASTR,XNAS,provider,provider,failure,Astra Rocket 3.3,2021-08-30,provisional
2021-F08,ASTR,XNAS,rival,tier1,failure,Firefly Alpha,2021-09-03,provisional
2021-F09,ASTR,XNAS,rival,tier3,failure,Nuri,2021-10-21,provisional
2021-108,ASTR,XNAS,provider,provider,success,Astra Rocket 3.3,2021-11-22,provisional
2021-F10,ASTR,XNAS,rival,tier3,failure,Kuaizhou-1A,2021-12-15,provisional
2021-133,ASTR,XNAS,rival,tier3,failure,Angara A5/Persei,2021-12-27,provisional
2021-F11,ASTR,XNAS,rival,tier3,failure,Simorgh,2021-12-30,provisional
2021-F11,VORB,XNAS,rival,tier3,failure,Simorgh,2021-12-30,provisional
2022-003,VORB,XNAS,provider,provider,success,LauncherOne,2022-01-14,provisional
2022-F01,ASTR,XNAS,provider,provider,failure,Astra Rocket 3.3,2022-02-10,high
2022-F01,VORB,XNAS,rival,tier1,failure,Astra Rocket 3.3,2022-02-10,high
2022-026,ASTR,XNAS,provider,provider,success,Astra Rocket 3.3,2022-03-15,provisional
2022-F02,ASTR,XNAS,rival,tier3,failure,Shuang Quxian 1,2022-05-13,provisional
2022-F02,VORB,XNAS,rival,tier3,failure,Shuang Quxian 1,2022-05-13,provisional
2022-F03,ASTR,XNAS,provider,provider,failure,Astra Rocket 3.3,2022-06-13,provisional
2022-F03,VORB,XNAS,rival,tier1,failure,Astra Rocket 3.3,2022-06-13,provisional
2022-074,VORB,XNAS,provider,provider,success,LauncherOne,2022-07-05,provisional
2022-U02,VORB,XNAS,rival,tier3,failure,SSLV,2022-08-08,provisional
2022-F04,VORB,XNAS,rival,tier3,failure,Epsilon,2022-10-12,provisional
2022-F05,VORB,XNAS,rival,tier3,failure,Zhuque-2,2022-12-14,provisional
2022-F06,VORB,XNAS,rival,tier3,failure,Vega C,2022-12-21,provisional
2023-F01,VORB,XNAS,provider,provider,failure,LauncherOne,2023-01-10,provisional
2023-F02,VORB,XNAS,rival,tier1,failure,RS1,2023-01-11,provisional
2023-F10,VORB,XNAS,rival,tier3,failure,Qaem-100,2023-03-06,provisional
2023-F03,VORB,XNAS,rival,tier3,failure,H3-22S,2023-03-07,provisional
2023-F04,VORB,XNAS,rival,tier1,failure,Terran 1,2023-03-23,provisional"""


# ------------------------------------------------------------------ pure calculations (no WRDS needed)
def market_model(est_r: np.ndarray, est_m: np.ndarray):
    n = len(est_r)
    if n >= MIN_OBS:
        X = np.column_stack([np.ones(n), est_m])
        (a, b), *_ = np.linalg.lstsq(X, est_r, rcond=None)
        res = est_r - (a + b * est_m)
        return "market_model", float(a), float(b), float(np.sqrt(res @ res / (n - 2))), res
    if n >= MIN_FALLBACK:
        res = est_r - est_m
        return "market_adjusted_fallback", 0.0, 1.0, float(np.std(res, ddof=1)), res
    return None, None, None, None, None


def event_stats(sessions: pd.DatetimeIndex, r: pd.Series, m: pd.Series, day0, listing_start=None):
    """Same arithmetic as pipeline/eventstudy.py: build_firm_event, abnormal and car."""
    d0 = pd.Timestamp(day0)
    k = sessions.searchsorted(d0)                    # first session on or after day 0
    if k >= len(sessions):
        return None
    if listing_start:
        r = r[r.index > pd.Timestamp(listing_start)]
    lo, hi = EST_WINDOW
    est_days = sessions[max(k + lo, 0): k + hi + 1]
    joint = pd.concat([r.reindex(est_days), m.reindex(est_days)], axis=1, keys=["r", "m"]).dropna()
    model, a, b, sigma, res = market_model(joint["r"].to_numpy("float64"), joint["m"].to_numpy("float64"))
    if model is None:
        return None
    rel = np.arange(PATH[0], PATH[1] + 1)
    rel = rel[(k + rel >= 0) & (k + rel < len(sessions))]
    ev_days = sessions[k + rel]
    ar = r.reindex(ev_days).to_numpy("float64", na_value=np.nan) - (a + b * m.reindex(ev_days).to_numpy("float64", na_value=np.nan))
    out = {"day0_used": sessions[k].date().isoformat(), "model": model, "est_obs": int(len(joint)), "sigma": sigma}
    T, mbar = len(joint), float(joint["m"].mean())
    sxx = float(np.sum((joint["m"].to_numpy("float64") - mbar) ** 2))
    for name, (w0, w1) in WINDOWS.items():
        mask = (rel >= w0) & (rel <= w1)
        L = int(mask.sum())
        if L != w1 - w0 + 1 or np.isnan(ar[mask]).any():
            out[f"car_{name}"], out[f"var_{name}"] = np.nan, np.nan
            continue
        if model == "market_model":
            sw = float(np.sum(m.reindex(ev_days).to_numpy("float64", na_value=np.nan)[mask] - mbar))
            var = sigma ** 2 * (L + L ** 2 / T + sw ** 2 / sxx)
        else:
            var = sigma ** 2 * L
        out[f"car_{name}"], out[f"var_{name}"] = float(ar[mask].sum()), float(var)
    for t, v in zip(rel, ar):
        out[f"ar_{'m' if t < 0 else 'p'}{abs(t)}"] = float(v) if np.isfinite(v) else np.nan
    return out, pd.Series(res, index=joint.index), set(ev_days)


# ------------------------------------------------------------------ WRDS access
def connect():
    import wrds
    return wrds.Connection()


def permnos(db) -> dict:
    out = {}
    for tk, f in FIRMS.items():
        if tk in PERMNO_OVERRIDE:
            out[tk] = int(PERMNO_OVERRIDE[tk]); continue
        start = f["listing_start"] or "1990-01-01"
        q = f"""select distinct permno, ticker, comnam, namedt, nameenddt from crsp.stocknames
                where ticker = '{tk}' and nameenddt >= '{start}' and namedt <= '{f["end"]}'"""
        df = db.raw_sql(q)
        if df.empty:
            sys.exit(f"No CRSP security found for {tk}. Look it up and set PERMNO_OVERRIDE.")
        print(f"{tk}: candidates\n{df.to_string(index=False)}")
        if df["permno"].nunique() != 1:
            sys.exit(f"Several PERMNOs for {tk}: choose one and set PERMNO_OVERRIDE.")
        out[tk] = int(df["permno"].iloc[0])
    return out


def load(db, pmap):
    plist = ",".join(str(p) for p in pmap.values())
    tables = {}
    try:                                            # legacy format (complete through December 2024)
        ret = db.raw_sql(f"select permno, date, ret from crsp.dsf where permno in ({plist}) "
                         f"and date between '1998-01-01' and '2024-12-31'", date_cols=["date"])
        dl = db.raw_sql(f"select permno, dlstdt as date, dlret from crsp.dsedelist where permno in ({plist})", date_cols=["date"])
        idx = db.raw_sql("select date, sprtrn from crsp.dsi where date between '1998-01-01' and '2024-12-31'", date_cols=["date"])
        tables = {"stock": "crsp.dsf", "delist": "crsp.dsedelist", "index": "crsp.dsi"}
    except Exception as err:                        # new CIZ format
        print(f"Legacy tables not available ({err}); trying the CIZ tables.")
        try:
            ret = db.raw_sql(f"select permno, dlycaldt as date, dlyret as ret from crsp.dsf_v2 where permno in ({plist}) "
                         f"and dlycaldt between '1998-01-01' and '2024-12-31'", date_cols=["date"])
        except Exception:
            sys.exit("Could not read CRSP daily stock data (crsp.dsf or crsp.dsf_v2). Please send Nahian the error above.")
        dl = pd.DataFrame(columns=["permno", "date", "dlret"])          # CIZ folds delisting returns into dlyret
        try:
            idx = db.raw_sql("select date, sprtrn from crsp.dsi where date between '1998-01-01' and '2024-12-31'", date_cols=["date"])
        except Exception:
            sys.exit("Could not read the S&P 500 return (crsp.dsi sprtrn). Please send Nahian the error above.")
        tables = {"stock": "crsp.dsf_v2", "delist": "included in dlyret", "index": "crsp.dsi"}
    # WRDS returns pandas nullable dtypes (Float64, Int64); convert to plain numpy types
    ret, dl, idx = ret.copy(), dl.copy(), idx.copy()
    ret = ret.assign(permno=pd.to_numeric(ret["permno"]).astype("int64"),
                     ret=pd.to_numeric(ret["ret"], errors="coerce").astype("float64"),
                     date=pd.to_datetime(ret["date"]))
    dl = dl.assign(permno=pd.to_numeric(dl["permno"]).astype("int64"),
                   dlret=pd.to_numeric(dl["dlret"], errors="coerce").astype("float64"),
                   date=pd.to_datetime(dl["date"]))
    for _, d in dl.dropna(subset=["dlret"]).iterrows():   # compound the delisting return into that day's return
        hit = (ret["permno"] == d["permno"]) & (ret["date"] == d["date"])
        if hit.any():
            ret.loc[hit, "ret"] = (1 + ret.loc[hit, "ret"].fillna(0)) * (1 + d["dlret"]) - 1
        else:
            ret = pd.concat([ret, pd.DataFrame([{"permno": int(d["permno"]), "date": d["date"], "ret": float(d["dlret"])}])], ignore_index=True)
    idx = idx.assign(sprtrn=pd.to_numeric(idx["sprtrn"], errors="coerce").astype("float64"),
                     date=pd.to_datetime(idx["date"]))
    return ret, idx, tables


def main():
    events = pd.read_csv(io.StringIO(EVENTS_CSV))
    db = connect()
    pmap = permnos(db)
    ret, idx, tables = load(db, pmap)
    sessions = pd.DatetimeIndex(sorted(idx["date"].unique()))       # US trading days
    m = idx.set_index("date")["sprtrn"]
    series = {tk: ret[ret["permno"] == p].set_index("date")["ret"].sort_index() for tk, p in pmap.items()}
    rows, resid, evdays = [], {}, {}
    for _, e in events.iterrows():
        tk = e["ticker"]
        st = event_stats(sessions, series[tk], m, e["day0"], FIRMS[tk]["listing_start"])
        key = f"{e['launch_tag']}|{tk}|{e['role']}"
        base = {k: e[k] for k in ("launch_tag", "ticker", "role", "tier", "outcome", "lv_type", "day0", "disclosure_confidence")}
        if st is None:
            rows.append({**base, "permno": pmap[tk], "model": "dropped (too few returns)"}); continue
        out, res, days = st
        rows.append({**base, "permno": pmap[tk], **out})
        resid[key], evdays[key] = res, (pd.Timestamp(out["day0_used"]), days)
    fe = pd.DataFrame(rows)
    pairs = []
    keys = list(resid)
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            di, dj = evdays[keys[i]][0], evdays[keys[j]][0]
            if abs((di - dj).days) > PAIR_GAP_DAYS:
                continue
            both = pd.concat([resid[keys[i]], resid[keys[j]]], axis=1, join="inner").dropna()
            same = keys[i].split("|")[1] == keys[j].split("|")[1]
            rc = 1.0 if same else (float(np.corrcoef(both.iloc[:, 0], both.iloc[:, 1])[0, 1]) if len(both) >= 30 else 0.0)
            pairs.append({"key_i": keys[i], "key_j": keys[j], "resid_corr": rc, "common_est_days": len(both),
                          "common_event_days": len(evdays[keys[i]][1] & evdays[keys[j]][1])})
    banned = {"prc", "price", "vol", "shrout", "ret", "retx", "alpha", "beta", "cfacpr"}
    assert not banned & {c.lower() for c in fe.columns}, "refusing to write raw data columns"
    fe.to_csv("tminus_crsp_firm_events.csv", index=False)
    pd.DataFrame(pairs).to_csv("tminus_crsp_pairs.csv", index=False)
    info = {"script_version": VERSION, "run_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "permnos": pmap, "crsp_tables": tables, "benchmark": "crsp.dsi sprtrn (S&P 500)",
            "events": len(fe), "events_with_car": int(fe["car_primary"].notna().sum()) if "car_primary" in fe else 0,
            "pairs": len(pairs), "contains_raw_data": False}
    with open("tminus_crsp_run_info.json", "w") as f:
        json.dump(info, f, indent=2)
    print(json.dumps(info, indent=2))
    print("Done. Please check the three tminus_crsp_* files, then send them.")


if __name__ == "__main__":
    main()
