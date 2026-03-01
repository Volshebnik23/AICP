from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "conformance/runner/aicp_conformance_runner.py"
SUITE = "conformance/ops/OPS_HARDENING_0.1.json"


def _run_suite(suite: Path, report: Path) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(RUNNER), "--suite", str(suite), "--out", str(report)]
    return subprocess.run(cmd, cwd=ROOT, check=False, capture_output=True, text=True)


def test_ops_hardening_conformance_suite_passes() -> None:
    report = ROOT / "conformance/report_ops_hardening_test.json"
    result = _run_suite(ROOT / SUITE, report)
    assert result.returncode == 0, result.stdout + result.stderr

    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["passed"] is True
    assert "AICP-OPS-HARDENING-0.1" in payload.get("compatibility_marks", [])
    report.unlink(missing_ok=True)


def test_ops_expected_fail_transcripts_trigger_required_checks(tmp_path: Path) -> None:
    required = {
        "fixtures/ops/OPS-01_resume_probing_expected_fail.jsonl": "RS-PROBING-01",
        "fixtures/ops/OPS-02_verdict_storm_expected_fail.jsonl": "ENF-VERDICT-STORM-01",
        "fixtures/ops/OPS-03_alert_verbosity_expected_fail.jsonl": "AL-VERBOSITY-01",
    }

    base_suite = json.loads((ROOT / SUITE).read_text(encoding="utf-8"))
    checks = base_suite["checks"]

    for idx, (transcript, expected_test_id) in enumerate(required.items(), start=1):
        suite_obj = {
            "suite_id": f"TMP-OPS-{idx}",
            "suite_version": "0.1.0-dev",
            "aicp_version": "0.1",
            "description": "Temporary suite for expected-fail signal assertion.",
            "schema_ref": base_suite["schema_ref"],
            "payload_schema_ref": base_suite["payload_schema_ref"],
            "payload_schema_map": base_suite["payload_schema_map"],
            "transcripts": [
                {
                    "id": f"TMP-{idx}",
                    "path": transcript,
                    "expected_message_types": []
                }
            ],
            "checks": checks,
        }
        suite_path = tmp_path / f"tmp_ops_{idx}.json"
        suite_path.write_text(json.dumps(suite_obj, indent=2) + "\n", encoding="utf-8")
        report = ROOT / f"conformance/report_tmp_ops_{idx}.json"

        result = _run_suite(suite_path, report)
        assert result.returncode == 1
        payload = json.loads(report.read_text(encoding="utf-8"))
        assert any(f["test_id"] == expected_test_id for f in payload.get("failures", []))
        report.unlink(missing_ok=True)
