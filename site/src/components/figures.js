// Printed-figure ("plate") charts as SVG strings. No libraries, no DOM.
// Each plate has a caption stating unit, sample, window and specification, and a data
// table inside <details> so the numbers are available without the picture.
import { ci, escapeHtml, pct, tLabel } from "../format.js";
import { axisBottom, axisLeft, band, bins, hatch, line, linear, niceDomain, niceTicks, path, rect, svgOpen, text } from "./svg.js";

let plateNo = 0;
export function resetPlates() { plateNo = 0; }

function plate({ title, svg, caption, table }) {
  plateNo += 1;
  const no = String(plateNo).padStart(2, "0");
  return `<figure class="plate" role="group" aria-label="${escapeHtml(title)}">
    <div class="plate-head"><span class="plate-title">${escapeHtml(title)}</span><span class="plate-no">FIG. ${no}</span></div>
    ${svg}
    <figcaption>${caption}</figcaption>
    ${table ? `<details><summary>Show the numbers</summary>${table}</details>` : ""}
  </figure>`;
}

const finite = (a) => a.filter(Number.isFinite);

/** Cumulative abnormal return paths. series: [{label, points:[{t, car}], tone}] */
export function carPathsPlate({ title, series, caption, from = -5, to = 20, notes = [] }) {
  const W = 720, H = 340, m = { t: 16, r: 150, b: 34, l: 52 };
  const vals = finite(series.flatMap((s) => s.points.map((p) => p.car)));
  const [y0, y1] = niceDomain(Math.min(0, ...vals) - 0.01, Math.max(0, ...vals) + 0.01, 6);
  const y = linear([y0, y1], [H - m.b, m.t]);
  const x = linear([from - 1, to], [m.l, W - m.r]);
  const yt = niceTicks(y0, y1, 6);
  let s = svgOpen(W, H, `${title}. Cumulative abnormal return by trading day relative to the failure, set to zero at the close before the failure.`);
  for (const t of yt) s += line(m.l, y(t), W - m.r, y(t), "grid-line");
  s += line(m.l, y(0), W - m.r, y(0), "zero-line") + line(x(-0.5), m.t, x(-0.5), H - m.b, "day0-line");
  s += axisBottom(x, H - m.b, [-5, -1, 0, 1, 3, 5, 10, 15, 20].filter((t) => t >= from && t <= to), tLabel, m.l, W - m.r);
  s += axisLeft(y, m.l, yt, (v) => pct(v, 0), m.t, H - m.b);
  const labels = [];
  for (const ser of series) {
    const pts = ser.points.filter((p) => p.t >= from - 1 && p.t <= to && p.car !== null);
    s += path(pts.map((p) => [x(p.t), y(p.car)]), `series ${ser.tone || "neutral"} draw`).replace("<path", '<path style="--len: 2000"');
    const last = pts[pts.length - 1];
    if (last) labels.push({ y: y(last.car), x: x(last.t), text: `${ser.label} ${pct(last.car)}` });
  }
  labels.sort((a, b) => a.y - b.y);                       // keep end labels from overlapping
  for (let i = 1; i < labels.length; i++) labels[i].y = Math.max(labels[i].y, labels[i - 1].y + 16);
  for (const l of labels) s += text(l.x + 6, l.y + 4, l.text);
  for (const n of notes) {                                   // small numbered marker on a line
    const p = series.find((q) => q.label === n.series)?.points.find((q) => q.t === n.t);
    if (!p || p.car === null) continue;
    s += `<circle cx="${x(p.t).toFixed(2)}" cy="${y(p.car).toFixed(2)}" r="9" fill="none" stroke="#1C1C1C" stroke-width="1"/>`;
    s += text(x(p.t) - 4, y(p.car) + 22, n.mark, "label");
  }
  s += "</svg>";
  const at = (ser, t) => ser.points.find((p) => p.t === t)?.car ?? null;
  const table = `<table><thead><tr><th>Series</th><th class="num">CAR to ${tLabel(1)}</th><th class="num">CAR to ${tLabel(3)}</th><th class="num">CAR to ${tLabel(20)}</th></tr></thead><tbody>${
    series.map((ser) => `<tr><td>${escapeHtml(ser.label)}</td><td class="num">${pct(at(ser, 1))}</td><td class="num">${pct(at(ser, 3))}</td><td class="num">${pct(at(ser, 20))}</td></tr>`).join("")}</tbody></table>`;
  return plate({ title, svg: s, caption, table });
}

