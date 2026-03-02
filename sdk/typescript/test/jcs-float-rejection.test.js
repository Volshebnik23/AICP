import test from "node:test";
import assert from "node:assert/strict";

import { canonicalizeJson } from "../src/jcs.js";

test("canonicalizeJson accepts finite float values", () => {
  assert.equal(canonicalizeJson({ score: 0.1 }), '{"score":0.1}');
  assert.equal(canonicalizeJson({ score: 1.0 }), '{"score":1}');
});

test("canonicalizeJson rejects non-finite floats", () => {
  assert.throws(
    () => canonicalizeJson({ score: Number.POSITIVE_INFINITY }),
    /non-finite/
  );
});

test("canonicalizeJson rejects unsafe integers", () => {
  assert.throws(
    () => canonicalizeJson({ score: 9007199254740993 }),
    /safe range/
  );
});
