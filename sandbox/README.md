# Sandbox debug thread workflow

Use this folder to quickly debug arbitrary AICP JSONL transcripts.

## Usage

1. Drop your transcript JSONL in `sandbox/` (or pass any path).
2. Run:

```bash
python sandbox/run.py sandbox/thread.jsonl
```

## What it checks

- JSONL parse errors
- Core message schema validation (when `jsonschema` is installed)
- `message_hash` recomputation
- `prev_msg_hash` chain verification
- optional signature verification (when signatures exist and crypto dependency is available)

Output is a concise, human-friendly failure summary with line numbers.
