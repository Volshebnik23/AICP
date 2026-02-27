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

## Runner usage

```bash
python conformance/runner/aicp_conformance_runner.py \
  --suite conformance/core/CT_CORE_0.1.json \
  --out conformance/report.json
```

Exit code is `0` on pass and `1` on fail.
