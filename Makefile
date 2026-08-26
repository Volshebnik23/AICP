PYTHON ?= python

.PHONY: validate message-surface-complete interop-validate interop-review interop-dryrun interop-build-example snapshot validate-snapshot test conformance conformance-core conformance-ext conformance-capneg-v02 conformance-session-state-projection-v2 conformance-bindings conformance-profiles conformance-demos conformance-ops conformance-security conformance-all conformance-provenance conformance-iut-smoke conformance-iut-full-reference evidence-targets-validate evidence-capability-smoke-reference evidence-capability-full-reference evidence-capability-full-external-test evidence-profile-mediated-smoke-reference evidence-profile-mediated-full-reference evidence-profile-mediated-full-external-test evidence-profile-resumable-smoke-reference evidence-profile-resumable-full-reference evidence-profile-resumable-full-external-test evidence-profile-delegated-smoke-reference evidence-profile-delegated-full-reference evidence-profile-delegated-full-external-test live-binding-http-smoke-reference live-binding-http-full-reference live-binding-http-full-external-test live-binding-mcp-smoke-reference live-binding-mcp-full-reference live-binding-mcp-full-external-test evidence-binding-examples evidence-submission-examples pairwise-targets-validate pairwise-base-mcp-cleanroom pairwise-base-mcp-external-test pairwise-negative pairwise-submission-examples interop-matrix demo-enforcement-behavioral quickstart-ts quickstart-py quickstart-core-v02-py quickstart-core-v02-ts quickstart-capneg-v02-py quickstart-capneg-v02-ts template-smoke uat-check prepr compatibility-gate release-gate lint release-check clean

validate:
	$(PYTHON) scripts/validate_json.py
	$(PYTHON) scripts/validate_jsonl.py
	$(PYTHON) scripts/validate_schema_instances.py
	$(PYTHON) scripts/validate_dropins_assets.py
	$(PYTHON) scripts/validate_registry.py
	$(PYTHON) scripts/validate_binding_case_instances.py
	$(PYTHON) scripts/validate_channel_properties_alignment.py
	$(PYTHON) scripts/validate_compatibility_marks.py
	$(PYTHON) scripts/validate_case_unique_paths.py
	$(PYTHON) scripts/validate_conformance_catalog.py
	$(PYTHON) scripts/validate_interop_submission_examples.py
	$(PYTHON) scripts/validate_interop_submissions.py
	$(PYTHON) scripts/validate_pairwise_targets.py
	$(PYTHON) scripts/validate_productization_coverage.py
	$(PYTHON) scripts/validate_errata.py
	$(PYTHON) scripts/validate_planning_docs.py
	$(PYTHON) scripts/validate_message_surface_completion.py
	$(PYTHON) scripts/validate_verification_gate_alignment.py
	$(PYTHON) scripts/validate_shipped_extension_coverage.py
	$(PYTHON) scripts/generate_core_v02_fixtures.py --check
	$(PYTHON) scripts/generate_profile_composition_registry.py --check
	$(PYTHON) scripts/generate_capneg_v02_fixtures.py --check
	$(PYTHON) scripts/generate_evidence_framework.py --check
	$(PYTHON) scripts/generate_pairwise_tck.py --check
	$(PYTHON) scripts/generate_evidence_submission_example.py --check
	@if [ "$$AICP_SKIP_SNAPSHOT" = "1" ]; then \
		echo "[WARN] skipping snapshot validation because AICP_SKIP_SNAPSHOT=1"; \
	else \
		$(MAKE) validate-snapshot; \
	fi
	$(PYTHON) scripts/check_naming.py
	$(PYTHON) scripts/check_terms.py
	$(PYTHON) scripts/check_no_binary_changes.py

message-surface-complete:
	$(PYTHON) scripts/validate_message_surface_completion.py

snapshot:
	$(PYTHON) scripts/generate_snapshot_manifest.py

validate-snapshot:
	$(PYTHON) -m py_compile scripts/validate_snapshot_manifest.py
	$(PYTHON) scripts/validate_snapshot_manifest.py

test:
	$(PYTHON) -c "import importlib.util, subprocess, sys; spec=importlib.util.find_spec('pytest'); raise SystemExit((print('pytest not installed; skipping make test.') or 0) if spec is None else subprocess.call([sys.executable,'-m','pytest','-q','reference/python/tests']))"

conformance:
	$(MAKE) conformance-core

