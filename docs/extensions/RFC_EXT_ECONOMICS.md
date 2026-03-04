# RFC: EXT-ECONOMICS (experimental)

## Purpose
EXT-ECONOMICS defines token-agnostic billing primitives with transcript-verifiable proofs.

## Contract configuration (normative)
Implementations MUST read economics config from `payload.contract.ext.economics` or `payload.contract.extensions["EXT-ECONOMICS"]` with:
- `accepted_token_systems[]` (`token_system_id`,`issuer`,`unit`,`amount_type=INTEGER`)
- `pricing_model_ref` (artifact_ref or inline with content_hash)
- `scope` (`SESSION`/`CHANNEL`/`TOPIC`)
- `max_spend_default` integer

## Message types (normative) {#message-types-normative}
`PAID_MESSAGE_SUBMIT`, `ECONOMICS_VERDICT`, `PAYMENT_PROOF_SUBMIT`, `PAID_MESSAGE_DELIVER`.

## Normative invariants
- Platform MUST NOT emit `PAID_MESSAGE_DELIVER` unless a prior `ECONOMICS_VERDICT` is `ALLOW` for the same submit_id and a valid proof exists.
- Proof MUST include `expires_at`, `nonce`, `receipt_id`, `covers_submit_id`, `covers_content_hash`.
- `receipt_id` MUST be unique at least within SESSION scope.
- Selective-disclosure amount hiding MAY be supported.

## Security considerations
Replay, issuer spoofing, downgrade, spend metadata leakage, and coercion MUST be mitigated.

## Registry entry {#registry-entry}
- Extension ID: `EXT-ECONOMICS`
- Status: experimental
- Schema: `schemas/extensions/ext-economics-payloads.schema.json`
- Conformance: `conformance/extensions/EC_ECONOMICS_0.1.json`
