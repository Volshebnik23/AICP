from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = ROOT / "conformance" / "evidence"
REF_PY = ROOT / "reference" / "python"
for path in (EVIDENCE_DIR, REF_PY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from aicp_external_evidence_runner import run_evidence  # noqa: E402
from aicp_ref.hashing import message_hash_from_body, object_hash  # noqa: E402
import aicp_external_evidence_runner as evidence_runner  # noqa: E402
import producer_suite_semantics  # noqa: E402
import target_catalog as target_catalog_module  # noqa: E402
from product_profile_fake_adapters import __file__ as ADAPTER_PATH  # noqa: E402
from profile_scenario_builder import generated_transcript_result  # noqa: E402
from profile_transcript_evaluator import evaluate_profile_transcript  # noqa: E402
from report_evaluator import evaluate_report  # noqa: E402
from producer_suite_semantics import (  # noqa: E402
    producer_check_inventory,
    suite_coverage_errors,
)
from target_catalog import (  # noqa: E402
    CURRENT_TCK_RELEASE_ID,
    canonical_digest,
    expected_input_artifacts,
    expected_suite_records,
    load_json,
    release_record,
    release_snapshot_digest,
    release_target_entry,
    resolve_target_record,
    runtime_import_closure,
    bundle_digest,
    target_catalog,
    validate_target_catalog,
)
from target_handlers import resolve_handler  # noqa: E402


HISTORICAL_REPORT = (
    ROOT
    / "interop/submissions/examples/capability_claim/reports/"
    "report_capability_projection_v1.json"
)
FROZEN_TCK_1_2_RECORD_DIGEST = (
    "sha256:71e231798a6e6c9a12e890f64ce0a1d4af26045d426057d5765700af5bb68913"
)


def _external_report(target_key: str) -> dict:
    return run_evidence(
        [
            sys.executable,
            str(ADAPTER_PATH),
            "--mode",
            "external_good",
        ],
        target=target_key,
        mode="full-profile",
        timestamp="2026-08-09T00:00:00Z",
    )


def _scenario(catalog_name: str, flow_id: str) -> dict:
    catalog = json.loads(
        (EVIDENCE_DIR / catalog_name).read_text(encoding="utf-8")
    )
    return next(item for item in catalog["scenarios"] if item["flow_id"] == flow_id)


def _rehash(messages: list[dict]) -> None:
    previous = None
    for message in messages:
        if previous is None:
            message.pop("prev_msg_hash", None)
        else:
            message["prev_msg_hash"] = previous
        body = dict(message)
        body.pop("message_hash", None)
        body.pop("signatures", None)
        message["message_hash"] = message_hash_from_body(body)
        previous = message["message_hash"]


def _message(messages: list[dict], message_type: str) -> dict:
    return next(item for item in messages if item["message_type"] == message_type)


def _report_artifact(report: dict, scenario_id: str) -> dict:
    return next(
        item
        for item in report["generated_artifacts"]
        if item["content"]["scenario_id"] == scenario_id
    )


def _refresh_artifact(artifact: dict) -> None:
    _rehash(artifact["content"]["messages"])
    artifact["content_digest"] = canonical_digest(artifact["content"])
    artifact["repeat_content_digest"] = artifact["content_digest"]


def _refresh_capneg_binding(messages: list[dict]) -> None:
    proposal = _message(messages, "CAPABILITIES_PROPOSE")["payload"][
        "negotiation_result"
    ]
    digest = object_hash("capneg.negotiation_result", proposal)
    acceptance = _message(messages, "CAPABILITIES_ACCEPT")["payload"]
    acceptance["negotiation_result_hash"] = digest
    capneg = _message(messages, "CONTRACT_PROPOSE")["payload"]["contract"][
        "ext"
    ]["capneg"]
    capneg["negotiation_result_hash"] = digest
    capneg["selected"] = copy.deepcopy(proposal["selected"])


def _mutate_artifact(
    report: dict,
    scenario_id: str,
    mutate,
    *,
    refresh_capneg: bool = False,
) -> None:
    artifact = _report_artifact(report, scenario_id)
    messages = artifact["content"]["messages"]
    mutate(messages)
    if refresh_capneg:
        _refresh_capneg_binding(messages)
    _refresh_artifact(artifact)


def test_exact_pre_m63_projection_report_remains_strongly_eligible() -> None:
    report = json.loads(HISTORICAL_REPORT.read_text(encoding="utf-8"))
    assert report["tck_release"]["registry_digest"] == (
        "sha256:b480aceb911e7f284352f157f3e04914788bdbdaa95d4c1857ea3ab8ac810426"
    )
    verdict = evaluate_report(
        report,
        expected_implementation_id="example-projection-v1-implementation",
        expected_implementation_version="1.0.0-example",
    )
    assert verdict["status"] == "eligible"
    assert verdict["eligible_marks"] == [
        "AICP-Evidence-SESSION-STATE-PROJECTION-v1"
    ]


def test_tck_1_2_release_record_is_frozen_before_correction() -> None:
    assert canonical_digest(release_record("AICP-EVIDENCE-TCK-1.2.0")) == (
        FROZEN_TCK_1_2_RECORD_DIGEST
    )


@pytest.mark.parametrize("different_content", [False, True])
def test_duplicate_generated_artifact_id_is_rejected(
    different_content: bool,
) -> None:
    report = _external_report("AICP-MEDIATED-BLOCKING@0.1")
    duplicate = copy.deepcopy(report["generated_artifacts"][0])
    if different_content:
        duplicate["content"]["scenario_id"] = "MB-FORGED-DUPLICATE"
        duplicate["content_digest"] = canonical_digest(duplicate["content"])
        duplicate["repeat_content_digest"] = duplicate["content_digest"]
    report["generated_artifacts"].append(duplicate)
    verdict = evaluate_report(
        report,
        expected_implementation_id="test-only-product-profile-external",
        expected_implementation_version="1.0.0",
    )
    assert verdict["status"] == "rejected"
    assert any(
        "EVIDENCE_PRODUCER_ARTIFACT_COVERAGE_MISMATCH" in error
        for error in verdict["errors"]
    )


SEMANTIC_MUTATIONS = (
    (
        "mediated_blocking_producer_scenarios.json",
        "core_contract_action",
        "CT-CONTRACT-SCHEMA-01",
        lambda messages: _message(messages, "CONTRACT_PROPOSE")["payload"]
        ["contract"].pop("goal"),
    ),
    (
        "mediated_blocking_producer_scenarios.json",
        "core_contract_action",
        "CT-POLICY-CATEGORIES-01",
        lambda messages: _message(messages, "CONTRACT_PROPOSE")["payload"]
        ["contract"].update(
            {"policies": [{"policy_id": "policy-1", "category": "NOT_REGISTERED"}]}
        ),
    ),
    (
        "mediated_blocking_producer_scenarios.json",
        "profile_reject",
        "CN-REASON-CODES-01",
        lambda messages: _message(messages, "CAPABILITIES_REJECT")["payload"].update(
            {"reason_code": "NOT_REGISTERED"}
        ),
    ),
    (
        "mediated_blocking_producer_scenarios.json",
        "profile_accept_contract",
        "CN-PRIVACY-MODES-01",
        lambda messages: _message(messages, "CAPABILITIES_PROPOSE")["payload"]
        ["negotiation_result"]["selected"].update({"privacy_mode": "not-registered"}),
    ),
    (
        "mediated_blocking_producer_scenarios.json",
        "profile_accept_contract",
        "CN-BINDINGS-01",
        lambda messages: _message(messages, "CAPABILITIES_PROPOSE")["payload"]
        ["negotiation_result"]["selected"].update({"binding": "NOT-REGISTERED"}),
    ),
    (
        "mediated_blocking_producer_scenarios.json",
        "profile_accept_contract",
        "CN-CHANNEL-PROPERTIES-01",
        lambda messages: _message(messages, "CAPABILITIES_PROPOSE")["payload"]
        ["negotiation_result"]["selected"].update(
            {"channel_properties": {"CP-ORDERING-0.1": "not-supported"}}
        ),
    ),
    (
        "mediated_blocking_producer_scenarios.json",
        "policy_deny_block",
        "ENF-SANCTION-CODES-01",
        lambda messages: _message(messages, "ENFORCEMENT_VERDICT")["payload"]
        ["sanctions"][0].update({"code": "NOT-REGISTERED"}),
    ),
    (
        "resumable_sessions_producer_scenarios.json",
        "resume_in_sync",
        "RS-ACTIONS-01",
        lambda messages: _message(messages, "RESUME_RESPONSE")["payload"].update(
            {"recommended_actions": ["NOT-REGISTERED"]}
        ),
    ),
)


@pytest.mark.parametrize(
    ("catalog_name", "flow_id", "expected_code", "mutate"),
    SEMANTIC_MUTATIONS,
)
def test_required_suite_semantic_mutation_is_rejected(
    catalog_name: str,
    flow_id: str,
    expected_code: str,
    mutate,
) -> None:
    scenario = _scenario(catalog_name, flow_id)
    result = generated_transcript_result(scenario)
    mutate(result["messages"])
    _rehash(result["messages"])
    evaluation = evaluate_profile_transcript(
        result["messages"],
        scenario["required_suites"],
    )
    assert evaluation.accepted is False
    assert expected_code in {item["code"] for item in evaluation.errors}


def test_current_release_uses_actual_runner_bundle_and_handler_artifact_kinds(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    projection = run_evidence(
        [
            sys.executable,
            str(EVIDENCE_DIR / "fake_adapters.py"),
            "--mode",
            "external_good",
        ],
        target="aicp.session_state_projection@v1",
        mode="full-capability",
        timestamp="2026-08-09T00:00:00Z",
    )
    release = release_record(CURRENT_TCK_RELEASE_ID)
    actual = bundle_digest(runtime_import_closure())
    assert projection["report_format_version"] == "2.2"
    assert projection["tck_release"]["release_id"] == CURRENT_TCK_RELEASE_ID
    assert projection["tck_release"]["registry_digest"] == release_snapshot_digest(
        CURRENT_TCK_RELEASE_ID
    )
    assert projection["runner"]["source_revision"] == actual
    assert release["runner_bundle"]["digest"] == actual
    assert projection["generated_artifacts"][0]["artifact_kind"] == "projection"
    assert projection["compatibility_marks"] == [
        "AICP-Evidence-SESSION-STATE-PROJECTION-v1"
    ]

    profile = _external_report("AICP-MEDIATED-BLOCKING@0.1")
    assert all(
        item["artifact_kind"] == "transcript"
        for item in profile["generated_artifacts"]
    )

    monkeypatch.setattr(
        evidence_runner,
        "bundle_digest",
        lambda _paths: "sha256:" + "0" * 64,
    )
    mismatch = evidence_runner.run_evidence(
        [
            sys.executable,
            str(EVIDENCE_DIR / "fake_adapters.py"),
            "--mode",
            "external_good",
        ],
        target="aicp.session_state_projection@v1",
        mode="full-capability",
        timestamp="2026-08-09T00:00:00Z",
    )
    assert mismatch["passed"] is False
    assert mismatch["compatibility_marks"] == []
    assert mismatch["runner"]["source_revision"] == "sha256:" + "0" * 64
    assert any(
        "EVIDENCE_RUNNER_WORKTREE_MISMATCH" in item["message"]
        for item in mismatch["failures"]
    )


def test_every_required_producer_suite_check_is_machine_accounted() -> None:
    scenarios: list[dict] = []
    for name in (
        "mediated_blocking_producer_scenarios.json",
        "resumable_sessions_producer_scenarios.json",
        "delegated_identity_producer_scenarios.json",
    ):
        scenarios.extend(load_json(EVIDENCE_DIR / name)["scenarios"])
    inventory = producer_check_inventory(scenarios)
    assert suite_coverage_errors(scenarios) == []
    assert all(
        item["execution_kind"]
        in {
            "executed_common_check",
            "executed_suite_semantic_check",
            "executed_scenario_sequence_check",
        }
        and item["implementation"] != "unimplemented"
        and item["producer_scenarios"]
        for item in inventory
    )
    assert {(item["suite"], item["check_id"]) for item in inventory} == {
        (suite_id, check["test_id"])
        for path in {
            suite_path
            for scenario in scenarios
            for suite_path in scenario["required_suites"]
        }
        for suite in [load_json(ROOT / path)]
        for suite_id in [suite["suite_id"]]
        for check in suite["checks"]
    }


def test_unknown_mandatory_suite_check_fails_catalog_producer_and_mark(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report = _external_report("AICP-MEDIATED-BLOCKING@0.1")
    monkeypatch.delitem(
        producer_suite_semantics.CHECK_IMPLEMENTATIONS,
        "CN-REASON-CODES-01",
    )
    record = resolve_target_record("AICP-MEDIATED-BLOCKING@0.1")
    catalog = target_catalog(record)
    catalog_errors = validate_target_catalog(
        catalog,
        record=record,
        handler=resolve_handler(record.handler_id),
    )
    assert any("CN-REASON-CODES-01" in error for error in catalog_errors)

    scenario = _scenario(
        "mediated_blocking_producer_scenarios.json", "profile_reject"
    )
    result = generated_transcript_result(scenario)
    transcript = evaluate_profile_transcript(
        result["messages"], scenario["required_suites"]
    )
    assert "EVIDENCE_PRODUCER_SUITE_CHECK_UNIMPLEMENTED" in {
        item["code"] for item in transcript.errors
    }
    verdict = evaluate_report(
        report,
        expected_implementation_id="test-only-product-profile-external",
        expected_implementation_version="1.0.0",
    )
    assert verdict["status"] == "rejected"
    assert verdict["eligible_marks"] == []


def _duplicate_policy(messages: list[dict]) -> None:
    _message(messages, "CONTRACT_PROPOSE")["payload"]["contract"]["policies"] = [
        {"policy_id": "policy-1", "category": "safety", "parameters": {}},
        {"policy_id": "policy-1", "category": "safety", "parameters": {}},
    ]


def _wrong_sequence(messages: list[dict]) -> None:
    messages[1], messages[2] = messages[2], messages[1]


def _invalid_capneg_selected(messages: list[dict], field: str, value: object) -> None:
    _message(messages, "CAPABILITIES_PROPOSE")["payload"]["negotiation_result"][
        "selected"
    ][field] = value


REPORT_MUTATIONS = (
    (
        "CT-CONTRACT-SCHEMA-01",
        "AICP-MEDIATED-BLOCKING@0.1",
        "MB-CAPNEG-ACCEPT-CONTRACT",
        lambda messages: _message(messages, "CONTRACT_PROPOSE")["payload"]
        ["contract"].pop("goal"),
        False,
    ),
    (
        "CT-POLICY-CATEGORIES-01",
        "AICP-MEDIATED-BLOCKING@0.1",
        "MB-CAPNEG-ACCEPT-CONTRACT",
        lambda messages: _message(messages, "CONTRACT_PROPOSE")["payload"]
        ["contract"].update(
            {
                "policies": [
                    {
                        "policy_id": "policy-1",
                        "category": "NOT_REGISTERED",
                        "parameters": {},
                    }
                ]
            }
        ),
        False,
    ),
    (
        "CT-POLICY-CATEGORIES-01",
        "AICP-MEDIATED-BLOCKING@0.1",
        "MB-CAPNEG-ACCEPT-CONTRACT",
        _duplicate_policy,
        False,
    ),
    (
        "CT-SEQUENCE-01",
        "AICP-MEDIATED-BLOCKING@0.1",
        "MB-CAPNEG-ACCEPT-CONTRACT",
        _wrong_sequence,
        False,
    ),
    (
        "CN-REASON-CODES-01",
        "AICP-MEDIATED-BLOCKING@0.1",
        "MB-CAPNEG-REJECT",
        lambda messages: _message(messages, "CAPABILITIES_REJECT")["payload"].update(
            {"reason_code": "NOT_REGISTERED"}
        ),
        False,
    ),
    (
        "CN-PRIVACY-MODES-01",
        "AICP-MEDIATED-BLOCKING@0.1",
        "MB-CAPNEG-ACCEPT-CONTRACT",
        lambda messages: _invalid_capneg_selected(
            messages, "privacy_mode", "not-registered"
        ),
        True,
    ),
    (
        "CN-BINDINGS-01",
        "AICP-MEDIATED-BLOCKING@0.1",
        "MB-CAPNEG-ACCEPT-CONTRACT",
        lambda messages: _invalid_capneg_selected(
            messages, "binding", "BIND-HTTP-0.1"
        ),
        True,
    ),
    (
        "CN-CHANNEL-PROPERTIES-01",
        "AICP-MEDIATED-BLOCKING@0.1",
        "MB-CAPNEG-ACCEPT-CONTRACT",
        lambda messages: _invalid_capneg_selected(
            messages,
            "channel_properties",
            {"CP-ORDERING-0.1": "ordered"},
        ),
        True,
    ),
    (
        "ENF-SANCTION-CODES-01",
        "AICP-MEDIATED-BLOCKING@0.1",
        "MB-POLICY-DENY-BLOCK",
        lambda messages: _message(messages, "ENFORCEMENT_VERDICT")["payload"]
        ["sanctions"][0].update({"code": "NOT-REGISTERED"}),
        False,
    ),
    (
        "RS-ACTIONS-01",
        "AICP-RESUMABLE-SESSIONS@0.1",
        "RS-RESUME-IN-SYNC",
        lambda messages: _message(messages, "RESUME_RESPONSE")["payload"].update(
            {"recommended_actions": ["NOT-REGISTERED"]}
        ),
        False,
    ),
)


@pytest.mark.parametrize(
    ("check_id", "target_key", "scenario_id", "mutate", "refresh_capneg"),
    REPORT_MUTATIONS,
)
def test_independent_evaluator_semantic_checks_are_load_bearing(
    check_id: str,
    target_key: str,
    scenario_id: str,
    mutate,
    refresh_capneg: bool,
) -> None:
    report = _external_report(target_key)
    _mutate_artifact(
        report,
        scenario_id,
        mutate,
        refresh_capneg=refresh_capneg,
    )
    kwargs = {
        "expected_implementation_id": "test-only-product-profile-external",
        "expected_implementation_version": "1.0.0",
    }
    rejected = evaluate_report(report, **kwargs)
    assert rejected["status"] == "rejected"
    assert rejected["eligible_marks"] == []
    control = evaluate_report(
        report,
        disabled_checks=frozenset({check_id}),
        **kwargs,
    )
    assert control["status"] == "eligible", control["errors"]
    assert control["eligible_marks"]


def test_independent_evaluator_artifact_multiplicity_is_load_bearing() -> None:
    report = _external_report("AICP-MEDIATED-BLOCKING@0.1")
    report["generated_artifacts"].append(
        copy.deepcopy(report["generated_artifacts"][0])
    )
    kwargs = {
        "expected_implementation_id": "test-only-product-profile-external",
        "expected_implementation_version": "1.0.0",
    }
    rejected = evaluate_report(report, **kwargs)
    assert rejected["status"] == "rejected"
    assert any(
        "EVIDENCE_PRODUCER_ARTIFACT_COVERAGE_MISMATCH" in error
        for error in rejected["errors"]
    )
    control = evaluate_report(
        report,
        disabled_checks=frozenset({"artifact_multiplicity"}),
        **kwargs,
    )
    assert control["status"] == "eligible"


@pytest.mark.parametrize(
    "release_id",
    ["AICP-EVIDENCE-TCK-1.2.0", "AICP-EVIDENCE-TCK-1.3.0"],
)
def test_superseded_tck_is_ineligible_by_explicit_policy(
    release_id: str,
) -> None:
    report = _external_report("AICP-MEDIATED-BLOCKING@0.1")
    release = release_record(release_id)
    target = release_target_entry(release, "AICP-MEDIATED-BLOCKING@0.1")
    report["tck_release"] = {
        "release_id": release["release_id"],
        "registry_digest": release_snapshot_digest(release["release_id"]),
        "target_registry_digest": release["target_registry"]["content_digest"],
        "target_registry_schema_digest": release["target_registry"]["schema_digest"],
        "target_catalog_digest": target["target_catalog"]["content_digest"],
        "report_schema_digest": release["report_schema"]["content_digest"],
        "runner_bundle_digest": release["runner_bundle"]["digest"],
    }
    report["runner"]["source_revision"] = release["runner_bundle"]["digest"]
    historical_schema = load_json(ROOT / release["report_schema"]["path"])
    historical_format = historical_schema["properties"]["report_format_version"][
        "const"
    ]
    report["report_format_version"] = historical_format
    report["runner"]["version"] = historical_format
    report["target"]["target_catalog_digest"] = target["target_catalog"][
        "content_digest"
    ]
    report["required_suites"] = expected_suite_records(
        release, "AICP-MEDIATED-BLOCKING@0.1"
    )
    report["input_artifacts"] = expected_input_artifacts(
        release, "AICP-MEDIATED-BLOCKING@0.1"
    )
    historical_case_ids = set(target["mandatory_case_ids"])
    report["case_results"] = [
        item
        for item in report["case_results"]
        if item["case_id"] in historical_case_ids
    ]
    report["compatibility_marks"] = []
    verdict = evaluate_report(
        report,
        expected_implementation_id="test-only-product-profile-external",
        expected_implementation_version="1.0.0",
    )
    assert verdict == {
        "status": "ineligible",
        "errors": [],
        "eligible_marks": [],
        "eligible_targets": [],
    }


@pytest.mark.parametrize("mutation", ["missing", "unknown", "hidden_invalid"])
def test_exact_artifact_counter_rejects_every_cardinality_forgery(
    mutation: str,
) -> None:
    report = _external_report("AICP-MEDIATED-BLOCKING@0.1")
    if mutation == "missing":
        report["generated_artifacts"].pop()
    elif mutation == "unknown":
        unknown = copy.deepcopy(report["generated_artifacts"][0])
        unknown["artifact_id"] = "EVIDENCE-PRODUCER-UNKNOWN"
        report["generated_artifacts"].append(unknown)
    else:
        valid = copy.deepcopy(report["generated_artifacts"][0])
        report["generated_artifacts"][0]["content"]["scenario_id"] = "INVALID-EARLIER"
        report["generated_artifacts"][0]["content_digest"] = canonical_digest(
            report["generated_artifacts"][0]["content"]
        )
        report["generated_artifacts"][0]["repeat_content_digest"] = report[
            "generated_artifacts"
        ][0]["content_digest"]
        report["generated_artifacts"].append(valid)
    verdict = evaluate_report(
        report,
        expected_implementation_id="test-only-product-profile-external",
        expected_implementation_version="1.0.0",
    )
    assert verdict["status"] == "rejected"
    assert any(
        "EVIDENCE_PRODUCER_ARTIFACT_COVERAGE_MISMATCH" in error
        for error in verdict["errors"]
    )


def test_future_mutable_registry_addition_does_not_invalidate_frozen_reports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    historical = json.loads(HISTORICAL_REPORT.read_text(encoding="utf-8"))
    current = _external_report("AICP-MEDIATED-BLOCKING@0.1")
    registry = load_json(EVIDENCE_DIR / "evidence_tck_releases.json")
    hypothetical = copy.deepcopy(release_record(CURRENT_TCK_RELEASE_ID, registry))
    hypothetical["release_id"] = "AICP-EVIDENCE-TCK-1.7.0"
    registry["releases"].append(hypothetical)
    future_path = tmp_path / "evidence_tck_releases.json"
    future_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
    monkeypatch.setattr(target_catalog_module, "TCK_RELEASES_PATH", future_path)

    historical_verdict = evaluate_report(
        historical,
        expected_implementation_id="example-projection-v1-implementation",
        expected_implementation_version="1.0.0-example",
    )
    current_verdict = evaluate_report(
        current,
        expected_implementation_id="test-only-product-profile-external",
        expected_implementation_version="1.0.0",
    )
    assert historical_verdict["status"] == "eligible"
    assert current_verdict["status"] == "eligible"


def test_no_checked_in_external_submission_depends_on_tck_1_2() -> None:
    references: list[str] = []
    for path in (ROOT / "interop/submissions").rglob("*.json"):
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if (
            isinstance(value, dict)
            and isinstance(value.get("tck_release"), dict)
            and value["tck_release"].get("release_id")
            == "AICP-EVIDENCE-TCK-1.2.0"
        ):
            references.append(path.relative_to(ROOT).as_posix())
    assert references == []