conformance-core:
	$(PYTHON) conformance/runner/aicp_batch_runner.py --catalog core
	$(PYTHON) conformance/core_v02_runner/aicp_core_v02_runner.py

conformance-ext:
	$(PYTHON) conformance/runner/aicp_batch_runner.py --catalog extensions
	$(MAKE) conformance-capneg-v02
	$(MAKE) conformance-session-state-projection-v2

conformance-capneg-v02:
	$(PYTHON) conformance/capneg_v02_runner/aicp_capneg_v02_runner.py

conformance-session-state-projection-v2:
	$(PYTHON) conformance/capneg_v02_runner/aicp_capneg_v02_runner.py --suite conformance/extensions/OR_SESSION_STATE_PROJECTION_V2.json --out conformance/report_ext_session_state_projection_v2.json

conformance-bindings:
	$(PYTHON) conformance/runner/aicp_batch_runner.py --catalog bindings

conformance-all:
	$(MAKE) conformance
	$(MAKE) conformance-ext
	$(MAKE) conformance-bindings
	$(MAKE) conformance-profiles
	$(MAKE) conformance-demos
	$(MAKE) conformance-ops
	$(MAKE) conformance-security

conformance-profiles:
	$(PYTHON) conformance/runner/aicp_batch_runner.py --catalog profiles
	$(PYTHON) conformance/core_v02_runner/aicp_core_v02_profile_runner.py

conformance-demos:
	$(PYTHON) conformance/runner/aicp_batch_runner.py --catalog demos

conformance-ops:
	$(PYTHON) conformance/runner/aicp_batch_runner.py --catalog ops

conformance-security:
	$(PYTHON) conformance/runner/aicp_batch_runner.py --catalog security

conformance-provenance:
	$(PYTHON) conformance/runner/aicp_conformance_runner.py --suite conformance/core/CT_CORE_0.1.json --report-format v1 --out out/provenance/report_core_v1.json
	$(PYTHON) conformance/runner/aicp_profile_runner.py --profile conformance/profiles/PF_AICP_BASE_0.1.json --report-format v1 --out out/provenance/report_profile_base_v1.json

conformance-iut-smoke:
	$(PYTHON) conformance/iut/aicp_iut_runner.py --cmd "$(PYTHON) conformance/iut/reference_adapter.py" --profile AICP-BASE@0.1 --mode smoke --include-session-state-projection --out conformance/iut/report_reference_base.json
	$(PYTHON) conformance/iut/aicp_iut_runner.py --cmd "$(PYTHON) conformance/iut/reference_adapter.py" --profile AICP-AUTHENTICATED-BASE@0.1 --mode smoke --out conformance/iut/report_reference_authenticated_base.json

conformance-iut-full-reference:
	$(PYTHON) conformance/iut/aicp_iut_runner.py --cmd "$(PYTHON) conformance/iut/reference_adapter.py" --profile AICP-BASE@0.1 --mode full-profile --out conformance/iut/report_reference_base_full.json
	$(PYTHON) conformance/iut/aicp_iut_runner.py --cmd "$(PYTHON) conformance/iut/reference_adapter.py" --profile AICP-AUTHENTICATED-BASE@0.1 --mode full-profile --out conformance/iut/report_reference_authenticated_base_full.json

evidence-targets-validate:
	$(PYTHON) scripts/generate_evidence_framework.py --check

evidence-capability-smoke-reference:
	$(PYTHON) conformance/evidence/aicp_external_evidence_runner.py --cmd-json '["$(PYTHON)","conformance/evidence/reference_adapter.py"]' --target aicp.session_state_projection@v1 --mode smoke --out out/evidence/projection-v1-reference-smoke.json

evidence-capability-full-reference:
	$(PYTHON) conformance/evidence/aicp_external_evidence_runner.py --cmd-json '["$(PYTHON)","conformance/evidence/reference_adapter.py"]' --target aicp.session_state_projection@v1 --mode full-capability --out out/evidence/projection-v1-reference-full.json

evidence-capability-full-external-test:
	$(PYTHON) conformance/evidence/aicp_external_evidence_runner.py --cmd-json '["$(PYTHON)","conformance/evidence/fake_adapters.py","--mode","external_good"]' --target aicp.session_state_projection@v1 --mode full-capability --out out/evidence/projection-v1-external-test.json

evidence-profile-mediated-smoke-reference:
	$(PYTHON) conformance/evidence/aicp_external_evidence_runner.py --cmd-json '["$(PYTHON)","conformance/evidence/product_profile_reference_adapter.py"]' --target AICP-MEDIATED-BLOCKING@0.1 --mode smoke --out out/evidence/mediated-blocking-reference-smoke.json

