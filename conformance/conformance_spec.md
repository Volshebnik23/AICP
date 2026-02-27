# AICP Conformance (Core v0.1)

## Purpose

This directory defines a minimal, machine-runnable conformance product for AICP Core v0.1.

## Suite structure

- `core/CT_CORE_0.1.json` — suite catalog (inputs + expected checks).
- `runner/aicp_conformance_runner.py` — CLI runner.
- `conformance_report_schema.json` — output report schema.

## Pass criteria

A suite **passes** when all configured transcript checks pass:

1. Every JSONL record validates against `schemas/core/aicp-core-message.schema.json`.
2. `prev_msg_hash` equals prior `message_hash` when present.
3. `session_id` is constant and `message_id` values are unique per transcript.
4. `message_type` sequence matches the catalog expectation.
5. If `signatures[*].object_hash` is present, it equals `message_hash`.
6. `CT-MESSAGE-HASH-01`: `message_hash` recomputes from message body (without `signatures` and `message_hash`) using Core object-hash algorithm.
7. `CT-SIGNATURE-VERIFY-01`: when signatures are present, Ed25519 verification succeeds against `fixtures/keys/GT_public_keys.json`.

## Runner usage

```bash
python conformance/runner/aicp_conformance_runner.py \
  --suite conformance/core/CT_CORE_0.1.json \
  --out conformance/report.json
```

Exit code is `0` on pass and `1` on fail.

## Negative transcript handling

Suite catalogs may mark transcripts as expected-failure cases via `expect_pass: false` and `expected_failures`.
A negative transcript passes only when all expected failure test IDs occur at least `min_count` and no unexpected failures are present.
