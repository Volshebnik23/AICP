PYTHON ?= python

.PHONY: validate snapshot validate-snapshot test conformance conformance-ext conformance-bindings conformance-profiles conformance-demos conformance-ops conformance-security conformance-all interop-matrix demo-enforcement-behavioral quickstart-ts quickstart-py lint release-check clean

validate:
	$(PYTHON) scripts/validate_json.py
	$(PYTHON) scripts/validate_jsonl.py
	$(PYTHON) scripts/validate_schema_instances.py
	$(PYTHON) scripts/validate_dropins_assets.py
	$(PYTHON) scripts/validate_registry.py
	$(PYTHON) scripts/validate_productization_coverage.py
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
	$(PYTHON) scripts/validate_snapshot_manifest.py

test:
	$(PYTHON) -c "import importlib.util, subprocess, sys; spec=importlib.util.find_spec('pytest'); raise SystemExit((print('pytest not installed; skipping make test.') or 0) if spec is None else subprocess.call(['pytest','-q','reference/python/tests']))"

conformance:
	$(PYTHON) conformance/runner/aicp_conformance_runner.py --suite conformance/core/CT_CORE_0.1.json --out conformance/report.json

conformance-ext:
	$(PYTHON) conformance/runner/aicp_conformance_runner.py --suite conformance/extensions/CN_CAPNEG_0.1.json --out conformance/report_ext_capneg.json
	$(PYTHON) conformance/runner/aicp_conformance_runner.py --suite conformance/extensions/DS_DISPUTES_0.1.json --out conformance/report_ext_disputes.json
	$(PYTHON) conformance/runner/aicp_conformance_runner.py --suite conformance/extensions/SA_SECURITY_ALERTS_0.1.json --out conformance/report_ext_security_alerts.json
	$(PYTHON) conformance/runner/aicp_conformance_runner.py --suite conformance/extensions/PA_PARTICIPANTS_0.1.json --out conformance/report_ext_participants.json
	$(PYTHON) conformance/runner/aicp_conformance_runner.py --suite conformance/extensions/TG_TOOL_GATING_0.1.json --out conformance/report_ext_tool_gating.json
	$(PYTHON) conformance/runner/aicp_conformance_runner.py --suite conformance/extensions/ID_IDENTITY_LC_0.1.json --out conformance/report_ext_identity_lc.json
	$(PYTHON) conformance/runner/aicp_conformance_runner.py --suite conformance/extensions/DL_DELEGATION_0.1.json --out conformance/report_ext_delegation.json
	$(PYTHON) conformance/runner/aicp_conformance_runner.py --suite conformance/extensions/WF_WORKFLOW_SYNC_0.1.json --out conformance/report_ext_workflow_sync.json
	$(PYTHON) conformance/runner/aicp_conformance_runner.py --suite conformance/extensions/OR_OBJECT_RESYNC_0.1.json --out conformance/report_ext_object_resync.json
	$(PYTHON) conformance/runner/aicp_conformance_runner.py --suite conformance/extensions/PE_POLICY_EVAL_0.1.json --out conformance/report_ext_policy_eval.json
	$(PYTHON) conformance/runner/aicp_conformance_runner.py --suite conformance/extensions/ENF_ENFORCEMENT_0.1.json --out conformance/report_ext_enforcement.json
	$(PYTHON) conformance/runner/aicp_conformance_runner.py --suite conformance/extensions/AL_ALERTS_0.1.json --out conformance/report_ext_alerts.json
	$(PYTHON) conformance/runner/aicp_conformance_runner.py --suite conformance/extensions/RS_RESUME_0.1.json --out conformance/report_ext_resume.json

conformance-bindings:
	$(PYTHON) conformance/runner/aicp_conformance_runner.py --suite conformance/bindings/TB_MCP_0.1.json --out conformance/report_bind_mcp.json

conformance-all:
	$(MAKE) conformance
	$(MAKE) conformance-ext
	$(MAKE) conformance-bindings
	$(MAKE) conformance-profiles
	$(MAKE) conformance-demos
	$(MAKE) conformance-ops
	$(MAKE) conformance-security

conformance-profiles:
	$(PYTHON) conformance/runner/aicp_profile_runner.py --profile conformance/profiles/PF_AICP_BASE_0.1.json --out conformance/report_profile_base.json
	$(PYTHON) conformance/runner/aicp_profile_runner.py --profile conformance/profiles/PF_AICP_MEDIATED_BLOCKING_0.1.json --out conformance/report_profile_mediated_blocking.json
	$(PYTHON) conformance/runner/aicp_profile_runner.py --profile conformance/profiles/PF_AICP_MEDIATED_BLOCKING_OPS_0.1.json --out conformance/report_profile_mediated_blocking_ops.json
	$(PYTHON) conformance/runner/aicp_profile_runner.py --profile conformance/profiles/PF_AICP_RESUMABLE_SESSIONS_0.1.json --out conformance/report_profile_resumable_sessions.json
	$(PYTHON) conformance/runner/aicp_profile_runner.py --profile conformance/profiles/PF_AICP_RECEPTION_CHAT_0.1.json --out conformance/report_profile_reception_chat.json

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

lint:
	@echo "Lint target placeholder: no lint checks configured."

release-check:
	$(PYTHON) -c "from pathlib import Path; req=['VERSION','RELEASE_NOTES.md','SECURITY.md','CONTRIBUTING.md','CODE_OF_CONDUCT.md','docs/core/AICP_Core_v0.1_Normative.md','schemas/core/aicp-core-message.schema.json','schemas/core/aicp-core-contract.schema.json','schemas/core/aicp-core-payloads.schema.json','fixtures/core_tv.json','fixtures/golden_transcripts/GT-01_happy_path_signed.jsonl','fixtures/golden_transcripts/GT-02_conflict_choose_signed.jsonl','fixtures/keys/GT_public_keys.json']; missing=[p for p in req if not Path(p).exists()]; print('All required release hygiene and canonical Core artifacts are present.' if not missing else 'Missing required files: ' + ', '.join(missing)); raise SystemExit(1 if missing else 0)"

clean:
	rm -f conformance/report.json conformance/report_ext_capneg.json conformance/report_ext_disputes.json conformance/report_ext_security_alerts.json conformance/report_ext_participants.json conformance/report_ext_tool_gating.json conformance/report_ext_identity_lc.json conformance/report_ext_delegation.json conformance/report_ext_workflow_sync.json conformance/report_ext_object_resync.json conformance/report_ext_policy_eval.json conformance/report_ext_enforcement.json conformance/report_ext_alerts.json conformance/report_ext_resume.json conformance/report_bind_mcp.json conformance/report_profile_base.json conformance/report_profile_mediated_blocking.json conformance/report_profile_mediated_blocking_ops.json conformance/report_profile_resumable_sessions.json conformance/report_profile_reception_chat.json conformance/report_demo_enforcement_behavioral.json conformance/report_ops_hardening.json conformance/report_security_signed_path.json
