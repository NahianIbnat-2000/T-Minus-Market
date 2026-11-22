# T-Minus Markets

**When a rocket blows up, who loses money, and does anyone win?**

An event study of stock market reactions to orbital launch failures since 2000,
with an interactive website (later phases). Author: Nahian Ibnat.

Launch data: GCAT (J. McDowell, planet4589.org/space/gcat), CC-BY.

---

## Website (Phases 4 and 5)

Static pages, all built by one command, ready for GitHub Pages (branch master, folder root):

| File | What it is |
| --- | --- |
| `index.html` | The article: one-page summary with the key numbers, method, and links (the front door) |
| `site/index.html` | The interactive report: five stages and four tools (Failure Timeline, Expected vs Actual, Event Study Lab, Placebo Simulator) |
| `case-study.html` | The case study: full write-up with research questions, figures, earlier work, limits, FAQ and references |
| `case-study.pdf` | The case study typeset with LaTeX (Times New Roman 12 pt), from the same text as the web page. Needs a LaTeX install (MiKTeX on Windows); without one, step 08 still writes `casestudy/` for Overleaf |
| `casestudy/` | `case-study.tex` and its four figures (vector PDFs) |
| `og.png` | Link-preview image for LinkedIn (needs matplotlib; skipped if missing) |

```
python pipeline/07_export_site_data.py   # results -> site/data/*.json
python pipeline/08_build_html.py         # -> index.html, site/index.html, case-study.html/.pdf, og.png, .nojekyll
```

Every number on every page comes from `site/data/` (derived statistics only). Edit text and code in
`site/src/`, the report frame in `site/template.html`, the article in `pipeline/landing.py`, the case study in `pipeline/casestudy.py`, and links in
`site/site_meta.json` (set `repo_url` only once the repository is public). Never edit the generated HTML by hand.
Optional checks with Node.js: `cd site && npm test`.

## Phase 3: website data (complete)

After steps 05 and 06:

```bash
python pipeline/07_export_site_data.py
```

This writes `site/data/` (see `docs/SITE_DATA.md`). Only derived statistics are exported: no raw
prices or returns. The browser module `site/src/stats/eventstudy.js` re-runs the primary test on any
subset of events and is checked against Python by `tests/test_phase3_parity.py` (needs Node.js;
the test is skipped without it).

## Phase 2: event study (complete)

Phase 1 is complete and the analysis plan is frozen (`docs/ANALYSIS_PLAN.md`).
Phase 2 runs the plan exactly. Run it **once**, after steps 01 to 04:

```bash
python pipeline/05_event_study.py
```

| Output | What it is |
| --- | --- |
| `reports/05_results.md` | Primary result (H2), all robustness checks R1 to R9, provider case series, exploratory H3 |
| `data/processed/results.json` | Every number, for the website and the paper |
| `data/processed/firm_event_cars.csv` | One row per firm-event: model, beta, sigma, CARs for all windows |

Then the exploratory confounding check (designed after results; never replaces H2):

```bash
python pipeline/06_confounding_sensitivity.py
```

It re-runs the primary test without rival events flagged in `data/manual/confounded_events.csv`
(E1 confounded, E2 plus possibly confounded, E3 every flag) and writes `reports/06_confounding_sensitivity.md`.

**After this run, do not change anything in `pipeline/config.py` or `data/manual/`.**
A data-error fix is allowed only with a dated entry in the plan's change log, and results are then
reported before and after the fix.

The tests include known-answer checks: a planted +3% rival effect is recovered, and with correlated
rivals and no true effect the primary test rejects about 5% of the time while a plain t-test rejects about 21%.

## Phase 1: feasibility (complete)

Phase 1 answers one question: **is there enough usable data for a credible test?**
It never computes an abnormal return inside an event window, so nothing you see
here can bias the sample rules. (A test checks this: `test_coverage_never_reads_event_window_values`.)

### Setup (Windows, Git Bash)

```bash
cd t-minus-markets
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
python -m pytest -q tests          # should print: 41 passed
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

## Reproduction and verification

| Step | Command | Needs |
| --- | --- | --- |
| 1-4 | `python pipeline/01_ingest_launches.py` ... `04_check_coverage.py` | internet (GCAT, Yahoo) |
| 5 | `python pipeline/05_event_study.py` | prices (local only) |
| 6 | `python pipeline/06_confounding_sensitivity.py` | prices; exploratory |
| 9 | `python pipeline/09_audit_exploratory.py` | prices; exploratory (R9b) |
| 10 | `python pipeline/10_crsp_supplement.py` | `data/crsp/` from the WRDS run (`wrds/tminus_crsp_extract.py`, not in git); CRSP supplement, plan v1.2 |
| 7 | `python pipeline/07_export_site_data.py` | derived statistics only |
| 8 | `python pipeline/08_build_html.py` | matplotlib; LaTeX for the PDF |
| check | `python audit/verify_published.py` | published data only; recomputes every statistic independently; writes `audit/VERIFICATION.md` |
| check | `python audit/check_consistency.py` | article, paper and report agree with results.json (also run by step 08) |
| tests | `python -m pytest tests` and `cd site && npm test` | |

Prices are never published (Yahoo licensing). Anyone can verify every test statistic, interval and p-value from
the published derived data with `audit/verify_published.py`; re-estimating the CARs themselves needs the prices.
`data/processed/firm_event_cars.csv` holds alphas and betas and is never committed.

`docs/ANALYSIS_PLAN.md` is the internal record of the rules fixed before results and of every later change. It is not published
on the website; the working paper reproduces its commit record (Appendix G).
