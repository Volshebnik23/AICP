from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "conformance/runner/aicp_conformance_runner.py"
SUITE_PATH = ROOT / "conformance/extensions/ID_IDENTITY_LC_0.1.json"


def _run_suite(suite: Path, report: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(RUNNER), "--suite", str(suite), "--out", str(report)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_identity_lc_suite_passes() -> None:
    report = ROOT / "conformance/report_ext_identity_lc_test.json"
    result = _run_suite(SUITE_PATH, report)
    assert result.returncode == 0, result.stdout + result.stderr

    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["passed"] is True
    assert "AICP-EXT-IDENTITY-LC-0.1" in payload.get("compatibility_marks", [])
    report.unlink(missing_ok=True)


def test_identity_lc_negative_fixture_triggers_revoke(tmp_path: Path) -> None:
    base_suite = json.loads(SUITE_PATH.read_text(encoding="utf-8"))
    suite_obj = {
        "suite_id": "TMP-ID-NEG-01",
        "suite_version": "0.1.0-dev",
        "aicp_version": "0.1",
        "description": "Temporary suite for ID-REVOKE-01 assertion.",
        "schema_ref": base_suite["schema_ref"],
        "payload_schema_ref": base_suite["payload_schema_ref"],
        "payload_schema_map": base_suite["payload_schema_map"],
        "transcripts": [
            {
                "id": "TMP-IL-03",
                "path": "fixtures/extensions/identity_lc/IL-03_revoke_then_use_revoked_key_expected_fail.jsonl",
                "expected_message_types": [
                    "CONTRACT_PROPOSE",
                    "CONTRACT_ACCEPT",
                    "IDENTITY_ANNOUNCE",
                    "KEY_ROTATION",
                    "KEY_REVOKE",
                    "CONTEXT_AMEND"
                ]
            }
        ],
        "checks": base_suite["checks"],
    }
    suite_path = tmp_path / "tmp_id_neg.json"
    suite_path.write_text(json.dumps(suite_obj, indent=2) + "\n", encoding="utf-8")
    report = ROOT / "conformance/report_ext_identity_lc_tmp_neg.json"

    result = _run_suite(suite_path, report)
    assert result.returncode == 1
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert any(failure.get("test_id") == "ID-REVOKE-01" for failure in payload.get("failures", []))
    report.unlink(missing_ok=True)
