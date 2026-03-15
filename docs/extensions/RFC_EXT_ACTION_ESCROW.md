# RFC_EXT_ACTION_ESCROW (EXT-ACTION-ESCROW)

## 1. Summary

`EXT-ACTION-ESCROW` defines transcript-native two-phase/three-step control for risky or irreversible tool actions.
It binds approval and policy context to commit operations so enforcement remains machine-checkable.

## 2. Message types (normative) {#message-types-normative}

- `ACTION_PREPARE`
- `ACTION_APPROVE`
- `ACTION_COMMIT`

## 3. Normative behavior

### 3.1 ACTION_PREPARE
`payload` MUST include:
- `escrow_id`
- `tool_call_request_hash`
- `policy_context_hash`

### 3.2 ACTION_APPROVE
`payload` MUST include:
- `escrow_id`
- `approval_hash`

### 3.3 ACTION_COMMIT
`payload` MUST include:
- `escrow_id`
- `tool_call_request_hash`
- `approval_hash`
- `policy_context_hash`

`ACTION_COMMIT` MUST bind all hashes to prior prepare/approve context for the same `escrow_id`.
Commit without valid prior prepare/approve MUST fail conformance.

## 4. Conformance expectations (normative)

Conformance suites for `EXT-ACTION-ESCROW` MUST include:
- pass flow `prepare -> approve -> commit`,
- expected-fail commit without prepare,
- expected-fail commit without approve,
- expected-fail hash-binding mismatch.

## 5. Security considerations

- Hash-bound prepare/approve/commit reduces replay and substitution attacks.
- Approval artifacts should be issuer-authenticated by policy.
- Escrow artifacts should be auditable alongside tool-gating and human-approval trails.

## 6. Registry entry {#registry-entry}

`EXT-ACTION-ESCROW` in `registry/extension_ids.json`.
