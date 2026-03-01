from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "conformance/runner/aicp_conformance_runner.py"
SUITE_PATH = ROOT / "conformance/extensions/TG_TOOL_GATING_0.1.json"


def _run_suite(suite: Path, report: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(RUNNER), "--suite", str(suite), "--out", str(report)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_tool_gating_suite_passes() -> None:
    report = ROOT / "conformance/report_ext_tool_gating_test.json"
    result = _run_suite(SUITE_PATH, report)
    assert result.returncode == 0, result.stdout + result.stderr

    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["passed"] is True
    assert "AICP-EXT-TOOL-GATING-0.1" in payload.get("compatibility_marks", [])
    report.unlink(missing_ok=True)


def test_tool_gating_expected_failures_trigger_tg_mode(tmp_path: Path) -> None:
    base_suite = json.loads(SUITE_PATH.read_text(encoding="utf-8"))
    checks = base_suite["checks"]
    required = [
        "fixtures/extensions/tool_gating/TG-03_blocking_result_without_allow_expected_fail.jsonl",
        "fixtures/extensions/tool_gating/TG-04_audit_missing_attest_expected_fail.jsonl",
    ]
    for idx, transcript in enumerate(required, start=1):
        suite_obj = {
            "suite_id": f"TMP-TG-{idx}",
            "suite_version": "0.1.0-dev",
            "aicp_version": "0.1",
            "description": "Temporary suite for TG-MODE-01 assertions.",
            "schema_ref": base_suite["schema_ref"],
            "payload_schema_ref": base_suite["payload_schema_ref"],
            "payload_schema_map": base_suite["payload_schema_map"],
            "transcripts": [{"id": f"TMP-{idx}", "path": transcript, "expected_message_types": []}],
            "checks": checks,
        }
        suite_path = tmp_path / f"tmp_tg_{idx}.json"
        suite_path.write_text(json.dumps(suite_obj, indent=2) + "\n", encoding="utf-8")
        report = ROOT / f"conformance/report_tmp_tg_{idx}.json"

        result = _run_suite(suite_path, report)
        assert result.returncode == 1
        payload = json.loads(report.read_text(encoding="utf-8"))
        assert any(failure.get("test_id") == "TG-MODE-01" for failure in payload.get("failures", []))
        report.unlink(missing_ok=True)
