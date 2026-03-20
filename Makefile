PYTHON ?= python

.PHONY: validate snapshot validate-snapshot test conformance conformance-core conformance-ext conformance-bindings conformance-profiles conformance-demos conformance-ops conformance-security conformance-all interop-matrix demo-enforcement-behavioral quickstart-ts quickstart-py template-smoke prepr lint release-check clean

validate:
	$(PYTHON) scripts/validate_json.py
	$(PYTHON) scripts/validate_jsonl.py
	$(PYTHON) scripts/validate_schema_instances.py
	$(PYTHON) scripts/validate_dropins_assets.py
	$(PYTHON) scripts/validate_registry.py
	$(PYTHON) scripts/validate_binding_case_instances.py
	$(PYTHON) scripts/validate_channel_properties_alignment.py
	$(PYTHON) scripts/validate_compatibility_marks.py
	$(PYTHON) scripts/validate_interop_submission_examples.py
	$(PYTHON) scripts/validate_productization_coverage.py
	$(PYTHON) scripts/validate_errata.py
	$(PYTHON) scripts/validate_planning_docs.py
	$(PYTHON) scripts/validate_verification_gate_alignment.py
	$(PYTHON) scripts/validate_shipped_extension_coverage.py
	@if [ "$$AICP_SKIP_SNAPSHOT" = "1" ]; then \
		echo "[WARN] skipping snapshot validation because AICP_SKIP_SNAPSHOT=1"; \
	else \
		$(MAKE) validate-snapshot; \
	fi
	$(PYTHON) scripts/check_naming.py
	$(PYTHON) scripts/check_terms.py
	$(PYTHON) scripts/check_no_binary_changes.py

snapshot:
	$(PYTHON) scripts/generate_snapshot_manifest.py

validate-snapshot:
	$(PYTHON) -m py_compile scripts/validate_snapshot_manifest.py
	$(PYTHON) scripts/validate_snapshot_manifest.py

test:
	$(PYTHON) -c "import importlib.util, subprocess, sys; spec=importlib.util.find_spec('pytest'); raise SystemExit((print('pytest not installed; skipping make test.') or 0) if spec is None else subprocess.call(['pytest','-q','reference/python/tests']))"

conformance:
	$(MAKE) conformance-core

conformance-core:
	$(PYTHON) conformance/runner/aicp_conformance_runner.py --suite conformance/core/CT_CORE_0.1.json --out conformance/report.json
	$(PYTHON) conformance/runner/aicp_conformance_runner.py --suite conformance/core/CT_NUMERIC_GUARDRAILS_0.1.json --out conformance/report_core_numeric_guardrails.json

