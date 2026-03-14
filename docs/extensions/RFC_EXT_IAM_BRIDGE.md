# RFC_EXT_IAM_BRIDGE (EXT-IAM-BRIDGE)

Status: Experimental (extension maturity); roadmap milestone M28 is shipped in `ROADMAP.md`  
AICP Version: 0.1

## 1. Purpose

`EXT-IAM-BRIDGE` defines a conservative, machine-checkable mapping from external IAM attributes (OAuth/OIDC style claims) into existing AICP-native controls.

This extension is intentionally content-layer and transport-neutral. It reuses existing AICP surfaces (`EXT-DELEGATION`, `EXT-DELEGATED-IDENTITY`, `EXT-HUMAN-APPROVAL`, `EXT-TOOL-GATING`) rather than introducing a new IAM protocol.

## 2. Scope boundaries (normative)

This extension is a mapping and evidence profile. It is **not**:

- an IAM provider,
- token exchange,
- JWT/OIDC wire-protocol verification,
- vendor-specific login/session protocol,
- enterprise app-domain policy translation framework.

Implementations MAY validate tokens externally, but transcript-level conformance for this extension MUST rely on normalized, hashable claim snapshots and policy objects defined here.

## 3. Mapping surface (normative)

External IAM concepts mapped by this extension:

- OAuth scopes,
- roles,
- groups,
- issuer,
- OIDC `acr`,
- OIDC `amr`.

Mapped targets in AICP-native controls:

- delegation `authority_subset`,
- delegation `scope`,
- protected action requirements,
- human-approval / intervention requirements,
- tool-gating authority decisions where relevant.

## 4. Normalized IAM claims snapshot (normative)

### 4.1 Object

A normalized, transport-neutral snapshot object MUST use this shape:

- `issuer` (string)
- `subject` (string)
- `scopes` (string array, MAY be empty)
- `roles` (string array, MAY be empty)
- `groups` (string array, MAY be empty)
- `acr` (string, OPTIONAL)
- `amr` (string array, OPTIONAL; MAY be empty)
- `issued_at` (RFC3339 date-time)
- `expires_at` (RFC3339 date-time)

### 4.2 Hashing and safety constraints

- Snapshot objects MUST be hashable and deterministic.
- Bearer tokens and raw token material MUST NOT appear in transcript payloads for this extension.
- Snapshot evaluation MUST be machine-checkable without dependency on JWT parsing libraries in protocol semantics.

### 4.3 Placement

`EXT-IAM-BRIDGE` reuses delegated identity:

- `SUBJECT_BINDING_ISSUE.payload.binding_ref.object.ext.iam_bridge_claims` carries the normalized claims snapshot.
- `SUBJECT_BINDING_ISSUE.payload.binding_ref.object.ext.iam_bridge_claims_hash` carries `object_hash("iam_claims_snapshot", iam_bridge_claims)`.

## 5. Contract policy object (normative)

Contract policy MUST be declared at:

- `CONTRACT_PROPOSE.payload.contract.ext.iam_bridge`

Normative minimum fields:

- `issuer_allowlist` (non-empty string array)
- `scope_to_authority` (map: scope -> non-empty authority token array)
- `role_to_authority` (map: role -> non-empty authority token array)
- `group_to_authority` (map: group -> non-empty authority token array)
- `actions` (map: action_id -> action requirement object)

Action requirement object MAY include:

- `required_scopes_any` / `required_scopes_all`
- `required_roles_any` / `required_roles_all`
- `required_groups_any` / `required_groups_all`
- `required_authority_any`
- `required_acr`
- `required_amr_any` / `required_amr_all`
- `requires_human_approval` (boolean)
- `approval_scope_action` (string, SHOULD be present when `requires_human_approval=true`)

## 6. Acting message context (normative)

When a protected action is evaluated under this extension, a message SHOULD include:

- `ext.subject_binding_hash` (from `EXT-DELEGATED-IDENTITY`), and
- `ext.iam_bridge.action` (contract action key).

Evaluators MAY also consume optional message-level declarations:

- `ext.iam_bridge.required_scopes`
- `ext.iam_bridge.required_roles`
- `ext.iam_bridge.required_groups`

## 7. Step-up mapping (normative)

`required_acr`, `required_amr_any`, and `required_amr_all` define step-up requirements at action level.

If current claims snapshot does not satisfy step-up requirements, the protected action MUST be rejected by conformance/evaluator semantics.

For M26 alignment:

- if `requires_human_approval=true`, protected action MUST have transcript evidence of valid `APPROVAL_GRANT` matching policy scope before action progression;
- deployments MAY emit `INTERVENTION_REQUIRED`/`INTERVENTION_COMPLETE` from `EXT-HUMAN-APPROVAL` as runtime bridge artifacts, but this extension does not orchestrate IdP interactions.

## 8. Enforcement semantics (normative)

For a message evaluated under `EXT-IAM-BRIDGE`:

1. the acting message MUST link to a valid delegated-identity binding context;
2. issuer MUST satisfy contract allowlist;
3. required scopes/roles/groups MUST be present in normalized claims as demanded by action policy;
4. mapped authorities from claims MUST authorize declared delegation/tool/action needs;
5. step-up (`acr`/`amr`) requirements MUST hold;
6. approval evidence MUST exist when policy requires approval.

## 9. Security considerations

- Keep snapshots minimal (claims only) and avoid raw token transport.
- Enforce claim expiry and delegated binding expiry.
- Validate issuer allowlists deterministically.
- Treat authority tokens as policy-critical inputs.

## 10. Registry entry

- `EXT-IAM-BRIDGE` in `registry/extension_ids.json`.
