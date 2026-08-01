from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
VALIDATOR_PATH = ROOT / "scripts/validate_planning_docs.py"
SPEC = importlib.util.spec_from_file_location(
    "validate_planning_docs", VALIDATOR_PATH
)
assert SPEC is not None and SPEC.loader is not None
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)

BASE_PROFILE = {
    "id": "AICP-BASE@0.1",
    "compatibility_mark": "AICP-Profile-BASE-0.1",
}
OTHER_PROFILE = {
    "id": "AICP-MEDIATED-BLOCKING@0.1",
    "compatibility_mark": "AICP-Profile-MEDIATED-BLOCKING-0.1",
}


def _status() -> dict:
    return json.loads((ROOT / VALIDATOR.STATUS).read_text(encoding="utf-8"))


def _roadmap() -> str:
    return (ROOT / VALIDATOR.ROADMAP).read_text(encoding="utf-8")


def _backlog() -> str:
    return (ROOT / VALIDATOR.BACKLOG).read_text(encoding="utf-8")


def _baseline() -> str:
    return (ROOT / VALIDATOR.BASELINE).read_text(encoding="utf-8")


def _profile_doc() -> str:
    return (ROOT / VALIDATOR.PROFILE_DOC).read_text(encoding="utf-8")


def _row(**overrides: object) -> dict:
    row = {
        "artifact_kind": "submission",
        "valid": True,
        "evidence_validation_status": "eligible",
        "claim_type": "implements_profile",
        "claim_scope": "external",
        "computed_marks": ["AICP-Profile-BASE-0.1"],
        "compatibility_marks": ["AICP-Profile-BASE-0.1"],
    }
    row.update(overrides)
    return row


def _matrix(*rows: dict) -> dict:
    return {
        "real_submissions": list(rows),
        "dry_run_artifacts": [],
        "instructional_artifacts": [],
    }


def _derive(*rows: dict, pairwise: bool = False) -> tuple[dict, dict]:
    return VALIDATOR.derive_interop_evidence(
        _matrix(*rows),
        [BASE_PROFILE, OTHER_PROFILE],
        pairwise_publication_available=pairwise,
    )


def _review_record(path: str) -> dict:
    return {
        "path": path,
        "review_type": "independent_external",
        "reviewer": "Example Independent Reviewer",
        "completion_date": "2026-07-01",
        "reviewed_scope": ["AICP Core v0.1"],
        "final_status": "completed",
        "findings_remediation_ref": None,
    }


def test_current_planning_and_repo_truth_status_pass() -> None:
    assert VALIDATOR.validate(ROOT) == []


def test_current_m62_profile_capability_and_milestone_truth() -> None:
    status = _status()
    assert status["profile_summary"] == {
        "registered": 16,
        "stable": 4,
        "experimental": 12,
        "external_iut_targets": 2,
        "ordinary_external_mark_reachable_targets": 2,
        "externally_demonstrated": 0,
    }
    assert status["capability_summary"] == {
        "external_capability_targets": 1,
        "reachable_external_capability_marks": 1,
        "externally_demonstrated_capabilities": 0,
    }
    projection_v1 = status["capability_evidence"][
        "aicp.session_state_projection.v1"
    ]
    assert projection_v1["external_evidence_target"] is True
    assert projection_v1["external_test_path"] == "full-capability"
    assert projection_v1["current_evidence_tck_release"] == (
        "AICP-EVIDENCE-TCK-1.1.0"
    )
    assert projection_v1["external_evidence_mark"] == (
        "AICP-Evidence-SESSION-STATE-PROJECTION-v1"
    )
    assert projection_v1["external_evidence_mark_reachable"] is True
    assert projection_v1["ordinary_compatibility_mark"] is False
    assert projection_v1["independent_external_evidence"] is False
    projection_v2 = status["capability_evidence"][
        "aicp.session_state_projection.v2"
    ]
    assert projection_v2["external_evidence_target"] is False
    assert projection_v2["independent_external_evidence"] is False
    milestones = {item["id"]: item for item in status["milestones"]}
    for number in range(58, 63):
        assert milestones[f"M{number}"]["status"] == "shipped"
        assert milestones[f"M{number}"]["document"] == "ROADMAP.md"
    assert all(
        milestones[f"M{number}"]["status"] == "planned"
        for number in range(63, 71)
    )


