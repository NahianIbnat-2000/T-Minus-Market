"""Step 02 logic: point-in-time firm mapping and rival tiers.

All inputs are dated, and a relationship is used only if it was true on the
launch date. Rivals are defined from pre-event information only:
vehicle segment (manual file) + whether the rival's vehicle launched in the
ACTIVE_LOOKBACK_DAYS before the failure (from GCAT). No return data is read.
"""
from __future__ import annotations

import re

import pandas as pd

import config as C

FIRM_MAP_COLUMNS = [
    "map_id", "lv_pattern", "firm_name", "entity_role", "ticker", "exchange",
    "listing_start", "listing_end", "relation_start", "relation_end",
    "segment", "market", "control_type", "launch_exposure", "verification_status",
    "source_url", "source_date", "notes",
]
SEGMENT_COLUMNS = ["lv_pattern", "segment", "market", "valid_from", "valid_to", "notes"]
OVERRIDE_COLUMNS = ["launch_tag", "ticker", "tier", "source_url", "notes"]
PRIMARY_EXPOSURE = {"pure_play", "major"}


def _dates(df, cols):
    for c in cols:
        df[c] = pd.to_datetime(df[c].replace("", pd.NA), utc=True, errors="coerce")
    return df


def load_firm_map(path) -> pd.DataFrame:
    fm = pd.read_csv(path, dtype=str, keep_default_na=False)
    missing = [c for c in FIRM_MAP_COLUMNS if c not in fm.columns]
    if missing:
        raise ValueError(f"firm_map.csv missing columns: {missing}")
    fm = fm[fm["verification_status"] != "rejected"].copy()
    return _dates(fm, ["listing_start", "listing_end", "relation_start", "relation_end"])


def _valid_on(row, when: pd.Timestamp) -> bool:
    def inside(start, end):
        return (pd.isna(start) or start <= when) and (pd.isna(end) or when <= end)
    return inside(row["relation_start"], row["relation_end"]) and inside(row["listing_start"], row["listing_end"])


def _matches(pattern: str, lv_type: str) -> bool:
    return bool(re.search(pattern, lv_type or "", flags=re.IGNORECASE))


def segment_of(lv_type: str, segments: pd.DataFrame, when: pd.Timestamp | None = None):
    """(segment, market) of a vehicle on a date. First matching row whose dates cover `when` wins."""
    for _, s in segments.iterrows():
        if not _matches(s["lv_pattern"], lv_type):
            continue
        if when is not None:
            lo = pd.to_datetime(s.get("valid_from") or None, utc=True)
            hi = pd.to_datetime(s.get("valid_to") or None, utc=True)
            if (pd.notna(lo) and when < lo) or (pd.notna(hi) and when > hi):
                continue
        return s["segment"], s.get("market") or None
    return None, None


def providers_for(launch: pd.Series, fm: pd.DataFrame):
    """Rows of the firm map that matched the vehicle, split into valid on date / not valid."""
    hits = fm[fm["lv_pattern"].apply(lambda p: _matches(p, launch["LV_Type"]))]
    if hits.empty:
        return hits, hits
    valid = hits[hits.apply(lambda r: _valid_on(r, launch["launch_utc"]), axis=1).astype(bool)]
    return valid, hits


def active_patterns(orbital: pd.DataFrame, fm: pd.DataFrame, when: pd.Timestamp) -> set[str]:
    """lv_patterns whose vehicle launched in the lookback window before `when` (strictly before)."""
    lo = when - pd.Timedelta(days=C.ACTIVE_LOOKBACK_DAYS)
    recent = orbital[(orbital["launch_utc"] < when) & (orbital["launch_utc"] >= lo)]["LV_Type"].unique()
    return {p for p in fm["lv_pattern"].unique() if any(_matches(p, v) for v in recent)}


def build_firm_events(orbital, failures, fm, segments, overrides=None):
    orbital = orbital.copy()
    orbital["launch_utc"] = pd.to_datetime(orbital["launch_utc"], utc=True)
    rows, excl = [], []

    # --- provider events: failures and successes of mapped vehicles
    for _, L in orbital.iterrows():
        valid, hits = providers_for(L, fm)
        if L["outcome"] == "failure":
            if hits.empty:
                excl.append((L["Launch_Tag"], L["LV_Type"], "no_firm_map_match", "vehicle not linked to any listed firm"))
            elif valid.empty:
                excl.append((L["Launch_Tag"], L["LV_Type"], "provider_not_listed_or_not_owner_on_date",
                             "; ".join(hits["firm_name"].unique())))
        for _, F in valid.iterrows():
            rows.append(dict(launch_tag=L["Launch_Tag"], launch_utc=L["launch_utc"], lv_type=L["LV_Type"],
                             outcome=L["outcome"], role="provider",
                             tier="provider" if F["launch_exposure"] in PRIMARY_EXPOSURE else "provider_minor_exposure",
                             ticker=F["ticker"], exchange=F["exchange"], firm_name=F["firm_name"],
                             launch_exposure=F["launch_exposure"], control_type=F["control_type"],
                             verification_status=F["verification_status"], map_id=F["map_id"]))

    # --- rival events: failures only
    for _, L in failures.iterrows():
        when = pd.Timestamp(L["launch_utc"])
        when = when.tz_localize("UTC") if when.tzinfo is None else when
        seg, mkt = segment_of(L["LV_Type"], segments, when)
        if seg is None:
            excl.append((L["Launch_Tag"], L["LV_Type"], "no_segment_for_vehicle", "add to vehicle_segments.csv"))
        own, _ = providers_for(pd.Series({"LV_Type": L["LV_Type"], "launch_utc": when}), fm)
        own_tickers = set(own["ticker"])
        active = active_patterns(orbital, fm, when)
        for _, F in fm.iterrows():
            if F["ticker"] in own_tickers or F["lv_pattern"] not in active or not _valid_on(F, when):
                continue
            same_seg = seg is not None and F["segment"] == seg
            same_mkt = mkt is not None and F["market"] == mkt
            close = same_seg and same_mkt and F["launch_exposure"] in PRIMARY_EXPOSURE
            tier = "tier1" if close else "tier3"
            rows.append(dict(launch_tag=L["Launch_Tag"], launch_utc=when, lv_type=L["LV_Type"],
                             outcome="failure", role="rival", tier=tier, ticker=F["ticker"],
                             exchange=F["exchange"], firm_name=F["firm_name"],
                             launch_exposure=F["launch_exposure"], control_type=F["control_type"],
                             verification_status=F["verification_status"], map_id=F["map_id"]))

    ev = pd.DataFrame(rows)
    if not ev.empty:
        # a ticker counted as tier1 for an event is not also counted as tier3
        ev["_rank"] = ev["tier"].map({"provider": 0, "provider_minor_exposure": 0, "tier1": 1, "tier2": 2, "tier3": 3})
        ev = (ev.sort_values("_rank").drop_duplicates(["launch_tag", "ticker", "role"], keep="first")
                .drop(columns="_rank"))
    if overrides is not None and not overrides.empty and not ev.empty:
        for _, o in overrides.iterrows():
            m = (ev["launch_tag"] == o["launch_tag"]) & (ev["ticker"] == o["ticker"]) & (ev["role"] == "rival")
            ev.loc[m, "tier"] = o["tier"]
    excl_df = pd.DataFrame(excl, columns=["launch_tag", "lv_type", "reason", "detail"])
    return ev.sort_values(["launch_utc", "role", "ticker"]).reset_index(drop=True) if not ev.empty else ev, excl_df
