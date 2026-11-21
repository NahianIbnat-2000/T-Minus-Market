import { test } from "node:test";
import assert from "node:assert/strict";
import { dodge, laneOf, whyText } from "../src/tools/timeline.js";

test("lanes: provider case first, then rival test, else not in study", () => {
  assert.equal(laneOf({ in_provider_case_series: true, in_rival_test: true }), "provider");
  assert.equal(laneOf({ in_provider_case_series: false, in_rival_test: true }), "rival");
  assert.equal(laneOf({ in_provider_case_series: false, in_rival_test: false }), "none");
});

test("dodge stacks only marks closer than the gap", () => {
  assert.deepEqual(dodge([10, 12, 30, 13], 7), [0, 1, 0, 2]);
});

test("exclusion codes become plain language; unknown codes stay readable", () => {
  assert.equal(whyText("no_firm_map_match"), "the rocket's maker is not a listed company");
  assert.equal(whyText("some_new_code"), "some new code");
  assert.equal(whyText(null), null);
});
