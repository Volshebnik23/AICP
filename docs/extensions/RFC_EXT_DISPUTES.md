15. RFC: Applied extensions (workflow, delegation, disputes, security alerts)

15.3 EXT-DISPUTES — Challenges, breach claims, arbitration hooks (Registered Extension)
Purpose: interoperable dispute primitives to challenge suspected distortion, incorrect results, or improper execution of delegated obligations, and to optionally request arbitration.
### 15.3.1 Message types (normative)
•	CHALLENGE_ASSERTION — dispute an attestation/object/message with evidence and requested remedy.
•	CLAIM_BREACH — assert breach of delegation purpose, acceptance criteria, or contract obligation.
•	ARBITRATION_REQUEST (optional) — request arbitration by a designated arbitrator party or profile.
•	ARBITRATION_RESULT (optional) — publish arbitration outcome with signatures.

### 15.3.2 Payload shape (normative minimum)
CHALLENGE_ASSERTION payload (normative minimum): challenge_id (MUST), target_ref (MUST: object_hash or message_id), challenge_type (MUST, registered), claim (MUST), evidence_refs (MUST, non-empty), requested_remedy (MAY), deadline (MAY).
CLAIM_BREACH payload (normative minimum): claim_id (MUST), delegation_id or obligation_ref (MUST), breach_type (MUST, registered), narrative (SHOULD), evidence_refs (SHOULD), requested_remedy (MAY).
Conformance requires evidence_refs to be present and non-empty for interoperability and auditability.

### 15.3.3 CHALLENGE_ASSERTION

### 15.3.4 CLAIM_BREACH

### 15.3.5 ARBITRATION_REQUEST

### 15.3.6 ARBITRATION_RESULT

### 15.3.3 CHALLENGE_ASSERTION

### 15.3.4 CLAIM_BREACH

### 15.3.5 ARBITRATION_REQUEST

### 15.3.6 ARBITRATION_RESULT

15.5 Extension conformance (normative minimum)
•	AW-01: WORKFLOW_DECLARE + WORKFLOW_STEP_ATTEST validates head_version binding and evidence_refs hashing.
•	AD-01: DELEGATION_GRANT/ACCEPT/RESULT_ATTEST forms a verifiable chain of responsibility; max_depth enforced.
•	DS-01: CHALLENGE_ASSERTION references an existing attestation and is audit-verifiable via object_hash.
•	SA-01: SECURITY_ALERT includes evidence_refs and does not leak secrets/PII beyond policy.
