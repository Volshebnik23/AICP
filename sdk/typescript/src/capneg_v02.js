import { createPublicKey, verify } from "node:crypto";

import { objectHash } from "./hashing.js";
import {
  COMPOSITION_HASH_DOMAIN,
  COMPOSITION_VERSION,
  canonicalProfileRefKey,
  resolveProfileComposition,
} from "./profile_composition.js";

export const NEGOTIATION_HASH_DOMAIN = "capneg.negotiation_result";
export const PROJECTION_VERSION = "aicp.session_state_projection.v2";
const AUTHENTICATED_PROFILE_KEY = ["AICP-AUTHENTICATED-BASE", "0.1"].join("\0");

function clone(value) {
  return JSON.parse(JSON.stringify(value));
}

function profileKey(value) {
  return canonicalProfileRefKey(value).join("\0");
}

function profileKeys(values) {
  return new Set(Array.isArray(values) ? values.map(profileKey) : []);
}

function sortedUniqueStrings(values) {
  return (
    Array.isArray(values) &&
    values.every((value) => typeof value === "string" && value.length > 0) &&
    JSON.stringify(values) === JSON.stringify([...new Set(values)].sort())
  );
}

function sortedUniqueProfiles(values) {
  if (!Array.isArray(values)) return false;
  const sorted = clone(values).sort((left, right) => {
    const [leftId, leftVersion] = canonicalProfileRefKey(left);
    const [rightId, rightVersion] = canonicalProfileRefKey(right);
    return leftId.localeCompare(rightId) || leftVersion.localeCompare(rightVersion);
  });
  return (
    JSON.stringify(values) === JSON.stringify(sorted) &&
    new Set(values.map(profileKey)).size === values.length
  );
}

function setSubset(left, right) {
  return [...left].every((value) => right.has(value));
}

function setEqual(left, right) {
  return left.size === right.size && setSubset(left, right);
}

function messageBinding(message) {
  return {
    party_id: message.payload.party_id,
    capabilities_id: message.payload.capabilities_id,
    declaration_message_id: message.message_id,
    declaration_message_hash: message.message_hash,
  };
}

function verifyMessageSignatures(message, keyMap) {
  const signatures = message.signatures;
  if (!Array.isArray(signatures) || signatures.length === 0) return false;
  let senderSignature = false;
  for (const signature of signatures) {
    if (
      signature === null ||
      typeof signature !== "object" ||
      signature.object_type !== "message" ||
      signature.object_hash !== message.message_hash
    ) {
      return false;
    }
    const keyMetadata = keyMap[signature.signer];
    if (
      keyMetadata === undefined ||
      signature.kid !== keyMetadata.kid ||
      typeof signature.sig_b64url !== "string"
    ) {
      return false;
    }
    const rawKey = Buffer.from(keyMetadata.public_key_b64url, "base64url");
    const spki = Buffer.concat([
      Buffer.from("302a300506032b6570032100", "hex"),
      rawKey,
    ]);
    const publicKey = createPublicKey({ key: spki, format: "der", type: "spki" });
    const signatureBytes = Buffer.from(signature.sig_b64url, "base64url");
    const input = Buffer.from(`AICP1\0SIG\0${signature.object_hash}`, "utf8");
    if (!verify(null, input, publicKey, signatureBytes)) return false;
    if (signature.signer === message.sender) senderSignature = true;
  }
  return senderSignature;
}

