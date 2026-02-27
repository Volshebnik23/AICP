15. RFC: Applied extensions (workflow, delegation, disputes, security alerts)

15.2 EXT-DELEGATION — Hierarchical purpose-oriented delegation (Registered Extension)
Purpose: allow a delegator to formally grant a subset of authority to a delegatee for a specific purpose, with hierarchical delegation limits, and with verifiable result control retained by the delegator.
Message types:
•	DELEGATION_GRANT — grant authority subset with scope, purpose, acceptance criteria, expiry, and max_depth.
•	DELEGATION_ACCEPT — accept the grant (delegatee commitment).
•	DELEGATION_REVOKE — revoke delegation (immediate or scheduled).
•	DELEGATION_RESULT_ATTEST — delegatee attests results bound to purpose and head_version.
DELEGATION_GRANT payload (normative minimum): delegation_id (MUST), delegator (MUST), delegatee (MUST), parent_delegation_id (MAY), authority_subset (MUST), scope (MUST), purpose (MUST), acceptance_criteria (SHOULD), expiry (MUST), max_depth (SHOULD, default=0), required_attestations (MAY).
Purpose-oriented control (normative): the delegator retains the right to accept/reject outcomes. A delegatee result MUST be attested via DELEGATION_RESULT_ATTEST and MAY be challenged or claimed as breach (Section 15.3).

15.5 Extension conformance (normative minimum)
•	AW-01: WORKFLOW_DECLARE + WORKFLOW_STEP_ATTEST validates head_version binding and evidence_refs hashing.
•	AD-01: DELEGATION_GRANT/ACCEPT/RESULT_ATTEST forms a verifiable chain of responsibility; max_depth enforced.
•	DS-01: CHALLENGE_ASSERTION references an existing attestation and is audit-verifiable via object_hash.
•	SA-01: SECURITY_ALERT includes evidence_refs and does not leak secrets/PII beyond policy.
