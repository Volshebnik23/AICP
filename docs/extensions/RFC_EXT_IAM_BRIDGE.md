# RFC: EXT-IAM-BRIDGE — OAuth/OIDC claim-to-authority mapping for delegation, tool gating, and human approval (Registered Extension)

**Status:** Shipped M28 extension surface (with executable conformance coverage in this repository).

EXT-IAM-BRIDGE standardizes a transport-neutral, machine-checkable mapping from external IAM attributes (issuer/scopes/roles/groups/acr/amr) into existing AICP-native controls.

This RFC reuses existing AICP primitives (`EXT-DELEGATED-IDENTITY`, `EXT-DELEGATION`, `EXT-TOOL-GATING`, `EXT-HUMAN-APPROVAL`) and does not define a new IAM protocol.

## 1. Scope and goals (normative)

EXT-IAM-BRIDGE defines:

- a contract policy object for IAM mapping under `payload.contract.ext.iam_bridge`,
- a normalized IAM claims snapshot object,
- deterministic conformance semantics for issuer/scope/role/group/acr/amr/approval evaluation.

## 2. Normalized IAM claims snapshot (normative)

A normalized IAM claims snapshot MUST be hashable and MUST NOT contain bearer-token material.

`iam_claims_snapshot` shape:

- `issuer` (MUST): IAM issuer identifier.
- `subject` (MUST): stable external principal identifier.
- `scopes` (MUST): string array (may be empty).
- `roles` (MUST): string array (may be empty).
- `groups` (MUST): string array (may be empty).
- `acr` (MAY): standardized authentication context class reference.
- `amr` (MAY): standardized auth method references array.
- `issued_at` (MUST): RFC3339 timestamp.
- `expires_at` (MUST): RFC3339 timestamp.

## 3. Delegated-identity integration (normative)

For this extension, `SUBJECT_BINDING_ISSUE.payload.binding_ref.object` MAY carry:

- `iam_claims_snapshot`

When present, it MUST follow the normalized shape above.

The snapshot participates in the existing `subject_binding` object hash via `binding_ref.object` and is therefore transcript-hash-bound.

## 4. Contract mapping object (normative)

When this extension is used, implementations SHOULD place mapping policy under:

- `CONTRACT_PROPOSE.payload.contract.ext.iam_bridge`

Normative minimum object:

- `issuers_allowlist` (MUST): non-empty array of accepted issuers.
- `scope_authority_map` (MUST): scope -> authority array.
- `role_authority_map` (MAY): role -> authority array.
- `group_authority_map` (MAY): group -> authority array.
- `protected_actions` (MUST): action ID -> requirement object.

Protected action requirement object:

- `required_authority` (MAY): authority identifiers required for action.
- `required_scopes` (MAY): external scopes required.
- `required_roles` (MAY): external roles required.
- `required_groups` (MAY): external groups required.
- `required_acr` (MAY): minimum required ACR value (exact-match profile for v0.1).
- `required_amr_any` (MAY): at least one AMR value must be present.
- `required_amr_all` (MAY): all listed AMR values must be present.
- `approval_required` (MAY, default false): action additionally requires M26 approval evidence.

## 5. Mapping semantics (normative)

For protected action evaluation:

1. Resolve acting identity via `ext.subject_binding_hash` (or equivalent extension-bound reference) to prior valid `SUBJECT_BINDING_ISSUE`.
2. Read `iam_claims_snapshot` from resolved subject binding.
3. Enforce issuer allowlist.
4. Derive effective authority from `scope_authority_map`, `role_authority_map`, and `group_authority_map` based on claims snapshot values.
5. Enforce action requirements for authority/scope/role/group.
6. Enforce step-up requirements (`required_acr`, `required_amr_any`, `required_amr_all`).
7. If `approval_required=true`, require valid M26 evidence (`APPROVAL_GRANT`) bound to the same protected target.

## 6. Step-up mapping to M26 (normative)

When `required_acr` or AMR requirements are unmet, implementations SHOULD emit/record M26 intervention evidence (`INTERVENTION_REQUIRED` / `INTERVENTION_COMPLETE`) or fail protected action evaluation according to policy.

This extension standardizes policy semantics; it does not standardize IdP challenge transport.

## 7. Security considerations

- Never place bearer tokens or raw credentials in transcript payloads.
- Enforce binding validity windows (`issued_at`/`expires_at`) and subject-binding linkage to prevent replay/substitution.
- Treat issuer matching as mandatory boundary control.
- Keep mapping policy minimal and explicit to reduce ambiguous privilege escalation.

## 8. Out of scope (normative boundary)

EXT-IAM-BRIDGE is:

- not an IAM provider,
- not token exchange,
- not JWT/OIDC wire-protocol verification,
- not enterprise app-domain policy translation (M29).

## 9. Conformance expectations

Conformance MUST cover at least:

- issuer allowlist enforcement,
- scope/role/group mapping correctness,
- delegated-identity binding linkage,
- ACR/AMR step-up enforcement,
- approval-required policy linkage to M26 evidence.

## 10. Registry entries

- `EXT-IAM-BRIDGE` in `registry/extension_ids.json`.
