#!/usr/bin/env python3
"""Shared helpers for validating AICP interop submission manifests."""

from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SUBMISSIONS_ROOT = ROOT / "interop" / "submissions"
EXAMPLES_ROOT = SUBMISSIONS_ROOT / "examples"
TEMPLATES_ROOT = SUBMISSIONS_ROOT / "templates"
SCHEMA_PATH = SUBMISSIONS_ROOT / "submission.schema.json"
INTEGRITY_SCHEMA_PATH = SUBMISSIONS_ROOT / "integrity.schema.json"
PROFILE_REGISTRY_PATH = ROOT / "registry" / "aicp_profiles.json"
IUT_CASES_PATH = ROOT / "conformance" / "iut" / "cases.json"
IUT_REPORT_SCHEMA_PATH = ROOT / "conformance" / "iut" / "iut_report_v1.schema.json"
IUT_TCK_RELEASES_PATH = ROOT / "conformance" / "iut" / "tck_releases.json"
IUT_DIR = ROOT / "conformance" / "iut"
RUNNER_DIR = ROOT / "conformance" / "runner"
for import_path in (IUT_DIR, RUNNER_DIR):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from _runner_context import build_validator as build_local_validator  # noqa: E402
from _runner_provenance import canonical_content_digest, sha256_file  # noqa: E402
from aicp_iut_catalog import mandatory_case_ids  # noqa: E402
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
PAIRWISE_JOINT_EVIDENCE_ERROR = (
    "PAIRWISE_JOINT_EVIDENCE_REQUIRED: real pairwise_interop publication is disabled until "
    "a dedicated joint-execution format binds one shared run, both named builds, and "
    "artifacts consumed in every required direction"
)


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

    optional_string_fields = ["peer_implementation_id", "peer_implementation_version", "notes"]
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

    profile_refs = manifest.get("profile_refs")
    if profile_refs is not None:
        if not isinstance(profile_refs, list) or not profile_refs:
            errors.append("profile_refs must be a non-empty array when present")
        else:
            for index, profile_ref in enumerate(profile_refs):
                if not isinstance(profile_ref, dict):
                    errors.append(f"profile_refs[{index}] must be an object")
                    continue
                if set(profile_ref) != {"profile_id", "profile_version"}:
                    errors.append(f"profile_refs[{index}] must contain only profile_id and profile_version")
                for field in ("profile_id", "profile_version"):
                    if not isinstance(profile_ref.get(field), str) or not profile_ref.get(field):
                        errors.append(f"profile_refs[{index}].{field} must be a non-empty string")

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
        if not manifest.get("peer_implementation_version"):
            errors.append("peer_implementation_version is required for pairwise_interop claims")
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
    data = path.read_bytes()
    if path.suffix.lower() in {".json", ".jsonl", ".md", ".py", ".ts", ".mjs", ".yml", ".yaml"}:
        data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    hasher.update(data)
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
    kind = classify_artifact_kind(path, manifest)
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

    profile_refs = manifest.get("profile_refs")
    if isinstance(profile_refs, list):
        ref_ids = {
            item.get("profile_id")
            for item in profile_refs
            if isinstance(item, dict) and isinstance(item.get("profile_id"), str)
        }
        declared_ids = {item for item in manifest.get("profile_ids", []) if isinstance(item, str)}
        if ref_ids != declared_ids:
            errors.append("profile_refs profile_id values must exactly match profile_ids")

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

    try:
        is_public_submission = path.resolve().is_relative_to(SUBMISSIONS_ROOT.resolve())
    except AttributeError:  # pragma: no cover - Python < 3.9 compatibility
        is_public_submission = str(path.resolve()).startswith(str(SUBMISSIONS_ROOT.resolve()))
    if kind == "submission" and require_existing_refs and is_public_submission:
        errors.extend(_validate_strong_report_evidence(path, manifest))

    return errors


def _profile_claims(manifest: dict[str, Any]) -> list[tuple[str, str]]:
    refs = manifest.get("profile_refs")
    if not isinstance(refs, list):
        return []
    return [
        (item["profile_id"], item["profile_version"])
        for item in refs
        if isinstance(item, dict)
        and isinstance(item.get("profile_id"), str)
        and isinstance(item.get("profile_version"), str)
    ]


def _profile_catalog(profile_id: str, profile_version: str) -> tuple[Path | None, dict[str, Any] | None]:
    for catalog_path in sorted((ROOT / "conformance" / "profiles").glob("PF_*.json")):
        try:
            catalog = load_json(catalog_path)
        except Exception:
            continue
        if (
            isinstance(catalog, dict)
            and catalog.get("profile_id") == profile_id
            and catalog.get("profile_version") == profile_version
        ):
            return catalog_path, catalog
    return None, None


