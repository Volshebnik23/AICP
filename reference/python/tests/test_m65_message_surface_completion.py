from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "conformance/runner"))
sys.path.insert(0, str(ROOT / "conformance/evidence"))
sys.path.insert(0, str(ROOT / "reference/python"))

from aicp_conformance_runner import run_suite  # noqa: E402
from aicp_ref.hashing import message_hash_from_body  # noqa: E402
from report_evaluator import evaluate_report  # noqa: E402
from target_catalog import (  # noqa: E402
    BUNDLE_MANIFEST_PATH,
    CURRENT_TCK_RELEASE_ID,
    EXPECTED_TARGET_KEYS,
    FROZEN_TCK_1_8_BUNDLE_MANIFEST_DIGEST,
    FROZEN_TCK_1_8_LIVE_TRACE_SCHEMA_DIGEST,
    FROZEN_TCK_1_8_PUBLIC_SCENARIO_SCHEMA_DIGEST,
    FROZEN_TCK_1_8_RECORD_DIGEST,
    FROZEN_TCK_1_8_REGISTRY_SNAPSHOT_DIGEST,
    FROZEN_TCK_1_8_REPORT_SCHEMA_DIGEST,
    FROZEN_TCK_1_8_RUNNER_BUNDLE_DIGEST,
    FROZEN_TCK_1_8_TARGET_CATALOG_DIGESTS,
    FROZEN_TCK_1_8_TARGET_REGISTRY_DIGEST,
    FROZEN_TCK_1_8_TARGET_REGISTRY_SCHEMA_DIGEST,
    FROZEN_TCK_1_9_BUNDLE_MANIFEST_DIGEST,
    FROZEN_TCK_1_9_RECORD_DIGEST,
    FROZEN_TCK_1_9_REGISTRY_SNAPSHOT_DIGEST,
    FROZEN_TCK_1_9_REPORT_SCHEMA_DIGEST,
    FROZEN_TCK_1_9_RUNNER_BUNDLE_DIGEST,
    FROZEN_TCK_1_9_TARGET_CATALOG_DIGESTS,
    FROZEN_TCK_1_9_TARGET_REGISTRY_DIGEST,
    FROZEN_TCK_1_9_TARGET_REGISTRY_SCHEMA_DIGEST,
    TCK_1_4_RELEASE_ID,
    TCK_1_8_RELEASE_ID,
    TCK_1_9_RELEASE_ID,
    TCK_1_10_RELEASE_ID,
    TCK_RELEASE_ID,
    canonical_digest,
    file_digest,
    release_policy,
    release_record,
    release_snapshot_digest,
    validate_release_registry,
)  # noqa: E402
from validate_message_surface_completion import completion_errors  # noqa: E402


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def _synthetic_surface_root(tmp_path: Path, mode: str) -> Path:
    spec_ref = "docs/extensions/RFC_EXT_FACILITATION.md#message-types-normative"
    _write_json(
        tmp_path / "registry/message_types.json",
        [{"id": "AGENDA_DECLARE", "spec_ref": spec_ref}],
    )
    _write_json(
        tmp_path / "registry/extension_ids.json",
        [{"id": "EXT-FACILITATION", "spec_ref": spec_ref}],
    )
    _write_json(
        tmp_path / "conformance/core/CT_CORE_0.1.json",
        {"payload_schema_map": {}},
    )

    fixture = tmp_path / "fixtures/extensions/facilitation/candidate.jsonl"
    fixture.parent.mkdir(parents=True, exist_ok=True)
    actual_type = "AGENDA_DECLARE" if mode == "negative" else "TURN_REQUEST"
    fixture.write_text(
        json.dumps({"message_type": actual_type, "payload": {"turn_id": "turn-1"}})
        + "\n",
        encoding="utf-8",
    )
    transcripts: list[dict] = []
    if mode == "metadata":
        transcripts.append(
            {
                "id": "FA-METADATA-ONLY",
                "path": fixture.relative_to(tmp_path).as_posix(),
                "expected_message_types": ["AGENDA_DECLARE"],
            }
        )
    elif mode == "negative":
        transcripts.append(
            {
                "id": "FA-NEGATIVE-ONLY",
                "path": fixture.relative_to(tmp_path).as_posix(),
                "expected_message_types": ["AGENDA_DECLARE"],
                "expect_pass": False,
            }
        )
    _write_json(
        tmp_path / "conformance/extensions/FA_FACILITATION_0.1.json",
        {
            "payload_schema_ref": "schemas/extensions/ext-facilitation-payloads.schema.json",
            "payload_schema_map": {"AGENDA_DECLARE": "#/$defs/AGENDA_DECLARE"},
            "transcripts": transcripts,
            "checks": [{"test_id": "CT-SEQUENCE-01"}],
        },
    )
    return tmp_path


