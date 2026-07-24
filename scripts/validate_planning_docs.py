#!/usr/bin/env python3
"""Validate canonical planning and repository-truth status without parsing arbitrary prose."""

from __future__ import annotations

import json
import re
import runpy
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BACKLOG = "AICP_Backlog"
ROADMAP = "ROADMAP.md"
BASELINE = "docs/process/AICP_Repo_Truth_Baseline.md"
STATUS = "docs/process/repo_truth_status.json"
PROFILE_REGISTRY = "registry/aicp_profiles.json"
MESSAGE_REGISTRY = "registry/message_types.json"
TRANSPORT_REGISTRY = "registry/transport_bindings.json"
IUT_CASES = "conformance/iut/cases.json"
INTEROP_MATRIX = "interop/interop_matrix.json"
PAIRWISE_VALIDATOR = "scripts/interop_submission_validation.py"
SUITE_CATALOG = "conformance/runner/_suite_catalog.py"
SNAPSHOT = "dist/releases/snapshots/AICP_SNAPSHOT_0.1.0-dev.json"

EXPECTED_MILESTONES = {
    "M58": "Repo-Truth Rebaseline",
    "M59": "Authenticated Base Evidence Reachability",
    "M60": "Exact Contract Agreement Core",
    "M61": "Multi-Profile Composition and CAPNEG v2",
    "M62": "Generalized External Evidence Framework",
    "M63": "Tier-1 External Profile TCK",
    "M64": "Live Transport and Binding Interoperability",
    "M65": "Registered Message Surface Completion",
    "M66": "Clean-Room Pairwise Interop Harness",
    "M67": "Security Coverage Closure",
    "M68": "Governance and Standard Maturity",
    "M69": "Release Engineering and RC Repackaging",
    "M70": "External Plugfest Readiness",
}
ALLOWED_MILESTONE_STATUSES = {"in_progress", "planned", "shipped"}
NO_WORK_REMAINS = "no remaining in-repo protocol backlog milestones"
ROADMAP_ROLE = "<!-- repo-truth-role: shipped-current-next -->"
BACKLOG_ROLE = "<!-- repo-truth-role: remaining-work -->"


def _text(root: Path, relative: str) -> str:
    path = root / relative
    if not path.is_file():
        raise FileNotFoundError(f"missing required file: {relative}")
    return path.read_text(encoding="utf-8")


def _json(root: Path, relative: str) -> Any:
    return json.loads(_text(root, relative))


def _heading_ids(text: str) -> set[str]:
    ids: set[str] = set()
    for line in text.splitlines():
        if re.match(r"^#{2,3}\s+", line):
            ids.update(match.upper() for match in re.findall(r"\bM\d+[a-z]?\b", line, re.IGNORECASE))
    return ids


def _milestone_errors(root: Path, status: dict[str, Any], roadmap: str, backlog: str) -> list[str]:
    errors: list[str] = []
    milestones = status.get("milestones")
    if not isinstance(milestones, list):
        return ["repo-truth status milestones must be a list"]

    ids = [item.get("id") for item in milestones if isinstance(item, dict)]
    if len(ids) != len(set(ids)):
        errors.append("every current/next/backlog milestone must have a unique ID")
    if set(ids) != set(EXPECTED_MILESTONES):
        errors.append(
            "repo-truth milestone IDs must be exactly "
            + ", ".join(EXPECTED_MILESTONES)
            + f"; found {', '.join(sorted(str(value) for value in ids))}"
        )

    roadmap_ids = _heading_ids(roadmap)
    backlog_ids = _heading_ids(backlog)
    overlap = sorted(roadmap_ids & backlog_ids)
    if overlap:
        errors.append("roadmap and backlog milestone headings overlap: " + ", ".join(overlap))

    if ROADMAP_ROLE not in roadmap:
        errors.append(f"{ROADMAP} is missing its stable repo-truth role marker")
    if BACKLOG_ROLE not in backlog:
        errors.append(f"{BACKLOG} is missing its stable repo-truth role marker")

    planned = 0
    for item in milestones:
        if not isinstance(item, dict):
            errors.append("milestone entries must be objects")
            continue
        milestone_id = item.get("id")
        title = item.get("title")
        milestone_status = item.get("status")
        document = item.get("document")
        if EXPECTED_MILESTONES.get(str(milestone_id)) != title:
            errors.append(f"{milestone_id}: title does not match the recorded milestone sequence")
        if milestone_status not in ALLOWED_MILESTONE_STATUSES:
            errors.append(f"{milestone_id}: unsupported status {milestone_status!r}")
        if milestone_status == "planned":
            planned += 1
            if document != BACKLOG:
                errors.append(f"{milestone_id}: planned milestone must resolve to {BACKLOG}")
        else:
            if document != ROADMAP:
                errors.append(f"{milestone_id}: current/shipped milestone must resolve to {ROADMAP}")
        if not isinstance(document, str) or not (root / document).is_file():
            errors.append(f"{milestone_id}: milestone document does not resolve: {document!r}")
        else:
            document_text = roadmap if document == ROADMAP else backlog
            if str(milestone_id) not in _heading_ids(document_text):
                errors.append(f"{milestone_id}: no milestone heading exists in {document}")

    if planned and NO_WORK_REMAINS in backlog.lower():
        errors.append("backlog cannot claim that no work remains while planned milestones exist")
    if "**Status:** Delivered" in backlog:
        errors.append("backlog must not contain delivered-status ledger markers")
    return errors