def test_repo_truth_discovers_base_v02_from_conformance_catalog() -> None:
    discovered = VALIDATOR.discover_profile_entries(ROOT, _status()["profiles"])
    base_v02 = next(item for item in discovered if item["id"] == "AICP-BASE@0.2")
    assert base_v02["profile_catalog"] == (
        "conformance/profiles/PF_AICP_BASE_0.2.json"
    )
    assert base_v02["internal_report_output"] == (
        "conformance/report_profile_base_v02.json"
    )
    assert base_v02["required_suites"] == [
        "conformance/core/CT_CORE_0.2.json"
    ]


def test_duplicate_milestone_status_is_rejected() -> None:
    status = _status()
    duplicate = copy.deepcopy(status["milestones"][1])
    duplicate["status"] = "shipped"
    duplicate["document"] = VALIDATOR.ROADMAP
    status["milestones"].append(duplicate)
    errors = VALIDATOR._milestone_errors(
        ROOT, status, _roadmap(), _backlog()
    )
    assert any("unique ID" in error for error in errors)


def test_no_work_remains_claim_is_rejected_when_planned_work_exists() -> None:
    errors = VALIDATOR._milestone_errors(
        ROOT,
        _status(),
        _roadmap(),
        _backlog()
        + "\nAICP currently has no remaining in-repo protocol backlog milestones.\n",
    )
    assert any("no work remains" in error for error in errors)


def test_version_drift_is_rejected() -> None:
    status = _status()
    status["current_version"] = "9.9.9"
    errors = VALIDATOR._version_errors(
        status,
        (ROOT / "VERSION").read_text(encoding="utf-8").strip(),
        _baseline(),
    )
    assert any("version mismatch" in error for error in errors)


def test_profile_status_table_rejects_experimental_to_stable_drift() -> None:
    original = (
        "| `AICP-AGENT-MEDIA@0.1` | Shipped | Experimental |"
    )
    changed = original.replace("Experimental", "Stable")
    profile_doc = _profile_doc().replace(original, changed, 1)
    errors = VALIDATOR._profile_document_errors(_status(), profile_doc)
    assert any("profile-status table is stale" in error for error in errors)


def test_profile_status_block_rejects_unqualified_available_now() -> None:
    profile_doc = _profile_doc() + "\n- **Status:** Available now.\n"
    errors = VALIDATOR._profile_document_errors(_status(), profile_doc)
    assert any("ambiguous Available now" in error for error in errors)


def test_authenticated_mark_reachability_requires_explicit_case_local_scope() -> None:
    catalog = json.loads((ROOT / VALIDATOR.IUT_CASES).read_text(encoding="utf-8"))
    auth = catalog["profiles"]["AICP-AUTHENTICATED-BASE@0.1"]
    assert VALIDATOR.derive_external_mark_status(auth) == (
        "reachable_for_eligible_external_implementation"
    )
    mutated = copy.deepcopy(auth)
    probe = next(
        item
        for item in mutated["full_profile"]["consumer_cases"]
        if item["case_id"] == "AUTH-CRYPTO-UNAVAILABLE"
    )
    probe["expected_execution_observation"]["scope"] = "run_level"
    assert VALIDATOR.derive_external_mark_status(mutated) == (
        "blocked_by_mandatory_degraded_probe"
    )


def test_invalid_real_submission_row_is_not_eligible() -> None:
    evidence, flags = _derive(_row(valid=False))
    assert evidence["real_submission_package_count"] == 1
    assert evidence["eligible_external_submission_count"] == 0
    assert evidence["rejected_real_submission_count"] == 1
    assert not any(flags.values())


def test_valid_but_ineligible_real_submission_is_not_evidence() -> None:
    evidence, flags = _derive(
        _row(evidence_validation_status="rejected")
    )
    assert evidence["eligible_external_submission_count"] == 0
    assert not any(flags.values())


def test_self_attested_rejected_submission_is_not_evidence() -> None:
    evidence, flags = _derive(
        _row(
            claim_scope="self_attested",
            evidence_validation_status="rejected",
        )
    )
    assert evidence["eligible_external_submission_count"] == 0
    assert flags["AICP-BASE@0.1"] is False


def test_eligible_base_submission_enables_only_base() -> None:
    evidence, flags = _derive(_row())
    assert evidence["eligible_external_submission_count"] == 1
    assert evidence["externally_demonstrated_profiles"] == [
        "AICP-BASE@0.1"
    ]
    assert flags == {
        "AICP-BASE@0.1": True,
        "AICP-MEDIATED-BLOCKING@0.1": False,
    }


