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
        "15 (4 stable, 11 experimental)",
        "14 (4 stable, 10 experimental)",
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
        "| M60 | planned |", "| M60 | shipped |", 1
    )
    assert VALIDATOR._baseline_generated_errors(_status(), baseline)


def test_baseline_rejects_stale_message_gap_count() -> None:
    baseline = _baseline().replace(
        "132 entries; 17 missing positive fixtures",
        "132 entries; 16 missing positive fixtures",
        1,
    )
    assert VALIDATOR._baseline_generated_errors(_status(), baseline)


def test_roadmap_planned_table_rejects_false_shipped_row() -> None:
    roadmap = _roadmap().replace(
        "| M60 | Planned |", "| M60 | Shipped |", 1
    )
    errors = VALIDATOR._milestone_errors(
        ROOT, _status(), roadmap, _backlog()
    )
    assert any("planned-milestone table is stale" in error for error in errors)


def test_backlog_visible_status_must_match_marker_and_json() -> None:
    backlog = _backlog().replace(
        "<!-- milestone-status: M60 planned -->\n- **Status:** Planned.",
        "<!-- milestone-status: M60 planned -->\n- **Status:** Shipped.",
        1,
    )
    errors = VALIDATOR._milestone_errors(
        ROOT, _status(), _roadmap(), backlog
    )
    assert any("M60: visible status" in error for error in errors)


def test_future_milestone_document_must_resolve() -> None:
    status = _status()
    status["milestones"][1]["document"] = (
        "docs/process/DOES_NOT_EXIST.md"
    )
    errors = VALIDATOR._milestone_errors(
        ROOT, status, _roadmap(), _backlog()
    )
    assert any("does not resolve" in error for error in errors)


def test_message_surface_has_all_132_entries() -> None:
    surface = _status()["message_surface"]
    assert len(surface["entries"]) == 132
    assert surface == VALIDATOR.derive_message_surface(ROOT)


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
