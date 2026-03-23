import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

import { canonicalizeJson } from "../src/jcs.js";
import { messageHashFromBody } from "../src/hashing.js";
import { verifyPrevHashChain } from "../src/chain.js";

const coreTv = JSON.parse(
  readFileSync(new URL("../../../fixtures/core_tv.json", import.meta.url), "utf8")
);

test("canonicalization sorts object keys by Unicode code point order", () => {
  const payload = { "😀": 1, "\ue000": 2 };
  assert.equal(canonicalizeJson(payload), '{"":2,"😀":1}');
});

test("TV-03 second message hash matches fixture and chain contract", () => {
  const tv3 = coreTv["TV-03"];
  const { m1, m2 } = tv3;
  const m1Hash = messageHashFromBody(m1.object);
  const m2Hash = messageHashFromBody(m2.object);

  assert.equal(m1Hash, m1.message_hash);
  assert.equal(m2.object.prev_msg_hash, m1Hash);
  assert.equal(m2Hash, m2.message_hash);
  assert.deepEqual(
    verifyPrevHashChain([
      { message_hash: m1Hash },
      { message_hash: m2Hash, prev_msg_hash: m2.object.prev_msg_hash },
    ]),
    []
  );
});
