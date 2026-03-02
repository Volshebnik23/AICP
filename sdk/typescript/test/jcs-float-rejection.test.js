import test from "node:test";
import assert from "node:assert/strict";

import { canonicalizeJson } from "../src/jcs.js";

test("canonicalizeJson normalizes floats and negative zero", () => {
  assert.equal(canonicalizeJson({ score: 1.0, prob: 0.1, neg_zero: -0.0 }), '{"neg_zero":0,"prob":0.1,"score":1}');
});

test("canonicalizeJson normalizes exponent format", () => {
  assert.equal(canonicalizeJson({ v: 1.2e-7 }), '{"v":1.2e-7}');
});

test("canonicalizeJson rejects unsafe integers", () => {
  assert.throws(
    () => canonicalizeJson({ big: 9007199254740992 }),
    /Unsafe integer for AICP canonicalization/
  );
});
