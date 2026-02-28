from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "conformance/runner/aicp_conformance_runner.py"
SUITE = ROOT / "conformance/ops/OPS_HARDENING_0.1.json"


def test_ops_hardening_suite_passes_with_expected_failures() -> None:
    report_path = ROOT / "conformance/report_ops_hardening_test.json"
    result = subprocess.run(
        [sys.executable, str(RUNNER), "--suite", str(SUITE), "--out", str(report_path)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    data = json.loads(report_path.read_text(encoding="utf-8"))
    report_path.unlink(missing_ok=True)

    assert result.returncode == 0, result.stdout + result.stderr
    assert data["passed"] is True


def test_ops_hardening_expected_fail_transcripts_declared() -> None:
    suite = json.loads(SUITE.read_text(encoding="utf-8"))
    expected = {
        "OPS-01": "RS-PROBING-01",
        "OPS-02": "ENF-VERDICT-STORM-01",
        "OPS-03": "AL-VERBOSITY-01",
    }
    for transcript in suite.get("transcripts", []):
        tid = transcript.get("id")
        if tid not in expected:
            continue
        assert transcript.get("expect_pass") is False
        failures = {f.get("test_id"): f.get("min_count") for f in transcript.get("expected_failures", [])}
        assert failures.get(expected[tid], 0) >= 1
