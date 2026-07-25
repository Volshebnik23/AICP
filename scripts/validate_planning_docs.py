#!/usr/bin/env python3
"""Validate canonical planning and repository truth without parsing arbitrary prose."""

from __future__ import annotations

import json
import re
import runpy
import subprocess
import sys
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from repo_truth import (  # noqa: E402
    BASELINE_BEGIN,
    BASELINE_END,
    PLANNED_TABLE_BEGIN,
    PLANNED_TABLE_END,
    PROFILE_TABLE_BEGIN,
    PROFILE_TABLE_END,
    derive_interop_evidence,
    derive_message_surface,
    extract_generated_section,
    profile_block_markers,
    render_baseline_facts,
    render_planned_milestones,
    render_profile_status_block,
    render_profile_status_table,
    summarize_message_entries,
)


ROOT = Path(__file__).resolve().parents[1]
BACKLOG = "AICP_Backlog"
ROADMAP = "ROADMAP.md"
BASELINE = "docs/process/AICP_Repo_Truth_Baseline.md"
STATUS = "docs/process/repo_truth_status.json"
PROFILE_DOC = "docs/profiles/AICP_Profiles.md"
PROFILE_REGISTRY = "registry/aicp_profiles.json"
TRANSPORT_REGISTRY = "registry/transport_bindings.json"
IUT_CASES = "conformance/iut/cases.json"
INTEROP_MATRIX = "interop/interop_matrix.json"
PAIRWISE_VALIDATOR = "scripts/interop_submission_validation.py"
SUITE_CATALOG = "conformance/runner/_suite_catalog.py"
SNAPSHOT = "dist/releases/snapshots/AICP_SNAPSHOT_0.1.0-dev.json"
EXTERNAL_REVIEW_CONTRACT = "security_review/external_reviews/README.md"
EXTERNAL_REVIEW_LOCATION = ("security_review", "external_reviews", "completed")

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
VISIBLE_MILESTONE_STATUS = {
    "in_progress": "In progress",
    "planned": "Planned",
    "shipped": "Shipped",
}
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


def _heading_records(text: str) -> dict[str, list[str]]:
    records: dict[str, list[str]] = {}
    pattern = re.compile(
        r"^#{2,3}\s+.*?\b(M\d+[a-z]?)\s+[—-]\s+(.+?)\s*$",
        re.IGNORECASE,
    )
    for line in text.splitlines():
        match = pattern.match(line)
        if match:
            records.setdefault(match.group(1).upper(), []).append(match.group(2))
    return records


def _heading_ids(text: str) -> set[str]:
    return set(_heading_records(text))


def _milestone_marker_statuses(text: str) -> dict[str, list[str]]:
    records: dict[str, list[str]] = {}
    for milestone_id, status in re.findall(
        r"<!-- milestone-status: (M\d+[a-z]?) (in_progress|planned|shipped) -->",
        text,
        flags=re.IGNORECASE,
    ):
        records.setdefault(milestone_id.upper(), []).append(status.lower())
    return records


def _visible_status_after_marker(
    text: str, milestone_id: str, milestone_status: str
) -> bool:
    marker = f"<!-- milestone-status: {milestone_id} {milestone_status} -->"
    marker_index = text.find(marker)
    if marker_index < 0:
        return False
    for line in text[marker_index + len(marker) :].splitlines():
        if not line.strip():
            continue
        expected = f"- **Status:** {VISIBLE_MILESTONE_STATUS[milestone_status]}."
        return line.strip() == expected
    return False


