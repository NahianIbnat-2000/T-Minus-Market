# Website data (site/data/)

Written by `pipeline/07_export_site_data.py`. Read by the website and by
`site/src/stats/eventstudy.js`. **Only derived statistics are published.** No raw prices,
raw returns, alphas or betas leave the pipeline, so the site does not republish Yahoo data.

## Files

| File | Contents | Used by |
| --- | --- | --- |
| `manifest.json` | Plan version, run and export times, windows, data policy, sources, parity tolerances | Footer, Methods page |
| `failures.json` | Every failure since 2000: date, vehicle, agency, GCAT code and score, listed providers, whether it is in the provider case series or the rival test, and why not | Failure Timeline (T-2) |
| `firm_events.json` | One record per rival and provider firm-event (fields below) | Event Study Lab (T0), Mission Anomaly cards |
| `rho.json` | For each window, `[id_a, id_b, rho]` for every pair of firm-events in the same cluster | Live primary test in the browser |
| `results.json` | Every reported result: primary H2, R1 to R9, placebo distribution, provider case series, exploratory H3 and step 06 | Results text, Is It Real? (T+1) |

## firm_events.json fields

| Field | Meaning |
| --- | --- |
| `id` | `launch_tag|ticker|role`, stable key |
| `group` | `rival` or `provider_failure` |
| `launch_tag`, `vehicle`, `firm`, `ticker`, `exchange`, `tier`, `role` | Identity |
| `cluster` | Independent cluster; the unit of inference |
| `day0`, `disclosure_confidence` | Event timing |
| `model`, `est_obs`, `sigma` | Market model or market-adjusted fallback; estimation days; daily residual s.d. |
| `flag` | `null`, or `{verdict, reason, source}` from `data/manual/confounded_events.csv` |
| `windows.{primary,robust,descriptive}` | `car` (fraction), `var` (variance of the CAR, prediction-error adjusted), `L` (days) |
| `path` | Daily abnormal returns from T-5 to T+20 (`ar`, fraction) |

## What the browser can recompute

From these files the Event Study Lab re-runs, live, on any subset (window, firms, flagged events,
low-confidence timing, fallback model):

- the primary test (BMP with Kolari-Pynnonen cluster adjustment), with cluster-robust 95% CI
- the portfolio t-test and exact sign test (R1)

Users choose among the three prespecified windows. Free choice of window or estimation period
would need raw returns in the browser, which this design avoids on purpose.

## Parity

`tests/test_phase3_parity.py` checks, on synthetic data with correlated rivals:

1. the test computed from exported numbers equals the test computed from raw returns (to 1e-12);
2. the JavaScript module equals Python within the tolerances in `manifest.json`
   (CARs and CIs 1e-9, t and p 1e-8; CARs are fractions, so 1e-9 = 0.0000001 percentage points);
3. no exported file contains a numeric field named like a price, return, alpha or beta.
