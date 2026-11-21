// T-Minus Markets: browser event-study statistics.
//
// Works only from exported derived statistics (site/data/*.json): per firm-event CARs and
// their variances, and same-cluster CAR correlations. It re-runs the plan's primary test
// (BMP with the Kolari-Pynnonen cluster adjustment) on any subset a reader chooses.
// It must match pipeline/siteexport.py::bmp_kp_from_records within the tolerances in
// site/data/manifest.json (checked by tests/test_phase3_parity.py).
//
// No dependencies. ES module.

// ---------------------------------------------------------------- special functions
function logGamma(x) {
  // Lanczos approximation (g = 7, n = 9)
  const c = [0.99999999999980993, 676.5203681218851, -1259.1392167224028, 771.32342877765313,
    -176.61502916214059, 12.507343278686905, -0.13857109526572012, 9.9843695780195716e-6,
    1.5056327351493116e-7];
  if (x < 0.5) return Math.log(Math.PI / Math.sin(Math.PI * x)) - logGamma(1 - x);
  x -= 1;
  let a = c[0];
  const t = x + 7.5;
  for (let i = 1; i < 9; i++) a += c[i] / (x + i);
  return 0.5 * Math.log(2 * Math.PI) + (x + 0.5) * Math.log(t) - t + Math.log(a);
}

function betacf(a, b, x) {
  // Continued fraction for the incomplete beta (modified Lentz)
  const MAXIT = 300, EPS = 1e-15, FPMIN = 1e-300;
  const qab = a + b, qap = a + 1, qam = a - 1;
  let c = 1, d = 1 - (qab * x) / qap;
  if (Math.abs(d) < FPMIN) d = FPMIN;
  d = 1 / d;
  let h = d;
  for (let m = 1; m <= MAXIT; m++) {
    const m2 = 2 * m;
    let aa = (m * (b - m) * x) / ((qam + m2) * (a + m2));
    d = 1 + aa * d; if (Math.abs(d) < FPMIN) d = FPMIN;
    c = 1 + aa / c; if (Math.abs(c) < FPMIN) c = FPMIN;
    d = 1 / d; h *= d * c;
    aa = (-(a + m) * (qab + m) * x) / ((a + m2) * (qap + m2));
    d = 1 + aa * d; if (Math.abs(d) < FPMIN) d = FPMIN;
    c = 1 + aa / c; if (Math.abs(c) < FPMIN) c = FPMIN;
    d = 1 / d;
    const del = d * c;
    h *= del;
    if (Math.abs(del - 1) < EPS) break;
  }
  return h;
}

function betaInc(a, b, x) {
  // Regularised incomplete beta I_x(a, b)
  if (x <= 0) return 0;
  if (x >= 1) return 1;
  const bt = Math.exp(logGamma(a + b) - logGamma(a) - logGamma(b) + a * Math.log(x) + b * Math.log(1 - x));
  return x < (a + 1) / (a + b + 2) ? (bt * betacf(a, b, x)) / a : 1 - (bt * betacf(b, a, 1 - x)) / b;
}

/** Student t survival function P(T > t). */
export function tSf(t, df) {
  const x = df / (df + t * t);
  const tail = 0.5 * betaInc(df / 2, 0.5, x);
  return t >= 0 ? tail : 1 - tail;
}

/** Student t quantile: the q with P(T <= q) = p. */
export function tPpf(p, df) {
  if (p <= 0 || p >= 1) return NaN;
  if (p === 0.5) return 0;
  let lo = -1, hi = 1;
  while (1 - tSf(lo, df) > p) lo *= 2;
  while (1 - tSf(hi, df) < p) hi *= 2;
  for (let i = 0; i < 200; i++) {
    const mid = (lo + hi) / 2;
    if (1 - tSf(mid, df) < p) lo = mid; else hi = mid;
    if (hi - lo < 1e-14 * Math.max(1, Math.abs(mid))) break;
  }
  return (lo + hi) / 2;
}

function binomPmf(k, n) {
  return Math.exp(logGamma(n + 1) - logGamma(k + 1) - logGamma(n - k + 1) - n * Math.LN2);
}

/** Exact two-sided sign test with p = 0.5 (matches scipy.stats.binomtest for p = 0.5). */
export function signTest(pos, n) {
  if (n === 0) return NaN;
  const pk = binomPmf(pos, n);
  let p = 0;
  for (let i = 0; i <= n; i++) {
    const pi = binomPmf(i, n);
    if (pi <= pk * (1 + 1e-7)) p += pi;
  }
  return Math.min(1, p);
}

// ---------------------------------------------------------------- helpers
const mean = (a) => a.reduce((s, x) => s + x, 0) / a.length;
const sdev = (a) => {
  const m = mean(a);
  return Math.sqrt(a.reduce((s, x) => s + (x - m) ** 2, 0) / (a.length - 1));
};