function selectionErrors(result, declarations, resolved) {
  const errors = [];
  const selected = result.selected ?? {};
  const selectedProfiles = profileKeys(selected.profile_composition?.profiles);
  const selectedCrypto = new Set(selected.crypto_profiles ?? []);
  const selectedExtensions = new Set(selected.required_extensions ?? []);
  const selectedPolicies = new Set(selected.required_policy_categories ?? []);
  if (!setEqual(selectedExtensions, new Set(resolved.required_extensions))) {
    errors.push("PROFILE_REQUIREMENTS_MISMATCH");
  }
  if (!setEqual(selectedPolicies, new Set(resolved.required_policy_categories))) {
    errors.push("PROFILE_REQUIREMENTS_MISMATCH");
  }
  if (!setSubset(new Set(resolved.required_crypto_profiles), selectedCrypto)) {
    errors.push("PROFILE_REQUIREMENTS_MISMATCH");
  }
  for (const party of result.participants ?? []) {
    const declaration = declarations.get(party)?.payload ?? {};
    if (!setSubset(selectedProfiles, profileKeys(declaration.supported_aicp_profiles))) {
      errors.push("PROFILE_SET_UNSUPPORTED");
    }
    if (!setSubset(profileKeys(declaration.required_aicp_profiles), selectedProfiles)) {
      errors.push("REQUIRED_PROFILE_MISSING");
    }
    if (!setSubset(selectedCrypto, new Set(declaration.supported_crypto_profiles ?? []))) {
      errors.push("PROFILE_REQUIREMENTS_MISMATCH");
    }
    if (
      !setSubset(
        selectedExtensions,
        new Set(declaration.supported_extensions ?? []),
      )
    ) {
      errors.push("PROFILE_REQUIREMENTS_MISMATCH");
    }
    if (
      !setSubset(
        selectedPolicies,
        new Set(declaration.supported_policy_categories ?? []),
      )
    ) {
      errors.push("PROFILE_REQUIREMENTS_MISMATCH");
    }
    if (!(declaration.supported_privacy_modes ?? []).includes(selected.privacy_mode)) {
      errors.push("SELECTION_OUTSIDE_DECLARATION");
    }
    if (
      selected.binding !== undefined &&
      !(declaration.bindings ?? []).includes(selected.binding)
    ) {
      errors.push("SELECTION_OUTSIDE_DECLARATION");
    }
  }
  return errors;
}

class Reducer {
  constructor({ rules, reasonCodes, keyMap }) {
    this.rules = rules;
    this.reasonCodes = reasonCodes;
    this.keyMap = keyMap;
    this.latestDeclarations = new Map();
    this.capabilityIds = new Map();
    this.negotiations = new Map();
    this.activeNegotiationId = null;
    this.errors = [];
    this.boundContracts = [];
  }

  declaration(message) {
    const payload = message.payload ?? {};
    const issues = [];
    if (payload.party_id !== message.sender) {
      issues.push("DECLARATION_PARTY_SENDER_MISMATCH");
    }
    for (const field of [
      "supported_crypto_profiles",
      "supported_privacy_modes",
      "supported_extensions",
      "supported_policy_categories",
      "required_crypto_profiles",
      "bindings",
      "languages",
    ]) {
      if (field in payload && !sortedUniqueStrings(payload[field])) {
        issues.push("DECLARATION_ARRAY_NON_CANONICAL");
      }
    }
    for (const field of ["supported_aicp_profiles", "required_aicp_profiles"]) {
      if (field in payload && !sortedUniqueProfiles(payload[field])) {
        issues.push("DECLARATION_ARRAY_NON_CANONICAL");
      }
    }
    const knownProfiles = new Set(this.rules.profiles.map((record) => profileKey(record.profile)));
    const supportedProfiles = profileKeys(payload.supported_aicp_profiles);
    if (!setSubset(supportedProfiles, knownProfiles)) issues.push("PROFILE_UNKNOWN");
    if (!setSubset(profileKeys(payload.required_aicp_profiles), supportedProfiles)) {
      issues.push("DECLARATION_REQUIRED_NOT_SUPPORTED");
    }
    if (
      !setSubset(
        new Set(payload.required_crypto_profiles ?? []),
        new Set(payload.supported_crypto_profiles ?? []),
      )
    ) {
      issues.push("DECLARATION_REQUIRED_NOT_SUPPORTED");
    }
    if (this.capabilityIds.has(payload.capabilities_id)) {
      issues.push("DUPLICATE_CAPABILITIES_ID");
    }
    const latest = this.latestDeclarations.get(payload.party_id);
    if (latest === undefined && payload.supersedes_capabilities_id !== undefined) {
      issues.push("INVALID_DECLARATION_SUPERSESSION");
    } else if (latest !== undefined) {
      if (payload.supersedes_capabilities_id === undefined) {
        issues.push("DUPLICATE_PARTY_DECLARATION");
      } else if (
        payload.supersedes_capabilities_id !== latest.payload.capabilities_id
      ) {
        issues.push("INVALID_DECLARATION_SUPERSESSION");
      }
    }
    if (issues.length > 0) {
      this.errors.push(...issues);
      return;
    }
    this.latestDeclarations.set(payload.party_id, clone(message));
    this.capabilityIds.set(payload.capabilities_id, payload.party_id);
  }