evidence-profile-mediated-full-reference:
	$(PYTHON) conformance/evidence/aicp_external_evidence_runner.py --cmd-json '["$(PYTHON)","conformance/evidence/product_profile_reference_adapter.py"]' --target AICP-MEDIATED-BLOCKING@0.1 --mode full-profile --out out/evidence/mediated-blocking-reference-full.json

evidence-profile-mediated-full-external-test:
	$(PYTHON) conformance/evidence/aicp_external_evidence_runner.py --cmd-json '["$(PYTHON)","conformance/evidence/product_profile_fake_adapters.py","--mode","external_good"]' --target AICP-MEDIATED-BLOCKING@0.1 --mode full-profile --out out/evidence/mediated-blocking-external-test.json

evidence-profile-resumable-smoke-reference:
	$(PYTHON) conformance/evidence/aicp_external_evidence_runner.py --cmd-json '["$(PYTHON)","conformance/evidence/product_profile_reference_adapter.py"]' --target AICP-RESUMABLE-SESSIONS@0.1 --mode smoke --out out/evidence/resumable-sessions-reference-smoke.json

evidence-profile-resumable-full-reference:
	$(PYTHON) conformance/evidence/aicp_external_evidence_runner.py --cmd-json '["$(PYTHON)","conformance/evidence/product_profile_reference_adapter.py"]' --target AICP-RESUMABLE-SESSIONS@0.1 --mode full-profile --out out/evidence/resumable-sessions-reference-full.json

evidence-profile-resumable-full-external-test:
	$(PYTHON) conformance/evidence/aicp_external_evidence_runner.py --cmd-json '["$(PYTHON)","conformance/evidence/product_profile_fake_adapters.py","--mode","external_good"]' --target AICP-RESUMABLE-SESSIONS@0.1 --mode full-profile --out out/evidence/resumable-sessions-external-test.json

evidence-profile-delegated-smoke-reference:
	$(PYTHON) conformance/evidence/aicp_external_evidence_runner.py --cmd-json '["$(PYTHON)","conformance/evidence/product_profile_reference_adapter.py"]' --target AICP-DELEGATED-IDENTITY@0.1 --mode smoke --out out/evidence/delegated-identity-reference-smoke.json

evidence-profile-delegated-full-reference:
	$(PYTHON) conformance/evidence/aicp_external_evidence_runner.py --cmd-json '["$(PYTHON)","conformance/evidence/product_profile_reference_adapter.py"]' --target AICP-DELEGATED-IDENTITY@0.1 --mode full-profile --out out/evidence/delegated-identity-reference-full.json

evidence-profile-delegated-full-external-test:
	$(PYTHON) conformance/evidence/aicp_external_evidence_runner.py --cmd-json '["$(PYTHON)","conformance/evidence/product_profile_fake_adapters.py","--mode","external_good"]' --target AICP-DELEGATED-IDENTITY@0.1 --mode full-profile --out out/evidence/delegated-identity-external-test.json

live-binding-http-smoke-reference:
	$(PYTHON) conformance/evidence/aicp_live_binding_runner.py --server-cmd-json '["$(PYTHON)","conformance/evidence/live_bindings/live_binding_test_implementation.py","--binding","http","--role","server_under_test","--kind","reference_corpus","--mode","good"]' --target BIND-HTTP@0.1 --mode smoke --out out/evidence/bind-http-reference-smoke.json

live-binding-http-full-reference:
	$(PYTHON) conformance/evidence/aicp_live_binding_runner.py --server-cmd-json '["$(PYTHON)","conformance/evidence/live_bindings/live_binding_test_implementation.py","--binding","http","--role","server_under_test","--kind","reference_corpus","--mode","good"]' --client-cmd-json '["$(PYTHON)","conformance/evidence/live_bindings/live_binding_test_implementation.py","--binding","http","--role","client_under_test","--kind","reference_corpus","--mode","good"]' --target BIND-HTTP@0.1 --mode full-binding --out out/evidence/bind-http-reference-full.json

