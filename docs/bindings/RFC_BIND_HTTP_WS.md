# RFC: BIND-HTTP-0.1 — HTTP(S)/WebSocket transport binding

## Overview
`BIND-HTTP-0.1` defines interoperable HTTP(S)/WSS transport semantics for carrying AICP envelopes without altering Core message/hash/signature behavior.

## Normative behavior
- Transport endpoints MUST preserve envelope bytes as valid JSON objects and MUST NOT rewrite AICP message fields.
- Minimum endpoint set:
  - `POST /aicp/v1/sessions/{session_id}/messages` (ingest envelope)
  - `GET /aicp/v1/sessions/{session_id}/messages?after={cursor}&limit=N` (replication/polling)
  - `GET /aicp/v1/sessions/{session_id}/head` (state/head snapshot)
  - `POST /aicp/v1/sessions/{session_id}/ack` (cursor acknowledgement)
- Idempotency: receivers MUST treat `message_id` as the idempotency key for POST ingestion.
- Ordering/replay behavior MUST be documented by implementations and enforced consistently with negotiated Channel Properties when present.
- If WSS streaming is provided, stream framing MUST preserve transcript ordering guarantees declared for the session.

### Channel Properties integration
- Negotiated `selected.channel_properties` from EXT-CAPNEG SHOULD drive per-session transport behavior.
- Binding implementations MUST reject unsupported negotiated Channel Property selections before accepting traffic for a session.
- If `CP-ACK-0.1` is negotiated as `"explicit"`, receivers MUST expose `POST /aicp/v1/sessions/{session_id}/ack` and clients MUST acknowledge delivered cursors via request body `{ "cursor": "..." }`.
- If `CP-REPLAY-WINDOW-0.1` is negotiated, polling cursors older than retained window MUST fail with HTTP `410` and body `{ "reason_code": "cursor_expired", "min_cursor": "..." }`.
- If `CP-ORDERING-0.1` is negotiated as `"ordered"`, delivered messages MUST be emitted in contiguous hash-chain order (for adjacent messages `next.prev_msg_hash == prev.message_hash`).

### Minimal WS framing
When WSS streaming is used, outbound frames MUST use one of the following minimal envelope shapes:
- Messages frame:
  - `{ "type": "messages", "messages": [ ...AICP messages... ], "next_cursor": "..." }`
- Overload frame:
  - `{ "type": "overload", "retry_after": "..." }`

## Registry entry {#registry-entry}
- Binding ID: `BIND-HTTP-0.1`
- Registry: `registry/transport_bindings.json`
- Status: experimental

## Security considerations
- Endpoints MUST require authenticated/authorized access and SHOULD apply anti-replay protections at ingress.
- Idempotency keys and replay windows SHOULD be bounded to prevent resource exhaustion.
- Backpressure and overload responses MUST fail closed (no silent message drops without explicit status).

## Deprecated alias notes
- Deprecated alias: `EXT-BIND-HTTP`.
- Implementations MAY accept deprecated alias values for backward compatibility in declarations.
- Deprecated aliases MUST NOT be emitted as canonical negotiated values; canonical selection MUST use `BIND-HTTP-0.1`.
