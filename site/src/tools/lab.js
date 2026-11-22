// Event Study Lab: re-runs the prespecified rival test (BMP with Kolari-Pynnonen cluster adjustment)
// on any subset the reader picks. Uses only the exported derived statistics.
import { bmpKp, indexRho, selectRecords } from "../stats/eventstudy.js";
import { ci, escapeHtml, num, pct, pval, signClass, tLabel, verdict } from "../format.js";
import { axisBottom, line, linear, niceDomain, niceTicks, rect, svgOpen, text } from "../components/svg.js";

const WINDOWS = [
  { key: "primary", label: (w) => `${tLabel(w[0])} to ${tLabel(w[1])}`, note: "main window" },
  { key: "robust", label: (w) => `${tLabel(w[0])} to ${tLabel(w[1])}`, note: "wider window" },
  { key: "descriptive", label: (w) => `${tLabel(w[0])} to ${tLabel(w[1])}`, note: "one month, descriptive" },
];

const FLAG_LABEL = {
  confounded: "Same-day company news (for example, a new contract)",
  possibly_confounded: "Possible same-day company news",
  sector_move: "Sector-wide move on the same day",
};

function defaults(rivals) {
  return { window: "primary", tickers: [...new Set(rivals.map((r) => r.ticker))], dropFlags: [],
           dropLowConfidence: false, dropFallback: false };
}

const plural = (n, one, many = `${one}s`) => `${n} ${n === 1 ? one : many}`;

const sameState = (a, b) => a.window === b.window && a.dropLowConfidence === b.dropLowConfidence &&
  a.dropFallback === b.dropFallback && a.dropFlags.length === b.dropFlags.length &&
  a.tickers.length === b.tickers.length && a.tickers.every((t) => b.tickers.includes(t));

/** Static markup; mountLab() wires it up. */
export function labHtml({ firmEvents, manifest }) {
  const rivals = firmEvents.filter((r) => r.group === "rival");
  const firms = [...new Map(rivals.map((r) => [r.ticker, r.firm])).entries()];
  const verdicts = [...new Set(rivals.filter((r) => r.flag).map((r) => r.flag.verdict))];
  const nLow = rivals.filter((r) => r.disclosure_confidence === "low").length;
  const nFb = rivals.filter((r) => r.model !== "market_model").length;
  const w = manifest.windows;
  const check = (name, value, label, count, checked) =>
    `<label class="lab-opt"><input type="checkbox" name="${name}" value="${escapeHtml(value)}"${checked ? " checked" : ""}> ${escapeHtml(label)}${
      count !== null ? ` <span class="lab-count">(${count})</span>` : ""}</label>`;
  return `<div class="tool lab" id="lab" data-tool="lab">
    <div class="tool-head"><span class="tool-kicker">Interactive tool</span><h3>Event Study Lab</h3>
      <p>Change the sample and the test re-runs in your browser, using the same method as the main result.</p></div>
    <form class="lab-form" aria-label="Choose the sample for the test">
      <fieldset><legend>Window</legend>
        ${WINDOWS.map((o, i) => `<label class="lab-opt"><input type="radio" name="window" value="${o.key}"${i === 0 ? " checked" : ""}> ${
          escapeHtml(o.label(w[o.key]))} <span class="lab-count">${escapeHtml(o.note)}</span></label>`).join("")}
      </fieldset>
      <fieldset><legend>Companies</legend>
        ${firms.map(([t, f]) => check("ticker", t, `${f} (${t})`, rivals.filter((r) => r.ticker === t).length, true)).join("")}
      </fieldset>
      <fieldset><legend>Leave out</legend>
        ${verdicts.map((v) => check("flag", v, FLAG_LABEL[v] || v, rivals.filter((r) => r.flag?.verdict === v).length, false)).join("")}
        ${nLow ? check("low", "1", "Failures with uncertain timing", nLow, false) : ""}
        ${nFb ? check("fallback", "1", "Firms with a short price history", nFb, false) : ""}
      </fieldset>
      <button type="button" class="lab-reset">Back to the main test</button>
    </form>
    <div class="lab-out" aria-live="polite"></div>
  </div>`;
}

