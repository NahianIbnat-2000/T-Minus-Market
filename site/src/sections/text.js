// Narrative text for the five stages. Pure functions: data in, HTML out.
// Rule: no number is typed here. Every figure comes from results.json, firm_events.json
// or failures.json, so the text cannot drift from the analysis.
import { ci, date, escapeHtml, num, pct, pval, signClass, verdict } from "../format.js";

const listJoin = (a) => (a.length <= 1 ? a.join("") : `${a.slice(0, -1).join(", ")} and ${a[a.length - 1]}`);

export function stageLabel(t, name) {
  return `<div class="stage-label"><span class="t">${t}</span><span>${escapeHtml(name)}</span></div>`;
}

// ------------------------------------------------------------------ T-3
export function questionText(c) {
  return `
  <p class="lead">Every rocket launch is a bet that a machine with millions of parts will work perfectly for about ten minutes. Sometimes it does not. This report asks what the stock market does next.</p>
  <p>When a rocket fails, the company that built it loses hardware, a customer's satellite and some of its reputation. Investors should mark its shares down. The harder question is what happens to its <em>competitors</em>. There are two opposite stories.</p>
  <div class="callout"><span class="label">Story 1: contagion</span>A failure reminds investors that spaceflight is risky for everyone, so rival launch companies fall too.</div>
  <div class="callout"><span class="label">Story 2: competitive gain</span>Customers may move their satellites to a rocket that works, so rivals rise.</div>
  <p>Both stories are plausible, and they point in opposite directions. Only data can say which one investors act on. This study looks at ${c.failures} orbital launch failures from ${c.firstYear} to ${c.lastYear}, follows the shares of the listed firms involved, and measures how they moved in the two trading days after each failure became public.</p>
  <div class="figures-row" role="list">
    <div role="listitem"><span class="big">${c.failures}</span><span class="cap">orbital launch failures, ${c.firstYear} to ${c.lastYear}</span></div>
    <div role="listitem"><span class="big">${c.rivalFailures}</span><span class="cap">failures with a listed competitor to study</span></div>
    <div role="listitem"><span class="big">${c.clusters}</span><span class="cap">independent events after grouping failures that overlap</span></div>
    <div role="listitem"><span class="big">${c.providerFailures}</span><span class="cap">failures where the rocket's own maker was listed</span></div>
  </div>`;
}

// ------------------------------------------------------------------ T-2
export function failuresText(c) {
  return `
  <p class="lead">Most rocket failures cannot tell us anything about stock prices, because the companies involved are not listed on a stock exchange.</p>
  <p>Of the ${c.failures} failures since ${c.firstYear}, many belong to state agencies or private companies. A failure enters the study only if a listed company had a clear stake in it on the day it happened: as the rocket's maker, or as a direct competitor of a similar size selling to the same customers. Every rule was fixed before any stock reaction was measured.</p>
  <p>That leaves ${c.rivalFailures} failures where listed competitors can be studied (${listJoin(c.rivalFirms.map(escapeHtml))}), and ${c.providerFailures} where the rocket's own maker was listed.</p>`;
}

// ------------------------------------------------------------------ T-1
export function methodText() {
  return `
  <p class="lead">To see a surprise in a stock price, you first need to know what the price would have done anyway.</p>
  <p>Stocks move every day for countless reasons, most of them about the whole market. So for each company we first learn its normal relationship with its home market index, using about a year of trading days that end well before the failure. That gives an <strong>expected return</strong> for any day.</p>
  <p>The <strong>abnormal return</strong> is the difference between what the stock actually did and what was expected. Adding up abnormal returns over the day the failure became public (T0) and the next trading day (T+1) gives the <strong>cumulative abnormal return</strong>, or CAR. This is the study's main measure.</p>
  <div class="callout"><span class="label">Why "T0" and "T+1"</span>Launches count down to T0. This study counts trading days the same way: T0 is the first trading session after the failure became public; T+1 is the session after that.</div>
  <p>Some failures happen close together, and some hit several competitors at once. Those reactions are not independent, so the statistics treat each group of overlapping failures as one observation, and adjust for the fact that rivals' prices tend to move together.</p>`;
}

// ------------------------------------------------------------------ T0
export function providerText(cases) {
  const vals = cases.map((c) => c.car_primary).filter(Number.isFinite);
  if (!vals.length) return "<p>No provider failures are available.</p>";
  const allNeg = vals.every((v) => v < 0);
  const excl = cases.filter((c) => c.car_primary_ci && (c.car_primary_ci[1] < 0 || c.car_primary_ci[0] > 0)).length;
  const lo = Math.min(...vals), hi = Math.max(...vals);
  return `
  <h3>The company whose rocket failed</h3>
  <p>In ${cases.length} cases the rocket's maker was listed. ${allNeg ? "In every one, its shares fell" : "Its shares moved"} by between <strong class="${signClass(lo)}">${pct(lo)}</strong> and <strong class="${signClass(hi)}">${pct(hi)}</strong> over two days, after allowing for the market. ${excl === cases.length ? "In each case the 95% interval excludes zero." : `In ${excl} of ${cases.length} cases the 95% interval excludes zero.`}</p>
  <p>With only ${cases.length} events, these are case studies, not an industry-wide average. They are shown one by one below.</p>`;
}

