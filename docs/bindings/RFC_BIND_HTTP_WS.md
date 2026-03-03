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
- Server-side idempotency is semantic: receivers MUST deduplicate by `message_id`.
- Clients MUST send `Idempotency-Key` header on POST ingestion.
- `Idempotency-Key` MUST be deterministically derived from `message_id`: either exactly equal to `message_id`, or namespaced with a terminal segment ending in `message_id` where preceding delimiter is one of `-`, `:`, or `/`.
- On replay, servers SHOULD respond idempotently (no duplicate acceptance) and MAY signal replay using header `AICP-Replay: true`.
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
- Stream push messages frame (legacy stream shape):
  - `{ "type": "messages", "messages": [ ...AICP messages... ], "next_cursor": "..." }`
- Pull/chunk messages frame (`wsPullMessages`):
  - `{ "type": "messages", "messages": [ ...AICP messages... ], "cursor_after_last": "...", "more": <bool> }`
- Overload frame:
  - `{ "type": "overload", "retry_after": "..." }`

### Rate limits and quotas
- On quota exhaustion, servers SHOULD respond with HTTP `429` (preferred) and MUST include `Retry-After`.
- Servers SHOULD include at least one rate-limit hint header: `RateLimit-Limit`, `RateLimit-Remaining`, or `RateLimit-Reset`.
- For WS/SSE overload signaling, overload objects/events SHOULD include `retry_after` string.

### Minimal SSE framing (pull-based backpressure)
When SSE streaming is supported, implementations SHOULD expose:
- `GET /aicp/v1/sessions/{session_id}/messages/stream?after={cursor}&limit=N`

Client backpressure is expressed by choosing `limit=N` and reconnecting with a later `after` cursor.

Response requirements:
- HTTP `200`
- `Content-Type: text/event-stream`

Server events:
- `messages` event
  - `event: messages`
  - `id: <cursor_after_last>`
  - `data: { "messages": [ ...AICP messages... ], "cursor_after_last": "...", "more": <bool> }`
- `overload` event
  - `event: overload`
  - `data: { "retry_after": "..." }`

Rules:
- For pull streams, server MAY chunk into multiple `messages` events.
- All non-final `messages` events MUST set `more=true`; the final `messages` event MUST set `more=false`.
- Total delivered messages across the stream MUST be `<= limit`.
- Clients MAY reconnect by sending `Last-Event-ID: <cursor>`; servers MUST treat it equivalently to `after=<cursor>`. If both are present, they MUST match.
- When `CP-ORDERING-0.1 == "ordered"`, delivered messages MUST preserve contiguous hash-chain order.

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
