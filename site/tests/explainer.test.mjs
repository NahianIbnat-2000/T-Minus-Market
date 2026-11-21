import { test } from "node:test";
import assert from "node:assert/strict";
import { eventDay, simulate } from "../src/tools/explainer.js";

test("simulated fit recovers the chosen beta roughly, and is the same every time", () => {
  const a = simulate(1.5), b = simulate(1.5);
  assert.equal(a.beta, b.beta);
  assert.ok(Math.abs(a.beta - 1.5) < 0.35);
});

test("abnormal return isolates the company shock from a market move", () => {
  const fit = simulate(1.5);
  const ev = eventDay(fit, 1.5, -0.03, -0.08);
  assert.ok(Math.abs(ev.abnormal - -0.08) < Math.abs(ev.actual - -0.08));
  assert.ok(Math.abs(ev.actual - ev.expected - ev.abnormal) < 1e-15);
});
