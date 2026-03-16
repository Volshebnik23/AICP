from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "conformance/runner/aicp_conformance_runner.py"
CORE_SUITE = ROOT / "conformance/core/CT_CORE_0.1.json"


def test_core_conformance_runner_cli_passes(tmp_path: Path) -> None:
    out = tmp_path / "report_core_rtss.json"
    cmd = [sys.executable, str(RUNNER), "--suite", str(CORE_SUITE), "--out", str(out)]
    cp = subprocess.run(cmd, capture_output=True, text=True)
    assert cp.returncode == 0, cp.stdout + cp.stderr
    report = json.loads(out.read_text(encoding="utf-8"))
    assert report["passed"] is True
