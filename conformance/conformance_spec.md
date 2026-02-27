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
8. `CT-PAYLOAD-SCHEMA-01` (when configured): mapped Core payloads validate against `schemas/core/aicp-core-payloads.schema.json`.

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


## Payload schema suites (Core + extensions)

Suites may specify `payload_schema_ref`, `payload_schema_map`, and optional `payload_schema_check_id` (default `CN-PAYLOAD-SCHEMA-01`). The runner validates payloads using a wrapper schema that preserves root `$defs` and references mapped payload definitions by JSON Pointer (`/$defs/X` or `#/$defs/X`). Core suites use `CT-PAYLOAD-SCHEMA-01`; extension suites typically use `CN-PAYLOAD-SCHEMA-01`.

For EXT-OBJECT-RESYNC, `OR-OBJECT-HASH-01` verifies any payload object tuple `{object_type, object, object_hash}` by recomputing `object_hash`.

For EXT-POLICY-EVAL, `PE-REASON-CODES-01` validates `policy_decision.reason_codes` against `registry/policy_reason_codes.json`, and `PE-CONTEXT-HASH-01` recomputes `evaluation_context.context_hash` using object_type `evaluation_context`.
