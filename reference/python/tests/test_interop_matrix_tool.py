from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
TOOL = ROOT / "interop/tools/interop_matrix.py"


def _run_tool(submissions: Path, out_md: Path, out_json: Path) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        str(TOOL),
        "--submissions",
        str(submissions),
        "--out-md",
        str(out_md),
        "--out-json",
        str(out_json),
    ]
    return subprocess.run(cmd, check=False, text=True, capture_output=True, cwd=ROOT)


def test_interop_matrix_tool_with_submission(tmp_path: Path) -> None:
    submissions = tmp_path / "submissions"
    impl_dir = submissions / "impl-one"
    reports_dir = impl_dir / "reports"
    reports_dir.mkdir(parents=True)

    implementation = {
        "implementation_id": "impl-one",
        "name": "Implementation One",
        "language": "python",
        "version": "0.1.0",
        "maintainer": "Maintainer One",
        "contact": "@impl-one",
    }
    (impl_dir / "implementation.json").write_text(json.dumps(implementation), encoding="utf-8")

    report = {
        "profile_id": "AICP-BASE",
        "passed": True,
        "compatibility_marks": ["AICP-Profile-BASE-0.1"],
    }
    (reports_dir / "report_profile_base.json").write_text(json.dumps(report), encoding="utf-8")

    out_md = tmp_path / "INTEROP_MATRIX.md"
    out_json = tmp_path / "interop_matrix.json"

    result = _run_tool(submissions, out_md, out_json)
    assert result.returncode == 0, result.stderr

    md = out_md.read_text(encoding="utf-8")
    data = json.loads(out_json.read_text(encoding="utf-8"))

    assert "| Implementation | Status |" in md
    assert "| impl-one | VALID |" in md
    impl = next(i for i in data["implementations"] if i.get("implementation", {}).get("implementation_id") == "impl-one")
    assert impl["valid"] is True
    assert "AICP-Profile-BASE-0.1" in impl["computed_marks"]


def test_interop_matrix_tool_marks_id_mismatch_invalid(tmp_path: Path) -> None:
    submissions = tmp_path / "submissions"
    impl_dir = submissions / "foo-impl"
    reports_dir = impl_dir / "reports"
    reports_dir.mkdir(parents=True)

    implementation = {
        "implementation_id": "bar-impl",
        "name": "Mismatched Implementation",
        "language": "python",
        "version": "0.1.0",
        "maintainer": "Mismatch Maintainer",
        "contact": "@mismatch",
    }
    (impl_dir / "implementation.json").write_text(json.dumps(implementation), encoding="utf-8")

    report = {
        "profile_id": "AICP-BASE",
        "passed": True,
        "compatibility_marks": ["AICP-Profile-BASE-0.1"],
    }
    (reports_dir / "report_profile_base.json").write_text(json.dumps(report), encoding="utf-8")

    out_md = tmp_path / "INTEROP_MATRIX.md"
    out_json = tmp_path / "interop_matrix.json"

    result = _run_tool(submissions, out_md, out_json)
    assert result.returncode == 0, result.stderr

    md = out_md.read_text(encoding="utf-8")
    data = json.loads(out_json.read_text(encoding="utf-8"))

    impl = data["implementations"][0]
    assert impl["valid"] is False
    assert impl["computed_marks"] == []
    assert any(e.get("error_code") == "IMPLEMENTATION_ID_MISMATCH" for e in impl["errors"])
    assert "| bar-impl | INVALID |" in md


def test_interop_matrix_tool_empty_submissions(tmp_path: Path) -> None:
    submissions = tmp_path / "submissions"
    submissions.mkdir(parents=True)

    out_md = tmp_path / "INTEROP_MATRIX.md"
    out_json = tmp_path / "interop_matrix.json"

    result = _run_tool(submissions, out_md, out_json)
    assert result.returncode == 0, result.stderr

    md = out_md.read_text(encoding="utf-8")
    data = json.loads(out_json.read_text(encoding="utf-8"))

    assert "No submissions found." in md
    assert data["implementations"] == []
