# AICP Core v0.1 (Normative)

**AICP — Agent Interaction Content Protocol**

“An open content-layer protocol for agent-to-agent interaction with enforceable policies.”

## 1. Scope

This document is the canonical normative Core v0.1 source. Implementations MUST treat this Markdown file as the source of truth for Core protocol behavior.

## 2. Message envelope (normative)

A Core message MUST include:
- `session_id`
- `message_id`
- `timestamp`
- `sender`
- `message_type`
- `payload`

Messages MUST include `contract_id`. Messages MAY include `contract_ref`, `prev_msg_hash`, `message_hash`, `signatures`, and relation metadata.

Implementations MUST validate incoming messages against the Core message schema at the boundary.

## 3. Core message types (normative)

Core v0.1 message taxonomy:
- `CONTRACT_PROPOSE`
- `CONTRACT_ACCEPT`
- `CONTEXT_AMEND`
- `ATTEST_ACTION`
- `RESOLVE_CONFLICT`

Implementations MUST use `CONTEXT_AMEND` for amendment flow. Earlier draft labels are non-normative and MUST NOT be used in Core conformance artifacts.

## 4. State machine and invariants (normative)

Implementations MUST model session state as a replicated state machine over valid messages.

Minimum invariants:
- `session_id` MUST remain constant within a transcript.
- `message_id` values MUST be unique within a transcript.
- `prev_msg_hash` (when present) MUST equal the previous message’s `message_hash`.
- Contract-changing operations MUST bind to explicit contract/version references.

Conflict resolution MUST be represented via `RESOLVE_CONFLICT` and SHOULD be quorum/signer-policy bound.

## 5. Hashing and signatures (normative minimum)

Hashing:
- Object hashes MUST use deterministic canonicalization and SHA-256 over `AICP1\0<object_type>\0<canonical-json>` preimage semantics.
- `message_hash` MUST be recomputable from message body excluding `message_hash` and `signatures`.

Signatures:
- Signature verification SHOULD use Ed25519 profile(s) registered for Core.
- If signatures are present, their `object_hash` MUST match the message hash being signed.

## 6. Core payload requirements (normative minimum)

Core payload schemas are machine-checkable via `schemas/core/aicp-core-payloads.schema.json` and MUST be enforced in Core conformance where configured.

Minimum required fields by type:
- `CONTRACT_PROPOSE`: `contract` (with optional `contract_hash`, `note`)
- `CONTRACT_ACCEPT`: `accepted` (optional `replay`)
- `CONTEXT_AMEND`: `amendment`
- `ATTEST_ACTION`: `action_id`, `action_type`, plus one attestation shape:
  - Result attestation: includes `result_hash` (and may include `authority_ref`, `scope_ref`).
  - Consent/authority attestation: includes `consent_ref` (and may include `authority_ref`, `scope_ref`).
  - `tool_name` remains optional.
- `RESOLVE_CONFLICT`: `conflict_id`, `conflict_class`, `resolution`, `candidates`

## 7. Conformance requirements (normative minimum)

Core suite execution MUST verify, at minimum:
- Core message schema validation per record
- Core payload schema validation for mapped message types
- hash-chain integrity
- invariants (constant `session_id`, unique `message_id`)
- expected message-type sequence
- `message_hash` recomputation
- signature hash consistency and signature verification when signatures are present

Core conformance artifacts are defined in `conformance/core/CT_CORE_0.1.json` and the conformance runner.

## 8. Canonical artifact pointers

- Core message schema: `schemas/core/aicp-core-message.schema.json`
- Core payload schema: `schemas/core/aicp-core-payloads.schema.json`
- Core conformance suite: `conformance/core/CT_CORE_0.1.json`
- Core fixtures: `fixtures/golden_transcripts/`
