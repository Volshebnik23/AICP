#!/usr/bin/env python3
"""Print a concise reviewer summary for one interop submission folder."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from interop_submission_validation import (
    INTEGRITY_FILENAME,
    classify_manifest_path,
    load_integrity_schema_validator,
    load_schema_and_registry,
    validate_bundle_integrity,
    validate_common_rules,
    validate_schema,
)


ROOT = Path(__file__).resolve().parents[1]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize one interop submission folder for maintainer review.")
    parser.add_argument("submission", help="Path to a submission folder or submission.json")
    parser.add_argument("--json", action="store_true", help="Emit the review summary as JSON")
    return parser.parse_args()


def _resolve_submission_path(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve()


def _submission_manifest_path(path: Path) -> Path:
    if path.is_dir():
        return path / "submission.json"
    return path


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _review_summary(path: Path) -> dict[str, Any]:
    submission_path = _submission_manifest_path(path)
    package_dir = submission_path.parent
    summary: dict[str, Any] = {
        "submission_path": _display_path(submission_path),
        "package_dir": _display_path(package_dir),
        "kind": "unknown",
        "validation_status": "invalid",
        "matrix_publication_possible": False,
        "matrix_publication_reason": "missing submission manifest",
        "integrity": {
            "present": (package_dir / INTEGRITY_FILENAME).exists(),
            "status": "absent",
        },
        "report_refs": [],
        "errors": [],
    }

    if not submission_path.exists():
        summary["errors"].append("missing submission.json")
        return summary

    _, validator, known_profiles = load_schema_and_registry()
    _, integrity_validator = load_integrity_schema_validator()
    manifest, errors = validate_schema(submission_path, validator)
    if manifest is None:
        summary["errors"].extend(errors)
        summary["kind"] = classify_manifest_path(submission_path)
        summary["matrix_publication_reason"] = "submission manifest is invalid"
        return summary

    kind = classify_manifest_path(submission_path)
    require_existing_refs = kind != "template"
    common_errors = validate_common_rules(
        submission_path,
        manifest,
        known_profiles,
        require_existing_refs=require_existing_refs,
    )
    integrity_status, integrity_errors = validate_bundle_integrity(
        package_dir,
        manifest["submission_id"],
        integrity_validator=integrity_validator,
    )

    report_refs: list[dict[str, Any]] = []
    for ref in manifest.get("report_refs", []):
        if not isinstance(ref, str):
            continue
        target = package_dir / ref
        report_refs.append(
            {
                "path": ref,
                "exists": target.exists(),
                "is_file": target.is_file(),
            }
        )

    all_errors = [*errors, *common_errors, *integrity_errors]
    matrix_ok = kind == "submission" and not all_errors
    if kind != "submission":
        matrix_reason = f"{kind} packages are instructional and stay separate from real external matrix rows"
    elif all_errors:
        matrix_reason = "submission requires fixes before public matrix publication"
    else:
        matrix_reason = "eligible for matrix publication after maintainer review and matrix regeneration"

    summary.update(
        {
            "kind": kind,
            "submission_id": manifest.get("submission_id"),
            "implementation_id": manifest.get("implementation_id"),
            "peer_implementation_id": manifest.get("peer_implementation_id"),
            "profile_ids": manifest.get("profile_ids", []),
            "claim_type": manifest.get("claim_type"),
            "claim_scope": manifest.get("claim_scope"),
            "evidence_status": manifest.get("evidence_status"),
            "disclosures": manifest.get("disclosures", []),
            "validation_status": "valid" if not all_errors else "invalid",
            "matrix_publication_possible": matrix_ok,
            "matrix_publication_reason": matrix_reason,
            "integrity": {
                "present": (package_dir / INTEGRITY_FILENAME).exists(),
                "status": integrity_status,
            },
            "report_refs": report_refs,
            "errors": all_errors,
        }
    )
    return summary


def _print_text(summary: dict[str, Any]) -> None:
    print("AICP interop review summary")
    print(f"- package_dir: {summary['package_dir']}")
    print(f"- kind: {summary['kind']}")
    print(f"- submission_id: {summary.get('submission_id', '—')}")
    print(f"- implementation_id: {summary.get('implementation_id', '—')}")
    print(f"- peer_implementation_id: {summary.get('peer_implementation_id') or '—'}")
    print(f"- profile_ids: {', '.join(summary.get('profile_ids', [])) or '—'}")
    print(f"- claim: {summary.get('claim_type', '—')} / {summary.get('claim_scope', '—')}")
    print(f"- evidence_status: {summary.get('evidence_status', '—')}")
    print(
        f"- integrity: {summary['integrity']['status']}"
        f" (present={str(summary['integrity']['present']).lower()})"
    )
    print(f"- validation_status: {summary['validation_status']}")
    print(
        f"- matrix_publication_possible: {str(summary['matrix_publication_possible']).lower()}"
        f" ({summary['matrix_publication_reason']})"
    )
    print("- report_refs:")
    for entry in summary.get("report_refs", []):
        print(
            "  - "
            f"{entry['path']} (exists={str(entry['exists']).lower()}, is_file={str(entry['is_file']).lower()})"
        )
    if summary.get("errors"):
        print("- errors:")
        for error in summary["errors"]:
            print(f"  - {error}")
    else:
        print("- errors: none")


def main() -> int:
    args = _parse_args()
    summary = _review_summary(_resolve_submission_path(args.submission))
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        _print_text(summary)
    return 0 if summary.get("validation_status") == "valid" else 1


if __name__ == "__main__":
    raise SystemExit(main())
