# AICP Python Reference (Core v0.1, minimal)

This reference implementation provides correctness-first helpers for:

- Deterministic canonicalization (`aicp_ref/jcs.py`)
- Core object/message hashing (`aicp_ref/hashing.py`)
- Ed25519 signature verification (`aicp_ref/signatures.py`)
- Transcript hash-chain checks (`aicp_ref/chain.py`)
- End-to-end transcript validation helpers (`aicp_ref/validate.py`)

## Notes

Canonicalization currently matches existing fixtures using sorted-key JSON encoding.
Full RFC8785 numeric edge-case handling is intentionally out of scope and unsupported
float cases raise explicit exceptions.

## Run tests

```bash
python -m pip install -r reference/python/requirements.txt
PYTHONPATH=reference/python pytest -q reference/python/tests
```
