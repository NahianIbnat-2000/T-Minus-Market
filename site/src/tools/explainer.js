// Expected vs Actual explorer: a SIMULATED example (no real prices) that shows how an abnormal return
// is measured. A made-up stock follows the market with a chosen sensitivity (beta); the reader sets the
// market's move and a company-specific shock on T0 and sees the market model separate the two.
import { escapeHtml, num, pct, signClass } from "../format.js";
import { axisBottom, axisLeft, line, linear, niceTicks, rect, svgOpen, text } from "../components/svg.js";

const EST_DAYS = 220;                 // length of the simulated estimation window
const SEED = 9;
const HALF_POINT = 0.005;           // below this the market effect is too small to mention

/** Small seeded generator so the example looks the same for every reader. */
function rng(seed) {
  let s = seed >>> 0;
  const u = () => { s = (s * 1664525 + 1013904223) >>> 0; return (s + 0.5) / 4294967296; };
  return () => Math.sqrt(-2 * Math.log(u())) * Math.cos(2 * Math.PI * u());   // standard normal
}

/** Simulated estimation window and ordinary least squares fit. Exported for tests. */
export function simulate(beta) {
  const z = rng(SEED);
  const mkt = [], stk = [];
  for (let i = 0; i < EST_DAYS; i++) {
    const m = 0.01 * z();
    mkt.push(m);
    stk.push(0.0003 + beta * m + 0.018 * z());
  }
  const mx = mkt.reduce((a, b) => a + b, 0) / EST_DAYS, my = stk.reduce((a, b) => a + b, 0) / EST_DAYS;
  let sxy = 0, sxx = 0;
  for (let i = 0; i < EST_DAYS; i++) { sxy += (mkt[i] - mx) * (stk[i] - my); sxx += (mkt[i] - mx) ** 2; }
  const b = sxy / sxx, a = my - b * mx;
  return { mkt, stk, alpha: a, beta: b };
}

/** One event day: expected = alpha + beta * market; actual = expected + shock; abnormal = actual - expected. */
export function eventDay(fit, trueBeta, marketMove, shock) {
  const actual = 0.0003 + trueBeta * marketMove + shock;
  const expected = fit.alpha + fit.beta * marketMove;
  return { actual, expected, abnormal: actual - expected, naive: actual };
}

const CONTROLS = [
  { name: "beta", label: "How strongly the stock follows the market (beta)", min: 0.2, max: 2.5, step: 0.1, value: 1.5, fmt: (v) => num(v, 1) },
  { name: "market", label: "Market move on T0", min: -0.04, max: 0.04, step: 0.005, value: -0.03, fmt: (v) => pct(v, 1) },
  { name: "shock", label: "Company-specific news on T0 (the failure)", min: -0.15, max: 0.05, step: 0.01, value: -0.08, fmt: (v) => pct(v, 0) },
];

export function explainerHtml() {
  return `<div class="tool explainer-tool" id="explainer" data-tool="explainer">
    <div class="tool-head"><span class="tool-kicker">Interactive tool · simulated example</span><h3>Expected vs Actual</h3>
      <p>A made-up stock, not real data. Move the sliders to see why the study compares each stock with what the market predicted, not with zero.</p></div>
    <form class="ex-form" aria-label="Set up the simulated example">
      ${CONTROLS.map((c) => `<label class="ex-ctl"><span>${escapeHtml(c.label)}: <output name="${c.name}-out"></output></span>
        <input type="range" name="${c.name}" min="${c.min}" max="${c.max}" step="${c.step}" value="${c.value}"></label>`).join("")}
    </form>
    <div class="ex-charts"><div class="ex-scatter"></div><div class="ex-bars"></div></div>
    <ul class="ex-legend" aria-label="Legend">
      <li><span class="sw sw-dot" aria-hidden="true"></span>Ordinary days in the estimation window (stock against market)</li>
      <li><span class="sw sw-line" aria-hidden="true"></span>Fitted market model: the expected return for any market move</li>
      <li><span class="sw sw-exp" aria-hidden="true"></span>Expected return on the event day</li>
      <li><span class="sw sw-act" aria-hidden="true"></span>Actual return on the event day; the gap is the abnormal return</li>
    </ul>
    <p class="ex-window">Event window here: one day (T0). The study adds the abnormal returns of T0 and T+1 (the two-day CAR).</p>
    <div class="ex-out" aria-live="polite"></div>
    <p class="tool-source">Simulated data only. The study's real expected and actual returns are not shown because the price data may not be republished; the real abnormal returns for each maker case are in the Results section (cumulative paths) and in the <a href="../case-study.html#s6">paper</a>. <a href="../methods.html#model">Market model</a></p>
  </div>`;
}

