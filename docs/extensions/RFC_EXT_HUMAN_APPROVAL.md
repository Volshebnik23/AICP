# RFC: EXT-HUMAN-APPROVAL — human-in-the-loop approvals and step-up intervention bridge (Registered Extension)

**Status:** Shipped M26 extension surface (with executable conformance coverage in this repository).

EXT-HUMAN-APPROVAL defines a conservative, machine-checkable primitive for human approval and denial decisions, plus minimal intervention hooks for external step-up completion.

This RFC intentionally does **not** define full IAM mapping (M28) or full external-transaction semantics (M40).

## 1. Message types (normative)

- `APPROVAL_CHALLENGE`
- `APPROVAL_GRANT`
- `APPROVAL_DENY`
- `INTERVENTION_REQUIRED`
- `INTERVENTION_COMPLETE`

All MUST use the Core envelope and transcript hash-chain rules.

## 2. APPROVAL_CHALLENGE payload (normative minimum)

`APPROVAL_CHALLENGE.payload` MUST include:

- `target_binding` (MUST): object containing exactly one of:
  - `tool_call_id`, or
  - `tool_call_hash`, or
  - `message_hash`.
- `approver_id` (MUST): approver actor identifier expected to sign/emit decision.
- `scope` (MUST): object defining what is being approved.
  - `action` (MUST): short machine-readable action label.
  - `constraints` (MAY): non-empty string list of bounded permissions.
- `expires_at` (MUST): RFC3339 timestamp (UTC recommended).
- `revocation_handle` (MAY): non-empty string for revocation or supersession tracking.

## 3. APPROVAL_GRANT and APPROVAL_DENY payloads (normative minimum)

`APPROVAL_GRANT.payload` and `APPROVAL_DENY.payload` MUST include:

- `challenge_message_hash` (MUST): hash of prior `APPROVAL_CHALLENGE`.
- `approver_id` (MUST): must match challenge approver.
- `target_binding` (MUST): must match challenge target binding exactly.
- `scope` (MUST): must match challenge scope exactly.
- `expires_at` (MUST): must match challenge expiry exactly.

Additional decision metadata MAY be included:

- `grant_ref` on grant,
- `deny_reason` on deny.

Conformance requirements:

- A grant/deny MUST reference a prior challenge in the same transcript.
- Decision sender and `approver_id` MUST equal challenge approver.
- Grant reuse across different targets MUST fail.
- A grant emitted after challenge expiry MUST fail.

## 4. Intervention bridge (normative minimum)

`INTERVENTION_REQUIRED.payload` MUST include:

- `reason_code` (MUST): one of `step_up_auth`, `manual_review`, `policy_exception`, `user_presence_required`.
- `provider_hint` (MUST): non-empty provider/integration hint (implementation-neutral).
- `expires_at` (MUST): RFC3339 timestamp.
- `intervention_handle` (MUST): stable non-empty handle for the external step.

`INTERVENTION_COMPLETE.payload` MUST include:

- `required_message_hash` (MUST): hash of prior `INTERVENTION_REQUIRED`.
- `intervention_handle` (MUST): must equal required handle.
- `completion_ref` (MAY): external completion evidence reference.

Conformance requirements:

- Completion MUST reference a prior required message.
- Completion handle MUST match exactly.

## 5. Contract extension object (optional)

When contract-level policy is declared, implementations SHOULD place this under:

- `CONTRACT_PROPOSE.payload.contract.ext.human_approval`

Normative minimum object shape:

- `default_required` (boolean): whether protected actions require approval by default.
- `approval_policy_ref` (non-empty string): policy reference for approval semantics.

## 6. Mediator/enforcer semantics (normative)

For protected actions, a mediator/enforcer MUST be able to verify transcript evidence that a valid `APPROVAL_GRANT` exists for the exact target binding and scope before allowing action progression.

A `TOOL_CALL_REQUEST` MAY declare requirement under `payload.ext.human_approval` with:

- `required: true`
- target binding (`tool_call_id` and/or `tool_call_hash`)

If requirement is declared and no valid grant is present, conformance MUST fail.

## 7. OAuth/OIDC and delegated-identity mapping note (non-goal for this milestone)

This extension defines protocol-native approval artifacts only. Deployments MAY map approvers to OAuth/OIDC subject claims, and MAY combine with delegated-identity controls. Normative IAM mapping profiles are defined by EXT-IAM-BRIDGE (M28).

## 8. Security considerations

- Challenge/decision binding prevents UX-only approval spoofing.
- Expiry checks reduce replay risk of stale approvals.
- Approver identity matching reduces signer substitution attacks.
- Intervention handles should avoid embedding secrets and should be integrity-protected by deployment policy.

## 9. Conformance expectations

Conformance MUST cover at least:

- target binding presence/validity,
- challenge approver/scope/expiry presence,
- grant/deny challenge reference validity,
- signer/approver equality,
- anti-reuse across different targets,
- expiry enforcement,
- intervention required/complete linkage.

## 10. Registry entries

- `EXT-HUMAN-APPROVAL` in `registry/extension_ids.json`.
- Message types above in `registry/message_types.json`.