def test_eligible_wrong_profile_submission_does_not_prove_base() -> None:
    evidence, flags = _derive(
        _row(
            computed_marks=[
                "AICP-Profile-MEDIATED-BLOCKING-0.1"
            ]
        )
    )
    assert evidence["externally_demonstrated_profiles"] == [
        "AICP-MEDIATED-BLOCKING@0.1"
    ]
    assert flags["AICP-BASE@0.1"] is False


def test_eligible_capability_submission_does_not_demonstrate_profile() -> None:
    evidence, flags = _derive(
        _row(
            claim_type="implements_capability",
            computed_marks=[],
            computed_profile_marks=[],
            computed_capability_marks=[
                "AICP-Evidence-SESSION-STATE-PROJECTION-v1"
            ],
            eligible_targets=[
                {
                    "kind": "capability",
                    "target_id": "aicp.session_state_projection",
                    "target_version": "v1",
                }
            ],
        )
    )
    assert evidence["externally_demonstrated_profiles"] == []
    assert evidence["externally_demonstrated_capabilities"] == [
        {
            "capability_id": "aicp.session_state_projection",
            "capability_version": "v1",
        }
    ]
    assert flags == {
        "AICP-BASE@0.1": False,
        "AICP-MEDIATED-BLOCKING@0.1": False,
    }


def test_forged_raw_marks_with_empty_computed_marks_are_ignored() -> None:
    evidence, flags = _derive(
        _row(
            compatibility_marks=["AICP-Profile-BASE-0.1"],
            computed_marks=[],
        )
    )
    assert evidence["eligible_external_submission_count"] == 0
    assert flags["AICP-BASE@0.1"] is False


def test_rejected_pairwise_row_cannot_enable_pairwise_status() -> None:
    evidence, _flags = _derive(
        _row(
            claim_type="pairwise_interop",
            claim_scope="pairwise",
            evidence_validation_status="rejected",
            joint_evidence_validation_status="rejected",
        ),
        pairwise=True,
    )
    assert evidence["pairwise_publication_available"] is True
    assert evidence["pairwise_demonstrated"] is False


def test_future_eligible_joint_pairwise_row_shape_is_supported() -> None:
    evidence, _flags = _derive(
        _row(
            claim_type="pairwise_interop",
            claim_scope="pairwise",
            joint_evidence_validation_status="eligible",
        ),
        pairwise=True,
    )
    assert evidence["pairwise_publication_available"] is True
    assert evidence["pairwise_demonstrated"] is True


def test_current_pairwise_fail_closed_status_is_enforced() -> None:
    status = _status()
    status["interop_evidence"]["pairwise_publication_available"] = True
    status["interop_evidence"]["pairwise_demonstrated"] = True
    errors = VALIDATOR._evidence_claim_errors(ROOT, status)
    assert any("must remain false" in error for error in errors)


def test_baseline_rejects_changed_profile_count() -> None:
    baseline = _baseline().replace(
        "16 (4 stable, 12 experimental)",
        "15 (4 stable, 11 experimental)",
        1,
    )
    assert VALIDATOR._baseline_generated_errors(_status(), baseline)


def test_baseline_rejects_changed_external_iut_count() -> None:
    baseline = _baseline().replace(
        "| External-IUT targets | 2:",
        "| External-IUT targets | 3:",
        1,
    )
    assert VALIDATOR._baseline_generated_errors(_status(), baseline)


def test_baseline_rejects_false_pairwise_demonstrated_row() -> None:
    baseline = _baseline().replace(
        "| Pairwise publication / demonstration | No / No |",
        "| Pairwise publication / demonstration | No / Yes |",
        1,
    )
    assert VALIDATOR._baseline_generated_errors(_status(), baseline)


def test_baseline_rejects_false_external_review_completion() -> None:
    baseline = _baseline().replace(
        "| Independent external security review | No |",
        "| Independent external security review | Yes |",
        1,
    )
    assert VALIDATOR._baseline_generated_errors(_status(), baseline)


def test_baseline_rejects_changed_milestone_status() -> None:
    baseline = _baseline().replace(
        "| M60 | shipped |", "| M60 | planned |", 1
    )
    assert VALIDATOR._baseline_generated_errors(_status(), baseline)


def test_baseline_rejects_stale_message_gap_count() -> None:
    baseline = _baseline().replace(
        "11 IDs use version-selected payload schemas; "
        "17 missing positive fixtures",
        "11 IDs use version-selected payload schemas; "
        "16 missing positive fixtures",
        1,
    )
    assert VALIDATOR._baseline_generated_errors(_status(), baseline)


