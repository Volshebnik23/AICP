import { objectHash } from "./hashing.js";
import { canonicalizeJson } from "./jcs.js";

export const CONTRACT_SCHEMA = "CT2-CONTRACT-SCHEMA-01";
export const CONTRACT_ID = "CT2-CONTRACT-ID-01";
export const CONTRACT_HASH = "CT2-CONTRACT-HASH-01";
export const CONTRACT_REF = "CT2-CONTRACT-REF-01";
export const PROPOSAL_BINDING = "CT2-PROPOSAL-BINDING-01";
export const ACCEPT_BINDING = "CT2-ACCEPT-BINDING-01";
export const ACTIVE_HEAD = "CT2-ACTIVE-HEAD-01";
export const CONTEXT_BINDING = "CT2-CONTEXT-BINDING-01";
export const CONFLICT_BINDING = "CT2-CONFLICT-BINDING-01";
export const AGREEMENT_STATE = "CT2-AGREEMENT-STATE-01";

const HASH_RE = /^sha256:[A-Za-z0-9_-]{43}$/;
const clone = (value) => value === undefined ? undefined : JSON.parse(JSON.stringify(value));
const equal = (left, right) => {
  if (left === undefined || right === undefined) return left === right;
  return canonicalizeJson(left) === canonicalizeJson(right);
};

export function computeContractHash(contract) {
  return objectHash("contract", contract);
}

function versionHashErrors(value, label) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    return [`${label} must be an object`];
  }
  if (!equal(Object.keys(value).sort(), ["contract_hash", "version"])) {
    return [`${label} must contain only version and contract_hash`];
  }
  const errors = [];
  if (typeof value.version !== "string" || value.version.length === 0) {
    errors.push(`${label}.version must be a non-empty opaque identifier`);
  }
  if (typeof value.contract_hash !== "string" || !HASH_RE.test(value.contract_hash)) {
    errors.push(`${label}.contract_hash must use AICP sha256 syntax`);
  }
  return errors;
}

export function validateContractReference(reference) {
  if (reference === null || typeof reference !== "object" || Array.isArray(reference)) {
    return ["contract_ref must be an object"];
  }
  if (!Object.hasOwn(reference, "branch_id") || !Object.hasOwn(reference, "head")) {
    return ["contract_ref requires branch_id and head"];
  }
  if (Object.keys(reference).some((key) => !["branch_id", "base", "head"].includes(key))) {
    return ["contract_ref contains unsupported properties"];
  }
  const errors = [];
  if (typeof reference.branch_id !== "string" || reference.branch_id.length === 0) {
    errors.push("contract_ref.branch_id must be a non-empty string");
  }
  errors.push(...versionHashErrors(reference.head, "contract_ref.head"));
  if (Object.hasOwn(reference, "base")) {
    errors.push(...versionHashErrors(reference.base, "contract_ref.base"));
    if (errors.length === 0 && equal(reference.base, reference.head)) {
      errors.push("contract_ref transition base and head must differ");
    }
  }
  return errors;
}

export function currentHeadReference(reference) {
  return { branch_id: reference.branch_id, head: clone(reference.head) };
}

export function buildProposalBinding(contract, { branchId = "main", base = null } = {}) {
  const contractHash = computeContractHash(contract);
  const contractRef = {
    branch_id: branchId,
    head: {
      version: contract.contract_version,
      contract_hash: contractHash,
    },
  };
  if (base !== null) {
    if (equal(Object.keys(base).sort(), ["branch_id", "head"])) {
      if (base.branch_id !== branchId) {
        throw new Error("proposal branch_id must match the active branch");
      }
      contractRef.base = clone(base.head);
    } else {
      contractRef.base = clone(base);
    }
  }
  const errors = validateContractReference(contractRef);
  if (errors.length) throw new Error(errors.join("; "));
  return { contract_hash: contractHash, contract_ref: contractRef };
}

export function buildAcceptanceBinding(proposal, { accepted, replay = false }) {
  if (proposal.message_type !== "CONTRACT_PROPOSE") {
    throw new Error("acceptance binding requires a CONTRACT_PROPOSE message");
  }
  const result = {
    accepted,
    proposal_message_id: proposal.message_id,
    proposal_message_hash: proposal.message_hash,
    contract_hash: proposal.payload.contract_hash,
  };
  if (replay) result.replay = true;
  return result;
}

export function proposalCandidate(proposal) {
  return {
    proposal_message_id: proposal.message_id,
    proposal_message_hash: proposal.message_hash,
    contract_hash: proposal.payload.contract_hash,
    contract_ref: clone(proposal.contract_ref),
  };
}

export function chooseResolution(candidate) {
  return {
    type: "CHOOSE",
    selected_proposal_message_id: candidate.proposal_message_id,
    selected_proposal_message_hash: candidate.proposal_message_hash,
    selected_contract_hash: candidate.contract_hash,
    selected_contract_ref: clone(candidate.contract_ref),
  };
}

