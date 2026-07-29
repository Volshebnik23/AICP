import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { evaluateCapnegVector } from "../src/capneg_v02.js";
import { resolveProfileComposition } from "../src/profile_composition.js";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "../../..");
const readJson = (relative) =>
  JSON.parse(fs.readFileSync(path.join(root, relative), "utf8"));

const vectors = readJson(
  "fixtures/extensions/capneg_v0_2/cross_language_vectors.json",
);
const rules = readJson("registry/aicp_profile_composition_rules.json");
const reasonCodes = new Set(
  readJson("registry/capneg_reason_codes.json").map((entry) => entry.id),
);
const keyMap = readJson("fixtures/keys/GT_public_keys.json");
const registeredExtensions = new Set(
  readJson("registry/extension_ids.json").map((entry) => entry.id),
);

function normalizedResolution(result) {
  return {
    composition: result.composition,
    composition_hash: result.composition_hash,
    core_suite: result.core_suite,
    required_suites: result.required_suites,
    required_extensions: result.required_extensions,
    required_crypto_profiles: result.required_crypto_profiles,
    required_policy_categories: result.required_policy_categories,
    component_compatibility_marks: result.component_compatibility_marks,
    error_ids: result.errors.map((entry) => entry.code),
  };
}

test("CAPNEG v0.2 composition resolver matches shared Python vectors", () => {
  for (const vector of vectors.composition_vectors) {
    const actual = resolveProfileComposition(vector.input, rules);
    const expected = {
      ...vector.expected,
      error_ids: vector.expected.errors.map((entry) => entry.code),
    };
    delete expected.errors;
    assert.deepEqual(
      normalizedResolution(actual),
      expected,
      vector.id,
    );
  }
});

test("CAPNEG v0.2 reducer, contract binding, and projection match shared vectors", () => {
  for (const vector of vectors.negotiation_vectors) {
    assert.deepEqual(
      evaluateCapnegVector(vector, {
        rules,
        reasonCodes,
        keyMap,
        registeredExtensions,
      }),
      {
        error_ids: vector.expected.error_ids,
        final_state: vector.expected.final_state,
      },
      vector.id,
    );
  }
});