conformance-ext:
	$(PYTHON) conformance/runner/aicp_batch_runner.py \
		--suite-out conformance/extensions/CN_CAPNEG_0.1.json::conformance/report_ext_capneg.json \
		--suite-out conformance/extensions/CF_CONFIDENTIALITY_0.1.json::conformance/report_ext_confidentiality.json \
		--suite-out conformance/extensions/CM_COMMERCE_ACP_PROFILE_0.1.json::conformance/report_ext_commerce_acp_profile.json \
		--suite-out conformance/extensions/RD_REDACTION_0.1.json::conformance/report_ext_redaction.json \
		--suite-out conformance/extensions/HA_HUMAN_APPROVAL_0.1.json::conformance/report_ext_human_approval.json \
		--suite-out conformance/extensions/DS_DISPUTES_0.1.json::conformance/report_ext_disputes.json \
		--suite-out conformance/extensions/SA_SECURITY_ALERT_0.1.json::conformance/report_ext_security_alerts.json \
		--suite-out conformance/extensions/PA_PARTICIPANTS_0.1.json::conformance/report_ext_participants.json \
		--suite-out conformance/extensions/TG_TOOL_GATING_0.1.json::conformance/report_ext_tool_gating.json \
		--suite-out conformance/extensions/AM_ARTIFACT_MANIFESTS_PINNING_0.1.json::conformance/report_ext_artifact_manifests_pinning.json \
		--suite-out conformance/extensions/ID_IDENTITY_LC_0.1.json::conformance/report_ext_identity_lc.json \
		--suite-out conformance/extensions/DL_DELEGATION_0.1.json::conformance/report_ext_delegation.json \
		--suite-out conformance/extensions/WF_WORKFLOW_SYNC_0.1.json::conformance/report_ext_workflow_sync.json \
		--suite-out conformance/extensions/OR_OBJECT_RESYNC_0.1.json::conformance/report_ext_object_resync.json \
		--suite-out conformance/extensions/PE_POLICY_EVAL_0.1.json::conformance/report_ext_policy_eval.json \
		--suite-out conformance/extensions/ENF_ENFORCEMENT_0.1.json::conformance/report_ext_enforcement.json \
		--suite-out conformance/extensions/AL_ALERTS_0.1.json::conformance/report_ext_alerts.json \
		--suite-out conformance/extensions/RS_RESUME_0.1.json::conformance/report_ext_resume.json \
		--suite-out conformance/extensions/DI_DELEGATED_IDENTITY_0.1.json::conformance/report_ext_delegated_identity.json \
		--suite-out conformance/extensions/IB_IAM_BRIDGE_0.1.json::conformance/report_ext_iam_bridge.json \
		--suite-out conformance/extensions/OB_OBSERVABILITY_0.1.json::conformance/report_ext_observability.json \
		--suite-out conformance/extensions/EB_ENTERPRISE_BINDINGS_0.1.json::conformance/report_ext_enterprise_bindings.json \
		--suite-out conformance/extensions/ET_EXTERNAL_TRANSACTION_0.1.json::conformance/report_ext_external_transaction.json \
		--suite-out conformance/extensions/RC_RECEPTION_CHAT_SEMANTICS_0.1.json::conformance/report_ext_reception_chat_semantics.json \
		--suite-out conformance/extensions/EC_ECONOMICS_0.1.json::conformance/report_ext_economics.json \
		--suite-out conformance/extensions/AD_ADMISSION_0.1.json::conformance/report_ext_admission.json \
		--suite-out conformance/extensions/QL_QUEUE_LEASES_0.1.json::conformance/report_ext_queue_leases.json \
		--suite-out conformance/extensions/FA_FACILITATION_0.1.json::conformance/report_ext_facilitation.json \
		--suite-out conformance/extensions/CH_CHANNELS_0.1.json::conformance/report_ext_channels.json \
		--suite-out conformance/extensions/SB_SUBSCRIPTIONS_0.1.json::conformance/report_ext_subscriptions.json \
		--suite-out conformance/extensions/PB_PUBLICATIONS_0.1.json::conformance/report_ext_publications.json \
		--suite-out conformance/extensions/IB_INBOX_0.1.json::conformance/report_ext_inbox.json \
		--suite-out conformance/extensions/MP_MARKETPLACE_0.1.json::conformance/report_ext_marketplace.json \
		--suite-out conformance/extensions/PR_PROVENANCE_0.1.json::conformance/report_ext_provenance.json \
		--suite-out conformance/extensions/ES_ACTION_ESCROW_0.1.json::conformance/report_ext_action_escrow.json \
		--suite-out conformance/extensions/RP_RESPONSIBILITY_0.1.json::conformance/report_ext_responsibility.json \
		--suite-out conformance/extensions/TA_TRUST_ATTESTATIONS_0.1.json::conformance/report_ext_trust_attestations.json \
		--suite-out conformance/extensions/SC_STATUS_CHANNEL_0.1.json::conformance/report_ext_status_channel.json \
		--suite-out conformance/extensions/TW_TRANSCRIPT_WITNESS_0.1.json::conformance/report_ext_transcript_witness.json \
		--suite-out conformance/extensions/EX_EXECUTION_LIFECYCLE_0.1.json::conformance/report_ext_execution_lifecycle.json

conformance-bindings:
	$(PYTHON) conformance/runner/aicp_conformance_runner.py --suite conformance/bindings/TB_MCP_0.1.json --out conformance/report_bind_mcp.json
	$(PYTHON) conformance/runner/aicp_conformance_runner.py --suite conformance/bindings/TB_HTTP_WS_0.1.json --out conformance/report_bind_http_ws.json

