import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { canonicalizeJson as sdkCanonicalize } from "../src/jcs.js";
import { canonicalizeJson as dropinCanonicalize } from "../../../dropins/aicp-core/typescript/src/aicp_core.mjs";

function fromBits(hex) {
  const bits = hex.replace(/^0x/, "");
  const buf = Buffer.from(bits, "hex");
  return buf.readDoubleBE(0);
}

test("dropin canonicalizer matches sdk for safe integers and nesting", () => {
  const payload = { z: [1, { a: -9007199254740991, f: 0.1 }], b: 2 };
  assert.equal(dropinCanonicalize(payload), sdkCanonicalize(payload));
});

test("dropin rejects unsafe integers and non-finite values like sdk", () => {
  for (const value of [9007199254740993, -9007199254740993, Infinity]) {
    assert.throws(() => dropinCanonicalize({ x: value }));
    assert.throws(() => sdkCanonicalize({ x: value }));
  }
});

test("shared float vectors match sdk and dropin tokens", () => {
  const vectors = JSON.parse(readFileSync(new URL("../../../conformance/vectors/rfc8785_float64_vectors.json", import.meta.url), "utf8"));
  for (const row of vectors.vectors) {
    const value = fromBits(row.bits);
    if (Number.isInteger(value) && Math.abs(value) > Number.MAX_SAFE_INTEGER) {
      assert.throws(() => sdkCanonicalize({ n: value }));
      assert.throws(() => dropinCanonicalize({ n: value }));
      continue;
    }
    assert.equal(sdkCanonicalize({ n: value }), `{"n":${row.expected}}`);
    assert.equal(dropinCanonicalize({ n: value }), `{"n":${row.expected}}`);
  }
});