live-binding-http-full-external-test:
	$(PYTHON) conformance/evidence/aicp_live_binding_runner.py --server-cmd-json '["$(PYTHON)","conformance/evidence/live_bindings/live_binding_test_implementation.py","--binding","http","--role","server_under_test","--kind","external_implementation","--mode","good"]' --client-cmd-json '["$(PYTHON)","conformance/evidence/live_bindings/live_binding_test_implementation.py","--binding","http","--role","client_under_test","--kind","external_implementation","--mode","good"]' --target BIND-HTTP@0.1 --mode full-binding --out out/evidence/bind-http-external-test.json

live-binding-mcp-smoke-reference:
	$(PYTHON) conformance/evidence/aicp_live_binding_runner.py --server-cmd-json '["$(PYTHON)","conformance/evidence/live_bindings/live_binding_test_implementation.py","--binding","mcp","--role","server_under_test","--kind","reference_corpus","--mode","good"]' --target BIND-MCP@0.1 --mode smoke --out out/evidence/bind-mcp-reference-smoke.json

live-binding-mcp-full-reference:
	$(PYTHON) conformance/evidence/aicp_live_binding_runner.py --server-cmd-json '["$(PYTHON)","conformance/evidence/live_bindings/live_binding_test_implementation.py","--binding","mcp","--role","server_under_test","--kind","reference_corpus","--mode","good"]' --client-cmd-json '["$(PYTHON)","conformance/evidence/live_bindings/live_binding_test_implementation.py","--binding","mcp","--role","client_under_test","--kind","reference_corpus","--mode","good"]' --target BIND-MCP@0.1 --mode full-binding --out out/evidence/bind-mcp-reference-full.json

live-binding-mcp-full-external-test:
	$(PYTHON) conformance/evidence/aicp_live_binding_runner.py --server-cmd-json '["$(PYTHON)","conformance/evidence/live_bindings/live_binding_test_implementation.py","--binding","mcp","--role","server_under_test","--kind","external_implementation","--mode","good"]' --client-cmd-json '["$(PYTHON)","conformance/evidence/live_bindings/live_binding_test_implementation.py","--binding","mcp","--role","client_under_test","--kind","external_implementation","--mode","good"]' --target BIND-MCP@0.1 --mode full-binding --out out/evidence/bind-mcp-external-test.json

evidence-binding-examples:
	$(PYTHON) scripts/validate_interop_submission_examples.py

evidence-submission-examples:
	$(PYTHON) scripts/generate_evidence_submission_example.py --check
	$(PYTHON) scripts/validate_interop_submission_examples.py

pairwise-targets-validate:
	$(PYTHON) scripts/validate_pairwise_targets.py

pairwise-base-mcp-cleanroom:
	$(PYTHON) scripts/run_pairwise_cleanroom.py --side-only

pairwise-base-mcp-external-test:
	$(PYTHON) scripts/run_pairwise_cleanroom.py

pairwise-negative:
	$(PYTHON) -m pytest reference/python/tests/test_pairwise_m66.py reference/python/tests/test_pairwise_m66_correction_reproductions.py reference/python/tests/test_pairwise_m66_correction.py -q

pairwise-submission-examples:
	$(PYTHON) scripts/validate_interop_submission_examples.py
	$(PYTHON) -m pytest reference/python/tests/test_pairwise_m66.py -q -k "public_pairwise or missing_joint"

interop-validate:
	$(PYTHON) scripts/validate_interop_submission_examples.py
	$(PYTHON) scripts/validate_interop_submissions.py
	$(MAKE) interop-matrix

interop-review:
	@: $${SUBMISSION:?set SUBMISSION=interop/submissions/<submission_id> (or an example/template path) }
	$(PYTHON) scripts/validate_interop_submissions.py
	$(PYTHON) scripts/review_interop_submission.py "$${SUBMISSION}"

interop-dryrun:
	$(PYTHON) scripts/validate_interop_submissions.py
	$(PYTHON) scripts/review_interop_submission.py interop/submissions/dryrun-reviewed-base
	$(MAKE) interop-matrix

interop-matrix:
	$(PYTHON) interop/tools/interop_matrix.py --submissions interop/submissions --out-md interop/INTEROP_MATRIX.md --out-json interop/interop_matrix.json

interop-build-example:
	$(PYTHON) interop/tools/build_submission.py \
		--out-root out/interop-submissions \
		--submission-id fictional-single-impl \
		--implementation-id fictional-impl-a \
		--implementation-version 1.2.3 \
		--profile-id AICP-BASE \
		--claim-type implements_profile \
		--claim-scope self_attested \
		--evidence-status reproducible \
		--report-path interop/submissions/examples/single_profile_claim/reports/report_profile_base.json \
		--report-path interop/submissions/examples/single_profile_claim/reports/report_core.json \
		--suite-ref PF_AICP_BASE_0.1 \
		--suite-ref CT_CORE_0.1 \
		--disclosure "Fictional example package only; not a market-facing claim." \
		--with-integrity \
		--validate

