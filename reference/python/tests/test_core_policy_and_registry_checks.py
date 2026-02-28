from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "conformance/runner/aicp_conformance_runner.py"
CORE_SUITE = ROOT / "conformance/core/CT_CORE_0.1.json"


def test_core_suite_declares_new_anti_drift_checks() -> None:
    suite = json.loads(CORE_SUITE.read_text(encoding="utf-8"))
    check_ids = {c["test_id"] for c in suite.get("checks", [])}
    assert "CT-MESSAGE-TYPE-REGISTRY-01" in check_ids
    assert "CT-CONTRACT-SCHEMA-01" in check_ids
    assert "CT-POLICY-CATEGORIES-01" in check_ids


def test_core_suite_passes_with_structured_policies_and_registered_message_types() -> None:
    report = ROOT / "conformance/report_core_policy_registry_test.json"
    cmd = [
        sys.executable,
        str(RUNNER),
        "--suite",
        str(CORE_SUITE),
        "--out",
        str(report),
    ]
    result = subprocess.run(cmd, cwd=ROOT, check=False, capture_output=True, text=True)
    data = json.loads(report.read_text(encoding="utf-8"))
    report.unlink(missing_ok=True)

    assert result.returncode == 0, result.stdout + result.stderr
    assert data["passed"] is True
    failure_ids = {f["test_id"] for f in data.get("failures", [])}
    assert "CT-MESSAGE-TYPE-REGISTRY-01" not in failure_ids
    assert "CT-CONTRACT-SCHEMA-01" not in failure_ids
    assert "CT-POLICY-CATEGORIES-01" not in failure_ids