/** Estimates with 95% intervals. rows: [{label, mean, lo, hi, note, emphasis}] */
export function intervalPlate({ title, rows, caption }) {
  const W = 720, rowH = 34, m = { t: 14, r: 24, b: 34, l: 300 };
  const H = m.t + m.b + rowH * rows.length;
  const lim = Math.max(0.01, ...finite(rows.flatMap((r) => [r.lo, r.hi, r.mean])).map(Math.abs)) * 1.15;
  const [d0, d1] = niceDomain(-lim, lim, 6);
  const x = linear([d0, d1], [m.l, W - m.r]);
  const [defs, fill] = hatch();
  let s = svgOpen(W, H, `${title}. Each row shows an estimate with its 95% confidence interval.`) + defs;
  for (const t of niceTicks(d0, d1, 6)) s += line(x(t), m.t, x(t), H - m.b, "grid-line");
  s += line(x(0), m.t, x(0), H - m.b, "zero-line");
  rows.forEach((r, i) => {
    const cy = m.t + rowH * i + rowH / 2;
    s += text(0, cy + 4, r.label, r.emphasis ? "label" : "label muted", r.emphasis ? 'font-weight="700"' : "");
    if (Number.isFinite(r.lo) && Number.isFinite(r.hi)) {
      s += rect(x(r.lo), cy - 7, Math.max(1, x(r.hi) - x(r.lo)), 14, `class="ci-band" fill="${fill}"`);
      s += line(x(r.lo), cy, x(r.hi), cy, "", 'stroke="#1C1C1C"');
    }
    if (Number.isFinite(r.mean)) {
      s += `<circle class="dot" cx="${x(r.mean).toFixed(2)}" cy="${cy}" r="${r.emphasis ? 5.5 : 4.5}" fill="${r.mean < 0 ? "#D9452B" : "#1F4E8C"}"/>`;
    }
  });
  s += axisBottom(x, H - m.b, niceTicks(d0, d1, 6), (v) => pct(v, 0), m.l, W - m.r) + "</svg>";
  const table = `<table><thead><tr><th>Estimate</th><th class="num">Mean</th><th class="num">95% interval</th><th>Note</th></tr></thead><tbody>${
    rows.map((r) => `<tr><td>${escapeHtml(r.label)}</td><td class="num">${pct(r.mean)}</td><td class="num">${
      Number.isFinite(r.lo) ? ci(r.lo, r.hi) : "n/a"}</td><td>${escapeHtml(r.note || "")}</td></tr>`).join("")}</tbody></table>`;
  return plate({ title, svg: s, caption, table });
}

/** Failures per year; the part that enters the study is solid. */
export function yearBarsPlate({ title, failures, caption }) {
  const by = new Map();
  for (const f of failures) {
    const yr = Number(String(f.launch_utc).slice(0, 4));
    if (!Number.isFinite(yr)) continue;
    const v = by.get(yr) || { all: 0, inStudy: 0 };
    v.all += 1;
    if (f.in_rival_test || f.in_provider_case_series) v.inStudy += 1;
    by.set(yr, v);
  }
  const years = [...by.keys()].sort((a, b) => a - b);
  const W = 720, H = 240, m = { t: 12, r: 12, b: 30, l: 36 };
  const top = niceDomain(0, Math.max(1, ...years.map((yr) => by.get(yr).all)), 4)[1];
  const y = linear([0, top], [H - m.b, m.t]);
  const x = band(years, [m.l, W - m.r]);
  let s = svgOpen(W, H, `${title}. Orbital launch failures per year; the solid part of each bar enters the study.`);
  for (const t of niceTicks(0, top, 4)) s += line(m.l, y(t), W - m.r, y(t), "grid-line");
  for (const yr of years) {
    const v = by.get(yr);
    s += rect(x(yr), y(v.all), x.bandwidth, y(0) - y(v.all), 'fill="none" stroke="#1C1C1C"');
    if (v.inStudy) s += rect(x(yr), y(v.inStudy), x.bandwidth, y(0) - y(v.inStudy), 'fill="#1C1C1C"');
  }
  s += `<g class="axis">${line(m.l, H - m.b, W - m.r, H - m.b)}${years.filter((yr) => yr % 5 === 0)
    .map((yr) => text(x(yr) + x.bandwidth / 2, H - m.b + 18, String(yr), "", 'text-anchor="middle"')).join("")}</g>`;
  s += axisLeft(y, m.l, niceTicks(0, top, 4), (v) => String(v), m.t, H - m.b) + "</svg>";
  const table = `<table><thead><tr><th>Year</th><th class="num">Failures</th><th class="num">In the study</th></tr></thead><tbody>${
    years.map((yr) => `<tr><td>${yr}</td><td class="num">${by.get(yr).all}</td><td class="num">${by.get(yr).inStudy}</td></tr>`).join("")}</tbody></table>`;
  return plate({ title, svg: s, caption, table });
}

/** Histogram of placebo means with the real value marked. */
export function placeboPlate({ title, distribution, actual, caption }) {
  const W = 720, H = 260, m = { t: 14, r: 16, b: 34, l: 40 };
  const vals = finite([...distribution, actual]);
  const [d0, d1] = niceDomain(Math.min(...vals), Math.max(...vals), 7);
  const x = linear([d0, d1], [m.l, W - m.r]);
  const bs = bins(distribution, d0, d1, 40);
  const top = niceDomain(0, Math.max(1, ...bs.map((b) => b.n)), 4)[1];
  const y = linear([0, top], [H - m.b, m.t]);
  let s = svgOpen(W, H, `${title}. Average two-day abnormal returns on random non-event days; the vertical line marks the real failures.`);
  for (const b of bs) if (b.n) s += rect(x(b.x0) + 0.5, y(b.n), x(b.x1) - x(b.x0) - 1, y(0) - y(b.n), 'fill="none" stroke="#5E574C"');
  s += line(x(actual), m.t, x(actual), H - m.b, "", 'stroke="#1C1C1C" stroke-width="2"');
  s += text(x(actual) + 6, m.t + 12, `Real failures ${pct(actual)}`);
  s += axisBottom(x, H - m.b, niceTicks(d0, d1, 7), (v) => pct(v, 1), m.l, W - m.r) + "</svg>";
  return plate({ title, svg: s, caption, table: null });
}
