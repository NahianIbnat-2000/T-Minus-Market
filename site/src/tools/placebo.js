// Placebo Simulator: replays the placebo draws computed offline (step 05, R9), so readers can watch
// how often ordinary trading days produce an average as large as the real failures.
// The draws come from results.json; no prices or returns are needed in the browser.
import { escapeHtml, num, pct } from "../format.js";
import { axisBottom, bins, line, linear, niceDomain, niceTicks, rect, svgOpen, text } from "../components/svg.js";

const BIN_COUNT = 40;
const STEPS = [1, 10];          // draw-button sizes
const PLACEBO_GAP = 10;         // sessions excluded around each failure day (pipeline/analysis.py, R9)

/** Share counts with the same two-sided rule as pipeline/analysis.py: 2 * min(P(<= actual), P(>= actual)). */
export function placeboShares(draws, actual) {
  const n = draws.length;
  if (!n) return { n, low: 0, high: 0, twoSided: null };
  const low = draws.filter((v) => v <= actual).length, high = draws.filter((v) => v >= actual).length;
  return { n, low, high, twoSided: Math.min(1, (2 * Math.min(low, high)) / n) };
}

export function placeboToolHtml({ results }) {
  const pl = results.placebo;
  if (!pl?.distribution?.length) return "";
  const N = pl.distribution.length;
  return `<div class="tool placebo-tool" id="placebo-sim" data-tool="placebo">
    <div class="tool-head"><span class="tool-kicker">Interactive tool</span><h3>Placebo Simulator</h3>
      <p>Could luck alone produce the competitors' reaction? Each draw picks one random ordinary trading day for every company reaction in the study and averages the two-day abnormal returns. Draw sets and watch where the real failures fall.</p></div>
    <div class="sim-controls" role="group" aria-label="Draw random sets of ordinary days">
      ${STEPS.map((k) => `<button type="button" data-draw="${k}">Draw ${k}</button>`).join("")}
      <button type="button" data-draw="all">Draw all ${N}</button>
      <button type="button" data-draw="reset" class="ghost">Start over</button>
    </div>
    <div class="sim-chart"></div>
    <div class="sim-out" aria-live="polite"></div>
    <ul class="sim-facts">
      <li><strong>Pseudo-event dates:</strong> random ordinary trading days of each stock's own exchange, at least ${PLACEBO_GAP} sessions away from any of that stock's failure days, with a full year of earlier prices for the market model.</li>
      <li><strong>One date per reaction:</strong> each company gets its own random day, so the same-day co-movement of rivals hit by one failure is not preserved; this makes the spread of placebo averages somewhat too narrow.</li>
      <li><strong>What the percentile means:</strong> the share of random-day averages at or below the real one. It is not the probability that the effect is real, and this is not an exact randomization test, because random days are not exchangeable with launch days.</li>
    </ul>
    <p class="sim-note">How this works: the draws were computed from real price data on the author's computer (fixed seed ${escapeHtml(String(pl.seed))}), and this page replays them in the same order. Only the resulting averages are published, never the prices.</p>
  </div>`;
}

