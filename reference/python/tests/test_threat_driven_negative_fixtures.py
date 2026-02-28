from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "conformance/runner/aicp_conformance_runner.py"


def _run_suite_path(suite_path: Path, report_path: Path) -> tuple[int, dict]:
    cmd = [sys.executable, str(RUNNER), "--suite", str(suite_path), "--out", str(report_path)]
    result = subprocess.run(cmd, cwd=ROOT, check=False, capture_output=True, text=True)
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    return result.returncode, payload


def test_capneg_suite_with_expected_fail_still_passes() -> None:
    report = ROOT / "conformance/report_ext_capneg_neg_test.json"
    code, payload = _run_suite_path(ROOT / "conformance/extensions/CN_CAPNEG_0.1.json", report)
    report.unlink(missing_ok=True)
    assert code == 0
    assert payload["passed"] is True


def test_resume_suite_with_expected_fail_still_passes() -> None:
    report = ROOT / "conformance/report_ext_resume_neg_test.json"
    code, payload = _run_suite_path(ROOT / "conformance/extensions/RS_RESUME_0.1.json", report)
    report.unlink(missing_ok=True)
    assert code == 0
    assert payload["passed"] is True


def test_cn_downgrade_rule_triggers_on_negative_fixture(tmp_path: Path) -> None:
    suite = {
        "suite_id": "TMP-CN-DOWNGRADE-0.1",
        "suite_version": "0.1.0-dev",
        "aicp_version": "0.1",
        "description": "Temporary suite to assert CN-DOWNGRADE-01 behavior.",
        "schema_ref": "schemas/core/aicp-core-message.schema.json",
        "payload_schema_ref": "schemas/extensions/ext-capneg-payloads.schema.json",
        "payload_schema_map": {
            "CAPABILITIES_DECLARE": "/$defs/CAPABILITIES_DECLARE",
            "CAPABILITIES_PROPOSE": "/$defs/CAPABILITIES_PROPOSE",
            "CAPABILITIES_ACCEPT": "/$defs/CAPABILITIES_ACCEPT"
        },
        "transcripts": [
            {
                "id": "TMP-CN-NEG-01",
                "path": "fixtures/extensions/capneg/CN-NEG-01_downgrade_attempt_expected_fail.jsonl",
                "expected_message_types": [
                    "CAPABILITIES_DECLARE",
                    "CAPABILITIES_PROPOSE",
                    "CAPABILITIES_ACCEPT",
                    "CAPABILITIES_PROPOSE"
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
            {"test_id": "CN-DOWNGRADE-01"}
        ]
    }
    suite_path = tmp_path / "tmp_cn_suite.json"
    report_path = tmp_path / "tmp_cn_report.json"
    suite_path.write_text(json.dumps(suite, indent=2) + "\n", encoding="utf-8")

    code, payload = _run_suite_path(suite_path, report_path)
    assert code == 1
    assert payload["passed"] is False
    assert any(f["test_id"] == "CN-DOWNGRADE-01" for f in payload.get("failures", []))


def test_rs_loop_rule_triggers_on_negative_fixture(tmp_path: Path) -> None:
    suite = {
        "suite_id": "TMP-RS-LOOP-0.1",
        "suite_version": "0.1.0-dev",
        "aicp_version": "0.1",
        "description": "Temporary suite to assert RS-LOOP-01 behavior.",
        "schema_ref": "schemas/core/aicp-core-message.schema.json",
        "payload_schema_ref": "schemas/extensions/ext-resume-payloads.schema.json",
        "payload_schema_map": {
            "RESUME_REQUEST": "#/$defs/RESUME_REQUEST",
            "RESUME_RESPONSE": "#/$defs/RESUME_RESPONSE"
        },
        "transcripts": [
            {
                "id": "TMP-RS-NEG-01",
                "path": "fixtures/extensions/resume/RS-NEG-01_forced_resync_loop_expected_fail.jsonl",
                "expected_message_types": [
                    "CONTRACT_PROPOSE",
                    "CONTRACT_ACCEPT",
                    "ATTEST_ACTION",
                    "RESUME_REQUEST",
                    "RESUME_RESPONSE",
                    "RESUME_REQUEST",
                    "RESUME_RESPONSE",
                    "RESUME_REQUEST",
                    "RESUME_RESPONSE"
                ]
            }
        ],
        "checks": [
            {"test_id": "CT-SCHEMA-JSONL-01"},
            {"test_id": "CN-PAYLOAD-SCHEMA-01"},
            {"test_id": "CT-HASH-CHAIN-01"},
            {"test_id": "CT-INVARIANTS-01"},
            {"test_id": "CT-MESSAGE-HASH-01"},
            {"test_id": "RS-RESUME-MATCH-01"},
            {"test_id": "RS-ACTIONS-01"},
            {"test_id": "RS-LOOP-01"}
        ]
    }
    suite_path = tmp_path / "tmp_rs_suite.json"
    report_path = tmp_path / "tmp_rs_report.json"
    suite_path.write_text(json.dumps(suite, indent=2) + "\n", encoding="utf-8")

    code, payload = _run_suite_path(suite_path, report_path)
    assert code == 1
    assert payload["passed"] is False
    assert any(f["test_id"] == "RS-LOOP-01" for f in payload.get("failures", []))
