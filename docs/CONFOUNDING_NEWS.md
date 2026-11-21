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
- **Rival events:** not yet checked. Do the same check for the largest rival moves before the
  site describes them individually.
