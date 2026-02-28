#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

DEFAULT_SUBMISSIONS = Path("interop/submissions")
DEFAULT_OUT_MD = Path("interop/INTEROP_MATRIX.md")
DEFAULT_OUT_JSON = Path("interop/interop_matrix.json")

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


def collect_submission(submission_dir: Path) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "implementation_folder": submission_dir.name,
        "implementation": None,
        "reports": [],
        "compatibility_marks": [],
        "profiles": {},
        "errors": [],
        "valid": True,
    }

    impl_path = submission_dir / "implementation.json"
    if not impl_path.exists():
        entry["errors"].append("missing implementation.json")
        entry["valid"] = False
    else:
        try:
            entry["implementation"] = _load_json(impl_path)
        except Exception as exc:
            entry["errors"].append(f"invalid implementation.json: {exc}")
            entry["valid"] = False

    reports_dir = submission_dir / "reports"
    marks: set[str] = set()

    if not reports_dir.exists() or not reports_dir.is_dir():
        entry["errors"].append("missing reports directory")
        entry["valid"] = False
    else:
        for report_path in sorted(reports_dir.glob("*.json")):
            report_rec: dict[str, Any] = {"path": str(report_path.relative_to(submission_dir))}
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
                    entry["profiles"][profile_id] = bool(report_obj.get("passed"))
            except Exception as exc:
                report_rec["error"] = f"malformed report: {exc}"
                entry["errors"].append(f"{report_path.name}: malformed report")
                entry["valid"] = False
            entry["reports"].append(report_rec)

    entry["compatibility_marks"] = sorted(marks)
    return entry


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

    dirs = sorted([d for d in submissions_dir.iterdir() if d.is_dir()])
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
        "",
    ]

    note = matrix.get("note")
    if isinstance(note, str) and note:
        lines.append(f"> {note}")
        lines.append("")

    cols = matrix["columns"]
    header = ["Implementation"] + cols
    lines.append("| " + " | ".join(header) + " |")
    lines.append("| " + " | ".join(["---"] * len(header)) + " |")

    for impl in matrix.get("implementations", []):
        impl_meta = impl.get("implementation") or {}
        impl_name = impl_meta.get("implementation_id") or impl.get("implementation_folder") or "unknown"
        marks = set(impl.get("compatibility_marks", []))
        row = [str(impl_name)]
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
                lines.append(f"- `{impl_name}`: " + "; ".join(str(e) for e in errors))
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
