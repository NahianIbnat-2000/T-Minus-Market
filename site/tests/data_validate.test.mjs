// The report must fail loudly, naming what is missing, when its data are incomplete.
import { test } from "node:test";
import assert from "node:assert/strict";
import { validate } from "../src/data.js";

const ok = { manifest: {}, results: { primary: {} }, firmEvents: [], failures: [], rho: {} };

test("complete data pass validation", () => { assert.equal(validate(ok), ok); });
test("missing parts are named", () => {
  assert.throws(() => validate({ ...ok, firmEvents: undefined }), /firmEvents/);
  assert.throws(() => validate({ ...ok, results: {} }), /results\.primary/);
  assert.throws(() => validate({ broken: true }), /manifest/);
});