function tupleKey(accepted, proposal, reference) {
  return canonicalizeJson({
    accepted,
    proposal_message_id: proposal.message_id,
    proposal_message_hash: proposal.message_hash,
    contract_hash: proposal.contract_hash,
    contract_ref: reference,
  });
}

class Machine {
  constructor(messages, invalidIndices = []) {
    this.messages = messages;
    this.invalidIndices = new Set(invalidIndices);
    this.identityInitialized = false;
    this.state = {
      state: "NO_ACTIVE_CONTRACT",
      session_id: null,
      contract_id: null,
      active_head: null,
      proposals: new Map(),
      proposals_by_hash: new Map(),
      acceptance_tuples: new Set(),
      rejected_tuples: new Set(),
      selected_conflict_result: null,
      issues: [],
    };
    this.messageIndex = new Map();
    this.messageTypes = new Map();
    messages.forEach((message, index) => {
      if (typeof message.message_id === "string") {
        this.messageIndex.set(message.message_id, index);
        this.messageTypes.set(message.message_id, message.message_type);
      }
    });
  }

  issue(code, message, index) {
    if (!this.state.issues.some((item) => item.code === code && item.message === message && item.index === index)) {
      this.state.issues.push({ code, message, index });
    }
  }

  identity(message, index) {
    if (!this.identityInitialized) {
      this.state.session_id = typeof message.session_id === "string" ? message.session_id : null;
      this.state.contract_id = typeof message.contract_id === "string" ? message.contract_id : null;
      this.identityInitialized = true;
      return true;
    }
    let valid = true;
    if (message.session_id !== this.state.session_id) {
      this.issue(AGREEMENT_STATE, "session_id changed within Core v0.2 transcript", index);
      valid = false;
    }
    if (message.contract_id !== this.state.contract_id) {
      this.issue(CONTRACT_ID, "contract_id changed within Core v0.2 transcript", index);
      valid = false;
    }
    return valid;
  }

  validReference(reference, index, code = CONTRACT_REF) {
    const errors = validateContractReference(reference);
    if (errors.length) {
      this.issue(code, errors.join("; "), index);
      return false;
    }
    return true;
  }

  proposal(message, index) {
    const before = this.state.issues.length;
    const payload = message.payload;
    if (payload === null || typeof payload !== "object" || Array.isArray(payload)) {
      this.issue(CONTRACT_SCHEMA, "proposal payload must be an object", index);
      return;
    }
    const contract = payload.contract;
    if (contract === null || typeof contract !== "object" || Array.isArray(contract)) {
      this.issue(CONTRACT_SCHEMA, "payload.contract must be an object", index);
      return;
    }
    if (contract.contract_id !== message.contract_id) {
      this.issue(CONTRACT_ID, "envelope contract_id must equal contract.contract_id", index);
    }
    let computed;
    try {
      computed = computeContractHash(contract);
    } catch (error) {
      this.issue(CONTRACT_HASH, `contract hash recomputation failed: ${error}`, index);
      return;
    }
    if (payload.contract_hash !== computed) {
      this.issue(CONTRACT_HASH, `contract_hash mismatch (expected ${computed}, got ${payload.contract_hash})`, index);
    }
    if (!this.validReference(message.contract_ref, index)) return;
    if (message.contract_ref.head.version !== contract.contract_version) {
      this.issue(PROPOSAL_BINDING, "proposal head version must equal contract.contract_version", index);
    }
    if (message.contract_ref.head.contract_hash !== payload.contract_hash) {
      this.issue(PROPOSAL_BINDING, "proposal head hash must equal payload.contract_hash", index);
    }
    const active = this.state.active_head;
    if (active === null) {
      if (Object.hasOwn(message.contract_ref, "base")) {
        this.issue(PROPOSAL_BINDING, "initial proposal must omit contract_ref.base", index);
      }
    } else if (
      message.contract_ref.branch_id !== active.branch_id
      || !equal(message.contract_ref.base, active.head)
    ) {
      this.issue(PROPOSAL_BINDING, "revision proposal base must equal the exact active head", index);
    }
    if (this.state.issues.length !== before) return;
    const record = {
      message_id: message.message_id,
      message_hash: message.message_hash,
      contract_id: message.contract_id,
      contract: clone(contract),
      contract_hash: payload.contract_hash,
      contract_ref: clone(message.contract_ref),
      index,
    };
    this.state.proposals.set(record.message_id, record);
    this.state.proposals_by_hash.set(record.message_hash, record);
    const sameBase = [...this.state.proposals.values()].filter(
      (item) => item.contract_ref.branch_id === record.contract_ref.branch_id
        && equal(item.contract_ref.base, record.contract_ref.base)
        && item.index <= index,
    );
    this.state.state = sameBase.length > 1 ? "COMPETING_CANDIDATES" : "CANDIDATE_PROPOSED";
  }