def _eligible_external_profile_report(
    report: dict[str, Any],
    *,
    implementation_id: str,
    implementation_version: str,
    profile_id: str,
    profile_version: str,
) -> list[str]:
    errors: list[str] = []
    schema = load_json(IUT_REPORT_SCHEMA_PATH)
    validator = build_local_validator(schema, IUT_REPORT_SCHEMA_PATH)
    if validator is None:
        return ["IUT_REPORT_SCHEMA_VALIDATION_UNAVAILABLE"]
    schema_errors = sorted(validator.iter_errors(report), key=lambda item: list(item.path))
    if schema_errors:
        return [
            "IUT_REPORT_SCHEMA_INVALID: "
            + ("/" + "/".join(str(part) for part in error.path) if error.path else "/")
            + f": {error.message}"
            for error in schema_errors
        ]

    catalog = load_json(IUT_CASES_PATH)
    target = f"{profile_id}@{profile_version}"
    profile_config = catalog.get("profiles", {}).get(target)
    if not isinstance(profile_config, dict):
        return [f"no full-profile IUT catalog exists for {target}"]
    if report.get("execution_mode") != "full-profile":
        errors.append("IUT_SMOKE_EVIDENCE_INELIGIBLE: execution_mode must be 'full-profile'")

    subject = report.get("execution_subject")
    if report.get("report_format_version") != "1.0":
        errors.append("report_format_version must be '1.0'")
    if not isinstance(subject, dict) or subject.get("kind") != "external_implementation":
        errors.append("execution_subject.kind must be 'external_implementation'")
    else:
        if subject.get("implementation_id") != implementation_id:
            errors.append("execution_subject.implementation_id does not match submission manifest")
        if subject.get("implementation_version") != implementation_version:
            errors.append("execution_subject.implementation_version does not match submission manifest")
        if (
            not isinstance(subject.get("implementation_digest"), str)
            or not subject.get("implementation_digest")
            or subject.get("implementation_digest") == "unknown"
        ):
            errors.append("execution_subject.implementation_digest must be present")
    release_registry = load_json(IUT_TCK_RELEASES_PATH)
    tck = report.get("tck_release")
    release = next(
        (
            item
            for item in release_registry.get("releases", [])
            if isinstance(item, dict)
            and isinstance(tck, dict)
            and item.get("release_id") == tck.get("release_id")
        ),
        None,
    )
    if not isinstance(release, dict):
        errors.append("report does not resolve to a registered IUT TCK release")
        release_profile: dict[str, Any] = {}
    else:
        release_profile = release.get("profiles", {}).get(target) or {}
        if not release_profile:
            errors.append(f"registered TCK release does not support {target}")
        expected_case_digest = release.get("case_catalog", {}).get("content_digest")
        expected_runner_digest = release.get("runner_bundle", {}).get("digest")
        if tck.get("registry_digest") != sha256_file(IUT_TCK_RELEASES_PATH):
            errors.append("TCK registry digest does not match the checked-in release registry")
        if tck.get("case_catalog_digest") != expected_case_digest:
            errors.append("TCK case-catalog digest does not match the registered release")
        if tck.get("runner_bundle_digest") != expected_runner_digest:
            errors.append("TCK runner-bundle digest does not match the registered release")
        runner = report.get("runner")
        if (
            not isinstance(runner, dict)
            or runner.get("name") != "aicp-iut-runner"
            or runner.get("source_revision") != expected_runner_digest
        ):
            errors.append("report runner provenance does not match the registered TCK runner bundle")

    profile = report.get("profile")
    if not isinstance(profile, dict):
        errors.append("report must contain profile provenance")
    else:
        if profile.get("profile_id") != profile_id or profile.get("profile_version") != profile_version:
            errors.append(f"report profile must be exactly {profile_id}@{profile_version}")
        catalog_path, product_profile = _profile_catalog(profile_id, profile_version)
        if catalog_path is None or product_profile is None:
            errors.append(f"no conformance profile catalog exists for {profile_id}@{profile_version}")
        else:
            expected_digest = release_profile.get("profile_catalog", {}).get("content_digest")
            if profile.get("profile_digest") != expected_digest:
                errors.append("profile provenance digest does not match the registered TCK release")
    if report.get("passed") is not True:
        errors.append("report must have passed=true")
    if report.get("degraded") is not False:
        errors.append("report must have degraded=false")
    if report.get("skipped_checks") not in ([], None):
        errors.append("report must not contain skipped checks")
    if report.get("failures") != []:
        errors.append("report failures must be an empty array")

    suite = report.get("suite")
    expected_suite_digest = release.get("case_catalog", {}).get("content_digest") if release else None
    if (
        not isinstance(suite, dict)
        or suite.get("suite_id") != catalog.get("suite_id")
        or suite.get("suite_version") != catalog.get("suite_version")
        or suite.get("suite_digest") != expected_suite_digest
    ):
        errors.append("report suite provenance does not match the registered IUT case catalog")

    expected_suites = {
        item.get("path"): item.get("content_digest")
        for item in release_profile.get("required_suites", [])
        if isinstance(item, dict)
    }
    reported_suites = report.get("required_suites")
    actual_suite_records: dict[str, str] = {}
    if isinstance(reported_suites, list):
        for record in reported_suites:
            if not isinstance(record, dict):
                continue
            matching_ref = next(
                (
                    suite_ref
                    for suite_ref in expected_suites
                    if load_json(ROOT / suite_ref).get("suite_id") == record.get("suite_id")
                ),
                None,
            )
            if matching_ref is not None:
                if matching_ref in actual_suite_records:
                    errors.append(f"duplicate required suite provenance for {matching_ref}")
                actual_suite_records[matching_ref] = str(record.get("suite_digest"))
    if actual_suite_records != expected_suites:
        errors.append("required suite provenance does not exactly match the registered TCK release")

    expected_inputs = {
        item.get("path"): item.get("content_digest")
        for item in release_profile.get("required_input_artifacts", [])
        if isinstance(item, dict)
    }
    inputs = report.get("input_artifacts")
    input_counts = Counter(
        item.get("path") for item in inputs if isinstance(item, dict)
    ) if isinstance(inputs, list) else Counter()
    if any(count != 1 for count in input_counts.values()):
        errors.append("report input_artifacts contains duplicate paths")
    actual_inputs = {
        item.get("path"): item.get("content_digest")
        for item in inputs or []
        if isinstance(item, dict) and item.get("path") in expected_inputs
    } if isinstance(inputs, list) else {}
    if actual_inputs != expected_inputs:
        errors.append("report input provenance does not contain every registered fixture/vector digest")

    expected_generated_ids = {
        str(item["case_id"])
        for item in profile_config["full_profile"]["producer_scenarios"]
    }
    generated = report.get("generated_artifacts")
    generated_counts = Counter(
        item.get("artifact_id") for item in generated if isinstance(item, dict)
    ) if isinstance(generated, list) else Counter()
    if set(generated_counts) != expected_generated_ids or any(count != 1 for count in generated_counts.values()):
        errors.append("generated artifacts do not exactly cover every mandatory producer scenario")
    for item in generated or []:
        if not isinstance(item, dict):
            continue
        if item.get("content_digest") != canonical_content_digest(item.get("content")):
            errors.append(f"generated artifact digest mismatch for {item.get('artifact_id')}")

    expected_cases = mandatory_case_ids(catalog, target, "full-profile")
    case_results = report.get("case_results")
    case_counts = Counter(
        item.get("case_id") for item in case_results if isinstance(item, dict)
    ) if isinstance(case_results, list) else Counter()
    expected_counts = Counter(expected_cases)
    if case_counts != expected_counts:
        missing = sorted((expected_counts - case_counts).elements())
        duplicate_or_unknown = sorted((case_counts - expected_counts).elements())
        errors.append(
            "mandatory IUT case coverage mismatch"
            + (f"; missing={missing}" if missing else "")
            + (f"; duplicate_or_unknown={duplicate_or_unknown}" if duplicate_or_unknown else "")
        )
    if isinstance(case_results, list) and any(item.get("passed") is not True for item in case_results if isinstance(item, dict)):
        errors.append("every mandatory IUT case result must have passed=true")

    expected_mark = profile_config.get("expected_mark")
    computed_marks = [expected_mark] if not errors and isinstance(expected_mark, str) else []
    if report.get("compatibility_marks") != computed_marks:
        errors.append(
            "compatibility_marks do not equal independently computed full-profile eligibility marks"
        )
    return errors


