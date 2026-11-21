# Data dictionary (Phase 1)

Three kinds of field are kept apart: **source facts** (from GCAT or Yahoo),
**researcher classifications** (hand-made, in `data/manual/`) and
**derived values** (computed by the pipeline).

## data/interim/orbital_launches.csv (source facts + derived outcome)

| Field | Type | Kind | Meaning | Rule |
| --- | --- | --- | --- | --- |
| Launch_Tag | str | source | GCAT launch ID (COSPAR for orbital) | unique; duplicates logged |
| launch_utc | datetime UTC | derived | From GCAT Launch_JD (first motion) | rows without a valid JD are excluded and logged |
| LV_Type, LV_Variant | str | source | Rocket type and variant | used for firm matching |
| Launch_Agency | str | source | GCAT org code for launch services | |
| LaunchCode | str | source | Category letter + result letter + optional score | parsed by `gcat.parse_launch_code` |
| score | float 0-1 | derived | Success fraction; S=1, F=0, digits = score | missing for U, Z, A, E |
| outcome | str | derived | failure (<0.75), partial_success (0.75-0.99), success (1) | McDowell's threshold |

## data/manual/firm_map.csv (researcher classification)

| Field | Meaning | Permitted values |
| --- | --- | --- |
| map_id | Stable row ID | FMnnn |
| lv_pattern | Regex on GCAT LV_Type | |
| firm_name, entity_role | Listed entity and its role | manufacturer, operator, manufacturer_operator, corporate_parent |
| ticker, exchange | Yahoo ticker and exchange_calendars code | XNYS, XNAS, XMIL, XPAR, XETR, XTKS, XLON |
| listing_start / listing_end | Dates the security traded | blank = open-ended |
| relation_start / relation_end | Dates the firm had this role for the vehicle | blank = open-ended |
| segment | Payload class of the vehicle in this row | small, medium, heavy |
| control_type | Ownership type | listed_private_owned, state_controlled_listed, diversified_parent |
| launch_exposure | Importance of launch to the firm | pure_play, major, minor |
| verification_status | Checked against a source? | unverified, verified, rejected |
| source_url, source_date, notes | Evidence | required when verified |

## data/interim/firm_events.csv (derived)

One row per launch x firm x role. `role` = provider or rival.
`tier` = provider, provider_minor_exposure, tier1, tier2, tier3.

## data/interim/coverage.csv (derived)

| Field | Meaning |
| --- | --- |
| disclosure_utc, disclosure_source, disclosure_confidence | Time used for day 0; `provisional` = launch time |
| day0 | First eligible session on the firm's exchange |
| est_obs | Estimation-window days with firm and benchmark returns |
| model | market_model (100+ obs) or market_adjusted_fallback (30-99) |
| sigma | Estimation-window residual std. dev. (daily) |
| coverage_reason | Why the firm-event is unusable; blank = usable |
| cluster | Independent cluster ID (failures only) |
