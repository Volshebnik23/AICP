# Registry Rules

Registries are authoritative and must remain collision-free.

## Edit policy

1. Additions must use unique IDs and avoid collisions with existing entries.
2. Each registry change should include rationale in PR context.
3. If compatibility behavior changes, include migration notes.
4. Keep entries machine-readable and deterministic for external validation.

Do not introduce untracked identifiers outside `registry/`.
