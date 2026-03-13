# RFC: EXT-CONFIDENTIALITY — confidentiality mode binding and selective disclosure evidence (Registered Extension)

**Status:** Shipped M23 extension surface (with executable conformance coverage in this repository).

EXT-CONFIDENTIALITY makes privacy mode selection externally verifiable by binding CAPNEG negotiation outcomes to a contract-level confidentiality object.

This RFC defines **binding and evidence requirements only**. It does **not** define a full redaction object model, retention/deletion semantics, or vault-neutral PII handle semantics (those are out of scope for this milestone).

## 1. Scope and intent

- Reuse EXT-CAPNEG for negotiation (`supported_privacy_modes`, `selected.privacy_mode`).
- Standardize contract-time confidentiality binding under `payload.contract.ext.confidentiality`.
- Make selective disclosure mode claims checkable by third-party enforcers using deterministic fields.

## 2. Canonical M23 privacy modes

For M23, canonical privacy modes are:

- `full`
- `redacted`
- `metadata-only`
- `classification-only`

Legacy registry values (for backward compatibility with prior CAPNEG fixtures) may remain registered but new implementations SHOULD prefer the canonical modes above.

## 3. Contract object (normative minimum)

When this extension is used, `CONTRACT_PROPOSE.payload.contract.ext.confidentiality` MUST be an object with this minimum shape:

- `mode_id` (MUST):
  - MUST be one of the canonical M23 privacy modes above, or
  - another registered privacy mode, or
  - a namespaced identifier (`vendor:*` or `org:*`).
- `negotiation_result_hash` (MUST when CAPNEG-mediated acceptance is present): object hash of accepted CAPNEG `negotiation_result` (`object_hash("capneg.negotiation_result", negotiation_result)`).
- `artifact_refs` (MAY): generic evidence refs for external audits.
- `redaction_artifact_refs` (MUST for `redacted`): non-empty references proving redaction policy/artifact presence.
- `metadata_projection` (MUST for `metadata-only`): non-empty object that states disclosed metadata fields/projections.
- `classification_labels` (MUST for `classification-only`): non-empty labels array.
- `classification_evidence_refs` (MUST for `classification-only`): non-empty references for label provenance/evidence.

Reference schema: `schemas/extensions/ext-confidentiality-artifacts.schema.json`.

## 4. CAPNEG integration and contract binding rules (normative)

For transcripts containing a valid `CAPABILITIES_ACCEPT` (`accepted: true`) for a negotiated session:

1. Any subsequent `CONTRACT_PROPOSE` in that transcript MUST include `payload.contract.ext.confidentiality`.
2. `payload.contract.ext.confidentiality.mode_id` MUST exactly equal accepted `selected.privacy_mode`.
3. `payload.contract.ext.confidentiality.negotiation_result_hash` MUST match the accepted negotiation result hash.
4. Mode-specific required artifacts MUST be present:
   - `full`: no additional mode-specific artifact field is required.
   - `redacted`: `redaction_artifact_refs` MUST be a non-empty array.
   - `metadata-only`: `metadata_projection` MUST be a non-empty object.
   - `classification-only`: `classification_labels` and `classification_evidence_refs` MUST both be non-empty arrays.

## 5. External enforcer reliance model

An external enforcer MAY rely on:

- CAPNEG transcript evidence (`CAPABILITIES_PROPOSE` + `CAPABILITIES_ACCEPT`),
- `negotiation_result_hash` integrity binding,
- contract object presence and mode-specific required fields.

An external enforcer MUST NOT infer full redaction semantics from this RFC alone. This extension proves declared mode binding and required artifact presence, not deep transformation correctness.

## 6. Conformance coverage

Suite: `conformance/extensions/CF_CONFIDENTIALITY_0.1.json`

Checks include:

- contract confidentiality object presence after CAPNEG acceptance,
- privacy mode registry/namespaced validity,
- CAPNEG-selected privacy mode binding,
- negotiation-result hash binding,
- mode-specific artifact requirements for `redacted`, `metadata-only`, and `classification-only`.

## 7. Security and compatibility notes

- Hash binding prevents silent mode mismatch between negotiation and contract.
- Required artifact fields reduce unverifiable “privacy mode promises.”
- Existing legacy CAPNEG privacy modes remain supported in registry for backward compatibility.

## 8. Registry entry

- Extension ID: `EXT-CONFIDENTIALITY`
- Registry file: `registry/extension_ids.json`