  proposalForAcceptance(proposalId, index) {
    const proposal = this.state.proposals.get(proposalId);
    if (proposal) return proposal;
    const position = this.messageIndex.get(proposalId);
    if (position !== undefined && position > index) {
      this.issue(ACCEPT_BINDING, "acceptance references a future proposal", index);
    } else if (position !== undefined && this.messageTypes.get(proposalId) !== "CONTRACT_PROPOSE") {
      this.issue(ACCEPT_BINDING, "acceptance target is not a proposal", index);
    } else {
      this.issue(ACCEPT_BINDING, "acceptance references an unknown proposal", index);
    }
    return null;
  }

  acceptance(message, index) {
    const payload = message.payload;
    if (payload === null || typeof payload !== "object" || Array.isArray(payload)) {
      this.issue(ACCEPT_BINDING, "acceptance payload must be an object", index);
      return;
    }
    if (!this.validReference(message.contract_ref, index, ACCEPT_BINDING)) return;
    const proposal = this.proposalForAcceptance(payload.proposal_message_id, index);
    if (!proposal) return;
    const mismatches = [];
    if (payload.proposal_message_hash !== proposal.message_hash) mismatches.push("proposal_message_hash");
    if (payload.contract_hash !== proposal.contract_hash) mismatches.push("contract_hash");
    if (!equal(message.contract_ref, proposal.contract_ref)) mismatches.push("contract_ref");
    if (message.contract_id !== proposal.contract_id) mismatches.push("contract_id");
    if (mismatches.length) {
      this.issue(ACCEPT_BINDING, `acceptance does not match proposal fields: ${mismatches.join(", ")}`, index);
      return;
    }
    const key = tupleKey(payload.accepted, proposal, proposal.contract_ref);
    if (payload.replay === true) {
      if (!this.state.acceptance_tuples.has(key) && !this.state.rejected_tuples.has(key)) {
        this.issue(ACCEPT_BINDING, "replay must repeat one exact prior acceptance tuple", index);
      }
      return;
    }
    if (payload.accepted === true) {
      const active = this.state.active_head;
      const base = proposal.contract_ref.base;
      if (active === null) {
        if (base !== undefined) {
          this.issue(ACCEPT_BINDING, "initial accepted proposal must omit base", index);
          return;
        }
      } else if (
        proposal.contract_ref.branch_id !== active.branch_id
        || !equal(base, active.head)
      ) {
        this.issue(ACCEPT_BINDING, "stale proposal base does not equal the current active head", index);
        return;
      }
      this.state.active_head = currentHeadReference(proposal.contract_ref);
      this.state.acceptance_tuples.add(key);
      this.state.state = "ACTIVE_HEAD";
    } else if (payload.accepted === false) {
      this.state.rejected_tuples.add(key);
      this.state.state = this.state.active_head === null ? "NO_ACTIVE_CONTRACT" : "ACTIVE_HEAD";
    } else {
      this.issue(ACCEPT_BINDING, "accepted must be boolean", index);
    }
  }

  requireCurrent(message, index, code, purpose) {
    if (!this.validReference(message.contract_ref, index, code)) return false;
    if (this.state.active_head === null) {
      this.issue(code, `${purpose} requires an active contract head`, index);
      return false;
    }
    if (!equal(message.contract_ref, this.state.active_head)) {
      this.issue(code, `${purpose} must bind the exact active head`, index);
      return false;
    }
    return true;
  }

  context(message, index) {
    if (message.payload === null || typeof message.payload !== "object" || message.payload.contract_effect !== "none") {
      this.issue(CONTEXT_BINDING, "CONTEXT_AMEND contract_effect must equal 'none'", index);
    }
    this.requireCurrent(message, index, CONTEXT_BINDING, "CONTEXT_AMEND");
  }

  action(message, index) {
    this.requireCurrent(message, index, ACTIVE_HEAD, "ATTEST_ACTION");
  }

  proposalForCandidate(candidate, index) {
    const proposalId = candidate.proposal_message_id;
    const proposal = this.state.proposals.get(proposalId);
    if (proposal) return proposal;
    const position = this.messageIndex.get(proposalId);
    let reason = "unknown";
    if (position !== undefined && position > index) reason = "future";
    else if (position !== undefined && this.messageTypes.get(proposalId) !== "CONTRACT_PROPOSE") reason = "non-proposal";
    this.issue(CONFLICT_BINDING, `conflict candidate references a ${reason} proposal`, index);
    return null;
  }