def _milestone_errors(
    root: Path, status: dict[str, Any], roadmap: str, backlog: str
) -> list[str]:
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

    roadmap_headings = _heading_records(roadmap)
    backlog_headings = _heading_records(backlog)
    overlap = sorted(set(roadmap_headings) & set(backlog_headings))
    if overlap:
        errors.append(
            "roadmap and backlog milestone headings overlap: " + ", ".join(overlap)
        )
    if ROADMAP_ROLE not in roadmap:
        errors.append(f"{ROADMAP} is missing its stable repo-truth role marker")
    if BACKLOG_ROLE not in backlog:
        errors.append(f"{BACKLOG} is missing its stable repo-truth role marker")

    roadmap_markers = _milestone_marker_statuses(roadmap)
    backlog_markers = _milestone_marker_statuses(backlog)
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
            errors.append(
                f"{milestone_id}: title does not match the recorded milestone sequence"
            )
        if milestone_status not in ALLOWED_MILESTONE_STATUSES:
            errors.append(f"{milestone_id}: unsupported status {milestone_status!r}")
            continue
        if milestone_status == "planned":
            planned += 1
            if document != BACKLOG:
                errors.append(
                    f"{milestone_id}: planned milestone must resolve to {BACKLOG}"
                )
        elif document != ROADMAP:
            errors.append(
                f"{milestone_id}: current/shipped milestone must resolve to {ROADMAP}"
            )

        if not isinstance(document, str) or not (root / document).is_file():
            errors.append(
                f"{milestone_id}: milestone document does not resolve: {document!r}"
            )
            continue
        document_text = roadmap if document == ROADMAP else backlog
        document_headings = (
            roadmap_headings if document == ROADMAP else backlog_headings
        )
        titles = document_headings.get(str(milestone_id), [])
        if titles != [title]:
            errors.append(
                f"{milestone_id}: owning document must contain one exact title "
                f"{title!r}; found {titles}"
            )

        all_marker_statuses = roadmap_markers.get(
            str(milestone_id), []
        ) + backlog_markers.get(str(milestone_id), [])
        if all_marker_statuses != [milestone_status]:
            errors.append(
                f"{milestone_id}: status marker must occur once and equal "
                f"{milestone_status!r}; found {all_marker_statuses}"
            )
        owning_markers = (
            roadmap_markers if document == ROADMAP else backlog_markers
        )
        if owning_markers.get(str(milestone_id)) != [milestone_status]:
            errors.append(
                f"{milestone_id}: status marker is not in owning document {document}"
            )
        if not _visible_status_after_marker(
            document_text, str(milestone_id), milestone_status
        ):
            errors.append(
                f"{milestone_id}: visible status does not match machine status "
                f"{milestone_status!r}"
            )

    actual_planned_table = extract_generated_section(
        roadmap, PLANNED_TABLE_BEGIN, PLANNED_TABLE_END
    )
    expected_planned_table = render_planned_milestones(status)
    if actual_planned_table != expected_planned_table:
        errors.append(
            "Roadmap planned-milestone table is stale relative to repo-truth status"
        )
    if planned and NO_WORK_REMAINS in backlog.lower():
        errors.append(
            "backlog cannot claim that no work remains while planned milestones exist"
        )
    if "**Status:** Delivered" in backlog:
        errors.append("backlog must not contain delivered-status ledger markers")
    return errors


def _version_errors(
    status: dict[str, Any], version: str, baseline: str
) -> list[str]:
    errors: list[str] = []
    status_version = status.get("current_version")
    if status_version != version:
        errors.append(
            f"repo-truth version mismatch: VERSION={version!r}, status={status_version!r}"
        )
    marker = f"<!-- repo-truth-current-version: {version} -->"
    if marker not in baseline:
        errors.append(
            "canonical baseline current-version marker does not match VERSION"
        )
    return errors


def _baseline_generated_errors(
    status: dict[str, Any], baseline: str
) -> list[str]:
    if extract_generated_section(
        baseline, BASELINE_BEGIN, BASELINE_END
    ) != render_baseline_facts(status):
        return [
            "canonical human-readable repo-truth facts are stale relative to JSON"
        ]
    return []


