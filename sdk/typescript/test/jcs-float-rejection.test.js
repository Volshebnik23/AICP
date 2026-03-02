import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import { canonicalizeJson } from "../src/jcs.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const vectorsPath = path.resolve(__dirname, "../../../conformance/vectors/rfc8785_float64_vectors.json");

function floatFromBits(bitsHex) {
  const buf = new ArrayBuffer(8);
  const dv = new DataView(buf);
  dv.setBigUint64(0, BigInt(bitsHex));
  return dv.getFloat64(0);
}

test("canonicalizeJson matches float vectors", () => {
  const vectors = JSON.parse(fs.readFileSync(vectorsPath, "utf-8")).vectors;
  for (const entry of vectors) {
    const n = floatFromBits(entry.bits);
    if (Number.isInteger(n) && !Number.isSafeInteger(n)) {
      assert.throws(() => canonicalizeJson({ x: n }), /safe range/);
    } else {
      assert.equal(canonicalizeJson({ x: n }), `{"x":${entry.expected}}`);
    }
  }
});

test("canonicalizeJson rejects unsafe integers", () => {
  assert.throws(
    () => canonicalizeJson({ score: 9007199254740993 }),
    /safe range/
  );
});

test("canonicalizeJson rejects non-finite numbers", () => {
  assert.throws(() => canonicalizeJson({ score: Infinity }), /non-finite/);
  assert.throws(() => canonicalizeJson({ score: NaN }), /non-finite/);
});
