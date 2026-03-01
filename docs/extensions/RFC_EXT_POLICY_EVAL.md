12. RFC: EXT-POLICY-EVAL — Policy evaluation semantics (Registered Extension)
EXT-POLICY-EVAL standardizes how machine-checkable policies are packaged, evaluated, and evidenced across vendors. It intentionally avoids forcing a single policy language; instead it provides a reference binding mechanism to existing policy engines while keeping evaluations auditable.
12.1 Core objects (normative)
policy_bundle (normative minimum) MUST include: policy_bundle_id, version, language_id (registered), content (inline) OR artifact_ref, and content_hash (object_hash).
policy_binding (normative minimum) MUST include: binding_id (registered), parameters (MAY), input_schema_version (MUST).
evaluation_context (normative minimum) MUST include: context_id, contract_head_version, subject, action, resource, environment (MAY), and context_hash (object_hash over canonical form).
policy_decision (normative minimum) MUST include: decision (ALLOW|DENY|INCONCLUSIVE), reason_codes (SHOULD, registered), obligations (MAY), advice (MAY), evaluated_at, engine_info (MAY), and context_hash binding.
12.2 Message types and payloads (normative)
POLICY_EVAL_REQUEST payload MUST include: eval_id, policy_bundle_ref (hash or artifact_ref), policy_binding_ref, evaluation_context, and requested_action_id (MAY). It MAY include dry_run and deadline.
POLICY_EVAL_RESULT payload MUST include: eval_id, policy_decision, and MAY include evidence_refs. If the result is intended to be enforcement-relevant, it SHOULD be signed by the evaluating enforcer/engine identity.
POLICY_DECISION_ATTEST (optional) MAY be used to bind a policy_decision to ATTEST_ACTION when decisions are produced asynchronously.
12.3 Determinism requirements (normative intent)
•	The context_hash MUST be computed over a canonical evaluation_context so independent implementations can reproduce the input to the policy engine.
•	Policy engines that are non-deterministic (LLM classifiers) MAY be used only if their outputs are treated as evidence, not as deterministic truth; such use SHOULD be explicitly marked in engine_info.
12.4 Conformance suite (PE-*) (normative minimum)
•	PE-01: Same evaluation_context -> identical context_hash across implementations.
•	PE-02: Registered reason_codes used; unknown codes rejected or mapped per registry policy.
•	PE-03: Signed POLICY_EVAL_RESULT verifies under EXT-IDENTITY-LC rules when used for enforcement.
12.5 Registry bindings (normative)
language_id and binding_id MUST be registered (Section 8).
reason_codes used in POLICY_EVAL_RESULT MUST be either registered in `registry/policy_reason_codes.json` or namespaced as `vendor:*` or `org:*`.
