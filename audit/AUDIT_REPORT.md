# T-Minus Markets: independent audit (Deliverables A and B)

Audit date: 22 Nov 2026. Author of the project: Nahian Ibnat.
Audited version: public repository `NahianIbnat-2000/T-Minus-Market`, commit `559ea07` (22 Nov 2026 00:42 +06),
plus the local versions v16-v17 (case study), which were not yet pushed.

Labels used below: **Confirmed error** (verified wrong), **Methodological risk** (a defensible choice with a
weakness that must be disclosed or tested), **Optional** (improvement). Priority: P0 could invalidate a main
conclusion; P1 substantially affects credibility; P2 usability, interpretation or reproducibility; P3 optional.

## 1. What was inspected, and what could not be

| Item | Status |
| --- | --- |
| Landing article, report, plan page (public) | Read (`index.html`, `site/index.html`, `plan.html`) |
| Feasibility, results, confounding reports | Read (`reports/04`, `05`, `06`, `docs/CONFOUNDING_NEWS.md`) |
| Python pipeline, JS statistics, tests | Read; tests run (49 Python, 14 site, all pass on synthetic data) |
| Published derived data | Read (`site/data/*.json`, `data/processed/results.json`, `data/interim/*.csv`) |
| Working paper | **Does not exist.** A case study (v16-v17) exists locally and is not yet published. |
| Raw prices | **Not available to the auditor** (Yahoo data are used locally only by design). Abnormal returns and CARs therefore cannot be re-estimated here; the owner re-runs step 05 to reproduce them. Every statistic built *from* the CARs was re-checked. |
| Accessibility | Keyboard and structure checked in a simulated browser only. **No screen-reader or mobile device test has been run.** No compliance claim is made. |

## 2. Reproducibility audit (Deliverable B)

`audit/verify_published.py` recomputes the published statistics from the public derived data with an
independent implementation (it imports no pipeline code).

**Result: 81 of 81 published quantities reproduced** (tolerance 1e-9 for estimates and intervals, 1e-8 for
t and p; 1e-7 where daily abnormal returns are exported rounded to 8 decimals).

| Published quantity | Published | Reproduced |
| --- | --- | --- |
| Rival mean CAR[0,+1] | +0.280% | +0.280% |
| 95% interval | -1.622% to +2.181% | same |
| Adjusted BMP t / p | 0.854 / 0.403 | same |
| Unadjusted t, adjustment factor | 0.932, 0.916 | same |
| All 12 R-checks (R1-R8): mean, interval, t, p | see `reports/05` | all match |
| E1, E2, E3 (exploratory) | -0.70%, -0.54%, -0.38% | all match |
| Maker CARs (4 cases) and intervals | -12.29%, -16.26%, -8.81%, -10.47% | all match (intervals use the constant 1.96) |
| Placebo percentile / two-sided share | 61.2 / 0.776 | match (from the stored 1,000 draws) |
| Daily AR paths sum to CAR[0,+1] | 46 records | all match |

Not reproducible without prices: the CARs themselves (R3 rank and R9 placebo draws also need prices). This is
a data-licensing limit, not a defect; it is now stated in the reproduction guide.

## 3. Sample construction (verified from `data/interim`)

| Stage | Launches | Firm-events | Firms | Independent clusters |
| --- | --- | --- | --- | --- |
| GCAT orbital launch attempts, 2000-2026 | 3,077 | | | |
| Failures (score < 0.75; no duplicate tags) | 138 | | | |
| Pad explosions (kept separate) | 5 | | | |
| Failures with a listed maker (case series) | 4 | 4 | 2 (Avio, Rocket Lab) | 4 |
| Failures with a Tier 1-2 listed rival | 24 | 42 | 3 | 22 |
| of which Avio / Rocket Lab / Firefly | 24 / 15 / 3 | 24 / 15 / 3 | | |
| Coverage exclusions (all roles) | | 137 no price data; 24 missing primary-window price; 10 short history | | |

Clusters: 8 contain one rival firm, 11 two, 3 all three; 20 contain one failure, 2 contain two.

## 4. Findings register (Deliverable A)

