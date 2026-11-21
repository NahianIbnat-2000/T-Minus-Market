# Confounding-news check: provider failures

Checked 21 Nov 2026, after the Phase 2 run. Under the analysis plan (section 8) this check
cannot remove events; it informs the case-study text only.

**Finding:** no unrelated firm-specific news (earnings, contracts, index changes) was found on
day 0 or day +1 for any of the four provider failures. In each case the press attributed the
price move to the failure itself, and the reported moves are close to the pipeline's CARs,
which is also an external check on the price data.

| Failure | Firm | Pipeline CAR[0,+1] | Move reported in the press | Same-window news | Sources |
| --- | --- | --- | --- | --- | --- |
| Vega VV15, 11 Jul 2019 | Avio | -12.29% | Fell nearly 15% in early trading, automatically suspended, -11.6% at 10:25 GMT | None found. Failure confirmed 9 min after liftoff (01:53 UTC), before Milan opened | [Reuters via MarketScreener](https://in.marketscreener.com/quote/stock/AVIO-S-P-A-23194747/news/Avio-Space-company-Avio-s-Vega-vehicle-has-launch-failure-28882446/); [SpaceNews](https://spacenews.com/?p=90923) |
| Vega VV17, 17 Nov 2020 | Avio | -16.26% | Large fall reported ("crolla in borsa") | None found. Last guidance confirmation was 5 Nov 2020, outside the window. Second Vega failure in three launches, so reputational effects may compound | [ESA](https://esa.int/Newsroom/Press_Releases/Vega_flight_VV17_failure_Arianespace_and_ESA_appoint_an_independent_Inquiry_Commission); [SpaceNews](https://spacenews.com/?p=108358); [Il Fatto Quotidiano](https://www.ilfattoquotidiano.it/2020/11/17/fallisce-il-lancio-del-razzo-vega-litaliana-avio-crolla-in-borsa-perche-il-flop-rischia-di-costare-caro-alla-politica-spaziale-italiana/6006342/) |
| Vega C VV22, 21 Dec 2022 | Avio | -8.81% | Down about 9.5% on the day; as much as 11% intraday | None found. CEO publicly took full responsibility the same day | [Insurance Journal](https://amp.insurancejournal.com/news/international/2022/12/22/700456.htm); [SpaceDaily/AFP](https://www.spacedaily.com/reports/Europes_access_to_space_in_jeopardy_after_Vega-C_rocket_failure_999.html) |
| Electron, 19 Sep 2023 | Rocket Lab | -10.47% | -15.5% at the open, closed down about 7.5% | The failure announcement itself (4:49 am EDT) said Q3 guidance would be revised: same news, not a confounder. The guidance cut came on 26 Sep after the close: outside [0,+1] and [-1,+3], inside [0,+20] | [Rocket Lab press release](https://www.nasdaq.com/press-release/rocket-lab-launch-update-2023-09-19); [Motley Fool](https://www.fool.com/investing/2023/09/19/why-rocket-lab-stock-got-rocked-today); [NZ Herald](https://nzherald.co.nz/business/rocket-lab-cuts-guidance-after-failed-flight/QYYBOSVRBVGOXIJKUDSAC7KBJE) |

## Notes for the case-study cards

- **Mechanism visible in the news:** Rocket Lab's own release linked the failure to lost and
  postponed revenue, and Avio's VV15 failure delayed the follow-on Falcon Eye 2 launch. This
  supports a cash-flow channel for providers, alongside reputation. It is evidence consistent
  with a mechanism, not proof of it.
- **VV17 is the largest loss (-16.3%)** and came two months after Vega's return to flight,
  as its second failure in three launches. Repeated failure may be priced as a reliability
  signal; with four events this is a description, not a test.

# Confounding-news check: largest rival moves

Checked 21 Nov 2026 for the 8 rival firm-events with the largest |CAR[0,+1]|. These cannot be
removed from the primary test (plan section 8). They are flagged for the site and for an
exploratory sensitivity analysis (labelled exploratory, because it was designed after results).

| Failure (rival of) | Ticker | Day 0 | CAR[0,+1] | Same-window news | Verdict | Sources |
| --- | --- | --- | --- | --- | --- | --- |
| Firefly Alpha, 22 Dec 2023 | RKLB | 2023-12-22 | +25.27% | Rocket Lab won a US government (Space Development Agency) contract worth up to $515m; shares up about 20% at the open that day | **Confounded** (large positive firm news) | [Motley Fool](https://www.fool.com/investing/2023/12/22/why-rocket-lab-stock-is-going-to-the-moon-today); [Benzinga](https://benzinga.com/news/23/12/36363533/why-rocket-lab-usa-stock-is-blasting-higher) |
| Kairos, 18 Dec 2024 | AVIO.MI | 2024-12-18 | +14.51% | ESA signed EUR 350m of contracts with Avio (Vega E development, Vega C launch rate); release 18 Dec 20:02 CET, after the Milan close, so it hits day +1 | **Confounded** (large positive firm news) | [Avio regulatory release](https://www.emarketstorage.it/sites/default/files/comunicati/2024-12/20241218_158732.pdf) |
| Firefly Alpha, 29 Apr 2025 | RKLB | 2025-04-29 | -7.45% | No firm-specific news found; RKLB fell while the market rose. Q1 results came 8 May, outside the window | Not confounded (none found) | [Zacks via Finviz](https://finviz.com/news/39365/rocket-lab-usa-inc-rklb-stock-sinks-as-market-gains-what-you-should-know) |
| RS1, 10 Jan 2023 | RKLB | 2023-01-11 | +7.33% (CAR[-1,+3] +23.17%) | No firm-specific news found in the window. The first US Electron launch was 24 Jan, outside the window | Not confounded (none found); unusually large drift | [Motley Fool](https://www.fool.com/investing/2023/02/11/rocket-lab-launched-its-first-us-rocket-what-next) |
| Kairos, 18 Dec 2024 | RKLB | 2024-12-18 | -7.31% | No firm-specific news found on 18-19 Dec. December 2024 trading was volatile after a large run-up, with insider sales earlier in the month | Not confounded (none found) | [Motley Fool](https://www.fool.com/investing/2024/12/08/why-rocket-lab-stock-sank-this-week) |
| Astra Rocket 3.3, 12 Jun 2022 | AVIO.MI | 2022-06-13 | -7.25% | No Avio-specific news found on 13-14 Jun 2022 | Not confounded (none found) | n/a |
| PSLV-DL, 12 Jan 2026 | FLY | 2026-01-12 | -6.98% | Lead-plaintiff deadline in a securities class action against Firefly fell on 12 Jan 2026; stock highly volatile after a strong start to 2026. Market-adjusted fallback model | **Possibly confounded** (weak) | [Levi & Korsinsky via Finviz](https://finviz.com/news/268191/shareholders-of-firefly-aerospace-inc-should-contact-levi-korsinsky-before-january-12-2026-to-discuss-your-rights-fly); [Benzinga via Finviz](https://finviz.com/news/274103/space-stocks-rip-into-2026-with-firefly-in-the-lead) |
| Spectrum, 30 Mar 2025 | RKLB | 2025-03-31 | -6.49% | Broad tech and space-stock selloff that day (Nasdaq down more than the S&P 500; Planet Labs and AST SpaceMobile also down about 4%), attributed by the press to macro news. The S&P 500 benchmark does not remove a tech or space factor | **Sector move** (not firm news; benchmark limitation) | [Motley Fool via Finviz](https://finviz.com/news/13588/why-rocket-lab-planet-labs-and-ast-spacemobile-stocks-all-dropped-on-monday) |

## What this means for the rival result

- The **two largest positive rival moves are both contract announcements**, not reactions to the
  competitor's failure. They pull the primary mean up. This explains the skew in the results:
  only 8 of 22 cluster CARs are positive, yet the mean is slightly positive.
- Rough arithmetic only (not a test): removing those two firm-events from the 42 would move the
  mean rival CAR[0,+1] from about +0.3% to about -0.7%. A proper exploratory re-estimate with
  the same test should be run and labelled exploratory.
- The 31 Mar 2025 case shows a limit of the design: a broad-market benchmark does not absorb a
  same-day move in tech or space stocks. A sector benchmark is a candidate for a future version
  of the plan, not a change to v1.0.
