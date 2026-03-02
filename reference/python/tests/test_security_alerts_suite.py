from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "conformance/runner/aicp_conformance_runner.py"
SUITE_PATH = ROOT / "conformance/extensions/SA_SECURITY_ALERT_0.1.json"


def _run_suite(suite: Path, report: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, str(RUNNER), "--suite", str(suite), "--out", str(report)], cwd=ROOT, check=False, capture_output=True, text=True)


def test_security_alerts_suite_passes() -> None:
    report = ROOT / "conformance/report_ext_security_alerts_test.json"
    result = _run_suite(SUITE_PATH, report)
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["passed"] is True
    assert "AICP-EXT-SECURITY-ALERT-0.1" in payload.get("compatibility_marks", [])
    report.unlink(missing_ok=True)
