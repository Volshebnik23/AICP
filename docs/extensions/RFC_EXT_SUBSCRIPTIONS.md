# RFC_EXT_SUBSCRIPTIONS (EXT-SUBSCRIPTIONS)

## 1. Summary

`EXT-SUBSCRIPTIONS` defines transcript-native subscription state and delivery preference semantics for channel-based distribution.

## 2. Message types (normative) {#message-types-normative}

- `SUBSCRIBE`
- `UNSUBSCRIBE`
- `SUBSCRIPTION_STATE`

## 3. Normative payload semantics

### 3.1 SUBSCRIBE
`payload` MUST include:
- `subscription_id`
- `channel_id`
- `delivery_mode` (`realtime` | `digest` | `critical-only`)

`payload.filters` MAY carry subject/topic/severity/locale/tier preferences.

### 3.2 SUBSCRIPTION_STATE
`payload` MUST include:
- `subscription_id`
- `cursor`

`SUBSCRIPTION_STATE.subscription_id` MUST reference a prior `SUBSCRIBE`.
Cursor progression MUST be monotonic for each active subscription.

### 3.3 UNSUBSCRIBE
`payload` MUST include:
- `subscription_id`

`UNSUBSCRIBE.subscription_id` MUST reference a prior `SUBSCRIBE`.

## 4. Conformance expectations (normative)

Conformance suites for `EXT-SUBSCRIPTIONS` MUST include:
- pass subscribe/state/unsubscribe flow,
- expected-fail state linkage mismatch,
- expected-fail non-monotonic cursor progression.

## 5. Security considerations

- Subscription control messages should be authenticated by policy.
- Filters and cursors should avoid sensitive leakage while preserving resumability.

## 6. Registry entry {#registry-entry}

`EXT-SUBSCRIPTIONS` in `registry/extension_ids.json`.
