from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = ROOT / "conformance" / "evidence"
SCRIPTS_DIR = ROOT / "scripts"
for path in (EVIDENCE_DIR, SCRIPTS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from aicp_external_evidence_runner import build_execution_plan, run_evidence  # noqa: E402
from interop_submission_validation import evaluate_strong_report_evidence  # noqa: E402
from product_profile_fake_adapters import MODES  # noqa: E402
from report_evaluator import evaluate_report  # noqa: E402
from target_catalog import (  # noqa: E402
    BUNDLE_MANIFEST_PATH,
    BINDING_TARGET_KEYS,
    CURRENT_TCK_RELEASE_ID,
    FROZEN_TCK_1_1_RECORD_DIGEST,
    HISTORICAL_RELEASE_RECORD_DIGEST,
    PROFILE_TARGET_KEYS,
    PROFILE_TCK_RELEASE_ID,
    TARGET_KEY,
    canonical_digest,
    load_json,
    mandatory_case_ids,
    release_record,
    resolve_target_record,
    target_catalog,
    validate_bundle_manifest,
    validate_release_registry,
    validate_target_catalog,
    validate_target_registry,
)
from target_handlers import resolve_handler  # noqa: E402


SPEC = importlib.util.spec_from_file_location(
    "generate_evidence_framework_m63_test",
    ROOT / "scripts/generate_evidence_framework.py",
)
assert SPEC is not None and SPEC.loader is not None
GENERATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENERATOR)

EXPECTED = {
    "AICP-MEDIATED-BLOCKING@0.1": {
        "mark": "AICP-Profile-MEDIATED-BLOCKING-0.1",
        "producer_count": 10,
        "consumer_count": 30,
        "negative_modes": (
            "profile_downgrade",
            "missing_capneg_contract_binding",
            "unsupported_selected_profile",
            "malformed_core_contract",
            "unknown_core_policy_category",
            "duplicate_core_policy_id",
            "wrong_generated_sequence",
            "invalid_capneg_reason_code",
            "invalid_capneg_privacy_mode",
            "invalid_capneg_binding",
            "invalid_capneg_channel_properties",
            "policy_reason_code_failure",
            "policy_context_hash_failure",
            "deny_followed_by_delivery",
            "wrong_enforcement_binding",
            "unauthorized_enforcer",
            "invalid_enforcement_sanction_code",
            "malformed_namespaced_enforcement_sanction",
        ),
    },
    "AICP-RESUMABLE-SESSIONS@0.1": {
        "mark": "AICP-Profile-RESUMABLE-SESSIONS-0.1",
        "producer_count": 9,
        "consumer_count": 20,
        "negative_modes": (
            "missing_resume_response",
            "mismatched_resume_response",
            "inconsistent_resume_head",
            "forced_resync_loop",
            "invalid_resume_recommended_action",
            "invalid_object_hash",
            "mismatched_object_response",
            "invalid_state_sync",
        ),
    },
    "AICP-DELEGATED-IDENTITY@0.1": {
        "mark": "AICP-Profile-DELEGATED-IDENTITY-0.1",
        "producer_count": 13,
        "consumer_count": 32,
        "negative_modes": (
            "unsigned_binding_issue",
            "invalid_issue_signature",
            "wrong_binding_issuer",
            "binding_object_hash_mismatch",
            "expired_binding_use",
            "revoked_binding_use",
            "revoked_identity_key_use",
            "invalid_rotation_cross_signature",
            "unknown_key",
            "kid_mismatch",
            "acting_agent_mismatch",
        ),
    },
}
GENERIC_NEGATIVE_MODES = (
    "target_not_declared",
    "wrong_profile_id",
    "wrong_profile_version",
    "missing_producer_scenario",
    "wrong_producer_scenario_identity",
    "nondeterministic_repeat",
    "missing_consumer_case",
    "duplicate_consumer_case",
    "consumer_accepts_every_fixture",
    "consumer_rejects_every_fixture",
    "consumer_missing_fields",
    "unexpected_degradation",
    "hidden_skipped_check",
    "wrong_profile_catalog_digest",
    "wrong_suite_digest",
    "wrong_input_digest",
    "wrong_runner_digest",
    "wrong_report_schema_digest",
    "forged_compatibility_mark",
    "reference_subject_with_external_mark",
)


