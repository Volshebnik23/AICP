from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "conformance/runner/aicp_conformance_runner.py"


def test_binding_conformance_suite_passes() -> None:
    report = "conformance/report_bind_mcp_test.json"
    cmd = [
        sys.executable,
        str(RUNNER),
        "--suite",
        "conformance/bindings/TB_MCP_0.1.json",
        "--out",
        report,
    ]
    result = subprocess.run(cmd, cwd=ROOT, check=False)
    try:
        assert result.returncode == 0
    finally:
        (ROOT / report).unlink(missing_ok=True)
