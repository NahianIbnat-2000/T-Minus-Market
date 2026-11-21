// Parity runner: node site/tests/parity.mjs <site_data_dir> <cases.json> <out.json>
// Computes every case with the browser module so Python can compare.
import { readFileSync, writeFileSync } from "node:fs";
import { bmpKp, indexRho, portfolio, selectRecords, signTest, tPpf, tSf } from "../src/stats/eventstudy.js";

const [dataDir, casesPath, outPath] = process.argv.slice(2);
const records = JSON.parse(readFileSync(`${dataDir}/firm_events.json`, "utf8"));
const rho = JSON.parse(readFileSync(`${dataDir}/rho.json`, "utf8"));
const cases = JSON.parse(readFileSync(casesPath, "utf8"));

const out = { tests: [], portfolio: [], t: [], sign: [] };
for (const c of cases.tests) {
  const sel = selectRecords(records, c.opts);
  out.tests.push({ name: c.name, ...bmpKp(sel, indexRho(rho[c.window]), c.window) });
  out.portfolio.push({ name: c.name, ...portfolio(sel, c.window) });
}
for (const [x, df] of cases.t_points) out.t.push({ x, df, sf: tSf(x, df), ppf975: tPpf(0.975, df) });
for (const [k, n] of cases.sign_points) out.sign.push({ k, n, p: signTest(k, n) });
writeFileSync(outPath, JSON.stringify(out));