def _version_errors(status: dict[str, Any], version: str, baseline: str) -> list[str]:
    errors: list[str] = []
    status_version = status.get("current_version")
    if status_version != version:
        errors.append(f"repo-truth version mismatch: VERSION={version!r}, status={status_version!r}")
    marker = f"<!-- repo-truth-current-version: {version} -->"
    if marker not in baseline:
        errors.append("canonical baseline current-version marker does not match VERSION")
    return errors


def _evidence_claim_errors(root: Path, status: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    matrix = _json(root, INTEROP_MATRIX)
    real_submissions = matrix.get("real_submissions", [])
    if not isinstance(real_submissions, list):
        errors.append("interop matrix real_submissions must be a list")
        real_submissions = []

    interop = status.get("interop_evidence", {})
    if interop.get("real_external_submission_count") != len(real_submissions):
        errors.append("real external submission count does not match the generated interop matrix")
    if interop.get("dry_run_count") != len(matrix.get("dry_run_artifacts", [])):
        errors.append("dry-run count does not match the generated interop matrix")
    if interop.get("instructional_artifact_count") != len(matrix.get("instructional_artifacts", [])):
        errors.append("instructional-artifact count does not match the generated interop matrix")
    if interop.get("externally_demonstrated_profiles") and not real_submissions:
        errors.append("externally demonstrated profile claims require a real external submission")

    pairwise_source = _text(root, PAIRWISE_VALIDATOR)
    pairwise_fail_closed = "PAIRWISE_JOINT_EVIDENCE_REQUIRED" in pairwise_source
    if interop.get("pairwise_publication_available") and pairwise_fail_closed:
        errors.append("pairwise publication cannot be available while the validator fails closed")
    if interop.get("pairwise_demonstrated"):
        pairwise_rows = [row for row in real_submissions if row.get("claim_type") == "pairwise_interop"]
        if not pairwise_rows:
            errors.append("pairwise-demonstrated status requires a real pairwise submission")

    profiles = status.get("profiles", [])
    if any(item.get("independent_external_evidence") for item in profiles) and not real_submissions:
        errors.append("profile independent-external-evidence claims require a real external submission")

    security = status.get("security_review", {})
    artifacts = security.get("external_review_artifacts", [])
    if security.get("external_independent_review_completed"):
        if not artifacts:
            errors.append("completed external security review requires an actual review artifact")
        for relative in artifacts:
            if not isinstance(relative, str) or not (root / relative).is_file():
                errors.append(f"external security review artifact does not resolve: {relative!r}")
            elif "SELF_REVIEW" in relative.upper():
                errors.append("internal SELF_REVIEW cannot count as an external security review")

    coverage_text = _text(root, "security_review/COVERAGE_MAP.md")
    coverage_rows = [
        line
        for line in coverage_text.splitlines()
        if line.startswith("|") and re.search(r"\|\s*(?:Strong|Partial|Doc-only)\s*\|", line)
    ]
    partial_rows = [
        line for line in coverage_rows if re.search(r"\|\s*Partial\s*\|", line)
    ]
    if security.get("coverage_map_rows") != len(coverage_rows):
        errors.append("security coverage-map row count is stale")
    if security.get("partial_coverage_rows") != len(partial_rows):
        errors.append("security partial-coverage row count is stale")
    if security.get("internal_self_review_completed") is not (
        root / "security_review/SELF_REVIEW.md"
    ).is_file():
        errors.append("internal self-review status is stale")
    return errors


def _load_profile_outputs(root: Path) -> dict[str, str]:
    namespace = runpy.run_path(str(root / SUITE_CATALOG))
    profile_catalogs = namespace["PROFILE_CATALOGS"]["profiles"]
    return {catalog: output for catalog, output in profile_catalogs}


def _is_tracked(root: Path, relative: str) -> bool | None:
    if not (root / ".git").exists():
        return None
    result = subprocess.run(
        ["git", "-C", str(root), "ls-files", "--error-unmatch", relative],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0


def _profile_errors(root: Path, status: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    registry = _json(root, PROFILE_REGISTRY)
    registry_by_id = {item["id"]: item for item in registry}
    status_profiles = status.get("profiles", [])
    status_by_id = {item.get("id"): item for item in status_profiles if isinstance(item, dict)}
    iut_profiles = _json(root, IUT_CASES).get("profiles", {})
    catalog_outputs = _load_profile_outputs(root)

    if set(status_by_id) != set(registry_by_id):
        errors.append("repo-truth profile IDs must exactly match registry/aicp_profiles.json")

    for profile_id, registry_entry in registry_by_id.items():
        item = status_by_id.get(profile_id)
        if not item:
            continue
        if item.get("registry_status") != registry_entry.get("status"):
            errors.append(f"{profile_id}: registry status mismatch")

        catalog_ref = item.get("profile_catalog")
        if not isinstance(catalog_ref, str) or not (root / catalog_ref).is_file():
            errors.append(f"{profile_id}: profile catalog does not resolve")
            continue
        catalog = _json(root, catalog_ref)
        catalog_id = f"{catalog.get('profile_id')}@{catalog.get('profile_version')}"
        if catalog_id != profile_id:
            errors.append(f"{profile_id}: profile catalog identifies {catalog_id}")
        if item.get("required_suites") != catalog.get("required_suites"):
            errors.append(f"{profile_id}: required_suites do not match the profile catalog")
        for suite_ref in item.get("required_suites", []):
            if not (root / suite_ref).is_file():
                errors.append(f"{profile_id}: required suite does not resolve: {suite_ref}")

        expected_output = catalog_outputs.get(catalog_ref)
        if item.get("internal_report_output") != expected_output:
            errors.append(f"{profile_id}: internal report output does not match the conformance catalog")
        tracked = _is_tracked(root, str(expected_output))
        if tracked is not None and item.get("tracked_report_present") is not tracked:
            errors.append(f"{profile_id}: tracked_report_present does not match git")

        has_iut = profile_id in iut_profiles
        if item.get("external_iut_target") is not has_iut:
            errors.append(f"{profile_id}: external-IUT target status does not match cases.json")
        if has_iut:
            iut = iut_profiles[profile_id]
            if iut.get("profile_catalog") != catalog_ref:
                errors.append(f"{profile_id}: IUT profile catalog does not match the profile map")
            mandatory_degraded = any(
                case.get("expected_degraded") is True or case.get("expected_skipped_checks")
                for case in iut.get("full_profile", {}).get("consumer_cases", [])
                if isinstance(case, dict)
            )
            expected_mark_status = (
                "blocked_by_mandatory_degraded_probe"
                if mandatory_degraded
                else "reachable_for_eligible_external_implementation"
            )
        else:
            expected_mark_status = "no_external_iut_target"
        if item.get("external_mark_status") != expected_mark_status:
            errors.append(f"{profile_id}: external mark reachability is inconsistent with IUT coverage")

    summary = status.get("profile_summary", {})
    stable = sum(item.get("status") == "stable" for item in registry)
    experimental = sum(item.get("status") == "experimental" for item in registry)
    reachable = sum(
        item.get("external_mark_status") == "reachable_for_eligible_external_implementation"
        for item in status_profiles
    )
    expected_summary = {
        "registered": len(registry),
        "stable": stable,
        "experimental": experimental,
        "external_iut_targets": len(iut_profiles),
        "ordinary_external_mark_reachable_targets": reachable,
        "externally_demonstrated": sum(
            bool(item.get("independent_external_evidence")) for item in status_profiles
        ),
    }
    if summary != expected_summary:
        errors.append(f"profile_summary does not match derived catalogs: expected {expected_summary}")
    return errors


def _walk_message_types(value: Any, found: set[str]) -> None:
    if isinstance(value, dict):
        message_type = value.get("message_type")
        if isinstance(message_type, str):
            found.add(message_type)
        for child in value.values():
            _walk_message_types(child, found)
    elif isinstance(value, list):
        for child in value:
            _walk_message_types(child, found)


def _fixture_message_types(path: Path) -> set[str]:
    found: set[str] = set()
    if not path.is_file():
        return found
    if path.suffix == ".jsonl":
        values = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    else:
        values = [json.loads(path.read_text(encoding="utf-8"))]
    for value in values:
        _walk_message_types(value, found)
    return found


def _derive_message_surface(root: Path) -> dict[str, Any]:
    registry = _json(root, MESSAGE_REGISTRY)
    registered = {item["id"] for item in registry}
    payload = {message_type: set() for message_type in registered}
    suites = {message_type: set() for message_type in registered}
    positive = {message_type: set() for message_type in registered}
    negative = {message_type: set() for message_type in registered}

    for suite_path in sorted((root / "conformance").glob("**/*.json")):
        suite = json.loads(suite_path.read_text(encoding="utf-8"))
        if not isinstance(suite, dict):
            continue
        suite_ref = suite_path.relative_to(root).as_posix()
        payload_map = suite.get("payload_schema_map", {})
        if isinstance(payload_map, dict):
            for message_type, schema_ref in payload_map.items():
                if message_type in registered:
                    payload[message_type].add(str(schema_ref))
                    suites[message_type].add(suite_ref)

        transcripts = suite.get("transcripts", [])
        if not isinstance(transcripts, list):
            continue
        for case in transcripts:
            if not isinstance(case, dict):
                continue
            fixture_ref = case.get("path") or case.get("fixture") or case.get("transcript")
            if not isinstance(fixture_ref, str):
                continue
            message_types = _fixture_message_types(root / fixture_ref)
            message_types.update(
                item for item in case.get("expected_message_types", []) if isinstance(item, str)
            )
            target = positive if case.get("expect_pass", True) else negative
            for message_type in message_types & registered:
                suites[message_type].add(suite_ref)
                target[message_type].add(fixture_ref)

    missing_positive = sorted(message_type for message_type in registered if not positive[message_type])
    return {
        "registered_count": len(registered),
        "payload_schema_mapped_count": sum(bool(payload[item]) for item in registered),
        "suite_referenced_count": sum(bool(suites[item]) for item in registered),
        "positive_fixture_referenced_count": sum(bool(positive[item]) for item in registered),
        "negative_fixture_referenced_count": sum(bool(negative[item]) for item in registered),
        "missing_positive_fixture_types": missing_positive,
        "gap_milestone": "M65",
    }


def _binding_errors(root: Path, status: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    registered = {item["id"] for item in _json(root, TRANSPORT_REGISTRY)}
    binding_evidence = status.get("binding_evidence", [])
    live_paths_present = False
    for item in binding_evidence:
        binding_id = item.get("id")
        if binding_id not in registered:
            errors.append(f"binding evidence references unknown registry ID: {binding_id}")
        suite_ref = item.get("suite")
        if not isinstance(suite_ref, str) or not (root / suite_ref).is_file():
            errors.append(f"{binding_id}: binding suite does not resolve")
            continue
        suite = _json(root, suite_ref)
        if item.get("static_case_count") != len(suite.get("cases", [])):
            errors.append(f"{binding_id}: static case count does not match the binding suite")
        for live_path in item.get("live_test_paths", []):
            live_paths_present = True
            if not isinstance(live_path, str) or not (root / live_path).exists():
                errors.append(f"{binding_id}: live test path does not resolve: {live_path!r}")
    if any(item.get("live_binding_tested") for item in status.get("profiles", [])) and not live_paths_present:
        errors.append("profile map cannot claim live binding coverage while only static cases exist")
    return errors


def _capability_errors(root: Path, status: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    capability = status.get("capability_evidence", {}).get("aicp.session_state_projection.v1")
    iut_cases = _json(root, IUT_CASES)
    iut_runner = _text(root, "conformance/iut/aicp_iut_runner.py")
    suite_exists = (root / "conformance/extensions/OR_SESSION_STATE_PROJECTION_V1.json").is_file()
    expected = {
        "status": ["shipped", "experimental", "internally_verified", "externally_testable"],
        "external_test_path": "separate_smoke_capability_run",
        "ordinary_compatibility_mark": False,
        "independent_external_evidence": False,
    }
    if capability != expected:
        errors.append("strict session-state projection status does not match the canonical capability model")
    if "session_state_projection" not in iut_cases or not suite_exists:
        errors.append("strict session-state projection evidence paths do not resolve")
    if "FULL_PROFILE_OVERLAYS_NOT_SUPPORTED" not in iut_runner:
        errors.append("strict session-state projection status expects a fail-closed full-profile overlay guard")
    return errors


def _release_engineering_errors(root: Path, status: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    release = status.get("release_engineering", {})
    snapshot = _json(root, SNAPSHOT)
    if release.get("snapshot_id") != snapshot.get("snapshot_id"):
        errors.append("release-engineering snapshot_id does not match the tracked snapshot")

    outputs = _load_profile_outputs(root)
    if release.get("profile_report_outputs") != len(outputs):
        errors.append("profile report output count does not match the conformance catalog")
    tracked_values = [_is_tracked(root, output) for output in outputs.values()]
    if all(value is not None for value in tracked_values):
        tracked_count = sum(bool(value) for value in tracked_values)
        if release.get("tracked_profile_reports") != tracked_count:
            errors.append("tracked profile report count does not match git")

    root_dependency_manifest = any(
        (root / name).is_file()
        for name in ("requirements.txt", "pyproject.toml", "Pipfile", "environment.yml")
    )
    if release.get("root_validation_dependency_manifest") is not root_dependency_manifest:
        errors.append("root validation dependency-manifest status is stale")
    shell_declared = bool(re.search(r"(?m)^SHELL\s*[:?+]?=", _text(root, "Makefile")))
    if release.get("cross_platform_make_shell_declared") is not shell_declared:
        errors.append("cross-platform Make shell status is stale")
    return errors


def validate(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    try:
        status = _json(root, STATUS)
        roadmap = _text(root, ROADMAP)
        backlog = _text(root, BACKLOG)
        baseline = _text(root, BASELINE)
        version = _text(root, "VERSION").strip()
    except (FileNotFoundError, json.JSONDecodeError) as exc:
        return [str(exc)]

    if status.get("canonical_document") != BASELINE:
        errors.append("repo-truth status canonical_document does not point to the canonical baseline")
    if f"<!-- repo-truth-status: {STATUS} -->" not in baseline:
        errors.append("canonical baseline does not point back to the machine-readable status companion")
    if status.get("planning_roles") != {
        "roadmap": "shipped_current_next",
        "backlog": "remaining_work",
    }:
        errors.append("planning roles must keep roadmap status separate from backlog remaining work")

    errors.extend(_version_errors(status, version, baseline))
    errors.extend(_milestone_errors(root, status, roadmap, backlog))
    errors.extend(_evidence_claim_errors(root, status))
    errors.extend(_profile_errors(root, status))
    errors.extend(_binding_errors(root, status))
    errors.extend(_capability_errors(root, status))
    errors.extend(_release_engineering_errors(root, status))

    derived_message_surface = _derive_message_surface(root)
    if status.get("message_surface") != derived_message_surface:
        errors.append(
            "registered message-surface status is stale; expected "
            + json.dumps(derived_message_surface, sort_keys=True)
        )

    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("[FAIL] planning-doc and repo-truth validation failed")
        for error in errors:
            print(f" - {error}")
        return 1
    print("OK: planning-doc and repo-truth validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
