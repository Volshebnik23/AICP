# RFC: Trust Anchors and Issuer Attestations (M20 baseline)

## 1. Scope (normative)
This RFC defines a **minimal, offline-verifiable baseline** for trust anchors and issuer attestations.

The baseline standardizes two hashable objects:
- `trust_anchor_list`
- `issuer_attestation`

The baseline is intentionally narrow:
- It supports deterministic verification from in-repo artifacts only.
- It does **not** define online status/revocation protocols (deferred to M21).

## 2. `trust_anchor_list` object (normative)
A `trust_anchor_list` object MUST be canonical-hashable and contain:
- `anchor_list_id` (string, stable identifier)
- `version` (string)
- `issued_at` (date-time)
- `expires_at` (date-time)
- `anchors` (non-empty array)

Each `anchors[]` entry MUST include:
- `issuer_id` (string; issuer namespace/identity)
- `signer` (string; signer identity expected on issuer attestations)
- `kid` (string; key id)
- `public_key_b64url` (string; Ed25519 public key, base64url)

The suite baseline uses object hash domain `trust_anchor_list` and transports the hash as `trust_anchor_list_hash`.

## 3. `issuer_attestation` object (normative)
An `issuer_attestation` object MUST be canonical-hashable and contain:
- `attestation_id` (string)
- `issuer_id` (string)
- `subject_id` (string)
- `attestation_type` (registered id from `registry/attestation_types.json`)
- `trust_signal` (registered id from `registry/trust_signal_types.json`)
- `issued_at` (date-time)
- `expires_at` (date-time)
- `anchor_list_id` (string; links to trust anchor list)

The suite baseline uses object hash domain `issuer_attestation` and transports the hash as `issuer_attestation_hash`.

Attestations MUST carry `attestation_signature` with:
- `signer`
- `kid`
- `object_type` (MUST be `issuer_attestation`)
- `object_hash` (MUST equal `issuer_attestation_hash`)
- `sig_b64url`

## 4. Baseline verification model (normative)
Given anchor set **A** (`trust_anchor_list`) and attestation **Y** (`issuer_attestation`), verifier MUST check:

1. **Anchor object integrity**
   - `trust_anchor_list_hash == object_hash("trust_anchor_list", trust_anchor_list)`.
2. **Attestation object integrity**
   - `issuer_attestation_hash == object_hash("issuer_attestation", issuer_attestation)`.
3. **Registry validity**
   - `attestation_type` is registered in `registry/attestation_types.json`.
   - `trust_signal` is registered in `registry/trust_signal_types.json`.
4. **Signature validity**
   - `attestation_signature.object_hash == issuer_attestation_hash`.
   - signature verifies under the anchor key identified by signer/kid.
5. **Trust-chain linkage**
   - `issuer_attestation.anchor_list_id == trust_anchor_list.anchor_list_id`.
   - signer/kid is present in `trust_anchor_list.anchors[]` for attestation `issuer_id`.
6. **Temporal validity**
   - anchor list and attestation timestamps are valid date-time values.
   - attestation validity window MUST be bounded by anchor list validity window.

If all checks pass, implementer can machine-check:
- “issuer X is trusted under anchor set A” and
- “issuer attestation Y is valid under anchor set A”.

## 5. Deferred topics (non-goals of this baseline)
Deferred to later milestones (especially M21):
- revocation/status channel semantics,
- online freshness/status lookups,
- governance/distribution policy for anchor publication.

## 6. Registry bindings
- `registry/trust_signal_types.json`
- `registry/attestation_types.json`
