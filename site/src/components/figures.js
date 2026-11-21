// Printed-figure ("plate") charts. Each returns an HTML string: an SVG drawn like a printed
// figure, a caption stating unit, sample, window and specification, and a data table
// inside <details> so the numbers are available without the picture.
import * as d3 from "d3";
import { ci, escapeHtml, pct, tLabel } from "../format.js";

let plateNo = 0;
let hatchId = 0;

export function resetPlates() { plateNo = 0; }

function hatch(svg, color) {
  const id = `hatch-${++hatchId}`;
  svg.append("defs").append("pattern").attr("id", id).attr("width", 6).attr("height", 6)
    .attr("patternUnits", "userSpaceOnUse").attr("patternTransform", "rotate(45)")
    .append("line").attr("x1", 0).attr("y1", 0).attr("x2", 0).attr("y2", 6)
    .attr("stroke", color).attr("stroke-width", 1.2).attr("stroke-opacity", 0.55);
  return `url(#${id})`;
}

function plate({ title, svg, caption, table, label }) {
  plateNo += 1;
  const no = String(plateNo).padStart(2, "0");
  return `<figure class="plate" role="group" aria-label="${escapeHtml(label || title)}">
    <div class="plate-head"><span class="plate-title">${escapeHtml(title)}</span><span class="plate-no">FIG. ${no}</span></div>
    ${svg}
    <figcaption>${caption}</figcaption>
    ${table ? `<details><summary>Show the numbers</summary>${table}</details>` : ""}
  </figure>`;
}

function newSvg(width, height, desc) {
  const el = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  const svg = d3.select(el).attr("viewBox", `0 0 ${width} ${height}`).attr("role", "img");
  svg.append("desc").text(desc);
  return svg;
}

/**
 * Cumulative abnormal return paths, one line per series, T-5..T+20 by default.
 * series: [{label, points:[{t, car}], tone: "loss"|"gain"|"neutral"}]
 */
