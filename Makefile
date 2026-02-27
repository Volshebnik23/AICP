PYTHON ?= python

.PHONY: validate test conformance conformance-ext conformance-bindings conformance-all lint release-check clean

validate:
	$(PYTHON) scripts/validate_json.py
	$(PYTHON) scripts/validate_jsonl.py
	$(PYTHON) scripts/validate_schema_instances.py
	$(PYTHON) scripts/validate_registry.py
	$(PYTHON) scripts/check_naming.py
	$(PYTHON) scripts/check_terms.py
	$(PYTHON) scripts/check_no_binary_changes.py

test:
	$(PYTHON) -c "import importlib.util, subprocess, sys; spec=importlib.util.find_spec('pytest'); raise SystemExit((print('pytest not installed; skipping make test.') or 0) if spec is None else subprocess.call(['pytest','-q','reference/python/tests']))"

conformance:
	$(PYTHON) conformance/runner/aicp_conformance_runner.py --suite conformance/core/CT_CORE_0.1.json --out conformance/report.json

conformance-ext:
	$(PYTHON) conformance/runner/aicp_conformance_runner.py --suite conformance/extensions/CN_CAPNEG_0.1.json --out conformance/report_ext_capneg.json
	$(PYTHON) conformance/runner/aicp_conformance_runner.py --suite conformance/extensions/OR_OBJECT_RESYNC_0.1.json --out conformance/report_ext_object_resync.json
	$(PYTHON) conformance/runner/aicp_conformance_runner.py --suite conformance/extensions/PE_POLICY_EVAL_0.1.json --out conformance/report_ext_policy_eval.json

conformance-bindings:
	$(PYTHON) conformance/runner/aicp_conformance_runner.py --suite conformance/bindings/TB_MCP_0.1.json --out conformance/report_bind_mcp.json

conformance-all:
	$(MAKE) conformance
	$(MAKE) conformance-ext
	$(MAKE) conformance-bindings

lint:
	@echo "Lint target placeholder: no lint checks configured."

release-check:
	$(PYTHON) -c "from pathlib import Path; req=['VERSION','RELEASE_NOTES.md','SECURITY.md','CONTRIBUTING.md','CODE_OF_CONDUCT.md','docs/core/AICP_Core_v0.1_Normative.md','schemas/core/aicp-core-message.schema.json','schemas/core/aicp-core-contract.schema.json','schemas/core/aicp-core-payloads.schema.json','fixtures/core_tv.json','fixtures/golden_transcripts/GT-01_happy_path_signed.jsonl','fixtures/golden_transcripts/GT-02_conflict_choose_signed.jsonl','fixtures/keys/GT_public_keys.json']; missing=[p for p in req if not Path(p).exists()]; print('All required release hygiene and canonical Core artifacts are present.' if not missing else 'Missing required files: ' + ', '.join(missing)); raise SystemExit(1 if missing else 0)"

clean:
	rm -f conformance/report.json conformance/report_ext_capneg.json conformance/report_ext_object_resync.json conformance/report_ext_policy_eval.json conformance/report_bind_mcp.json
