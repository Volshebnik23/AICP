15. RFC: Applied extensions (workflow, delegation, disputes, security alerts)

15.4 EXT-SECURITY-ALERT — Security events and escalation (Registered Extension)
Purpose: standardize security incident reporting for agent-to-agent interaction (e.g., suspected malicious result distortion, key substitution, replay/forgery attempts) with evidence binding.
### 15.4.1 Message types (normative)
•	SECURITY_ALERT — report a security event bound to session evidence.

### 15.4.2 Payload shape (normative minimum)
SECURITY_ALERT payload (normative minimum): alert_id (MUST), category (MUST, registered), severity (MUST: low|medium|high|critical), suspected_actor (MAY), suspected_attack (MAY), indicators (SHOULD), evidence_refs (SHOULD), recommended_action (MAY), disclosure_policy (MAY).

### 15.4.3 SECURITY_ALERT

15.5 Extension conformance (normative minimum)
•	AW-01: WORKFLOW_DECLARE + WORKFLOW_STEP_ATTEST validates head_version binding and evidence_refs hashing.
•	AD-01: DELEGATION_GRANT/ACCEPT/RESULT_ATTEST forms a verifiable chain of responsibility; max_depth enforced.
•	DS-01: CHALLENGE_ASSERTION references an existing attestation and is audit-verifiable via object_hash.
•	SA-01: SECURITY_ALERT includes evidence_refs and does not leak secrets/PII beyond policy.
