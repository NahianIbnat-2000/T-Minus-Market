# Step 10: CRSP supplement (plan v1.2)

Four delisted US launch firms added from CRSP (derived statistics only, run by a WRDS subscriber). The v1.0 result is the headline and is unchanged; S1 and S2 are reported next to it.

CRSP run: script 1.1 (22 Nov 2026), 2026-11-22T01:19:45+00:00, PERMNOs ORB 76139, OA 76477, ASTR 19835, VORB 21321.

Coverage: 129 of 137 CRSP events have a CAR; 8 dropped (fewer than 30 estimation returns); 12 new rival reactions enter H2.

## Rival test (H2), window [0,+1]

| Sample | Reactions | Clusters | Firms | Mean CAR | 95% CI | cluster-robust p | wild bootstrap p | BMP-KP t | BMP-KP p |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v1.0 sample (headline, unchanged) | 42 | 22 | 3 | +0.28% | -1.62% to +2.18% | 0.763 | 0.848 | 0.854 | 0.403 |
| S1: v1.0 + CRSP firms | 54 | 30 | 6 | +0.42% | -1.96% to +2.80% | 0.721 | 0.760 | 0.786 | 0.438 |
| S2 (exploratory): S1 without events flagged 'confounded' | 51 | 30 | 6 | -1.12% | -2.49% to +0.25% | 0.105 | 0.098 | -0.695 | 0.493 |

Other windows (BMP-KP p): S1 robust 0.189; S1 descriptive 0.503; S2 robust 0.528; S2 descriptive 0.717

Firm level (S1): 6 firms, mean of firm means +0.11%, 95% CI -3.14% to +3.35%.

Cross-source residual correlation (a CRSP firm and a v1.0 firm in one cluster) is not observable; it is set to 0.149, the mean of observed different-firm pairs with the same day 0. BMP-KP p for S1 with other values: 0.0: 0.430, 0.5: 0.458.

Dropped in S2: 2023-202 RKLB, 2023-F04 VORB, 2024-F04 AVIO.MI.

## Maker failures (case series)

| Day 0 | Firm | Vehicle | CAR [0,+1] | z | Source |
| --- | --- | --- | --- | --- | --- |
| 2001-09-21 | ORB | Taurus 2110 | -20.10% | -2.88 | crsp |
| 2009-02-24 | ORB | Taurus 3110 | -7.09% | -2.19 | crsp |
| 2011-03-04 | ORB | Taurus 3110 | -3.06% | -1.51 | crsp |
| 2014-10-29 | ORB | Antares 130 | -14.62% | -5.48 | crsp |
| 2019-07-11 | AVIO.MI | Vega | -12.29% | -6.63 | v1.0 |
| 2020-11-17 | AVIO.MI | Vega | -16.26% | -5.66 | v1.0 |
| 2022-02-10 | ASTR | Astra Rocket 3.3 | -34.81% | -3.87 | crsp |
| 2022-06-13 | ASTR | Astra Rocket 3.3 | -13.11% | -1.59 | crsp |
| 2022-12-21 | AVIO.MI | Vega C | -8.81% | -2.43 | v1.0 |
| 2023-01-10 | VORB | LauncherOne | -15.26% | -1.69 | crsp |
| 2023-09-19 | RKLB | Electron | -10.47% | -2.25 | v1.0 |

11 of 11 negative (5 firms); mean -14.17%, median -13.11%; exact sign test p = 0.0010 (descriptive: cases are few and not independent draws).

## Caveats

- S2 is exploratory. The VORB flag (2023-F04) was found after the CRSP CARs were seen, by checking the largest new reaction. The same news check has not yet been done for every new reaction, so S2 may be tilted.
- CRSP returns (RET, with delisting returns) and Yahoo adjusted closes are different sources; the S&P 500 benchmark is the same index in both.
- 2001-U01 ORB (maker case) is flagged possibly confounded: the first week of US trading after 11 Sep 2001.
