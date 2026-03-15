# RFC_EXT_PUBLICATIONS (EXT-PUBLICATIONS)

## 1. Summary

`EXT-PUBLICATIONS` is the canonical M38 content distribution surface (feed semantics).
This RFC uses **PUBLICATIONS** as canonical naming; roadmap/backlog references to "feeds" are treated as conceptual aliases, not a separate extension ID.

## 2. Message types (normative) {#message-types-normative}

- `PUBLICATION_PUBLISH`
- `PUBLICATION_UPDATE`
- `PUBLICATION_RETRACT`

## 3. Normative lifecycle semantics

### 3.1 PUBLICATION_PUBLISH
`payload` MUST include:
- `publication_id`
- `version_id`
- `content_hash`
- `ttl_seconds`

### 3.2 PUBLICATION_UPDATE
`payload` MUST include:
- `publication_id`
- `version_id`
- `prior_version_id`
- `content_hash`
- `ttl_seconds`

`PUBLICATION_UPDATE.publication_id` MUST reference a previously published publication.
`prior_version_id` MUST match the current known version.
`version_id` MUST progress beyond `prior_version_id`.

### 3.3 PUBLICATION_RETRACT
`payload` MUST include:
- `publication_id`
- `version_id`
- `prior_version_id`
- `content_hash`
- `ttl_seconds`
- `reason_code`

`reason_code` MUST be a registered policy reason code or a namespaced vendor/org identifier.

## 4. Delivery policy hooks (normative)

If policy marks publication delivery as must-reach (e.g., via contract extension policy), publish/update/retract payloads MUST include machine-checkable `delivery_proof_ref` evidence.

## 5. Conformance expectations (normative)

Conformance suites for `EXT-PUBLICATIONS` MUST include:
- pass publish/update/retract flow with policy-aware delivery evidence,
- expected-fail update without valid prior chain,
- expected-fail update without version progression,
- expected-fail retract with invalid reason code,
- expected-fail must-reach publication without delivery proof.

## 6. Security considerations

- Publication integrity is hash-bound (`content_hash`) and should be signature-protected by policy.
- Delivery policy claims should be auditable and replay-resistant.

## 7. Registry entry {#registry-entry}

`EXT-PUBLICATIONS` in `registry/extension_ids.json`.
