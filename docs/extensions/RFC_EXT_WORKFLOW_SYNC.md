15. RFC: Applied extensions (workflow, delegation, disputes, security alerts)

15.1 EXT-WORKFLOW-SYNC — Workflow synchronization (Registered Extension)
Purpose: synchronize a machine-readable workflow (plan/graph) as part of context, and attest step execution in a way a third-party enforcer can verify.
Message types:
•	WORKFLOW_DECLARE — introduce a workflow artifact and bind it to a contract head_version.
•	WORKFLOW_UPDATE — update/replace the workflow artifact (new version), referencing base_workflow_ref.
•	WORKFLOW_STEP_ATTEST — attest execution of a workflow step (inputs/outputs/evidence) under a specific head_version.
WORKFLOW_DECLARE payload (normative minimum): workflow_id (MUST), contract_head_version (MUST), workflow_artifact_ref (MUST), workflow_hash (SHOULD), version (MUST), step_index (MAY), policies_applied (MAY).
WORKFLOW_STEP_ATTEST payload (normative minimum): workflow_id (MUST), step_id (MUST), contract_head_version (MUST), status (MUST: started|completed|failed|skipped), input_refs or input_hash (SHOULD), output_refs or output_hash (SHOULD), evidence_refs (MAY), started_at/ended_at (MAY).
Enforcement hooks (normative intent): an enforcer MAY require that side effects only occur after a prior WORKFLOW_STEP_ATTEST or after a policy_decision attached to it.

15.5 Extension conformance (normative minimum)
•	AW-01: WORKFLOW_DECLARE + WORKFLOW_STEP_ATTEST validates head_version binding and evidence_refs hashing.
•	AD-01: DELEGATION_GRANT/ACCEPT/RESULT_ATTEST forms a verifiable chain of responsibility; max_depth enforced.
•	DS-01: CHALLENGE_ASSERTION references an existing attestation and is audit-verifiable via object_hash.
•	SA-01: SECURITY_ALERT includes evidence_refs and does not leak secrets/PII beyond policy.
