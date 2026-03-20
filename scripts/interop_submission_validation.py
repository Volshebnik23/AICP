#!/usr/bin/env python3
"""Shared helpers for validating AICP interop submission manifests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SUBMISSIONS_ROOT = ROOT / "interop" / "submissions"
EXAMPLES_ROOT = SUBMISSIONS_ROOT / "examples"
TEMPLATES_ROOT = SUBMISSIONS_ROOT / "templates"
SCHEMA_PATH = SUBMISSIONS_ROOT / "submission.schema.json"
PROFILE_REGISTRY_PATH = ROOT / "registry" / "aicp_profiles.json"
RESERVED_DIRS = {"examples", "templates"}
ALLOWED_CLAIM_TYPES = {
    "implements_profile",
    "compatible_with_profile",
    "pairwise_interop",
}
ALLOWED_EVIDENCE_STATUSES = {
    "example",
    "template",
    "self_attested",
    "reproducible",
    "pairwise",
}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_validator(schema: dict[str, Any]):
    try:
        from jsonschema import Draft202012Validator  # type: ignore
        from jsonschema import FormatChecker  # type: ignore
    except Exception:
        return None
    return Draft202012Validator(schema, format_checker=FormatChecker())


def registry_profile_ids() -> set[str]:
    registry = load_json(PROFILE_REGISTRY_PATH)
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


def manifest_paths(root: Path) -> list[Path]:
    if not root.exists():
        return []
    return sorted(root.glob("*/submission.json"))


def fallback_schema_errors(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = {
        "submission_id",
        "implementation_id",
        "implementation_version",
        "profile_ids",
        "evidence_types",
        "evidence_status",
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
        "evidence_status",
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

    claim_type = manifest.get("claim_type")
    if isinstance(claim_type, str) and claim_type not in ALLOWED_CLAIM_TYPES:
        errors.append(
            "claim_type must be one of: " + ", ".join(sorted(ALLOWED_CLAIM_TYPES))
        )

    evidence_status = manifest.get("evidence_status")
    if isinstance(evidence_status, str) and evidence_status not in ALLOWED_EVIDENCE_STATUSES:
        errors.append(
            "evidence_status must be one of: " + ", ".join(sorted(ALLOWED_EVIDENCE_STATUSES))
        )

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

    if claim_type == "pairwise_interop":
        if not manifest.get("peer_implementation_id"):
            errors.append("peer_implementation_id is required for pairwise_interop claims")
        if manifest.get("claim_scope") != "pairwise":
            errors.append("claim_scope must be 'pairwise' for pairwise_interop claims")
        report_refs = manifest.get("report_refs")
        if isinstance(report_refs, list) and len(report_refs) < 2:
            errors.append("pairwise_interop claims require at least two report_refs")

    return errors


def validate_schema(path: Path, validator: Any) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        obj = load_json(path)
    except Exception as exc:
        return None, [f"invalid JSON: {exc}"]

    if not isinstance(obj, dict):
        return None, ["submission manifest must be a JSON object"]

    if validator is None:
        return obj, fallback_schema_errors(obj)

    errors = [error.message for error in sorted(validator.iter_errors(obj), key=lambda err: list(err.path))]
    return obj, errors


def classify_manifest_path(path: Path) -> str:
    parent = path.parent.parent.name
    if parent == "examples":
        return "example"
    if parent == "templates":
        return "template"
    return "submission"


def validate_common_rules(
    path: Path,
    manifest: dict[str, Any],
    known_profiles: set[str],
    *,
    require_existing_refs: bool,
) -> list[str]:
    errors: list[str] = []
    kind = classify_manifest_path(path)
    claim_type = manifest.get("claim_type")
    evidence_status = manifest.get("evidence_status")
    disclosures = manifest.get("disclosures")

    if claim_type not in ALLOWED_CLAIM_TYPES:
        errors.append(f"claim_type must be one of: {', '.join(sorted(ALLOWED_CLAIM_TYPES))}")

    if evidence_status not in ALLOWED_EVIDENCE_STATUSES:
        errors.append(
            f"evidence_status must be one of: {', '.join(sorted(ALLOWED_EVIDENCE_STATUSES))}"
        )

    for profile_id in manifest.get("profile_ids", []):
        if isinstance(profile_id, str) and profile_id not in known_profiles:
            errors.append(f"unknown profile_id '{profile_id}' (not present in registry/aicp_profiles.json)")

    if kind == "example":
        if evidence_status != "example":
            errors.append("example manifests must declare evidence_status='example'")
        for field in ["implementation_id", "peer_implementation_id"]:
            value = manifest.get(field)
            if value is not None and isinstance(value, str) and not value.startswith("example-"):
                errors.append(f"example manifests must use fictional {field} values starting with 'example-'")
    elif kind == "template":
        if evidence_status != "template":
            errors.append("template manifests must declare evidence_status='template'")
    else:
        if evidence_status in {"example", "template"}:
            errors.append("real submission folders must not declare evidence_status='example' or 'template'")
        if not isinstance(disclosures, list) or not disclosures:
            errors.append("real submissions must include at least one disclosure entry")

    if evidence_status == "pairwise" and claim_type != "pairwise_interop":
        errors.append("evidence_status='pairwise' requires claim_type='pairwise_interop'")
    if claim_type == "pairwise_interop" and evidence_status not in {"example", "pairwise"}:
        errors.append("pairwise_interop claims must use evidence_status='pairwise' (or 'example' for instructional examples)")
    if evidence_status == "reproducible":
        evidence_types = set(item for item in manifest.get("evidence_types", []) if isinstance(item, str))
        if not ({"conformance_report", "profile_report"} & evidence_types):
            errors.append("reproducible submissions must include conformance_report or profile_report in evidence_types")

    report_refs = manifest.get("report_refs", [])
    for ref in report_refs:
        if not isinstance(ref, str):
            continue
        target = path.parent / ref
        if require_existing_refs and not target.exists():
            errors.append(f"missing referenced file: {ref}")
            continue
        if target.exists() and target.is_dir():
            errors.append(f"referenced path is a directory, expected file: {ref}")
            continue
        if require_existing_refs and target.exists():
            try:
                load_json(target)
            except Exception as exc:
                errors.append(f"referenced file is not valid JSON ({ref}): {exc}")

    return errors


def load_schema_and_registry() -> tuple[dict[str, Any], Any, set[str]]:
    schema = load_json(SCHEMA_PATH)
    return schema, load_validator(schema), registry_profile_ids()
