from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
REVIEW_TOOL = ROOT / "scripts/review_interop_submission.py"
BUILD_TOOL = ROOT / "interop/tools/build_submission.py"


def _run_review(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(REVIEW_TOOL), *args],
        check=False,
        text=True,
        capture_output=True,
        cwd=ROOT,
    )


def _run_build(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(BUILD_TOOL), *args],
        check=False,
        text=True,
        capture_output=True,
        cwd=ROOT,
    )


def test_review_interop_submission_reports_example_as_non_matrix_eligible() -> None:
    result = _run_review("interop/submissions/examples/single_profile_claim", "--json")
    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)

    assert summary["kind"] == "example"
    assert summary["validation_status"] == "valid"
    assert summary["integrity"]["status"] == "valid"
    assert summary["matrix_publication_possible"] is False
    assert "instructional" in summary["matrix_publication_reason"]


def test_review_interop_submission_reports_real_submission_as_matrix_eligible(tmp_path: Path) -> None:
    out_root = tmp_path / "submissions"
    report_one = tmp_path / "inputs" / "report_profile_base.json"
    report_one.parent.mkdir(parents=True, exist_ok=True)
    report_one.write_text(json.dumps({"profile_id": "AICP-BASE", "passed": True}), encoding="utf-8")
    report_two = tmp_path / "inputs" / "report_core.json"
    report_two.write_text(json.dumps({"suite_id": "CT_CORE_0.1", "passed": True}), encoding="utf-8")

    build = _run_build(
        "--out-root",
        str(out_root),
        "--submission-id",
        "reviewable-real-submission",
        "--implementation-id",
        "fictional-impl-a",
        "--implementation-version",
        "1.0.0",
        "--profile-id",
        "AICP-BASE",
        "--claim-type",
        "implements_profile",
        "--claim-scope",
        "self_attested",
        "--evidence-status",
        "reproducible",
        "--report-path",
        str(report_one),
        "--report-path",
        str(report_two),
        "--suite-ref",
        "PF_AICP_BASE_0.1",
        "--suite-ref",
        "CT_CORE_0.1",
        "--disclosure",
        "Fictional local review package; not a market-facing claim.",
        "--with-integrity",
        "--validate",
    )
    assert build.returncode == 0, build.stderr

    result = _run_review(str(out_root / "reviewable-real-submission"), "--json")
    assert result.returncode == 0, result.stderr
    summary = json.loads(result.stdout)

    assert summary["kind"] == "submission"
    assert summary["validation_status"] == "valid"
    assert summary["integrity"]["status"] == "valid"
    assert summary["matrix_publication_possible"] is True
    assert "eligible for matrix publication" in summary["matrix_publication_reason"]