def _command(adapter: str, *args: str) -> list[str]:
    return [sys.executable, adapter, *args]


def _external_report(target_key: str) -> dict:
    return run_evidence(
        _command(
            "conformance/evidence/product_profile_fake_adapters.py",
            "--mode",
            "external_good",
        ),
        target=target_key,
        mode="full-profile",
        timestamp="2026-08-08T00:00:00Z",
    )


def _all_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {
            key for child in value.values() for key in _all_keys(child)
        }
    if isinstance(value, list):
        return {key for child in value for key in _all_keys(child)}
    return set()


def test_frozen_m62_and_iut_boundaries_are_unchanged() -> None:
    # Git stores these text artifacts with LF. Windows checkouts may materialize
    # CRLF, so hash the repository-normalized bytes rather than platform-specific
    # working-tree line endings.
    frozen_files = {
        "conformance/iut/iut_report_v1.schema.json": "728cc512439c162327412570576754d07244da694aceb90e681cb7fa15ba0ee4",
        "conformance/iut/cases.json": "6b033ce91eee939f637df6efda2ea7c2f011b752b6b09c810d51dbe83bf637fe",
        "conformance/iut/aicp_iut_runner.py": "bc82d59ffe919098606d9543a823811da43bc1720436fe1197636edc46e9e2fd",
        "conformance/evidence/external_evidence_report_v2.schema.json": "f1afe5b31e231f1fb3e24c151b6a0ccf07fd025e9e79cd903293ac7210ae8ddd",
        "conformance/evidence/evidence_runner_bundle.json": "a1505f9a8e2519009a3d18dd7c1c114c2752f6e942432cd6846137640504d2d0",
    }
    for relative, expected in frozen_files.items():
        repository_bytes = (ROOT / relative).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(repository_bytes).hexdigest() == expected
    assert canonical_digest(release_record("AICP-EVIDENCE-TCK-1.0.0")) == (
        HISTORICAL_RELEASE_RECORD_DIGEST
    )
    assert canonical_digest(release_record("AICP-EVIDENCE-TCK-1.1.0")) == (
        FROZEN_TCK_1_1_RECORD_DIGEST
    )
    assert resolve_target_record(TARGET_KEY).current_release_id == (
        CURRENT_TCK_RELEASE_ID
    )


def test_generated_registry_release_and_three_catalogs_are_exact() -> None:
    targets, projection, profiles, bundle, releases = GENERATOR.generated_payloads()
    assert load_json(EVIDENCE_DIR / "targets.json") == targets
    assert load_json(EVIDENCE_DIR / "session_state_projection_v1_target.json") == projection
    assert load_json(BUNDLE_MANIFEST_PATH) == bundle
    assert load_json(EVIDENCE_DIR / "evidence_tck_releases.json") == releases
    assert [item["target_key"] for item in targets["targets"]] == [
        TARGET_KEY,
        *PROFILE_TARGET_KEYS,
        *BINDING_TARGET_KEYS,
    ]
    assert validate_target_registry(targets, enforce_current_scope=True) == []
    assert validate_bundle_manifest(bundle) == []
    assert validate_release_registry(releases, bundle_manifest=bundle) == []
    assert release_record(PROFILE_TCK_RELEASE_ID, releases)["targets"]

    total_consumers = 0
    for target_key, expectation in EXPECTED.items():
        record = resolve_target_record(target_key)
        catalog = profiles[target_key]
        assert load_json(ROOT / record.catalog_path) == catalog
        assert validate_target_catalog(
            catalog,
            record=record,
            handler=resolve_handler(record.handler_id),
        ) == []
        assert len(catalog["producer_scenarios"]) == expectation["producer_count"]
        assert len(catalog["consumer_cases"]) == expectation["consumer_count"]
        total_consumers += len(catalog["consumer_cases"])
        observed = Counter(
            (item["source_suite_id"], item["source_case_id"])
            for item in catalog["consumer_cases"]
        )
        expected = Counter()
        for suite_record in catalog["required_suites"]:
            suite = load_json(ROOT / suite_record["path"])
            expected.update(
                (suite["suite_id"], item["id"])
                for item in suite["transcripts"]
            )
        assert observed == expected
        assert len(mandatory_case_ids(catalog, "full-profile", resolve_handler(record.handler_id))) == (
            7 + expectation["producer_count"] + expectation["consumer_count"]
        )
    assert total_consumers == 82


