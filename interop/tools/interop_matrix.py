#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from interop_submission_validation import (
    RESERVED_DIRS,
    classify_manifest_path,
    load_json,
)

DEFAULT_SUBMISSIONS = Path("interop/submissions")
DEFAULT_OUT_MD = Path("interop/INTEROP_MATRIX.md")
DEFAULT_OUT_JSON = Path("interop/interop_matrix.json")
LEGACY_MARK_COLUMNS = [
    "AICP-Profile-BASE-0.1",
    "AICP-Profile-MEDIATED-BLOCKING-0.1",
    "AICP-Core-0.1",
    "AICP-EXT-ENFORCEMENT-0.1",
    "AICP-EXT-ALERTS-0.1",
    "AICP-EXT-RESUME-0.1",
]


def _add_error(entry: dict[str, Any], code: str, message: str) -> None:
    entry["errors"].append({"error_code": code, "error_message": message})
    entry["valid"] = False


def _add_warning(entry: dict[str, Any], code: str, message: str) -> None:
    entry["warnings"].append({"warning_code": code, "warning_message": message})


def _entry_status(entry: dict[str, Any]) -> str:
    if not entry.get("valid"):
        return "INVALID"
    if entry.get("artifact_kind") == "template":
        return "INSTRUCTIONAL"
    return "VALID"


def _read_report(report_path: Path, relative_to: Path) -> tuple[dict[str, Any], set[str], list[str]]:
    report_rec: dict[str, Any] = {"path": str(report_path.relative_to(relative_to))}
    marks: set[str] = set()
    errors: list[str] = []
    try:
        report_obj = load_json(report_path)
        report_rec["suite_id"] = report_obj.get("suite_id")
        report_rec["profile_id"] = report_obj.get("profile_id")
        report_rec["passed"] = report_obj.get("passed")
        report_rec["compatibility_marks"] = report_obj.get("compatibility_marks", [])
        for mark in report_obj.get("compatibility_marks", []) or []:
            if isinstance(mark, str):
                marks.add(mark)
    except Exception as exc:
        report_rec["error"] = f"malformed report: {exc}"
        errors.append(f"{report_path.name}: malformed report")
    return report_rec, marks, errors


def _manifest_entry(submission_dir: Path) -> dict[str, Any]:
    submission_path = submission_dir / "submission.json"
    entry: dict[str, Any] = {
        "folder": submission_dir.name,
        "submission_id": None,
        "implementation_id": None,
        "implementation": None,
        "peer_implementation_id": None,
        "artifact_kind": "submission",
        "evidence_status": None,
        "claim_type": None,
        "claim_scope": None,
        "profile_ids": [],
        "reports": [],
        "compatibility_marks": [],
        "computed_marks": [],
        "errors": [],
        "warnings": [],
        "valid": True,
        "matrix_status": "VALID",
    }
    try:
        manifest = load_json(submission_path)
    except Exception as exc:
        _add_error(entry, "INVALID_SUBMISSION_MANIFEST", f"invalid submission.json: {exc}")
        entry["matrix_status"] = _entry_status(entry)
        return entry

    if not isinstance(manifest, dict):
        _add_error(entry, "INVALID_SUBMISSION_MANIFEST", "submission.json must be an object")
        entry["matrix_status"] = _entry_status(entry)
        return entry

    artifact_kind = classify_manifest_path(submission_path)
    entry["submission_id"] = manifest.get("submission_id")
    entry["implementation_id"] = manifest.get("implementation_id")
    entry["implementation"] = {
        "implementation_id": manifest.get("implementation_id"),
        "implementation_version": manifest.get("implementation_version"),
        "peer_implementation_id": manifest.get("peer_implementation_id"),
        "claim_type": manifest.get("claim_type"),
        "claim_scope": manifest.get("claim_scope"),
        "evidence_status": manifest.get("evidence_status"),
    }
    entry["peer_implementation_id"] = manifest.get("peer_implementation_id")
    entry["artifact_kind"] = artifact_kind
    entry["evidence_status"] = manifest.get("evidence_status")
    entry["claim_type"] = manifest.get("claim_type")
    entry["claim_scope"] = manifest.get("claim_scope")
    entry["profile_ids"] = manifest.get("profile_ids", [])

    marks: set[str] = set()
    for ref in manifest.get("report_refs", []):
        if not isinstance(ref, str):
            _add_error(entry, "INVALID_REPORT_REF", "report_refs entries must be strings")
            continue
        report_path = submission_dir / ref
        if not report_path.exists() or not report_path.is_file():
            if artifact_kind == "template":
                _add_warning(
                    entry,
                    "TEMPLATE_PLACEHOLDER_REF",
                    f"template placeholder report_refs target not yet replaced: {ref}",
                )
            else:
                _add_error(entry, "MISSING_REPORT_REF_TARGET", f"report_refs target missing: {ref}")
            continue
        report_rec, report_marks, report_errors = _read_report(report_path, submission_dir)
        entry["reports"].append(report_rec)
        marks.update(report_marks)
        for message in report_errors:
            _add_error(entry, "MALFORMED_REPORT", message)

    entry["compatibility_marks"] = sorted(marks)
    entry["computed_marks"] = sorted(marks) if entry["valid"] else []
    entry["matrix_status"] = _entry_status(entry)
    return entry


