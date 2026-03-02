import test from "node:test";
import assert from "node:assert/strict";

import { canonicalizeJson as canonicalizeDropin } from "../../../dropins/aicp-core/typescript/src/aicp_core.mjs";

test("dropin canonicalizeJson normalizes numeric forms", () => {
  assert.equal(canonicalizeDropin({ score: 1.0, prob: 0.1, neg_zero: -0.0 }), '{"neg_zero":0,"prob":0.1,"score":1}');
  assert.equal(canonicalizeDropin({ v: 1.2e-7 }), '{"v":1.2e-7}');
});

test("dropin canonicalizeJson rejects unsafe integers", () => {
  assert.throws(() => canonicalizeDropin({ big: 9007199254740992 }), /Unsafe integer for AICP canonicalization/);
});
