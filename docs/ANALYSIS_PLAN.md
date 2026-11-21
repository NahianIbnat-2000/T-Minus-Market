# Frozen Analysis Plan v1.0 (21 Nov 2026)


The numbers below are enforced by `pipeline/config.py`. Changing any of them after
abnormal returns are computed is a plan change and must be logged in the change log.

| Item | Locked value |
| --- | --- |
| Confirmatory test | H2: mean rival CAR[0,+1] = 0, two-sided, 5% |
| Primary test | BMP standardized test with Kolari-Pynnonen within-cluster correlation adjustment |
| Providers | Case series (4 failures) unless CRSP data gives >= 10 independent failures |
| Failure | GCAT score < 0.75, categories O and D, from 2000-01-01 |
| Tier 1 rival | listed, pure_play/major, same size class and customer market, flew in prior 730 days |
| Day 0 | first session at/after disclosure; sourced time if timing-sensitive |
| Model | market model, simple returns, local index benchmark |
| Estimation window | [-250, -30]; >=100 obs market model; 30-99 market-adjusted (flagged) |
| Windows | primary [0,+1]; robustness [-1,+3]; descriptive [0,+20] |
| Clusters | failures sharing a firm within 5 trading days |
| Robustness | R1 portfolio, R2 plain t, R3 rank (simulated p), R4 window, R5 timing, R6 fallback, R7 overlaps, R8 leave-one-firm-out, R9 placebo (seed 20261121) |

## Freeze record

Prespecified in git, not filed with an independent registry. Git timestamps are set by the author.

| Item | Commit | Time (+06:00) |
| --- | --- | --- |
| Plan v1.0 with the locked table (end of Phase 1) | `6e43dee` | 21 Nov 2026 20:13:38 |
| Phase 2 code; plan v1.0 frozen before results | `54393b2` | 21 Nov 2026 20:30:24 |
| First results (step 05) | `be71a52` | 21 Nov 2026 20:31:18 |

## Change log

| Date | Version | Change | Results seen? |
| --- | --- | --- | --- |
| 2026-11-21 | 1.0 | Plan frozen at end of Phase 1 | No |
| 2026-11-21 | 1.0 | Phase 2 run (05_event_study.py). No settings changed. Confounding-news check for provider failures added (docs/CONFOUNDING_NEWS.md); no events removed | Yes |
| 2026-11-21 | 1.0 | Added step 06, an EXPLORATORY confounding sensitivity (E1-E3) designed after results; flags in data/manual/confounded_events.csv. H2 unchanged | Yes |
| 2026-11-21 | 1.0 | Phase 3: site export (step 07) and browser module; derived statistics only (no raw returns). No analysis change | Yes |
| 2026-11-21 | 1.0 | Phase 4: website skeleton (five stages, anomaly cards, printed-figure charts); text generated from results. No analysis change | Yes |
| 2026-11-21 | 1.0 | Website rebuilt as one self-contained file (step 08, site/index.html); D3 and Vite removed; Methods moved into the page. Presentation only, no analysis change | Yes |
| 2026-11-21 | 1.0 | Website display fixes: provider chart anchored at T-1 close (values match cards); RKLB day -5 founder share-sale news noted (docs/CONFOUNDING_NEWS.md); card header and date format. Presentation only, no analysis change | Yes |
| 2026-11-21 | 1.0 | Phase 5 tool 1: Event Study Lab (re-runs the prespecified rival test on reader-chosen subsets; non-default choices labelled exploratory). Step 07 exports min_rival_clusters from config. No analysis change | Yes |
| 2026-11-21 | 1.0 | Phase 5 tool 2: Placebo Simulator (replays the R9 draws stored in results.json; same two-sided rule as analysis.py). No analysis change | Yes |
| 2026-11-21 | 1.0 | Phase 5 tool 3: Failure Timeline (all failures in three lanes, filter and search, detail card). Exclusion codes shown in plain language. Site test scanner rewritten as a tokenizer (it missed nested template strings). No analysis change | Yes |
| 2026-11-21 | 1.0 | Phase 5 tool 4: Expected vs Actual explorer (simulated example, labelled). Step 08 also builds the root article (index.html) and plan.html for GitHub Pages; links in site/site_meta.json. No analysis change | Yes |
| 2026-11-21 | 1.0 | Link-preview image (og.png) built from results; non-detectable result shown in neutral colour on the article and image. No analysis change | Yes |
| 2026-11-22 | 1.0 | Phase 6 changed from a working paper to a case study: case-study.html and case-study.pdf built by step 08 from results (literature, limits including delisted firms and the SpaceX listing). No analysis change | Yes |
| 2026-11-22 | 1.0 | Case study PDF now typeset with LaTeX (XeLaTeX, Times New Roman 12 pt) from the same text as case-study.html; links point to index.html files so pages work when opened from disk; private plan link removed. No analysis change | Yes |
| 2026-11-22 | 1.1 | Independent audit (audit/AUDIT_REPORT.md): all 81 published quantities reproduced from published data. Added EXPLORATORY R9b (step 09): placebo with one shared pseudo-date per cluster, reported next to R9, never instead. Prespecified results unchanged | Yes |
| 2026-11-22 | 1.1 | Wording corrected after audit: 'prespecified' not 'preregistered'; robustness described as stable non-rejection with unstable sign and size; firm-specific reading presented as a possible explanation; power (MDE), weighting sensitivity and the two estimands (interval vs standardized test) disclosed. Descriptive diagnostics only, no new tests | Yes |
| 2026-11-22 | 1.1 | Case study upgraded to the working paper 'Rocket Launch Failures and Equity-Market Spillovers' (case-study.html / case-study.pdf). firm_event_cars.csv (alphas, betas) excluded from git permanently | Yes |
