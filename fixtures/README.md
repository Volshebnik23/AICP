# Fixtures Policy

Fixtures and golden transcripts are verification artifacts.

## Layout

- Core test vectors: `fixtures/core_tv.json`
- Golden transcripts: `fixtures/golden_transcripts/`
- Verification keys: `fixtures/keys/`

## Rules

- Do not hand-edit golden transcripts.
- Regenerate fixtures deterministically and document generation method.
- Keep fixture updates aligned with schema and conformance expectations.
- Treat fixtures as executable proof for interoperability checks.
