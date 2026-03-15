# RFC_EXT_RESPONSIBILITY (EXT-RESPONSIBILITY)

## 1. Summary

`EXT-RESPONSIBILITY` defines transcript-native responsibility-transfer and chain-failure attestation artifacts for multi-agent service chaining.
It provides operational (non-legal) accountability hints, transfer lifecycle messages, and machine-readable failure evidence.

## 2. Message types (normative) {#message-types-normative}

- `RESPONSIBILITY_ASSIGN`
- `RESPONSIBILITY_ACCEPT`
- `RESPONSIBILITY_REVOKE`
- `CHAIN_FAILURE_ATTEST`

## 3. Transfer lifecycle semantics (normative) {#transfer-lifecycle-semantics-normative}

### 3.1 RESPONSIBILITY_ASSIGN
`payload` MUST include:
- `transfer_id`
- `action_ref`
- `from_party`
- `to_party`
- `warranty_class`

### 3.2 RESPONSIBILITY_ACCEPT
`payload` MUST include:
- `transfer_id`
- `accepted_by`

`RESPONSIBILITY_ACCEPT.transfer_id` MUST reference a prior assignment.

### 3.3 RESPONSIBILITY_REVOKE
`payload` MUST include:
- `transfer_id`
- `reason_code`

`RESPONSIBILITY_REVOKE.transfer_id` MUST reference a prior assignment.

### 3.4 Lifecycle closure
Each assignment MUST conclude with explicit accept or revoke evidence.

## 4. Chain failure attestation semantics (normative)

`CHAIN_FAILURE_ATTEST` MUST include:
- `failure_id`
- `classification` (`transient` or `permanent`)
- `reason_code`

If `classification=transient`, `retry_after_seconds` MUST be present and > 0.
`compensating_action_ref` is optional and SHOULD be supplied when rollback/compensation is available.

## 5. Conformance expectations (normative)

Conformance suites for `EXT-RESPONSIBILITY` MUST include:
- pass transfer flow with assign/accept and failure attestation,
- expected-fail accept/revoke without prior assign,
- expected-fail lifecycle without terminal accept/revoke,
- expected-fail chain-failure attestation violating classification requirements.

## 6. Security considerations

- Responsibility transfer artifacts should be signed/authenticated by policy.
- Failure attestations should include hash-bound references to affected actions/provenance context.
- Warranty class labels are operational hints and do not represent legal contracts.

## 7. Registry entry {#registry-entry}

`EXT-RESPONSIBILITY` in `registry/extension_ids.json`.
