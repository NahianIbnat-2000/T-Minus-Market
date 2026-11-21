# Step 05: Event study results (analysis plan v1.0)

## Primary result (H2, confirmatory)

When a rival's small rocket fails, the mean two-day abnormal return of listed small-launch firms (CAR[0,+1]) is **+0.28%** (95% CI -1.62% to +2.18%), not detectable at the 5% level at this sample size (this is not evidence of no effect).

| Statistic | Value |
| --- | --- |
| Mean CAR[0,+1] | +0.28% |
| 95% CI (cluster-robust) | -1.62% to +2.18% |
| Adjusted BMP t | 0.854 |
| p-value (two-sided) | 0.4027 |
| Failures / firms / firm-events / clusters | 24 / 3 / 42 / 22 |
| Mean within-cluster CAR correlation | 0.150 |
| Notes | unadjusted BMP t = 0.932; adjustment factor = 0.916; df = 21 |

Returns are simple daily returns; market model on [-250, -30]; local index benchmark.

## Robustness (all prespecified, all reported)

| Check | Mean CAR | 95% CI | Statistic | p | Firm-events | Clusters | Note |
| --- | --- | --- | --- | --- | --- | --- | --- |
| R1 portfolio t-test | +0.21% | -1.63% to +2.05% | 0.234 | 0.8173 | 42 | 22 |  |
| R1 portfolio sign test | +0.21% | n/a | 8.000 | 0.2863 | 42 | 22 | 8 of 22 cluster CARs positive |
| R2 plain t | +0.28% | -1.57% to +2.13% | 0.305 | 0.7620 | 42 | 22 | ignores cross-correlation (literature baseline) |
| R3 rank (simulated p) | +0.28% | n/a | 0.047 | 0.4439 | 42 | 22 | 5000 simulations, seed 20261121; ignores cross-correlation |
| R4 window [-1,+3] | +1.84% | -0.41% to +4.09% | 1.397 | 0.1770 | 42 | 22 | unadjusted BMP t = 1.552; adjustment factor = 0.900; df = 21 |
| R5a drop low-confidence timing | +0.45% | -1.52% to +2.42% | 0.918 | 0.3694 | 40 | 21 | unadjusted BMP t = 1.005; adjustment factor = 0.913; df = 20 |
| R5b low-confidence day 0 + 1 session | +0.54% | -1.34% to +2.41% | 1.093 | 0.2867 | 42 | 22 | unadjusted BMP t = 1.193; adjustment factor = 0.917; df = 21 |
| R6 drop fallback-model events | +0.83% | -1.15% to +2.81% | 1.124 | 0.2744 | 38 | 21 | unadjusted BMP t = 1.215; adjustment factor = 0.925; df = 20 |
| R7 drop multi-failure clusters | +0.25% | -1.97% to +2.47% | 0.922 | 0.3683 | 36 | 20 | unadjusted BMP t = 0.987; adjustment factor = 0.934; df = 19 |
| R8 without AVIO.MI | -0.15% | -4.23% to +3.93% | 0.297 | 0.7713 | 18 | 14 | unadjusted BMP t = 0.318; adjustment factor = 0.932; df = 13 |
| R8 without FLY | +0.68% | -1.28% to +2.63% | 1.060 | 0.3010 | 39 | 22 | unadjusted BMP t = 1.123; adjustment factor = 0.945; df = 21 |
| R8 without RKLB | -0.00% | -1.76% to +1.75% | 0.653 | 0.5208 | 27 | 22 | unadjusted BMP t = 0.686; adjustment factor = 0.952; df = 21 |

## R9 Placebo benchmark

1000 draws (seed 20261121). Real mean CAR[0,+1] = +0.28%; placebo middle 95% = -1.40% to +1.51%; real value sits at the 61.2th percentile (two-sided share 0.776, Monte Carlo s.e. 0.013). Eligible pseudo-dates per firm-event: min 48, median 1091. This is a benchmark for context, not an exact permutation test.

## Provider failures (case series, not a pooled test)

| Failure | Firm | Day 0 | CAR[0,+1] | 95% interval | CAR[-1,+3] | Model |
| --- | --- | --- | --- | --- | --- | --- |
| 2019-F05 Vega | Avio SpA (AVIO.MI) | 2019-07-11 | -12.29% | -15.92% to -8.65% | -11.01% | market_model |
| 2020-U01 Vega | Avio SpA (AVIO.MI) | 2020-11-17 | -16.26% | -21.89% to -10.63% | -14.06% | market_model |
| 2022-F06 Vega C | Avio SpA (AVIO.MI) | 2022-12-21 | -8.81% | -15.92% to -1.69% | -9.28% | market_model |
| 2023-F08 Electron | Rocket Lab (RKLB) | 2023-09-19 | -10.47% | -19.58% to -1.37% | -7.22% | market_model |

## Exploratory (not confirmatory; Holm-adjusted p across this family)

| ID | Question | Estimate | n | p (raw) | p (Holm) |
| --- | --- | --- | --- | --- | --- |
| H3a | Rival CAR[0,+1]: first-flight failures minus others [exploratory] | -1.33% | [18, 24] | 0.4459 | 0.8918 |
| H3b | Provider CAR[0,+1]: failures minus successes [exploratory] | -11.84% | [4, 88] | 0.0018 | 0.0055 |
| H3c | Rival CAR[0,+20] (descriptive) [exploratory] | +0.83% | 42 | 0.7151 | 0.8918 |