demo-enforcement-behavioral:
	$(PYTHON) demos/enforcement_behavioral/scripts/run_demo.py


quickstart-ts:
	node dropins/aicp-core/typescript/scripts/generate_minimal_core_transcript.mjs --out out/quickstart/ts/minimal_core.jsonl
	$(PYTHON) sandbox/run.py out/quickstart/ts/minimal_core.jsonl --no-signature-verify

quickstart-py:
	$(PYTHON) dropins/aicp-core/python/generate_minimal_core_transcript.py --out out/quickstart/py/minimal_core.jsonl
	$(PYTHON) sandbox/run.py out/quickstart/py/minimal_core.jsonl --no-signature-verify

quickstart-core-v02-py:
	$(PYTHON) dropins/aicp-core-v0.2/python/generate_exact_contract_transcript.py --out out/quickstart/core-v02-py/exact_contract.jsonl
	$(PYTHON) scripts/validate_core_v02_transcript.py out/quickstart/core-v02-py/exact_contract.jsonl

quickstart-core-v02-ts:
	node dropins/aicp-core-v0.2/typescript/scripts/generate_exact_contract_transcript.mjs --out out/quickstart/core-v02-ts/exact_contract.jsonl
	$(PYTHON) scripts/validate_core_v02_transcript.py out/quickstart/core-v02-ts/exact_contract.jsonl

quickstart-capneg-v02-py:
	$(PYTHON) reference/python/aicp_ref_capneg_v02/quickstart.py --out out/quickstart/capneg-v02-py/profile-composition.jsonl
	$(PYTHON) scripts/validate_capneg_v02_transcript.py out/quickstart/capneg-v02-py/profile-composition.jsonl

quickstart-capneg-v02-ts:
	node sdk/typescript/scripts/generate_capneg_v02_quickstart.mjs --out out/quickstart/capneg-v02-ts/profile-composition.jsonl
	$(PYTHON) scripts/validate_capneg_v02_transcript.py out/quickstart/capneg-v02-ts/profile-composition.jsonl

template-smoke:
	$(PYTHON) -c "from pathlib import Path; Path('out/template-ts-agent').mkdir(parents=True, exist_ok=True); Path('out/template-protocol-adapter').mkdir(parents=True, exist_ok=True)"
	node templates/ts-agent/agent.js > out/template-ts-agent/thread.jsonl
	$(PYTHON) sandbox/run.py out/template-ts-agent/thread.jsonl --no-signature-verify
	$(PYTHON) templates/protocol-adapter/adapter.py fixtures/golden_transcripts/GT-01_happy_path_signed.jsonl > out/template-protocol-adapter/events.json

uat-check:
	$(MAKE) validate
	$(MAKE) conformance
	$(MAKE) conformance-bindings
	$(MAKE) conformance-profiles
	$(PYTHON) scripts/validate_interop_submission_examples.py
	$(PYTHON) scripts/validate_interop_submissions.py
	$(PYTHON) scripts/review_interop_submission.py interop/submissions/

prepr:
	$(MAKE) validate
	$(MAKE) conformance-all
	$(MAKE) test
	$(MAKE) quickstart-py
	$(MAKE) quickstart-ts
	$(MAKE) quickstart-core-v02-py
	$(MAKE) quickstart-core-v02-ts
	$(MAKE) quickstart-capneg-v02-py
	$(MAKE) quickstart-capneg-v02-ts
	$(MAKE) template-smoke
	$(MAKE) conformance-iut-smoke
	$(MAKE) evidence-targets-validate
	$(MAKE) evidence-capability-smoke-reference
	$(MAKE) evidence-capability-full-reference
	$(MAKE) evidence-capability-full-external-test
	$(MAKE) evidence-profile-mediated-smoke-reference
	$(MAKE) evidence-profile-mediated-full-reference
	$(MAKE) evidence-profile-mediated-full-external-test
	$(MAKE) evidence-profile-resumable-smoke-reference
	$(MAKE) evidence-profile-resumable-full-reference
	$(MAKE) evidence-profile-resumable-full-external-test
	$(MAKE) evidence-profile-delegated-smoke-reference
	$(MAKE) evidence-profile-delegated-full-reference
	$(MAKE) evidence-profile-delegated-full-external-test
	$(MAKE) live-binding-http-smoke-reference
	$(MAKE) live-binding-http-full-reference
	$(MAKE) live-binding-http-full-external-test
	$(MAKE) live-binding-mcp-smoke-reference
	$(MAKE) live-binding-mcp-full-reference
	$(MAKE) live-binding-mcp-full-external-test
	$(MAKE) evidence-binding-examples
	$(MAKE) evidence-submission-examples
	cd sdk/typescript && npm ci && npm test

