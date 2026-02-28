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


def test_core_message_schema_requires_contract_id() -> None:
    schema = json.loads((ROOT / "schemas/core/aicp-core-message.schema.json").read_text(encoding="utf-8"))
    required = set(schema.get("required", []))
    assert "contract_id" in required


def test_core_suite_declares_prev_msg_required_check_and_expected_fail_fixture() -> None:
    suite = json.loads(CORE_SUITE.read_text(encoding="utf-8"))
    check_ids = {c["test_id"] for c in suite.get("checks", [])}
    assert "CT-PREV-MSG-REQUIRED-01" in check_ids

    gt9 = next((tr for tr in suite.get("transcripts", []) if tr.get("id") == "GT-09"), None)
    assert gt9 is not None
    assert gt9.get("expect_pass") is False
    expected = {e.get("test_id"): e.get("min_count") for e in gt9.get("expected_failures", [])}
    assert expected.get("CT-PREV-MSG-REQUIRED-01") == 1
