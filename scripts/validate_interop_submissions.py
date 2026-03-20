#!/usr/bin/env python3
"""Validate arbitrary real interop submission folders."""

from __future__ import annotations

from pathlib import Path

from interop_submission_validation import (
    RESERVED_DIRS,
    SUBMISSIONS_ROOT,
    classify_artifact_kind,
    load_integrity_schema_validator,
    load_schema_and_registry,
    validate_bundle_integrity,
    validate_common_rules,
    validate_schema,
)


def _submission_dirs() -> list[Path]:
    if not SUBMISSIONS_ROOT.exists():
        return []
    return sorted(
        path
        for path in SUBMISSIONS_ROOT.iterdir()
        if path.is_dir() and path.name not in RESERVED_DIRS and not path.name.startswith(".")
    )


def main() -> int:
    try:
        _, validator, known_profiles = load_schema_and_registry()
        _, integrity_validator = load_integrity_schema_validator()
    except Exception as exc:
        print(f"[FAIL] setup error: {exc}")
        return 1

    dirs = _submission_dirs()
    if not dirs:
        print("OK: no real interop submission folders found under interop/submissions/ (reserved examples/templates skipped).")
        return 0

    failures: list[str] = []
    checked = 0
    skipped = 0

    for submission_dir in dirs:
        submission_path = submission_dir / "submission.json"
        legacy_path = submission_dir / "implementation.json"
        if legacy_path.exists() and not submission_path.exists():
            skipped += 1
            print(f"[SKIP] {submission_dir}: legacy implementation.json layout retained for backward compatibility")
            continue
        if not submission_path.exists():
            failures.append(f"{submission_dir}: missing submission.json")
            continue

        checked += 1
        manifest, errors = validate_schema(submission_path, validator)
        if manifest is None:
            failures.extend([f"{submission_path}: {error}" for error in errors])
            continue

        errors.extend(validate_common_rules(submission_path, manifest, known_profiles, require_existing_refs=True))
        integrity_status, integrity_errors = validate_bundle_integrity(
            submission_dir,
            manifest["submission_id"],
            integrity_validator=integrity_validator,
        )
        errors.extend(integrity_errors)
        artifact_kind = classify_artifact_kind(submission_path, manifest)
        if errors:
            failures.extend([f"{submission_path}: {error}" for error in errors])
        else:
            print(f"[OK] {submission_path} (kind={artifact_kind}, integrity={integrity_status})")

    if failures:
        for failure in failures:
            print(f"[FAIL] {failure}")
        print(f"Interop submission validation failed with {len(failures)} issue(s).")
        return 1

    print(
        "OK: validated "
        f"{checked} real interop submission manifest(s); skipped {skipped} legacy submission folder(s)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
