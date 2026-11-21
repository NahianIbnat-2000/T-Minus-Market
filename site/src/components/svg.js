// Tiny SVG helpers (replaces D3). Everything returns strings, so charts need no DOM.
import { escapeHtml } from "../format.js";

/** "Nice" tick values covering [lo, hi] with about n ticks. */
export function niceTicks(lo, hi, n = 6) {
  if (!Number.isFinite(lo) || !Number.isFinite(hi)) return [];
  if (lo === hi) { lo -= 1; hi += 1; }
  const raw = (hi - lo) / Math.max(1, n);
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw) || 10 * mag;
  const start = Math.ceil(lo / step - 1e-9) * step;
  const out = [];
  for (let v = start; v <= hi + step * 1e-9; v += step) out.push(Math.abs(v) < step * 1e-9 ? 0 : +v.toPrecision(12));
  return out;
}

/** Extend [lo, hi] outward to tick boundaries. */
export function niceDomain(lo, hi, n = 6) {
  const t = niceTicks(lo, hi, n);
  if (t.length < 2) return [lo, hi];
  const step = t[1] - t[0];
  return [Math.floor(lo / step - 1e-9) * step, Math.ceil(hi / step - 1e-9) * step];
}

export function linear([d0, d1], [r0, r1]) {
  const f = (v) => r0 + ((v - d0) / (d1 - d0 || 1)) * (r1 - r0);
  f.domain = [d0, d1];
  return f;
}

export function band(keys, [r0, r1], padding = 0.25) {
  const step = (r1 - r0) / Math.max(1, keys.length);
  const width = step * (1 - padding);
  const f = (k) => r0 + keys.indexOf(k) * step + (step - width) / 2;
  f.bandwidth = width;
  return f;
}

/** Equal-width histogram bins over [lo, hi]. */
export function bins(values, lo, hi, count = 40) {
  const w = (hi - lo) / count;
  const out = Array.from({ length: count }, (_, i) => ({ x0: lo + i * w, x1: lo + (i + 1) * w, n: 0 }));
  for (const v of values) {
    if (!Number.isFinite(v)) continue;
    const i = Math.min(count - 1, Math.max(0, Math.floor((v - lo) / w)));
    out[i].n += 1;
  }
  return out;
}

const f2 = (v) => (Math.round(v * 100) / 100).toString();

export const svgOpen = (W, H, desc) =>
  `<svg viewBox="0 0 ${W} ${H}" role="img" xmlns="http://www.w3.org/2000/svg"><desc>${escapeHtml(desc)}</desc>`;
export const line = (x1, y1, x2, y2, cls = "", extra = "") =>
  `<line class="${cls}" x1="${f2(x1)}" y1="${f2(y1)}" x2="${f2(x2)}" y2="${f2(y2)}" ${extra}/>`;
export const rect = (x, y, w, h, extra = "") =>
  `<rect x="${f2(x)}" y="${f2(y)}" width="${f2(Math.max(0, w))}" height="${f2(Math.max(0, h))}" ${extra}/>`;
export const text = (x, y, s, cls = "label", extra = "") =>
  `<text class="${cls}" x="${f2(x)}" y="${f2(y)}" ${extra}>${escapeHtml(s)}</text>`;
export const path = (pts, cls) =>
  pts.length ? `<path class="${cls}" d="M${pts.map(([x, y]) => `${f2(x)},${f2(y)}`).join("L")}"/>` : "";

/** Bottom axis at y with tick labels. */
export function axisBottom(scale, y, ticks, fmt, x0, x1) {
  let s = `<g class="axis">${line(x0, y, x1, y)}`;
  for (const t of ticks) {
    const x = scale(t);
    s += line(x, y, x, y + 5) + text(x, y + 18, fmt(t), "", 'text-anchor="middle"');
  }
  return s + "</g>";
}

/** Left axis at x with tick labels. */
export function axisLeft(scale, x, ticks, fmt, y0, y1) {
  let s = `<g class="axis">${line(x, y0, x, y1)}`;
  for (const t of ticks) {
    const y = scale(t);
    s += line(x - 5, y, x, y) + text(x - 8, y + 4, fmt(t), "", 'text-anchor="end"');
  }
  return s + "</g>";
}

let hatchCount = 0;
/** A hatched fill pattern (printed-figure look for confidence intervals). Returns [defs, url]. */
export function hatch(color = "#1C1C1C") {
  const id = `hatch-${++hatchCount}`;
  return [`<defs><pattern id="${id}" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">` +
    `<line x1="0" y1="0" x2="0" y2="6" stroke="${color}" stroke-width="1.2" stroke-opacity="0.55"/></pattern></defs>`, `url(#${id})`];
}
