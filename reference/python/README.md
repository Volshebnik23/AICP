# AICP Python Reference (Core v0.1, minimal)

“An open content-layer protocol for agent-to-agent interaction with enforceable policies.”

This reference implementation provides correctness-first helpers for:

- Deterministic canonicalization (`aicp_ref/jcs.py`)
- Core object/message hashing (`aicp_ref/hashing.py`)
- Ed25519 signature verification (`aicp_ref/signatures.py`)
- Transcript hash-chain checks (`aicp_ref/chain.py`)
- End-to-end transcript validation helpers (`aicp_ref/validate.py`)

## Notes

This package is an implementer helper layer (minimal ergonomics, correctness-first checks),
not the protocol authority. Normative behavior is defined by Core docs + schemas + conformance suites.

Validation helpers in `aicp_ref/validate.py` enforce key Core invariants including:
- non-first transcript messages requiring `prev_msg_hash`,
- signature `object_hash` matching the enclosing `message_hash`,
- consistent signer/`kid` key selection when `kid` is present.

## Run tests

```bash
python -m pip install -r reference/python/requirements.txt
PYTHONPATH=reference/python pytest -q reference/python/tests
```
