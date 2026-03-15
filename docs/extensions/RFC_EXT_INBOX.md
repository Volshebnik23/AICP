# RFC_EXT_INBOX (EXT-INBOX)

## 1. Summary

`EXT-INBOX` defines transcript-native inbox queue routing/lease/ack semantics for reception delivery.
It is designed to interoperate with M35 admission and queue-lease controls.

## 2. Message types (normative) {#message-types-normative}

- `INBOX_ENQUEUE`
- `INBOX_ROUTE`
- `INBOX_LEASE_GRANT`
- `INBOX_ACK`

## 3. Normative semantics

### 3.1 INBOX_ENQUEUE
`payload` MUST include:
- `inbox_id`
- `item_id`

### 3.2 INBOX_ROUTE
`payload` MUST include:
- `item_id`
- `route_key`

`INBOX_ROUTE.item_id` MUST reference a prior enqueue.

### 3.3 INBOX_LEASE_GRANT
`payload` MUST include:
- `inbox_id`
- `lease_id`
- `ttl_seconds`

When policy requires queue/admission context, lease grants MUST include `queue_lease_ref` and `admission_ref`.

### 3.4 INBOX_ACK
`payload` MUST include:
- `inbox_id`
- `item_id`

`INBOX_ACK.item_id` MUST reference prior enqueue context.
If item delivery used a lease grant, `lease_id` SHOULD be present and MUST reference prior lease context when present.

## 4. Conformance expectations (normative)

Conformance suites for `EXT-INBOX` MUST include:
- pass enqueue/route/lease/ack flow,
- expected-fail ack without enqueue,
- expected-fail missing queue/admission context when policy requires it.

## 5. Security considerations

- Inbox routing and lease grants should be authenticated to prevent hijack/replay.
- Queue/admission references should be policy-verified for anti-abuse controls.

## 6. Registry entry {#registry-entry}

`EXT-INBOX` in `registry/extension_ids.json`.
