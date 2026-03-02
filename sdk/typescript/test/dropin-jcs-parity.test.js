import test from "node:test";
import assert from "node:assert/strict";

import { canonicalizeJson as sdkCanonicalize } from "../src/jcs.js";
import { canonicalizeJson as dropinCanonicalize } from "../../../dropins/aicp-core/typescript/src/aicp_core.mjs";

test("dropin canonicalizer matches sdk for safe integers and nesting", () => {
  const payload = { z: [1, { a: -9007199254740991 }], b: 2 };
  assert.equal(dropinCanonicalize(payload), sdkCanonicalize(payload));
});

test("dropin rejects unsafe integers and floats like sdk", () => {
  for (const value of [9007199254740993, -9007199254740993, 0.1]) {
    assert.throws(() => dropinCanonicalize({ x: value }));
    assert.throws(() => sdkCanonicalize({ x: value }));
  }
});
