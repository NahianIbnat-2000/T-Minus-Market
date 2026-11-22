// Failure Timeline: every orbital launch failure since 2000 on one strip, sorted into three lanes
// (rocket's maker listed / listed competitor studied / not in the study). Click or tab to a mark for details.
import { date, escapeHtml, num } from "../format.js";
import { axisBottom, line, linear, svgOpen, text } from "../components/svg.js";

const LANES = [
  { key: "provider", label: "Rocket's maker listed", cls: "tl-provider" },
  { key: "rival", label: "Listed competitor studied", cls: "tl-rival" },
  { key: "none", label: "Not in the study", cls: "tl-none" },
];

const WHY = {
  no_firm_map_match: "the rocket's maker is not a listed company",
  provider_not_listed_or_not_owner_on_date: "the maker was not listed, or did not own the rocket, on that date",
  no_segment_for_vehicle: "the rocket is not in the size and market table, so no direct competitor could be matched",
};

/** Plain-language reasons from the codes in exclusion_log_02.csv ("a; b"). */
export function whyText(codes) {
  if (!codes) return null;
  return String(codes).split(";").map((c) => c.trim()).filter(Boolean)
    .map((c) => WHY[c] || c.replace(/_/g, " ")).join("; ");
}

export function laneOf(f) {
  if (f.in_provider_case_series) return "provider";
  if (f.in_rival_test) return "rival";
  return "none";
}

const yearFrac = (iso) => {
  const d = new Date(String(iso).slice(0, 10) + "T00:00:00Z");
  const y = d.getUTCFullYear(), start = Date.UTC(y, 0, 1), end = Date.UTC(y + 1, 0, 1);
  return y + (d.getTime() - start) / (end - start);
};

/** Stack marks that would overlap: returns a level (0, 1, 2...) per item, in input order. */
export function dodge(xs, gap) {
  const order = xs.map((x, i) => [x, i]).sort((a, b) => a[0] - b[0]);
  const lastX = [], level = new Array(xs.length);
  for (const [x, i] of order) {
    let k = 0;
    while (lastX[k] !== undefined && x - lastX[k] < gap) k++;
    lastX[k] = x; level[i] = k;
  }
  return level;
}

export function timelineHtml({ failures }) {
  if (!failures?.length) return "";
  const counts = Object.fromEntries(LANES.map((l) => [l.key, failures.filter((f) => laneOf(f) === l.key).length]));
  return `<div class="tool timeline-tool" id="timeline" data-tool="timeline">
    <div class="tool-head"><span class="tool-kicker">Interactive tool</span><h3>Failure Timeline</h3>
      <p>Every orbital launch failure since the start of the sample, one mark each. Select a mark to see the launch and why it is, or is not, in the study.</p></div>
    <form class="tl-form" aria-label="Filter the timeline">
      <fieldset><legend>Show</legend>
        ${LANES.map((l) => `<label class="lab-opt"><input type="checkbox" name="lane" value="${l.key}" checked> <span class="tl-key ${l.cls}" aria-hidden="true"></span>${
          escapeHtml(l.label)} <span class="lab-count">(${counts[l.key]})</span></label>`).join("")}
      </fieldset>
      <label class="tl-search"><span>Rocket name</span><input type="search" name="q" placeholder="for example, Vega" autocomplete="off"></label>
    </form>
    <div class="tl-chart"></div>
    <div class="tl-detail" aria-live="polite"></div>
    <p class="tool-source">Source: GCAT (J. McDowell), CC-BY; failure means a GCAT success score below 0.75. Only failures in the lane for the study have stock-market observations; most historical failures involve no listed company. <a href="../methods.html#sample">Sample definitions</a></p>
  </div>`;
}

