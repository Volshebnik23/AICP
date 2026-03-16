# AICP-COMMERCE-ACP@0.1 (Normative, optional profile)

## Purpose and scope

`AICP-COMMERCE-ACP@0.1` defines a deterministic, optional profile for commerce-bound transcript interoperability where irreversible external steps are executed outside AICP and anchored inside AICP as auditable artifacts.

This profile standardizes composition across already-shipped AICP surfaces:

- CAPNEG profile negotiation
- policy-eval gating evidence
- human-approval gating evidence
- enforcement coherence evidence
- external transaction declaration/result linkage
- redaction-safe PII reference handling

## Explicit non-goals

This profile does **not** define:

- payment rails,
- checkout/order/cart APIs,
- settlement/reconciliation semantics,
- vendor-specific commerce runtime contracts.

AICP remains content-layer only; external checkout/payment rails remain external.

## Required extensions (normative)

- `EXT-CAPNEG`
- `EXT-ENFORCEMENT`
- `EXT-POLICY-EVAL`
- `EXT-EXTERNAL-TRANSACTION`
- `EXT-HUMAN-APPROVAL`
- `EXT-REDACTION`

## Required suites (normative)

- `conformance/core/CT_CORE_0.1.json`
- `conformance/extensions/CN_CAPNEG_0.1.json`
- `conformance/extensions/PE_POLICY_EVAL_0.1.json`
- `conformance/extensions/ENF_ENFORCEMENT_0.1.json`
- `conformance/extensions/ET_EXTERNAL_TRANSACTION_0.1.json`
- `conformance/extensions/HA_HUMAN_APPROVAL_0.1.json`
- `conformance/extensions/RD_REDACTION_0.1.json`
- `conformance/extensions/CM_COMMERCE_ACP_PROFILE_0.1.json`

## CAPNEG expectations (normative)

Commerce-bound transcripts claiming this profile MUST:

- declare required profile `AICP-COMMERCE-ACP@0.1` in CAPNEG when profile-gated operation is expected,
- select `AICP-COMMERCE-ACP@0.1` in `CAPABILITIES_PROPOSE.negotiation_result.selected.aicp_profile` for successful profile-bound flows,
- reject or fail deterministic conformance when downgraded/absent profile selection is used in profile-bound flows.

## Deterministic interoperability boundary (normative)

Profile conformance is determined by transcript-native evidence and required suite outcomes only.

Runtime/vendor behavior outside transcript evidence is not part of conformance determination.

## Privacy / PII boundary (normative)

- Receipt evidence MUST be anchor/reference oriented.
- Sensitive receipt data SHOULD use `pii_ref` and redaction-safe references.
- Inline raw sensitive receipt fields are non-conformant for this profile.

## ACP mapping note (informative only)

ACP is a first integration mapping target for this profile, but mapping is non-binding and informative only.

A transcript is conformant because it satisfies AICP profile semantics, not because an ACP-specific runtime contract is present.

## Security considerations

- Enforce deterministic binding among policy decisions, approvals, and irreversible external-step results.
- Treat profile downgrade attempts as conformance/security failures for profile-bound flows.
- Require declaration/result linkage and digest/evidence coherence for auditability.

## Registry entry

- `registry/aicp_profiles.json` → `AICP-COMMERCE-ACP@0.1`
