# RFC_EXT_DELEGATED_IDENTITY (EXT-DELEGATED-IDENTITY)

Status: Experimental  
AICP Version: 0.1

## 1. Purpose
`EXT-DELEGATED-IDENTITY` binds an `agent_id` to an authenticated `account_id` with scoped authority issued by an identity provider/auth authority.

This extension is **OPTIONAL**. Platforms MAY require it via profiles/policies. When present, it MUST be machine-checkable.

## 2. Binding object triple (normative)
A subject binding is represented as a hashable triple:

- `object_type`: `"subject_binding"`
- `object`:
  - `binding_id`
  - `agent_id`
  - `account_id`
  - `issuer`
  - `scopes[]`
  - `issued_at`
  - `expires_at`
- `object_hash`: computed as `object_hash("subject_binding", object)`

## 3. Message types (normative)
- `SUBJECT_BINDING_ISSUE`
- `SUBJECT_BINDING_REVOKE`

## 4. Envelope attachment for acting-on-behalf-of (normative)
Any AICP message MAY include:

- `ext.subject_binding_hash`

If present, it MUST refer to a previously issued binding and MUST be valid at message time.

## 5. Validity rules (normative)
For conformance and third-party enforcement:

1. `SUBJECT_BINDING_ISSUE` MUST include a non-empty `signatures` array.
2. `SUBJECT_BINDING_ISSUE.sender` MUST equal `binding_ref.object.issuer` when `binding_ref` is present.
3. If `binding_ref` is present, `binding_hash` MUST equal `binding_ref.object_hash`.
4. If `binding_ref` is present, `binding_ref.object_hash` MUST equal `object_hash("subject_binding", binding_ref.object)`.
5. A message using `ext.subject_binding_hash` is valid only if:
   - a prior `SUBJECT_BINDING_ISSUE` exists for that hash,
   - binding `agent_id` equals message `sender`,
   - message `timestamp` is not later than binding `expires_at`,
   - no `SUBJECT_BINDING_REVOKE` for that hash is effective at or before message `timestamp`.

## 6. Security considerations
- Issuer signatures and key lifecycle evidence are required to prevent spoofed bindings.
- Revocation processing MUST be time-aware (`effective_at`) to avoid stale delegated authority use.
- Implementations SHOULD keep binding scope minimal and short-lived.


## 7. EXT-IAM-BRIDGE integration note (normative compatibility)
`binding_ref.object` MAY include `iam_claims_snapshot` for EXT-IAM-BRIDGE evaluation.
When present, it is part of the `subject_binding` hashed object and MUST NOT contain bearer token material.
