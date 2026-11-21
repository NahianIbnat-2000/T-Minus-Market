// Assembles the five stages from data. Charts need a browser DOM (figures.js).
import { anomalyCard } from "../components/anomalyCard.js";
import { carPathsPlate, intervalPlate, placeboPlate, resetPlates, yearBarsPlate } from "../components/figures.js";
import { counts } from "../data.js";
import { carPath } from "../stats/eventstudy.js";
import { escapeHtml, pct } from "../format.js";
import * as T from "./text.js";
import { methodsSection } from "./methods.js";

const placeholder = (what, phase) =>
  `<div class="placeholder-tool" role="note">${escapeHtml(what)} arrives in ${escapeHtml(phase)}.</div>`;

export function renderReport(data) {
  resetPlates();
  const { results, firmEvents, failures } = data;
  const c = counts(data);
  const providers = firmEvents.filter((r) => r.group === "provider_failure");
  const rivals = firmEvents.filter((r) => r.group === "rival");
  const cases = results.provider_case_series || [];
  const caseFor = (r) => cases.find((x) => x.launch_tag === r.launch_tag && x.ticker === r.ticker);
  const e1 = results.exploratory_confounding?.results?.find((r) => r.id === "E1");
  const robust = (results.robustness || []).filter((r) => !/sign test/.test(r.name));

  const t3 = `<section class="stage" id="t-3" aria-labelledby="h-t-3"><div class="wrap">
    ${T.stageLabel("T−3", "The Question")}
    <h2 id="h-t-3">Why would investors care about a rocket?</h2>
    ${T.questionText(c)}</div></section>`;

  const t2 = `<section class="stage" id="t-2" aria-labelledby="h-t-2"><div class="wrap">
    ${T.stageLabel("T−2", "The Failures")}
    <h2 id="h-t-2">Every rocket that failed</h2>
    ${T.failuresText(c)}
    ${yearBarsPlate({ title: "Orbital launch failures per year", failures,
      caption: `Outline: all orbital launch failures (GCAT success score below 0.75), ${c.firstYear} to ${c.lastYear}. Solid: failures that enter the study. Source: GCAT (J. McDowell), CC-BY.` })}
    ${placeholder("The interactive Failure Timeline", "Phase 5")}</div></section>`;

  const t1 = `<section class="stage" id="t-1" aria-labelledby="h-t-1"><div class="wrap">
    ${T.stageLabel("T−1", "The Method")}
    <h2 id="h-t-1">How do you measure a surprise?</h2>
    ${T.methodText()}
    ${placeholder("The Expected vs Actual explorer (with a clearly labelled simulated example)", "Phase 5")}</div></section>`;

  const providerPaths = providers.map((r) => ({ label: `${r.vehicle} (${r.ticker})`, tone: "loss", points: carPath(r, -5) }));
  const t0 = `<section class="stage" id="t0" aria-labelledby="h-t0"><div class="wrap">
    ${T.stageLabel("T0", "The Reaction")}
    <h2 id="h-t0">What the market did</h2>
    ${T.providerText(cases)}
    <ul class="anomaly-grid">${providers.map((r, i) => anomalyCard(r, caseFor(r), i + 1)).join("")}</ul>
    ${carPathsPlate({ title: "The rocket's maker: cumulative abnormal return", series: providerPaths,
      caption: "Cumulative abnormal return (market model, simple returns) from five trading days before to twenty after each failure. T0 is the first session after the failure became public. Each line is one case; they are not averaged." })}
    ${T.rivalText(results.primary, e1)}
    ${intervalPlate({ title: "Competitors: average two-day reaction (T0 to T+1)",
      rows: [
        { label: "Main result (prespecified)", mean: results.primary.mean_car, lo: results.primary.ci_low, hi: results.primary.ci_high, emphasis: true, note: "confirmatory" },
        ...robust.filter((r) => r.ci_low !== null && r.ci_low !== undefined).map((r) => ({ label: r.name, mean: r.mean_car, lo: r.ci_low, hi: r.ci_high, note: "robustness" })),
        ...(e1 ? [{ label: "Without two contract-news days", mean: e1.mean_car, lo: e1.ci_low, hi: e1.ci_high, note: "exploratory, chosen after results" }] : []),
      ],
      caption: `Mean cumulative abnormal return of listed competitors over T0 to T+1, with 95% intervals (cluster-robust). Rival sample: ${results.primary.n_failures} failures, ${results.primary.n_firm_events} firm-events, ${results.primary.n_clusters} independent events. Dots are blue above zero and red below; the sign is also given in the table.` })}
    ${placeholder("The Event Study Lab (re-run the test on any subset)", "Phase 5")}</div></section>`;

  const pl = results.placebo;
  const t1p = `<section class="stage" id="t+1" aria-labelledby="h-t1p"><div class="wrap">
    ${T.stageLabel("T+1", "Is It Real?")}
    <h2 id="h-t1p">Could it just be luck?</h2>
    ${T.placeboText(pl)}
    ${pl?.distribution ? placeboPlate({ title: "Real failures against ordinary days", distribution: pl.distribution, actual: pl.actual_mean_car,
      caption: `Each bar counts random draws of ordinary trading days (${pl.draws} draws, fixed seed ${pl.seed}) by their average two-day abnormal return for the competitor sample. The line marks the real failures (${pct(pl.actual_mean_car, 2)}).` }) : ""}
    <h3>The same question, checked ${robust.length} ways</h3>
    ${T.robustnessTable(robust)}
    ${T.flagsList(rivals)}
    ${T.limitsText(c)}
    ${placeholder("The Placebo Simulator", "Phase 5")}</div></section>`;

  return t3 + t2 + t1 + t0 + t1p + methodsSection(data);
}
