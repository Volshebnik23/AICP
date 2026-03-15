# RFC_EXT_CHANNELS (EXT-CHANNELS)

## 1. Summary

`EXT-CHANNELS` defines transcript-native channel topology for agent media/reception distribution.
Channels provide auditable hierarchy and policy metadata used by subscriptions, publications, and inbox routing.

## 2. Message types (normative) {#message-types-normative}

- `CHANNEL_DECLARE`
- `CHANNEL_UPDATE`
- `CHANNEL_DEPRECATE`

## 3. Normative payload semantics

### 3.1 CHANNEL_DECLARE
`payload` MUST include:
- `channel_id`
- `version_id`

`payload` SHOULD include channel metadata used by downstream policy:
- `parent_channel_id`
- `subject_tags`
- `topic_keys`
- `visibility_class`
- `retention_policy_ref`

If `parent_channel_id` is present, it MUST reference a previously declared channel in transcript context.

### 3.2 CHANNEL_UPDATE
`payload` MUST include:
- `channel_id`
- `version_id`

`CHANNEL_UPDATE.channel_id` MUST reference a previously declared channel.

### 3.3 CHANNEL_DEPRECATE
`payload` MUST include:
- `channel_id`
- `version_id`

`CHANNEL_DEPRECATE.channel_id` MUST reference a previously declared channel.

## 4. Hierarchy constraints (normative)

- Child channels MUST NOT escalate `visibility_class` beyond restrictive parent visibility.
- Parent linkage and visibility checks MUST be machine-checkable in conformance.

## 5. Conformance expectations (normative)

Conformance suites for `EXT-CHANNELS` MUST include:
- pass lifecycle `declare -> update -> deprecate`,
- expected-fail invalid parent linkage,
- expected-fail visibility misuse.

## 6. Security considerations

- Channel ownership/update rights should be authenticated by policy.
- Visibility metadata should be enforced consistently to prevent unauthorized broad distribution.

## 7. Registry entry {#registry-entry}

`EXT-CHANNELS` in `registry/extension_ids.json`.