@pytest.mark.parametrize("mode", ["metadata", "negative", "orphan"])
def test_completion_gate_rejects_non_positive_byte_coverage(
    tmp_path: Path, mode: str
) -> None:
    root = _synthetic_surface_root(tmp_path, mode)
    errors = completion_errors(root)
    assert any(
        "missing actual positive fixture coverage: AGENDA_DECLARE" in error
        for error in errors
    )


def _b64url_no_pad(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _sign(private_key: Ed25519PrivateKey, digest: str) -> str:
    return _b64url_no_pad(
        private_key.sign(f"AICP1\0SIG\0{digest}".encode("utf-8"))
    )


def _private_keys() -> dict[tuple[str, str], Ed25519PrivateKey]:
    test_keys = json.loads(
        (ROOT / "fixtures/keys/TEST_private_keys.json").read_text(encoding="utf-8")
    )
    moderator = test_keys["moderator:Z"]["private_key_b64url"]
    moderator_raw = base64.urlsafe_b64decode(
        moderator + "=" * (-len(moderator) % 4)
    )
    return {
        ("agent:Q", "Q1"): Ed25519PrivateKey.from_private_bytes(bytes(range(1, 33))),
        ("moderator:Z", "Z1"): Ed25519PrivateKey.from_private_bytes(moderator_raw),
        ("auth:IDP", "P1"): Ed25519PrivateKey.from_private_bytes(bytes([11]) * 32),
        ("agent:A", "A1"): Ed25519PrivateKey.from_private_bytes(bytes([22]) * 32),
    }


def _rehash_and_resign(messages: list[dict]) -> None:
    keys = _private_keys()
    previous: str | None = None
    for message in messages:
        signatures = message.pop("signatures", None)
        message.pop("message_hash", None)
        message.pop("prev_msg_hash", None)
        if previous is not None:
            message["prev_msg_hash"] = previous
        digest = message_hash_from_body(message)
        message["message_hash"] = digest
        previous = digest
        if not signatures:
            continue
        for signature in signatures:
            key = keys[(signature["signer"], signature["kid"])]
            signature["object_hash"] = digest
            signature["sig_b64url"] = _sign(key, digest)
        message["signatures"] = signatures


def _mutated_report(
    tmp_path: Path,
    suite_relative: str,
    fixture_relative: str,
    mutate: object,
) -> dict:
    suite = json.loads((ROOT / suite_relative).read_text(encoding="utf-8"))
    messages = [
        json.loads(line)
        for line in (ROOT / fixture_relative).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    assert callable(mutate)
    mutate(messages)
    _rehash_and_resign(messages)
    fixture_path = tmp_path / Path(fixture_relative).name
    fixture_path.write_text(
        "\n".join(json.dumps(message, separators=(",", ":")) for message in messages)
        + "\n",
        encoding="utf-8",
    )
    suite["suite_id"] = "M65-MUTATION"
    suite["transcripts"] = [
        {
            "id": "M65-MUTATION",
            "path": fixture_path.as_posix(),
            "expected_message_types": [message["message_type"] for message in messages],
        }
    ]
    suite.pop("compatibility_mark", None)
    suite_path = tmp_path / "suite.json"
    _write_json(suite_path, suite)
    return run_suite(suite_path)


def _mutate_payload(message_type: str, field: str, value: str):
    def apply(messages: list[dict]) -> None:
        target = next(message for message in messages if message["message_type"] == message_type)
        target["payload"][field] = value

    return apply


@pytest.mark.parametrize(
    ("suite", "fixture", "mutate", "expected_check"),
    [
        (
            "conformance/extensions/MP_MARKETPLACE_0.1.json",
            "fixtures/extensions/marketplace/MP-10_bid_update_withdraw_award_decline_pass.jsonl",
            _mutate_payload("AWARD_DECLINE", "award_id", "award-unknown"),
            "MP-AWARD-01",
        ),
        (
            "conformance/extensions/RP_RESPONSIBILITY_0.1.json",
            "fixtures/extensions/responsibility/RP-06_assign_revoke_pass.jsonl",
            _mutate_payload("RESPONSIBILITY_REVOKE", "transfer_id", "t-unknown"),
            "RS-ACCEPT-01",
        ),
        (
            "conformance/extensions/EX_EXECUTION_LIFECYCLE_0.1.json",
            "fixtures/extensions/execution_lifecycle/EX-08_active_run_cancel_pass.jsonl",
            _mutate_payload("RUN_CANCEL", "run_id", "run-unknown"),
            "EX-RUN-REF-01",
        ),
    ],
)
def test_hash_valid_semantic_mutations_fail_the_owning_check(
    tmp_path: Path,
    suite: str,
    fixture: str,
    mutate: object,
    expected_check: str,
) -> None:
    report = _mutated_report(tmp_path, suite, fixture, mutate)
    observed = {failure["test_id"] for failure in report["failures"]}
    assert expected_check in observed
    assert "CT-MESSAGE-HASH-01" not in observed
    assert "CT-HASH-CHAIN-01" not in observed
    assert "CT-SIGNATURE-HASH-01" not in observed
    assert "CT-SIGNATURE-VERIFY-01" not in observed


def test_schema_only_positive_fixture_is_rejected(tmp_path: Path) -> None:
    report = _mutated_report(
        tmp_path,
        "conformance/extensions/FA_FACILITATION_0.1.json",
        "fixtures/extensions/facilitation/FA-02_agenda_and_turn_revoke_pass.jsonl",
        lambda messages: next(
            message for message in messages if message["message_type"] == "AGENDA_DECLARE"
        )["payload"].pop("agenda_id"),
    )
    observed = {failure["test_id"] for failure in report["failures"]}
    assert "CN-PAYLOAD-SCHEMA-01" in observed
    assert "CT-MESSAGE-HASH-01" not in observed
    assert "CT-HASH-CHAIN-01" not in observed


def test_final_registered_message_surface_is_exactly_complete() -> None:
    assert completion_errors(ROOT) == []


def test_m65_audit_inventory_matches_mechanical_repo_truth() -> None:
    audit = json.loads(
        (ROOT / "docs/process/M65_Message_Surface_Audit.json").read_text(
            encoding="utf-8"
        )
    )
    expected_gap = {
        "AGENDA_DECLARE",
        "AGENDA_UPDATE",
        "AGENT_MIGRATION",
        "ARBITRATION_REQUEST",
        "ARBITRATION_RESULT",
        "AWARD_DECLINE",
        "BID_UPDATE",
        "BID_WITHDRAW",
        "CLAIM_BREACH",
        "DELEGATION_REVOKE",
        "KEY_REVOKE",
        "PARTICIPANT_LEAVE",
        "POLICY_DECISION_ATTEST",
        "RESPONSIBILITY_REVOKE",
        "RUN_CANCEL",
        "SUBJECT_BINDING_REVOKE",
        "TURN_REVOKE",
    }
    assert set(audit["baseline_missing_positive_fixture_types"]) == expected_gap
    assert len(audit["entries"]) == 17

    from repo_truth import derive_message_surface

    current = {
        entry["id"]: entry for entry in derive_message_surface(ROOT)["entries"]
    }
    for item in audit["entries"]:
        derived = current[item["message_type"]]
        assert item["owner"] == derived["owner"]
        assert item["payload_schema_file"] == derived["payload_schema"]["file"]
        assert item["payload_schema_pointer"] == derived["payload_schema"]["pointer"]
        assert item["owning_suite"] in derived["suites"]
        assert item["positive_coverage"]["fixture"] in derived["positive_fixtures"]
        assert (ROOT / item["normative_rfc"]).is_file()
        assert (ROOT / item["positive_coverage"]["generator"]).is_file()
        for candidate in item["candidate_fixtures_before"]:
            assert (ROOT / candidate).is_file()
        suite = json.loads((ROOT / item["owning_suite"]).read_text(encoding="utf-8"))
        checks = {check["test_id"] for check in suite["checks"]}
        assert set(item["positive_coverage"]["semantic_checks"]).issubset(checks)
        assert item["negative_accounting"]["rfc_basis"]
        assert item["negative_accounting"]["check"] in checks

    audited_changes = {
        (item["suite"], item["check_id"])
        for item in audit["semantic_change_audit"]
    }
    assert audited_changes == {
        ("ID-IDENTITY-LC-0.1", "ID-MIGRATE-01"),
        ("ID-IDENTITY-LC-0.1", "ID-REVOKE-01"),
        ("DS-DISPUTES-0.1", "DS-EVIDENCE-01"),
        ("DS-DISPUTES-0.1", "DS-EVIDENCE-RESOLVE-01"),
        ("DS-DISPUTES-0.1", "DS-ARBITRATION-01"),
        ("DL-DELEGATION-0.1", "DL-REVOKE-01"),
        ("MP-MARKETPLACE-0.1", "MP-BID-01"),
        ("PA-PARTICIPANTS-0.1", "PA-MEM-01"),
        ("PE-POLICY-EVAL-0.1", "PE-ATTEST-01"),
        ("DI-DELEGATED-IDENTITY-0.1", "DI-REVOKE-01"),
    }
    assert all(
        item["compatibility_rejection_justified"] is False
        for item in audit["semantic_change_audit"]
    )

    new_fixtures = {
        item["positive_coverage"]["fixture"]
        for item in audit["entries"]
        if item["positive_coverage"]["kind"] == "new"
    }
    reused_fixtures = {
        item["positive_coverage"]["fixture"]
        for item in audit["entries"]
        if item["positive_coverage"]["kind"].startswith("reused")
    }
    assert len(new_fixtures) == 6
    assert len(reused_fixtures) == 5


def test_tck_18_and_19_are_frozen_and_tck_110_is_current() -> None:
    frozen = release_record(TCK_1_8_RELEASE_ID)
    assert canonical_digest(frozen) == FROZEN_TCK_1_8_RECORD_DIGEST
    assert (
        release_snapshot_digest(TCK_1_8_RELEASE_ID)
        == FROZEN_TCK_1_8_REGISTRY_SNAPSHOT_DIGEST
    )
    assert file_digest(
        ROOT / "conformance/evidence/evidence_runner_bundle_v1_8.json"
    ) == FROZEN_TCK_1_8_BUNDLE_MANIFEST_DIGEST
    assert frozen["runner_bundle"]["digest"] == FROZEN_TCK_1_8_RUNNER_BUNDLE_DIGEST
    assert (
        frozen["report_schema"]["content_digest"]
        == FROZEN_TCK_1_8_REPORT_SCHEMA_DIGEST
    )
    assert (
        frozen["target_registry"]["content_digest"]
        == FROZEN_TCK_1_8_TARGET_REGISTRY_DIGEST
    )
    assert (
        frozen["target_registry"]["schema_digest"]
        == FROZEN_TCK_1_8_TARGET_REGISTRY_SCHEMA_DIGEST
    )
    assert {
        item["target_key"]: item["target_catalog"]["content_digest"]
        for item in frozen["targets"]
    } == FROZEN_TCK_1_8_TARGET_CATALOG_DIGESTS
    assert file_digest(
        ROOT / "conformance/evidence/live_bindings/live_binding_trace_v4.schema.json"
    ) == FROZEN_TCK_1_8_LIVE_TRACE_SCHEMA_DIGEST
    assert file_digest(
        ROOT / "conformance/evidence/live_bindings/live_public_scenario_v1.schema.json"
    ) == FROZEN_TCK_1_8_PUBLIC_SCENARIO_SCHEMA_DIGEST

    frozen_19 = release_record(TCK_1_9_RELEASE_ID)
    assert canonical_digest(frozen_19) == FROZEN_TCK_1_9_RECORD_DIGEST
    assert (
        release_snapshot_digest(TCK_1_9_RELEASE_ID)
        == FROZEN_TCK_1_9_REGISTRY_SNAPSHOT_DIGEST
    )
    assert file_digest(
        ROOT / "conformance/evidence/evidence_runner_bundle_v1_9.json"
    ) == FROZEN_TCK_1_9_BUNDLE_MANIFEST_DIGEST
    assert frozen_19["runner_bundle"]["digest"] == FROZEN_TCK_1_9_RUNNER_BUNDLE_DIGEST
    assert frozen_19["report_schema"]["content_digest"] == FROZEN_TCK_1_9_REPORT_SCHEMA_DIGEST
    assert frozen_19["target_registry"]["content_digest"] == FROZEN_TCK_1_9_TARGET_REGISTRY_DIGEST
    assert frozen_19["target_registry"]["schema_digest"] == FROZEN_TCK_1_9_TARGET_REGISTRY_SCHEMA_DIGEST
    assert {
        item["target_key"]: item["target_catalog"]["content_digest"]
        for item in frozen_19["targets"]
    } == FROZEN_TCK_1_9_TARGET_CATALOG_DIGESTS

    current = release_record(CURRENT_TCK_RELEASE_ID)
    assert CURRENT_TCK_RELEASE_ID == "AICP-EVIDENCE-TCK-1.11.0"
    assert BUNDLE_MANIFEST_PATH.name == "evidence_runner_bundle_v1_11.json"
    assert current["report_schema"]["path"].endswith(
        "external_evidence_report_v2_2.schema.json"
    )
    assert [item["target_key"] for item in current["targets"]] == list(
        EXPECTED_TARGET_KEYS
    )
    assert validate_release_registry() == []
    assert release_policy(TCK_RELEASE_ID)["strong_eligible"] is True
    assert release_policy(TCK_1_4_RELEASE_ID)["strong_eligible"] is True
    assert release_policy(TCK_1_8_RELEASE_ID)["strong_eligible"] is True
    assert release_policy(TCK_1_9_RELEASE_ID)["strong_eligible"] is False
    assert release_policy(TCK_1_10_RELEASE_ID)["strong_eligible"] is True
    assert release_policy(CURRENT_TCK_RELEASE_ID)["strong_eligible"] is True


def test_tier1_catalogs_include_current_required_consumer_cases() -> None:
    expected = {
        "mediated_blocking_target.json": 30,
        "resumable_sessions_target.json": 20,
        "delegated_identity_target.json": 32,
    }
    for name, count in expected.items():
        catalog = json.loads(
            (ROOT / "conformance/evidence" / name).read_text(encoding="utf-8")
        )
        assert len(catalog["consumer_cases"]) == count
    targets = json.loads(
        (ROOT / "conformance/evidence/targets.json").read_text(encoding="utf-8")
    )
    assert len(targets["targets"]) == 6
    assert {item["target_key"] for item in targets["targets"]} == set(
        EXPECTED_TARGET_KEYS
    )


def test_exact_historical_tck_18_report_bytes_remain_eligible() -> None:
    path = (
        ROOT
        / "conformance/evidence/historical_reports/AICP-EVIDENCE-TCK-1.8.0-session-state-projection.json"
    )
    assert file_digest(path) == (
        "sha256:8569bd2f403740a785ee6963f8aa8d6e507f5a11c0b8044c62cdf8021344b6d1"
    )
    report = json.loads(path.read_text(encoding="utf-8"))
    evaluation = evaluate_report(
        report,
        expected_implementation_id="fictional-projection-v1-test-adapter",
        expected_implementation_version="1.0.0-test",
    )
    assert evaluation["status"] == "eligible", evaluation
