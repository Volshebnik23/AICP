13. RFC: EXT-OBJECT-RESYNC — Object retrieval and state resync (Registered Extension)
EXT-OBJECT-RESYNC provides a transport-independent recovery mechanism to fetch missing objects by object_hash and to resynchronize minimal session state. It is essential for real deployments with reordering, partial replication, offline operation, and third-party observation.
13.1 Message types (normative)
•	OBJECT_REQUEST — request one or more objects by object_hash.
•	OBJECT_RESPONSE — return objects or statuses for requested hashes.
•	STATE_SYNC_REQUEST — request minimal session state (heads, closed status, hints).
•	STATE_SYNC_RESPONSE — return minimal session state and replication hints.
13.2 OBJECT_REQUEST payload (normative minimum)
•	request_id (MUST): identifier for idempotency and correlation.
•	objects (MUST): list of {object_hash (MUST), want_type (MAY), max_bytes (MAY)}.
•	allow_redaction (SHOULD): whether REDACTED responses are acceptable.
•	allow_encrypted (MAY): whether encrypted objects are acceptable (binding/profile dependent).
•	max_total_bytes (MAY): receiver may cap response size.
13.3 OBJECT_RESPONSE payload (normative minimum)
OBJECT_RESPONSE MUST include request_id and entries[]. Each entry MUST include: object_hash, status, and (if status=FOUND) object_type and object_json (or artifact_ref).
status MUST be one of: FOUND | NOT_FOUND | ACCESS_DENIED | TOO_LARGE | REDACTED | ERROR.
If status=FOUND and object_json is provided, the receiver MUST ensure that re-hashing the object_json under the declared object_type yields object_hash.
13.4 STATE_SYNC_* payloads (normative minimum)
STATE_SYNC_REQUEST MUST include: request_id (MUST), known_heads (MAY), known_message_hash (MAY), want_closed_status (MAY).
STATE_SYNC_RESPONSE MUST include: request_id (MUST), session_state (MUST), branch_heads (MUST), active_head_version (MAY), final_head_version (MAY), replication_hints (MAY).
13.5 Security and privacy considerations (normative intent)
•	Implementations SHOULD mitigate DoS/amplification (rate limits, max bytes, chunking via artifact_ref, and TOO_LARGE responses).
•	Object existence leakage is a security concern; implementations MAY respond with ACCESS_DENIED instead of NOT_FOUND based on policy.
•	Redaction MUST be explicit (status=REDACTED) and SHOULD include redaction_note. Receivers MUST NOT silently alter objects.
13.6 Conformance suite (OR-*) (normative minimum)
•	OR-01: UNKNOWN_BASE_REF -> ERROR with recover_action=FETCH_OBJECT; OBJECT_REQUEST/RESPONSE resolves it.
•	OR-02: HASH_MISMATCH on FOUND object -> reject and raise CRYPTO error.
