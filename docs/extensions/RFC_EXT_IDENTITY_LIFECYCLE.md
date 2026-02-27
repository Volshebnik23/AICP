14. RFC: EXT-IDENTITY-LC — Identity lifecycle (Registered Extension)
EXT-IDENTITY-LC standardizes identity lifecycle events so long-lived or cross-platform sessions remain verifiable even when keys rotate or agents migrate. It introduces an Agent Identity Document (AID) as a canonical, hashable object and defines rotation/revocation semantics that third-party enforcers can verify.
14.1 Agent Identity Document (AID) (normative)
AID MUST be a canonical object (subject to AICP-JCS-1) that includes at minimum: agent_id (MUST), issuer (SHOULD), issued_at (MUST), expires_at (SHOULD), keys[] (MUST).
Each keys[] entry MUST include: kid (MUST), alg (MUST), public_key_b64url (MUST), status (MUST: active|retiring|revoked), not_before (MAY), not_after (MAY).
AID MAY include: provider metadata (name/version), revocation endpoints, external attestation refs, and constraints (e.g., allowed transports).
14.2 Message types (normative)
•	IDENTITY_ANNOUNCE — announce or update an AID reference for a session.
•	KEY_ROTATION — introduce a new key and retire an old key with cross-signing.
•	KEY_REVOKE — revoke a kid/key set by a revocation authority per policy.
•	AGENT_MIGRATION — record runtime/model/environment migration with updated AID and optional attestations.
14.3 Payloads (normative minimum)
IDENTITY_ANNOUNCE payload MUST include: aid_hash (MUST), aid_ref (MAY), supersedes_aid_hash (MAY), reason (MAY).
KEY_ROTATION payload MUST include: rotation_id (MUST), old_kid (MUST), new_key (MUST: kid+public_key+alg), effective_at (MAY), cross_signatures (MUST) where: (a) old key signs the new key material; and (b) new key signs the old key identifier.
KEY_REVOKE payload MUST include: revocation_id (MUST), target_kid or target_aid_hash (MUST), reason_code (SHOULD, registered), effective_at (MUST), issuer_attestation_ref (MAY).
AGENT_MIGRATION payload MUST include: migration_id (MUST), from_agent_version/from_environment (SHOULD), to_agent_version/to_environment (SHOULD), aid_hash (MUST), external_attestations (MAY).
14.4 Validation rules (normative)
•	KEY_ROTATION without valid cross_signatures MUST be rejected.
•	Once a KEY_REVOKE is known, messages signed by the revoked kid MUST be rejected for contract-changing operations; local policy MAY allow limited read-only audit parsing.
•	If AID is expired and no newer AID is available, implementations SHOULD enter a safe degraded mode (freeze side effects) or close per policy.
14.5 Conformance suite (IL-*) (normative minimum)
•	IL-01: IDENTITY_ANNOUNCE + valid AID -> resolver loads active keys; signatures verify.
•	IL-02: KEY_ROTATION cross-signing verified; old key transitions to retiring; new key becomes active.
•	IL-03: KEY_REVOKE -> subsequent messages by revoked key rejected.
