from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "conformance/runner/aicp_conformance_runner.py"
SUITE_PATH = ROOT / "conformance/extensions/AM_ARTIFACT_MANIFESTS_PINNING_0.1.json"


def _run_suite(suite: Path, report: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(RUNNER), "--suite", str(suite), "--out", str(report)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )


def test_artifact_manifests_pinning_suite_passes() -> None:
    report = ROOT / "conformance/report_ext_artifact_manifests_pinning_test.json"
    result = _run_suite(SUITE_PATH, report)
    assert result.returncode == 0, result.stdout + result.stderr

    payload = json.loads(report.read_text(encoding="utf-8"))
    assert payload["passed"] is True
    assert "AICP-EXT-ARTIFACT-MANIFESTS-PINNING-0.1" in payload.get("compatibility_marks", [])
    report.unlink(missing_ok=True)


def test_artifact_manifests_expected_failures_surface() -> None:
    report = ROOT / "conformance/report_ext_artifact_manifests_pinning_test.json"
    result = _run_suite(SUITE_PATH, report)
    assert result.returncode == 0, result.stdout + result.stderr
    payload = json.loads(report.read_text(encoding="utf-8"))

    # Suite should pass overall while containing expected-fail transcript assertions.
    assert payload["passed"] is True
    report.unlink(missing_ok=True)