function scatter(sim, ev, marketMove) {
  const W = 360, H = 300, m = { t: 14, r: 12, b: 34, l: 44 };
  const lim = 0.05;
  const x = linear([-lim, lim], [m.l, W - m.r]), y = linear([-0.16, 0.08], [H - m.b, m.t]);
  const ticksX = niceTicks(-lim, lim, 4), ticksY = niceTicks(-0.16, 0.08, 6);
  let s = svgOpen(W, H, "Simulated daily returns of the stock against the market in the estimation window, the fitted line, and the event day.");
  for (const t of ticksY) s += line(m.l, y(t), W - m.r, y(t), "grid-line");
  sim.mkt.forEach((v, i) => { s += `<circle class="ex-dot" cx="${x(v).toFixed(1)}" cy="${y(Math.max(-0.16, Math.min(0.08, sim.stk[i]))).toFixed(1)}" r="2"/>`; });
  s += line(x(-lim), y(sim.alpha + sim.beta * -lim), x(lim), y(sim.alpha + sim.beta * lim), "ex-fit");
  s += line(x(marketMove), y(ev.expected), x(marketMove), y(ev.actual), "ex-gap");
  s += `<circle class="ex-exp" cx="${x(marketMove).toFixed(1)}" cy="${y(ev.expected).toFixed(1)}" r="5"/>`;
  s += `<circle class="ex-act" cx="${x(marketMove).toFixed(1)}" cy="${y(ev.actual).toFixed(1)}" r="5"/>`;
  s += text(m.l + 4, m.t + 10, "each dot: one ordinary day", "label muted");
  return s + axisBottom(x, H - m.b, ticksX, (v) => pct(v, 0), m.l, W - m.r) + axisLeft(y, m.l, ticksY, (v) => pct(v, 0), m.t, H - m.b)
    + text(W - m.r - 4, H - 4, "market return (benchmark index)", "label muted", 'text-anchor="end"')
    + `<text class="label muted" transform="translate(11 ${(m.t + H - m.b) / 2}) rotate(-90)" text-anchor="middle">stock return</text>` + "</svg>";
}

function bars(ev) {
  const W = 360, H = 300, m = { t: 14, r: 12, b: 34, l: 44 };
  const items = [["Actual", ev.actual, "ex-act-bar"], ["Expected", ev.expected, "ex-exp-bar"], ["Abnormal", ev.abnormal, "ex-ab-bar"]];
  const y = linear([-0.2, 0.1], [H - m.b, m.t]);
  const bw = (W - m.l - m.r) / items.length;
  let s = svgOpen(W, H, "Bars for the actual, expected and abnormal return on the event day.");
  s += text(m.l + 4, m.t + 10, "return on the event day (T0)", "label muted");
  const ticks = niceTicks(-0.2, 0.1, 6);
  for (const t of ticks) s += line(m.l, y(t), W - m.r, y(t), "grid-line");
  s += line(m.l, y(0), W - m.r, y(0), "zero-line");
  items.forEach(([lab, v, cls], i) => {
    const x0 = m.l + i * bw + bw * 0.2, w = bw * 0.6, top = y(Math.max(0, v)), h = Math.abs(y(v) - y(0));
    s += rect(x0, top, w, h, `class="${cls}"`);
    s += text(x0 + w / 2, H - m.b + 16, lab, "label", 'text-anchor="middle"');
    s += text(x0 + w / 2, v < 0 ? y(v) + 14 : y(v) - 5, pct(v, 1), "label", 'text-anchor="middle"');
  });
  return s + axisLeft(y, m.l, ticks, (v) => pct(v, 0), m.t, H - m.b) + "</svg>";
}

export function mountExplainer(root) {
  const el = root.querySelector("#explainer");
  if (!el) return null;
  const form = el.querySelector("form");
  const val = (n) => Number(form.elements[n].value);
  let cacheBeta = null, sim = null;
  const paint = () => {
    const beta = val("beta"), marketMove = val("market"), shock = val("shock");
    for (const c of CONTROLS) form.elements[`${c.name}-out`].value = c.fmt(val(c.name));
    if (cacheBeta !== beta) { sim = simulate(beta); cacheBeta = beta; }
    const ev = eventDay(sim, beta, marketMove, shock);
    el.querySelector(".ex-scatter").innerHTML = scatter(sim, ev, marketMove);
    el.querySelector(".ex-bars").innerHTML = bars(ev);
    el.querySelector(".ex-out").innerHTML = `<p class="lab-read">The stock moved <strong class="${signClass(ev.actual)}">${pct(ev.actual, 1)}</strong>.
      Given the market's move, the fitted line expected <strong class="${signClass(ev.expected)}">${pct(ev.expected, 1)}</strong>
      (estimated beta ${num(sim.beta, 2)}). The difference, <strong class="${signClass(ev.abnormal)}">${pct(ev.abnormal, 1)}</strong>, is the abnormal return:
      the part the market cannot explain. Here it is close to the company news you set (${pct(shock, 0)}), while the raw move
      ${Math.abs(ev.expected) >= HALF_POINT ? `mixes the news with the market's move, which alone would have meant ${pct(ev.expected, 1)}` : "happens to be close too, because the market barely moved"}.</p>`;
  };
  form.addEventListener("input", paint);
  paint();
  return { paint };
}
