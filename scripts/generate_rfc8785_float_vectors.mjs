#!/usr/bin/env node
import { writeFileSync, mkdirSync } from 'node:fs';
import { dirname, resolve } from 'node:path';

const bitsList = [
  '0x0000000000000000', // +0
  '0x8000000000000000', // -0
  '0x3ff0000000000000', // 1
  '0xbff0000000000000', // -1
  '0x3fb999999999999a', // 0.1
  '0x3ff3c083126e978d', // 1.2345
  '0x3eb0c6f7a0b5ed8d', // around 1e-6
  '0x3e112e0be826d695', // around 1e-9
  '0x41cdcd6500000000', // 1e9
  '0x4341c37937e08000', // 1e16
  '0x444b1ae4d6e2ef50', // 1e21
  '0x444b1ae4d6e2ef4f', // just below 1e21
  '0x3ff0000000000001', // 1 + ulp
  '0x0010000000000000', // min normal
  '0x0000000000000001', // min subnormal
  '0x7fefffffffffffff', // max finite
  '0x3fefffffffffffff', // below 1
  '0x3f50624dd2f1a9fc', // 1e-4
  '0x3eb0c6f7a0b5ed8e', // near 1e-6 threshold
  '0x3eb0c6f7a0b5ed8c',
  '0x3cb0000000000000', // 2^-52-ish tiny
];

function fromBits(hex) {
  const buf = new ArrayBuffer(8);
  const dv = new DataView(buf);
  dv.setBigUint64(0, BigInt(hex));
  return dv.getFloat64(0);
}

const vectors = bitsList.map((bits) => {
  const n = fromBits(bits);
  return {
    bits,
    expected: JSON.stringify(n),
  };
});

const outPath = resolve('conformance/vectors/rfc8785_float64_vectors.json');
mkdirSync(dirname(outPath), { recursive: true });
writeFileSync(outPath, JSON.stringify({ vectors }, null, 2) + '\n', 'utf-8');
console.log(`Wrote ${outPath} (${vectors.length} vectors)`);
