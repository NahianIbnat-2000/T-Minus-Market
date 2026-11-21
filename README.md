# T-Minus Markets

**When a rocket blows up, who loses money, and does anyone win?**

An event study of stock market reactions to orbital launch failures since 2000,
with an interactive website (later phases). Author: Nahian Ibnat.

Launch data: GCAT (J. McDowell, planet4589.org/space/gcat), CC-BY.

---

## Phase 1: feasibility (current)

Phase 1 answers one question: **is there enough usable data for a credible test?**
It never computes an abnormal return inside an event window, so nothing you see
here can bias the sample rules. (A test checks this: `test_coverage_never_reads_event_window_values`.)

### Setup (Windows, Git Bash)

```bash
cd t-minus-markets
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
python -m pytest -q tests          # should print: 29 passed
```

### Run

```bash
python pipeline/01_ingest_launches.py     # downloads GCAT, builds failure list
python pipeline/02_map_firms.py           # links launches to listed firms, rival tiers
python pipeline/03_pull_prices.py         # yfinance prices for mapped firms + benchmarks
python pipeline/04_check_coverage.py      # coverage, clusters, power, gate decision
```

If the GCAT download fails, save
`https://planet4589.org/space/gcat/tsv/launch/launch.tsv` by hand into
`data/raw/launch.tsv` and run step 01 with `--offline`.

### Read the results

| File | What it tells you |
| --- | --- |
| `reports/01_ingest_summary.md` | Failures by year, vehicle and agency; the sample funnel |
| `data/interim/exclusion_log_01.csv`, `_02.csv` | Every dropped launch and the specific reason |
| `data/interim/price_download_log.csv` | Which tickers Yahoo had, and from when |
| `data/interim/price_quality_issues.csv` | Splits, huge returns, bad prices to check by hand |
| `reports/04_feasibility_report.md` | **The gate decision**, MDE at the real sample size |

---

## Your research checklist (the manual part)

The pipeline is only as good as three hand-made files in `data/manual/`.
**Every row in `firm_map.csv` is currently `unverified`: the candidates and dates
are from memory and must be checked.** The gate result is not final until they are.

1. **Run step 01 first**, then open `reports/01_ingest_summary.md`. Look at the
   failure list by vehicle. That tells you which firms are worth researching.
2. **`firm_map.csv`**: for each candidate row:
   - check the regex in `lv_pattern` matches the exact GCAT `LV_Type` spelling
     (step 02's exclusion log lists failures with `no_firm_map_match`);
   - verify listing start/end and ownership dates from a primary source
     (company filings, exchange notices); fill `source_url`, `source_date`;
   - set `launch_exposure` from revenue share evidence: `pure_play`, `major` or `minor`;
   - set `verification_status` to `verified`, or `rejected` to drop a row.
   Split a row into dated rows when ownership changed (for example ULA in 2006).
3. **`vehicle_segments.csv`**: segment for every vehicle that failed, including
   private and state rockets (needed to find their listed rivals). Rule:
   small < 2 t to LEO, medium 2 to 10 t, heavy > 10 t. These are v0 guesses.
4. **`disclosure_times.csv`**: for each failure that survives step 04, the UTC
   time of the first public report of the failure, a source and a confidence
   (`high`, `medium`, `low`). Without a row, the launch time is used and the
   event is flagged `provisional`. Example of a well-sourced case: the 2014
   Antares failure happened at 6:22 pm EDT (22:22 UTC), after the New York close.
5. **`rival_overrides.csv`** (optional): Tier 2 rivals with documented
   competition for the same contracts, each with a source.

**Do all of this before Phase 2.** Rival tiers and timing must be fixed before
any abnormal return is computed.

### Known data risks

- **Delisted tickers** (Orbital Sciences, Orbital ATK, Astra, Virgin Orbit) are
  often missing from Yahoo. Step 04 reports them as `no_price_data_for_ticker`.
  Options: a university database (CRSP via a library), or drop and log them.
- **Redistribution**: check Yahoo's terms before publishing prices or returns
  on the website (audit risk 8).

---

## Fixed rules (from the audit; change only in `pipeline/config.py`)

| Rule | Value |
| --- | --- |
| Failure | GCAT success score < 0.75 (McDowell's own pass/fail line) |
| Pad explosions (code E) | Separate set, never pooled |
| Day 0 | Disclosure in session = that day; otherwise next session (real exchange calendars) |
| Estimation window | [-250, -30] trading days; 100+ obs = market model, 30 to 99 = market-adjusted (flagged) |
| Primary window | CAR[0, +1]; [-1, +3] robustness; [0, +20] descriptive |
| Returns | Simple returns from adjusted close |
| Tier 1 rival | Listed, pure-play or major exposure, same segment, vehicle flew in the 730 days before |
| Tier 3 | Any other active listed launch firm (descriptive only) |
| Independence | Failures sharing a firm within 5 sessions form one cluster |
| Gate | Providers: >= 10 independent failures AND MDE <= 5% (t-based). Rivals: >= 8 independent clusters with a Tier 1/2 rival |
| If the gate fails | Publish as a documented case series |
