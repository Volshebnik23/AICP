11. RFC: Transport bindings (Registered Extensions)

11.3 EXT-BIND-HTTP — HTTP(S)/WebSocket binding (normative)
Model: an HTTP(S) service (or WSS gateway) accepts envelopes and provides polling for message replication. This binding does not define auth; deployments may use OAuth/JWT/mTLS, but MUST NOT alter envelopes.
Normative endpoints (minimum):
•	POST /aicp/v1/sessions/{session_id}/messages  (body: envelope) -> 202 Accepted or 4xx with optional ERROR
•	GET  /aicp/v1/sessions/{session_id}/messages?after={cursor}&limit=N -> {messages[], next_cursor}
•	GET  /aicp/v1/sessions/{session_id}/head -> {session_state, branch_heads, active_head_version?, final_head_version?}
•	GET  /aicp/v1/objects/{object_hash} (SHOULD) -> object or status (or redirect to artifact_ref)
Idempotency: servers MUST use message_id as an idempotency key; duplicate POST MUST NOT create duplicates and SHOULD return 200/202 with the same acceptance disposition.
