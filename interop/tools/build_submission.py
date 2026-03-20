#!/usr/bin/env python3
"""Build a real interop submission package from explicit metadata and report files."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from interop_submission_validation import (  # noqa: E402
    ALLOWED_CLAIM_TYPES,
    ALLOWED_EVIDENCE_STATUSES,
    INTEGRITY_FILENAME,
    build_integrity_manifest,
    load_json,
    load_schema_and_registry,
    load_integrity_schema_validator,
    manifest_tracked_paths,
    validate_bundle_integrity,
    validate_common_rules,
    validate_schema,
)

REAL_EVIDENCE_STATUSES = {"self_attested", "reproducible", "pairwise"}
ALLOWED_CLAIM_SCOPES = {"self_attested", "pairwise"}
ALLOWED_EVIDENCE_TYPES = {
    "conformance_report",
    "profile_report",
    "golden_transcript",
    "pairwise_transcript",
    "human_summary",
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build an AICP interop submission package from supplied evidence.")
    parser.add_argument("--out-root", required=True, help="Directory under which <submission-id>/ will be created")
    parser.add_argument("--submission-id", required=True)
    parser.add_argument("--implementation-id", required=True)
    parser.add_argument("--implementation-version", required=True)
    parser.add_argument("--profile-id", action="append", required=True, dest="profile_ids")
    parser.add_argument("--claim-type", required=True, choices=sorted(ALLOWED_CLAIM_TYPES))
    parser.add_argument("--claim-scope", required=True, choices=sorted(ALLOWED_CLAIM_SCOPES))
    parser.add_argument("--evidence-status", required=True, choices=sorted(REAL_EVIDENCE_STATUSES))
    parser.add_argument("--peer-implementation-id")
    parser.add_argument("--report-path", action="append", required=True, dest="report_paths")
    parser.add_argument("--suite-ref", action="append", required=True, dest="suite_refs")
    parser.add_argument("--evidence-type", action="append", dest="evidence_types")
    parser.add_argument("--disclosure", action="append", dest="disclosures")
    parser.add_argument("--note")
    parser.add_argument("--generated-at", help="Override generated_at (RFC3339 / date-time)")
    parser.add_argument(
        "--with-integrity",
        action="store_true",
        help=f"Write {INTEGRITY_FILENAME} with digests for submission.json and copied package evidence",
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate the generated package with the existing submission schema and common-rule checks",
    )
    return parser.parse_args()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _stable_unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def _infer_evidence_types(report_paths: list[Path]) -> list[str]:
    inferred: list[str] = []
    for report_path in report_paths:
        try:
            report = load_json(report_path)
        except Exception:
            continue
        if not isinstance(report, dict):
            continue
        if isinstance(report.get("suite_id"), str) and report.get("suite_id"):
            inferred.append("conformance_report")
        if isinstance(report.get("profile_id"), str) and report.get("profile_id"):
            inferred.append("profile_report")
    return _stable_unique(inferred)


def _validate_inputs(args: argparse.Namespace, report_paths: list[Path]) -> list[str]:
    errors: list[str] = []
    if args.evidence_status not in ALLOWED_EVIDENCE_STATUSES:
        errors.append(f"evidence_status must be one of: {', '.join(sorted(REAL_EVIDENCE_STATUSES))}")
    if not args.disclosures:
        errors.append("at least one --disclosure is required for a real submission package")
    if args.claim_type == "pairwise_interop":
        if not args.peer_implementation_id:
            errors.append("--peer-implementation-id is required for --claim-type pairwise_interop")
        if args.claim_scope != "pairwise":
            errors.append("--claim-scope must be pairwise for --claim-type pairwise_interop")
        if len(report_paths) < 2:
            errors.append("pairwise_interop packages require at least two --report-path values")
        if args.evidence_status != "pairwise":
            errors.append("--evidence-status must be pairwise for --claim-type pairwise_interop")
    if args.evidence_status == "pairwise" and args.claim_type != "pairwise_interop":
        errors.append("--evidence-status pairwise requires --claim-type pairwise_interop")
    if args.peer_implementation_id and args.claim_type != "pairwise_interop":
        errors.append("--peer-implementation-id is only supported for --claim-type pairwise_interop")
    for report_path in report_paths:
        if not report_path.exists() or not report_path.is_file():
            errors.append(f"report path does not exist or is not a file: {report_path}")
    if len({path.name for path in report_paths}) != len(report_paths):
        errors.append("report filenames must be unique when copied into reports/")
    return errors


def _build_manifest(args: argparse.Namespace, report_refs: list[str], evidence_types: list[str]) -> dict[str, Any]:
    manifest: dict[str, Any] = {
        "submission_id": args.submission_id,
        "implementation_id": args.implementation_id,
        "implementation_version": args.implementation_version,
        "profile_ids": _stable_unique(args.profile_ids),
        "evidence_types": evidence_types,
        "evidence_status": args.evidence_status,
        "report_refs": report_refs,
        "suite_refs": _stable_unique(args.suite_refs),
        "claim_type": args.claim_type,
        "claim_scope": args.claim_scope,
        "generated_at": args.generated_at or _utc_now(),
        "disclosures": args.disclosures,
    }
    if args.peer_implementation_id:
        manifest["peer_implementation_id"] = args.peer_implementation_id
    if args.note:
        manifest["notes"] = args.note
    return manifest


def _write_package(package_dir: Path, report_paths: list[Path], manifest: dict[str, Any], *, with_integrity: bool) -> None:
    reports_dir = package_dir / "reports"
    reports_dir.mkdir(parents=True, exist_ok=False)
    for report_path in report_paths:
        shutil.copy2(report_path, reports_dir / report_path.name)

    submission_path = package_dir / "submission.json"
    submission_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    if with_integrity:
        tracked_paths = manifest_tracked_paths(manifest)
        missing_paths = [tracked_path.as_posix() for tracked_path in tracked_paths if not (package_dir / tracked_path).is_file()]
        if missing_paths:
            raise FileNotFoundError(
                "cannot generate bundle integrity manifest because required package files are missing: "
                + ", ".join(missing_paths)
            )
        integrity_manifest = build_integrity_manifest(
            package_dir,
            manifest["submission_id"],
            tracked_paths,
            generated_at=manifest["generated_at"],
        )
        (package_dir / INTEGRITY_FILENAME).write_text(
            json.dumps(integrity_manifest, indent=2) + "\n", encoding="utf-8"
        )


def _validate_package(package_dir: Path) -> list[str]:
    submission_path = package_dir / "submission.json"
    _, validator, known_profiles = load_schema_and_registry()
    _, integrity_validator = load_integrity_schema_validator()
    manifest, errors = validate_schema(submission_path, validator)
    if manifest is None:
        return errors
    errors.extend(validate_common_rules(submission_path, manifest, known_profiles, require_existing_refs=True))
    _, integrity_errors = validate_bundle_integrity(
        package_dir,
        manifest["submission_id"],
        integrity_validator=integrity_validator,
    )
    errors.extend(integrity_errors)
    return errors


def main() -> int:
    args = _parse_args()
    report_paths = [Path(path).resolve() for path in args.report_paths]
    errors = _validate_inputs(args, report_paths)
    evidence_types = _stable_unique(args.evidence_types or _infer_evidence_types(report_paths))
    if not evidence_types:
        errors.append(
            "unable to infer evidence_types from supplied reports; pass one or more --evidence-type values explicitly"
        )
    unknown_evidence_types = [value for value in evidence_types if value not in ALLOWED_EVIDENCE_TYPES]
    if unknown_evidence_types:
        errors.append("evidence_type must be one of: " + ", ".join(sorted(ALLOWED_EVIDENCE_TYPES)))
    if errors:
        for error in errors:
            print(f"[FAIL] {error}")
        return 1

    package_dir = Path(args.out_root) / args.submission_id
    if package_dir.exists():
        print(f"[FAIL] output package already exists: {package_dir}")
        return 1

    report_refs = [f"reports/{path.name}" for path in report_paths]
    manifest = _build_manifest(args, report_refs, evidence_types)

    package_dir.mkdir(parents=True, exist_ok=False)
    try:
        _write_package(package_dir, report_paths, manifest, with_integrity=args.with_integrity)
        if args.validate:
            validation_errors = _validate_package(package_dir)
            if validation_errors:
                for error in validation_errors:
                    print(f"[FAIL] {error}")
                return 1
    except Exception:
        shutil.rmtree(package_dir, ignore_errors=True)
        raise

    print(f"[OK] wrote {package_dir / 'submission.json'}")
    for ref in report_refs:
        print(f"[OK] copied evidence -> {package_dir / ref}")
    if args.with_integrity:
        print(f"[OK] wrote {package_dir / INTEGRITY_FILENAME}")
    if args.validate:
        print(f"[OK] validated generated package: {package_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