export function carPathsPlate({ title, series, caption, from = -5, to = 20 }) {
  const W = 720, H = 340, m = { t: 16, r: 120, b: 34, l: 52 };
  const all = series.flatMap((s) => s.points.filter((p) => p.car !== null));
  const ext = d3.extent(all, (p) => p.car);
  const pad = 0.01;
  const y = d3.scaleLinear().domain([Math.min(ext[0] ?? 0, 0) - pad, Math.max(ext[1] ?? 0, 0) + pad]).nice()
    .range([H - m.b, m.t]);
  const x = d3.scaleLinear().domain([from, to]).range([m.l, W - m.r]);
  const svg = newSvg(W, H, `${title}. Cumulative abnormal return by trading day relative to the failure.`);
  svg.append("g").selectAll("line").data(y.ticks(6)).join("line").attr("class", "grid-line")
    .attr("x1", m.l).attr("x2", W - m.r).attr("y1", y).attr("y2", y);
  svg.append("line").attr("class", "zero-line").attr("x1", m.l).attr("x2", W - m.r).attr("y1", y(0)).attr("y2", y(0));
  svg.append("line").attr("class", "day0-line").attr("x1", x(0)).attr("x2", x(0)).attr("y1", m.t).attr("y2", H - m.b);
  svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.b})`)
    .call(d3.axisBottom(x).tickValues([-5, -1, 0, 1, 3, 5, 10, 15, 20].filter((t) => t >= from && t <= to)).tickFormat(tLabel).tickSizeOuter(0));
  svg.append("g").attr("class", "axis").attr("transform", `translate(${m.l},0)`)
    .call(d3.axisLeft(y).ticks(6).tickFormat((v) => pct(v, 0)).tickSizeOuter(0));
  const line = d3.line().defined((p) => p.car !== null).x((p) => x(p.t)).y((p) => y(p.car));
  series.forEach((s) => {
    const pts = s.points.filter((p) => p.t >= from && p.t <= to);
    const path = svg.append("path").attr("class", `series ${s.tone || "neutral"} draw`).attr("d", line(pts));
    const last = [...pts].reverse().find((p) => p.car !== null);
    if (last) {
      svg.append("text").attr("class", "label").attr("x", x(last.t) + 6).attr("y", y(last.car) + 4)
        .text(`${s.label} ${pct(last.car)}`);
    }
    path.attr("style", "--len: 2000");
  });
  const rows = series.map((s) => {
    const at = (t) => s.points.find((p) => p.t === t)?.car ?? null;
    return `<tr><td>${escapeHtml(s.label)}</td><td class="num">${pct(at(1))}</td><td class="num">${pct(at(3))}</td><td class="num">${pct(at(20))}</td></tr>`;
  }).join("");
  const table = `<table><thead><tr><th>Series</th><th class="num">CAR to T+1</th><th class="num">CAR to T+3</th><th class="num">CAR to T+20</th></tr></thead><tbody>${rows}</tbody></table>`;
  return plate({ title, svg: svg.node().outerHTML, caption, table });
}

/**
 * Estimates with 95% intervals, one row each (dot + hatched band).
 * rows: [{label, mean, lo, hi, note, emphasis}]
 */
export function intervalPlate({ title, rows, caption }) {
  const W = 720, rowH = 34, m = { t: 14, r: 24, b: 34, l: 300 };
  const H = m.t + m.b + rowH * rows.length;
  const vals = rows.flatMap((r) => [r.lo, r.hi, r.mean]).filter(Number.isFinite);
  const lim = Math.max(0.01, ...vals.map(Math.abs)) * 1.15;
  const x = d3.scaleLinear().domain([-lim, lim]).nice().range([m.l, W - m.r]);
  const svg = newSvg(W, H, `${title}. Each row shows an estimate with its 95% confidence interval.`);
  const fill = hatch(svg, "#1C1C1C");
  svg.append("g").selectAll("line").data(x.ticks(6)).join("line").attr("class", "grid-line")
    .attr("x1", x).attr("x2", x).attr("y1", m.t).attr("y2", H - m.b);
  svg.append("line").attr("class", "zero-line").attr("x1", x(0)).attr("x2", x(0)).attr("y1", m.t).attr("y2", H - m.b);
  rows.forEach((r, i) => {
    const cy = m.t + rowH * i + rowH / 2;
    svg.append("text").attr("class", `label${r.emphasis ? "" : " muted"}`).attr("x", 0).attr("y", cy + 4)
      .attr("font-weight", r.emphasis ? 700 : 400).text(r.label);
    if (Number.isFinite(r.lo) && Number.isFinite(r.hi)) {
      svg.append("rect").attr("class", "ci-band").attr("x", x(r.lo)).attr("width", Math.max(1, x(r.hi) - x(r.lo)))
        .attr("y", cy - 7).attr("height", 14).attr("fill", fill);
      svg.append("line").attr("stroke", "#1C1C1C").attr("x1", x(r.lo)).attr("x2", x(r.hi)).attr("y1", cy).attr("y2", cy);
    }
    if (Number.isFinite(r.mean)) {
      svg.append("circle").attr("class", "dot").attr("cx", x(r.mean)).attr("cy", cy).attr("r", r.emphasis ? 5.5 : 4.5)
        .attr("fill", r.mean < 0 ? "#D9452B" : "#1F4E8C");
    }
  });
  svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.b})`)
    .call(d3.axisBottom(x).ticks(6).tickFormat((v) => pct(v, 0)).tickSizeOuter(0));
  const table = `<table><thead><tr><th>Estimate</th><th class="num">Mean</th><th class="num">95% interval</th><th>Note</th></tr></thead><tbody>${
    rows.map((r) => `<tr><td>${escapeHtml(r.label)}</td><td class="num">${pct(r.mean)}</td><td class="num">${
      Number.isFinite(r.lo) ? ci(r.lo, r.hi) : "n/a"}</td><td>${escapeHtml(r.note || "")}</td></tr>`).join("")}</tbody></table>`;
  return plate({ title, svg: svg.node().outerHTML, caption, table });
}

