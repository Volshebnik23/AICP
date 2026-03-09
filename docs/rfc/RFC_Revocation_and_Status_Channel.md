# RFC: Revocation and Status Channel (M21 baseline)

## 1. Scope (normative)
This RFC defines a minimal, deterministic status/revocation baseline built on M20 trust anchors and issuer attestations.

The baseline standardizes:
- `status_query` (hashable query object), and
- `status_assertion` (hashable signed status object).

The baseline is offline-verifiable from in-repo artifacts and does not require network retrieval.

## 2. `status_query` object (normative)
A `status_query` object MUST be canonical-hashable and include:
- `query_id`
- `target_type`
- `target_ref` (exact bound target object reference)
- `status_as_of`

`target_ref` MUST include:
- `object_type`
- `object_id`
- `object_hash`

The suite baseline transports `status_query_hash = object_hash("status_query", status_query)`.

## 3. `status_assertion` object (normative)
A `status_assertion` object MUST be canonical-hashable and include:
- `status_id`
- `query_id`
- `target_type`
- `target_ref`
- `status`
- `status_as_of`
- `issued_at`
- `expires_at`
- `issuer_id`
- `anchor_list_id`
- `max_age_seconds`

If `status == "REVOKED"`, `revoked_at` and `revocation_reason` MUST be present.

`status` values MUST come from `registry/status_assertion_codes.json`.
`revocation_reason` values MUST come from `registry/revocation_reason_codes.json` when present.

The suite baseline transports `status_assertion_hash = object_hash("status_assertion", status_assertion)`.

Assertions MUST carry `status_signature` with:
- `signer`
- `kid`
- `object_type` (MUST be `status_assertion`)
- `object_hash` (MUST equal `status_assertion_hash`)
- `sig_b64url`

## 4. Baseline verification model (normative)
Verifier checks:
1. Query/assertion object integrity hashes.
2. Query/assertion target binding consistency (`target_type`, `target_ref`, `query_id`, `status_as_of`).
3. Signature binding (`status_signature.object_hash == status_assertion_hash`).
4. Trust-chain validity under M20 anchor list (issuer/signer/kid + key verification).
5. Temporal validity:
   - anchor list validity covers status assertion validity,
   - `issued_at < expires_at`,
   - `status_as_of` within assertion validity window,
   - cache freshness: `observed_at <= issued_at + max_age_seconds`.
6. Revocation semantics:
   - `REVOKED` MUST satisfy `revoked_at <= status_as_of`.
   - `GOOD` MUST NOT carry `revoked_at`.

If checks pass, implementer can machine-check:
- “target is GOOD as of T”, or
- “target is REVOKED as of T”,
under a trust anchor set.

## 5. Deferred topics
Deferred beyond this baseline:
- network retrieval protocols,
- federation/gossip distribution,
- dynamic online freshness channels,
- governance/policy frameworks.

## 6. Registry bindings
- `registry/status_assertion_codes.json`
- `registry/revocation_reason_codes.json`