### P0: none found
No computational error was found in any published statistic, and no finding below reverses the headline
(no detectable average rival reaction; large losses for the maker in each case).

### P1

| # | Dimension | Finding | Type | Fix | Frozen spec? | Effort |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Interpretation | The public article calls the plan **"Preregistered"**. The plan was prespecified and committed to git before results (plan in `6e43dee` 20:13 and `54393b2` 20:30:24; results in `be71a52` 20:31:18, 21 Nov 2026), but it was not filed with an independent registry, and git timestamps are set by the author. | Confirmed error (wording) | Say "prespecified (frozen in git before results)"; cite the hashes | No | S |
| 2 | Interpretation | **"12 of 12 checks reach the same conclusion"** overstates stability. All 12 fail to reject zero, but estimates range from -0.15% (without Avio) to +1.84% (wider window). | Confirmed error (wording) | "No prespecified check detects a significant average at 5%; direction and size vary" | No | S |
| 3 | Interpretation | **"A failure behaves like a firm-specific shock"** is presented as a finding. The data are consistent with it but cannot establish it: power is low (#5) and the sign depends on weighting (#4). | Confirmed error (overclaim) | Present as one reading the data do not contradict, alongside what is not ruled out | No | S |
| 4 | Statistics | **Direction depends on weighting.** Observation-weighted +0.28%; per independent event +0.21%; precision-weighted +0.87%; each firm equal **-1.16%** (Firefly's 3 events average -4.86%). Leave-one-firm-out: -0.15% (no Avio), -0.00% (no Rocket Lab), +0.68% (no Firefly). Three firms cannot support firm-clustered asymptotic inference. | Methodological risk (concentration) | Report the weighting table and per-firm means; describe the population as three listed firms; no industry-wide claims | No (descriptive) | S |
| 5 | Statistics | **Low power.** From the published interval (cluster SE 0.91%, 21 df): minimum detectable effect 2.7% at 80% power; power 18% for a true +/-1%, 55% for +/-2%. 90% interval [-1.29%, +1.85%]: equivalence holds only against a +/-1.85% margin, which is not economically negligible for a two-day return. | Methodological risk | State the MDE and that absence of an effect is not shown; no equivalence claim | No | S |
| 6 | Statistics | **Interval and p-value come from different procedures** and estimate different things: the interval is cluster-robust around the equal-weighted mean CAR; the p-value is the standardized BMP-KP test (volatility-weighted). They can disagree; E1 shows it (mean -0.70%, interval [-1.80%, +0.39%], BMP p = 0.86, because the standardized mean is only -0.03). The plan fixes the test, not the interval method. | Methodological risk (disclosure) | Say so wherever the pair is reported; report both the raw mean and the standardized mean | No | S |
| 7 | Statistics | **Placebo draws an independent random date for each firm-event**, breaking the same-day co-movement of rivals hit by one failure, so the placebo spread is too narrow. The result (61st percentile) would move further to the middle, so the conclusion is unaffected, but the procedure understates dependence. Correctly labelled a benchmark, not a permutation test. | Methodological risk | Exploratory R9b with one shared pseudo-date per cluster (needs prices; owner runs locally; log as plan v1.1) | No (exploratory addition) | M |
| 8 | Statistics | **The mean is fragile to two outliers.** The two contract-news days (+25.3%, +14.5%) move the mean from +0.28% to -0.70%; the median moves only from +0.28% to +0.09%, and the share of negative CARs from 48% to 50%. | Methodological risk | Report median and share negative next to the mean | No | S |
| 9 | Reproducibility | `data/processed/firm_event_cars.csv` (alphas, betas) is **public**, against the project's own data policy. It was untracked in `e578563` and re-added in `aada2fb` because the v14 `.gitignore` lacked the line (an error in the files supplied to the owner). | Confirmed error | Ignore permanently; optional history rewrite (owner's decision) | No | S |
| 10 | Transparency | Article says the code is **"available on request"**, but the repository is public. | Confirmed error | Link the repository | No | S |
| 11 | Sample | **Survivorship:** listed launch firms that later delisted (Orbital Sciences/Orbital ATK, Astra, Virgin Orbit) are missing because the free price source lacks them. Rival reactions may differ for firms that later failed. | Methodological risk | State as a limit; CRSP extension as recorded plan v1.1 | Would need a plan revision | L |

### P2

| # | Finding | Type | Fix |
| --- | --- | --- | --- |
| 12 | The interactive report is drawn entirely by JavaScript; without it the reader gets one sentence. The article and case study are static. | Optional | Static summary and links inside the report's `<noscript>` and above the stages |
| 13 | KP adjustment uses within-cluster estimation-window residual correlation scaled by shared window days; pairs in different clusters are set to zero. Reasonable, but an extension of KP (who assume one event date). | Methodological risk (disclosure) | Document the assumption in methods |
| 14 | p-values use t with G-1 = 21 df (independent clusters), more conservative than N-1 = 41. | Disclosure | Document |
| 15 | Maker intervals use +/-1.96 x prediction-error SD (normal approximation); with ~220 estimation days, t would widen them by under 1%. | Disclosure | Document |
| 16 | Placebo excludes +/-10 sessions only around the same ticker's failures, not around other industry events. | Methodological risk | Document; consider in R9b |
| 17 | The largest unflagged rival move (-7.45%, Rocket Lab after Firefly 29 Apr 2025) is a low-confidence-timing event. R5a/R5b cover it. | Note | Mention in the confounding exhibit |

### P3 (extensions, evaluate only)
Abnormal volume; pre-event drift; first-flight vs mature rockets (H3a exists, exploratory); rival proximity;
CRSP delisted firms; sector benchmarks. Each adds tests on the same 22 clusters, so each must be logged as
exploratory with a multiple-testing correction. Recommended for v2 only: CRSP (more firms, not more tests).

## 5. What the evidence supports (revised conclusion)

Across 22 independent rival-event clusters involving three listed firms (Avio, Rocket Lab, Firefly), the
average two-day abnormal return is +0.28% (95% cluster-robust interval -1.62% to +2.18%; standardized BMP-KP
test p = 0.40). The data do not establish systematic contagion or systematic competitive gains among these
firms. They also do not show that the effect is negligible: average effects of about 2-3% in either direction
cannot be excluded, and the sign of the average changes with how events and firms are weighted. For the
rocket's maker, each of the four listed cases (two firms) shows a large loss (-8.8% to -16.3% over two days,
each interval excluding zero); these are case studies, not an industry average.