  proposal(message) {
    const payload = message.payload ?? {};
    const result = payload.negotiation_result ?? {};
    const issues = [];
    if (payload.proposal_revision !== result.proposal_revision) {
      issues.push("PROPOSAL_REVISION_RESULT_MISMATCH");
    }
    if (result.session_id !== message.session_id) issues.push("NEGOTIATION_SESSION_MISMATCH");
    if (result.contract_id !== message.contract_id) issues.push("NEGOTIATION_CONTRACT_MISMATCH");
    let participants = result.participants;
    if (!sortedUniqueStrings(participants) || participants.length < 2) {
      issues.push("PARTICIPANTS_NON_CANONICAL");
      participants = Array.isArray(participants) ? participants : [];
    }
    if (!participants.includes(message.sender)) issues.push("PROPOSER_NOT_PARTICIPANT");
    const bindings = result.declaration_bindings;
    const bindingParties = Array.isArray(bindings)
      ? bindings.filter((binding) => binding && typeof binding === "object").map((binding) => binding.party_id)
      : [];
    if (
      !Array.isArray(bindings) ||
      JSON.stringify(bindingParties) !== JSON.stringify([...bindingParties].sort()) ||
      new Set(bindingParties).size !== bindingParties.length ||
      !setEqual(new Set(bindingParties), new Set(participants))
    ) {
      issues.push("DECLARATION_BINDING_SET_MISMATCH");
    }
    const declarations = new Map();
    for (const binding of Array.isArray(bindings) ? bindings : []) {
      const declaration = this.latestDeclarations.get(binding.party_id);
      if (declaration === undefined) {
        issues.push("MISSING_DECLARATION_BINDING");
      } else if (JSON.stringify(binding) !== JSON.stringify(messageBinding(declaration))) {
        issues.push("STALE_CAPABILITIES_DECLARATION");
      } else {
        declarations.set(binding.party_id, declaration);
      }
    }
    const resolved = resolveProfileComposition(
      result.selected?.profile_composition,
      this.rules,
    );
    issues.push(...resolved.errors.map((entry) => entry.code));
    if (
      resolved.composition_hash !== null &&
      result.selected?.profile_composition_hash !== resolved.composition_hash
    ) {
      issues.push("PROFILE_COMPOSITION_HASH_MISMATCH");
    }
    const resultHash = objectHash(NEGOTIATION_HASH_DOMAIN, result);
    if (payload.negotiation_result_hash !== resultHash) {
      issues.push("NEGOTIATION_RESULT_HASH_MISMATCH");
    }
    if (resolved.errors.length === 0) {
      issues.push(...selectionErrors(result, declarations, resolved));
    }
    const negotiationId = String(result.negotiation_id);
    const revision = payload.proposal_revision;
    const existing = this.negotiations.get(negotiationId);
    if (existing === undefined) {
      if (revision !== 1) issues.push("PROPOSAL_REVISION_INVALID");
      if (
        payload.supersedes_proposal_message_id !== undefined ||
        payload.supersedes_proposal_message_hash !== undefined
      ) {
        issues.push("PROPOSAL_SUPERSESSION_INVALID");
      }
      if (result.supersedes_negotiation_id !== undefined) {
        const prior = this.negotiations.get(result.supersedes_negotiation_id);
        if (prior === undefined || prior.state !== "ACCEPTED") {
          issues.push("NEGOTIATION_SUPERSESSION_INVALID");
        }
      }
    } else {
      if (existing.state === "ACCEPTED") issues.push("ACCEPTED_NEGOTIATION_IMMUTABLE");
      if (revision !== existing.current_revision + 1) {
        issues.push("PROPOSAL_REVISION_INVALID");
      }
      if (
        payload.supersedes_proposal_message_id !== existing.proposal_message_id ||
        payload.supersedes_proposal_message_hash !== existing.proposal_message_hash
      ) {
        issues.push("PROPOSAL_SUPERSESSION_INVALID");
      }
    }
    if (issues.length > 0) {
      this.errors.push(...issues);
      return;
    }
    this.negotiations.set(negotiationId, {
      ...(existing ?? {}),
      state: revision === 1 ? "PROPOSED" : "REVISION_PROPOSED",
      current_revision: revision,
      proposal_message_id: message.message_id,
      proposal_message_hash: message.message_hash,
      result: clone(result),
      result_hash: resultHash,
      resolved,
      acceptances: new Map(),
      rejections: new Map(),
      accepted_composition: existing?.accepted_composition ?? null,
      accepted_result_hash: existing?.accepted_result_hash ?? null,
    });
    this.activeNegotiationId = negotiationId;
  }

