from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "conformance/runner/aicp_conformance_runner.py"
SUITE = ROOT / "conformance/extensions/CN_CAPNEG_0.1.json"


def _run_suite(suite: Path, report: Path) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(RUNNER), "--suite", str(suite), "--out", str(report)]
    return subprocess.run(cmd, cwd=ROOT, check=False, capture_output=True, text=True)


def test_capneg_suite_passes_with_profile_negotiation_fixtures() -> None:
    report = ROOT / "conformance/report_ext_capneg_profile_negotiation_test.json"
    result = _run_suite(SUITE, report)
    assert result.returncode == 0, result.stdout + result.stderr

    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["passed"] is True
    report.unlink(missing_ok=True)


def test_capneg_profile_downgrade_negative_fixture_triggers_rule(tmp_path: Path) -> None:
    suite = {
        "suite_id": "TMP-CN-PROFILE-NEG-0.1",
        "suite_version": "0.1.0-dev",
        "aicp_version": "0.1",
        "description": "Temporary suite to assert CN-AICP-PROFILE-NEGOTIATION-01 behavior.",
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
            {"test_id": "CN-AICP-PROFILE-NEGOTIATION-01"}
        ]
    }
    suite_path = tmp_path / "tmp_capneg_profile_suite.json"
    suite_path.write_text(json.dumps(suite, indent=2) + "\n", encoding="utf-8")
    report = ROOT / "conformance/report_tmp_capneg_profile_negotiation.json"

    result = _run_suite(suite_path, report)
    assert result.returncode == 1

    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["passed"] is False
    assert any(f["test_id"] == "CN-AICP-PROFILE-NEGOTIATION-01" for f in payload.get("failures", []))
    report.unlink(missing_ok=True)


def test_selected_profile_exists_in_registry() -> None:
    registry = json.loads((ROOT / "registry/aicp_profiles.json").read_text(encoding="utf-8"))
    registry_set = {(e["profile_id"], e["profile_version"]) for e in registry}

    fixture = ROOT / "fixtures/extensions/capneg/CN-05_profile_agree_mediated_blocking_pass.jsonl"
    rows = [json.loads(line) for line in fixture.read_text(encoding="utf-8").splitlines() if line.strip()]
    propose = next(r for r in rows if r.get("message_type") == "CAPABILITIES_PROPOSE")
    selected = ((propose.get("payload") or {}).get("negotiation_result") or {}).get("selected", {}).get("aicp_profile", {})
    assert (selected.get("profile_id"), selected.get("profile_version")) in registry_set