conformance-all:
	$(MAKE) conformance
	$(MAKE) conformance-ext
	$(MAKE) conformance-bindings
	$(MAKE) conformance-profiles
	$(MAKE) conformance-demos
	$(MAKE) conformance-ops
	$(MAKE) conformance-security

conformance-profiles:
	$(PYTHON) conformance/runner/aicp_batch_runner.py \
		--profile-out conformance/profiles/PF_AICP_BASE_0.1.json::conformance/report_profile_base.json \
		--profile-out conformance/profiles/PF_AICP_MEDIATED_BLOCKING_0.1.json::conformance/report_profile_mediated_blocking.json \
		--profile-out conformance/profiles/PF_AICP_MEDIATED_BLOCKING_OPS_0.1.json::conformance/report_profile_mediated_blocking_ops.json \
		--profile-out conformance/profiles/PF_AICP_RESUMABLE_SESSIONS_0.1.json::conformance/report_profile_resumable_sessions.json \
		--profile-out conformance/profiles/PF_AICP_RECEPTION_CHAT_0.1.json::conformance/report_profile_reception_chat.json \
		--profile-out conformance/profiles/PF_AICP_DELEGATED_IDENTITY_0.1.json::conformance/report_profile_delegated_identity.json \
		--profile-out conformance/profiles/PF_AICP_WORKFLOW_ORCHESTRATION_DELEGATION_0.1.json::conformance/report_profile_workflow_orchestration_delegation.json \
		--profile-out conformance/profiles/PF_AICP_BAZAAR_RECEPTION_0.1.json::conformance/report_profile_bazaar_reception.json \
		--profile-out conformance/profiles/PF_AICP_AGENT_MEDIA_0.1.json::conformance/report_profile_agent_media.json \
		--profile-out conformance/profiles/PF_AICP_EXECUTION_INTEROP_0.1.json::conformance/report_profile_execution_interop.json \
		--profile-out conformance/profiles/PF_AICP_COMMERCE_ACP_0.1.json::conformance/report_profile_commerce_acp.json \
		--profile-out conformance/profiles/PF_AICP_POLICY_OPA_REGO_0.1.json::conformance/report_profile_policy_opa_rego.json \
		--profile-out conformance/profiles/PF_AICP_POLICY_ABAC_RBAC_0.1.json::conformance/report_profile_policy_abac_rbac.json \
		--profile-out conformance/profiles/PF_AICP_POLICY_LLM_SAFETY_0.1.json::conformance/report_profile_policy_llm_safety.json

conformance-demos:
	$(PYTHON) conformance/runner/aicp_conformance_runner.py --suite conformance/demos/DEMO_ENFORCEMENT_BEHAVIORAL_0.1.json --out conformance/report_demo_enforcement_behavioral.json

conformance-ops:
	$(PYTHON) conformance/runner/aicp_conformance_runner.py --suite conformance/ops/OPS_HARDENING_0.1.json --out conformance/report_ops_hardening.json

conformance-security:
	$(PYTHON) conformance/runner/aicp_conformance_runner.py --suite conformance/security/SIG_SIGNED_PATHS_0.1.json --out conformance/report_security_signed_path.json

interop-matrix:
	$(PYTHON) interop/tools/interop_matrix.py --submissions interop/submissions --out-md interop/INTEROP_MATRIX.md --out-json interop/interop_matrix.json

demo-enforcement-behavioral:
	$(PYTHON) demos/enforcement_behavioral/scripts/run_demo.py


quickstart-ts:
	node dropins/aicp-core/typescript/scripts/generate_minimal_core_transcript.mjs --out out/quickstart/ts/minimal_core.jsonl
	$(PYTHON) sandbox/run.py out/quickstart/ts/minimal_core.jsonl --no-signature-verify

quickstart-py:
	$(PYTHON) dropins/aicp-core/python/generate_minimal_core_transcript.py --out out/quickstart/py/minimal_core.jsonl
	$(PYTHON) sandbox/run.py out/quickstart/py/minimal_core.jsonl --no-signature-verify