function chart(dist, shown, actual, domain) {
  const W = 720, H = 240, m = { t: 22, r: 16, b: 34, l: 40 };
  const [d0, d1] = domain;
  const x = linear([d0, d1], [m.l, W - m.r]);
  const full = bins(dist, d0, d1, BIN_COUNT);
  const top = niceDomain(0, Math.max(1, ...full.map((b) => b.n)), 4)[1];
  const y = linear([0, top], [H - m.b, m.t]);
  const bs = bins(shown, d0, d1, BIN_COUNT);
  let s = svgOpen(W, H, `Histogram of ${shown.length} replayed placebo averages; the vertical line marks the real failures.`);
  for (const b of full) if (b.n) s += rect(x(b.x0) + 0.5, y(b.n), x(b.x1) - x(b.x0) - 1, y(0) - y(b.n), 'class="sim-ghost"');
  for (const b of bs) if (b.n) {
    const beyond = actual >= 0 ? b.x0 >= actual : b.x1 <= actual;
    s += rect(x(b.x0) + 0.5, y(b.n), x(b.x1) - x(b.x0) - 1, y(0) - y(b.n), `class="${beyond ? "sim-bar beyond" : "sim-bar"}"`);
  }
  const last = shown[shown.length - 1];
  if (last !== undefined) s += `<circle class="sim-last" cx="${x(last).toFixed(2)}" cy="${(m.t - 8).toFixed(2)}" r="5"/>`
    + text(x(last) + 8, m.t - 4, `latest ${pct(last, 2)}`, "label muted");
  s += line(x(actual), m.t, x(actual), H - m.b, "sim-actual") + text(x(actual) + 6, m.t + 14, `Real failures ${pct(actual, 2)}`);
  return s + axisBottom(x, H - m.b, niceTicks(d0, d1, 7), (v) => pct(v, 1), m.l, W - m.r) + "</svg>";
}

export function mountPlacebo(root, { results }) {
  const el = root.querySelector("#placebo-sim");
  const pl = results.placebo;
  if (!el || !pl?.distribution?.length) return null;
  const dist = pl.distribution.filter(Number.isFinite), actual = pl.actual_mean_car, N = dist.length;
  const domain = niceDomain(Math.min(...dist, actual), Math.max(...dist, actual), 7);
  const chartEl = el.querySelector(".sim-chart"), out = el.querySelector(".sim-out");
  const reduce = typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches;
  let n = 0, timer = null;

  const paint = () => {
    const shown = dist.slice(0, n);
    chartEl.innerHTML = chart(dist, shown, actual, domain);
    const s = placeboShares(shown, actual);
    const side = actual >= 0 ? s.high : s.low;
    const dir = actual >= 0 ? "as high as" : "as low as";
    if (!n) { out.innerHTML = `<p>No draws yet. The pale outline shows where all ${N} draws will end up; press a button to fill it in.</p>`; return; }
    const done = n === N;
    const matches = done && Math.abs(s.twoSided - pl.two_sided_share) < 1e-12;
    out.innerHTML = `<dl class="lab-stats">
        <div><dt>Draws so far</dt><dd>${n} of ${N}</dd></div>
        <div><dt>${escapeHtml(`Draws ${dir} the real result`)}</dt><dd>${side} (${pct(side / n, 1, false)})</dd></div>
        <div><dt>Two-sided share</dt><dd>${num(s.twoSided, 3)}</dd></div>
      </dl>
      <p class="lab-read">${side === 0
        ? (n === 1 ? `The first random set was not ${escapeHtml(dir)} the real failures.` : `None of the ${n} random sets has been ${escapeHtml(dir)} the real failures so far.`)
        : `${side} of ${n} random sets of ordinary days ${side === 1 ? "was" : "were"} ${escapeHtml(dir)} the real failures.`}
        The two-sided share counts surprises in either direction, so it is double the smaller of the two tails.
        ${done ? ` With all draws in, it equals the share reported in the robustness checks${matches ? " (checked)" : ""}. A small share means ordinary days rarely produce a move this large; a large share means luck could easily explain it.` : ""}</p>`;
  };
  const stop = () => { if (timer) { clearInterval(timer); timer = null; } };
  el.querySelector(".sim-controls").addEventListener("click", (ev) => {
    const b = ev.target.closest("button[data-draw]");
    if (!b) return;
    const a = b.dataset.draw;
    stop();
    if (a === "reset") n = 0;
    else if (a === "all" && !reduce) {
      const step = Math.max(1, Math.ceil((N - n) / 40));
      timer = setInterval(() => { n = Math.min(N, n + step); paint(); if (n === N) stop(); }, 30);
      return;
    } else n = a === "all" ? N : Math.min(N, n + Number(a));
    paint();
  });
  paint();
  return { draw: (k) => { n = Math.min(N, n + k); paint(); }, state: () => ({ n, ...placeboShares(dist.slice(0, n), actual) }) };
}