@pytest.mark.parametrize("target_key", PROFILE_TARGET_KEYS)
def test_profile_requests_are_answer_isolated(target_key: str) -> None:
    record = resolve_target_record(target_key)
    catalog = target_catalog(record)
    requests, _ = build_execution_plan(
        record,
        catalog,
        resolve_handler(record.handler_id),
        "full-profile",
    )
    producer_requests = [
        request for request in requests if request["operation"] == "generate_scenario"
    ]
    assert len(producer_requests) == 2 * len(catalog["producer_scenarios"])
    for request in producer_requests:
        public = request["input"]
        serialized = json.dumps(public, sort_keys=True)
        assert "fixture" not in serialized
        assert "expected" not in serialized
        assert "case_id" not in serialized
        assert "messages" not in public
        assert set(public) == {"target", "scenario", "runtime_options"}
    for first, repeat in zip(producer_requests[::2], producer_requests[1::2]):
        assert first["request_id"] != repeat["request_id"]
        assert first["input"] == repeat["input"]

    for request in (
        item for item in requests if item["operation"] == "validate_transcript"
    ):
        assert set(request["input"]) == {
            "target",
            "transcript",
            "public_verification_material",
            "runtime_options",
        }
        serialized = json.dumps(request["input"], sort_keys=True)
        assert not ({"fixture", "expected", "case_id"} & _all_keys(request["input"]))
        assert all(
            case["fixture"] not in serialized for case in catalog["consumer_cases"]
        )


@pytest.mark.parametrize("target_key", PROFILE_TARGET_KEYS)
def test_reference_and_external_full_profile_eligibility(target_key: str) -> None:
    reference = run_evidence(
        _command("conformance/evidence/product_profile_reference_adapter.py"),
        target=target_key,
        mode="full-profile",
        timestamp="2026-08-08T00:00:00Z",
    )
    assert reference["passed"] is True
    assert reference["compatibility_marks"] == []
    assert evaluate_report(reference)["status"] == "ineligible"

    external = _external_report(target_key)
    expectation = EXPECTED[target_key]
    assert external["report_format_version"] == "2.2"
    assert external["runner"]["version"] == "2.2"
    assert external["passed"] is True
    assert external["compatibility_marks"] == [expectation["mark"]]
    assert len(external["generated_artifacts"]) == expectation["producer_count"]
    assert all(
        item["artifact_kind"] == "transcript"
        and item["content_digest"] == item["repeat_content_digest"]
        for item in external["generated_artifacts"]
    )
    verdict = evaluate_report(
        external,
        expected_implementation_id="test-only-product-profile-external",
        expected_implementation_version="1.0.0",
    )
    assert verdict == {
        "status": "eligible",
        "errors": [],
        "eligible_marks": [expectation["mark"]],
        "eligible_targets": [resolve_target_record(target_key).identity()],
    }


NEGATIVE_CASES = [
    (target_key, mode)
    for target_key, expectation in EXPECTED.items()
    for mode in expectation["negative_modes"]
] + [
    ("AICP-MEDIATED-BLOCKING@0.1", mode)
    for mode in GENERIC_NEGATIVE_MODES
]


def test_every_fake_adapter_mode_is_accounted_for() -> None:
    accounted = {"external_good"} | {mode for _, mode in NEGATIVE_CASES}
    assert accounted == set(MODES)


@pytest.mark.parametrize(("target_key", "mode"), NEGATIVE_CASES)
def test_every_negative_adapter_mode_emits_no_profile_mark(
    target_key: str,
    mode: str,
) -> None:
    report = run_evidence(
        _command(
            "conformance/evidence/product_profile_fake_adapters.py",
            "--mode",
            mode,
        ),
        target=target_key,
        mode="full-profile",
        timestamp="2026-08-08T00:00:00Z",
    )
    assert report["compatibility_marks"] == []


@pytest.mark.parametrize("target_key", PROFILE_TARGET_KEYS)
@pytest.mark.parametrize("dependency", ["jsonschema", "crypto"])
def test_missing_mandatory_dependency_suppresses_marks(
    target_key: str,
    dependency: str,
) -> None:
    options = {
        "simulate_no_jsonschema": dependency == "jsonschema",
        "simulate_no_crypto": dependency == "crypto",
    }
    report = run_evidence(
        _command(
            "conformance/evidence/product_profile_fake_adapters.py",
            "--mode",
            "external_good",
        ),
        target=target_key,
        mode="full-profile",
        timestamp="2026-08-08T00:00:00Z",
        **options,
    )
    assert report["degraded"] is True
    assert report["compatibility_marks"] == []


