import assert from "node:assert/strict";
import { createPrivateKey, sign } from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import {
  evaluateCapnegVector,
  NEGOTIATION_HASH_DOMAIN,
  reduceCapnegV02,
  validateProjectionV2,
} from "../src/capneg_v02.js";
import { messageHashFromBody, objectHash } from "../src/hashing.js";
import { resolveProfileComposition } from "../src/profile_composition.js";

const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.resolve(here, "../../..");
const readJson = (relative) =>
  JSON.parse(fs.readFileSync(path.join(root, relative), "utf8"));
const clone = (value) => JSON.parse(JSON.stringify(value));

const vectors = readJson(
  "fixtures/extensions/capneg_v0_2/cross_language_vectors.json",
);
const negotiationOracle = readJson(vectors.negotiation_oracle_ref).cases;
const compositionOracle = readJson(vectors.composition_oracle_ref).cases;
const rules = readJson("registry/aicp_profile_composition_rules.json");
const reasonCodes = new Set(
  readJson("registry/capneg_reason_codes.json").map((entry) => entry.id),
);
const keyMap = readJson("fixtures/keys/GT_public_keys.json");
const privateKeys = readJson("fixtures/keys/TEST_private_keys.json");
const registeredExtensions = new Set(
  readJson("registry/extension_ids.json").map((entry) => entry.id),
);
const options = { rules, reasonCodes, keyMap, registeredExtensions };
const parties = ["agent:S", "agent:T"];
const baseProfile = { profile_id: "AICP-BASE", profile_version: "0.1" };
const authProfile = {
  profile_id: "AICP-AUTHENTICATED-BASE",
  profile_version: "0.1",
};

function sourceCase(vector) {
  const catalog = readJson(vector.source_catalog);
  const matches = catalog.cases.filter((entry) => entry.id === vector.case_id);
  assert.equal(matches.length, 1, vector.id);
  const expectation = negotiationOracle[vector.oracle_case_id];
  assert.ok(expectation, vector.id);
  return {
    ...matches[0],
    expected_error_observations: expectation.expected_error_observations,
    expected_final_state: expectation.expected_final_state,
  };
}

function privateKey(signer) {
  const raw = Buffer.from(privateKeys[signer].private_key_b64url, "base64url");
  return createPrivateKey({
    key: Buffer.concat([
      Buffer.from("302e020100300506032b657004220420", "hex"),
      raw,
    ]),
    format: "der",
    type: "pkcs8",
  });
}

function signature(messageHash, signer) {
  return {
    signer,
    kid: privateKeys[signer].kid,
    object_type: "message",
    object_hash: messageHash,
    sig_b64url: sign(
      null,
      Buffer.from(`AICP1\0SIG\0${messageHash}`, "utf8"),
      privateKey(signer),
    ).toString("base64url"),
  };
}

function body(message) {
  const result = clone(message);
  delete result.message_hash;
  delete result.signatures;
  return result;
}

function rehash(messages, signers = new Map()) {
  let previous = null;
  for (const message of messages) {
    const next = body(message);
    delete next.prev_msg_hash;
    if (previous !== null) next.prev_msg_hash = previous;
    const digest = messageHashFromBody(next);
    for (const key of Object.keys(message)) delete message[key];
    Object.assign(message, next, { message_hash: digest });
    const signer = signers.get(message.message_id);
    if (signer !== undefined) {
      message.signatures = [signature(digest, signer)];
    }
    previous = digest;
  }
}

function message(messages, messageType, sender, payload) {
  const index = messages.length + 1;
  return {
    session_id: messages[0]?.session_id ?? "direct-session",
    message_id: `m${index}`,
    timestamp: `2026-07-30T00:00:${String(index).padStart(2, "0")}Z`,
    sender,
    message_type: messageType,
    contract_id: messages[0]?.contract_id ?? "direct-contract",
    payload,
  };
}

function appendDecision(
  messages,
  proposal,
  sender,
  { accepted = true, signer = null, signers = new Map() } = {},
) {
  const result = proposal.payload.negotiation_result;
  const payload = {
    capneg_version: "0.2",
    negotiation_id: result.negotiation_id,
    proposal_revision: proposal.payload.proposal_revision,
    proposal_message_id: proposal.message_id,
    proposal_message_hash: proposal.message_hash,
    negotiation_result_hash: proposal.payload.negotiation_result_hash,
  };
  if (accepted) payload.accepted = true;
  else payload.reason_code = "PROFILE_SET_UNSUPPORTED";
  const decision = message(
    messages,
    accepted ? "CAPABILITIES_ACCEPT" : "CAPABILITIES_REJECT",
    sender,
    payload,
  );
  messages.push(decision);
  if (signer !== null) signers.set(decision.message_id, signer);
  rehash(messages, signers);
  return decision;
}

