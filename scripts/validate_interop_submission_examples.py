#!/usr/bin/env python3
"""Validate shipped interop submission examples and templates."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SUBMISSIONS_ROOT = ROOT / "interop" / "submissions"
EXAMPLES_ROOT = SUBMISSIONS_ROOT / "examples"
TEMPLATES_ROOT = SUBMISSIONS_ROOT / "templates"
SCHEMA_PATH = SUBMISSIONS_ROOT / "submission.schema.json"
PROFILE_REGISTRY_PATH = ROOT / "registry" / "aicp_profiles.json"

ALLOWED_CLAIM_TYPES = {
    "implements_profile",
    "compatible_with_profile",
    "pairwise_interop",
}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _fallback_schema_errors(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "submission_id",
        "implementation_id",
        "implementation_version",
        "profile_ids",
        "evidence_types",
        "report_refs",
        "suite_refs",
        "claim_type",
        "claim_scope",
        "generated_at",
    }
    missing = sorted(required_fields - set(manifest.keys()))
    for field in missing:
        errors.append(f"missing required property '{field}'")

    string_fields = [
        "submission_id",
        "implementation_id",
        "implementation_version",
        "claim_type",
        "claim_scope",
        "generated_at",
    ]
    for field in string_fields:
        value = manifest.get(field)
        if value is not None and not isinstance(value, str):
            errors.append(f"{field} must be a string")

    optional_string_fields = ["peer_implementation_id", "notes"]
    for field in optional_string_fields:
        value = manifest.get(field)
        if value is not None and not isinstance(value, str):
            errors.append(f"{field} must be a string when present")

    list_fields = ["profile_ids", "evidence_types", "report_refs", "suite_refs"]
    for field in list_fields:
        value = manifest.get(field)
        if value is None:
            continue
        if not isinstance(value, list) or not value:
            errors.append(f"{field} must be a non-empty array")
        elif not all(isinstance(item, str) and item for item in value):
            errors.append(f"{field} entries must be non-empty strings")

    disclosures = manifest.get("disclosures")
    if disclosures is not None:
        if not isinstance(disclosures, list) or not all(isinstance(item, str) for item in disclosures):
            errors.append("disclosures must be an array of strings when present")

    allowed_scopes = {"self_attested", "pairwise"}
    claim_scope = manifest.get("claim_scope")
    if isinstance(claim_scope, str) and claim_scope not in allowed_scopes:
        errors.append("claim_scope must be one of: pairwise, self_attested")

    for field in ["submission_id", "implementation_id", "peer_implementation_id"]:
        value = manifest.get(field)
        if value is None:
            continue
        if isinstance(value, str) and (value.startswith("/") or "../" in value):
            errors.append(f"{field} must not contain path-like traversal values")

    for ref in manifest.get("report_refs", []):
        if isinstance(ref, str) and (ref.startswith("/") or ref.startswith("..") or "/../" in ref):
            errors.append(f"report_refs entry must be a relative non-traversing path: {ref}")

    if manifest.get("claim_type") == "pairwise_interop":
        if not manifest.get("peer_implementation_id"):
            errors.append("peer_implementation_id is required for pairwise_interop claims")
        if manifest.get("claim_scope") != "pairwise":
            errors.append("claim_scope must be 'pairwise' for pairwise_interop claims")
        report_refs = manifest.get("report_refs")
        if isinstance(report_refs, list) and len(report_refs) < 2:
            errors.append("pairwise_interop claims require at least two report_refs")

    return errors


def _load_validator(schema: dict[str, Any]):
    try:
        from jsonschema import Draft202012Validator  # type: ignore
        from jsonschema import FormatChecker  # type: ignore
    except Exception:
        return None
    return Draft202012Validator(schema, format_checker=FormatChecker())


def _registry_profile_ids() -> set[str]:
    registry = _load_json(PROFILE_REGISTRY_PATH)
    if not isinstance(registry, list):
        raise ValueError("registry/aicp_profiles.json must be a JSON list")
    ids: set[str] = set()
    for entry in registry:
        if isinstance(entry, dict):
            profile_id = entry.get("profile_id")
            if isinstance(profile_id, str) and profile_id:
                ids.add(profile_id)
    if not ids:
        raise ValueError("registry/aicp_profiles.json did not yield any profile_id values")
    return ids


def _manifest_paths(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(root.glob("*/submission.json"))


def _validate_schema(path: Path, validator: Any) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        obj = _load_json(path)
    except Exception as exc:
        return None, [f"invalid JSON: {exc}"]

    if not isinstance(obj, dict):
        return None, ["submission manifest must be a JSON object"]

    if validator is None:
        return obj, _fallback_schema_errors(obj)

    errors = [error.message for error in sorted(validator.iter_errors(obj), key=lambda err: list(err.path))]
    return obj, errors


def _validate_common_rules(path: Path, manifest: dict[str, Any], known_profiles: set[str]) -> list[str]:
    errors: list[str] = []
    claim_type = manifest.get("claim_type")
    if claim_type not in ALLOWED_CLAIM_TYPES:
        errors.append(f"claim_type must be one of: {', '.join(sorted(ALLOWED_CLAIM_TYPES))}")

    for profile_id in manifest.get("profile_ids", []):
        if isinstance(profile_id, str) and profile_id not in known_profiles:
            errors.append(f"unknown profile_id '{profile_id}' (not present in registry/aicp_profiles.json)")

    if path.parent.parent.name == "examples":
        impl_id = manifest.get("implementation_id")
        if isinstance(impl_id, str) and not impl_id.startswith("example-"):
            errors.append("example submissions must use fictional implementation_id values starting with 'example-'")
        peer_id = manifest.get("peer_implementation_id")
        if peer_id is not None and isinstance(peer_id, str) and not peer_id.startswith("example-"):
            errors.append("example submissions must use fictional peer_implementation_id values starting with 'example-'")

    return errors


def _validate_example_refs(path: Path, manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for ref in manifest.get("report_refs", []):
        if not isinstance(ref, str):
            continue
        target = path.parent / ref
        if not target.exists():
            errors.append(f"missing referenced report/example file: {ref}")
            continue
        if target.is_dir():
            errors.append(f"referenced report/example path is a directory, expected file: {ref}")
            continue
        try:
            _load_json(target)
        except Exception as exc:
            errors.append(f"referenced report/example file is not valid JSON ({ref}): {exc}")
    return errors


def _validate_template_refs(path: Path, manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for ref in manifest.get("report_refs", []):
        if not isinstance(ref, str):
            continue
        target = path.parent / ref
        if target.exists() and target.is_dir():
            errors.append(f"template report_ref points to a directory instead of a file: {ref}")
    return errors


def _validate_dir_layout() -> list[str]:
    errors: list[str] = []
    if not EXAMPLES_ROOT.exists():
        errors.append("interop/submissions/examples directory is missing")
    if not TEMPLATES_ROOT.exists():
        errors.append("interop/submissions/templates directory is missing")
    return errors


def main() -> int:
    failures: list[str] = []

    try:
        schema = _load_json(SCHEMA_PATH)
        validator = _load_validator(schema)
        known_profiles = _registry_profile_ids()
    except Exception as exc:
        print(f"[FAIL] setup error: {exc}")
        return 1

    failures.extend(_validate_dir_layout())

    example_manifests = _manifest_paths(EXAMPLES_ROOT)
    template_manifests = _manifest_paths(TEMPLATES_ROOT)

    if not example_manifests:
        failures.append("no example submission manifests found under interop/submissions/examples/*/submission.json")
    if not template_manifests:
        failures.append("no template submission manifests found under interop/submissions/templates/*/submission.json")

    checked = 0
    for path in example_manifests + template_manifests:
        checked += 1
        manifest, errors = _validate_schema(path, validator)
        if manifest is None:
            failures.extend([f"{path.relative_to(ROOT)}: {error}" for error in errors])
            continue

        errors.extend(_validate_common_rules(path, manifest, known_profiles))
        if path.parent.parent.name == "examples":
            errors.extend(_validate_example_refs(path, manifest))
        elif path.parent.parent.name == "templates":
            errors.extend(_validate_template_refs(path, manifest))
        else:
            errors.append("submission manifest must live under interop/submissions/examples/ or interop/submissions/templates/")

        if errors:
            failures.extend([f"{path.relative_to(ROOT)}: {error}" for error in errors])
        else:
            print(f"[OK] {path.relative_to(ROOT)}")

    if failures:
        for failure in failures:
            print(f"[FAIL] {failure}")
        print(f"Interop submission example/template validation failed with {len(failures)} issue(s).")
        return 1

    print(f"OK: validated {checked} interop submission manifest(s) across examples/templates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
