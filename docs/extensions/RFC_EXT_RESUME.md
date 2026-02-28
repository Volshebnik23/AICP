# RFC: EXT-RESUME — Session resumption and reconnect handshake (Registered Extension)

## 1. Purpose (normative)
EXT-RESUME defines a compact, interoperable reconnect handshake so participants can rejoin a session/thread without replaying full history.
It reduces onboarding cost and reconnect error risk in mediated environments.

This extension is protocol-only and does not require any hosted platform behavior.

## 2. Roles (normative)
- Any participant MAY emit `RESUME_REQUEST`.
- A mediator/host SHOULD emit `RESUME_RESPONSE` for each request it can process.
- An enforcer MAY emit operational alerts around resume flows, but enforcer participation is optional.

## 3. Binding context (normative)
Resume binding uses:
- `session_id` (string): logical channel/thread identifier.
- `contract_id` (string) and/or `contract_hash` (string): stable contract binding context.
- `last_seen_message_hash` (string): requester's last known message head.

## 4. Message types and payloads (normative)
- `RESUME_REQUEST` payload schema: `schemas/extensions/ext-resume-payloads.schema.json#/$defs/RESUME_REQUEST`.
- `RESUME_RESPONSE` payload schema: `schemas/extensions/ext-resume-payloads.schema.json#/$defs/RESUME_RESPONSE`.

`RESUME_RESPONSE.status` values:
- `OK`: requester is in sync with responder head.
- `NEEDS_RESYNC`: requester is behind; resync is needed.
- `UNKNOWN_SESSION`: responder does not recognize requested session.

## 5. Recommended actions (normative)
EXT-RESUME reuses EXT-ALERTS action taxonomy and MUST NOT define a new action registry.
`RESUME_RESPONSE.recommended_actions` entries MUST come from `registry/alert_recommended_actions.json`.

## 6. Interaction with EXT-OBJECT-RESYNC and EXT-ALERTS (normative)
When `RESUME_RESPONSE.status` is `NEEDS_RESYNC`, implementations SHOULD follow with object/state resync via EXT-OBJECT-RESYNC.
This state MAY be paired with an EXT-ALERTS `ALERT` message such as code `RESYNC_REQUIRED`.

## 7. Security and privacy notes (normative)
- Resume metadata should be minimal and avoid sensitive disclosure.
- `details` / `client_info` payload fields, when present, SHOULD contain safe operational metadata only.
- Resume responses should remain auditable via message hashes and transcript chain integrity.

Security note: repeated `NEEDS_RESYNC` loops are an operational/security risk; conformance check `RS-LOOP-01` in `conformance/extensions/RS_RESUME_0.1.json` provides deterministic transcript-based detection coverage.