/** Failures per year, with the part that enters the study highlighted. */
export function yearBarsPlate({ title, failures, caption }) {
  const byYear = d3.rollups(failures, (v) => ({ all: v.length, inStudy: v.filter((f) => f.in_rival_test || f.in_provider_case_series).length }),
    (f) => Number(String(f.launch_utc).slice(0, 4))).sort((a, b) => a[0] - b[0]);
  const W = 720, H = 240, m = { t: 12, r: 12, b: 30, l: 36 };
  const x = d3.scaleBand().domain(byYear.map((d) => d[0])).range([m.l, W - m.r]).padding(0.25);
  const y = d3.scaleLinear().domain([0, d3.max(byYear, (d) => d[1].all) || 1]).nice().range([H - m.b, m.t]);
  const svg = newSvg(W, H, `${title}. Orbital launch failures per year; the dark part of each bar enters the study.`);
  svg.append("g").selectAll("line").data(y.ticks(4)).join("line").attr("class", "grid-line")
    .attr("x1", m.l).attr("x2", W - m.r).attr("y1", y).attr("y2", y);
  const g = svg.append("g");
  byYear.forEach(([yr, v]) => {
    g.append("rect").attr("x", x(yr)).attr("width", x.bandwidth()).attr("y", y(v.all)).attr("height", y(0) - y(v.all))
      .attr("fill", "none").attr("stroke", "#1C1C1C");
    if (v.inStudy) g.append("rect").attr("x", x(yr)).attr("width", x.bandwidth()).attr("y", y(v.inStudy))
      .attr("height", y(0) - y(v.inStudy)).attr("fill", "#1C1C1C");
  });
  svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.b})`)
    .call(d3.axisBottom(x).tickValues(x.domain().filter((yr) => yr % 5 === 0)).tickSizeOuter(0));
  svg.append("g").attr("class", "axis").attr("transform", `translate(${m.l},0)`).call(d3.axisLeft(y).ticks(4).tickSizeOuter(0));
  const table = `<table><thead><tr><th>Year</th><th class="num">Failures</th><th class="num">In the study</th></tr></thead><tbody>${
    byYear.map(([yr, v]) => `<tr><td>${yr}</td><td class="num">${v.all}</td><td class="num">${v.inStudy}</td></tr>`).join("")}</tbody></table>`;
  return plate({ title, svg: svg.node().outerHTML, caption, table });
}

/** Histogram of placebo means with the real value marked. */
export function placeboPlate({ title, distribution, actual, caption }) {
  const W = 720, H = 260, m = { t: 14, r: 16, b: 34, l: 40 };
  const ext = d3.extent([...distribution, actual]);
  const x = d3.scaleLinear().domain(ext).nice().range([m.l, W - m.r]);
  const bins = d3.bin().domain(x.domain()).thresholds(40)(distribution);
  const y = d3.scaleLinear().domain([0, d3.max(bins, (b) => b.length) || 1]).nice().range([H - m.b, m.t]);
  const svg = newSvg(W, H, `${title}. Distribution of average two-day abnormal returns on random non-event days; vertical line marks the real failures.`);
  svg.append("g").selectAll("rect").data(bins).join("rect").attr("x", (b) => x(b.x0) + 0.5)
    .attr("width", (b) => Math.max(0, x(b.x1) - x(b.x0) - 1)).attr("y", (b) => y(b.length))
    .attr("height", (b) => y(0) - y(b.length)).attr("fill", "none").attr("stroke", "#5E574C");
  svg.append("line").attr("stroke", "#1C1C1C").attr("stroke-width", 2).attr("x1", x(actual)).attr("x2", x(actual))
    .attr("y1", m.t).attr("y2", H - m.b);
  svg.append("text").attr("class", "label").attr("x", x(actual) + 6).attr("y", m.t + 12).text(`Real failures ${pct(actual)}`);
  svg.append("g").attr("class", "axis").attr("transform", `translate(0,${H - m.b})`)
    .call(d3.axisBottom(x).ticks(7).tickFormat((v) => pct(v, 1)).tickSizeOuter(0));
  return plate({ title, svg: svg.node().outerHTML, caption, table: null });
}