function directTranscript({
  authenticated = false,
  acceptSenders = [],
  signAcceptances = authenticated,
  participantRequiredCrypto = false,
} = {}) {
  const profile = authenticated ? authProfile : baseProfile;
  const selectedCrypto = authenticated ? ["aicp.crypto.ed25519.v1"] : [];
  const composition = {
    composition_version: "aicp.profile_composition.v1",
    profiles: [clone(profile)],
  };
  const messages = [];
  for (const party of parties) {
    const requiredCrypto =
      participantRequiredCrypto && party === parties[0]
        ? ["aicp.crypto.ed25519.v1"]
        : selectedCrypto;
    const supportedCrypto = [
      ...new Set([...selectedCrypto, ...requiredCrypto]),
    ].sort();
    messages.push(
      message(messages, "CAPABILITIES_DECLARE", party, {
        capneg_version: "0.2",
        capabilities_id: `direct-${party.at(-1)}`,
        party_id: party,
        supported_crypto_profiles: supportedCrypto,
        required_crypto_profiles: requiredCrypto,
        supported_privacy_modes: ["standard"],
        supported_aicp_profiles: [clone(profile)],
        required_aicp_profiles: [],
        supported_extensions: [],
        supported_policy_categories: [],
        bindings: ["BIND-HTTP-0.1"],
        limits: { max_message_bytes: 1024 },
      }),
    );
  }
  rehash(messages);
  const result = {
    negotiation_id: "direct-root",
    proposal_revision: 1,
    session_id: "direct-session",
    contract_id: "direct-contract",
    participants: parties,
    declaration_bindings: messages.map((entry) => ({
      party_id: entry.payload.party_id,
      capabilities_id: entry.payload.capabilities_id,
      declaration_message_id: entry.message_id,
      declaration_message_hash: entry.message_hash,
    })),
    selected: {
      crypto_profiles: selectedCrypto,
      privacy_mode: "standard",
      profile_composition: composition,
      profile_composition_hash: objectHash(
        "capneg.profile_composition",
        composition,
      ),
      required_extensions: [],
      required_policy_categories: [],
      binding: "BIND-HTTP-0.1",
      limits: { max_message_bytes: 1024 },
    },
  };
  const proposal = message(messages, "CAPABILITIES_PROPOSE", parties[0], {
    capneg_version: "0.2",
    proposal_revision: 1,
    negotiation_result: result,
    negotiation_result_hash: objectHash(NEGOTIATION_HASH_DOMAIN, result),
  });
  messages.push(proposal);
  rehash(messages);
  const signers = new Map();
  for (const sender of acceptSenders) {
    appendDecision(messages, proposal, sender, {
      signer: signAcceptances ? sender : null,
      signers,
    });
  }
  return { messages, proposal, signers };
}

function appendSuccessor(
  messages,
  negotiationId,
  supersedes,
  acceptSenders = [],
) {
  const result = clone(messages[2].payload.negotiation_result);
  result.negotiation_id = negotiationId;
  if (supersedes === null) delete result.supersedes_negotiation_id;
  else result.supersedes_negotiation_id = supersedes;
  const proposal = message(messages, "CAPABILITIES_PROPOSE", parties[1], {
    capneg_version: "0.2",
    proposal_revision: 1,
    negotiation_result: result,
    negotiation_result_hash: objectHash(NEGOTIATION_HASH_DOMAIN, result),
  });
  messages.push(proposal);
  rehash(messages);
  for (const sender of acceptSenders) {
    appendDecision(messages, proposal, sender);
  }
  return proposal;
}

function reduce(messages, extra = {}) {
  return reduceCapnegV02(messages, {
    rules,
    reasonCodes,
    keyMap,
    ...extra,
  });
}

test("composition resolver matches the reviewed composition oracle", () => {
  for (const vector of vectors.composition_vectors) {
    const reviewed = compositionOracle[vector.oracle_case_id];
    assert.ok(reviewed, vector.id);
    const actual = resolveProfileComposition(reviewed.input, rules);
    for (const [field, expected] of Object.entries(reviewed.expected)) {
      if (field === "errors") {
        assert.deepEqual(
          actual.errors.map((entry) => entry.code),
          expected.map((entry) => entry.code),
          `${vector.id}:${field}`,
        );
      } else {
        assert.deepEqual(actual[field], expected, `${vector.id}:${field}`);
      }
    }
  }
  const reviewed = compositionOracle["mediated-resumable"];
  const broken = resolveProfileComposition(reviewed.input, rules);
  broken.required_extensions = [];
  assert.notDeepEqual(
    broken.required_extensions,
    reviewed.expected.required_extensions,
  );
});