function readForm(form) {
  const all = (n) => [...form.querySelectorAll(`input[name="${n}"]:checked`)].map((i) => i.value);
  return { window: all("window")[0] || "primary", tickers: all("ticker"), dropFlags: all("flag"),
           dropLowConfidence: all("low").length > 0, dropFallback: all("fallback").length > 0 };
}

function stripSvg(rows, window, res) {
  const W = 720, H = 120, m = { l: 20, r: 20, t: 18, b: 30 };
  const cars = rows.map((r) => r.windows[window].car);
  const lim = Math.max(0.02, ...cars.map(Math.abs), Math.abs(res.ci_low ?? 0), Math.abs(res.ci_high ?? 0)) * 1.1;
  const [d0, d1] = niceDomain(-lim, lim, 6);
  const x = linear([d0, d1], [m.l, W - m.r]);
  let s = svgOpen(W, H, "Each dot is one company's abnormal return after one failure. The band is the 95% interval of the average; the tall mark is the average.");
  if (Number.isFinite(res.ci_low)) s += rect(x(res.ci_low), m.t, x(res.ci_high) - x(res.ci_low), H - m.t - m.b, 'class="lab-band"');
  s += line(x(0), m.t - 6, x(0), H - m.b, "zero-line");
  rows.forEach((r, i) => {
    const c = r.windows[window].car;
    const jitter = ((i * 37) % 11) - 5;                         // fixed offset so dots do not hide each other
    s += `<circle cx="${x(c).toFixed(2)}" cy="${(H - m.b) / 2 + m.t / 2 + jitter * 3}" r="4" fill="${c < 0 ? "#E8604C" : "#14A38B"}" fill-opacity="0.75"><title>${
      escapeHtml(`${r.firm}, after ${r.vehicle} (${r.day0}): ${pct(c)}`)}</title></circle>`;
  });
  if (Number.isFinite(res.mean)) s += line(x(res.mean), m.t - 8, x(res.mean), H - m.b + 2, "lab-mean")
    + text(x(res.mean) + 5, m.t - 2, `average ${pct(res.mean, 2)}`, "label");
  return s + axisBottom(x, H - m.b, niceTicks(d0, d1, 6), (v) => pct(v, 0), m.l, W - m.r) + "</svg>";
}

