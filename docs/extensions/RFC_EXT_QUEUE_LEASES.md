# RFC_EXT_QUEUE_LEASES (EXT-QUEUE-LEASES)

Status: Experimental  
AICP Version: 0.1

## 1. Purpose

`EXT-QUEUE-LEASES` defines transcript-native queue admission/lease/backpressure artifacts so crowded sessions can bound interaction capacity and signal overload in portable machine-readable form.

## 2. Scope boundaries (normative)

This extension is **not**:
- a message broker runtime,
- a transport queue API,
- a scheduler implementation,
- an anti-abuse classifier.

This extension provides content-layer evidence for queue coordination.

## 3. Message types (normative)

- `QUEUE_ENQUEUE`
- `QUEUE_LEASE_GRANT`
- `QUEUE_ACK`
- `QUEUE_NACK`
- `QUEUE_RELEASE`
- `OVERLOAD_SIGNAL`
- `THROTTLE_UPDATE`

## 4. Queue and lease semantics (normative)

### 4.1 QUEUE_ENQUEUE
`payload` MUST include:
- `queue_id`
- `item_id`

### 4.2 QUEUE_LEASE_GRANT
`payload` MUST include:
- `lease_id`
- `queue_id`
- `ttl_seconds`
- `max_msgs`
- `max_tool_calls`

`payload` MAY include:
- `priority_class`
- `cursor`
- `allowed_message_types`

### 4.3 QUEUE_ACK / QUEUE_NACK
Both MUST include:
- `lease_id`
- `item_id`

`QUEUE_NACK` additionally MUST include:
- `reason_code`
- `retry_after_seconds`

### 4.4 QUEUE_RELEASE
`payload` MUST include:
- `lease_id`

Release closes active lease usage for that participant/context.

## 5. Overload/backpressure semantics (normative)

### 5.1 OVERLOAD_SIGNAL
`payload` MUST include:
- `severity`
- `reason_code`
- `retry_after_seconds`

`payload` MAY include:
- `degradation_mode`
- `allowed_message_types`

### 5.2 THROTTLE_UPDATE
`payload` MUST include:
- `max_msgs_per_minute`

`payload` MAY include:
- `max_tool_calls_per_minute`
- `applies_to_message_types`

## 6. Bounded interaction rules (normative)

When lease-required mode is enabled by contract extension policy, content-producing actions MUST remain within active lease bounds (`max_msgs`, `max_tool_calls`, and TTL window).

Exceeding bounds MUST be machine-detectable and MUST fail conformance.

## 7. Conformance expectations

Conformance MUST cover at least:
- lease grant validity and bound fields,
- bounded interaction compliance,
- overrun failure detection,
- explicit NACK retry/backoff semantics,
- overload signaling shape and severity semantics,
- release linkage to prior granted lease,
- at least one M27 observability-correlated lease flow.

## 8. Security considerations

- Lease IDs should be unpredictable enough to resist blind guessing in multi-tenant hosts.
- Overload/throttle messages should be authenticated to prevent adversarial backoff injection.
- Example: if a participant exceeds `max_msgs`, emit explicit NACK/overrun evidence rather than silently dropping traffic.

## 9. Privacy considerations

- Queue metadata should avoid embedding sensitive user/session identifiers when stable references suffice.
- Backpressure reason codes should be informative without exposing internal anti-abuse model details.

## 10. Relationship to adjacent milestones

- M27 (`EXT-OBSERVABILITY`): lease/overload events should correlate with operational telemetry.
- M26 (`EXT-HUMAN-APPROVAL`): strict queue classes may require approval for renewals/escalations.
- M20/M21 trust/status: queue admission can consume trust/status references, but trust semantics remain external.

## 11. Registry entry

- `EXT-QUEUE-LEASES` in `registry/extension_ids.json`.
