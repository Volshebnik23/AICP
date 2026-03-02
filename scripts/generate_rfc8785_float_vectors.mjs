#!/usr/bin/env node
import { writeFileSync } from 'node:fs';
import { resolve } from 'node:path';

const OUT = resolve(process.cwd(), 'conformance/vectors/rfc8785_float64_vectors.json');

const vectors = [
  '8000000000000000', // -0
  '0000000000000000', // +0
  '0000000000000001', // min subnormal
  '000fffffffffffff', // max subnormal
  '0010000000000000', // min normal
  '3fb999999999999a', // 0.1
  '3fe0000000000000', // 0.5
  '3ff3c083126e978d', // 1.2345
  '3eb0c6f7a0b5ed8d', // near 1e-6 above
  '3eb0c6f7a0b5ed8c', // near 1e-6 below
  '444b1ae4d6e2ef4f', // near 1e21 below
  '444b1ae4d6e2ef50', // 1e21 boundary-ish
  '7fefffffffffffff'  // max finite
];

function fromBits(hex) {
  const buf = Buffer.from(hex, 'hex');
  return buf.readDoubleBE(0);
}

const out = {
  generated_by: 'scripts/generate_rfc8785_float_vectors.mjs',
  generator_runtime: process.version,
  vectors: vectors.map((bits) => {
    const n = fromBits(bits);
    return { bits: `0x${bits}`, expected: JSON.stringify(n) };
  }),
};

writeFileSync(OUT, `${JSON.stringify(out, null, 2)}\n`, 'utf8');
console.log(`wrote ${OUT}`);
