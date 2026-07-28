# AICP Core v0.2 — Exact Contract Agreement (Normative, Experimental)

## 1. Status and scope

Core v0.2 is an experimental, post-UAT protocol target. It is selected explicitly through
`AICP-BASE@0.2`; it does not reinterpret Core v0.1 or the frozen `AICP-BASE@0.1` target.
The normative machine-readable artifacts are:

- `schemas/core/aicp-core-message-v0.2.schema.json`;
- `schemas/core/aicp-core-payloads-v0.2.schema.json`;
- `schemas/core/aicp-core-contract-v0.2.schema.json`;
- `conformance/core/CT_CORE_0.2.json`.

Core v0.2 reuses the registered message type IDs `CONTRACT_PROPOSE`, `CONTRACT_ACCEPT`,
`CONTEXT_AMEND`, `ATTEST_ACTION`, `RESOLVE_CONFLICT`, and `ERROR`. Their v0.2 meaning is
selected only by the explicit Core/profile version.

## 2. Hash and version model

A contract hash MUST be:

```text
object_hash("contract", contract_object)
```

It uses the existing AICP object-hash domain, canonicalization, SHA-256 algorithm, and
`sha256:` base64url syntax. `contract_id` and `contract_version` are inside the hashed
object. The contract object MUST NOT contain its own hash.

`contract_version` is a non-empty opaque identifier. Implementations MUST NOT infer numeric,
semantic-version, lexical, or chronological ordering from it. State transitions are proven
by exact base/head references.

## 3. Contract object

A Core v0.2 contract MUST contain:

```json
{
  "contract_id": "contract-123",
  "contract_version": "v2",
  "goal": "Exact shared objective",
  "roles": ["proposer", "acceptor"]
}
```

`contract_id`, `contract_version`, and `goal` MUST be non-empty strings. `roles` MUST be a
non-empty, unique array of non-empty strings. `policies`, `extensions`, and `ext` remain
available as defined by the versioned contract schema. Unknown top-level fields and an
embedded `contract_hash` are forbidden.

## 4. Exact contract reference

Transition references have this shape:

```json
{
  "branch_id": "main",
  "base": {
    "version": "v1",
    "contract_hash": "sha256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
  },
  "head": {
    "version": "v2",
    "contract_hash": "sha256:BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
  }
}
```

`branch_id` and `head` are required. Each version/hash pair requires a non-empty opaque
`version` and a valid AICP SHA-256 hash. `base` is optional. Unknown properties are
forbidden. A transition MUST NOT have identical `base` and `head`.

A current-head binding omits `base`:

```json
{
  "branch_id": "main",
  "head": {
    "version": "v2",
    "contract_hash": "sha256:BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
  }
}
```

An initial proposal omits `base`. A revision proposal includes the exact active head as
`base`. A conflict resolution includes the common active base and selected resulting head.

## 5. Transcript invariants

One Core v0.2 transcript MUST retain one `session_id` and one `contract_id`. Message IDs
MUST be unique. Every non-first message MUST contain the exact previous `message_hash`.
Every `message_hash` MUST be recomputable with the existing message object-hash domain.

Message-chain integrity proves transcript ordering and bytes; it does not prove that peers
accepted the same contract. Exact agreement is created only by a valid positive acceptance
or a valid conflict resolution.

## 6. `CONTRACT_PROPOSE`

The payload MUST contain:

```json
{
  "contract": {
    "contract_id": "contract-123",
    "contract_version": "v2",
    "goal": "Exact shared objective",
    "roles": ["proposer", "acceptor"]
  },
  "contract_hash": "sha256:BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
}
```

The contract MUST validate against the v0.2 contract schema. `contract_hash` MUST equal
`object_hash("contract", contract)`. Envelope `contract_id` MUST equal
`contract.contract_id`. Reference head version/hash MUST equal
`contract.contract_version`/`contract_hash`.

With no active head, `base` MUST be absent. With an active head, `base` MUST equal that
exact head. Proposal head MUST differ from base. A proposal is only a candidate and MUST
NOT activate agreement. Multiple valid candidates from the same active base are allowed.

## 7. `CONTRACT_ACCEPT`

The payload MUST contain:

