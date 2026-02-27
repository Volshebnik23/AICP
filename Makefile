PYTHON ?= python

.PHONY: validate test conformance lint release-check

validate:
	$(PYTHON) scripts/validate_json.py
	$(PYTHON) scripts/validate_jsonl.py
	$(PYTHON) scripts/validate_schema_instances.py
	$(PYTHON) scripts/validate_registry.py

test:
	$(PYTHON) -c "import importlib.util, subprocess, sys; spec=importlib.util.find_spec('pytest'); raise SystemExit((print('pytest not installed; skipping make test.') or 0) if spec is None else subprocess.call(['pytest','-q','reference/python/tests']))"

conformance:
	$(PYTHON) conformance/runner/aicp_conformance_runner.py --suite conformance/core/CT_CORE_0.1.json --out conformance/report.json

conformance:
	$(PYTHON) conformance/runner/aicp_conformance_runner.py --suite conformance/core/CT_CORE_0.1.json --out conformance/report.json

lint:
	@echo "Lint target placeholder: no lint checks configured."

release-check:
	$(PYTHON) -c "from pathlib import Path; req=['VERSION','RELEASE_NOTES.md','SECURITY.md','CONTRIBUTING.md','CODE_OF_CONDUCT.md','docs/core/AICP_Core_v0.1_Normative_0.1.0.docx','schemas/core/aicp-core-message.schema.json','schemas/core/aicp-core-contract.schema.json','schemas/core/aicp-core-payloads.schema.json','fixtures/core_tv.json','fixtures/golden_transcripts/GT-01_happy_path_signed.jsonl','fixtures/golden_transcripts/GT-02_conflict_choose_signed.jsonl','fixtures/keys/GT_public_keys.json']; missing=[p for p in req if not Path(p).exists()]; print('All required release hygiene and canonical Core artifacts are present.' if not missing else 'Missing required files: ' + ', '.join(missing)); raise SystemExit(1 if missing else 0)"
