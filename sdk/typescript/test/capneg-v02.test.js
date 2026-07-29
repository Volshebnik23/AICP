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
        error_observations: vector.expected_error_observations,
        final_state: vector.expected_final_state,
      },
      vector.id,
    );
  }
});

test("CAPNEG v0.2 load-bearing rules have direct hand-authored assertions", () => {
  const catalog = readJson(
    "fixtures/extensions/capneg_v0_2/negative_cases.json",
  );
  const cases = new Map(catalog.cases.map((entry) => [entry.id, entry]));
  const expected = {
    N52: { codes: ["CAPNEG_TRANSCRIPT_SESSION_MISMATCH", "DECISION_SESSION_MISMATCH"], state: "PARTIALLY_ACCEPTED" },
    N53: { codes: ["CAPNEG_TRANSCRIPT_CONTRACT_MISMATCH", "DECISION_CONTRACT_MISMATCH"], state: "PARTIALLY_ACCEPTED" },
    N56: { codes: ["AUTHENTICATED_ACCEPTANCE_SIGNATURE_REQUIRED"], state: "PARTIALLY_ACCEPTED" },
    N58: { codes: ["ACCEPTANCE_SIGNATURE_INVALID", "AUTHENTICATED_ACCEPTANCE_SIGNATURE_REQUIRED"], state: "ACCEPTED" },
    N59: { codes: ["CAPNEG_SIGNATURE_INVALID", "MISSING_DECLARATION_BINDING", "PROFILE_SET_UNSUPPORTED", "SELECTION_OUTSIDE_DECLARATION"], state: "COLLECTING_DECLARATIONS" },
    N60: { codes: ["CAPNEG_SIGNATURE_INVALID"], state: "COLLECTING_DECLARATIONS" },
    N61: { codes: ["CAPNEG_SIGNATURE_INVALID"], state: "PROPOSED" },
    N69: { codes: ["STALE_CAPABILITIES_DECLARATION"], state: "PROPOSED" },
    N73: { codes: ["REVISION_REJECTED"], state: "REJECTED" },
    N76: { codes: ["PARTICIPANT_REQUIRED_CRYPTO_MISSING"], state: "COLLECTING_DECLARATIONS" },
    N77: { codes: ["SELECTION_OUTSIDE_DECLARATION"], state: "COLLECTING_DECLARATIONS" },
    N78: { codes: ["SELECTION_OUTSIDE_DECLARATION"], state: "COLLECTING_DECLARATIONS" },
    N79: { codes: ["NEGOTIATION_SESSION_MISMATCH", "NEGOTIATION_SUPERSESSION_CONTEXT_MISMATCH"], state: "ACCEPTED" },
    N83: { codes: ["PROJECTION_ACCEPTANCE_NOT_ESTABLISHED", "PROJECTION_ACCEPTED_RESULT_HASH_MISMATCH", "PROJECTION_PROFILE_SET_MISMATCH"], state: "ACCEPTED" },
    N88: { codes: ["CONTRACT_ID_MISMATCH", "CORE_CONTRACT_SCHEMA_INVALID"], state: "ACCEPTED" },
  };
  for (const [caseId, assertion] of Object.entries(expected)) {
    const actual = evaluateCapnegVector(cases.get(caseId), {
      rules,
      reasonCodes,
      keyMap,
      registeredExtensions,
    });
    assert.deepEqual(
      [...new Set(actual.error_observations.map((item) => item.code))].sort(),
      [...assertion.codes].sort(),
      `${caseId} codes`,
    );
    assert.equal(actual.final_state.state, assertion.state, `${caseId} state`);
  }
});
