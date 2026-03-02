# RFC: BIND-HTTP-0.1 — HTTP(S)/WebSocket transport binding

## Overview
`BIND-HTTP-0.1` defines interoperable HTTP(S)/WSS transport semantics for carrying AICP envelopes without altering Core message/hash/signature behavior.

## Normative behavior
- Transport endpoints MUST preserve envelope bytes as valid JSON objects and MUST NOT rewrite AICP message fields.
- Minimum endpoint set:
  - `POST /aicp/v1/sessions/{session_id}/ack` (cursor acknowledgement when explicit ACK is negotiated)
  - `POST /aicp/v1/sessions/{session_id}/messages` (ingest envelope)
  - `GET /aicp/v1/sessions/{session_id}/messages?after={cursor}&limit=N` (replication/polling)
  - `GET /aicp/v1/sessions/{session_id}/head` (state/head snapshot)
- Idempotency: receivers MUST treat `message_id` as the idempotency key for POST ingestion.
- Ordering/replay behavior MUST be documented by implementations and enforced consistently with negotiated Channel Properties when present.
- If WSS streaming is provided, stream framing MUST preserve transcript ordering guarantees declared for the session.

Channel Properties integration (experimental):
- Negotiated `selected.channel_properties` from EXT-CAPNEG SHOULD drive per-session transport behavior (for example ordering, ack semantics, replay window).
- Binding implementations MUST reject unsupported negotiated Channel Property selections before accepting traffic for a session.

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

- Cursor expiry semantics: poll requests beyond replay window MUST return `410` with `{ "reason_code": "cursor_expired", "min_cursor": "..." }`.

- When `CP-ORDERING-0.1 == "ordered"`, delivered embedded messages MUST be in contiguous hash-chain order (`next.prev_msg_hash == prev.message_hash`).
