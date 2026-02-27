# Fixtures Policy

Fixtures and golden transcripts are verification artifacts.

## Rules

- Do not hand-edit golden transcripts.
- Regenerate fixtures deterministically and document generation method.
- Keep fixture updates aligned with schema and conformance expectations.
- Treat fixtures as executable proof for interoperability checks.


Generation note: GT-04..GT-08 were generated deterministically using `reference/python/aicp_ref/hashing.py` for `message_hash` recomputation and serialized as JSONL in canonical field order from Python dict insertion order used by generation scripts.

Extension note: CAPNEG fixtures (`fixtures/extensions/capneg/CN-01*`, `CN-02*`) are generated deterministically using `reference/python/aicp_ref/hashing.py` for message hash computation.
