import numpy as np
import pandas as pd
import pytest

import config as C
from coverage import assign_clusters, check_one, mde, timing_sensitive
from eventtime import day_zero
from gcat import jd_to_utc, parse_launch_code, read_launch_tsv, vague_date_to_utc
from ingest import classify
from mapping import build_firm_events, load_firm_map


# ------------------------------------------------------------ GCAT parsing
@pytest.mark.parametrize("code,cat,res,score", [
    ("OS", "O", "S", 1.0), ("OF", "O", "F", 0.0), ("OS85", "O", "S", 0.85),
    ("OF40", "O", "F", 0.40), ("OE", "O", "E", None), ("OU", "O", "U", None), ("DS", "D", "S", 1.0),
])
def test_parse_launch_code(code, cat, res, score):
    p = parse_launch_code(code)
    assert (p["category"], p["result"], p["score"]) == (cat, res, score)


def test_parse_launch_code_rejects_garbage():
    assert not parse_launch_code("Q?")["code_ok"]
    assert not parse_launch_code(None)["code_ok"]


def test_jd_round_trip():
    assert jd_to_utc("2456959.432870") == pd.Timestamp("2014-10-28 22:23:20", tz="UTC")


# ------------------------------------------------------------ classification
def test_classify_funnel_and_sets(gcat_file):
    raw = read_launch_tsv(gcat_file)
    orbital, failures, ground, excl, funnel = classify(raw)
    assert set(failures["Launch_Tag"]) == {"2014-F01", "2015-F01", "2020-F01", "2022-F01", "2023-F01", "2023-F02"}
    assert list(ground["Launch_Tag"]) == ["2016-E01"]
    assert orbital.set_index("Launch_Tag").loc["2023-002", "outcome"] == "partial_success"
    reasons = dict(zip(excl["launch_tag"], excl["reason"]))
    assert reasons["2018-U01"] == "outcome_unknown"
    assert reasons["2019-B01"] == "unparseable_launch_code"
    assert "1999-001" not in set(orbital["Launch_Tag"])
    assert "2019-S01" not in set(orbital["Launch_Tag"])


# ------------------------------------------------------------ event time
def test_day_zero_after_us_close_moves_to_next_session():
    assert day_zero(pd.Timestamp("2014-10-28 22:22", tz="UTC"), "XNYS") == pd.Timestamp("2014-10-29")


def test_day_zero_during_session_is_same_day():
    assert day_zero(pd.Timestamp("2014-10-28 15:00", tz="UTC"), "XNYS") == pd.Timestamp("2014-10-28")


def test_day_zero_weekend_moves_to_monday():
    assert day_zero(pd.Timestamp("2023-09-16 12:00", tz="UTC"), "XNAS") == pd.Timestamp("2023-09-18")


def test_day_zero_tokyo_uses_local_session():
    # 2023-03-07 01:37 UTC = 10:37 JST, Tokyo open -> same day in Tokyo
    assert day_zero(pd.Timestamp("2023-03-07 01:37", tz="UTC"), "XTKS") == pd.Timestamp("2023-03-07")
    # Same instant is before the New York open -> NY day 0 is that NY session
    assert day_zero(pd.Timestamp("2023-03-07 01:37", tz="UTC"), "XNYS") == pd.Timestamp("2023-03-07")


