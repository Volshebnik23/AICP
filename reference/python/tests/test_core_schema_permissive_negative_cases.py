from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from aicp_ref.hashing import message_hash_from_body


ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "conformance/runner/aicp_conformance_runner.py"


def _write_message(path: Path, body: dict) -> None:
    path.write_text(json.dumps({**body, "message_hash": message_hash_from_body(body)}) + "\n", encoding="utf-8")


def _run_core_contract_suite(tmp_path: Path, transcript_path: Path) -> tuple[int, dict]:
    suite = {
        "suite_id": "TMP-CORE-CONTRACT-NEG-0.1",
        "suite_version": "0.1.0-dev",
        "aicp_version": "0.1",
        "description": "Temporary Core suite for schema-admissible but semantically invalid contract cases.",
        "schema_ref": "schemas/core/aicp-core-message.schema.json",
        "payload_schema_ref": "schemas/core/aicp-core-payloads.schema.json",
        "payload_schema_map": {"CONTRACT_PROPOSE": "#/$defs/CONTRACT_PROPOSE"},
        "payload_schema_check_id": "CT-PAYLOAD-SCHEMA-01",
        "transcripts": [
            {
                "id": "TMP-CORE-CONTRACT-NEG-01",
                "path": os.path.relpath(transcript_path, ROOT),
                "expected_message_types": ["CONTRACT_PROPOSE"],
            }
        ],
        "checks": [
            {"test_id": "CT-SCHEMA-JSONL-01"},
            {"test_id": "CT-PAYLOAD-SCHEMA-01"},
            {"test_id": "CT-MESSAGE-TYPE-REGISTRY-01"},
            {"test_id": "CT-SEQUENCE-01"},
            {"test_id": "CT-MESSAGE-HASH-01"},
            {"test_id": "CT-CONTRACT-SCHEMA-01"},
        ],
    }
    suite_path = tmp_path / "tmp_core_contract_suite.json"
    report_path = tmp_path / "tmp_core_contract_report.json"
    suite_path.write_text(json.dumps(suite, indent=2) + "\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(RUNNER), "--suite", str(suite_path), "--out", str(report_path)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    return result.returncode, payload


def test_core_conformance_rejects_empty_contract_id_even_if_schema_admits_it(tmp_path: Path) -> None:
    transcript_path = tmp_path / "core_empty_contract_id.jsonl"
    body = {
        "session_id": "s-core-neg-1",
        "message_id": "m1",
        "timestamp": "2026-03-23T00:00:00Z",
        "sender": "agent:A",
        "message_type": "CONTRACT_PROPOSE",
        "contract_id": "",
        "payload": {
            "contract": {
                "contract_id": "",
                "goal": "exercise schema-permissive/conformance-strict boundary",
                "roles": ["initiator"],
            }
        },
    }
    _write_message(transcript_path, body)

    code, payload = _run_core_contract_suite(tmp_path, transcript_path)

    assert code == 1
    assert payload["passed"] is False
    assert any(
        failure["test_id"] == "CT-CONTRACT-SCHEMA-01"
        and "contract.contract_id must be a non-empty string" in failure["message"]
        for failure in payload.get("failures", [])
    )


def test_core_conformance_rejects_envelope_payload_contract_id_mismatch(tmp_path: Path) -> None:
    transcript_path = tmp_path / "core_contract_id_mismatch.jsonl"
    body = {
        "session_id": "s-core-neg-2",
        "message_id": "m1",
        "timestamp": "2026-03-23T00:00:00Z",
        "sender": "agent:A",
        "message_type": "CONTRACT_PROPOSE",
        "contract_id": "contract-envelope",
        "payload": {
            "contract": {
                "contract_id": "contract-payload",
                "goal": "exercise envelope/payload binding invariant",
                "roles": ["initiator"],
            }
        },
    }
    _write_message(transcript_path, body)

    code, payload = _run_core_contract_suite(tmp_path, transcript_path)

    assert code == 1
    assert payload["passed"] is False
    assert any(
        failure["test_id"] == "CT-CONTRACT-SCHEMA-01"
        and "envelope.contract_id must equal payload.contract.contract_id" in failure["message"]
        for failure in payload.get("failures", [])
    )
