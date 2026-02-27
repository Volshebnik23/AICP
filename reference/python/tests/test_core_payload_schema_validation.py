from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "conformance/runner/aicp_conformance_runner.py"


def test_core_suite_conformance_passes_with_payload_schema() -> None:
    report = "conformance/report_core_payload_test.json"
    cmd = [
        sys.executable,
        str(RUNNER),
        "--suite",
        "conformance/core/CT_CORE_0.1.json",
        "--out",
        report,
    ]
    result = subprocess.run(cmd, cwd=ROOT, check=False)
    try:
        assert result.returncode == 0
    finally:
        (ROOT / report).unlink(missing_ok=True)


def test_core_payload_negative_missing_required_field() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    Draft202012Validator = jsonschema.Draft202012Validator

    suite = json.loads((ROOT / "conformance/core/CT_CORE_0.1.json").read_text(encoding="utf-8"))
    payload_schema = json.loads((ROOT / suite["payload_schema_ref"]).read_text(encoding="utf-8"))
    ptr = suite["payload_schema_map"]["ATTEST_ACTION"]

    transcript = (ROOT / "fixtures/golden_transcripts/GT-01_happy_path_signed.jsonl").read_text(encoding="utf-8").splitlines()
    attest_msg = json.loads(transcript[2])
    bad_payload = dict(attest_msg["payload"])
    bad_payload.pop("action_id", None)

    pointer = ptr[1:] if ptr.startswith("#") else ptr
    wrapper = {
        "$schema": payload_schema.get("$schema"),
        "$id": payload_schema.get("$id"),
        "$ref": f"#{pointer}" if pointer else "#",
        "$defs": payload_schema.get("$defs", {}),
    }
    errs = list(Draft202012Validator(wrapper).iter_errors(bad_payload))
    assert errs, "Expected payload schema validation error when required field is missing"


def test_core_payload_negative_reports_ct_payload_schema_check(tmp_path: Path) -> None:
    pytest.importorskip("jsonschema")

    bad_message = {
        "session_id": "s-neg-1",
        "message_id": "m-neg-1",
        "timestamp": "2026-01-01T00:00:00Z",
        "sender": "agent:A",
        "message_type": "ATTEST_ACTION",
        "payload": {
            "action_type": "share_profile",
            "consent_ref": "consent:neg"
        }
    }

    transcript_path = tmp_path / "neg_core_payload.jsonl"
    transcript_path.write_text(json.dumps(bad_message) + "\n", encoding="utf-8")

    suite = {
        "suite_id": "CT-CORE-PAYLOAD-NEG",
        "suite_version": "0.1.0-dev",
        "aicp_version": "0.1",
        "description": "negative payload schema check",
        "schema_ref": str((ROOT / "schemas/core/aicp-core-message.schema.json").resolve()),
        "payload_schema_ref": str((ROOT / "schemas/core/aicp-core-payloads.schema.json").resolve()),
        "payload_schema_map": {
            "ATTEST_ACTION": "#/$defs/ATTEST_ACTION"
        },
        "payload_schema_check_id": "CT-PAYLOAD-SCHEMA-01",
        "transcripts": [
            {
                "id": "NEG-ATTEST-ACTION",
                "path": str(transcript_path.resolve()),
                "expected_message_types": ["ATTEST_ACTION"]
            }
        ],
        "checks": [
            {"test_id": "CT-SCHEMA-JSONL-01", "description": "core schema"},
            {"test_id": "CT-PAYLOAD-SCHEMA-01", "description": "payload schema"},
            {"test_id": "CT-INVARIANTS-01", "description": "invariants"},
            {"test_id": "CT-SEQUENCE-01", "description": "sequence"},
            {"test_id": "CT-MESSAGE-HASH-01", "description": "hash"}
        ]
    }

    suite_path = tmp_path / "neg_core_payload_suite.json"
    suite_path.write_text(json.dumps(suite), encoding="utf-8")
    report_path = tmp_path / "neg_core_payload_report.json"

    cmd = [
        sys.executable,
        str(RUNNER),
        "--suite",
        str(suite_path.resolve()),
        "--out",
        str(report_path.resolve()),
    ]
    result = subprocess.run(cmd, cwd=ROOT, check=False)
    assert result.returncode != 0

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert any(f.get("test_id") == "CT-PAYLOAD-SCHEMA-01" for f in report.get("failures", []))
