from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = ROOT / "conformance" / "evidence"
RUNNER_DIR = ROOT / "conformance" / "runner"
REF_PY = ROOT / "reference" / "python"
for path in (EVIDENCE_DIR, RUNNER_DIR, REF_PY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from aicp_conformance_runner import (  # noqa: E402
    _is_namespaced_identifier,
    run_suite,
)
from aicp_external_evidence_runner import run_evidence  # noqa: E402
from aicp_ref.hashing import message_hash_from_body, object_hash  # noqa: E402
from evidence_identifier_rules import (  # noqa: E402
    is_broad_namespaced_identifier,
)
from producer_payload_schema_router import (  # noqa: E402
    derive_payload_routes,
    payload_route_errors,
    payload_route_inventory,
    tier1_payload_routes,
    tier1_scenarios,
)
from producer_suite_semantics import (  # noqa: E402
    PRIVATE_FLOW_SEQUENCES,
    producer_check_inventory,
    semantic_parity_inventory,
    suite_coverage_errors,
)
from product_profile_fake_adapters import __file__ as ADAPTER_PATH  # noqa: E402
from profile_scenario_builder import generated_transcript_result  # noqa: E402
from profile_transcript_evaluator import evaluate_profile_transcript  # noqa: E402
from report_evaluator import evaluate_report  # noqa: E402
from target_catalog import (  # noqa: E402
    CURRENT_TCK_RELEASE_ID,
    FROZEN_TCK_1_3_BUNDLE_MANIFEST_DIGEST,
    FROZEN_TCK_1_3_RECORD_DIGEST,
    FROZEN_TCK_1_3_REGISTRY_SNAPSHOT_DIGEST,
    PREVIOUS_TCK_RELEASE_ID,
    canonical_digest,
    file_digest,
    load_json,
    release_policy,
    release_record,
    release_snapshot_digest,
)


def _scenario(catalog_name: str, flow_id: str) -> dict:
    catalog = json.loads(
        (EVIDENCE_DIR / catalog_name).read_text(encoding="utf-8")
    )
    return next(item for item in catalog["scenarios"] if item["flow_id"] == flow_id)


def _messages(catalog_name: str, flow_id: str) -> tuple[dict, list[dict]]:
    scenario = _scenario(catalog_name, flow_id)
    result = generated_transcript_result(scenario)
    return scenario, copy.deepcopy(result["messages"])


def _message(messages: list[dict], message_type: str) -> dict:
    return next(item for item in messages if item["message_type"] == message_type)


def _rechain(messages: list[dict]) -> None:
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


def _external_report(target_key: str) -> dict:
    return run_evidence(
        [sys.executable, str(ADAPTER_PATH), "--mode", "external_good"],
        target=target_key,
        mode="full-profile",
        timestamp="2026-08-09T00:00:00Z",
    )


def _report_artifact(report: dict, scenario_id: str) -> dict:
    return next(
        item
        for item in report["generated_artifacts"]
        if item["content"]["scenario_id"] == scenario_id
    )


def _refresh_artifact(artifact: dict) -> None:
    _rechain(artifact["content"]["messages"])
    artifact["content_digest"] = canonical_digest(artifact["content"])
    artifact["repeat_content_digest"] = artifact["content_digest"]


def _evaluate_report(report: dict, disabled: frozenset[str] = frozenset()) -> dict:
    return evaluate_report(
        report,
        expected_implementation_id="test-only-product-profile-external",
        expected_implementation_version="1.0.0",
        disabled_checks=disabled,
    )


def _evaluate(scenario: dict, messages: list[dict]):
    _rechain(messages)
    return evaluate_profile_transcript(
        messages,
        scenario["required_suites"],
        enforce_core_contract_semantics=True,
    )


@pytest.mark.parametrize(
    ("catalog_name", "flow_id", "message_type"),
    [
        (
            "resumable_sessions_producer_scenarios.json",
            "resume_in_sync",
            "CONTRACT_ACCEPT",
        ),
        (
            "delegated_identity_producer_scenarios.json",
            "identity_announce_use",
            "ATTEST_ACTION",
        ),
    ],
)
def test_core_payload_schema_is_enforced_inside_extension_scenarios(
    catalog_name: str,
    flow_id: str,
    message_type: str,
) -> None:
    scenario, messages = _messages(catalog_name, flow_id)
    _message(messages, message_type)["payload"]["unexpected"] = True
    evaluation = _evaluate(scenario, messages)
    assert not evaluation.accepted
    assert any(
        item["code"] == "EVIDENCE-GENERATED-PAYLOAD-SCHEMA-01"
        for item in evaluation.errors
    )


def test_object_resync_payload_schema_is_enforced_inside_core_scenario() -> None:
    scenario, messages = _messages(
        "resumable_sessions_producer_scenarios.json",
        "core_resync",
    )
    _message(messages, "STATE_SYNC_RESPONSE")["payload"]["unexpected"] = True
    evaluation = _evaluate(scenario, messages)
    assert not evaluation.accepted
    assert any(
        item["code"] == "EVIDENCE-GENERATED-PAYLOAD-SCHEMA-01"
        for item in evaluation.errors
    )


@pytest.mark.parametrize(
    ("value", "ordinary_accepts"),
    [
        ("PII_BLOCKED", True),
        ("vendor:custom-reason", True),
        ("org:custom-reason", True),
        ("foo:custom-reason", False),
        ("x-custom-reason", False),
    ],
)
def test_policy_reason_namespace_matches_ordinary_conformance(
    value: str,
    ordinary_accepts: bool,
) -> None:
    registered = {
        item["id"] for item in load_json(ROOT / "registry/policy_reason_codes.json")
    }
    assert (
        value in registered or _is_namespaced_identifier(value)
    ) is ordinary_accepts
    scenario, messages = _messages(
        "mediated_blocking_producer_scenarios.json",
        "policy_allow_delivery",
    )
    decision = _message(messages, "POLICY_EVAL_RESULT")["payload"][
        "policy_decision"
    ]
    decision["reason_codes"] = [value]
    evaluation = _evaluate(scenario, messages)
    assert evaluation.accepted is ordinary_accepts
    assert any(
        item["code"] == "PE-REASON-CODES-01" for item in evaluation.errors
    ) is (not ordinary_accepts)


def _set_privacy_mode(messages: list[dict], value: str) -> None:
    for message in messages:
        payload = message["payload"]
        if message["message_type"] == "CAPABILITIES_DECLARE":
            payload["supported_privacy_modes"] = [value]
        elif message["message_type"] == "CAPABILITIES_PROPOSE":
            payload["negotiation_result"]["selected"]["privacy_mode"] = value
    proposal = _message(messages, "CAPABILITIES_PROPOSE")["payload"][
        "negotiation_result"
    ]
    proposal_hash = object_hash("capneg.negotiation_result", proposal)
    acceptance = _message(messages, "CAPABILITIES_ACCEPT")["payload"]
    acceptance["negotiation_result_hash"] = proposal_hash
    capneg = _message(messages, "CONTRACT_PROPOSE")["payload"]["contract"][
        "ext"
    ]["capneg"]
    capneg["negotiation_result_hash"] = proposal_hash
    capneg["selected"] = copy.deepcopy(proposal["selected"])


@pytest.mark.parametrize(
    ("value", "ordinary_accepts"),
    [
        ("standard", True),
        ("vendor:private", True),
        ("org:private", True),
        ("foo:private", False),
        ("x-private-mode", False),
    ],
)
def test_capneg_privacy_namespace_matches_ordinary_conformance(
    value: str,
    ordinary_accepts: bool,
) -> None:
    registered = {
        item["id"] for item in load_json(ROOT / "registry/privacy_modes.json")
    }
    assert (
        value in registered or _is_namespaced_identifier(value)
    ) is ordinary_accepts
    scenario, messages = _messages(
        "mediated_blocking_producer_scenarios.json",
        "profile_accept_contract",
    )
    _set_privacy_mode(messages, value)
    evaluation = _evaluate(scenario, messages)
    assert evaluation.accepted is ordinary_accepts
    assert any(
        item["code"] == "CN-PRIVACY-MODES-01" for item in evaluation.errors
    ) is (not ordinary_accepts)


EXPECTED_PAYLOAD_ROUTES = {
    **{
        message_type: (
            "schemas/core/aicp-core-payloads.schema.json",
            f"/$defs/{message_type}",
            "CT-CORE-0.1",
        )
        for message_type in (
            "CONTRACT_PROPOSE",
            "CONTRACT_ACCEPT",
            "CONTEXT_AMEND",
            "ATTEST_ACTION",
            "RESOLVE_CONFLICT",
            "ERROR",
        )
    },
    **{
        message_type: (
            "schemas/extensions/ext-capneg-payloads.schema.json",
            f"/$defs/{message_type}",
            "CN-CAPNEG-0.1",
        )
        for message_type in (
            "CAPABILITIES_DECLARE",
            "CAPABILITIES_PROPOSE",
            "CAPABILITIES_ACCEPT",
            "CAPABILITIES_REJECT",
        )
    },
    **{
        message_type: (
            "schemas/extensions/ext-policy-eval-payloads.schema.json",
            f"/$defs/{message_type}",
            "PE-POLICY-EVAL-0.1",
        )
        for message_type in ("POLICY_EVAL_REQUEST", "POLICY_EVAL_RESULT")
    },
    **{
        message_type: (
            "schemas/extensions/ext-enforcement-payloads.schema.json",
            f"/$defs/{message_type}",
            "ENF-ENFORCEMENT-0.1",
        )
        for message_type in (
            "CONTENT_MESSAGE",
            "ENFORCEMENT_VERDICT",
            "CONTENT_DELIVER",
        )
    },
    **{
        message_type: (
            "schemas/extensions/ext-resume-payloads.schema.json",
            f"/$defs/{message_type}",
            "RS-RESUME-0.1",
        )
        for message_type in ("RESUME_REQUEST", "RESUME_RESPONSE")
    },
    **{
        message_type: (
            "schemas/extensions/ext-object-resync-payloads.schema.json",
            f"/$defs/{message_type}",
            "OR-OBJECT-RESYNC-0.1",
        )
        for message_type in (
            "STATE_SYNC_REQUEST",
            "STATE_SYNC_RESPONSE",
            "OBJECT_REQUEST",
            "OBJECT_RESPONSE",
        )
    },
    **{
        message_type: (
            "schemas/extensions/ext-identity-lc-payloads.schema.json",
            f"/$defs/{message_type}",
            "ID-IDENTITY-LC-0.1",
        )
        for message_type in ("IDENTITY_ANNOUNCE", "KEY_ROTATION", "KEY_REVOKE")
    },
    **{
        message_type: (
            "schemas/extensions/ext-delegated-identity-payloads.schema.json",
            f"/$defs/{message_type}",
            "DI-DELEGATED-IDENTITY-0.1",
        )
        for message_type in ("SUBJECT_BINDING_ISSUE", "SUBJECT_BINDING_REVOKE")
    },
}


def test_every_private_flow_message_has_one_exact_v01_payload_route() -> None:
    scenarios = tier1_scenarios()
    assert payload_route_errors(scenarios, PRIVATE_FLOW_SEQUENCES) == []
    inventory = payload_route_inventory(scenarios, PRIVATE_FLOW_SEQUENCES)
    assert len(inventory) == len(EXPECTED_PAYLOAD_ROUTES) == 26
    observed = {
        item["message_type"]: (
            item["schema_path"],
            item["schema_pointer"],
            item["owning_suite"],
        )
        for item in inventory
    }
    assert observed == EXPECTED_PAYLOAD_ROUTES
    assert all(item["surface_version"] == "0.1" for item in inventory)
    assert all("v0.2" not in item["schema_path"] for item in inventory)
    assert all(item["producer_flows"] for item in inventory)


def test_conflicting_payload_route_fails_catalog_validation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    suite = load_json(ROOT / "conformance/core/CT_CORE_0.1.json")
    suite["suite_id"] = "TMP-CONFLICT-0.1"
    suite["payload_schema_map"] = {
        "CONTRACT_ACCEPT": "#/$defs/ATTEST_ACTION"
    }
    conflict_path = tmp_path / "conflicting_payload_route.json"
    conflict_path.write_text(json.dumps(suite, indent=2) + "\n", encoding="utf-8")
    scenarios = copy.deepcopy(tier1_scenarios())
    scenarios[0]["required_suites"].append(str(conflict_path.resolve()))
    _, route_errors = derive_payload_routes(scenarios)
    assert any("ambiguous payload schema route for CONTRACT_ACCEPT" in item for item in route_errors)

    import producer_suite_semantics as semantics

    monkeypatch.setattr(semantics, "tier1_scenarios", lambda: scenarios)
    catalog_errors = suite_coverage_errors(
        load_json(EVIDENCE_DIR / "mediated_blocking_producer_scenarios.json")[
            "scenarios"
        ]
    )
    assert any("ambiguous payload schema route" in item for item in catalog_errors)


def test_missing_payload_route_fails_producer_execution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import profile_transcript_evaluator as evaluator

    scenario, messages = _messages(
        "resumable_sessions_producer_scenarios.json",
        "resume_in_sync",
    )

    def fail_routes():
        raise ValueError("synthetic missing route")

    monkeypatch.setattr(evaluator, "tier1_payload_routes", fail_routes)
    evaluation = _evaluate(scenario, messages)
    assert not evaluation.accepted
    assert any(
        item["code"] == "EVIDENCE-GENERATED-PAYLOAD-SCHEMA-01"
        and "synthetic missing route" in item["message"]
        for item in evaluation.errors
    )


def test_semantic_parity_inventory_covers_all_current_suite_rows() -> None:
    scenarios = tier1_scenarios()
    inventory = producer_check_inventory(scenarios)
    parity = semantic_parity_inventory()
    assert len(inventory) == 95
    assert len(parity) == 18
    assert suite_coverage_errors(scenarios) == []
    assert all(item["parity_evidence"] for item in inventory)
    assert {
        "core_payload_schemas",
        "extension_payload_schemas",
        "core_contract",
        "core_policy_categories",
        "capneg_reason_codes",
        "capneg_privacy_modes",
        "capneg_bindings",
        "capneg_channel_properties",
        "policy_reason_codes",
        "policy_context_hash",
        "enforcement_sanctions",
        "enforcement_gate_authorization",
        "resume_semantics",
        "object_hash",
        "identity_lifecycle",
        "delegated_identity",
    }.issubset({item["family"] for item in parity})


PARITY_SUITE_PATHS = (
    "conformance/core/CT_CORE_0.1.json",
    "conformance/extensions/CN_CAPNEG_0.1.json",
    "conformance/extensions/DI_DELEGATED_IDENTITY_0.1.json",
    "conformance/extensions/ENF_ENFORCEMENT_0.1.json",
    "conformance/extensions/ID_IDENTITY_LC_0.1.json",
    "conformance/extensions/OR_OBJECT_RESYNC_0.1.json",
    "conformance/extensions/PE_POLICY_EVAL_0.1.json",
    "conformance/extensions/RS_RESUME_0.1.json",
)


def test_producer_evaluator_matches_ordinary_conformance_corpus_for_all_parity_families(
) -> None:
    compared_checks: set[str] = set()
    compared_transcripts = 0
    for suite_path in PARITY_SUITE_PATHS:
        suite = load_json(ROOT / suite_path)
        ordinary = run_suite(ROOT / suite_path)
        assert ordinary["passed"], ordinary["failures"]
        compared_checks.update(item["test_id"] for item in suite["checks"])
        for transcript in suite["transcripts"]:
            messages = [
                json.loads(line)
                for line in (ROOT / transcript["path"])
                .read_text(encoding="utf-8")
                .splitlines()
                if line.strip()
            ]
            evidence = evaluate_profile_transcript(messages, [suite_path])
            assert evidence.accepted is transcript.get("expect_pass", True), (
                suite["suite_id"],
                transcript["id"],
                evidence.errors,
            )
            compared_transcripts += 1

    assert compared_transcripts == 42
    inventory = producer_check_inventory(tier1_scenarios())
    assert {item["family"] for item in semantic_parity_inventory()} == {
        item["parity_family"]
        for item in inventory
        if item["check_id"] in compared_checks
    }


@pytest.mark.parametrize(
    "value",
    ["x-custom-category", "foo:custom-category"],
)
def test_core_policy_category_broad_namespace_is_preserved(value: str) -> None:
    assert is_broad_namespaced_identifier(value)
    scenario, messages = _messages(
        "mediated_blocking_producer_scenarios.json",
        "core_contract_action",
    )
    contract = _message(messages, "CONTRACT_PROPOSE")["payload"]["contract"]
    contract["policies"] = [
        {"policy_id": "p-custom", "category": value, "parameters": {}}
    ]
    _message(messages, "CONTRACT_PROPOSE")["payload"]["contract_hash"] = (
        object_hash("contract", contract)
    )
    for message in messages:
        message.pop("signatures", None)
    assert _evaluate(scenario, messages).accepted


@pytest.mark.parametrize(
    "value",
    ["x-custom-sanction", "foo:custom-sanction"],
)
def test_enforcement_sanction_broad_namespace_is_preserved(value: str) -> None:
    assert is_broad_namespaced_identifier(value)
    scenario, messages = _messages(
        "mediated_blocking_producer_scenarios.json",
        "policy_deny_block",
    )
    verdict = _message(messages, "ENFORCEMENT_VERDICT")["payload"]
    verdict["sanctions"] = [{"code": value}]
    assert _evaluate(scenario, messages).accepted


@pytest.fixture(scope="module")
def external_reports() -> dict[str, dict]:
    return {
        target: _external_report(target)
        for target in (
            "AICP-MEDIATED-BLOCKING@0.1",
            "AICP-RESUMABLE-SESSIONS@0.1",
            "AICP-DELEGATED-IDENTITY@0.1",
        )
    }


def _unexpected(message_type: str):
    return lambda messages: _message(messages, message_type)["payload"].__setitem__(
        "unexpected", True
    )


def _missing_accept(messages: list[dict]) -> None:
    _message(messages, "CONTRACT_ACCEPT")["payload"].pop("accepted")


def _missing_action_type(messages: list[dict]) -> None:
    _message(messages, "ATTEST_ACTION")["payload"].pop("action_type")


PAYLOAD_REPORT_MUTATIONS = (
    ("AICP-RESUMABLE-SESSIONS@0.1", "RS-RESUME-IN-SYNC", _unexpected("CONTRACT_ACCEPT")),
    ("AICP-RESUMABLE-SESSIONS@0.1", "RS-RESUME-IN-SYNC", _missing_accept),
    ("AICP-DELEGATED-IDENTITY@0.1", "DI-IDENTITY-ANNOUNCE-USE", _missing_action_type),
    ("AICP-MEDIATED-BLOCKING@0.1", "MB-CORE-CONFLICT-CHOOSE", _unexpected("CONTEXT_AMEND")),
    ("AICP-RESUMABLE-SESSIONS@0.1", "RS-CORE-RESYNC", _unexpected("STATE_SYNC_RESPONSE")),
    ("AICP-RESUMABLE-SESSIONS@0.1", "RS-RESUME-IN-SYNC", _unexpected("RESUME_RESPONSE")),
    ("AICP-MEDIATED-BLOCKING@0.1", "MB-CAPNEG-ACCEPT-CONTRACT", _unexpected("CAPABILITIES_PROPOSE")),
    ("AICP-DELEGATED-IDENTITY@0.1", "DI-IDENTITY-ANNOUNCE-USE", _unexpected("IDENTITY_ANNOUNCE")),
    ("AICP-DELEGATED-IDENTITY@0.1", "DI-BINDING-ISSUE-USE", _unexpected("SUBJECT_BINDING_ISSUE")),
)


@pytest.mark.parametrize(
    ("target_key", "scenario_id", "mutate"),
    PAYLOAD_REPORT_MUTATIONS,
)
def test_independent_report_evaluator_rejects_every_payload_schema_mutation(
    external_reports: dict[str, dict],
    target_key: str,
    scenario_id: str,
    mutate,
) -> None:
    report = copy.deepcopy(external_reports[target_key])
    artifact = _report_artifact(report, scenario_id)
    mutate(artifact["content"]["messages"])
    _refresh_artifact(artifact)
    verdict = _evaluate_report(report)
    assert verdict["status"] == "rejected"
    assert verdict["eligible_marks"] == []
    assert any(
        "EVIDENCE-GENERATED-PAYLOAD-SCHEMA-01" in item
        for item in verdict["errors"]
    )


def _mutate_report_artifact(report: dict, scenario_id: str, mutate) -> None:
    artifact = _report_artifact(report, scenario_id)
    mutate(artifact["content"]["messages"])
    _refresh_artifact(artifact)


@pytest.mark.parametrize(
    ("target_key", "scenario_id", "mutate", "check_id"),
    [
        (
            "AICP-RESUMABLE-SESSIONS@0.1",
            "RS-RESUME-IN-SYNC",
            _unexpected("CONTRACT_ACCEPT"),
            "EVIDENCE-GENERATED-PAYLOAD-SCHEMA-01",
        ),
        (
            "AICP-RESUMABLE-SESSIONS@0.1",
            "RS-CORE-RESYNC",
            _unexpected("STATE_SYNC_RESPONSE"),
            "EVIDENCE-GENERATED-PAYLOAD-SCHEMA-01",
        ),
    ],
)
def test_payload_router_is_independently_load_bearing(
    external_reports: dict[str, dict],
    target_key: str,
    scenario_id: str,
    mutate,
    check_id: str,
) -> None:
    report = copy.deepcopy(external_reports[target_key])
    _mutate_report_artifact(report, scenario_id, mutate)
    assert _evaluate_report(report)["status"] == "rejected"
    bypass = _evaluate_report(report, frozenset({check_id}))
    assert bypass["status"] == "eligible"
    assert bypass["eligible_marks"] == [report["compatibility_marks"][0]]


def _mutate_policy_reason(messages: list[dict]) -> None:
    decision = _message(messages, "POLICY_EVAL_RESULT")["payload"][
        "policy_decision"
    ]
    decision["reason_codes"] = ["foo:custom-reason"]


@pytest.mark.parametrize("privacy", ["foo:private", "x-private-mode"])
def test_namespace_checks_are_independently_load_bearing(
    external_reports: dict[str, dict],
    privacy: str,
) -> None:
    pe_report = copy.deepcopy(external_reports["AICP-MEDIATED-BLOCKING@0.1"])
    _mutate_report_artifact(pe_report, "MB-POLICY-ALLOW-DELIVERY", _mutate_policy_reason)
    assert _evaluate_report(pe_report)["status"] == "rejected"
    assert _evaluate_report(
        pe_report, frozenset({"PE-REASON-CODES-01"})
    )["status"] == "eligible"

    cn_report = copy.deepcopy(external_reports["AICP-MEDIATED-BLOCKING@0.1"])
    _mutate_report_artifact(
        cn_report,
        "MB-CAPNEG-ACCEPT-CONTRACT",
        lambda messages: _set_privacy_mode(messages, privacy),
    )
    assert _evaluate_report(cn_report)["status"] == "rejected"
    assert _evaluate_report(
        cn_report, frozenset({"CN-PRIVACY-MODES-01"})
    )["status"] == "eligible"


def test_tck_1_3_is_frozen_and_tck_1_4_is_current(
    external_reports: dict[str, dict],
) -> None:
    previous = release_record(PREVIOUS_TCK_RELEASE_ID)
    assert canonical_digest(previous) == FROZEN_TCK_1_3_RECORD_DIGEST
    assert release_snapshot_digest(PREVIOUS_TCK_RELEASE_ID) == (
        FROZEN_TCK_1_3_REGISTRY_SNAPSHOT_DIGEST
    )
    assert file_digest(
        EVIDENCE_DIR / "evidence_runner_bundle_v1_3.json"
    ) == FROZEN_TCK_1_3_BUNDLE_MANIFEST_DIGEST
    assert release_policy(PREVIOUS_TCK_RELEASE_ID)["strong_eligible"] is False
    assert release_policy(CURRENT_TCK_RELEASE_ID)["strong_eligible"] is True
    assert CURRENT_TCK_RELEASE_ID == "AICP-EVIDENCE-TCK-1.10.0"
    for report in external_reports.values():
        assert report["tck_release"]["release_id"] == CURRENT_TCK_RELEASE_ID
        assert _evaluate_report(report)["status"] == "eligible"


def test_no_checked_in_external_submission_depends_on_tck_1_3() -> None:
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
            == PREVIOUS_TCK_RELEASE_ID
        ):
            references.append(path.relative_to(ROOT).as_posix())
    assert references == []
