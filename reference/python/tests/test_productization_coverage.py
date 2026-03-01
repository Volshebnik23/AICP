from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_validate_productization_coverage_script_passes() -> None:
    script = ROOT / "scripts/validate_productization_coverage.py"
    result = subprocess.run([sys.executable, str(script)], cwd=ROOT, check=False, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_core_suite_maps_error_payload_and_fixture() -> None:
    suite = json.loads((ROOT / "conformance/core/CT_CORE_0.1.json").read_text(encoding="utf-8"))
    assert suite["payload_schema_map"].get("ERROR") == "#/$defs/ERROR"
    assert any(t.get("path") == "fixtures/golden_transcripts/GT-08_error_minimal.jsonl" for t in suite.get("transcripts", []))