function render(out, state, base, ctx) {
  const rows = selectRecords(ctx.records, { group: "rival", tickers: state.tickers, dropFlags: state.dropFlags,
    dropLowConfidence: state.dropLowConfidence, dropFallback: state.dropFallback })
    .filter((r) => r.windows[state.window].car !== null);
  const res = bmpKp(rows, ctx.rho[state.window], state.window);
  const isMain = sameState(state, base);
  const few = res.clusters < ctx.minClusters;
  const status = isMain
    ? `<p class="lab-status main">This is the prespecified main test.${ctx.matches ? " It matches the result in the report exactly." : ""}</p>`
    : `<p class="lab-status explore">Exploratory: you chose this sample after seeing the data, so treat the p-value as a description, not a test.</p>`;
  if (!rows.length) { out.innerHTML = status + `<p class="lab-empty">No company reactions match this choice.</p>`; return; }
  const b = ctx.baseRes;
  const setting = (label, a, c) => `<tr class="${a !== c ? "changed" : ""}"><td>${escapeHtml(label)}</td><td>${escapeHtml(a)}</td><td>${escapeHtml(c)}${a !== c ? " (changed)" : ""}</td></tr>`;
  const stat = (label, a, c) => `<tr><td>${escapeHtml(label)}</td><td class="num">${a}</td><td class="num">${c}</td></tr>`;
  const wl = (k) => `${tLabel(ctx.windows[k][0])} to ${tLabel(ctx.windows[k][1])}`;
  const listOr = (arr, none) => (arr.length ? arr.join(", ") : none);
  const compare = `<table class="lab-compare"><caption class="visually-hidden">Prespecified baseline compared with your selection</caption>
    <thead><tr><th></th><th>Prespecified baseline</th><th>Your selection</th></tr></thead><tbody>
    ${setting("Event window", wl(base.window), wl(state.window))}
    ${setting("Companies", listOr(base.tickers, "none"), listOr(state.tickers, "none"))}
    ${setting("Left out", "nothing", listOr([...state.dropFlags.map((f) => f.replace(/_/g, " ")), ...(state.dropLowConfidence ? ["uncertain timing"] : []), ...(state.dropFallback ? ["short price history"] : [])], "nothing"))}
    ${setting("Expected-return model", "market model (fallback where flagged)", "market model (fallback where flagged)")}
    ${ctx.est ? setting("Estimation window", ctx.est, ctx.est) : ""}
    ${stat("Average CAR", pct(b.mean, 2), pct(res.mean, 2))}
    ${stat("95% interval", b.ci_low !== null ? ci(b.ci_low, b.ci_high, 2) : "n/a", res.ci_low !== null ? ci(res.ci_low, res.ci_high, 2) : "n/a")}
    ${stat("Standardized test p", b.p !== null ? pval(b.p) : "n/a", res.p !== null ? pval(res.p) : "n/a")}
    ${stat("Reactions / independent events", `${b.n} / ${b.clusters}`, `${res.n} / ${res.clusters}`)}
    </tbody></table>`;
  out.innerHTML = `${status}
    <div class="lab-big"><span class="lab-num ${signClass(res.mean)}">${pct(res.mean, 2)}</span>
      <span class="lab-unit">average abnormal return, ${escapeHtml(tLabel(ctx.windows[state.window][0]))} to ${escapeHtml(tLabel(ctx.windows[state.window][1]))}</span></div>
    ${isMain ? "" : compare}
    <dl class="lab-stats">
      <div><dt>95% interval</dt><dd>${res.ci_low !== null ? ci(res.ci_low, res.ci_high, 2) : "n/a"}</dd></div>
      <div><dt>Adjusted t</dt><dd>${res.stat !== null ? num(res.stat) : "n/a"}</dd></div>
      <div><dt>p-value</dt><dd>${res.p !== null ? pval(res.p) : "n/a"}</dd></div>
      <div><dt>Sample</dt><dd>${plural(res.n, "reaction")}, ${plural(res.failures, "failure")}, ${plural(res.firms, "company", "companies")}, ${plural(res.clusters, "independent event")}</dd></div>
    </dl>
    <p class="lab-read">${res.p !== null ? `In plain words: this average ${escapeHtml(verdict(res.p))}.` : ""}${
      few ? ` <strong>Caution:</strong> fewer than ${ctx.minClusters} independent events, which is below the minimum set in advance, so the test is not reliable here.` : ""}</p>
    <figure class="lab-strip">${stripSvg(rows, state.window, res)}
      <figcaption>Each dot is one company's reaction to one failure (coral below zero, teal above). Hover a dot for details. The shaded band is the 95% interval of the average.</figcaption></figure>`;
}

/** Attach behaviour after the report HTML is in the page. */
export function mountLab(root, { firmEvents, rho, manifest, results }) {
  const el = root.querySelector("#lab");
  if (!el) return null;
  const form = el.querySelector("form"), out = el.querySelector(".lab-out");
  const records = firmEvents.filter((r) => r.group === "rival");
  const base = defaults(records);
  const rhoIdx = Object.fromEntries(Object.entries(rho).map(([k, v]) => [k, indexRho(v)]));
  const check = bmpKp(records.filter((r) => r.windows.primary.car !== null), rhoIdx.primary, "primary");
  const matches = results?.primary && Math.abs(check.mean - results.primary.mean_car) <= manifest.parity_tolerances.car_and_ci_abs
    && Math.abs(check.p - results.primary.p) <= manifest.parity_tolerances.p_value_abs;
  const ctx = { records, rho: rhoIdx, windows: manifest.windows, minClusters: manifest.min_rival_clusters ?? 0, matches, baseRes: check,
    est: results?.settings?.estimation_window ? `${-results.settings.estimation_window[0]} to ${-results.settings.estimation_window[1]} trading days before T0` : null };
  const update = () => render(out, readForm(form), base, ctx);
  form.addEventListener("change", update);
  el.querySelector(".lab-reset").addEventListener("click", () => { form.reset(); update(); });
  update();
  return { update };
}
