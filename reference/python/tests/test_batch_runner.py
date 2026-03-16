from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
BATCH_RUNNER = ROOT / "conformance/runner/aicp_batch_runner.py"


def test_batch_runner_emits_reports_and_pass_status() -> None:
    out1 = ROOT / "conformance/report_ext_capneg_batch_test.json"
    out2 = ROOT / "conformance/report_ext_redaction_batch_test.json"

    cmd = [
        sys.executable,
        str(BATCH_RUNNER),
        "--suite-out",
        "conformance/extensions/CN_CAPNEG_0.1.json::conformance/report_ext_capneg_batch_test.json",
        "--suite-out",
        "conformance/extensions/RD_REDACTION_0.1.json::conformance/report_ext_redaction_batch_test.json",
    ]
    result = subprocess.run(cmd, cwd=ROOT, check=False, capture_output=True, text=True)
    try:
        assert result.returncode == 0
        assert out1.exists()
        assert out2.exists()

        r1 = json.loads(out1.read_text(encoding="utf-8"))
        r2 = json.loads(out2.read_text(encoding="utf-8"))
        assert r1["passed"] is True
        assert r2["passed"] is True
        assert "Conformance PASSED" in result.stdout
    finally:
        out1.unlink(missing_ok=True)
        out2.unlink(missing_ok=True)