def _legacy_entry(submission_dir: Path) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "folder": submission_dir.name,
        "submission_id": submission_dir.name,
        "implementation_id": submission_dir.name,
        "implementation": None,
        "peer_implementation_id": None,
        "artifact_kind": "legacy_submission",
        "evidence_status": "self_attested",
        "claim_type": "compatible_with_profile",
        "claim_scope": "self_attested",
        "profile_ids": [],
        "reports": [],
        "compatibility_marks": [],
        "computed_marks": [],
        "errors": [],
        "warnings": [],
        "valid": True,
        "matrix_status": "VALID",
    }
    impl_path = submission_dir / "implementation.json"
    if not impl_path.exists():
        _add_error(entry, "MISSING_IMPLEMENTATION_MANIFEST", "missing implementation.json")
        entry["matrix_status"] = _entry_status(entry)
        return entry

    try:
        impl_obj = load_json(impl_path)
    except Exception as exc:
        _add_error(entry, "INVALID_IMPLEMENTATION_MANIFEST", f"invalid implementation.json: {exc}")
        entry["matrix_status"] = _entry_status(entry)
        return entry

    if isinstance(impl_obj, dict):
        entry["implementation"] = impl_obj
        entry["implementation_id"] = impl_obj.get("implementation_id", submission_dir.name)
        entry["profile_ids"] = impl_obj.get("profiles_claimed", []) or []
        impl_id = impl_obj.get("implementation_id")
        if isinstance(impl_id, str) and impl_id != submission_dir.name:
            _add_error(
                entry,
                "IMPLEMENTATION_ID_MISMATCH",
                f"implementation_id '{impl_id}' does not match folder '{submission_dir.name}'",
            )
    else:
        _add_error(entry, "INVALID_IMPLEMENTATION_MANIFEST", "implementation.json must be an object")
        entry["matrix_status"] = _entry_status(entry)
        return entry

    reports_dir = submission_dir / "reports"
    if not reports_dir.exists() or not reports_dir.is_dir():
        _add_error(entry, "MISSING_REPORTS_DIR", "missing reports directory")
        entry["matrix_status"] = _entry_status(entry)
        return entry

    marks: set[str] = set()
    for report_path in sorted(reports_dir.glob("*.json")):
        report_rec, report_marks, report_errors = _read_report(report_path, submission_dir)
        entry["reports"].append(report_rec)
        marks.update(report_marks)
        for message in report_errors:
            _add_error(entry, "MALFORMED_REPORT", message)
        profile_id = report_rec.get("profile_id")
        if isinstance(profile_id, str) and profile_id not in entry["profile_ids"]:
            entry["profile_ids"].append(profile_id)

    entry["compatibility_marks"] = sorted(marks)
    entry["computed_marks"] = sorted(marks) if entry["valid"] else []
    entry["matrix_status"] = _entry_status(entry)
    return entry