  conflict(message, index) {
    const before = this.state.issues.length;
    if (this.state.active_head === null) {
      this.issue(CONFLICT_BINDING, "conflict resolution requires an active contract head", index);
      return;
    }
    const payload = message.payload;
    if (
      payload === null || typeof payload !== "object"
      || !Array.isArray(payload.candidates)
      || payload.resolution === null || typeof payload.resolution !== "object"
    ) {
      this.issue(CONFLICT_BINDING, "conflict candidates and resolution must be structured", index);
      return;
    }
    const resolved = new Map();
    const candidateIds = new Set();
    for (const candidate of payload.candidates) {
      if (candidate === null || typeof candidate !== "object" || Array.isArray(candidate)) {
        this.issue(CONFLICT_BINDING, "candidate must be an object", index);
        continue;
      }
      const proposalId = candidate.proposal_message_id;
      if (candidateIds.has(proposalId)) {
        this.issue(CONFLICT_BINDING, "duplicate conflict candidate", index);
        continue;
      }
      candidateIds.add(proposalId);
      const proposal = this.proposalForCandidate(candidate, index);
      if (!proposal) continue;
      const expected = {
        proposal_message_id: proposal.message_id,
        proposal_message_hash: proposal.message_hash,
        contract_hash: proposal.contract_hash,
        contract_ref: proposal.contract_ref,
      };
      if (!equal(candidate, expected)) {
        this.issue(CONFLICT_BINDING, `candidate ${proposalId} does not exactly match its proposal`, index);
        continue;
      }
      if (proposal.contract_id !== this.state.contract_id) {
        this.issue(CONFLICT_BINDING, "cross-contract conflict candidate is forbidden", index);
        continue;
      }
      if (
        proposal.contract_ref.branch_id !== this.state.active_head.branch_id
        || !equal(proposal.contract_ref.base, this.state.active_head.head)
      ) {
        this.issue(CONFLICT_BINDING, "all conflict candidates must derive from the exact active base", index);
        continue;
      }
      resolved.set(String(proposalId), proposal);
    }
    const resolution = payload.resolution;
    if (resolution.type !== "CHOOSE") {
      this.issue(CONFLICT_BINDING, "only CHOOSE resolution is supported", index);
      return;
    }
    const selected = resolved.get(String(resolution.selected_proposal_message_id));
    if (!selected) {
      this.issue(CONFLICT_BINDING, "selected proposal is not an exact declared candidate", index);
      return;
    }
    const candidate = {
      proposal_message_id: selected.message_id,
      proposal_message_hash: selected.message_hash,
      contract_hash: selected.contract_hash,
      contract_ref: selected.contract_ref,
    };
    const expectedResolution = chooseResolution(candidate);
    if (!equal(resolution, expectedResolution)) {
      this.issue(CONFLICT_BINDING, "selected result fields do not exactly match the candidate", index);
      return;
    }
    if (!equal(message.contract_ref, selected.contract_ref)) {
      this.issue(CONFLICT_BINDING, "resolution envelope must equal the selected contract reference", index);
      return;
    }
    if (this.state.issues.length !== before) return;
    this.state.active_head = currentHeadReference(selected.contract_ref);
    this.state.selected_conflict_result = clone(expectedResolution);
    this.state.state = "CONFLICT_RESOLVED";
  }

  error(message, index) {
    if (message.contract_ref === undefined) return;
    if (!this.validReference(message.contract_ref, index)) return;
    const known = [...this.state.proposals.values()].some((proposal) => equal(proposal.contract_ref, message.contract_ref));
    if (!equal(message.contract_ref, this.state.active_head) && !known) {
      this.issue(ACTIVE_HEAD, "ERROR contract_ref must bind the current or an explicitly known head", index);
    }
  }

  process() {
    const handlers = {
      CONTRACT_PROPOSE: (message, index) => this.proposal(message, index),
      CONTRACT_ACCEPT: (message, index) => this.acceptance(message, index),
      CONTEXT_AMEND: (message, index) => this.context(message, index),
      ATTEST_ACTION: (message, index) => this.action(message, index),
      RESOLVE_CONFLICT: (message, index) => this.conflict(message, index),
      ERROR: (message, index) => this.error(message, index),
    };
    this.messages.forEach((message, index) => {
      if (this.invalidIndices.has(index) && !this.identityInitialized) return;
      const identityValid = this.identity(message, index);
      if (!identityValid || this.invalidIndices.has(index)) return;
      handlers[message.message_type]?.(message, index);
    });
    return this.state;
  }
}

/**
 * @param {Array<Record<string, unknown>>} messages
 * @param {{invalidIndices?: Iterable<number>}} [options]
 */
export function reduceTranscript(messages, { invalidIndices = [] } = {}) {
  return new Machine(messages, invalidIndices).process();
}

export function semanticIssueIds(messages, options = {}) {
  return [...new Set(reduceTranscript(messages, options).issues.map((issue) => issue.code))].sort();
}