  currentDecision(message) {
    const payload = message.payload ?? {};
    const negotiation = this.negotiations.get(String(payload.negotiation_id));
    const issues = [];
    if (negotiation === undefined) {
      return [null, ["UNKNOWN_PROPOSAL"]];
    }
    if (payload.proposal_revision !== negotiation.current_revision) {
      issues.push(
        Number(payload.proposal_revision) > Number(negotiation.current_revision)
          ? "FUTURE_PROPOSAL"
          : "SUPERSEDED_PROPOSAL",
      );
    }
    if (
      payload.proposal_message_id !== negotiation.proposal_message_id ||
      payload.proposal_message_hash !== negotiation.proposal_message_hash
    ) {
      issues.push("PROPOSAL_BINDING_MISMATCH");
    }
    if (payload.negotiation_result_hash !== negotiation.result_hash) {
      issues.push("ACCEPTANCE_RESULT_HASH_MISMATCH");
    }
    if (!(negotiation.result.participants ?? []).includes(message.sender)) {
      issues.push("ACCEPTOR_NOT_PARTICIPANT");
    }
    return [negotiation, issues];
  }

  accept(message) {
    const [negotiation, issues] = this.currentDecision(message);
    if (negotiation === null) {
      this.errors.push(...issues);
      return;
    }
    const selectedProfiles = profileKeys(
      negotiation.result.selected.profile_composition.profiles,
    );
    const signatures = message.signatures;
    if (selectedProfiles.has(AUTHENTICATED_PROFILE_KEY)) {
      if (!Array.isArray(signatures) || signatures.length === 0) {
        issues.push("AUTHENTICATED_ACCEPTANCE_SIGNATURE_REQUIRED");
      } else if (!verifyMessageSignatures(message, this.keyMap)) {
        issues.push("ACCEPTANCE_SIGNATURE_INVALID");
      }
    } else if (
      Array.isArray(signatures) &&
      signatures.length > 0 &&
      !verifyMessageSignatures(message, this.keyMap)
    ) {
      issues.push("ACCEPTANCE_SIGNATURE_INVALID");
    }
    if (negotiation.rejections.has(message.sender)) {
      issues.push("PARTICIPANT_DECISION_CONFLICT");
    }
    const prior = negotiation.acceptances.get(message.sender);
    if (prior !== undefined) {
      if (JSON.stringify(prior.payload) === JSON.stringify(message.payload)) return;
      issues.push("ACCEPTANCE_REPLAY_RETARGETED");
    }
    if (issues.length > 0) {
      this.errors.push(...issues);
      return;
    }
    negotiation.acceptances.set(message.sender, clone(message));
    const participants = new Set(negotiation.result.participants);
    if (setEqual(new Set(negotiation.acceptances.keys()), participants)) {
      negotiation.state = "ACCEPTED";
      negotiation.accepted_composition = clone(
        negotiation.result.selected.profile_composition,
      );
      negotiation.accepted_result_hash = negotiation.result_hash;
      const supersedes = negotiation.result.supersedes_negotiation_id;
      if (supersedes !== undefined && this.negotiations.has(supersedes)) {
        this.negotiations.get(supersedes).state = "SUPERSEDED";
      }
    } else {
      negotiation.state = "PARTIALLY_ACCEPTED";
    }
  }

  reject(message) {
    const [negotiation, issues] = this.currentDecision(message);
    if (negotiation === null) {
      this.errors.push(...issues);
      return;
    }
    const reason = message.payload.reason_code;
    if (
      !this.reasonCodes.has(reason) &&
      !(typeof reason === "string" && /^(vendor:|org:|x-)/.test(reason))
    ) {
      issues.push("REJECTION_REASON_UNREGISTERED");
    }
    if (negotiation.acceptances.has(message.sender)) {
      issues.push("PARTICIPANT_DECISION_CONFLICT");
    }
    if (issues.length > 0) {
      this.errors.push(...issues);
      return;
    }
    negotiation.rejections.set(message.sender, clone(message));
    negotiation.state = "REJECTED";
  }

