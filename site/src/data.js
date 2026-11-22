// Loads site/data/*.json (served from the site root by Vite's publicDir).
const BASE = "./";

async function getJson(name) {
  const res = await fetch(`${BASE}${name}`);
  if (!res.ok) throw new Error(`Could not load ${name} (${res.status})`);
  return res.json();
}

export async function loadAll() {
  // Single-file build: data is embedded in <script type="application/json" id="site-data">.
  const inline = typeof document !== "undefined" && document.getElementById("site-data");
  if (inline) return validate(JSON.parse(inline.textContent));
  const [manifest, results, firmEvents, failures, rho] = await Promise.all([
    getJson("manifest.json"), getJson("results.json"), getJson("firm_events.json"),
    getJson("failures.json"), getJson("rho.json"),
  ]);
  return validate({ manifest, results, firmEvents, failures, rho });
}

const REQUIRED = { manifest: "object", results: "object", firmEvents: "array", failures: "array", rho: "object" };

/** Fail loudly, naming what is missing, instead of rendering a half-empty report. */
export function validate(d) {
  const bad = Object.entries(REQUIRED).filter(([k, t]) => (t === "array" ? !Array.isArray(d?.[k]) : !d?.[k] || typeof d[k] !== "object")).map(([k]) => k);
  if (!bad.length && !d.results.primary) bad.push("results.primary");
  if (bad.length) throw new Error(`missing or invalid: ${bad.join(", ")}`);
  return d;
}

/** Derived counts used in the text (never typed by hand). */
export function counts({ failures, firmEvents, results }) {
  const rivals = firmEvents.filter((r) => r.group === "rival");
  const providers = firmEvents.filter((r) => r.group === "provider_failure");
  const years = failures.map((f) => Number(String(f.launch_utc).slice(0, 4))).filter(Number.isFinite);
  return {
    failures: failures.length,
    firstYear: years.length ? Math.min(...years) : null,
    lastYear: years.length ? Math.max(...years) : null,
    providerFailures: providers.length,
    rivalFailures: new Set(rivals.map((r) => r.launch_tag)).size,
    rivalFirmEvents: rivals.length,
    rivalFirms: [...new Set(rivals.map((r) => r.firm))],
    clusters: results.primary?.n_clusters ?? new Set(rivals.map((r) => r.cluster)).size,
    flagged: rivals.filter((r) => r.flag).length,
  };
}
