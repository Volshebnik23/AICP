#!/usr/bin/env python3
"""Derive and render the non-normative AICP repository-truth status."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
STATUS_PATH = "docs/process/repo_truth_status.json"
BASELINE_PATH = "docs/process/AICP_Repo_Truth_Baseline.md"
PROFILE_DOC_PATH = "docs/profiles/AICP_Profiles.md"
ROADMAP_PATH = "ROADMAP.md"
PROFILE_REGISTRY_PATH = "registry/aicp_profiles.json"
MESSAGE_REGISTRY_PATH = "registry/message_types.json"
EXTENSION_REGISTRY_PATH = "registry/extension_ids.json"
INTEROP_MATRIX_PATH = "interop/interop_matrix.json"
PAIRWISE_VALIDATOR_PATH = "scripts/interop_submission_validation.py"
CORE_SUITE_PATH = "conformance/core/CT_CORE_0.1.json"
IUT_CASES_PATH = "conformance/iut/cases.json"

BASELINE_BEGIN = "<!-- BEGIN GENERATED REPO-TRUTH FACTS -->"
BASELINE_END = "<!-- END GENERATED REPO-TRUTH FACTS -->"
PROFILE_TABLE_BEGIN = "<!-- BEGIN GENERATED PROFILE STATUS -->"
PROFILE_TABLE_END = "<!-- END GENERATED PROFILE STATUS -->"
PLANNED_TABLE_BEGIN = "<!-- BEGIN GENERATED PLANNED MILESTONES -->"
PLANNED_TABLE_END = "<!-- END GENERATED PLANNED MILESTONES -->"


def load_json(root: Path, relative: str) -> Any:
    return json.loads((root / relative).read_text(encoding="utf-8"))


def profile_block_markers(profile_id: str) -> tuple[str, str]:
    return (
        f"<!-- BEGIN GENERATED PROFILE TRUTH: {profile_id} -->",
        f"<!-- END GENERATED PROFILE TRUTH: {profile_id} -->",
    )


def extract_generated_section(text: str, begin: str, end: str) -> str | None:
    start = text.find(begin)
    if start < 0:
        return None
    finish = text.find(end, start + len(begin))
    if finish < 0:
        return None
    return text[start + len(begin) : finish].strip("\r\n")


def replace_generated_section(text: str, begin: str, end: str, content: str) -> str:
    start = text.find(begin)
    if start < 0:
        raise ValueError(f"missing generated-section marker: {begin}")
    finish = text.find(end, start + len(begin))
    if finish < 0:
        raise ValueError(f"missing generated-section marker: {end}")
    finish += len(end)
    replacement = f"{begin}\n{content.rstrip()}\n{end}"
    return text[:start] + replacement + text[finish:]


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
        values = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
    else:
        values = [json.loads(path.read_text(encoding="utf-8"))]
    for value in values:
        _walk_message_types(value, found)
    return found


def _message_owners(root: Path) -> dict[str, str]:
    messages = load_json(root, MESSAGE_REGISTRY_PATH)
    extensions = load_json(root, EXTENSION_REGISTRY_PATH)
    core_payloads = load_json(root, CORE_SUITE_PATH).get("payload_schema_map", {})

    extensions_by_spec: dict[str, list[str]] = {}
    for extension in extensions:
        spec_path = str(extension["spec_ref"]).split("#", 1)[0]
        extensions_by_spec.setdefault(spec_path, []).append(extension["id"])

    owners: dict[str, str] = {}
    for message in messages:
        message_id = message["id"]
        spec_path = str(message["spec_ref"]).split("#", 1)[0]
        extension_ids = extensions_by_spec.get(spec_path, [])
        if len(extension_ids) == 1:
            owners[message_id] = extension_ids[0]
        elif not extension_ids and message_id in core_payloads:
            owners[message_id] = "Core"
        else:
            raise ValueError(
                f"{message_id}: owner is absent or ambiguous from registry/spec/core taxonomy"
            )
    return owners


def summarize_message_entries(entries: list[dict[str, Any]]) -> dict[str, Any]:
    missing_positive = sorted(
        entry["id"] for entry in entries if not entry.get("positive_fixtures")
    )
    return {
        "registered_count": len(entries),
        "payload_schema_mapped_count": sum(
            isinstance(entry.get("payload_schema"), dict)
            and bool(entry["payload_schema"].get("file"))
            and bool(entry["payload_schema"].get("pointer"))
            for entry in entries
        ),
        "suite_referenced_count": sum(bool(entry.get("suites")) for entry in entries),
        "positive_fixture_referenced_count": sum(
            bool(entry.get("positive_fixtures")) for entry in entries
        ),
        "negative_fixture_referenced_count": sum(
            bool(entry.get("negative_fixtures")) for entry in entries
        ),
        "missing_positive_fixture_types": missing_positive,
        "gap_milestone": "M65" if missing_positive else None,
    }


def derive_message_surface(root: Path = ROOT) -> dict[str, Any]:
    messages = load_json(root, MESSAGE_REGISTRY_PATH)
    registered = {item["id"] for item in messages}
    owners = _message_owners(root)
    suites = {message_id: set() for message_id in registered}
    positive = {message_id: set() for message_id in registered}
    negative = {message_id: set() for message_id in registered}
    canonical_schema_candidates = {message_id: set() for message_id in registered}
    for suite_path in sorted((root / "conformance").glob("**/*.json")):
        try:
            suite = json.loads(suite_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(suite, dict):
            continue
        payload_map = suite.get("payload_schema_map")
        payload_schema_ref = suite.get("payload_schema_ref")
        if isinstance(payload_map, dict):
            suite_ref = suite_path.relative_to(root).as_posix()
            for message_id in payload_map:
                if message_id in registered:
                    suites[message_id].add(suite_ref)

            mapped_owners = {
                owners[message_id]
                for message_id in payload_map
                if message_id in owners
            }
            if len(mapped_owners) == 1 and isinstance(payload_schema_ref, str):
                only_owner = next(iter(mapped_owners))
                for message_id, pointer in payload_map.items():
                    if message_id in registered and owners[message_id] == only_owner:
                        canonical_schema_candidates[message_id].add(
                            (payload_schema_ref, str(pointer))
                        )

        transcripts = suite.get("transcripts")
        if not isinstance(transcripts, list):
            continue
        suite_ref = suite_path.relative_to(root).as_posix()
        for case in transcripts:
            if not isinstance(case, dict):
                continue
            fixture_ref = case.get("path") or case.get("fixture") or case.get("transcript")
            if not isinstance(fixture_ref, str):
                continue
            message_types = _fixture_message_types(root / fixture_ref)
            expected = case.get("expected_message_types", [])
            if isinstance(expected, list):
                message_types.update(item for item in expected if isinstance(item, str))
            target = positive if case.get("expect_pass", True) else negative
            for message_id in message_types & registered:
                suites[message_id].add(suite_ref)
                target[message_id].add(fixture_ref)

    entries: list[dict[str, Any]] = []
    for message_id in sorted(registered):
        candidates = canonical_schema_candidates[message_id]
        if len(candidates) != 1:
            raise ValueError(
                f"{message_id}: expected one owner-pure payload schema mapping, found "
                f"{sorted(candidates)}"
            )
        schema_file, pointer = next(iter(candidates))
        has_positive = bool(positive[message_id])
        entries.append(
            {
                "id": message_id,
                "owner": owners[message_id],
                "payload_schema": {
                    "file": schema_file,
                    "pointer": pointer,
                },
                "suites": sorted(suites[message_id]),
                "positive_fixtures": sorted(positive[message_id]),
                "negative_fixtures": sorted(negative[message_id]),
                "coverage_status": (
                    "complete" if has_positive else "missing_positive_fixture"
                ),
                "gap_milestone": None if has_positive else "M65",
            }
        )

    return {
        "summary": summarize_message_entries(entries),
        "entries": entries,
    }


def _eligible_profile_marks(
    row: dict[str, Any], expected_marks: set[str]
) -> set[str]:
    if (
        row.get("artifact_kind") != "submission"
        or row.get("valid") is not True
        or row.get("evidence_validation_status") != "eligible"
    ):
        return set()
    computed_marks = row.get("computed_marks")
    if not isinstance(computed_marks, list):
        return set()
    return {
        mark
        for mark in computed_marks
        if isinstance(mark, str) and mark in expected_marks
    }


def derive_interop_evidence(
    matrix: dict[str, Any],
    profiles: list[dict[str, Any]],
    *,
    pairwise_publication_available: bool,
) -> tuple[dict[str, Any], dict[str, bool]]:
    real_rows = matrix.get("real_submissions", [])
    if not isinstance(real_rows, list):
        raise ValueError("interop matrix real_submissions must be a list")

    mark_to_profile = {
        item["compatibility_mark"]: item["id"]
        for item in profiles
        if isinstance(item.get("compatibility_mark"), str)
    }
    expected_marks = set(mark_to_profile)
    eligible_rows: list[tuple[dict[str, Any], set[str]]] = []
    demonstrated: set[str] = set()
    for row in real_rows:
        if not isinstance(row, dict):
            continue
        marks = _eligible_profile_marks(row, expected_marks)
        if not marks:
            continue
        eligible_rows.append((row, marks))
        demonstrated.update(mark_to_profile[mark] for mark in marks)

    pairwise_demonstrated = (
        pairwise_publication_available
        and any(
            row.get("claim_type") == "pairwise_interop"
            and row.get("joint_evidence_validation_status") == "eligible"
            for row, _marks in eligible_rows
        )
    )
    flags = {item["id"]: item["id"] in demonstrated for item in profiles}
    evidence = {
        "real_submission_package_count": len(real_rows),
        "eligible_external_submission_count": len(eligible_rows),
        "rejected_real_submission_count": len(real_rows) - len(eligible_rows),
        "externally_demonstrated_profiles": sorted(demonstrated),
        "pairwise_publication_available": pairwise_publication_available,
        "pairwise_demonstrated": pairwise_demonstrated,
        "dry_run_count": len(matrix.get("dry_run_artifacts", [])),
        "instructional_artifact_count": len(
            matrix.get("instructional_artifacts", [])
        ),
    }
    return evidence, flags


def _human_bool(value: bool, *, present: str = "Yes", absent: str = "No") -> str:
    return present if value else absent


def _code_list(values: list[str]) -> str:
    return ", ".join(f"`{value}`" for value in values) if values else "None"


def _mark_status_text(value: str) -> str:
    return {
        "reachable_for_eligible_external_implementation": (
            "Reachable for an eligible external implementation"
        ),
        "blocked_by_mandatory_degraded_probe": (
            "Blocked by the mandatory degraded probe"
        ),
        "no_external_iut_target": "No external-IUT target",
    }.get(value, value)


def derive_external_mark_status(iut_profile: dict[str, Any] | None) -> str:
    """Derive reachability from explicit IUT case-accounting semantics."""

    if iut_profile is None:
        return "no_external_iut_target"
    for case in iut_profile.get("full_profile", {}).get("consumer_cases", []):
        if not isinstance(case, dict):
            return "blocked_by_mandatory_degraded_probe"
        if any(
            field in case
            for field in (
                "expected_degraded",
                "expected_degraded_reasons",
                "expected_skipped_checks",
            )
        ):
            return "blocked_by_mandatory_degraded_probe"
        configured = case.get("expected_execution_observation")
        runtime_options = case.get("runtime_options")
        explicitly_unavailable = (
            isinstance(runtime_options, dict)
            and runtime_options.get("cryptographic_verification") == "unavailable"
        )
        if configured is None:
            if explicitly_unavailable:
                return "blocked_by_mandatory_degraded_probe"
            continue
        reasons = (
            configured.get("degraded_reasons")
            if isinstance(configured, dict)
            else None
        )
        skips = (
            configured.get("skipped_checks")
            if isinstance(configured, dict)
            else None
        )
        if (
            not isinstance(configured, dict)
            or set(configured)
            != {
                "scope",
                "degraded",
                "degraded_reasons",
                "skipped_checks",
            }
            or configured.get("scope") != "case_local_expected"
            or configured.get("degraded") is not True
            or not isinstance(reasons, list)
            or not all(isinstance(value, str) and value for value in reasons or [])
            or len(reasons or []) != len(set(reasons or []))
            or not isinstance(skips, list)
            or not all(isinstance(value, str) and value for value in skips or [])
            or len(skips or []) != len(set(skips or []))
        ):
            return "blocked_by_mandatory_degraded_probe"
    return "reachable_for_eligible_external_implementation"


def render_profile_status_table(status: dict[str, Any]) -> str:
    lines = [
        "| Profile | Repository availability | Registry maturity | Internal evidence | External-IUT target | Ordinary external mark | Independent external evidence |",
        "|---|---|---|---|---|---|---|",
    ]
    for profile in sorted(status["profiles"], key=lambda item: item["id"]):
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{profile['id']}`",
                    str(profile["repository_availability"]).capitalize(),
                    str(profile["registry_status"]).capitalize(),
                    str(profile["internal_evidence"]).capitalize(),
                    _human_bool(profile["external_iut_target"]),
                    _mark_status_text(profile["external_mark_status"]),
                    _human_bool(
                        profile["independent_external_evidence"],
                        present="Present",
                        absent="Absent",
                    ),
                ]
            )
            + " |"
        )
    return "\n".join(lines)


def render_profile_status_block(profile: dict[str, Any]) -> str:
    return "\n".join(
        [
            f"- **Repository availability:** {str(profile['repository_availability']).capitalize()}.",
            f"- **Registry maturity:** {str(profile['registry_status']).capitalize()}.",
            f"- **Internal evidence:** {str(profile['internal_evidence']).capitalize()}.",
            "- **External-IUT target:** "
            + _human_bool(
                profile["external_iut_target"],
                present="Available.",
                absent="Not available.",
            ),
            "- **Ordinary external mark:** "
            + _mark_status_text(profile["external_mark_status"])
            + ".",
            "- **Independent external evidence:** "
            + _human_bool(
                profile["independent_external_evidence"],
                present="Present.",
                absent="Absent.",
            ),
        ]
    )


def render_planned_milestones(status: dict[str, Any]) -> str:
    lines = [
        "| ID | Status | Title | Planning record |",
        "|---|---|---|---|",
    ]
    for milestone in status["milestones"]:
        if milestone["status"] != "planned":
            continue
        lines.append(
            f"| {milestone['id']} | Planned | {milestone['title']} | "
            f"`{milestone['document']}` |"
        )
    return "\n".join(lines)


def render_baseline_facts(status: dict[str, Any]) -> str:
    summary = status["profile_summary"]
    profiles = status["profiles"]
    interop = status["interop_evidence"]
    security = status["security_review"]
    governance = status["governance"]
    message_summary = status["message_surface"]["summary"]
    targets = sorted(item["id"] for item in profiles if item["external_iut_target"])
    reachable = sorted(
        item["id"]
        for item in profiles
        if item["external_mark_status"]
        == "reachable_for_eligible_external_implementation"
    )
    demonstrated = interop["externally_demonstrated_profiles"]
    bindings = status["binding_evidence"]
    live_bindings = sorted(
        item["id"] for item in bindings if item.get("live_test_paths")
    )

    lines = [
        "## Machine-bound repository facts",
        "",
        "| Fact | Current value | Machine evidence |",
        "|---|---|---|",
        f"| Version / release phase | `{status['current_version']}` / `{status['release_phase']}` | `VERSION`, `repo_truth_status.json` |",
        f"| Registered profiles | {summary['registered']} ({summary['stable']} stable, {summary['experimental']} experimental) | `registry/aicp_profiles.json` |",
        f"| External-IUT targets | {summary['external_iut_targets']}: {_code_list(targets)} | `conformance/iut/cases.json` |",
        f"| Ordinary external marks currently reachable | {summary['ordinary_external_mark_reachable_targets']}: {_code_list(reachable)} | profile catalogs and IUT cases |",
        f"| Real submission packages | {interop['real_submission_package_count']} | `interop/interop_matrix.json` |",
        f"| Eligible external submissions | {interop['eligible_external_submission_count']} | public interop eligibility result plus profile computed marks |",
        f"| Rejected/ineligible real packages | {interop['rejected_real_submission_count']} | `interop/interop_matrix.json` |",
        f"| Externally demonstrated profiles | {len(demonstrated)}: {_code_list(demonstrated)} | eligible profile-specific `computed_marks` only |",
        f"| Pairwise publication / demonstration | {_human_bool(interop['pairwise_publication_available'])} / {_human_bool(interop['pairwise_demonstrated'])} | joint-evidence validator status |",
        f"| Live binding paths | {len(live_bindings)}: {_code_list(live_bindings)} | binding evidence map |",
        f"| Independent external security review | {_human_bool(security['external_independent_review_completed'])} | `{security['artifact_contract']}` |",
        f"| Governance model / maturity | `{governance['current_model']}` / `{governance['standard_maturity']}` | `GOVERNANCE.md` |",
        f"| Registered message surface | {message_summary['registered_count']} entries; {len(message_summary['missing_positive_fixture_types'])} missing positive fixtures | `message_surface.entries` |",
        "",
        "### Milestone summary",
        "",
        "| ID | Status | Title | Owning document |",
        "|---|---|---|---|",
    ]
    for milestone in status["milestones"]:
        lines.append(
            f"| {milestone['id']} | {milestone['status']} | {milestone['title']} | "
            f"`{milestone['document']}` |"
        )

    lines.extend(
        [
            "",
            "## Repository-truth evidence table",
            "",
            "| Surface | Repository truth | Independent-evidence boundary | Planned gap |",
            "|---|---|---|---|",
            f"| Profiles | {summary['registered']} shipped catalogs; maturity is {summary['stable']} stable / {summary['experimental']} experimental | {summary['externally_demonstrated']} externally demonstrated profiles | M62, M63, M70 |",
            f"| External submissions | {interop['real_submission_package_count']} real packages; {interop['eligible_external_submission_count']} eligible | Only valid `artifact_kind=submission` rows with `evidence_validation_status=eligible` and expected profile `computed_marks` count | M70 |",
            f"| Pairwise | publication={str(interop['pairwise_publication_available']).lower()}, demonstrated={str(interop['pairwise_demonstrated']).lower()} | A valid eligible joint-execution result is required | M66 |",
            f"| Bindings | {sum(item['static_case_count'] for item in bindings)} static cases; {len(live_bindings)} live paths | Static cases do not prove live independent interoperability | M64 |",
            f"| Security review | internal self-review={str(security['internal_self_review_completed']).lower()}, external completed={str(security['external_independent_review_completed']).lower()} | Only contracted artifacts under `{security['artifact_location']}` may support completion | M67 |",
            f"| Governance | `{governance['current_model']}` | No external standards body is recorded | M68 |",
            f"| Message surface | {message_summary['registered_count']} machine-mapped entries; {len(message_summary['missing_positive_fixture_types'])} positive-fixture gaps | Aggregates are derived from entries | M65 |",
            f"| Release | `{status['release_phase']}` | Repository metadata is not external adoption or GA evidence | M69 |",
        ]
    )
    return "\n".join(lines)


def sync_status(root: Path, status: dict[str, Any]) -> dict[str, Any]:
    registry = {
        item["id"]: item for item in load_json(root, PROFILE_REGISTRY_PATH)
    }
    profiles = sorted(status["profiles"], key=lambda item: item["id"])
    iut_profiles = load_json(root, IUT_CASES_PATH)["profiles"]
    for profile in profiles:
        profile_id = profile["id"]
        profile["registry_status"] = registry[profile_id]["status"]
        profile["repository_availability"] = "shipped"
        profile["internal_evidence"] = "available"
        profile_catalog = load_json(root, profile["profile_catalog"])
        profile["compatibility_mark"] = profile_catalog["compatibility_mark"]
        iut_profile = iut_profiles.get(profile_id)
        profile["external_iut_target"] = iut_profile is not None
        profile["external_mark_status"] = derive_external_mark_status(iut_profile)

    pairwise_source = (root / PAIRWISE_VALIDATOR_PATH).read_text(encoding="utf-8")
    pairwise_fail_closed = "PAIRWISE_JOINT_EVIDENCE_REQUIRED" in pairwise_source
    requested_pairwise_availability = bool(
        status.get("interop_evidence", {}).get("pairwise_publication_available")
    )
    interop, flags = derive_interop_evidence(
        load_json(root, INTEROP_MATRIX_PATH),
        profiles,
        pairwise_publication_available=(
            requested_pairwise_availability and not pairwise_fail_closed
        ),
    )
    for profile in profiles:
        profile["independent_external_evidence"] = flags[profile["id"]]

    status["schema_version"] = 2
    status["profiles"] = profiles
    status["interop_evidence"] = interop
    status["message_surface"] = derive_message_surface(root)
    status["profile_summary"] = {
        "registered": len(profiles),
        "stable": sum(
            item["registry_status"] == "stable" for item in profiles
        ),
        "experimental": sum(
            item["registry_status"] == "experimental" for item in profiles
        ),
        "external_iut_targets": sum(item["external_iut_target"] for item in profiles),
        "ordinary_external_mark_reachable_targets": sum(
            item["external_mark_status"]
            == "reachable_for_eligible_external_implementation"
            for item in profiles
        ),
        "externally_demonstrated": sum(flags.values()),
    }
    security = status["security_review"]
    security["artifact_contract"] = (
        "security_review/external_reviews/README.md"
    )
    security["artifact_location"] = (
        "security_review/external_reviews/completed/"
    )
    return status


def write_generated_truth(root: Path = ROOT) -> None:
    status = sync_status(root, load_json(root, STATUS_PATH))
    (root / STATUS_PATH).write_text(
        json.dumps(status, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    baseline_path = root / BASELINE_PATH
    baseline = replace_generated_section(
        baseline_path.read_text(encoding="utf-8"),
        BASELINE_BEGIN,
        BASELINE_END,
        render_baseline_facts(status),
    )
    baseline_path.write_text(baseline, encoding="utf-8")

    profile_path = root / PROFILE_DOC_PATH
    profile_doc = replace_generated_section(
        profile_path.read_text(encoding="utf-8"),
        PROFILE_TABLE_BEGIN,
        PROFILE_TABLE_END,
        render_profile_status_table(status),
    )
    for profile in status["profiles"]:
        begin, end = profile_block_markers(profile["id"])
        profile_doc = replace_generated_section(
            profile_doc,
            begin,
            end,
            render_profile_status_block(profile),
        )
    profile_path.write_text(profile_doc, encoding="utf-8")

    roadmap_path = root / ROADMAP_PATH
    roadmap = replace_generated_section(
        roadmap_path.read_text(encoding="utf-8"),
        PLANNED_TABLE_BEGIN,
        PLANNED_TABLE_END,
        render_planned_milestones(status),
    )
    roadmap_path.write_text(roadmap, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--write",
        action="store_true",
        help="refresh machine-derived status and generated Markdown sections",
    )
    args = parser.parse_args()
    if not args.write:
        parser.error("--write is required")
    write_generated_truth()
    print("Updated repository-truth status and generated documentation sections.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