def _profile_manifest(report_ref: str = "report.json") -> dict:
    return {
        "claim_type": "implements_profile",
        "evidence_status": "reproducible",
        "profile_ids": ["AICP-MEDIATED-BLOCKING"],
        "profile_refs": [
            {
                "profile_id": "AICP-MEDIATED-BLOCKING",
                "profile_version": "0.1",
            }
        ],
        "suite_refs": [
            "CT-CORE-0.1",
            "CN-CAPNEG-0.1",
            "PE-POLICY-EVAL-0.1",
            "ENF-ENFORCEMENT-0.1",
        ],
        "report_refs": [report_ref],
        "implementation_id": "test-only-product-profile-external",
        "implementation_version": "1.0.0",
    }


def test_public_profile_claim_accepts_v21_and_suite_refs_are_load_bearing(
    tmp_path: Path,
) -> None:
    report = _external_report("AICP-MEDIATED-BLOCKING@0.1")
    (tmp_path / "report.json").write_text(json.dumps(report), encoding="utf-8")
    manifest = _profile_manifest()
    evaluation = evaluate_strong_report_evidence(tmp_path / "submission.json", manifest)
    assert evaluation.status == "eligible"
    assert evaluation.eligible_profile_marks == (
        "AICP-Profile-MEDIATED-BLOCKING-0.1",
    )
    assert evaluation.eligible_capability_marks == ()

    mutations = [
        manifest["suite_refs"][:-1],
        [*manifest["suite_refs"], manifest["suite_refs"][0]],
        [*manifest["suite_refs"], "OR-OBJECT-RESYNC-0.1"],
    ]
    for suite_refs in mutations:
        rejected = evaluate_strong_report_evidence(
            tmp_path / "submission.json",
            {**manifest, "suite_refs": suite_refs},
        )
        assert rejected.status == "rejected"
        assert rejected.eligible_marks == ()


def test_report_evaluator_does_not_trust_runner_conclusions() -> None:
    report = _external_report("AICP-MEDIATED-BLOCKING@0.1")
    forged = copy.deepcopy(report)
    forged["case_results"] = forged["case_results"][:-1]
    assert forged["passed"] is True
    assert forged["compatibility_marks"]
    verdict = evaluate_report(
        forged,
        expected_implementation_id="test-only-product-profile-external",
        expected_implementation_version="1.0.0",
    )
    assert verdict["status"] == "rejected"
    assert verdict["eligible_marks"] == []


@pytest.mark.parametrize(
    ("check", "mutate"),
    [
        (
            "target_provenance",
            lambda report: report["target"].update(
                {"target_catalog_digest": "sha256:" + "5" * 64}
            ),
        ),
        ("case_coverage", lambda report: report["case_results"].pop(0)),
        (
            "determinism",
            lambda report: report["generated_artifacts"][0].update(
                {"repeat_content_digest": "sha256:" + "6" * 64}
            ),
        ),
        (
            "consumer_observations",
            lambda report: next(
                item
                for item in report["case_results"]
                if item["case_id"].startswith("EVIDENCE-CONSUMER")
            )["execution_observation"].update({"accepted": False}),
        ),
        (
            "subject_kind",
            lambda report: report["execution_subject"].update(
                {"kind": "reference_corpus"}
            ),
        ),
    ],
)
def test_profile_evaluator_mutation_controls_are_load_bearing(
    check: str,
    mutate,
) -> None:
    report = _external_report("AICP-MEDIATED-BLOCKING@0.1")
    mutate(report)
    kwargs = {
        "expected_implementation_id": "test-only-product-profile-external",
        "expected_implementation_version": "1.0.0",
    }
    assert evaluate_report(report, **kwargs)["status"] == "rejected"
    corrupted = evaluate_report(
        report,
        disabled_checks=frozenset({check}),
        **kwargs,
    )
    assert corrupted["status"] == "eligible"
    assert corrupted["eligible_marks"] == [
        "AICP-Profile-MEDIATED-BLOCKING-0.1"
    ]
