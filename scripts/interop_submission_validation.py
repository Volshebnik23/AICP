#!/usr/bin/env python3
"""Shared helpers for validating AICP interop submission manifests."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SUBMISSIONS_ROOT = ROOT / "interop" / "submissions"
EXAMPLES_ROOT = SUBMISSIONS_ROOT / "examples"
TEMPLATES_ROOT = SUBMISSIONS_ROOT / "templates"
SCHEMA_PATH = SUBMISSIONS_ROOT / "submission.schema.json"
INTEGRITY_SCHEMA_PATH = SUBMISSIONS_ROOT / "integrity.schema.json"
PROFILE_REGISTRY_PATH = ROOT / "registry" / "aicp_profiles.json"
RESERVED_DIRS = {"examples", "templates"}
INTEGRITY_FILENAME = "bundle-integrity.json"
INTEGRITY_MANIFEST_VERSION = "1.0"
ALLOWED_DIGEST_ALGS = {"sha256": hashlib.sha256}
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
        errors.append("claim_type must be one of: " + ", ".join(sorted(ALLOWED_CLAIM_TYPES)))

    evidence_status = manifest.get("evidence_status")
    if isinstance(evidence_status, str) and evidence_status not in ALLOWED_EVIDENCE_STATUSES:
        errors.append("evidence_status must be one of: " + ", ".join(sorted(ALLOWED_EVIDENCE_STATUSES)))

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


def fallback_integrity_schema_errors(manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    required_fields = {"submission_id", "manifest_version", "generated_at", "digest_alg", "files"}
    missing = sorted(required_fields - set(manifest.keys()))
    for field in missing:
        errors.append(f"missing required property '{field}'")

    for field in ["submission_id", "manifest_version", "generated_at", "digest_alg"]:
        value = manifest.get(field)
        if value is not None and not isinstance(value, str):
            errors.append(f"{field} must be a string")

    files = manifest.get("files")
    if files is None:
        return errors
    if not isinstance(files, list) or not files:
        errors.append("files must be a non-empty array")
        return errors

    for index, entry in enumerate(files):
        if not isinstance(entry, dict):
            errors.append(f"files[{index}] must be an object")
            continue
        for field in ["path", "digest"]:
            value = entry.get(field)
            if not isinstance(value, str) or not value:
                errors.append(f"files[{index}].{field} must be a non-empty string")
        rel_path = entry.get("path")
        if isinstance(rel_path, str) and (
            rel_path.startswith("/") or rel_path.startswith("..") or "/../" in rel_path
        ):
            errors.append(f"files[{index}].path must be a relative non-traversing path: {rel_path}")

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


def validate_integrity_schema(path: Path, validator: Any) -> tuple[dict[str, Any] | None, list[str]]:
    try:
        obj = load_json(path)
    except Exception as exc:
        return None, [f"invalid JSON: {exc}"]

    if not isinstance(obj, dict):
        return None, ["integrity manifest must be a JSON object"]

    if validator is None:
        return obj, fallback_integrity_schema_errors(obj)

    errors = [error.message for error in sorted(validator.iter_errors(obj), key=lambda err: list(err.path))]
    return obj, errors


def classify_manifest_path(path: Path) -> str:
    parent = path.parent.parent.name
    if parent == "examples":
        return "example"
    if parent == "templates":
        return "template"
    return "submission"


def classify_artifact_kind(path: Path, manifest: dict[str, Any] | None = None) -> str:
    kind = classify_manifest_path(path)
    if kind != "submission":
        return kind

    identifiers: list[str] = [path.parent.name]
    if isinstance(manifest, dict):
        for field in ("submission_id", "implementation_id"):
            value = manifest.get(field)
            if isinstance(value, str):
                identifiers.append(value)
        for field in ("notes",):
            value = manifest.get(field)
            if isinstance(value, str):
                identifiers.append(value)
        for item in manifest.get("disclosures", []):
            if isinstance(item, str):
                identifiers.append(item)

    lowered = " ".join(identifiers).lower()
    if "dryrun-" in lowered or "dry-run" in lowered or "rehearsal" in lowered:
        return "dry_run"
    return kind


def manifest_tracked_paths(manifest: dict[str, Any]) -> list[Path]:
    tracked_paths = [Path("submission.json")]
    for ref in manifest.get("report_refs", []):
        if isinstance(ref, str) and ref:
            tracked_paths.append(Path(ref))
    return tracked_paths


def compute_file_digest(path: Path, digest_alg: str = "sha256") -> str:
    algorithm = ALLOWED_DIGEST_ALGS.get(digest_alg)
    if algorithm is None:
        raise ValueError(f"unsupported digest algorithm: {digest_alg}")
    hasher = algorithm()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def build_integrity_manifest(
    package_dir: Path,
    submission_id: str,
    tracked_paths: list[Path],
    *,
    generated_at: str,
    digest_alg: str = "sha256",
) -> dict[str, Any]:
    if digest_alg not in ALLOWED_DIGEST_ALGS:
        raise ValueError(f"unsupported digest algorithm: {digest_alg}")

    files: list[dict[str, str]] = []
    seen: set[str] = set()
    for tracked_path in tracked_paths:
        relative_path = tracked_path.as_posix()
        if relative_path in seen:
            continue
        seen.add(relative_path)
        target = package_dir / tracked_path
        if not target.exists() or not target.is_file():
            raise FileNotFoundError(f"cannot add missing package file to integrity manifest: {relative_path}")
        files.append({"path": relative_path, "digest": compute_file_digest(target, digest_alg)})

    if not files:
        raise ValueError("integrity manifest requires at least one tracked file")

    return {
        "submission_id": submission_id,
        "manifest_version": INTEGRITY_MANIFEST_VERSION,
        "generated_at": generated_at,
        "digest_alg": digest_alg,
        "files": files,
    }


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
        errors.append(f"evidence_status must be one of: {', '.join(sorted(ALLOWED_EVIDENCE_STATUSES))}")

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


def validate_bundle_integrity(
    package_dir: Path,
    submission_id: str,
    *,
    integrity_validator: Any | None = None,
) -> tuple[str, list[str]]:
    integrity_path = package_dir / INTEGRITY_FILENAME
    if not integrity_path.exists():
        return "absent", []
    if not integrity_path.is_file():
        return "invalid", [f"{INTEGRITY_FILENAME} exists but is not a file"]

    manifest, errors = validate_integrity_schema(integrity_path, integrity_validator)
    if manifest is None:
        return "invalid", errors

    manifest_submission_id = manifest.get("submission_id")
    if manifest_submission_id != submission_id:
        errors.append(
            f"integrity manifest submission_id '{manifest_submission_id}' does not match submission.json '{submission_id}'"
        )

    manifest_version = manifest.get("manifest_version")
    if manifest_version != INTEGRITY_MANIFEST_VERSION:
        errors.append(
            f"integrity manifest_version must be '{INTEGRITY_MANIFEST_VERSION}'"
        )

    digest_alg = manifest.get("digest_alg")
    if digest_alg not in ALLOWED_DIGEST_ALGS:
        errors.append(
            "integrity digest_alg must be one of: " + ", ".join(sorted(ALLOWED_DIGEST_ALGS))
        )
        return "invalid", errors

    seen_paths: set[str] = set()
    for index, entry in enumerate(manifest.get("files", [])):
        if not isinstance(entry, dict):
            continue
        relative_path = entry.get("path")
        expected_digest = entry.get("digest")
        if not isinstance(relative_path, str) or not isinstance(expected_digest, str):
            continue
        if relative_path in seen_paths:
            errors.append(f"integrity files[{index}].path is duplicated: {relative_path}")
            continue
        seen_paths.add(relative_path)
        if relative_path == INTEGRITY_FILENAME:
            errors.append(f"integrity manifest must not track itself ({INTEGRITY_FILENAME})")
            continue

        target = package_dir / relative_path
        if not target.exists():
            errors.append(f"integrity manifest references missing file: {relative_path}")
            continue
        if not target.is_file():
            errors.append(f"integrity manifest references non-file path: {relative_path}")
            continue

        actual_digest = compute_file_digest(target, digest_alg)
        if actual_digest != expected_digest:
            errors.append(
                f"digest mismatch for {relative_path}: expected {expected_digest}, got {actual_digest}"
            )

    return ("valid", []) if not errors else ("invalid", errors)


def load_schema_and_registry() -> tuple[dict[str, Any], Any, set[str]]:
    schema = load_json(SCHEMA_PATH)
    return schema, load_validator(schema), registry_profile_ids()


def load_integrity_schema_validator() -> tuple[dict[str, Any], Any]:
    schema = load_json(INTEGRITY_SCHEMA_PATH)
    return schema, load_validator(schema)