function chart(items, all, selected) {
  const W = 720, laneH = 64, m = { t: 8, r: 12, b: 30, l: 150 };
  const H = m.t + m.b + laneH * LANES.length;
  const years = all.map((f) => yearFrac(f.launch_utc)).filter(Number.isFinite);
  const y0 = Math.floor(Math.min(...years)), y1 = Math.ceil(Math.max(...years) + 0.001);
  const x = linear([y0, y1], [m.l, W - m.r]);
  let s = svgOpen(W, H, "Timeline of orbital launch failures by date, in three lanes by whether a listed company was involved.", "group");
  const ticks = [];
  for (let y = Math.ceil(y0 / 5) * 5; y <= y1; y += 5) ticks.push(y);
  for (const t of ticks) s += line(x(t), m.t, x(t), H - m.b, "grid-line");
  LANES.forEach((lane, li) => {
    const top = m.t + li * laneH, mid = top + laneH / 2;
    s += line(m.l, top + laneH, W - m.r, top + laneH, "grid-line");
    s += text(0, mid + 4, lane.label, "label");
    const inLane = items.filter((f) => laneOf(f) === lane.key);
    const xs = inLane.map((f) => x(yearFrac(f.launch_utc)));
    const lv = dodge(xs, 7);
    inLane.forEach((f, i) => {
      const k = lv[i], off = (k % 2 ? 1 : -1) * Math.ceil(k / 2) * 8;
      const cy = Math.max(top + 6, Math.min(top + laneH - 6, mid + off));
      const sel = selected === f.launch_tag;
      s += `<circle class="tl-mark ${lane.cls}${sel ? " sel" : ""}" data-tag="${escapeHtml(f.launch_tag)}" cx="${xs[i].toFixed(2)}" cy="${cy.toFixed(2)}" r="${sel ? 6 : 4}" tabindex="0" role="button" aria-label="${
        escapeHtml(`${f.vehicle}, ${date(f.launch_utc)}, ${lane.label}`)}"><title>${escapeHtml(`${f.vehicle}, ${date(f.launch_utc)}`)}</title></circle>`;
    });
  });
  return s + axisBottom(x, H - m.b, ticks, (v) => String(v), m.l, W - m.r) + "</svg>";
}

function detail(f) {
  if (!f) return `<p class="tl-hint">Select a mark to see details.</p>`;
  const lane = laneOf(f);
  const status = lane === "provider"
    ? `In the study as a case: the rocket's maker (${escapeHtml(f.listed_providers.join(", ") || "listed firm")}) traded on a stock exchange.`
    : lane === "rival"
      ? `In the competitor test: listed rivals ${escapeHtml(f.rival_tickers.join(", "))} were measured.`
      : `Not in the study: ${escapeHtml(whyText(f.why_not_in_sample) || "no listed maker or listed direct competitor on that day")}.`;
  const row = (k, v) => (v ? `<dt>${k}</dt><dd>${escapeHtml(v)}</dd>` : "");
  return `<article class="anomaly tl-card">
    <header><span class="no">LAUNCH ${escapeHtml(f.launch_tag)}</span><span class="stamp" aria-hidden="true">FAILURE</span></header>
    <h4>${escapeHtml(f.vehicle)}, ${escapeHtml(date(f.launch_utc))}</h4>
    <dl>${row("Operator", f.agency)}${row("Site", f.site)}${row("GCAT code", f.gcat_code)}${
      f.score !== null && f.score !== undefined ? `<dt>Success score</dt><dd>${num(f.score, 2)} (a failure is below 0.75)</dd>` : ""}</dl>
    <p class="finding">${status}</p>
  </article>`;
}

export function mountTimeline(root, { failures }) {
  const el = root.querySelector("#timeline");
  if (!el || !failures?.length) return null;
  const all = [...failures].sort((a, b) => String(a.launch_utc).localeCompare(String(b.launch_utc)));
  const form = el.querySelector("form"), chartEl = el.querySelector(".tl-chart"), det = el.querySelector(".tl-detail");
  let selected = null;
  const visible = () => {
    const lanes = [...form.querySelectorAll('input[name="lane"]:checked')].map((i) => i.value);
    const q = form.querySelector('input[name="q"]').value.trim().toLowerCase();
    return all.filter((f) => lanes.includes(laneOf(f)) && (!q || String(f.vehicle).toLowerCase().includes(q)));
  };
  const paint = () => {
    const items = visible();
    if (selected && !items.some((f) => f.launch_tag === selected)) selected = null;
    chartEl.innerHTML = chart(items, all, selected) + `<p class="tl-count">${items.length} of ${all.length} failures shown.</p>`;
    det.innerHTML = detail(all.find((f) => f.launch_tag === selected));
  };
  const pick = (tag) => {
    selected = tag; paint();
    [...chartEl.querySelectorAll(".tl-mark")].find((m) => m.dataset.tag === tag)?.focus();
  };
  chartEl.addEventListener("click", (e) => { const m = e.target.closest(".tl-mark"); if (m) pick(m.dataset.tag); });
  chartEl.addEventListener("keydown", (e) => {
    const m = e.target.closest(".tl-mark");
    if (m && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); pick(m.dataset.tag); }
  });
  form.addEventListener("input", paint);
  form.addEventListener("submit", (e) => e.preventDefault());
  paint();
  return { pick, visible };
}
