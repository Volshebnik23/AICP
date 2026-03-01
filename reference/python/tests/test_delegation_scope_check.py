from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "conformance/runner/aicp_conformance_runner.py"
SUITE_PATH = ROOT / "conformance/extensions/DL_DELEGATION_0.1.json"


def test_delegation_scope_negative_fixture_triggers_scope_check(tmp_path: Path) -> None:
    base_suite = json.loads(SUITE_PATH.read_text(encoding="utf-8"))
    suite_obj = {
        "suite_id": "TMP-DL-SCOPE-01",
        "suite_version": "0.1.0-dev",
        "aicp_version": "0.1",
        "description": "Temporary delegation scope negative suite.",
        "schema_ref": base_suite["schema_ref"],
        "payload_schema_ref": base_suite["payload_schema_ref"],
        "payload_schema_map": base_suite["payload_schema_map"],
        "transcripts": [
            {
                "id": "TMP-DL-04",
                "path": "fixtures/extensions/delegation/DL-04_scope_not_subset_expected_fail.jsonl",
                "expected_message_types": []
            }
        ],
        "checks": base_suite["checks"],
    }
    suite_path = tmp_path / "tmp_dl_scope.json"
    suite_path.write_text(json.dumps(suite_obj, indent=2) + "\n", encoding="utf-8")
    report = ROOT / "conformance/report_tmp_dl_scope.json"

    result = subprocess.run(
        [sys.executable, str(RUNNER), "--suite", str(suite_path), "--out", str(report)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert any(failure.get("test_id") == "DL-SCOPE-01" for failure in payload.get("failures", []))
    report.unlink(missing_ok=True)
