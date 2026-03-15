# RFC_EXT_TRANSCRIPT_WITNESS (EXT-TRANSCRIPT-WITNESS)

## 1. Summary

`EXT-TRANSCRIPT-WITNESS` defines transcript-native anti-equivocation evidence for checkpointing, witness receipts, cross-domain head exchange, and inclusion proofs.

The extension is optional and transport-independent. It standardizes portable witness artifacts; it does **not** standardize a hosted witness service.

## 2. Scope boundaries (normative)

This extension is:
- content-layer,
- transport-agnostic,
- optional by profile/deployment,
- verifiable from transcript evidence.

This extension is **not**:
- a hosted witness network,
- a mandatory public transparency log,
- a transport-layer gossip protocol,
- a replacement for core local hash-chain validation.

## 3. Message types (normative) {#message-types-normative}

- `WITNESS_SUBMIT`
- `WITNESS_RECEIPT`
- `HEAD_EXCHANGE`
- `INCLUSION_PROOF_DECLARE`

## 4. Witness objects (normative)

### 4.1 Checkpoint commitment
Checkpoint commitment MUST bind at least:
- `checkpoint_id`
- `session_id`
- `head_hash`
- `issued_at`

Checkpoint commitment SHOULD include:
- `sequence_no` (monotonic per session),
- optional signer/witness metadata,
- optional `original_sender_sig_ref` when non-repudiation strengthening is enabled.

### 4.2 Witness receipt
Witness receipt MUST include:
- `receipt_id`
- `checkpoint_id`
- deterministic binding to prior submit (`submit_message_hash`)
- `witness_id`
- `issued_at`

### 4.3 Head exchange object
Head exchange MUST include:
- `session_id`
- `head_hash`
- `as_of`

Optional metadata MAY include source/witness references.

### 4.4 Inclusion proof object
Inclusion proof MUST include:
- `proof_id`
- `checkpoint_id`
- `target_message_hash`
- `root_hash`

Proof format is transport-neutral and may use abstract proof references, but linkage MUST be deterministic and hash-bound.

## 5. Message semantics (normative)

### 5.1 WITNESS_SUBMIT
`WITNESS_SUBMIT.payload.checkpoint` MUST contain a valid checkpoint commitment.
`checkpoint.session_id` MUST match transcript session context.
`checkpoint.head_hash` MUST reference a known transcript message hash.

### 5.2 WITNESS_RECEIPT
`WITNESS_RECEIPT.payload.receipt.submit_message_hash` MUST reference a prior `WITNESS_SUBMIT` message hash.
Receipt checkpoint binding MUST match the submitted checkpoint.

### 5.3 HEAD_EXCHANGE
`HEAD_EXCHANGE.payload.head.head_hash` MUST reference a known message hash for `head.session_id` in current transcript context.

### 5.4 INCLUSION_PROOF_DECLARE
`INCLUSION_PROOF_DECLARE.payload.proof.target_message_hash` MUST reference a known prior message hash.
`proof.checkpoint_id` MUST reference a known checkpoint context.

## 6. Equivocation and non-repudiation semantics

### 6.1 Equivocation detection (normative)
Conflicting checkpoint heads for the same `session_id` and `sequence_no` MUST fail conformance when strict witness mode is required.

### 6.2 Optional non-repudiation strengthening (optional profile behavior)
Deployments MAY require checkpoint commitments to include sender-signed origin references (for example `original_sender_sig_ref`) for critical events.
When enabled by policy/profile, missing origin-signature references MUST fail conformance.

## 7. Conformance expectations (normative)

Conformance suite MUST include:
- pass submit/receipt flow,
- pass head exchange + inclusion proof flow,
- expected-fail receipt without prior submit,
- expected-fail inclusion proof for unknown target,
- expected-fail split-history equivocation when strict witness mode applies.

## 8. Security considerations

- Witness artifacts should be authenticated and signature-verified by deployment policy.
- Checkpoints and receipts should be replay-resistant via IDs, timestamps, and hash-bound references.
- Equivocation checks should be enabled for high-value sessions and critical events.

## 9. Privacy considerations

- Checkpoints and head exchange should avoid leaking unnecessary payload content.
- Use hash references and policy-scoped metadata rather than raw sensitive content.

## 10. Registry entry {#registry-entry}

`EXT-TRANSCRIPT-WITNESS` in `registry/extension_ids.json`.