def test_roadmap_planned_table_rejects_false_shipped_row() -> None:
    roadmap = _roadmap().replace(
        "| M63 | Planned |", "| M63 | Shipped |", 1
    )
    errors = VALIDATOR._milestone_errors(
        ROOT, _status(), roadmap, _backlog()
    )
    assert any("planned-milestone table is stale" in error for error in errors)


def test_backlog_visible_status_must_match_marker_and_json() -> None:
    backlog = _backlog().replace(
        "<!-- milestone-status: M63 planned -->\n- **Status:** Planned.",
        "<!-- milestone-status: M63 planned -->\n- **Status:** Shipped.",
        1,
    )
    errors = VALIDATOR._milestone_errors(
        ROOT, _status(), _roadmap(), backlog
    )
    assert any("M63: visible status" in error for error in errors)


def test_future_milestone_document_must_resolve() -> None:
    status = _status()
    next(
        milestone for milestone in status["milestones"]
        if milestone["id"] == "M63"
    )["document"] = "docs/process/DOES_NOT_EXIST.md"
    errors = VALIDATOR._milestone_errors(
        ROOT, status, _roadmap(), _backlog()
    )
    assert any("does not resolve" in error for error in errors)


def test_message_surface_has_all_132_entries() -> None:
    surface = _status()["message_surface"]
    assert len(surface["entries"]) == 132
    assert surface == VALIDATOR.derive_message_surface(ROOT)


def test_eleven_messages_expose_version_selected_payload_schemas() -> None:
    entries = _status()["message_surface"]["entries"]
    versioned = [
        entry for entry in entries if "payload_schema_variants" in entry
    ]
    core_ids = {
        "ATTEST_ACTION",
        "CONTEXT_AMEND",
        "CONTRACT_ACCEPT",
        "CONTRACT_PROPOSE",
        "ERROR",
        "RESOLVE_CONFLICT",
    }
    capneg_ids = {
        "CAPABILITIES_ACCEPT",
        "CAPABILITIES_DECLARE",
        "CAPABILITIES_PROPOSE",
        "CAPABILITIES_REJECT",
    }
    assert {entry["id"] for entry in versioned} == (
        core_ids | capneg_ids | {"STATE_SYNC_RESPONSE"}
    )
    for entry in versioned:
        if entry["id"] not in core_ids:
            continue
        assert entry["owner"] == "Core"
        assert entry["payload_schema"]["aicp_version"] == "0.1"
        assert [
            variant["aicp_version"]
            for variant in entry["payload_schema_variants"]
        ] == ["0.1", "0.2"]
        canonical = entry["payload_schema_variants"][0]
        assert entry["payload_schema"]["file"] == canonical["file"]
        assert entry["payload_schema"]["pointer"] == canonical["pointer"]
    for entry in versioned:
        if entry["id"] not in capneg_ids:
            continue
        assert entry["owner"] == "EXT-CAPNEG"
        assert entry["payload_schema"]["surface_selector"] == {
            "surface_kind": "extension",
            "surface_id": "EXT-CAPNEG",
            "surface_version": "0.1",
        }
        assert [
            variant["surface_selector"]["surface_version"]
            for variant in entry["payload_schema_variants"]
        ] == ["0.1", "0.2"]
    projection = next(
        entry for entry in versioned if entry["id"] == "STATE_SYNC_RESPONSE"
    )
    assert projection["payload_schema"]["surface_selector"] == {
        "surface_kind": "capability",
        "surface_id": "aicp.session_state_projection",
        "surface_version": "v1",
    }
    assert [
        variant["surface_selector"]["surface_version"]
        for variant in projection["payload_schema_variants"]
    ] == ["v1", "v2"]
    assert all(
        "payload_schema_variants" not in entry
        for entry in entries
        if entry["id"] not in core_ids | capneg_ids | {"STATE_SYNC_RESPONSE"}
    )


def _versioned_core_entry(surface: dict) -> dict:
    return next(
        entry
        for entry in surface["entries"]
        if entry["id"] == "CONTRACT_ACCEPT"
    )


def _versioned_capneg_entry(surface: dict) -> dict:
    return next(
        entry
        for entry in surface["entries"]
        if entry["id"] == "CAPABILITIES_PROPOSE"
    )


def test_message_surface_rejects_missing_schema_variant() -> None:
    surface = copy.deepcopy(_status()["message_surface"])
    _versioned_core_entry(surface)["payload_schema_variants"].pop()
    errors = VALIDATOR._message_surface_errors(ROOT, surface)
    assert any("variants are missing" in error for error in errors)


