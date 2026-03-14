# RFC_EXT_OBSERVABILITY (EXT-OBSERVABILITY)

Status: Experimental  
AICP Version: 0.1

## 1. Purpose

`EXT-OBSERVABILITY` defines a minimal, transcript-native production-attributes layer for:

- trace correlation across messages/tool calls/workflow steps,
- reusable SLA/error operational signals,
- normalized metering/accounting events.

This extension is content-layer only. It does **not** define transport header processing, hosted telemetry pipelines, or billing systems.

## 2. Scope boundaries (normative)

This extension is **not**:

- HTTP header parsing or vendor tracing SDK behavior,
- an external monitoring backend,
- pricing, invoicing, or payment settlement logic.

Conformance MUST be verifiable from transcript artifacts.

## 3. Message surface (normative)

- `OBS_SIGNAL`

`OBS_SIGNAL.payload` MUST contain exactly one of:

- `trace`,
- `sla`,
- `metering`.

## 4. Correlation model (normative)

Observability signals MUST bind to exactly one transcript-relevant target via `correlation_ref`, using one of:

- `message_hash`,
- `tool_call_id`,
- `tool_call_hash`,
- `workflow_step_ref`.

Bindings MUST remain deterministic and hashable.

## 5. Trace payload (normative)

`trace` object fields:

- `trace_id` (MUST): W3C-compatible trace identifier token.
- `span_id` (MUST): W3C-compatible span identifier token.
- `correlation_ref` (MUST): one target binding as defined above.
- `parent_span_id` (MAY): parent span identifier.
- `trace_flags` (MAY): normalized tracing flag token.
- `trace_state_ref` (MAY): implementation-neutral reference token.

Rules:

- `trace_id` and `span_id` MUST be non-empty and machine-parseable.
- if `parent_span_id` is present it MUST differ from `span_id`.
- no transport headers are required in payloads.

## 6. SLA/error signal payload (normative)

`sla` object fields:

- `signal_type` (MUST): one of `drop`, `throttle`, `deny`, `degraded`, `timeout`.
- `reason_code` (MUST): registered policy reason code or namespaced `vendor:`/`org:` identifier.
- `correlation_ref` (MUST): one target binding as defined above.
- `observed_at` (MUST): RFC3339 timestamp.

Rules:

- reason code reuse from `registry/policy_reason_codes.json` is preferred.
- unregistered, non-namespaced reason codes MUST fail observability conformance.

## 7. Metering payload (normative)

`metering` object fields:

- `meter_type` (MUST): usage class label (for example `tokens_input`, `tokens_output`, `tool_call_count`).
- `quantity` (MUST): non-negative numeric value.
- `unit` (MUST): normalized unit label.
- `correlation_ref` (MUST): one target binding as defined above.
- `observed_at` (MUST): RFC3339 timestamp.
- `subject_ref` (MAY): accountable subject identifier.
- `billing_ref` (MAY): external accounting reference.
- `window_start` / `window_end` (MAY): usage window timestamps.

Rules:

- metering payloads MUST remain accounting-friendly but vendor-neutral.
- pricing semantics are explicitly out of scope.

## 8. Conformance expectations

Conformance MUST cover at least:

- trace target correlation validity,
- trace identifier shape and parent/child constraints,
- SLA signal-type validity,
- reason-code registration/namespaced allowance,
- metering non-negative quantity and unit validity,
- SLA/metering correlation to transcript targets,
- correlation examples against M26 approval and M28 IAM step-up governed flows.

## 9. Security considerations

- Treat observability events as audit artifacts; preserve hash-chain integrity.
- Avoid embedding secrets in trace/metering references.
- Correlation references should point to stable protocol identifiers only.
- Validate reason codes to prevent opaque policy bypass tags.

## 10. Privacy considerations

- Do not emit raw tokens, credentials, or sensitive session secrets.
- Keep metering and SLA payloads minimal and role-appropriate.
- Prefer references/hashes over direct sensitive content.

## 11. Relationship to M26, M28, and future M29

- M26 (`EXT-HUMAN-APPROVAL`): observability can correlate approval challenge/grant-governed actions.
- M28 (`EXT-IAM-BRIDGE`): observability can correlate IAM step-up/claims-governed actions.
- M29 (enterprise bindings): may map domain-specific telemetry vocabularies onto this baseline, without changing core observability transcript semantics.

## 12. Registry entry

- `EXT-OBSERVABILITY` in `registry/extension_ids.json`.
- `OBS_SIGNAL` in `registry/message_types.json`.
