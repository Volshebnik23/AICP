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

## Usage (validator-only)

```ts
import { messageHashFromBody } from "./src/hashing.js";

const body = {
  session_id: "s1",
  message_id: "m1",
  message_type: "CAPABILITIES_DECLARE",
  payload: { supported_profiles: ["core.v0.1"] },
};

const hash = messageHashFromBody(body);
console.log(hash);
```
