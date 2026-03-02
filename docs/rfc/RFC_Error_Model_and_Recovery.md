9. RFC: Error model and recovery
The error model makes integrations predictable. A protocol ERROR does not change contract state; it reports a failure to validate or apply a message, using machine-readable codes and recovery hints.
Implementation-oriented operational summary: [docs/ops/ERROR_AND_RECOVERY.md](../ops/ERROR_AND_RECOVERY.md).
9.1 Principles (normative)
•	Errors MUST NOT change the contract state; they describe refusal or inability to apply a message.
•	Receivers MUST be idempotent by message_id.
•	ERROR payload MUST be safe to log (no secrets/PII unless policy explicitly allows).
•	Implementations MAY rate-limit ERROR replies to mitigate abuse, but SHOULD log locally for audit.
9.2 ERROR message (Core v0.1, SHOULD)
Core defines message_type=ERROR. Implementations SHOULD support generating and receiving ERROR; if a party declares ERROR support, it MUST follow this section.
ERROR payload fields (normative):
Field	Level	Meaning
error_code	MUST	Error code from Section 9.3 or registered extension.
error_class	MUST	VALIDATION | CRYPTO | STATE | POLICY | RATE | INTERNAL.
severity	MUST	low | medium | high | critical.
applies_to	MUST	Reference to message_id and/or object_hash.
disposition	MUST	IGNORED | BUFFERED | REJECTED.
recover_action	SHOULD	Recommended recovery action (Section 9.4).
retry_after_ms	MAY	Suggested delay for retry.
details	MAY	Human-readable explanation (no secrets/PII).
evidence_refs	MAY	References to hashes/logs/artifacts, if safe.
Schema note: Core payload schema models evidence_refs as an array of non-empty string references (deterministic and implementation-neutral).
9.3 Core v0.1 error codes (minimum)
•	VALIDATION:
•	INVALID_ENVELOPE
•	UNKNOWN_MESSAGE_TYPE
•	DUPLICATE_MESSAGE_ID
•	INVALID_CONTRACT_REF
•	INVALID_PAYLOAD
•	CRYPTO:
•	SIGNATURE_REQUIRED
•	UNKNOWN_KEY
•	INVALID_SIGNATURE
•	HASH_MISMATCH
•	STATE:
•	SESSION_NOT_FOUND
•	SESSION_CLOSED
•	UNKNOWN_BASE_REF
•	INVALID_STATE_TRANSITION
•	CONFLICT_ACTIVE
•	QUORUM_NOT_MET
•	POLICY:
•	CONSENT_REQUIRED
•	AUTHORITY_MISSING
•	SCOPE_VIOLATION
•	TOOL_ACCESS_DENIED
•	PII_POLICY_BLOCKED
•	RATE:
•	RATE_LIMITED
•	DEADLINE_EXCEEDED
9.4 Recovery actions (recover_action)
•	RETRY_LATER: Retry later; use retry_after_ms if provided.
•	RESEND_MESSAGE: Resend the original message (transport loss).
•	FETCH_OBJECT: Retrieve a missing object/base_version (recommended: EXT-OBJECT-RESYNC).
•	SYNC_STATE: Resynchronize session head/state (recommended: EXT-OBJECT-RESYNC).
•	REQUEST_CONSENT: Prompt the human user for required consent and attach consent artifacts.
•	ROTATE_KEY: Rotate identity key and provide linkage proof (EXT-IDENTITY-LC).
•	CLOSE_SESSION: Close the session if recovery is unsafe or impossible.
9.5 Typical cases (normative)
UNKNOWN_BASE_REF: MUST NOT change state; SHOULD buffer if policy allows and request missing objects via FETCH_OBJECT.
INVALID_SIGNATURE: MUST reject and keep state unchanged; MAY emit SECURITY_ALERT via extension if attack is suspected.
SESSION_CLOSED: MUST reject any contract-changing messages.
