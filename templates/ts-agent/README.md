# TS Agent Template (copy-paste)

Minimal skeleton for agent developers who need to emit AICP-compatible message envelopes quickly.

## What it demonstrates

- constructing Core message envelopes
- computing `message_hash` via the repo's canonical helper (`sdk/typescript/src/hashing.js`)
- maintaining `prev_msg_hash` chain across messages
- producing deterministic JSONL output for local verification

## Run

```bash
node templates/ts-agent/agent.js > out/template-ts-agent/thread.jsonl
python sandbox/run.py out/template-ts-agent/thread.jsonl --no-signature-verify
```

This template emits **two** JSONL records (`CONTRACT_PROPOSE`, then `CONTRACT_ACCEPT`) with ISO-8601 demo timestamps.
When copying this template outside this repo, replace the helper import with your local copy of
`dropins/aicp-core/typescript/` or `sdk/typescript/src/` so hashing stays aligned with conformance.
