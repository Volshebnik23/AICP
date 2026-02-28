from __future__ import annotations

import json
import subprocess
import tempfile
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "conformance/runner/aicp_profile_runner.py"


def _run_profile(profile: str, report: str) -> tuple[int, dict]:
    cmd = [
        sys.executable,
        str(RUNNER),
        "--profile",
        profile,
        "--out",
        report,
    ]
    result = subprocess.run(cmd, cwd=ROOT, check=False)
    report_path = ROOT / report
    data = json.loads(report_path.read_text(encoding="utf-8"))
    return result.returncode, data


def test_profile_conformance_catalogs_pass() -> None:
    cases = [
        (
            "conformance/profiles/PF_AICP_BASE_0.1.json",
            "conformance/report_profile_base_test.json",
            "AICP-Profile-BASE-0.1",
        ),
        (
            "conformance/profiles/PF_AICP_MEDIATED_BLOCKING_0.1.json",
            "conformance/report_profile_mediated_blocking_test.json",
            "AICP-Profile-MEDIATED-BLOCKING-0.1",
        ),
    ]

    for profile, report, expected_mark in cases:
        rc, data = _run_profile(profile, report)
        try:
            assert rc == 0, f"profile failed: {profile}"
            assert data["passed"] is True
            assert expected_mark in data["compatibility_marks"]
        finally:
            (ROOT / report).unlink(missing_ok=True)


def test_profile_runner_prints_absolute_path_when_outside_repo() -> None:
    with tempfile.TemporaryDirectory(prefix="aicp-profile-out-") as tmp:
        out_path = Path(tmp) / "profile_report.json"
        cmd = [
            sys.executable,
            str(RUNNER),
            "--profile",
            "conformance/profiles/PF_AICP_BASE_0.1.json",
            "--out",
            str(out_path),
        ]
        result = subprocess.run(cmd, cwd=ROOT, check=False, capture_output=True, text=True)
        try:
            assert result.returncode == 0
            assert str(out_path) in result.stdout
            assert out_path.exists()
            data = json.loads(out_path.read_text(encoding="utf-8"))
            assert data["passed"] is True
        finally:
            out_path.unlink(missing_ok=True)
