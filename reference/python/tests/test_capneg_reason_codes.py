from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "conformance/runner/aicp_conformance_runner.py"


def _run_suite(suite: Path, report: Path) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(RUNNER), "--suite", str(suite), "--out", str(report)]
    return subprocess.run(cmd, cwd=ROOT, check=False, capture_output=True, text=True)


def test_cn_reason_codes_check_enforced(tmp_path: Path) -> None:
    suite = {
        "suite_id": "TMP-CN-REASON-CODES-0.1",
        "suite_version": "0.1.0-dev",
        "aicp_version": "0.1",
        "description": "Temporary suite to assert CN-REASON-CODES-01 behavior.",
        "schema_ref": "schemas/core/aicp-core-message.schema.json",
        "payload_schema_ref": "schemas/extensions/ext-capneg-payloads.schema.json",
        "payload_schema_map": {
            "CAPABILITIES_DECLARE": "/$defs/CAPABILITIES_DECLARE",
            "CAPABILITIES_PROPOSE": "/$defs/CAPABILITIES_PROPOSE",
            "CAPABILITIES_REJECT": "/$defs/CAPABILITIES_REJECT"
        },
        "transcripts": [
            {
                "id": "TMP-CN-06",
                "path": "fixtures/extensions/capneg/CN-06_profile_downgrade_attempt_expected_fail.jsonl",
                "expected_message_types": [
                    "CAPABILITIES_DECLARE",
                    "CAPABILITIES_DECLARE",
                    "CAPABILITIES_PROPOSE",
                    "CAPABILITIES_REJECT"
                ]
            }
        ],
        "checks": [
            {"test_id": "CT-SCHEMA-JSONL-01"},
            {"test_id": "CN-PAYLOAD-SCHEMA-01"},
            {"test_id": "CT-HASH-CHAIN-01"},
            {"test_id": "CT-INVARIANTS-01"},
            {"test_id": "CT-SEQUENCE-01"},
            {"test_id": "CT-MESSAGE-HASH-01"},
            {"test_id": "CN-REASON-CODES-01"}
        ]
    }
    suite_path = tmp_path / "tmp_capneg_reason_suite.json"
    suite_path.write_text(json.dumps(suite, indent=2) + "\n", encoding="utf-8")
    report = ROOT / "conformance/report_tmp_capneg_reason_codes.json"

    result = _run_suite(suite_path, report)
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["passed"] is True
    report.unlink(missing_ok=True)