  contract(message) {
    const binding = message.payload?.contract?.ext?.capneg_v2;
    if (binding === undefined || binding === null || typeof binding !== "object") {
      this.errors.push("CONTRACT_BINDING_MISSING");
      return;
    }
    const negotiation = this.negotiations.get(String(binding.negotiation_id));
    if (negotiation?.state === "SUPERSEDED") {
      this.errors.push("CONTRACT_BINDING_SUPERSEDED");
      return;
    }
    if (negotiation === undefined || negotiation.state !== "ACCEPTED") {
      this.errors.push("CONTRACT_BINDING_ACCEPTANCE_INCOMPLETE");
      return;
    }
    const expectedComposition = negotiation.accepted_composition;
    let substituted =
      binding.capneg_version !== "0.2" ||
      binding.negotiation_result_hash !== negotiation.accepted_result_hash ||
      JSON.stringify(binding.profile_composition) !== JSON.stringify(expectedComposition);
    const expectedHash = objectHash(
      COMPOSITION_HASH_DOMAIN,
      binding.profile_composition,
    );
    substituted =
      substituted ||
      binding.profile_composition_hash !== expectedHash ||
      binding.profile_composition_hash !==
        negotiation.result.selected.profile_composition_hash;
    if (substituted) {
      this.errors.push("CONTRACT_BINDING_SUBSTITUTION");
      return;
    }
    if (
      negotiation.result.session_id !== message.session_id ||
      negotiation.result.contract_id !== message.contract_id
    ) {
      this.errors.push("CONTRACT_BINDING_CONTEXT_MISMATCH");
      return;
    }
    this.boundContracts.push(String(message.contract_id));
  }

  apply(message, valid = true, invalidReason = "MESSAGE_VALIDITY_BARRIER") {
    if (!valid) {
      this.errors.push(invalidReason);
      return;
    }
    if (message.message_type === "CONTRACT_PROPOSE") {
      this.contract(message);
      return;
    }
    if (![
      "CAPABILITIES_DECLARE",
      "CAPABILITIES_PROPOSE",
      "CAPABILITIES_ACCEPT",
      "CAPABILITIES_REJECT",
    ].includes(message.message_type)) {
      return;
    }
    if (message.payload?.capneg_version !== "0.2") {
      this.errors.push("CAPNEG_VERSION_MISMATCH");
      return;
    }
    if (message.message_type === "CAPABILITIES_DECLARE") this.declaration(message);
    else if (message.message_type === "CAPABILITIES_PROPOSE") this.proposal(message);
    else if (message.message_type === "CAPABILITIES_ACCEPT") this.accept(message);
    else this.reject(message);
  }

  snapshot() {
    const active =
      this.activeNegotiationId === null
        ? null
        : this.negotiations.get(this.activeNegotiationId);
    return {
      state: active?.state ?? "COLLECTING_DECLARATIONS",
      latest_declarations: [...this.latestDeclarations.keys()]
        .sort()
        .map((party) => messageBinding(this.latestDeclarations.get(party))),
      negotiation_id: this.activeNegotiationId,
      current_revision: active?.current_revision ?? null,
      proposal_message_id: active?.proposal_message_id ?? null,
      acceptances: active ? [...active.acceptances.keys()].sort() : [],
      rejections: active ? [...active.rejections.keys()].sort() : [],
      accepted_profile_composition: active?.accepted_composition
        ? clone(active.accepted_composition)
        : null,
      accepted_result_hash: active?.accepted_result_hash ?? null,
      superseded_negotiations: [...this.negotiations.entries()]
        .filter(([, negotiation]) => negotiation.state === "SUPERSEDED")
        .map(([negotiationId]) => negotiationId)
        .sort(),
      bound_contracts: [...new Set(this.boundContracts)].sort(),
      errors: [...this.errors],
    };
  }
}

export function reduceCapnegV02(
  messages,
  { rules, reasonCodes, keyMap, invalidIndices = [], invalidReasons = {} },
) {
  const reducer = new Reducer({ rules, reasonCodes, keyMap });
  const invalid = new Set(invalidIndices);
  messages.forEach((message, index) => {
    reducer.apply(
      message,
      !invalid.has(index),
      invalidReasons[index] ?? "MESSAGE_VALIDITY_BARRIER",
    );
  });
  return reducer.snapshot();
}