def _external_security_review_errors(
    root: Path, security: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    if security.get("artifact_contract") != EXTERNAL_REVIEW_CONTRACT:
        errors.append("external security-review artifact contract path is stale")
    if not (root / EXTERNAL_REVIEW_CONTRACT).is_file():
        errors.append("external security-review artifact contract does not resolve")
    expected_location = "/".join(EXTERNAL_REVIEW_LOCATION) + "/"
    if security.get("artifact_location") != expected_location:
        errors.append("external security-review artifact location is stale")

    artifacts = security.get("external_review_artifacts")
    if not isinstance(artifacts, list):
        return errors + ["external_review_artifacts must be a list of records"]
    completed = security.get("external_independent_review_completed")
    if completed is not bool(artifacts):
        errors.append(
            "external security-review completion must exactly match contracted "
            "completed-artifact records"
        )

    for index, artifact in enumerate(artifacts):
        prefix = f"external review artifact {index}"
        if not isinstance(artifact, dict):
            errors.append(f"{prefix}: record must be an object")
            continue
        path_value = artifact.get("path")
        if not isinstance(path_value, str) or not path_value:
            errors.append(f"{prefix}: artifact path is required")
            continue
        pure_path = PurePosixPath(path_value)
        if (
            pure_path.is_absolute()
            or ".." in pure_path.parts
            or pure_path.parts[:3] != EXTERNAL_REVIEW_LOCATION
            or len(pure_path.parts) < 4
        ):
            errors.append(
                f"{prefix}: artifact must be below {expected_location}"
            )
        if "SELF_REVIEW" in path_value.upper():
            errors.append(
                f"{prefix}: internal SELF_REVIEW cannot count as an external review"
            )
        if not (root / path_value).is_file():
            errors.append(f"{prefix}: artifact does not resolve: {path_value!r}")

        if artifact.get("review_type") != "independent_external":
            errors.append(
                f"{prefix}: review_type must be 'independent_external'"
            )
        reviewer = artifact.get("reviewer")
        if (
            not isinstance(reviewer, str)
            or not reviewer.strip()
            or reviewer.strip().lower() in {"unknown", "tbd", "n/a", "placeholder"}
        ):
            errors.append(f"{prefix}: real reviewer identity/organization is required")
        completion_date = artifact.get("completion_date")
        try:
            parsed_date = (
                date.fromisoformat(completion_date)
                if isinstance(completion_date, str)
                else None
            )
        except ValueError:
            parsed_date = None
        if parsed_date is None or parsed_date.isoformat() != completion_date:
            errors.append(f"{prefix}: completion_date must be ISO YYYY-MM-DD")
        reviewed_scope = artifact.get("reviewed_scope")
        if (
            not isinstance(reviewed_scope, list)
            or not reviewed_scope
            or any(
                not isinstance(item, str) or not item.strip()
                for item in reviewed_scope
            )
        ):
            errors.append(f"{prefix}: reviewed_scope must be a non-empty string list")
        final_status = artifact.get("final_status")
        if final_status not in {"completed", "completed_with_findings"}:
            errors.append(
                f"{prefix}: final_status must identify a completed review"
            )
        remediation_ref = artifact.get("findings_remediation_ref")
        if final_status == "completed_with_findings" and (
            not isinstance(remediation_ref, str) or not remediation_ref
        ):
            errors.append(
                f"{prefix}: completed_with_findings requires findings/remediation"
            )
        if isinstance(remediation_ref, str) and remediation_ref:
            remediation_path = PurePosixPath(remediation_ref)
            if remediation_path.is_absolute() or ".." in remediation_path.parts:
                errors.append(f"{prefix}: findings/remediation path must be repo-relative")
            elif not (root / remediation_ref).is_file():
                errors.append(
                    f"{prefix}: findings/remediation reference does not resolve"
                )
    return errors


def _evidence_claim_errors(root: Path, status: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    matrix = _json(root, INTEROP_MATRIX)
    pairwise_source = _text(root, PAIRWISE_VALIDATOR)
    pairwise_fail_closed = "PAIRWISE_JOINT_EVIDENCE_REQUIRED" in pairwise_source
    interop = status.get("interop_evidence", {})
    try:
        expected_interop, profile_flags = derive_interop_evidence(
            matrix,
            status.get("profiles", []),
            pairwise_publication_available=(
                bool(interop.get("pairwise_publication_available"))
                and not pairwise_fail_closed
            ),
        )
    except ValueError as exc:
        return [str(exc)]

    if interop != expected_interop:
        errors.append(
            "interop evidence status does not match eligible profile-specific "
            f"computed evidence: expected {json.dumps(expected_interop, sort_keys=True)}"
        )
    if pairwise_fail_closed and (
        interop.get("pairwise_publication_available")
        or interop.get("pairwise_demonstrated")
    ):
        errors.append(
            "pairwise publication and demonstration must remain false while "
            "PAIRWISE_JOINT_EVIDENCE_REQUIRED fails closed"
        )
    for profile in status.get("profiles", []):
        profile_id = profile.get("id")
        if profile.get("independent_external_evidence") is not profile_flags.get(
            profile_id
        ):
            errors.append(
                f"{profile_id}: independent external evidence must derive from an "
                "eligible row containing the exact computed profile mark"
            )
    demonstrated_from_flags = sorted(
        profile_id for profile_id, demonstrated in profile_flags.items() if demonstrated
    )
    if interop.get("externally_demonstrated_profiles") != demonstrated_from_flags:
        errors.append(
            "externally_demonstrated_profiles must exactly match profile-level flags"
        )

    security = status.get("security_review", {})
    errors.extend(_external_security_review_errors(root, security))
    coverage_text = _text(root, "security_review/COVERAGE_MAP.md")
    coverage_rows = [
        line
        for line in coverage_text.splitlines()
        if line.startswith("|")
        and re.search(r"\|\s*(?:Strong|Partial|Doc-only)\s*\|", line)
    ]
    partial_rows = [
        line
        for line in coverage_rows
        if re.search(r"\|\s*Partial\s*\|", line)
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
    status_by_id = {
        item.get("id"): item for item in status_profiles if isinstance(item, dict)
    }
    iut_profiles = _json(root, IUT_CASES).get("profiles", {})
    catalog_outputs = _load_profile_outputs(root)
    profile_doc = _text(root, PROFILE_DOC)

    if set(status_by_id) != set(registry_by_id):
        errors.append(
            "repo-truth profile IDs must exactly match registry/aicp_profiles.json"
        )
    errors.extend(_profile_document_errors(status, profile_doc))

    for profile_id, registry_entry in registry_by_id.items():
        item = status_by_id.get(profile_id)
        if not item:
            continue
        if item.get("registry_status") != registry_entry.get("status"):
            errors.append(f"{profile_id}: registry status mismatch")
        if item.get("repository_availability") != "shipped":
            errors.append(f"{profile_id}: repository availability must be shipped")
        if item.get("internal_evidence") != "available":
            errors.append(f"{profile_id}: internal evidence status is stale")

        catalog_ref = item.get("profile_catalog")
        if not isinstance(catalog_ref, str) or not (root / catalog_ref).is_file():
            errors.append(f"{profile_id}: profile catalog does not resolve")
            continue
        catalog = _json(root, catalog_ref)
        catalog_id = f"{catalog.get('profile_id')}@{catalog.get('profile_version')}"
        if catalog_id != profile_id:
            errors.append(f"{profile_id}: profile catalog identifies {catalog_id}")
        if item.get("compatibility_mark") != catalog.get("compatibility_mark"):
            errors.append(f"{profile_id}: compatibility mark does not match catalog")
        if item.get("required_suites") != catalog.get("required_suites"):
            errors.append(
                f"{profile_id}: required_suites do not match the profile catalog"
            )
        for suite_ref in item.get("required_suites", []):
            if not (root / suite_ref).is_file():
                errors.append(
                    f"{profile_id}: required suite does not resolve: {suite_ref}"
                )

        expected_output = catalog_outputs.get(catalog_ref)
        if item.get("internal_report_output") != expected_output:
            errors.append(
                f"{profile_id}: internal report output does not match the "
                "conformance catalog"
            )
        tracked = _is_tracked(root, str(expected_output))
        if (
            tracked is not None
            and item.get("tracked_report_present") is not tracked
        ):
            errors.append(
                f"{profile_id}: tracked_report_present does not match git"
            )

        has_iut = profile_id in iut_profiles
        if item.get("external_iut_target") is not has_iut:
            errors.append(
                f"{profile_id}: external-IUT target status does not match cases.json"
            )
        if has_iut:
            iut = iut_profiles[profile_id]
            if iut.get("profile_catalog") != catalog_ref:
                errors.append(
                    f"{profile_id}: IUT profile catalog does not match profile map"
                )
            mandatory_degraded = any(
                case.get("expected_degraded") is True
                or case.get("expected_skipped_checks")
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
            errors.append(
                f"{profile_id}: external mark reachability is inconsistent with "
                "IUT coverage"
            )

    summary = status.get("profile_summary", {})
    expected_summary = {
        "registered": len(registry),
        "stable": sum(item.get("status") == "stable" for item in registry),
        "experimental": sum(
            item.get("status") == "experimental" for item in registry
        ),
        "external_iut_targets": len(iut_profiles),
        "ordinary_external_mark_reachable_targets": sum(
            item.get("external_mark_status")
            == "reachable_for_eligible_external_implementation"
            for item in status_profiles
        ),
        "externally_demonstrated": sum(
            bool(item.get("independent_external_evidence"))
            for item in status_profiles
        ),
    }
    if summary != expected_summary:
        errors.append(
            f"profile_summary does not match derived catalogs: expected {expected_summary}"
        )
    return errors


def _profile_document_errors(
    status: dict[str, Any], profile_doc: str
) -> list[str]:
    errors: list[str] = []
    if extract_generated_section(
        profile_doc, PROFILE_TABLE_BEGIN, PROFILE_TABLE_END
    ) != render_profile_status_table(status):
        errors.append(
            "canonical generated profile-status table is stale relative to repo truth"
        )
    if "**Status:** Available now" in profile_doc:
        errors.append(
            "profile catalog must not use ambiguous Available now status prose"
        )
    for profile in status.get("profiles", []):
        profile_id = profile.get("id")
        if not isinstance(profile_id, str):
            continue
        begin, end = profile_block_markers(profile_id)
        if extract_generated_section(
            profile_doc, begin, end
        ) != render_profile_status_block(profile):
            errors.append(
                f"{profile_id}: generated profile truth block is stale or missing"
            )
    return errors


def _json_pointer_exists(root: Path, schema: dict[str, Any]) -> bool:
    schema_file = schema.get("file")
    pointer = schema.get("pointer")
    if (
        not isinstance(schema_file, str)
        or not isinstance(pointer, str)
        or not (root / schema_file).is_file()
        or not (pointer.startswith("#/") or pointer.startswith("/"))
    ):
        return False
    try:
        value: Any = _json(root, schema_file)
        pointer_path = pointer[1:] if pointer.startswith("#") else pointer
        for raw_token in pointer_path[1:].split("/"):
            token = raw_token.replace("~1", "/").replace("~0", "~")
            if isinstance(value, dict):
                value = value[token]
            elif isinstance(value, list):
                value = value[int(token)]
            else:
                return False
    except (KeyError, IndexError, ValueError, TypeError, json.JSONDecodeError):
        return False
    return True


def _message_surface_errors(
    root: Path, message_surface: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    try:
        expected = derive_message_surface(root)
    except (ValueError, json.JSONDecodeError) as exc:
        return [str(exc)]
    entries = message_surface.get("entries")
    if not isinstance(entries, list):
        return ["message_surface.entries must be a list"]
    entry_ids = [
        entry.get("id") for entry in entries if isinstance(entry, dict)
    ]
    expected_ids = [entry["id"] for entry in expected["entries"]]
    if entry_ids != sorted(entry_ids):
        errors.append("message-surface entries must be ordered by message type ID")
    if entry_ids != expected_ids:
        errors.append(
            "message-surface entry IDs must exactly match all registered message types"
        )

    expected_by_id = {entry["id"]: entry for entry in expected["entries"]}
    for entry in entries:
        if not isinstance(entry, dict):
            errors.append("message-surface entries must be objects")
            continue
        message_id = entry.get("id")
        expected_entry = expected_by_id.get(message_id)
        if expected_entry is None:
            continue
        if entry.get("owner") != expected_entry["owner"]:
            errors.append(f"{message_id}: message owner is incorrect")
        schema = entry.get("payload_schema")
        if not isinstance(schema, dict) or not _json_pointer_exists(root, schema):
            errors.append(
                f"{message_id}: payload schema file/pointer does not resolve"
            )
        if schema != expected_entry["payload_schema"]:
            errors.append(
                f"{message_id}: payload schema mapping is not the canonical owner mapping"
            )
        suites = entry.get("suites")
        if not isinstance(suites, list) or any(
            not isinstance(ref, str) or not (root / ref).is_file()
            for ref in suites
        ):
            errors.append(f"{message_id}: conformance suite reference does not resolve")
        if suites != expected_entry["suites"]:
            errors.append(f"{message_id}: conformance suite references are stale")
        for field in ("positive_fixtures", "negative_fixtures"):
            fixtures = entry.get(field)
            if not isinstance(fixtures, list) or any(
                not isinstance(ref, str) or not (root / ref).is_file()
                for ref in fixtures
            ):
                errors.append(f"{message_id}: {field} contains a nonexistent fixture")
            if fixtures != expected_entry[field]:
                errors.append(f"{message_id}: {field} is stale")
        if entry.get("coverage_status") != expected_entry["coverage_status"]:
            errors.append(f"{message_id}: coverage status is false")
        if entry.get("gap_milestone") != expected_entry["gap_milestone"]:
            errors.append(f"{message_id}: gap milestone is inconsistent with coverage")

    derived_summary = summarize_message_entries(
        [entry for entry in entries if isinstance(entry, dict)]
    )
    if message_surface.get("summary") != derived_summary:
        errors.append(
            "message-surface aggregate summary must be derived from entries"
        )
    if message_surface != expected:
        errors.append("registered message-surface status is stale")
    return errors


def _binding_errors(root: Path, status: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    registered = {item["id"] for item in _json(root, TRANSPORT_REGISTRY)}
    binding_evidence = status.get("binding_evidence", [])
    live_paths_present = False
    for item in binding_evidence:
        binding_id = item.get("id")
        if binding_id not in registered:
            errors.append(
                f"binding evidence references unknown registry ID: {binding_id}"
            )
        suite_ref = item.get("suite")
        if not isinstance(suite_ref, str) or not (root / suite_ref).is_file():
            errors.append(f"{binding_id}: binding suite does not resolve")
            continue
        suite = _json(root, suite_ref)
        if item.get("static_case_count") != len(suite.get("cases", [])):
            errors.append(
                f"{binding_id}: static case count does not match binding suite"
            )
        for live_path in item.get("live_test_paths", []):
            live_paths_present = True
            if not isinstance(live_path, str) or not (root / live_path).exists():
                errors.append(
                    f"{binding_id}: live test path does not resolve: {live_path!r}"
                )
    if (
        any(item.get("live_binding_tested") for item in status.get("profiles", []))
        and not live_paths_present
    ):
        errors.append(
            "profile map cannot claim live binding coverage while only static cases exist"
        )
    return errors


def _capability_errors(root: Path, status: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    capability = status.get("capability_evidence", {}).get(
        "aicp.session_state_projection.v1"
    )
    iut_cases = _json(root, IUT_CASES)
    iut_runner = _text(root, "conformance/iut/aicp_iut_runner.py")
    suite_exists = (
        root / "conformance/extensions/OR_SESSION_STATE_PROJECTION_V1.json"
    ).is_file()
    expected = {
        "status": [
            "shipped",
            "experimental",
            "internally_verified",
            "externally_testable",
        ],
        "external_test_path": "separate_smoke_capability_run",
        "ordinary_compatibility_mark": False,
        "independent_external_evidence": False,
    }
    if capability != expected:
        errors.append(
            "strict session-state projection status does not match canonical model"
        )
    if "session_state_projection" not in iut_cases or not suite_exists:
        errors.append("strict session-state projection evidence paths do not resolve")
    if "FULL_PROFILE_OVERLAYS_NOT_SUPPORTED" not in iut_runner:
        errors.append(
            "strict session-state projection status expects a fail-closed "
            "full-profile overlay guard"
        )
    return errors


def _release_engineering_errors(
    root: Path, status: dict[str, Any]
) -> list[str]:
    errors: list[str] = []
    release = status.get("release_engineering", {})
    snapshot = _json(root, SNAPSHOT)
    if release.get("snapshot_id") != snapshot.get("snapshot_id"):
        errors.append(
            "release-engineering snapshot_id does not match tracked snapshot"
        )
    outputs = _load_profile_outputs(root)
    if release.get("profile_report_outputs") != len(outputs):
        errors.append(
            "profile report output count does not match conformance catalog"
        )
    tracked_values = [_is_tracked(root, output) for output in outputs.values()]
    if all(value is not None for value in tracked_values):
        tracked_count = sum(bool(value) for value in tracked_values)
        if release.get("tracked_profile_reports") != tracked_count:
            errors.append("tracked profile report count does not match git")
    root_dependency_manifest = any(
        (root / name).is_file()
        for name in ("requirements.txt", "pyproject.toml", "Pipfile", "environment.yml")
    )
    if (
        release.get("root_validation_dependency_manifest")
        is not root_dependency_manifest
    ):
        errors.append("root validation dependency-manifest status is stale")
    shell_declared = bool(
        re.search(r"(?m)^SHELL\s*[:?+]?=", _text(root, "Makefile"))
    )
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

    if status.get("schema_version") != 2:
        errors.append("repo-truth schema_version must be 2")
    if status.get("canonical_document") != BASELINE:
        errors.append(
            "repo-truth status canonical_document does not point to canonical baseline"
        )
    if f"<!-- repo-truth-status: {STATUS} -->" not in baseline:
        errors.append(
            "canonical baseline does not point back to machine-readable companion"
        )
    if status.get("planning_roles") != {
        "roadmap": "shipped_current_next",
        "backlog": "remaining_work",
    }:
        errors.append(
            "planning roles must keep roadmap status separate from backlog work"
        )
    errors.extend(_baseline_generated_errors(status, baseline))

    errors.extend(_version_errors(status, version, baseline))
    errors.extend(_milestone_errors(root, status, roadmap, backlog))
    errors.extend(_evidence_claim_errors(root, status))
    errors.extend(_profile_errors(root, status))
    errors.extend(_message_surface_errors(root, status.get("message_surface", {})))
    errors.extend(_binding_errors(root, status))
    errors.extend(_capability_errors(root, status))
    errors.extend(_release_engineering_errors(root, status))
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