def test_message_surface_rejects_duplicate_schema_variant() -> None:
    surface = copy.deepcopy(_status()["message_surface"])
    entry = _versioned_core_entry(surface)
    entry["payload_schema_variants"].append(
        copy.deepcopy(entry["payload_schema_variants"][0])
    )
    errors = VALIDATOR._message_surface_errors(ROOT, surface)
    assert any("duplicate payload schema variant" in error for error in errors)


def test_message_surface_rejects_unknown_schema_variant() -> None:
    surface = copy.deepcopy(_status()["message_surface"])
    entry = _versioned_core_entry(surface)
    unknown = copy.deepcopy(entry["payload_schema_variants"][0])
    unknown["aicp_version"] = "9.9"
    entry["payload_schema_variants"].append(unknown)
    errors = VALIDATOR._message_surface_errors(ROOT, surface)
    assert any("unknown payload schema variant" in error for error in errors)


def test_message_surface_rejects_conflicting_canonical_variant() -> None:
    surface = copy.deepcopy(_status()["message_surface"])
    entry = _versioned_core_entry(surface)
    entry["payload_schema_variants"][0]["pointer"] = (
        "#/$defs/CONTRACT_PROPOSE"
    )
    errors = VALIDATOR._message_surface_errors(ROOT, surface)
    assert any("canonical schema conflicts" in error for error in errors)


def test_message_surface_rejects_unresolved_variant_pointer_and_suite() -> None:
    surface = copy.deepcopy(_status()["message_surface"])
    variant = _versioned_core_entry(surface)["payload_schema_variants"][1]
    variant["pointer"] = "#/$defs/DOES_NOT_EXIST"
    variant["suite"] = "conformance/DOES_NOT_EXIST.json"
    errors = VALIDATOR._message_surface_errors(ROOT, surface)
    assert any("variant schema file/pointer does not resolve" in error for error in errors)
    assert any("variant suite does not resolve" in error for error in errors)


def test_message_surface_rejects_missing_noncore_selector() -> None:
    surface = copy.deepcopy(_status()["message_surface"])
    variant = _versioned_capneg_entry(surface)["payload_schema_variants"][1]
    variant.pop("surface_selector")
    errors = VALIDATOR._message_surface_errors(ROOT, surface)
    assert any("must have one exact selector" in error for error in errors)


def test_message_surface_rejects_duplicate_noncore_selector() -> None:
    surface = copy.deepcopy(_status()["message_surface"])
    entry = _versioned_capneg_entry(surface)
    entry["payload_schema_variants"].append(
        copy.deepcopy(entry["payload_schema_variants"][1])
    )
    errors = VALIDATOR._message_surface_errors(ROOT, surface)
    assert any("duplicate payload schema variant" in error for error in errors)


def test_message_surface_rejects_conflicting_noncore_selector() -> None:
    surface = copy.deepcopy(_status()["message_surface"])
    variant = _versioned_capneg_entry(surface)["payload_schema_variants"][1]
    variant["surface_selector"]["surface_id"] = "EXT-NOT-CAPNEG"
    errors = VALIDATOR._message_surface_errors(ROOT, surface)
    assert any("unknown payload schema variant" in error for error in errors)


def test_message_surface_rejects_missing_entry() -> None:
    surface = copy.deepcopy(_status()["message_surface"])
    surface["entries"].pop()
    errors = VALIDATOR._message_surface_errors(ROOT, surface)
    assert any("exactly match all registered" in error for error in errors)


def test_message_surface_rejects_wrong_owner() -> None:
    surface = copy.deepcopy(_status()["message_surface"])
    surface["entries"][0]["owner"] = "Core"
    errors = VALIDATOR._message_surface_errors(ROOT, surface)
    assert any("owner is incorrect" in error for error in errors)


def test_message_surface_rejects_nonexistent_schema_pointer() -> None:
    surface = copy.deepcopy(_status()["message_surface"])
    surface["entries"][0]["payload_schema"]["pointer"] = (
        "#/$defs/DOES_NOT_EXIST"
    )
    errors = VALIDATOR._message_surface_errors(ROOT, surface)
    assert any("schema file/pointer does not resolve" in error for error in errors)


def test_message_surface_rejects_nonexistent_suite() -> None:
    surface = copy.deepcopy(_status()["message_surface"])
    surface["entries"][0]["suites"] = [
        "conformance/DOES_NOT_EXIST.json"
    ]
    errors = VALIDATOR._message_surface_errors(ROOT, surface)
    assert any("suite reference does not resolve" in error for error in errors)


