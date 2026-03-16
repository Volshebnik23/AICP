# RFC: EXT-EXTERNAL-TRANSACTION — protocol-neutral external irreversible-step transcript bridge (Registered Extension)

**Status:** Shipped M40 extension surface (with executable conformance coverage in this repository).

EXT-EXTERNAL-TRANSACTION defines how AICP transcripts declare and record externally executed irreversible steps without turning AICP into a commerce/payment protocol.

## 1. Purpose and scope (normative)

This extension standardizes transcript-native artifacts for:

- declaring an external transaction step intent,
- recording an external step result,
- anchoring external receipt evidence by digest/reference,
- linking policy and approval evidence already represented by existing AICP extensions.

The extension is protocol-neutral and can be used for any external irreversible operation class.

## 2. Explicit non-goals (normative)

This extension does **not** define:

- payment rails or checkout APIs,
- order/cart lifecycle semantics,
- vendor-specific commerce protocol requirements,
- vault implementations for PII storage.

## 3. Message types (normative)

- `EXTERNAL_TX_DECLARE`
- `EXTERNAL_TX_RESULT`

Both messages MUST use the Core envelope.

## 4. Canonical objects (normative minimum)

### 4.1 `external_transaction`

`external_transaction` MUST include:

- `external_tx_id`
- `step_kind`
- `irreversible` (boolean)
- `provider_hint`
- `transaction_ref`

`external_transaction` MAY include:

- `policy_eval_ref`
- `approval_ref`
- `redaction_policy_ref`
- `pii_refs` (vault-neutral `pii_ref` handles)
- `policy_required` / `approval_required`
- `external_protocol_id` / `mapping_target`

### 4.2 `external_receipt_anchor`

`external_receipt_anchor` MUST include:

- `receipt_digest`
- `artifact_ref`

`external_receipt_anchor` MAY include:

- `digest_alg`
- `receipt_type`
- `contains_pii`
- bounded inline artifact object for deterministic fixture validation

Raw receipt body material MUST NOT be required in transcript payloads.

## 5. Linkage and ordering semantics (normative)

1. A `EXTERNAL_TX_RESULT` message MUST reference a prior `EXTERNAL_TX_DECLARE` message via `declared_message_hash`.
2. The `external_tx_id` in result payload MUST match the declaration transaction id.
3. A result without a matching prior declaration MUST fail conformance.

## 6. Irreversible-step gating semantics (normative)

For irreversible steps (`external_transaction.irreversible = true`):

- implementations MUST be able to require prior approval evidence,
- evidence linkage MUST be transcript-native and machine-checkable,
- if approval is required (`approval_required = true` or `approval_ref` present), `approval_ref` MUST resolve to a prior `APPROVAL_GRANT` message hash.

Missing or mismatched approval linkage MUST fail when required.

## 7. Policy linkage semantics (normative)

If policy is required (`policy_required = true` or `policy_eval_ref` present):

- `policy_eval_ref` MUST resolve to a prior `POLICY_EVAL_RESULT`, and
- linked decision evidence MUST be enforcement-appropriate (e.g., non-deny for pass vectors).

Missing or mismatched policy linkage MUST fail when required.

## 8. Receipt digest anchoring semantics (normative)

- Receipt evidence MUST be anchored by digest/reference (`receipt_digest`, `artifact_ref`).
- Conformance MUST verify digest structure.
- If inline artifact evidence is present in deterministic fixtures, conformance MUST recompute and verify digest consistency.
- Digest mismatch MUST fail.

## 9. Privacy boundary semantics (normative)

- Inline raw sensitive receipt fields MUST NOT be required.
- If sensitive receipt data exists, implementations SHOULD use `pii_refs` + redaction policy references.
- `pii_refs` MUST follow EXT-REDACTION `pii_ref` semantics.

## 10. Relationship to existing extensions (normative)

- **EXT-POLICY-EVAL:** supplies policy decision evidence linked by `policy_eval_ref`.
- **EXT-HUMAN-APPROVAL:** supplies approval grant evidence linked by `approval_ref`.
- **EXT-REDACTION:** supplies vault-neutral `pii_ref` structure and redaction-policy linkage semantics.

This extension MUST reuse those surfaces and MUST NOT introduce parallel policy/approval/redaction engines.

## 11. Security considerations

- Enforcers should validate declaration/result linkage before allowing irreversible-step progression.
- Verify digest integrity to prevent receipt substitution.
- Treat mismatched `external_tx_id`, policy links, or approval links as tampering/bypass attempts.
- Avoid embedding raw PII in result payloads; use references and policy-controlled dereference paths.

## 12. Conformance expectations

Suite: `conformance/extensions/ET_EXTERNAL_TRANSACTION_0.1.json`

Conformance enforces declaration linkage, irreversible approval gating, policy linkage, receipt digest integrity, privacy boundary checks, and `pii_ref` semantics.

## 13. Registry entries

- Extension ID: `EXT-EXTERNAL-TRANSACTION`
- Message types: `EXTERNAL_TX_DECLARE`, `EXTERNAL_TX_RESULT`

## Appendix A (informative, non-binding): ACP mapping note

ACP is a first mapping target for this extension.

Informative mapping sketch:

- ACP action kickoff/checkpoint semantics can map to `EXTERNAL_TX_DECLARE`.
- ACP completion/failure callback semantics can map to `EXTERNAL_TX_RESULT`.
- ACP receipt artifacts map to `external_receipt_anchor` digest/reference fields.

This appendix is non-normative and MUST NOT be interpreted as ACP-specific behavior in the extension core model.
