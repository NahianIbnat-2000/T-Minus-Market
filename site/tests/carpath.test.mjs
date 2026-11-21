import { test } from "node:test";
import assert from "node:assert/strict";
import { carPath } from "../src/stats/eventstudy.js";

const rec = { path: [-5, -4, -3, -2, -1, 0, 1, 2].map((t) => ({ t, ar: t === -5 ? -0.12 : t === 0 ? -0.08 : t === 1 ? -0.02 : 0.001 })) };

test("path is zero at T-1 and equals CAR[0,t] after the failure", () => {
  const p = new Map(carPath(rec, -5).map((q) => [q.t, q.car]));
  assert.equal(p.get(-1), 0);
  assert.ok(Math.abs(p.get(1) - (-0.10)) < 1e-12);           // CAR[0,+1]
  assert.ok(Math.abs(p.get(2) - (-0.099)) < 1e-12);
});

test("news before the failure shows as a move into T-1, not as a shifted start", () => {
  const p = new Map(carPath(rec, -5).map((q) => [q.t, q.car]));
  assert.ok(Math.abs(p.get(-6) - (0.12 - 0.004)) < 1e-12);   // starts above zero, then the day -5 drop
  assert.ok(Math.abs(p.get(-5) - (-0.004)) < 1e-12);
});

test("a missing day breaks the line instead of being treated as zero", () => {
  const gap = { path: rec.path.map((q) => (q.t === 1 ? { ...q, ar: null } : q)) };
  const p = new Map(carPath(gap, -5).map((q) => [q.t, q.car]));
  assert.equal(p.get(1), null); assert.equal(p.get(2), null);
});
