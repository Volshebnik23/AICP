# AICP Core v0.1 (Normative) - Package

This package contains:
- Normative spec document (DOCX)
- JSON Schemas (Envelope, Contract, Payloads)
- Test vectors (TV-01..TV-03)
- Golden transcripts (JSONL) + public keys

## Quickstart

1) Validate message envelopes against `schemas/aicp-core-message.schema.json`.
2) Validate contract objects against `schemas/aicp-core-contract.schema.json`.
3) Verify `fixtures/core_tv.json` with the reference implementation.
4) Replay `fixtures/golden_transcripts/*.jsonl`:
   - recompute `message_hash` for each envelope excluding `signatures` and `message_hash`
   - check `prev_msg_hash` chaining
   - verify Ed25519 signatures over signing input:
     `AICP1\0SIG\0` + `<object_hash>` (UTF-8)

Reference implementation: see `aicp_reference_v0.1.0.zip` (separate artifact).
