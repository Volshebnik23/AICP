# RFC EXT-TOOL-GATING

## 1. Purpose (normative)
`EXT-TOOL-GATING` standardizes tool/side-effect steps as protocol messages with optional external gating controls.
It enables deterministic transcript evidence for pre-execution authorization (`blocking`) and post-execution attestation (`audit`).

## 2. Contract configuration (normative)
Implementations MUST read tool gating configuration from the first `CONTRACT_PROPOSE` payload contract using:

1. `payload.contract.ext.tool_gating`, OR
2. fallback `payload.contract.extensions["EXT-TOOL-GATING"]`.

Configuration object:
- `mode` (REQUIRED): `"blocking"` or `"audit"`.
- `acceptors` (OPTIONAL): array of sender IDs permitted to emit `TOOL_CALL_VERDICT` and `TOOL_CALL_ATTEST`.

## 3. Message types (normative)
- `TOOL_CALL_REQUEST`
- `TOOL_CALL_VERDICT`
- `TOOL_CALL_RESULT`
- `TOOL_CALL_ATTEST`

## 4. Binding rules (normative)
- `TOOL_CALL_VERDICT.payload.target_request_hash` MUST equal `message_hash` of a specific earlier `TOOL_CALL_REQUEST`.
- `TOOL_CALL_RESULT.payload.target_request_hash` MUST equal `message_hash` of a specific earlier `TOOL_CALL_REQUEST`.
- `TOOL_CALL_ATTEST` MUST bind to a specific result and request:
  - `payload.target_result_hash` MUST equal `message_hash` of a specific `TOOL_CALL_RESULT`.
  - `payload.target_request_hash` MUST equal the bound result/request hash chain for that result.

## 5. Mode rules (normative)

### 5.1 Blocking mode
For each `TOOL_CALL_RESULT`:
- `payload.verdict_ref` MUST be present.
- `payload.verdict_ref` MUST reference `message_id` of a prior `TOOL_CALL_VERDICT` where:
  - `decision == "ALLOW"`, and
  - `target_request_hash == TOOL_CALL_RESULT.payload.target_request_hash`.

### 5.2 Audit mode
For each `TOOL_CALL_RESULT`:
- There MUST be a later `TOOL_CALL_ATTEST` where:
  - `target_result_hash == TOOL_CALL_RESULT.message_hash`, and
  - `target_request_hash == TOOL_CALL_RESULT.payload.target_request_hash`.

## 6. Security considerations
- Prevent spoofing by authenticating senders of verdicts/attestations.
- Prevent replay by binding all decisions/results/attestations to request/result hashes.
- Constrain authority (`acceptors`) to reduce role escalation.
- Reject/flag "result without allow" in blocking mode to prevent bypass of gating controls.