test("compact cross-language manifests resolve catalogs and oracle exactly", () => {
  for (const vector of vectors.negotiation_vectors) {
    const resolved = sourceCase(vector);
    assert.deepEqual(
      evaluateCapnegVector(resolved, options),
      {
        error_observations: resolved.expected_error_observations,
        final_state: resolved.expected_final_state,
      },
      vector.id,
    );
  }
});

test("manual decisions enforce context, sender, rejection, and latest declaration", () => {
  const direct = directTranscript({ acceptSenders: [parties[0]] });
  const wrongSession = clone(direct.messages);
  wrongSession.at(-1).session_id = "other-session";
  assert.deepEqual(reduce(wrongSession).errors, ["DECISION_SESSION_MISMATCH"]);

  const wrongContract = clone(direct.messages);
  wrongContract.at(-1).contract_id = "other-contract";
  assert.deepEqual(reduce(wrongContract).errors, ["DECISION_CONTRACT_MISMATCH"]);

  const authenticated = directTranscript({
    authenticated: true,
    acceptSenders: [parties[0]],
  });
  authenticated.messages.at(-1).signatures = [
    signature(authenticated.messages.at(-1).message_hash, parties[1]),
  ];
  assert.deepEqual(reduce(authenticated.messages).errors, [
    "AUTHENTICATED_ACCEPTANCE_SIGNATURE_REQUIRED",
  ]);

  const rejected = directTranscript();
  appendDecision(rejected.messages, rejected.proposal, parties[0], {
    accepted: false,
  });
  appendDecision(rejected.messages, rejected.proposal, parties[1]);
  assert.equal(reduce(rejected.messages).state, "REJECTED");
  assert.deepEqual(reduce(rejected.messages).errors, ["REVISION_REJECTED"]);

  const stale = directTranscript();
  const declaration = clone(stale.messages[0]);
  declaration.message_id = "m4";
  declaration.payload.capabilities_id = "direct-S-next";
  declaration.payload.supersedes_capabilities_id = "direct-S";
  stale.messages.push(declaration);
  rehash(stale.messages);
  appendDecision(stale.messages, stale.proposal, parties[0]);
  assert.deepEqual(reduce(stale.messages).errors, [
    "STALE_CAPABILITIES_DECLARATION",
  ]);
});

test("manual crypto, projection, contract, and accepted-root barriers are load-bearing", () => {
  const participantCrypto = directTranscript({
    participantRequiredCrypto: true,
  });
  assert.deepEqual(reduce(participantCrypto.messages).errors, [
    "PARTICIPANT_REQUIRED_CRYPTO_MISSING",
  ]);

  const partial = directTranscript({ acceptSenders: [parties[0]] });
  const projection = {
    projection_version: "aicp.session_state_projection.v2",
    session_id: "direct-session",
    contract_id: "direct-contract",
    as_of_message_hash: partial.messages.at(-1).message_hash,
    session_status: "OPEN",
    selected_aicp_profiles: [baseProfile],
    profile_composition_hash:
      partial.proposal.payload.negotiation_result.selected
        .profile_composition_hash,
    accepted_negotiation_result_hash:
      partial.proposal.payload.negotiation_result_hash,
    participant_refs: parties,
    active_extensions: [],
  };
  const projectionMessage = message(
    partial.messages,
    "STATE_SYNC_RESPONSE",
    parties[1],
    {
      request_id: "direct-projection",
      session_state: projection,
      session_state_hash: objectHash("session_state_projection", projection),
    },
  );
  partial.messages.push(projectionMessage);
  rehash(partial.messages);
  assert.deepEqual(
    validateProjectionV2(
      partial.messages.at(-1),
      partial.messages,
      partial.messages.length - 1,
      options,
    ),
    [
      "PROJECTION_ACCEPTANCE_NOT_ESTABLISHED",
      "PROJECTION_PROFILE_SET_MISMATCH",
      "PROJECTION_ACCEPTED_RESULT_HASH_MISMATCH",
    ],
  );

  const invalidContract = directTranscript({
    acceptSenders: parties,
  });
  invalidContract.messages.push(
    message(
      invalidContract.messages,
      "CONTRACT_PROPOSE",
      parties[0],
      { contract: { contract_id: "direct-contract" } },
    ),
  );
  rehash(invalidContract.messages);
  const evaluated = evaluateCapnegVector(
    {
      messages: invalidContract.messages,
      expected_final_state: { state: "IGNORED" },
    },
    options,
  );
  assert.ok(
    evaluated.error_observations.some(
      (entry) => entry.code === "CORE_CONTRACT_SCHEMA_INVALID",
    ),
  );

  const unlinked = directTranscript({ acceptSenders: parties });
  appendSuccessor(
    unlinked.messages,
    "direct-unlinked",
    null,
  );
  assert.deepEqual(reduce(unlinked.messages).errors, [
    "NEGOTIATION_SUPERSESSION_REQUIRED",
  ]);
});