export function rivalText(primary, e1) {
  const p = primary;
  let s = `
  <h3>The competitors</h3>
  <p>When a rival's rocket failed, listed small-launch companies moved by <strong class="${signClass(p.mean_car)}">${pct(p.mean_car, 2)}</strong> on average over two days (95% interval ${ci(p.ci_low, p.ci_high, 2)}; p = ${pval(p.p)}). This reaction ${verdict(p.p)}. It is based on ${p.n_failures} failures, ${p.n_firms} companies and ${p.n_clusters} independent events.</p>`;
  if (p.p >= 0.05) {
    s += `<p>"Not detectable" is not the same as "no effect". The interval still tells us something: average reactions much larger than its ends, in either direction, are unlikely.</p>`;
  }
  if (e1) {
    s += `<div class="callout"><span class="label">Exploratory check, added after the results</span>Two of the largest rival moves fell on days when the same companies announced large new contracts. Leaving those two out, the average becomes <strong class="${signClass(e1.mean_car)}">${pct(e1.mean_car, 2)}</strong> (95% interval ${ci(e1.ci_low, e1.ci_high, 2)}; p = ${pval(e1.p)}). Because this check was designed after seeing the data, it cannot replace the main result above.</div>`;
  }
  return s;
}

// ------------------------------------------------------------------ T+1
export function placeboText(pl) {
  if (!pl) return "";
  return `
  <p>One way to judge a result is to compare it with ordinary days. We picked ${pl.draws} sets of random trading days for the same companies, away from any failure, and measured the same two-day average each time. The real failures sit at the <strong>${num(pl.actual_percentile, 0)}th percentile</strong> of that spread. This is a sense check, not a formal test: random days are not perfectly comparable to launch days.</p>`;
}

export function robustnessTable(rows) {
  const body = rows.map((r) => `<tr><td>${escapeHtml(r.name)}</td><td class="num ${signClass(r.mean_car)}">${pct(r.mean_car, 2)}</td><td class="num">${
    r.ci_low === null || r.ci_low === undefined ? "n/a" : ci(r.ci_low, r.ci_high, 2)}</td><td class="num">${pval(r.p)}</td><td class="num">${r.n_firm_events ?? ""}</td></tr>`).join("");
  return `<table><caption class="visually-hidden">Robustness checks for the rival result</caption>
    <thead><tr><th>Check (all chosen before the results)</th><th class="num">Mean CAR</th><th class="num">95% interval</th><th class="num">p</th><th class="num">Firm-events</th></tr></thead>
    <tbody>${body}</tbody></table>`;
}

export function flagsList(records) {
  const flagged = records.filter((r) => r.flag);
  if (!flagged.length) return "";
  return `<h3>Events with other news on the same days</h3>
  <p>We checked the news around the largest reactions. These events stay in the main result (the rules do not allow removing events after the fact), but readers should know about them.</p>
  <table><thead><tr><th>Failure</th><th>Company</th><th class="num">CAR T0 to T+1</th><th>Other news</th></tr></thead><tbody>${
    flagged.map((r) => `<tr><td>${escapeHtml(r.vehicle)}, ${date(r.day0)}</td><td>${escapeHtml(r.firm)}</td><td class="num ${signClass(r.windows.primary.car)}">${pct(r.windows.primary.car, 1)}</td><td>${escapeHtml(r.flag.reason)}${
      r.flag.source ? ` (<a href="${escapeHtml(r.flag.source)}" rel="noopener">source</a>)` : ""}</td></tr>`).join("")}</tbody></table>`;
}

export function limitsText(c) {
  return `<h3>What this study cannot tell you</h3>
  <ul>
    <li>The competitor result rests on ${c.rivalFirms.length} companies. It describes how these firms reacted, not every space company.</li>
    <li>A zero average could hide two effects that cancel out: some investors fearing contagion, others expecting customers to switch.</li>
    <li>A market reaction shows what investors expected, not what actually happened to the companies' business afterwards.</li>
    <li>The market benchmark removes broad market moves but not moves shared only by technology or space stocks.</li>
    <li>Several failed rockets belonged to companies that are no longer listed, and free price data for them is not available.</li>
  </ul>`;
}
