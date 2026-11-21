import { test } from "node:test";
import assert from "node:assert/strict";
import { placeboShares } from "../src/tools/placebo.js";

test("two-sided share uses the same rule as the Python pipeline", () => {
  const d = [-0.02, -0.01, 0, 0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07];
  const s = placeboShares(d, 0.05);              // >= 0.05: 3 of 10; <= 0.05: 8 of 10
  assert.equal(s.high, 3); assert.equal(s.low, 8);
  assert.ok(Math.abs(s.twoSided - 0.6) < 1e-12);
});

test("empty replay has no share", () => {
  assert.equal(placeboShares([], 0.01).twoSided, null);
});
