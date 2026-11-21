# Frozen Analysis Plan v1.0 (21 Nov 2026)

Full plan: https://claude.ai/artifact/6xn5JNEeNn75fEXcL5bs5a

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

## Change log

| Date | Version | Change | Results seen? |
| --- | --- | --- | --- |
| 2026-11-21 | 1.0 | Plan frozen at end of Phase 1 | No |
| 2026-11-21 | 1.0 | Phase 2 run (05_event_study.py). No settings changed. Confounding-news check for provider failures added (docs/CONFOUNDING_NEWS.md); no events removed | Yes |
| 2026-11-21 | 1.0 | Added step 06, an EXPLORATORY confounding sensitivity (E1-E3) designed after results; flags in data/manual/confounded_events.csv. H2 unchanged | Yes |
| 2026-11-21 | 1.0 | Phase 3: site export (step 07) and browser module; derived statistics only (no raw returns). No analysis change | Yes |
| 2026-11-21 | 1.0 | Phase 4: website skeleton (five stages, anomaly cards, printed-figure charts); text generated from results. No analysis change | Yes |
| 2026-11-21 | 1.0 | Website rebuilt as one self-contained file (step 08, site/index.html); D3 and Vite removed; Methods moved into the page. Presentation only, no analysis change | Yes |
