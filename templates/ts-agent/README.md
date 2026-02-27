# TS Agent Template (copy-paste)

Minimal skeleton for agent developers who need to emit AICP-compatible message envelopes quickly.

## What it demonstrates

- constructing message envelopes
- computing `message_hash`
- maintaining `prev_msg_hash` chain
- where enforcement hooks should run

## Run

```bash
node templates/ts-agent/agent.js
```

This prints a two-message JSONL-compatible thread you can drop into `sandbox/thread.jsonl` for local debugging.