Population: historically eligible, publicly traded launch-service competitors with comparable commercial
exposure; not private, state-owned or diversified aerospace firms.

## 6. Quality assurance: what changed (Deliverable I)

| Finding | Status in v18 |
| --- | --- |
| 1 "Preregistered" | Fixed: "prespecified", with commit hashes in the plan's freeze record |
| 2 "12 of 12 same conclusion" | Fixed on article, report and paper: stable non-rejection, unstable sign and size, range shown |
| 3 "firm-specific shock" as a finding | Fixed: listed as a possible explanation, next to what is not shown |
| 4 Weighting and concentration | Added: weighting table, per-firm table, exposure matrix, "Avio in every event" (all data-driven) |
| 5 Power | Added: MDE 2.7% (80%), power at 1-3%, 90% interval, no equivalence claim |
| 6 Two estimands | Disclosed on article, report and paper; paper reports raw and standardized means |
| 7 Placebo independence | Disclosed; exploratory R9b implemented (step 09), tested on synthetic data; owner runs it on real prices |
| 8 Outlier sensitivity | Median reported next to the mean in the confounding exhibit |
| 9 Alpha/beta file public | Fixed going forward (`.gitignore`, regression test); history left as is (owner's decision) |
| 10 "On request" | Fixed: repository linked; evidence links to reports |
| 11 Survivorship | Listed in limitations; CRSP extension remains plan v1.1 future work |
| 12 Report needs JavaScript | Static key-results summary in `<noscript>` |
| 13-17 | Documented in the paper's methods and limitations |

Tests: 54 Python and 14 site tests pass. Paper and article were built from the real published data and read
in full; the PDF was compiled with XeLaTeX (15 pages) and every page inspected.
**Not tested:** screen readers and physical mobile devices; R9b on real prices (needs the owner's local run).