def _validate_strong_report_evidence(path: Path, manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    claims = _profile_claims(manifest)
    if not claims:
        return ["real submissions require exact profile_refs with profile_id and profile_version"]

    reports: list[tuple[str, dict[str, Any]]] = []
    for ref in manifest.get("report_refs", []):
        if not isinstance(ref, str):
            continue
        target = path.parent / ref
        if not target.is_file():
            continue
        try:
            report = load_json(target)
        except Exception:
            continue
        if isinstance(report, dict):
            reports.append((ref, report))

    claim_type = manifest.get("claim_type")
    implementation_id = manifest.get("implementation_id")
    implementation_version = manifest.get("implementation_version")
    if not isinstance(implementation_id, str) or not isinstance(implementation_version, str):
        return errors

    if claim_type in {"implements_profile", "compatible_with_profile"}:
        if manifest.get("evidence_status") != "reproducible":
            return errors
        for profile_id, profile_version in claims:
            eligible = False
            report_errors: list[str] = []
            for ref, report in reports:
                current = _eligible_external_profile_report(
                    report,
                    implementation_id=implementation_id,
                    implementation_version=implementation_version,
                    profile_id=profile_id,
                    profile_version=profile_version,
                )
                if not current:
                    eligible = True
                    break
                report_errors.append(f"{ref}: " + "; ".join(current))
            if not eligible:
                errors.append(
                    f"no eligible external IUT report proves {profile_id}@{profile_version} for "
                    f"{implementation_id}@{implementation_version}"
                )
                errors.extend(report_errors)
        return errors

    if claim_type != "pairwise_interop":
        return errors
    return [PAIRWISE_JOINT_EVIDENCE_ERROR]


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