function clusterCI(cars, clusters) {
  const N = cars.length;
  const ids = [...new Set(clusters)];
  const G = ids.length;
  const mu = mean(cars);
  if (G < 2) return { mu, lo: null, hi: null, G };
  const sums = new Map();
  cars.forEach((c, i) => sums.set(clusters[i], (sums.get(clusters[i]) || 0) + (c - mu)));
  let ss = 0;
  for (const v of sums.values()) ss += v * v;
  const se = Math.sqrt((G / (G - 1)) * ss) / N;
  const q = tPpf(0.975, G - 1);
  return { mu, lo: mu - q * se, hi: mu + q * se, G };
}

/** Index rho pairs once: Map "idA||idB" -> rho (both orders). */
export function indexRho(pairs) {
  const m = new Map();
  for (const [a, b, r] of pairs) { m.set(`${a}||${b}`, r); m.set(`${b}||${a}`, r); }
  return m;
}

// ---------------------------------------------------------------- tests
/**
 * Primary test on a subset of firm-event records.
 * @param {object[]} records  firm_events.json entries
 * @param {Map} rhoIndex      indexRho(rho[window])
 * @param {string} window     "primary" | "robust" | "descriptive"
 */
export function bmpKp(records, rhoIndex, window) {
  const rows = records.filter((r) => r.windows[window].car !== null);
  const N = rows.length;
  const cars = rows.map((r) => r.windows[window].car);
  const cl = rows.map((r) => r.cluster);
  const out = {
    mean: N ? mean(cars) : NaN, ci_low: null, ci_high: null, stat: null, p: null, n: N, clusters: 0,
    failures: new Set(rows.map((r) => r.launch_tag)).size, firms: new Set(rows.map((r) => r.ticker)).size,
    mean_corr: null,
  };
  if (!N) return out;
  const ci = clusterCI(cars, cl);
  out.clusters = ci.G; out.ci_low = ci.lo; out.ci_high = ci.hi;
  if (N < 3) return out;
  const scar = rows.map((r) => r.windows[window].car / Math.sqrt(r.windows[window].var));
  const t = (mean(scar) * Math.sqrt(N)) / sdev(scar);
  let S = 0, k = 0, sumRho = 0;
  for (let i = 0; i < N; i++) {
    for (let j = i + 1; j < N; j++) {
      if (cl[i] !== cl[j]) continue;
      const r = rhoIndex.get(`${rows[i].id}||${rows[j].id}`);
      if (r === undefined) continue;
      S += 2 * r; sumRho += r; k += 1;
    }
  }
  const adj = Math.sqrt(Math.max(1 - S / (N * (N - 1)), 1e-12) / (1 + S / N));
  const tAdj = t * adj;
  out.stat = tAdj;
  out.p = 2 * tSf(Math.abs(tAdj), Math.max(ci.G - 1, 1));
  out.mean_corr = k ? sumRho / k : 0;
  return out;
}

/** R1: one equal-weighted CAR per cluster; t-test and exact sign test across clusters. */
export function portfolio(records, window) {
  const rows = records.filter((r) => r.windows[window].car !== null);
  const byC = new Map();
  for (const r of rows) {
    if (!byC.has(r.cluster)) byC.set(r.cluster, []);
    byC.get(r.cluster).push(r.windows[window].car);
  }
  const pc = [...byC.values()].map(mean);
  const G = pc.length;
  if (G < 3) return { mean: G ? mean(pc) : NaN, clusters: G, t: null, p: null, ci_low: null, ci_high: null };
  const m = mean(pc), se = sdev(pc) / Math.sqrt(G), t = m / se, q = tPpf(0.975, G - 1);
  const pos = pc.filter((x) => x > 0).length, nz = pc.filter((x) => x !== 0).length;
  return { mean: m, clusters: G, t, p: 2 * tSf(Math.abs(t), G - 1), ci_low: m - q * se, ci_high: m + q * se,
           positive: pos, sign_p: signTest(pos, nz) };
}

/**
 * Subset filter for the Event Study Lab.
 * opts: { group, tickers: string[] | null, dropFlags: string[] (verdicts), dropLowConfidence, dropFallback }
 */
export function selectRecords(records, opts = {}) {
  const { group = "rival", tickers = null, dropFlags = [], dropLowConfidence = false, dropFallback = false } = opts;
  return records.filter((r) =>
    r.group === group &&
    (!tickers || tickers.includes(r.ticker)) &&
    !(r.flag && dropFlags.includes(r.flag.verdict)) &&
    !(dropLowConfidence && r.disclosure_confidence === "low") &&
    !(dropFallback && r.model !== "market_model"));
}

/** Cumulative abnormal return path (for charts), from the exported daily ARs. */
export function carPath(record, from = -5) {
  let c = 0;
  return record.path.filter((p) => p.t >= from).map((p) => {
    if (p.ar !== null) c += p.ar;
    return { t: p.t, car: p.ar === null ? null : c };
  });
}