# ------------------------------------------------------------ point-in-time mapping and rivals
def test_mapping_point_in_time_and_tiers(gcat_file, firm_map_file, segments):
    orbital, failures, *_ = classify(read_launch_tsv(gcat_file))
    fm = load_firm_map(firm_map_file)
    assert "REJ" not in set(fm["ticker"])
    ev, excl = build_firm_events(orbital, failures, fm, segments)

    prov = ev[(ev["role"] == "provider") & (ev["outcome"] == "failure")]
    # 2020 Electron failure happened before the listing -> no provider event, logged
    assert "2020-F01" not in set(prov["launch_tag"])
    assert (excl.set_index("launch_tag").loc["2020-F01", "reason"]) == "provider_not_listed_or_not_owner_on_date"
    # 2023 Electron failure maps to RKLB; 2014 Antares to ORB (before its listing end)
    assert set(prov[prov["launch_tag"] == "2023-F01"]["ticker"]) == {"RKLB"}
    assert set(prov[prov["launch_tag"] == "2014-F01"]["ticker"]) == {"ORB"}
    # Falcon 9 failure: private provider, logged
    assert excl.set_index("launch_tag").loc["2015-F01", "reason"] == "no_firm_map_match"

    riv = ev[ev["role"] == "rival"]
    # Vega (small) failure in Dec 2022: Electron flew in Jun 2022 and RKLB was listed -> Tier 1
    v = riv[riv["launch_tag"] == "2022-F01"].set_index("ticker")["tier"].to_dict()
    assert v.get("RKLB") == "tier1"
    # Electron failure in 2023: AVIO is not active (no Vega launch in lookback after the 2022 failure? it failed,
    # but a failed launch still counts as activity) -> Tier 1 small-segment rival
    e = riv[riv["launch_tag"] == "2023-F01"].set_index("ticker")["tier"].to_dict()
    assert e.get("AVIO.MI") == "tier1"
    assert "RKLB" not in e  # a firm is never its own rival
    # Boeing has minor exposure -> never Tier 1
    assert not ((riv["ticker"] == "BA") & (riv["tier"] == "tier1")).any()
    # Successes of mapped vehicles are kept as the comparison group
    succ = ev[(ev["role"] == "provider") & (ev["outcome"] != "failure")]
    assert "2022-001" in set(succ["launch_tag"])  # Electron success in 2022 after listing
    assert "2021-001" not in set(succ["launch_tag"])  # before listing


def test_rival_activity_uses_only_pre_event_launches(gcat_file, firm_map_file, segments):
    orbital, failures, *_ = classify(read_launch_tsv(gcat_file))
    fm = load_firm_map(firm_map_file)
    # Drop every Electron launch before the Vega failure: RKLB must stop being a rival
    o2 = orbital[~((orbital["LV_Type"] == "Electron") & (orbital["launch_utc"] < pd.Timestamp("2022-12-21", tz="UTC")))]
    ev, _ = build_firm_events(o2, failures, fm, segments)
    riv = ev[(ev["role"] == "rival") & (ev["launch_tag"] == "2022-F01")]
    assert "RKLB" not in set(riv["ticker"])


# ------------------------------------------------------------ coverage
def _event(ticker="ORB", exch="XNYS", when="2014-10-28 22:22"):
    return pd.Series({"ticker": ticker, "exchange": exch, "disclosure_utc": pd.Timestamp(when, tz="UTC")})


def test_coverage_sigma_recovers_true_noise(synthetic_returns):
    b = synthetic_returns[synthetic_returns["ticker"] == "^GSPC"][["date", "ret"]]
    out = check_one(_event(), synthetic_returns, b)
    assert out["coverage_reason"] is None
    assert out["day0"] == pd.Timestamp("2014-10-29")
    assert out["model"] == "market_model" and out["est_obs"] == 221
    assert abs(out["sigma"] - 0.03) < 0.004


def test_coverage_flags_missing_primary_window_price(synthetic_returns):
    r = synthetic_returns[~((synthetic_returns["ticker"] == "ORB") &
                            (synthetic_returns["date"] == pd.Timestamp("2014-10-30")))]
    b = r[r["ticker"] == "^GSPC"][["date", "ret"]]
    assert check_one(_event(), r, b)["coverage_reason"] == "missing_price_in_primary_window"


def test_coverage_short_history_uses_flagged_fallback(synthetic_returns):
    r = synthetic_returns[~((synthetic_returns["ticker"] == "ORB") &
                            (synthetic_returns["date"] < pd.Timestamp("2014-07-01")))]
    b = r[r["ticker"] == "^GSPC"][["date", "ret"]]
    out = check_one(_event(), r, b)
    assert out["model"] == "market_adjusted_fallback" and 30 <= out["est_obs"] < C.EST_MIN_OBS


