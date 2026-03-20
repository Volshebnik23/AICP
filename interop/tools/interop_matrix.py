#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

DEFAULT_SUBMISSIONS = Path("interop/submissions")
DEFAULT_OUT_MD = Path("interop/INTEROP_MATRIX.md")
DEFAULT_OUT_JSON = Path("interop/interop_matrix.json")
RESERVED_DIRS = {"examples", "templates"}

MATRIX_MARK_COLUMNS = [
    "AICP-Profile-BASE-0.1",
    "AICP-Profile-MEDIATED-BLOCKING-0.1",
    "AICP-Core-0.1",
    "AICP-EXT-ENFORCEMENT-0.1",
    "AICP-EXT-ALERTS-0.1",
    "AICP-EXT-RESUME-0.1",
]


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _add_error(entry: dict[str, Any], code: str, message: str) -> None:
    entry["errors"].append({"error_code": code, "error_message": message})
    entry["valid"] = False


def _base_entry(submission_dir: Path) -> dict[str, Any]:
    return {
        "implementation_folder": submission_dir.name,
        "implementation": None,
        "submission": None,
        "reports": [],
        "computed_marks": [],
        "profiles": {},
        "errors": [],
        "valid": True,
    }


def _read_report(report_path: Path, relative_to: Path) -> tuple[dict[str, Any], set[str], dict[str, bool], list[str]]:
    report_rec: dict[str, Any] = {"path": str(report_path.relative_to(relative_to))}
    marks: set[str] = set()
    profiles: dict[str, bool] = {}
    errors: list[str] = []
    try:
        report_obj = _load_json(report_path)
        report_rec["suite_id"] = report_obj.get("suite_id")
        report_rec["profile_id"] = report_obj.get("profile_id")
        report_rec["passed"] = report_obj.get("passed")
        report_rec["compatibility_marks"] = report_obj.get("compatibility_marks", [])
        for mark in report_obj.get("compatibility_marks", []) or []:
            if isinstance(mark, str):
                marks.add(mark)
        profile_id = report_obj.get("profile_id")
        if isinstance(profile_id, str):
            profiles[profile_id] = bool(report_obj.get("passed"))
    except Exception as exc:
        report_rec["error"] = f"malformed report: {exc}"
        errors.append(f"{report_path.name}: malformed report")
    return report_rec, marks, profiles, errors


def _collect_legacy_submission(submission_dir: Path) -> dict[str, Any]:
    entry = _base_entry(submission_dir)
    impl_path = submission_dir / "implementation.json"
    if not impl_path.exists():
        _add_error(entry, "MISSING_IMPLEMENTATION_MANIFEST", "missing implementation.json")
        return entry

    try:
        impl_obj = _load_json(impl_path)
        if not isinstance(impl_obj, dict):
            _add_error(entry, "INVALID_IMPLEMENTATION_MANIFEST", "implementation.json must be an object")
        else:
            entry["implementation"] = impl_obj
            impl_id = impl_obj.get("implementation_id")
            if not isinstance(impl_id, str):
                _add_error(entry, "INVALID_IMPLEMENTATION_ID", "implementation_id must be a string")
            elif impl_id != submission_dir.name:
                _add_error(
                    entry,
                    "IMPLEMENTATION_ID_MISMATCH",
                    f"implementation_id '{impl_id}' does not match folder '{submission_dir.name}'",
                )
    except Exception as exc:
        _add_error(entry, "INVALID_IMPLEMENTATION_MANIFEST", f"invalid implementation.json: {exc}")
        return entry

    reports_dir = submission_dir / "reports"
    if not reports_dir.exists() or not reports_dir.is_dir():
        _add_error(entry, "MISSING_REPORTS_DIR", "missing reports directory")
        return entry

    marks: set[str] = set()
    profiles: dict[str, bool] = {}
    for report_path in sorted(reports_dir.glob("*.json")):
        report_rec, report_marks, report_profiles, report_errors = _read_report(report_path, submission_dir)
        marks.update(report_marks)
        profiles.update(report_profiles)
        for message in report_errors:
            _add_error(entry, "MALFORMED_REPORT", message)
        entry["reports"].append(report_rec)

    entry["profiles"] = profiles
    entry["computed_marks"] = sorted(marks) if entry["valid"] else []
    return entry