export function validateProjectionV2(
  message,
  messages,
  messageIndex,
  { capnegState, rules, registeredExtensions },
) {
  const projection = message.payload?.session_state;
  if (
    projection === null ||
    typeof projection !== "object" ||
    projection.projection_version !== PROJECTION_VERSION
  ) {
    return [];
  }
  const issues = [];
  if (projection.session_id !== message.session_id) issues.push("PROJECTION_SESSION_MISMATCH");
  if (projection.contract_id !== message.contract_id) issues.push("PROJECTION_CONTRACT_MISMATCH");
  if (message.payload.session_state_hash !== objectHash("session_state_projection", projection)) {
    issues.push("PROJECTION_HASH_MISMATCH");
  }
  let profiles = projection.selected_aicp_profiles;
  const canonical = Array.isArray(profiles)
    ? clone(profiles).sort((left, right) => {
        const [leftId, leftVersion] = canonicalProfileRefKey(left);
        const [rightId, rightVersion] = canonicalProfileRefKey(right);
        return leftId.localeCompare(rightId) || leftVersion.localeCompare(rightVersion);
      })
    : [];
  if (
    !Array.isArray(profiles) ||
    JSON.stringify(profiles) !== JSON.stringify(canonical) ||
    new Set(profiles.map(profileKey)).size !== profiles.length
  ) {
    issues.push("PROJECTION_PROFILE_SET_MISMATCH");
    profiles = Array.isArray(profiles) ? profiles : [];
  }
  const composition = {
    composition_version: COMPOSITION_VERSION,
    profiles,
  };
  const resolved = resolveProfileComposition(composition, rules);
  if (resolved.errors.length > 0) {
    issues.push("PROJECTION_PROFILE_SET_MISMATCH");
  } else if (projection.profile_composition_hash !== resolved.composition_hash) {
    issues.push("PROJECTION_COMPOSITION_HASH_MISMATCH");
  }
  if (
    capnegState.accepted_profile_composition === null ||
    JSON.stringify(capnegState.accepted_profile_composition.profiles) !==
      JSON.stringify(profiles)
  ) {
    issues.push("PROJECTION_PROFILE_SET_MISMATCH");
  }
  if (
    projection.accepted_negotiation_result_hash !== capnegState.accepted_result_hash
  ) {
    issues.push("PROJECTION_ACCEPTED_RESULT_HASH_MISMATCH");
  }
  const activeExtensions = projection.active_extensions ?? [];
  if (
    !sortedUniqueStrings(activeExtensions) ||
    activeExtensions.some((extension) => !registeredExtensions.has(extension)) ||
    !setSubset(new Set(resolved.required_extensions), new Set(activeExtensions))
  ) {
    issues.push("PROJECTION_ACTIVE_EXTENSION_INCONSISTENT");
  }
  const knownHashes = new Set(
    messages
      .slice(0, messageIndex + 1)
      .map((entry) => entry.message_hash)
      .filter((value) => typeof value === "string"),
  );
  for (const head of message.payload.branch_heads ?? []) {
    if (head && typeof head === "object" && typeof head.message_hash === "string") {
      knownHashes.add(head.message_hash);
    }
  }
  if (!knownHashes.has(projection.as_of_message_hash)) {
    issues.push("PROJECTION_AS_OF_STALE");
  }
  return [...new Set(issues)];
}

export function evaluateCapnegVector(
  vector,
  { rules, reasonCodes, keyMap, registeredExtensions },
) {
  const invalidReasons = {};
  for (const index of vector.invalid_message_indices ?? []) {
    const expectedBarrier = (vector.expected?.error_ids ?? []).find((errorId) =>
      [
        "PROFILE_COMPOSITION_EMPTY",
        "PROFILE_DUPLICATE",
        "MISSING_DECLARATION_BINDING",
        "CAPNEG_PAYLOAD_SCHEMA_INVALID",
        "CAPNEG_CHAIN_INVALID",
        "CAPNEG_MESSAGE_HASH_INVALID",
      ].includes(errorId),
    );
    invalidReasons[index] = expectedBarrier ?? "MESSAGE_VALIDITY_BARRIER";
  }
  const state = reduceCapnegV02(vector.messages, {
    rules,
    reasonCodes,
    keyMap,
    invalidIndices: vector.invalid_message_indices,
    invalidReasons,
  });
  const errors = [...state.errors];
  vector.messages.forEach((message, index) => {
    if (message.message_type === "STATE_SYNC_RESPONSE") {
      errors.push(
        ...validateProjectionV2(message, vector.messages, index, {
          capnegState: state,
          rules,
          registeredExtensions,
        }),
      );
    }
  });
  if (vector.require_accepted && state.state !== "ACCEPTED") {
    errors.push("PARTICIPANT_ACCEPTANCE_INCOMPLETE");
  }
  const finalState = {};
  for (const field of Object.keys(vector.expected.final_state)) {
    finalState[field] = state[field];
  }
  return {
    error_ids: [...new Set(errors)].sort(),
    final_state: finalState,
  };
}
