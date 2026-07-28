import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { canonicalizeJson } from "../src/jcs.js";
import {
  computeContractHash,
  reduceTranscript,
  semanticIssueIds,
  validateContractReference,
} from "../src/contract_agreement.js";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "../../..");
const vectors = JSON.parse(
  fs.readFileSync(
    path.join(
      root,
      "fixtures/core_v0_2/exact_contract_agreement/cross_language_vectors.json",
    ),
    "utf8",
  ),
);

function loadJsonl(relative) {
  return fs
    .readFileSync(path.join(root, relative), "utf8")
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line) => JSON.parse(line));
}

test("Core v0.2 contract canonicalization, hash, and reference match shared vectors", () => {
  assert.equal(canonicalizeJson(vectors.contract), vectors.canonical_json);
  assert.equal(computeContractHash(vectors.contract), vectors.contract_hash);
  assert.deepEqual(validateContractReference(vectors.contract_ref), []);
});

test("Core v0.2 positive agreement transitions match Python vectors", () => {
  for (const vector of vectors.positive) {
    const state = reduceTranscript(loadJsonl(vector.path), {
      invalidIndices: vector.invalid_message_indices,
    });
    assert.deepEqual(state.issues, [], vector.path);
    assert.equal(state.state, vector.expected_state, vector.path);
    assert.deepEqual(state.active_head, vector.expected_active_head, vector.path);
    assert.deepEqual([...state.proposals.keys()].sort(), vector.expected_proposal_ids, vector.path);
    assert.deepEqual(
      state.selected_conflict_result,
      vector.expected_selected_conflict_result,
      vector.path,
    );
    assert.equal(state.acceptance_tuples.size, vector.expected_accepted_tuple_count, vector.path);
    assert.equal(state.rejected_tuples.size, vector.expected_rejected_tuple_count, vector.path);
  }
});

test("Core v0.2 negative classifications match Python vectors", () => {
  for (const vector of vectors.negative) {
    const messages = loadJsonl(vector.path);
    const options = { invalidIndices: vector.invalid_message_indices };
    assert.deepEqual(
      semanticIssueIds(messages, options),
      vector.expected_semantic_issue_ids,
      vector.path,
    );
    const state = reduceTranscript(messages, options);
    assert.equal(state.state, vector.expected_state, vector.path);
    assert.deepEqual(state.active_head, vector.expected_active_head, vector.path);
    assert.deepEqual([...state.proposals.keys()].sort(), vector.expected_proposal_ids, vector.path);
    assert.deepEqual(
      state.selected_conflict_result,
      vector.expected_selected_conflict_result,
      vector.path,
    );
    assert.equal(state.acceptance_tuples.size, vector.expected_accepted_tuple_count, vector.path);
    assert.equal(state.rejected_tuples.size, vector.expected_rejected_tuple_count, vector.path);
  }
});
