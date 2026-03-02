import test from "node:test";
import assert from "node:assert/strict";

import { canonicalizeJson } from "../src/jcs.js";

test("canonicalizeJson rejects float values", () => {
  assert.throws(
    () => canonicalizeJson({ score: 0.1 }),
    /Floats are not supported by AICP Core v0.1/
  );
});

test("canonicalizeJson allows integer values", () => {
  assert.equal(canonicalizeJson({ score: 1 }), '{"score":1}');
});
