# RFC_EXT_ADMISSION (EXT-ADMISSION)

Status: Experimental  
AICP Version: 0.1

## 1. Purpose

`EXT-ADMISSION` defines transcript-native admission lifecycle artifacts for crowded sessions where entry, renewal, and revocation decisions must be explicit, auditable, and machine-checkable.

## 2. Scope boundaries (normative)

This extension is **not**:
- a hosted identity provider,
- a Sybil/spam classifier,
- a staking economics engine,
- a transport admission gateway implementation.

This extension standardizes content-layer admission evidence only.

## 3. Message types (normative)

- `ADMISSION_REQUEST`
- `ADMISSION_OFFER`
- `ADMISSION_ACCEPT`
- `ADMISSION_REJECT`
- `ADMISSION_RENEW`
- `ADMISSION_REVOKE`

## 4. Admission lifecycle semantics (normative)

### 4.1 ADMISSION_REQUEST
`payload` MUST include:
- `request_id`
- `requested_roles` (non-empty array)
- `requested_scopes` (non-empty array)
- `risk_tier`

`payload` MAY include:
- `attestation_refs` (for trust/status evidence)
- `stake_ref`
- `desired_quota_class`
- `priority_class`

### 4.2 ADMISSION_OFFER
`payload` MUST include:
- `request_id` (references request)
- `offer_id`
- `granted_roles`
- `granted_scopes`
- `quota_class`
- `lease_profile`

Rules:
- granted roles/scopes MUST be coherent with request context and policy.

### 4.3 ADMISSION_ACCEPT
`payload` MUST include:
- `request_id`
- `offer_id`

Acceptance confirms participant agreement to offered constraints.

### 4.4 ADMISSION_REJECT
`payload` MUST include:
- `request_id`
- `reason_code`

### 4.5 ADMISSION_RENEW
`payload` MUST include:
- `request_id`
- `prior_request_id`
- `reason_code`

### 4.6 ADMISSION_REVOKE
`payload` MUST include:
- `request_id`
- `reason_code`

## 5. No-silent-drop rule (normative)

When admission is denied, revoked, or deferred by sanction/throttle policy, participants MUST receive explicit machine-readable transcript evidence (`ADMISSION_REJECT`, `ADMISSION_REVOKE`, or queue overload/throttle artifacts). Silent drops MUST NOT be used as enforcement semantics.

## 6. Trust/attestation hook semantics (normative)

`attestation_refs` and `stake_ref` are reference hooks for external trust/status/anti-Sybil signals.

Rules:
- references MUST be stable, non-empty, and transcript-verifiable in format,
- this extension does not define attestation crypto primitives,
- policy outcomes MUST remain explainable via transcript reason codes.

## 7. Conformance expectations

Conformance MUST cover at least:
- request shape and role/scope presence,
- offer coherence with request constraints,
- reason-code validity for reject/revoke/renew outcomes,
- attestation/stake reference shape checks,
- renewal linkage to prior admission context,
- explicit no-silent-drop rejection/revocation evidence.

## 8. Security considerations

- Admission artifacts should be authenticated and signer-attributed.
- Reject/revoke reason codes must avoid secret leakage while remaining machine-actionable.
- Example: if admission is denied for scope escalation, return a policy reason code (for example `SCOPE_VIOLATION`) rather than dropping subsequent messages silently.

## 9. Privacy considerations

- Do not embed raw financial identity or private trust proofs in admission payloads.
- Prefer references/hashes for attestations and stake/bond evidence.
- Minimize role/scope disclosure to required governance context.

## 10. Relationship to adjacent milestones

- M26 (`EXT-HUMAN-APPROVAL`): admission/renewal can require approval evidence.
- M27 (`EXT-OBSERVABILITY`): admission outcomes should be observable for ops/debug.
- M20/M21 trust/status surfaces: this extension consumes references, not trust-network semantics.

## 11. Registry entry

- `EXT-ADMISSION` in `registry/extension_ids.json`.
