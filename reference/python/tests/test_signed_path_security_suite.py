from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from aicp_ref.signatures import signature_verifier_available


ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "conformance/runner/aicp_conformance_runner.py"
SUITE = "conformance/security/SIG_SIGNED_PATHS_0.1.json"


def _run_suite(suite: Path, report: Path) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(RUNNER), "--suite", str(suite), "--out", str(report)]
    return subprocess.run(cmd, cwd=ROOT, check=False, capture_output=True, text=True)


def test_signed_path_security_suite_passes() -> None:
    report = ROOT / "conformance/report_security_signed_path_test.json"
    result = _run_suite(ROOT / SUITE, report)
    assert result.returncode == 0, result.stdout + result.stderr

    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["passed"] is True
    assert "AICP-SECURITY-SIGNED-PATH-0.1" in payload.get("compatibility_marks", []) or payload.get("degraded")

    if signature_verifier_available():
        assert payload.get("degraded") is False

    report.unlink(missing_ok=True)