test("manual successor decisions replay after exact supersession only", () => {
  const direct = directTranscript({ acceptSenders: parties });
  const successor = appendSuccessor(
    direct.messages,
    "direct-successor",
    "direct-root",
    parties,
  );
  appendDecision(direct.messages, successor, parties[1]);
  appendDecision(direct.messages, successor, parties[0]);
  const snapshot = reduce(direct.messages);
  assert.deepEqual(snapshot.errors, []);
  assert.deepEqual(snapshot.superseded_negotiations, ["direct-root"]);

  for (const [field, value, code] of [
    ["session_id", "other-session", "DECISION_SESSION_MISMATCH"],
    ["contract_id", "other-contract", "DECISION_CONTRACT_MISMATCH"],
  ]) {
    const mutated = clone(direct.messages.slice(0, -2));
    const replay = appendDecision(mutated, successor, parties[1]);
    replay[field] = value;
    assert.ok(reduce(mutated).errors.includes(code));
  }

  const changedHash = clone(direct.messages.slice(0, -2));
  const replay = appendDecision(changedHash, successor, parties[1]);
  replay.payload.negotiation_result_hash = `sha256:${"A".repeat(43)}`;
  assert.ok(
    reduce(changedHash).errors.includes("ACCEPTANCE_RESULT_HASH_MISMATCH"),
  );

  const invalidSignature = clone(direct.messages.slice(0, -2));
  const signedReplay = appendDecision(
    invalidSignature,
    successor,
    parties[1],
  );
  signedReplay.signatures = [
    {
      ...signature(signedReplay.message_hash, parties[1]),
      sig_b64url: "A".repeat(86),
    },
  ];
  assert.ok(
    reduce(invalidSignature).errors.includes("ACCEPTANCE_SIGNATURE_INVALID"),
  );

  const fork = directTranscript({ acceptSenders: parties });
  const successorA = appendSuccessor(
    fork.messages,
    "successor-a",
    "direct-root",
  );
  const successorB = appendSuccessor(
    fork.messages,
    "successor-b",
    "direct-root",
  );
  appendDecision(fork.messages, successorA, parties[0]);
  appendDecision(fork.messages, successorA, parties[1]);
  appendDecision(fork.messages, successorB, parties[0]);
  assert.equal(
    reduce(fork.messages).errors.at(-1),
    "NEGOTIATION_SUPERSESSION_INVALID",
  );
});

test("manual reducers are fail-closed when verification is unavailable", () => {
  const unsignedAuth = directTranscript({ authenticated: true });
  appendDecision(unsignedAuth.messages, unsignedAuth.proposal, parties[0]);
  let snapshot = reduce(unsignedAuth.messages, { cryptoAvailable: false });
  assert.equal(snapshot.state, "PROPOSED");
  assert.deepEqual(snapshot.errors, [
    "AUTHENTICATED_ACCEPTANCE_SIGNATURE_REQUIRED",
  ]);

  const signedAuth = directTranscript({
    authenticated: true,
    acceptSenders: [parties[0]],
  });
  snapshot = reduce(signedAuth.messages, { cryptoAvailable: false });
  assert.equal(snapshot.state, "PROPOSED");
  assert.deepEqual(snapshot.errors, ["CRYPTO_VERIFICATION_UNAVAILABLE"]);

  const unsignedBase = directTranscript({ acceptSenders: [parties[0]] });
  snapshot = reduce(unsignedBase.messages, { cryptoAvailable: false });
  assert.equal(snapshot.state, "PARTIALLY_ACCEPTED");
  assert.deepEqual(snapshot.errors, []);

  const signedBase = directTranscript({
    acceptSenders: [parties[0]],
    signAcceptances: true,
  });
  snapshot = reduce(signedBase.messages, { cryptoAvailable: false });
  assert.equal(snapshot.state, "PROPOSED");
  assert.deepEqual(snapshot.errors, ["CRYPTO_VERIFICATION_UNAVAILABLE"]);
});
