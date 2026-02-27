# Registry Rules

Registries are authoritative and must remain collision-free.

## Registry artifacts

Machine-readable registries live in this directory:
- `message_types.json`
- `policy_categories.json`
- `crypto_profiles.json`
- `canonicalization_profiles.json`
- `hash_domains.json`
- `transport_bindings.json`
- `policy_reason_codes.json`
- `extension_ids.json`
- `security_alert_categories.json`
- `dispute_claim_types.json`

Validate registry integrity with:
- `make validate` (includes `scripts/validate_registry.py`)

## Edit policy

1. Additions must use unique IDs and avoid collisions with existing entries.
2. Each registry change should include rationale in PR context.
3. If compatibility behavior changes, include migration notes.
4. Keep entries machine-readable and deterministic for external validation.

Do not introduce untracked identifiers outside `registry/`.
