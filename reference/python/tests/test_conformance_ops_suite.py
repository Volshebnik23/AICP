from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "conformance/runner/aicp_conformance_runner.py"
OPS_SUITE = ROOT / "conformance/ops/OPS_HARDENING_0.1.json"


def test_ops_hardening_suite_passes_with_expected_verbosity_failure_only() -> None:
    report = ROOT / "conformance/report_ops_hardening_test.json"
    cmd = [
        sys.executable,
        str(RUNNER),
        "--suite",
        str(OPS_SUITE),
        "--out",
        str(report),
    ]
    result = subprocess.run(cmd, cwd=ROOT, check=False, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    report.unlink(missing_ok=True)
