import { test } from "node:test";
import assert from "node:assert/strict";
import { ci, pct, pval, tLabel, verdict } from "../src/format.js";

test("percentages carry a sign and a symbol", () => {
  assert.equal(pct(0.0123), "+1.2%");
  assert.equal(pct(-0.0123, 2), "−1.23%");
  assert.equal(pct(0), "0.0%");
  assert.equal(pct(NaN), "n/a");
  assert.equal(ci(-0.0162, 0.0218, 2), "−1.62% to +2.18%");
});

test("p-values and event-time labels", () => {
  assert.equal(pval(0.4027), "0.40");
  assert.equal(pval(0.0056), "0.006");
  assert.equal(pval(0.0001), "< 0.001");
  assert.equal(tLabel(0), "T0");
  assert.equal(tLabel(3), "T+3");
  assert.equal(tLabel(-1), "T−1");
});

test("verdict never says 'no effect'", () => {
  assert.match(verdict(0.40), /not statistically detectable/);
  assert.match(verdict(0.01), /is statistically detectable/);
  assert.doesNotMatch(verdict(0.40), /no effect/);
});
