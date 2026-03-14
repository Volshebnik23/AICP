# RFC: EXT-REDACTION — redaction declarations, retention policy, and vault-neutral PII references (Registered Extension)

**Status:** Shipped M24 extension surface (with executable conformance coverage in this repository).

EXT-REDACTION defines a minimal, verifiable M24 foundation for declaring redacted derivatives without mutating prior transcript records.

This RFC is intentionally conservative: it standardizes redaction declarations, contract retention-policy fields, and a vault-neutral `pii_ref` pattern. It does **not** standardize full deletion workflows, vendor vault APIs, or advanced cryptographic transformation proofs.

## 1. Message type (normative)

- `CONTENT_REDACTED`

`CONTENT_REDACTED` MUST use the Core envelope and declares a redacted derivative of already-recorded content.

## 2. CONTENT_REDACTED payload (normative minimum)

`CONTENT_REDACTED.payload` MUST include:

- `original_message_hash` (MUST): hash of a prior transcript message being redaction-derived.
- `redaction_policy_ref` (MUST): machine-readable policy/rule reference.
- `redaction_proof` (MUST): minimal structured proof object (not free-form blob).

`CONTENT_REDACTED.payload` MAY include:

- `artifact_refs`: supporting evidence references.
- `pii_refs`: array of vault-neutral `pii_ref` objects.
- `replacement_summary`: compact structured summary of replaced classes, never raw sensitive values.

## 3. Redaction proof object (normative minimum)

`redaction_proof` MUST be an object with:

- `proof_type` (MUST): proof type identifier.
- `proof_ref` (MUST): dereferenceable/auditable proof reference.
- `generated_at` (MUST): RFC3339 timestamp.

## 4. Contract retention policy (normative)

When retention is contractually declared for this extension, implementations MUST place it under:

- `CONTRACT_PROPOSE.payload.contract.ext.redaction.retention_policy`

`retention_policy` MUST include:

- `ttl_seconds` (MUST): retention TTL in seconds.
- `delete_semantics` (MUST): one of `hard-delete`, `soft-delete`, `tombstone`.
- `audit_retention_seconds` (MUST): audit retention period in seconds.
- `policy_category` (MUST): policy category for retention/deletion controls; MUST be `retention_deletion`.
- `policy_ref` (MUST): reference to the governing retention/deletion policy artifact.

`audit_retention_seconds` SHOULD be greater than or equal to `ttl_seconds`.

Delete semantics standardization: for M24, `delete_semantics` is standardized by the authoritative enum in `schemas/extensions/ext-redaction-payloads.schema.json` (no separate registry file).

## 5. Vault-neutral pii_ref (normative)

A `pii_ref` object is a stable transcript handle to sensitive data stored out-of-band.

`pii_ref` MUST:

- be hashable and stable within a transcript,
- avoid raw plaintext PII,
- support least-privilege access through policy references,
- remain implementation-neutral (no mandatory vendor vault API).

`pii_ref` minimum fields:

- `ref_id` (MUST)
- `class` (MUST)
- `controller` (MUST)
- `access_policy_ref` (MUST)
- `handle_digest` (MAY)

`pii_ref` MUST NOT include inline plaintext sensitive values.

## 6. Verifiability and transcript integrity

- Redaction is represented as a new declaration (`CONTENT_REDACTED`) and MUST NOT mutate the original message record.
- `original_message_hash` MUST resolve to an earlier message in the same transcript.
- Standard hash-chain integrity checks remain applicable.

## 7. Security considerations

- Validate `original_message_hash` resolution before processing redaction declarations to avoid forged replacement lineage.
- Require policy-controlled access for `pii_ref` dereferencing; transcript presence alone is not authorization.
- Example: if `replacement_summary` includes raw identifier values, treat as data-leak regression and reject publication.

## 8. Conformance expectations

Suite: `conformance/extensions/RD_REDACTION_0.1.json`

Conformance enforces:

- original-hash binding to prior messages,
- required policy/proof fields,
- pii_ref structural and anti-inline-PII constraints,
- contract retention policy required fields,
- chain-integrity behavior (new declaration, not mutation).

## 9. Registry entries

- Extension ID: `EXT-REDACTION`
- Message type: `CONTENT_REDACTED`

