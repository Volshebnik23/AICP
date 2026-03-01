from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "conformance/runner/aicp_conformance_runner.py"
SUITE_PATH = ROOT / "conformance/extensions/PA_PARTICIPANTS_0.1.json"


def _run_suite(suite: Path, report: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(RUNNER), "--suite", str(suite), "--out", str(report)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_participants_suite_passes() -> None:
    report = ROOT / "conformance/report_ext_participants_test.json"
    result = _run_suite(SUITE_PATH, report)
    assert result.returncode == 0, result.stdout + result.stderr

    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["passed"] is True
    assert "AICP-EXT-PARTICIPANTS-0.1" in payload.get("compatibility_marks", [])
    report.unlink(missing_ok=True)


def test_participants_negative_fixture_triggers_pa_mem(tmp_path: Path) -> None:
    base_suite = json.loads(SUITE_PATH.read_text(encoding="utf-8"))
    tmp_suite = {
        "suite_id": "TMP-PA-NEG-01",
        "suite_version": "0.1.0-dev",
        "aicp_version": "0.1",
        "description": "Temporary suite for PA-MEM-01 assertion.",
        "schema_ref": base_suite["schema_ref"],
        "payload_schema_ref": base_suite["payload_schema_ref"],
        "payload_schema_map": base_suite["payload_schema_map"],
        "transcripts": [
            {
                "id": "TMP-PA-03",
                "path": "fixtures/extensions/participants/PA-03_message_before_accept_expected_fail.jsonl",
                "expected_message_types": [
                    "CONTRACT_PROPOSE",
                    "CONTRACT_ACCEPT",
                    "PARTICIPANT_JOIN",
                    "ATTEST_ACTION",
                    "PARTICIPANT_ACCEPT"
                ]
            }
        ],
        "checks": base_suite["checks"],
    }
    suite_path = tmp_path / "tmp_pa_neg.json"
    suite_path.write_text(json.dumps(tmp_suite, indent=2) + "\n", encoding="utf-8")

    report = ROOT / "conformance/report_ext_participants_tmp_neg.json"
    result = _run_suite(suite_path, report)
    assert result.returncode == 1

    payload = json.loads(report.read_text(encoding="utf-8"))
    assert any(failure.get("test_id") == "PA-MEM-01" for failure in payload.get("failures", []))
    report.unlink(missing_ok=True)