template-smoke:
	mkdir -p out/template-ts-agent out/template-protocol-adapter
	node templates/ts-agent/agent.js > out/template-ts-agent/thread.jsonl
	$(PYTHON) sandbox/run.py out/template-ts-agent/thread.jsonl --no-signature-verify
	$(PYTHON) templates/protocol-adapter/adapter.py fixtures/golden_transcripts/GT-01_happy_path_signed.jsonl > out/template-protocol-adapter/events.json

prepr:
	$(MAKE) validate
	$(MAKE) conformance
	$(MAKE) conformance-ext
	$(MAKE) conformance-bindings
	$(MAKE) conformance-profiles
	$(MAKE) test
	$(MAKE) quickstart-py
	$(MAKE) quickstart-ts
	$(MAKE) template-smoke
	cd sdk/typescript && npm ci && npm test

lint:
	@echo "Lint target placeholder: no lint checks configured."

release-check:
	$(PYTHON) -c "from pathlib import Path; req=['VERSION','RELEASE_NOTES.md','SECURITY.md','CONTRIBUTING.md','CODE_OF_CONDUCT.md','docs/core/AICP_Core_v0.1_Normative.md','schemas/core/aicp-core-message.schema.json','schemas/core/aicp-core-contract.schema.json','schemas/core/aicp-core-payloads.schema.json','fixtures/core_tv.json','fixtures/golden_transcripts/GT-01_happy_path_signed.jsonl','fixtures/golden_transcripts/GT-02_conflict_choose_signed.jsonl','fixtures/keys/GT_public_keys.json']; missing=[p for p in req if not Path(p).exists()]; print('All required release hygiene and canonical Core artifacts are present.' if not missing else 'Missing required files: ' + ', '.join(missing)); raise SystemExit(1 if missing else 0)"

clean:
	rm -f conformance/report.json conformance/report_core_numeric_guardrails.json conformance/report_ext_capneg.json conformance/report_ext_confidentiality.json conformance/report_ext_redaction.json conformance/report_ext_human_approval.json conformance/report_ext_disputes.json conformance/report_ext_security_alerts.json conformance/report_ext_participants.json conformance/report_ext_tool_gating.json conformance/report_ext_identity_lc.json conformance/report_ext_delegation.json conformance/report_ext_workflow_sync.json conformance/report_ext_object_resync.json conformance/report_ext_policy_eval.json conformance/report_ext_enforcement.json conformance/report_ext_alerts.json conformance/report_ext_resume.json conformance/report_ext_delegated_identity.json conformance/report_ext_reception_chat_semantics.json conformance/report_ext_economics.json conformance/report_ext_admission.json conformance/report_ext_queue_leases.json conformance/report_ext_facilitation.json conformance/report_ext_channels.json conformance/report_ext_subscriptions.json conformance/report_ext_publications.json conformance/report_ext_inbox.json conformance/report_ext_marketplace.json conformance/report_ext_provenance.json conformance/report_ext_action_escrow.json conformance/report_ext_responsibility.json conformance/report_ext_trust_attestations.json conformance/report_ext_observability.json conformance/report_ext_enterprise_bindings.json conformance/report_ext_status_channel.json conformance/report_ext_execution_lifecycle.json conformance/report_bind_mcp.json conformance/report_bind_http_ws.json conformance/report_profile_base.json conformance/report_profile_mediated_blocking.json conformance/report_profile_mediated_blocking_ops.json conformance/report_profile_resumable_sessions.json conformance/report_profile_reception_chat.json conformance/report_profile_delegated_identity.json conformance/report_profile_workflow_orchestration_delegation.json conformance/report_profile_bazaar_reception.json conformance/report_profile_agent_media.json conformance/report_profile_execution_interop.json conformance/report_profile_policy_opa_rego.json conformance/report_profile_policy_abac_rbac.json conformance/report_profile_policy_llm_safety.json conformance/report_demo_enforcement_behavioral.json conformance/report_ops_hardening.json conformance/report_security_signed_path.json
