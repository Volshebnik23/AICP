from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
VALIDATOR_PATH = ROOT / "scripts/validate_planning_docs.py"
SPEC = importlib.util.spec_from_file_location("validate_planning_docs", VALIDATOR_PATH)
assert SPEC is not None and SPEC.loader is not None
VALIDATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(VALIDATOR)


def _status() -> dict:
    return json.loads((ROOT / VALIDATOR.STATUS).read_text(encoding="utf-8"))


def _roadmap() -> str:
    return (ROOT / VALIDATOR.ROADMAP).read_text(encoding="utf-8")


def _backlog() -> str:
    return (ROOT / VALIDATOR.BACKLOG).read_text(encoding="utf-8")


def test_current_planning_and_repo_truth_status_pass() -> None:
    assert VALIDATOR.validate(ROOT) == []


def test_duplicate_milestone_status_is_rejected() -> None:
    status = _status()
    duplicate = copy.deepcopy(status["milestones"][1])
    duplicate["status"] = "shipped"
    duplicate["document"] = VALIDATOR.ROADMAP
    status["milestones"].append(duplicate)

    errors = VALIDATOR._milestone_errors(ROOT, status, _roadmap(), _backlog())

    assert any("unique ID" in error for error in errors)


def test_no_work_remains_claim_is_rejected_when_planned_work_exists() -> None:
    errors = VALIDATOR._milestone_errors(
        ROOT,
        _status(),
        _roadmap(),
        _backlog() + "\nAICP currently has no remaining in-repo protocol backlog milestones.\n",
    )

    assert any("no work remains" in error for error in errors)


def test_version_drift_is_rejected() -> None:
    status = _status()
    status["current_version"] = "9.9.9"

    errors = VALIDATOR._version_errors(
        status,
        (ROOT / "VERSION").read_text(encoding="utf-8").strip(),
        (ROOT / VALIDATOR.BASELINE).read_text(encoding="utf-8"),
    )

    assert any("version mismatch" in error for error in errors)


def test_fail_closed_pairwise_and_external_claims_are_enforced() -> None:
    status = _status()
    status["interop_evidence"]["pairwise_publication_available"] = True
    status["interop_evidence"]["externally_demonstrated_profiles"] = ["AICP-BASE@0.1"]
    status["profiles"][0]["independent_external_evidence"] = True

    errors = VALIDATOR._evidence_claim_errors(ROOT, status)

    assert any("fails closed" in error for error in errors)
    assert any("real external submission" in error for error in errors)


def test_external_security_review_requires_real_artifact() -> None:
    status = _status()
    status["security_review"]["external_independent_review_completed"] = True
    status["security_review"]["external_review_artifacts"] = []

    errors = VALIDATOR._evidence_claim_errors(ROOT, status)

    assert any("actual review artifact" in error for error in errors)


def test_external_iut_profile_ids_must_resolve_to_registry() -> None:
    status = _status()
    status["profiles"][0]["id"] = "AICP-NOT-REGISTERED@0.1"

    errors = VALIDATOR._profile_errors(ROOT, status)

    assert any("exactly match" in error for error in errors)


def test_future_milestone_document_must_resolve() -> None:
    status = _status()
    status["milestones"][1]["document"] = "docs/process/DOES_NOT_EXIST.md"

    errors = VALIDATOR._milestone_errors(ROOT, status, _roadmap(), _backlog())

    assert any("does not resolve" in error for error in errors)


def test_registered_message_surface_matches_derived_coverage() -> None:
    assert _status()["message_surface"] == VALIDATOR._derive_message_surface(ROOT)