def test_coverage_never_reads_event_window_values(synthetic_returns):
    """Changing event-window returns must not change anything step 04 computes."""
    b = synthetic_returns[synthetic_returns["ticker"] == "^GSPC"][["date", "ret"]]
    base = check_one(_event(), synthetic_returns, b)
    shocked = synthetic_returns.copy()
    mask = (shocked["ticker"] == "ORB") & shocked["date"].between("2014-10-28", "2014-11-30")
    shocked.loc[mask, "ret"] = -0.4
    after = check_one(_event(), shocked, b)
    assert base["sigma"] == after["sigma"] and base["est_obs"] == after["est_obs"]


def test_clusters_join_close_failures_sharing_a_firm():
    u = pd.DataFrame({"launch_tag": ["A", "B", "C"], "ticker": ["X", "X", "X"], "exchange": ["XNYS"] * 3,
                      "day0": pd.to_datetime(["2023-09-18", "2023-09-20", "2023-12-01"])})
    cl = assign_clusters(u)
    assert cl.iloc[0] == cl.iloc[1] and cl.iloc[2] != cl.iloc[0]


def test_mde_formula_uses_t_critical_values():
    from scipy.stats import t
    m = t.ppf(0.975, 9) + t.ppf(0.80, 9)
    assert mde(0.04, 10) == pytest.approx(m * 0.04 * np.sqrt(2) / np.sqrt(10))
    assert mde(0.04, 4) > 2.8 * 0.04 * np.sqrt(2) / 2   # small samples are penalised
    assert np.isnan(mde(0.04, 1))


def test_coverage_drops_prices_before_listing(synthetic_returns):
    """Shell (pre-listing) prices must not enter the estimation window."""
    b = synthetic_returns[synthetic_returns["ticker"] == "^GSPC"][["date", "ret"]]
    ev = _event()
    ev["listing_start"] = pd.Timestamp("2014-07-01")
    out = check_one(ev, synthetic_returns, b)
    assert out["model"] == "market_adjusted_fallback" and out["est_obs"] < C.EST_MIN_OBS


def test_same_size_different_market_is_not_tier1(gcat_file, firm_map_file, segments):
    """A Chinese small-rocket failure must not make Rocket Lab a Tier 1 rival."""
    orbital, failures, *_ = classify(read_launch_tsv(gcat_file))
    extra = pd.DataFrame([{"Launch_Tag": "2023-F09", "launch_utc": pd.Timestamp("2023-01-10 08:00", tz="UTC"),
                           "LV_Type": "Zhuque-2", "outcome": "failure", "score": 0.0}])
    orbital = pd.concat([orbital, extra], ignore_index=True)
    failures = orbital[orbital["outcome"] == "failure"]
    ev, _ = build_firm_events(orbital, failures, load_firm_map(firm_map_file), segments)
    riv = ev[(ev["role"] == "rival") & (ev["launch_tag"] == "2023-F09")].set_index("ticker")["tier"].to_dict()
    assert riv.get("RKLB") == "tier3"


@pytest.mark.parametrize("text,expected", [
    ("2014 Oct 28 2222:38", pd.Timestamp("2014-10-28 22:22:38", tz="UTC")),
    ("2023 Sep 19 0655", pd.Timestamp("2023-09-19 06:55", tz="UTC")),
    ("2001 Jul 12", None),            # no time of day -> fall back to JD
    ("2001 Jul 12 2158?", None),      # uncertain -> fall back to JD
])
def test_vague_date_parsing(text, expected):
    assert vague_date_to_utc(text) == expected


def test_timing_sensitivity_flags_launches_near_the_close():
    # 20:00 UTC launch, NY closes 21:00 UTC in February: +3 h moves day 0 -> sensitive
    assert timing_sensitive(pd.Timestamp("2022-02-10 20:00", tz="UTC"), "XNAS")
    # Saturday launch: any shift lands on Monday -> robust
    assert not timing_sensitive(pd.Timestamp("2021-05-15 11:17", tz="UTC"), "XMIL")
