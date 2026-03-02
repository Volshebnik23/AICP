import test from "node:test";
import assert from "node:assert/strict";

import { canonicalizeJson } from "../src/jcs.js";

test("canonicalizeJson rejects float values", () => {
  assert.throws(
    () => canonicalizeJson({ score: 0.1 }),
    /Floats are not supported by AICP Core v0.1/
  );
});

test("canonicalizeJson rejects unsafe integers", () => {
  assert.throws(
    () => canonicalizeJson({ score: 9007199254740993 }),
    /safe range/
  );
});

test("canonicalizeJson allows safe integer values", () => {
  assert.equal(canonicalizeJson({ score: 9007199254740991 }), '{"score":9007199254740991}');
});
