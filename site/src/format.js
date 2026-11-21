// Formatting helpers. Every number shown on the site passes through here.

const MINUS = "−"; // typographic minus

/** 0.0123 -> "+1.23%"; signed by default; always a sign and a symbol, never colour alone. */
export function pct(x, digits = 1, signed = true) {
  if (x === null || x === undefined || !Number.isFinite(x)) return "n/a";
  const v = (100 * x).toFixed(digits);
  const n = Number(v);
  if (n === 0) return `${(0).toFixed(digits)}%`;
  const s = n > 0 ? (signed ? "+" : "") : MINUS;
  return `${s}${Math.abs(n).toFixed(digits)}%`;
}

export function num(x, digits = 2) {
  if (x === null || x === undefined || !Number.isFinite(x)) return "n/a";
  const v = x.toFixed(digits);
  return Number(v) < 0 ? `${MINUS}${Math.abs(Number(v)).toFixed(digits)}` : v;
}

/** p-values: "0.40", "0.012", "< 0.001". */
export function pval(p) {
  if (p === null || p === undefined || !Number.isFinite(p)) return "n/a";
  if (p < 0.001) return "< 0.001";
  return p < 0.01 ? p.toFixed(3) : p.toFixed(2);
}

/** "-1.6% to +2.2%" */
export function ci(lo, hi, digits = 1) {
  return `${pct(lo, digits)} to ${pct(hi, digits)}`;
}

/** Event-time label: 0 -> "T0", -1 -> "T-1", 3 -> "T+3" */
export function tLabel(t) {
  if (t === 0) return "T0";
  return t > 0 ? `T+${t}` : `T${MINUS}${Math.abs(t)}`;
}

/** "11 Jul 2019" */
export function date(iso) {
  if (!iso) return "n/a";
  const d = new Date(String(iso).slice(0, 10) + "T00:00:00Z");
  if (Number.isNaN(d.getTime())) return String(iso);
  return d.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
}

/** CSS class for a signed value, paired with a sign in the text. */
export function signClass(x) {
  if (!Number.isFinite(x) || x === 0) return "";
  return x < 0 ? "loss" : "gain";
}

export function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

/** Plain-language verdict for a two-sided test at 5%. */
export function verdict(p) {
  if (!Number.isFinite(p)) return "could not be tested";
  return p < 0.05 ? "is statistically detectable at the 5% level"
                  : "is not statistically detectable at the 5% level at this sample size";
}
