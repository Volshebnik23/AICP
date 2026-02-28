# AICP TypeScript SDK (minimal Core helpers)

“An open content-layer protocol for agent-to-agent interaction with enforceable policies.”

This lightweight SDK is validator-focused. It provides:

- deterministic canonicalization (`src/jcs.ts`)
- object/message hashing (`src/hashing.ts`)
- base64url helpers (`src/base64url.ts`)
- `prev_msg_hash` chain verification (`src/chain.ts`)

## Install and test

```bash
cd sdk/typescript
npm ci
npm test
```

## Minimal valid Core envelope example

```ts
import { messageHashFromBody } from "./src/hashing.js";

const body = {
  session_id: "s1",
  message_id: "m1",
  timestamp: "t0001",
  sender: "agent:A",
  message_type: "CONTRACT_ACCEPT",
  contract_id: "c1",
  contract_ref: { branch_id: "main", base_version: "v1", head_version: "v1" },
  payload: { accepted: true },
};

const message = { ...body, message_hash: messageHashFromBody(body) };
console.log(message);
```

## Validation

From repo root, validate with:

```bash
make validate
python sandbox/run.py sandbox/thread.jsonl
```