def test_message_surface_rejects_nonexistent_fixture() -> None:
    surface = copy.deepcopy(_status()["message_surface"])
    complete = next(
        entry for entry in surface["entries"] if entry["positive_fixtures"]
    )
    complete["positive_fixtures"] = [
        "fixtures/DOES_NOT_EXIST.jsonl"
    ]
    errors = VALIDATOR._message_surface_errors(ROOT, surface)
    assert any("nonexistent fixture" in error for error in errors)


def test_message_surface_rejects_aggregate_mismatch() -> None:
    surface = copy.deepcopy(_status()["message_surface"])
    surface["summary"]["registered_count"] += 1
    errors = VALIDATOR._message_surface_errors(ROOT, surface)
    assert any("summary must be derived" in error for error in errors)


def test_message_surface_rejects_false_complete_gap_status() -> None:
    surface = copy.deepcopy(_status()["message_surface"])
    gap = next(
        entry
        for entry in surface["entries"]
        if entry["coverage_status"] == "missing_positive_fixture"
    )
    gap["coverage_status"] = "complete"
    gap["gap_milestone"] = None
    errors = VALIDATOR._message_surface_errors(ROOT, surface)
    assert any("coverage status is false" in error for error in errors)


def test_external_review_completion_requires_artifact_records() -> None:
    security = copy.deepcopy(_status()["security_review"])
    security["external_independent_review_completed"] = True
    security["external_review_artifacts"] = []
    errors = VALIDATOR._external_security_review_errors(ROOT, security)
    assert any("completion must exactly match" in error for error in errors)


def test_external_review_rejects_self_review() -> None:
    security = copy.deepcopy(_status()["security_review"])
    security["external_independent_review_completed"] = True
    security["external_review_artifacts"] = [
        _review_record("security_review/SELF_REVIEW.md")
    ]
    errors = VALIDATOR._external_security_review_errors(ROOT, security)
    assert any("SELF_REVIEW cannot count" in error for error in errors)


def test_external_review_rejects_random_unrelated_file() -> None:
    security = copy.deepcopy(_status()["security_review"])
    security["external_independent_review_completed"] = True
    security["external_review_artifacts"] = [_review_record("README.md")]
    errors = VALIDATOR._external_security_review_errors(ROOT, security)
    assert any("must be below" in error for error in errors)


def test_external_review_rejects_missing_contracted_artifact() -> None:
    security = copy.deepcopy(_status()["security_review"])
    security["external_independent_review_completed"] = True
    security["external_review_artifacts"] = [
        _review_record(
            "security_review/external_reviews/completed/missing.md"
        )
    ]
    errors = VALIDATOR._external_security_review_errors(ROOT, security)
    assert any("artifact does not resolve" in error for error in errors)


def test_external_review_rejects_missing_reviewer_scope_and_date() -> None:
    security = copy.deepcopy(_status()["security_review"])
    record = _review_record(
        "security_review/external_reviews/completed/missing.md"
    )
    record["reviewer"] = "TBD"
    record["completion_date"] = "not-a-date"
    record["reviewed_scope"] = []
    security["external_independent_review_completed"] = True
    security["external_review_artifacts"] = [record]
    errors = VALIDATOR._external_security_review_errors(ROOT, security)
    assert any("real reviewer" in error for error in errors)
    assert any("completion_date" in error for error in errors)
    assert any("reviewed_scope" in error for error in errors)


def test_external_review_rejects_incomplete_status() -> None:
    security = copy.deepcopy(_status()["security_review"])
    record = _review_record(
        "security_review/external_reviews/completed/missing.md"
    )
    record["final_status"] = "in_progress"
    security["external_independent_review_completed"] = True
    security["external_review_artifacts"] = [record]
    errors = VALIDATOR._external_security_review_errors(ROOT, security)
    assert any("completed review" in error for error in errors)


def test_external_review_findings_require_remediation_reference() -> None:
    security = copy.deepcopy(_status()["security_review"])
    record = _review_record(
        "security_review/external_reviews/completed/missing.md"
    )
    record["final_status"] = "completed_with_findings"
    record["findings_remediation_ref"] = None
    security["external_independent_review_completed"] = True
    security["external_review_artifacts"] = [record]
    errors = VALIDATOR._external_security_review_errors(ROOT, security)
    assert any("requires findings/remediation" in error for error in errors)