def _collect_real_submissions(submissions_dir: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if not submissions_dir.exists() or not submissions_dir.is_dir():
        return entries
    for subdir in sorted(
        d for d in submissions_dir.iterdir() if d.is_dir() and d.name not in RESERVED_DIRS and not d.name.startswith(".")
    ):
        if (subdir / "submission.json").exists():
            entries.append(_manifest_entry(subdir))
        else:
            entries.append(_legacy_entry(subdir))
    return entries


def _collect_instructional(root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    if not root.exists():
        return entries
    for manifest_path in sorted(root.glob("*/submission.json")):
        entries.append(_manifest_entry(manifest_path.parent))
    return entries


def build_matrix(submissions_dir: Path) -> dict[str, Any]:
    real_entries = _collect_real_submissions(submissions_dir)
    instructional_entries = _collect_instructional(submissions_dir / "examples") + _collect_instructional(submissions_dir / "templates")
    note = ""
    if not real_entries and not instructional_entries:
        note = "No submissions found."
    return {
        "submissions_dir": str(submissions_dir),
        "columns": LEGACY_MARK_COLUMNS,
        "implementations": real_entries,
        "real_submissions": real_entries,
        "instructional_artifacts": instructional_entries,
        "note": note,
        "notes": [
            "Instructional artifacts are listed separately from real submissions.",
            "evidence_status describes package strength/scope and does not imply maintainer endorsement.",
            "Template placeholder refs are surfaced as instructional warnings, not as real-submission compatibility evidence.",
            "Legacy implementation.json folders are shown as self_attested by default for backward-compatible display only.",
        ],
    }


def _fmt_profiles(value: Any) -> str:
    if isinstance(value, list) and value:
        return ", ".join(str(item) for item in value)
    return "—"


def _fmt_marks(value: Any) -> str:
    if isinstance(value, list) and value:
        return ", ".join(str(item) for item in value)
    return "—"


def _render_rows(entries: list[dict[str, Any]], *, include_peer: bool) -> list[str]:
    header = ["Folder", "Implementation", "Artifact kind"]
    if include_peer:
        header.append("Peer")
    header.extend(["Evidence status", "Claim type", "Claim scope", "Profiles", "Marks", "Matrix status"])
    rows = ["| " + " | ".join(header) + " |", "| " + " | ".join(["---"] * len(header)) + " |"]
    for entry in entries:
        row = [
            entry.get("folder") or "unknown",
            entry.get("implementation_id") or "unknown",
            entry.get("artifact_kind") or "unknown",
        ]
        if include_peer:
            row.append(entry.get("peer_implementation_id") or "—")
        row.extend(
            [
                entry.get("evidence_status") or "—",
                entry.get("claim_type") or "—",
                entry.get("claim_scope") or "—",
                _fmt_profiles(entry.get("profile_ids")),
                _fmt_marks(entry.get("compatibility_marks")),
                entry.get("matrix_status") or _entry_status(entry),
            ]
        )
        rows.append("| " + " | ".join(row) + " |")
    return rows


def render_markdown(matrix: dict[str, Any]) -> str:
    lines = [
        "# AICP Interop Matrix",
        "",
        "Generated from `interop/submissions/` using `interop/tools/interop_matrix.py`.",
        "",
    ]
    note = matrix.get("note")
    if isinstance(note, str) and note:
        lines.append(f"> {note}")
        lines.append("")

    real_entries = matrix.get("real_submissions", [])
    header = ["Implementation", "Status", "Evidence status"] + matrix.get("columns", [])
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join(["---"] * len(header)) + " |")
    for entry in real_entries:
        impl_name = entry.get("implementation_id") or entry.get("folder") or "unknown"
        marks = set(entry.get("compatibility_marks", [])) if entry.get("valid") else set()
        row = [impl_name, entry.get("matrix_status") or _entry_status(entry), entry.get("evidence_status") or "—"]
        for col in matrix.get("columns", []):
            row.append("✅" if col in marks else "❌")
        lines.append("| " + " | ".join(row) + " |")

    lines.extend(["", "## Interpretation notes", ""])
    for note in matrix.get("notes", []):
        lines.append(f"- {note}")

    lines.extend(["", "## Real submissions", ""])
    if real_entries:
        lines.extend(_render_rows(real_entries, include_peer=True))
    else:
        lines.append("No real submission folders are currently present.")

    lines.extend(["", "## Instructional artifacts", ""])
    instructional_entries = matrix.get("instructional_artifacts", [])
    if instructional_entries:
        lines.extend(_render_rows(instructional_entries, include_peer=False))
    else:
        lines.append("No instructional example/template artifacts found.")

    lines.extend(["", "## Parsing notes", ""])
    for section_name, entries in (
        ("real submissions", real_entries),
        ("instructional artifacts", instructional_entries),
    ):
        if not entries:
            lines.append(f"- {section_name}: no entries.")
            continue
        for entry in entries:
            label = entry.get("submission_id") or entry.get("folder") or "unknown"
            parts: list[str] = []
            if entry.get("errors"):
                parts.append(
                    "; ".join(f"{e.get('error_code')}: {e.get('error_message')}" for e in entry["errors"])
                )
            if entry.get("warnings"):
                parts.append(
                    "; ".join(f"{w.get('warning_code')}: {w.get('warning_message')}" for w in entry["warnings"])
                )
            if parts:
                lines.append(f"- `{label}`: {'; '.join(parts)}")
            else:
                lines.append(f"- `{label}`: no parsing errors or instructional warnings.")
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