compatibility-gate:
	$(MAKE) validate
	$(MAKE) conformance-all
	$(MAKE) evidence-targets-validate
	$(MAKE) live-binding-http-full-reference
	$(MAKE) live-binding-mcp-full-reference
	$(MAKE) evidence-binding-examples
	$(MAKE) snapshot

release-gate:
	$(MAKE) compatibility-gate
	$(MAKE) test
	$(MAKE) release-check

lint:
	$(PYTHON) scripts/check_naming.py
	$(PYTHON) scripts/check_terms.py
	$(PYTHON) scripts/check_no_binary_changes.py
	$(MAKE) release-check

release-check:
	$(PYTHON) scripts/validate_release_metadata.py
	$(PYTHON) -c "from pathlib import Path; req=['VERSION','RELEASE_NOTES.md','CHANGELOG.md','SECURITY.md','CONTRIBUTING.md','CODE_OF_CONDUCT.md','docs/core/AICP_Core_v0.1_Normative.md','schemas/core/aicp-core-message.schema.json','schemas/core/aicp-core-contract.schema.json','schemas/core/aicp-core-payloads.schema.json','fixtures/core_tv.json','fixtures/golden_transcripts/GT-01_happy_path_signed.jsonl','fixtures/golden_transcripts/GT-02_conflict_choose_signed.jsonl','fixtures/keys/GT_public_keys.json','sdk/typescript/package.json','sdk/typescript/package-lock.json']; missing=[p for p in req if not Path(p).exists()]; print('All required release hygiene and canonical Core artifacts are present.' if not missing else 'Missing required files: ' + ', '.join(missing)); raise SystemExit(1 if missing else 0)"
clean:
	rm -f conformance/report.json conformance/report_core_numeric_guardrails.json conformance/report_ext_capneg.json conformance/report_ext_confidentiality.json conformance/report_ext_redaction.json conformance/report_ext_human_approval.json conformance/report_ext_disputes.json conformance/report_ext_security_alerts.json conformance/report_ext_participants.json conformance/report_ext_tool_gating.json conformance/report_ext_identity_lc.json conformance/report_ext_delegation.json conformance/report_ext_workflow_sync.json conformance/report_ext_object_resync.json conformance/report_ext_policy_eval.json conformance/report_ext_enforcement.json conformance/report_ext_alerts.json conformance/report_ext_resume.json conformance/report_ext_delegated_identity.json conformance/report_ext_reception_chat_semantics.json conformance/report_ext_economics.json conformance/report_ext_admission.json conformance/report_ext_queue_leases.json conformance/report_ext_facilitation.json conformance/report_ext_channels.json conformance/report_ext_subscriptions.json conformance/report_ext_publications.json conformance/report_ext_inbox.json conformance/report_ext_marketplace.json conformance/report_ext_provenance.json conformance/report_ext_action_escrow.json conformance/report_ext_responsibility.json conformance/report_ext_trust_attestations.json conformance/report_ext_observability.json conformance/report_ext_enterprise_bindings.json conformance/report_ext_status_channel.json conformance/report_ext_execution_lifecycle.json conformance/report_bind_mcp.json conformance/report_bind_http_ws.json conformance/report_profile_base.json conformance/report_profile_mediated_blocking.json conformance/report_profile_mediated_blocking_ops.json conformance/report_profile_resumable_sessions.json conformance/report_profile_reception_chat.json conformance/report_profile_delegated_identity.json conformance/report_profile_workflow_orchestration_delegation.json conformance/report_profile_bazaar_reception.json conformance/report_profile_agent_media.json conformance/report_profile_execution_interop.json conformance/report_profile_policy_opa_rego.json conformance/report_profile_policy_abac_rbac.json conformance/report_profile_policy_llm_safety.json conformance/report_demo_enforcement_behavioral.json conformance/report_ops_hardening.json conformance/report_security_signed_path.json