def _collect_manifest_submission(submission_dir: Path) -> dict[str, Any]:
    entry = _base_entry(submission_dir)
    submission_path = submission_dir / "submission.json"
    try:
        submission_obj = _load_json(submission_path)
    except Exception as exc:
        _add_error(entry, "INVALID_SUBMISSION_MANIFEST", f"invalid submission.json: {exc}")
        return entry

    if not isinstance(submission_obj, dict):
        _add_error(entry, "INVALID_SUBMISSION_MANIFEST", "submission.json must be an object")
        return entry

    entry["submission"] = submission_obj
    impl_id = submission_obj.get("implementation_id")
    entry["implementation"] = {
        "implementation_id": impl_id,
        "implementation_version": submission_obj.get("implementation_version"),
        "peer_implementation_id": submission_obj.get("peer_implementation_id"),
        "claim_type": submission_obj.get("claim_type"),
        "claim_scope": submission_obj.get("claim_scope"),
    }
    if not isinstance(impl_id, str):
        _add_error(entry, "INVALID_IMPLEMENTATION_ID", "submission.json implementation_id must be a string")

    report_refs = submission_obj.get("report_refs")
    if not isinstance(report_refs, list) or not report_refs:
        _add_error(entry, "MISSING_REPORT_REFS", "submission.json must contain a non-empty report_refs array")
        return entry

    marks: set[str] = set()
    profiles: dict[str, bool] = {}
    for ref in report_refs:
        if not isinstance(ref, str):
            _add_error(entry, "INVALID_REPORT_REF", "report_refs entries must be strings")
            continue
        report_path = submission_dir / ref
        if not report_path.exists() or not report_path.is_file():
            _add_error(entry, "MISSING_REPORT_REF_TARGET", f"report_refs target missing: {ref}")
            continue
        report_rec, report_marks, report_profiles, report_errors = _read_report(report_path, submission_dir)
        marks.update(report_marks)
        profiles.update(report_profiles)
        for message in report_errors:
            _add_error(entry, "MALFORMED_REPORT", message)
        entry["reports"].append(report_rec)

    for profile_id in submission_obj.get("profile_ids", []):
        if isinstance(profile_id, str) and profile_id not in profiles:
            profiles.setdefault(profile_id, True)

    entry["profiles"] = profiles
    entry["computed_marks"] = sorted(marks) if entry["valid"] else []
    return entry


def collect_submission(submission_dir: Path) -> dict[str, Any]:
    if (submission_dir / "submission.json").exists():
        return _collect_manifest_submission(submission_dir)
    return _collect_legacy_submission(submission_dir)


def build_matrix(submissions_dir: Path) -> dict[str, Any]:
    matrix: dict[str, Any] = {
        "submissions_dir": str(submissions_dir),
        "columns": MATRIX_MARK_COLUMNS,
        "implementations": [],
        "note": "",
    }

    if not submissions_dir.exists() or not submissions_dir.is_dir():
        matrix["note"] = "Submissions directory not found."
        return matrix

    dirs = sorted(
        d
        for d in submissions_dir.iterdir()
        if d.is_dir() and d.name not in RESERVED_DIRS and not d.name.startswith(".")
    )
    if not dirs:
        matrix["note"] = "No submissions found."
        return matrix

    for subdir in dirs:
        matrix["implementations"].append(collect_submission(subdir))

    return matrix


def render_markdown(matrix: dict[str, Any]) -> str:
    lines: list[str] = [
        "# AICP Interop Matrix",
        "",
        "Generated from `interop/submissions/*` using `interop/tools/interop_matrix.py`.",
        "Reserved instructional directories (`examples/`, `templates/`) are ignored.",
        "",
    ]

    note = matrix.get("note")
    if isinstance(note, str) and note:
        lines.append(f"> {note}")
        lines.append("")

    cols = matrix["columns"]
    header = ["Implementation", "Status"] + cols
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join(["---"] * len(header)) + " |")

    for impl in matrix.get("implementations", []):
        impl_meta = impl.get("implementation") or {}
        impl_name = impl_meta.get("implementation_id") or impl.get("implementation_folder") or "unknown"
        status = "VALID" if impl.get("valid") else "INVALID"
        marks = set(impl.get("computed_marks", [])) if impl.get("valid") else set()
        row = [str(impl_name), status]
        for col in cols:
            row.append("✅" if col in marks else "❌")
        lines.append("| " + " | ".join(row) + " |")

    lines.append("")
    lines.append("## Submission parsing notes")
    lines.append("")

    if not matrix.get("implementations"):
        lines.append("- No implementation submissions available.")
    else:
        for impl in matrix["implementations"]:
            impl_meta = impl.get("implementation") or {}
            impl_name = impl_meta.get("implementation_id") or impl.get("implementation_folder") or "unknown"
            errors = impl.get("errors", [])
            if errors:
                rendered = "; ".join(f"{e.get('error_code')}: {e.get('error_message')}" for e in errors)
                lines.append(f"- `{impl_name}`: {rendered}")
            else:
                lines.append(f"- `{impl_name}`: no parsing errors.")

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate AICP interop matrix artifacts from submission folders")
    parser.add_argument("--submissions", default=str(DEFAULT_SUBMISSIONS), help="Submissions directory path")
    parser.add_argument("--out-md", default=str(DEFAULT_OUT_MD), help="Markdown output path")
    parser.add_argument("--out-json", default=str(DEFAULT_OUT_JSON), help="JSON output path")
    args = parser.parse_args()

    submissions_dir = Path(args.submissions)
    out_md = Path(args.out_md)
    out_json = Path(args.out_json)

    matrix = build_matrix(submissions_dir)
    md = render_markdown(matrix)

    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text(md, encoding="utf-8")
    out_json.write_text(json.dumps(matrix, indent=2) + "\n", encoding="utf-8")

    print(f"Wrote {out_md}")
    print(f"Wrote {out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
