# Step 06: Confounding sensitivity (EXPLORATORY)

**Designed after the Phase 2 results were seen. Exploratory only: the confirmatory result is H2 in reports/05_results.md and does not change.**

## Flagged rival firm-events

| Launch | Ticker | Verdict | Reason |
| --- | --- | --- | --- |
| 2023-202 | RKLB | confounded | USD 515m Space Development Agency contract announced in the same window |
| 2024-F04 | AVIO.MI | confounded | EUR 350m ESA contracts released 18 Dec 2024 after the Milan close (day +1) |
| 2026-F01 | FLY | possibly_confounded | Securities class-action lead-plaintiff deadline on day 0 |
| 2025-F04 | RKLB | sector_move | Broad tech and space-stock selloff on day 0 not absorbed by the S&P 500 benchmark |

## Results (CAR[0,+1])

| Spec | Mean CAR | 95% CI | Statistic | p | Firm-events | Clusters | Dropped |
| --- | --- | --- | --- | --- | --- | --- | --- |
| H2 primary (confirmatory, all events) | +0.28% | -1.62% to +2.18% | 0.854 | 0.4027 | 42 | 22 | - |
| E1 drop 'confounded' [exploratory] | -0.70% | -1.80% to +0.39% | -0.182 | 0.8572 | 40 | 22 | 2023-202 RKLB; 2024-F04 AVIO.MI |
| E1 portfolio t-test [exploratory] | -0.72% | -2.03% to +0.59% | -1.143 | 0.2657 | 40 | 22 | - |
| E1 portfolio sign test [exploratory] | -0.72% | n/a | 7.000 | 0.1338 | 40 | 22 | - |
| E2 drop 'confounded' and 'possibly_confounded' [exploratory] | -0.54% | -1.71% to +0.63% | -0.069 | 0.9453 | 39 | 22 | 2023-202 RKLB; 2024-F04 AVIO.MI; 2026-F01 FLY |
| E2 portfolio t-test [exploratory] | -0.58% | -1.92% to +0.76% | -0.894 | 0.3813 | 39 | 22 | - |
| E2 portfolio sign test [exploratory] | -0.58% | n/a | 8.000 | 0.2863 | 39 | 22 | - |
| E3 drop every flagged event [exploratory] | -0.38% | -1.58% to +0.82% | 0.058 | 0.9543 | 38 | 22 | 2023-202 RKLB; 2024-F04 AVIO.MI; 2025-F04 RKLB; 2026-F01 FLY |
| E3 portfolio t-test [exploratory] | -0.37% | -1.74% to +1.00% | -0.559 | 0.5821 | 38 | 22 | - |
| E3 portfolio sign test [exploratory] | -0.37% | n/a | 9.000 | 0.5235 | 38 | 22 | - |

No multiple-testing correction is applied across E1 to E3; none of them is a confirmatory test.
