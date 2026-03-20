#!/usr/bin/env python3
"""Validate shipped interop submission examples and templates."""

from __future__ import annotations

from interop_submission_validation import (
    EXAMPLES_ROOT,
    TEMPLATES_ROOT,
    load_schema_and_registry,
    manifest_paths,
    validate_common_rules,
    validate_integrity_manifest,
    validate_schema,
)


def main() -> int:
    failures: list[str] = []

    try:
        _, validator, known_profiles = load_schema_and_registry()
    except Exception as exc:
        print(f"[FAIL] setup error: {exc}")
        return 1

    example_manifests = manifest_paths(EXAMPLES_ROOT)
    template_manifests = manifest_paths(TEMPLATES_ROOT)

    if not EXAMPLES_ROOT.exists():
        failures.append("interop/submissions/examples directory is missing")
    if not TEMPLATES_ROOT.exists():
        failures.append("interop/submissions/templates directory is missing")
    if not example_manifests:
        failures.append("no example submission manifests found under interop/submissions/examples/*/submission.json")
    if not template_manifests:
        failures.append("no template submission manifests found under interop/submissions/templates/*/submission.json")

    checked = 0
    for path in example_manifests + template_manifests:
        checked += 1
        manifest, errors = validate_schema(path, validator)
        if manifest is None:
            failures.extend([f"{path}: {error}" for error in errors])
            continue

        errors.extend(
            validate_common_rules(
                path,
                manifest,
                known_profiles,
                require_existing_refs=path.parent.parent.name == "examples",
            )
        )
        integrity_status, integrity_errors = validate_integrity_manifest(path.parent)
        if integrity_status == "invalid":
            errors.extend(integrity_errors)
        if errors:
            failures.extend([f"{path}: {error}" for error in errors])
        else:
            print(f"[OK] {path} (integrity: {integrity_status})")

    if failures:
        for failure in failures:
            print(f"[FAIL] {failure}")
        print(f"Interop submission example/template validation failed with {len(failures)} issue(s).")
        return 1

    print(f"OK: validated {checked} interop submission manifest(s) across examples/templates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
