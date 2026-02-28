from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "conformance/runner/aicp_conformance_runner.py"
SUITE = "conformance/demos/DEMO_ENFORCEMENT_BEHAVIORAL_0.1.json"


def _run_suite(suite: Path, report: Path) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(RUNNER), "--suite", str(suite), "--out", str(report)]
    return subprocess.run(cmd, cwd=ROOT, check=False, capture_output=True, text=True)


def test_demo_behavioral_conformance_suite_passes() -> None:
    report = ROOT / "conformance/report_demo_behavioral_test.json"
    result = _run_suite(ROOT / SUITE, report)
    assert result.returncode == 0, result.stdout + result.stderr

    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["passed"] is True
    assert "AICP-DEMO-ENFORCEMENT-BEHAVIORAL-0.1" in payload.get("compatibility_marks", [])
    report.unlink(missing_ok=True)


def test_enf_auth_detects_spoofed_verdict_sender(tmp_path: Path) -> None:
    suite_obj = {
        "suite_id": "TMP-ENF-AUTH-0.1",
        "suite_version": "0.1.0-dev",
        "aicp_version": "0.1",
        "description": "Temporary suite to assert ENF-AUTH-01 behavior.",
        "schema_ref": "schemas/core/aicp-core-message.schema.json",
        "payload_schema_ref": "schemas/demos/demo-enforcement-behavioral-payloads.schema.json",
        "payload_schema_map": {
            "CONTENT_MESSAGE": "#/$defs/CONTENT_MESSAGE",
            "ENFORCEMENT_VERDICT": "#/$defs/ENFORCEMENT_VERDICT",
            "CONTENT_DELIVER": "#/$defs/CONTENT_DELIVER"
        },
        "transcripts": [
            {
                "id": "TMP-01",
                "path": "fixtures/demos/enforcement_behavioral/07_spoofed_verdict_sender_expected_fail.jsonl",
                "expected_message_types": [
                    "CONTRACT_PROPOSE",
                    "CONTRACT_ACCEPT",
                    "CONTENT_MESSAGE",
                    "ENFORCEMENT_VERDICT",
                    "CONTENT_DELIVER"
                ]
            }
        ],
        "checks": [
            {"test_id": "CT-SCHEMA-JSONL-01"},
            {"test_id": "CN-PAYLOAD-SCHEMA-01"},
            {"test_id": "CT-HASH-CHAIN-01"},
            {"test_id": "CT-INVARIANTS-01"},
            {"test_id": "CT-MESSAGE-HASH-01"},
            {"test_id": "ENF-AUTH-01"}
        ]
    }
    suite_path = tmp_path / "tmp_enf_auth_suite.json"
    suite_path.write_text(json.dumps(suite_obj, indent=2) + "\n", encoding="utf-8")
    report = ROOT / "conformance/report_demo_enf_auth_negative_test.json"

    result = _run_suite(suite_path, report)
    assert result.returncode == 1

    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["passed"] is False
    assert any(f["test_id"] == "ENF-AUTH-01" for f in payload.get("failures", []))
    report.unlink(missing_ok=True)
