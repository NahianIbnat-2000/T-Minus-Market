# Step 04: Feasibility report

This report uses estimation-window volatility only. No event-window abnormal return has been computed.

## Gate decision

- (a) Provider test: >= 10 independent failures AND MDE for CAR[0,+1] <= 5.0%: **FAIL** (4 failures, MDE = 6.7%)
- (b) Independent failure clusters with a Tier 1/2 rival >= 8: **PASS** (22)
- Overall: **PARTIAL: confirmatory rival test; providers as case series**

Not final while provider/Tier 1-2 firm-events use unverified firm-map rows (0) or timing-sensitive events lack a sourced disclosure time (0).  
Status: **FINAL for the current sample**. (Tier 3 descriptive firm-events on unverified rows: 749; these do not enter any test.)

Timing-sensitive = day 0 would change if the disclosure came 10 min earlier or up to 180 min later than recorded.


## Usable sample

| Group | Failures | Independent clusters | Firm-events | Median daily AR std. dev. | MDE CAR[0,+1] |
| --- | --- | --- | --- | --- | --- |
| Providers (pure-play or major exposure) | 4 | 4 | 4 | 2.3% | 6.7% |
| Rivals Tier 1-2 | 24 | 22 | 42 | 2.9% | 2.6% |
| Rivals Tier 3 (descriptive) | 138 | 119 | 821 | 1.5% | 0.6% |
| Provider successes (comparison group) | n/a | n/a | 88 | 4.4% | n/a |

MDE: 5% two-sided, 80% power, t critical values, independent clusters, no event-induced variance (a lower bound).

## Firm-events dropped at the coverage step

| Reason | Firm-events |
| --- | --- |
| no_price_data_for_ticker | 137 |
| missing_price_in_primary_window | 24 |
| insufficient_estimation_history | 10 |

## Usable failure firm-events by firm

| Firm | Ticker | Role/tier | Events | Model |
| --- | --- | --- | --- | --- |
| Airbus SE (EADS before 2014) | AIR.PA | provider_minor_exposure | 2 | market_model |
| Airbus SE (EADS before 2014) | AIR.PA | tier3 | 130 | market_model |
| Avio SpA | AVIO.MI | provider | 3 | market_model |
| Avio SpA | AVIO.MI | tier1 | 1 | market_adjusted_fallback |
| Avio SpA | AVIO.MI | tier1 | 23 | market_model |
| Avio SpA | AVIO.MI | tier3 | 46 | market_model |
| Boeing Co | BA | provider_minor_exposure | 2 | market_model |
| Boeing Co | BA | tier3 | 136 | market_model |
| Firefly Aerospace | FLY | tier1 | 2 | market_adjusted_fallback |
| Firefly Aerospace | FLY | tier1 | 1 | market_model |
| Firefly Aerospace | FLY | tier3 | 4 | market_adjusted_fallback |
| Firefly Aerospace | FLY | tier3 | 4 | market_model |
| IHI Corp | 7013.T | provider_minor_exposure | 1 | market_model |
| IHI Corp | 7013.T | tier3 | 54 | market_model |
| Lockheed Martin Corp | LMT | provider_minor_exposure | 2 | market_model |
| Lockheed Martin Corp | LMT | tier3 | 136 | market_model |
| Mitsubishi Heavy Industries | 7011.T | provider_minor_exposure | 3 | market_model |
| Mitsubishi Heavy Industries | 7011.T | tier3 | 129 | market_model |
| Northrop Grumman Corp | NOC | tier3 | 70 | market_model |
| Rocket Lab | RKLB | provider | 1 | market_model |
| Rocket Lab | RKLB | tier1 | 1 | market_adjusted_fallback |
| Rocket Lab | RKLB | tier1 | 14 | market_model |
| Rocket Lab | RKLB | tier3 | 3 | market_adjusted_fallback |
| Rocket Lab | RKLB | tier3 | 26 | market_model |
| Safran SA | SAF.PA | provider_minor_exposure | 1 | market_model |
| Safran SA | SAF.PA | tier3 | 83 | market_model |

## Usable failures by year

| Year | Failures with any usable firm |
| --- | --- |
| 2000 | 4 |
| 2001 | 2 |
| 2002 | 4 |
| 2003 | 2 |
| 2004 | 3 |
| 2005 | 4 |
| 2006 | 4 |
| 2007 | 3 |
| 2008 | 3 |
| 2009 | 4 |
| 2010 | 4 |
| 2011 | 6 |
| 2012 | 5 |
| 2013 | 3 |
| 2014 | 3 |
| 2015 | 5 |
| 2016 | 2 |
| 2017 | 6 |
| 2018 | 3 |
| 2019 | 5 |
| 2020 | 10 |
| 2021 | 11 |
| 2022 | 7 |
| 2023 | 10 |
| 2024 | 6 |
| 2025 | 11 |
| 2026 | 8 |
