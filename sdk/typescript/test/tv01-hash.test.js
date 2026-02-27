import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import test from "node:test";
import assert from "node:assert/strict";

import { objectHash } from "../src/hashing.js";

test("TV-01 contract hash matches fixture", () => {
  const fixturePath = resolve(process.cwd(), "../../fixtures/core_tv.json");
  const fixture = JSON.parse(readFileSync(fixturePath, "utf-8"));
  const tv = fixture["TV-01"];
  const recomputed = objectHash(tv.object_type, tv.object);
  assert.equal(recomputed, tv.object_hash);
});
