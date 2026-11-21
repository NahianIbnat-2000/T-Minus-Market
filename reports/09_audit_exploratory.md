# Step 09: exploratory checks added after the audit

Designed after the results were seen (audit of 22 Nov 2026). Exploratory: reported next to the
prespecified results, never instead of them. Logged as plan v1.1.

## R9b: placebo with one shared pseudo-date per failure cluster

| | R9 (prespecified) | R9b (exploratory) |
| --- | --- | --- |
| Pseudo-dates | one per firm-event | one per cluster (22 of 22 clusters had a date eligible for all members) |
| Draws | 1000 | 1000 |
| Real mean CAR[0,+1] | +0.28% | +0.28% |
| Placebo mean | +0.07% | -0.02% |
| Placebo standard deviation | +0.75% | +0.83% |
| Middle 95% of placebo averages | -1.40% to +1.51% | -1.62% to +1.65% |
| Percentile of the real result | 61.2 | 65.8 |
| Two-sided share | 0.776 | 0.684 (Monte Carlo s.e. 0.015) |

A wider R9b spread than R9 means the original placebo understated how much ordinary-day averages vary
when rivals share dates. Neither is an exact permutation test.