```json
{
  "accepted": true,
  "proposal_message_id": "proposal-42",
  "proposal_message_hash": "sha256:CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC",
  "contract_hash": "sha256:BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
}
```

`replay` MAY be present. The referenced message MUST be a prior valid proposal. Its ID,
message hash, contract hash, and complete envelope `contract_ref` MUST match exactly.
Unknown, future, cross-contract, substituted, and stale proposal references MUST fail.

For `accepted=true`, the proposal base MUST equal the active head, or both MUST be absent
for initial agreement. The proposal head then becomes active. For `accepted=false`, active
state is unchanged. A replay MUST repeat an exact previously observed tuple and MUST NOT
retarget another proposal, hash, reference, or accepted value.

Agreement binding is independent of optional signatures. Base 0.2 proves exact artifact
agreement, not sender authentication.

## 8. `CONTEXT_AMEND`

The payload MUST contain:

```json
{
  "amendment": {},
  "contract_effect": "none"
}
```

`none` is the only standardized `contract_effect` in Core v0.2. The envelope MUST use the
exact current-head binding with no `base`. The message does not change active contract
state and cannot introduce a contract version/hash. Contract revisions require a new
proposal followed by exact acceptance or conflict resolution. Core v0.2 defines no JSON
Patch or deterministic merge dialect.

## 9. `ATTEST_ACTION`

The existing result/consent attestation alternatives remain available. An action MUST
occur after agreement and MUST use the exact current-head binding with no `base`. A stale,
unknown, or substituted head MUST fail.

## 10. `RESOLVE_CONFLICT`

Only exact `CHOOSE` is standardized. Each candidate MUST contain:

```json
{
  "proposal_message_id": "proposal-a",
  "proposal_message_hash": "sha256:CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC",
  "contract_hash": "sha256:BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
  "contract_ref": {
    "branch_id": "main",
    "base": {
      "version": "v1",
      "contract_hash": "sha256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    },
    "head": {
      "version": "v2",
      "contract_hash": "sha256:BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
    }
  }
}
```

The resolution MUST contain:

```json
{
  "type": "CHOOSE",
  "selected_proposal_message_id": "proposal-a",
  "selected_proposal_message_hash": "sha256:CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC",
  "selected_contract_hash": "sha256:BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
  "selected_contract_ref": {
    "branch_id": "main",
    "base": {
      "version": "v1",
      "contract_hash": "sha256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
    },
    "head": {
      "version": "v2",
      "contract_hash": "sha256:BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"
    }
  }
}
```

Every candidate MUST identify a distinct prior valid proposal and exactly reproduce its
message hash, contract hash, and reference. Candidates MUST belong to the transcript
contract and derive from the same exact active base. The selected proposal MUST be declared,
all selected fields MUST match it, and the resolution envelope reference MUST equal the
selected reference. The selected head becomes active.

Duplicate, unknown, future, stale, cross-contract, or substituted candidates MUST fail.
Contract merge, JSON Patch, and deterministic patch semantics are deferred.

## 11. `ERROR`

`ERROR` does not change contract state. Before agreement it MAY omit `contract_ref`. When a
reference is present, it MUST bind the current or an explicitly known targeted head. Its
existing payload purpose remains unchanged.

## 12. State machine

Conforming reducers maintain proposal indexes by message ID and message hash, exact proposal
objects/hashes/references, accepted and rejected tuples, active head, and selected conflict
result. Observable concepts are `NO_ACTIVE_CONTRACT`, `CANDIDATE_PROPOSED`, `ACTIVE_HEAD`,
`COMPETING_CANDIDATES`, and `CONFLICT_RESOLVED`.

Only exact `CONTRACT_ACCEPT(accepted=true)` and exact `RESOLVE_CONFLICT` activate a head.
Invalid messages MUST NOT advance state.

## 13. Security boundary

Core v0.2 detects contract/proposal/branch/head substitution, stale or future acceptance,
cross-contract acceptance, replay retargeting, stale context/action execution, conflict
candidate substitution, and transcripts whose message chain is valid but agreement state
is not.

It does not prove signer identity, proposal/acceptance authority, quorum legitimacy, policy
correctness, hidden-transcript non-equivocation, transport security, or real-world legal
enforceability.
