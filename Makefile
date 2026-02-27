PYTHON ?= python

.PHONY: validate test lint release-check

validate:
	$(PYTHON) scripts/validate_json.py
	$(PYTHON) scripts/validate_jsonl.py
	$(PYTHON) scripts/validate_schema_instances.py
	$(PYTHON) scripts/validate_registry.py

test:
	$(PYTHON) -c "from pathlib import Path; import subprocess, sys; tests = list(Path('.').rglob('test_*.py')); raise SystemExit(subprocess.call(['pytest', '-q']) if tests else (print('No pytest tests found; skipping.') or 0))"

lint:
	@echo "Lint target placeholder: no lint checks configured."

release-check:
	$(PYTHON) -c "from pathlib import Path; req=['VERSION','RELEASE_NOTES.md','SECURITY.md','CONTRIBUTING.md','CODE_OF_CONDUCT.md','docs/core/AICP_Core_v0.1_Normative_0.1.0.docx','schemas/core/aicp-core-message.schema.json','schemas/core/aicp-core-contract.schema.json','schemas/core/aicp-core-payloads.schema.json','fixtures/core_tv.json','fixtures/golden_transcripts/GT-01_happy_path_signed.jsonl','fixtures/golden_transcripts/GT-02_conflict_choose_signed.jsonl','fixtures/keys/GT_public_keys.json']; missing=[p for p in req if not Path(p).exists()]; print('All required release hygiene and canonical Core artifacts are present.' if not missing else 'Missing required files: ' + ', '.join(missing)); raise SystemExit(1 if missing else 0)"
