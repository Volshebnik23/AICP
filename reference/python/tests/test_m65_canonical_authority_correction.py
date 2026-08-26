from __future__ import annotations

import base64
import copy
import json
import subprocess
import sys
from pathlib import Path
from typing import Callable

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


ROOT = Path(__file__).resolve().parents[3]
RUNNER_DIR = ROOT / "conformance/runner"
EVIDENCE_DIR = ROOT / "conformance/evidence"
for path in (RUNNER_DIR, EVIDENCE_DIR, ROOT / "reference/python", ROOT / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import aicp_batch_runner  # noqa: E402
import aicp_profile_runner  # noqa: E402
from aicp_conformance_runner import run_suite  # noqa: E402
from aicp_ref.hashing import message_hash_from_body  # noqa: E402
from profile_transcript_evaluator import evaluate_profile_transcript  # noqa: E402
from validate_message_surface_completion import completion_errors  # noqa: E402


Transform = Callable[[list[dict]], None]
HASH_FAILURES = {
    "CT-MESSAGE-HASH-01",
    "CT-HASH-CHAIN-01",
    "CT-SIGNATURE-HASH-01",
    "CT-SIGNATURE-VERIFY-01",
}
M65_POSITIVE_SUITES = (
    "conformance/extensions/FA_FACILITATION_0.1.json",
    "conformance/extensions/ID_IDENTITY_LC_0.1.json",
    "conformance/extensions/DS_DISPUTES_0.1.json",
    "conformance/extensions/MP_MARKETPLACE_0.1.json",
    "conformance/extensions/DL_DELEGATION_0.1.json",
    "conformance/extensions/PA_PARTICIPANTS_0.1.json",
    "conformance/extensions/PE_POLICY_EVAL_0.1.json",
    "conformance/extensions/RP_RESPONSIBILITY_0.1.json",
    "conformance/extensions/EX_EXECUTION_LIFECYCLE_0.1.json",
    "conformance/extensions/DI_DELEGATED_IDENTITY_0.1.json",
)
REMOVED_NON_NORMATIVE_CHECKS = {
    "ID-MIGRATE-01",
    "DS-ARBITRATION-01",
    "DL-REVOKE-01",
    "PE-ATTEST-01",
}


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


def _messages(relative: str | Path) -> list[dict]:
    path = Path(relative)
    if not path.is_absolute():
        path = ROOT / path
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _write_case(
    tmp_path: Path,
    suite_relative: str,
    fixture_relative: str,
    transform: Transform,
) -> Path:
    suite = json.loads((ROOT / suite_relative).read_text(encoding="utf-8"))
    messages = _messages(fixture_relative)
    transform(messages)
    _rehash_and_resign(messages)

    fixture = tmp_path / "case.jsonl"
    fixture.write_text(
        "\n".join(json.dumps(message, separators=(",", ":")) for message in messages)
        + "\n",
        encoding="utf-8",
    )
    suite["transcripts"] = [
        {
            "id": "M65-CORRECTION",
            "path": fixture.as_posix(),
            "expected_message_types": [message["message_type"] for message in messages],
        }
    ]
    suite_path = tmp_path / "suite.json"
    suite_path.write_text(json.dumps(suite, indent=2) + "\n", encoding="utf-8")
    return suite_path


def _set_payload(message_type: str, field: str, value: object) -> Transform:
    def apply(messages: list[dict]) -> None:
        target = next(item for item in messages if item["message_type"] == message_type)
        target["payload"][field] = value

    return apply


def _assert_only_semantic_failure(report: dict, expected_check: str) -> None:
    observed = {failure["test_id"] for failure in report["failures"]}
    assert expected_check in observed
    assert not (observed & HASH_FAILURES), report["failures"]
    assert report["passed"] is False
    assert report["compatibility_marks"] == []


def _migration_external_aid(messages: list[dict]) -> None:
    migration = next(
        message for message in messages if message["message_type"] == "AGENT_MIGRATION"
    )
    migration["payload"]["aid_hash"] = "sha256:" + "0" * 64


def _arbitration_external_state(messages: list[dict]) -> None:
    request = next(
        message for message in messages if message["message_type"] == "ARBITRATION_REQUEST"
    )
    result = next(
        message for message in messages if message["message_type"] == "ARBITRATION_RESULT"
    )
    request["payload"]["related_challenge_id"] = "CH-EXTERNAL"
    result["payload"]["arbitration_id"] = "ARB-EXTERNAL"


def _standalone_leave(messages: list[dict]) -> None:
    leave = next(
        copy.deepcopy(message)
        for message in messages
        if message["message_type"] == "PARTICIPANT_LEAVE"
    )
    leave["sender"] = "user:external"
    leave["payload"]["participant_id"] = "user:persisted"
    messages[:] = [leave]


def _standalone_binding_revoke(messages: list[dict]) -> None:
    messages[:] = [
        message
        for message in messages
        if message["message_type"] != "SUBJECT_BINDING_ISSUE"
    ]


def _bid_update_withdraw_external_bid(messages: list[dict]) -> None:
    messages[:] = [
        message
        for message in messages
        if message["message_type"] in {"RFW_POST", "BID_UPDATE", "BID_WITHDRAW"}
    ]


NON_OVERREACH_CASES = (
    (
        "identity migration with externally known AID",
        "conformance/extensions/ID_IDENTITY_LC_0.1.json",
        "fixtures/extensions/identity_lc/IL-04_agent_migration_presence.jsonl",
        _migration_external_aid,
    ),
    (
        "key revoke with externally known key",
        "conformance/extensions/ID_IDENTITY_LC_0.1.json",
        "fixtures/extensions/identity_lc/IL-05_valid_key_revoke_pass.jsonl",
        _set_payload("KEY_REVOKE", "target_kid", "EXTERNAL-KID"),
    ),
    (
        "arbitration with external challenge and request state",
        "conformance/extensions/DS_DISPUTES_0.1.json",
        "fixtures/extensions/disputes/DS-04_claim_and_arbitration_pass.jsonl",
        _arbitration_external_state,
    ),
    (
        "delegation revoke with externally known grant",
        "conformance/extensions/DL_DELEGATION_0.1.json",
        "fixtures/extensions/delegation/DL-04_delegation_revoke_presence.jsonl",
        _set_payload("DELEGATION_REVOKE", "delegation_id", "D-EXTERNAL"),
    ),
    (
        "participant leave without local join or sender equality",
        "conformance/extensions/PA_PARTICIPANTS_0.1.json",
        "fixtures/extensions/participants/PA-04_participant_leave_pass.jsonl",
        _standalone_leave,
    ),
    (
        "policy attestation without invented local binding",
        "conformance/extensions/PE_POLICY_EVAL_0.1.json",
        "fixtures/extensions/policy_eval/PE-05_policy_decision_attest_presence.jsonl",
        _set_payload(
            "POLICY_DECISION_ATTEST", "policy_decision_ref", "sha256:" + "0" * 64
        ),
    ),
    (
        "binding revoke with externally known issue",
        "conformance/extensions/DI_DELEGATED_IDENTITY_0.1.json",
        "fixtures/extensions/delegated_identity/DI-05_issue_and_revoke_binding_pass.jsonl",
        _standalone_binding_revoke,
    ),
    (
        "bid update and withdraw with external bid state",
        "conformance/extensions/MP_MARKETPLACE_0.1.json",
        "fixtures/extensions/marketplace/MP-10_bid_update_withdraw_award_decline_pass.jsonl",
        _bid_update_withdraw_external_bid,
    ),
)


@pytest.mark.parametrize(
    ("label", "suite", "fixture", "transform"),
    NON_OVERREACH_CASES,
    ids=[item[0] for item in NON_OVERREACH_CASES],
)
def test_current_01_conformance_does_not_invent_local_state_requirements(
    tmp_path: Path,
    label: str,
    suite: str,
    fixture: str,
    transform: Transform,
) -> None:
    del label
    report = run_suite(_write_case(tmp_path, suite, fixture, transform))
    assert report["passed"] is True, report["failures"]
    assert report["compatibility_marks"]


def _identity_use_after_revoke(messages: list[dict]) -> None:
    source = _messages(
        "fixtures/extensions/identity_lc/IL-03_revoke_then_use_revoked_key_expected_fail.jsonl"
    )[-1]
    amendment = copy.deepcopy(source)
    amendment.update(
        {
            "session_id": messages[0]["session_id"],
            "message_id": "m5",
            "timestamp": "2026-03-02T00:10:04Z",
            "contract_id": messages[0]["contract_id"],
        }
    )
    amendment["signatures"][0].update({"signer": "agent:Q", "kid": "Q1"})
    messages.append(amendment)


def _delegated_use_after_revoke(messages: list[dict]) -> None:
    action = copy.deepcopy(
        _messages(
            "fixtures/extensions/delegated_identity/DI-01_issue_and_use_binding_pass.jsonl"
        )[-1]
    )
    binding_hash = next(
        message["payload"]["binding_hash"]
        for message in messages
        if message["message_type"] == "SUBJECT_BINDING_REVOKE"
    )
    action.update(
        {
            "session_id": messages[0]["session_id"],
            "message_id": "m7",
            "timestamp": "2026-03-01T00:00:07Z",
            "contract_id": messages[0]["contract_id"],
        }
    )
    action["ext"]["subject_binding_hash"] = binding_hash
    messages.append(action)


def _participant_traffic_after_leave(messages: list[dict]) -> None:
    messages.append(
        {
            "session_id": messages[0]["session_id"],
            "message_id": "m6",
            "timestamp": "2026-03-21T10:00:05Z",
            "sender": "user:U",
            "message_type": "CONTENT_MESSAGE",
            "contract_id": messages[0]["contract_id"],
            "payload": {
                "content": "must be rejected after leave",
                "content_format": "text/plain",
            },
        }
    )


NORMATIVE_MUTATIONS = (
    (
        "marketplace wrong prior RFW",
        "conformance/extensions/MP_MARKETPLACE_0.1.json",
        "fixtures/extensions/marketplace/MP-10_bid_update_withdraw_award_decline_pass.jsonl",
        _set_payload("BID_UPDATE", "rfw_id", "rfw-unknown"),
        "MP-BID-01",
    ),
    (
        "marketplace decline unknown award",
        "conformance/extensions/MP_MARKETPLACE_0.1.json",
        "fixtures/extensions/marketplace/MP-10_bid_update_withdraw_award_decline_pass.jsonl",
        _set_payload("AWARD_DECLINE", "award_id", "award-unknown"),
        "MP-AWARD-01",
    ),
    (
        "identity post-revocation key reuse",
        "conformance/extensions/ID_IDENTITY_LC_0.1.json",
        "fixtures/extensions/identity_lc/IL-05_valid_key_revoke_pass.jsonl",
        _identity_use_after_revoke,
        "ID-REVOKE-01",
    ),
    (
        "delegated identity use after revocation",
        "conformance/extensions/DI_DELEGATED_IDENTITY_0.1.json",
        "fixtures/extensions/delegated_identity/DI-05_issue_and_revoke_binding_pass.jsonl",
        _delegated_use_after_revoke,
        "DI-REVOKE-01",
    ),
    (
        "participant traffic after leave",
        "conformance/extensions/PA_PARTICIPANTS_0.1.json",
        "fixtures/extensions/participants/PA-04_participant_leave_pass.jsonl",
        _participant_traffic_after_leave,
        "PA-MEM-01",
    ),
    (
        "execution cancel unknown run",
        "conformance/extensions/EX_EXECUTION_LIFECYCLE_0.1.json",
        "fixtures/extensions/execution_lifecycle/EX-08_active_run_cancel_pass.jsonl",
        _set_payload("RUN_CANCEL", "run_id", "run-unknown"),
        "EX-RUN-REF-01",
    ),
    (
        "responsibility revoke unknown transfer",
        "conformance/extensions/RP_RESPONSIBILITY_0.1.json",
        "fixtures/extensions/responsibility/RP-06_assign_revoke_pass.jsonl",
        _set_payload("RESPONSIBILITY_REVOKE", "transfer_id", "t-unknown"),
        "RS-ACCEPT-01",
    ),
    (
        "disputes unresolved evidence",
        "conformance/extensions/DS_DISPUTES_0.1.json",
        "fixtures/extensions/disputes/DS-04_claim_and_arbitration_pass.jsonl",
        _set_payload("CHALLENGE_ASSERTION", "evidence_refs", ["msgid:unknown"]),
        "DS-EVIDENCE-RESOLVE-01",
    ),
)


@pytest.mark.parametrize(
    ("label", "suite", "fixture", "transform", "expected_check"),
    NORMATIVE_MUTATIONS,
    ids=[item[0] for item in NORMATIVE_MUTATIONS],
)
def test_normative_mutations_fail_directly_in_canonical_runner(
    tmp_path: Path,
    label: str,
    suite: str,
    fixture: str,
    transform: Transform,
    expected_check: str,
) -> None:
    del label
    report = run_suite(_write_case(tmp_path, suite, fixture, transform))
    _assert_only_semantic_failure(report, expected_check)


def _marketplace_failure_suite(tmp_path: Path) -> Path:
    return _write_case(
        tmp_path,
        "conformance/extensions/MP_MARKETPLACE_0.1.json",
        "fixtures/extensions/marketplace/MP-10_bid_update_withdraw_award_decline_pass.jsonl",
        _set_payload("BID_UPDATE", "rfw_id", "rfw-unknown"),
    )


def test_batch_runner_report_suppresses_mark_before_any_followup_validator(
    tmp_path: Path,
) -> None:
    suite_path = _marketplace_failure_suite(tmp_path)
    report_path = tmp_path / "batch-report.json"

    exit_code = aicp_batch_runner.run_batch(
        [f"{suite_path.as_posix()}::{report_path.as_posix()}"], []
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert exit_code == 1
    _assert_only_semantic_failure(report, "MP-BID-01")


def test_batch_cli_writes_truthful_failure_report_without_second_process(
    tmp_path: Path,
) -> None:
    suite_path = _marketplace_failure_suite(tmp_path)
    report_path = tmp_path / "cli-report.json"
    result = subprocess.run(
        [
            sys.executable,
            str(ROOT / "conformance/runner/aicp_batch_runner.py"),
            "--suite-out",
            f"{suite_path.as_posix()}::{report_path.as_posix()}",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    report = json.loads(report_path.read_text(encoding="utf-8"))

    assert result.returncode == 1
    _assert_only_semantic_failure(report, "MP-BID-01")


def test_profile_runner_suppresses_profile_and_suite_marks(
    tmp_path: Path,
) -> None:
    suite_path = _marketplace_failure_suite(tmp_path)
    profile_path = tmp_path / "profile.json"
    profile_path.write_text(
        json.dumps(
            {
                "profile_id": "M65-CANONICAL-AUTHORITY",
                "profile_version": "0.1",
                "aicp_version": "0.1",
                "required_suites": [suite_path.as_posix()],
                "compatibility_mark": "AICP-PROFILE-M65-TEST-ONLY",
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    report = aicp_profile_runner.run_profile(profile_path)

    assert report["passed"] is False
    assert report["compatibility_marks"] == []
    assert report["suite_reports"][0]["compatibility_marks"] == []
    assert {failure["test_id"] for failure in report["failures"]} >= {"MP-BID-01"}


def test_one_canonical_compatibility_authority_remains() -> None:
    assert aicp_batch_runner.run_suite is run_suite
    assert aicp_profile_runner.run_suite is run_suite
    assert not (ROOT / "scripts/m65_extension_semantics.py").exists()
    assert not (ROOT / "scripts/validate_m65_extension_semantics.py").exists()
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "m65_extension_semantics" not in makefile
    assert "validate_m65_extension_semantics" not in makefile


def test_removed_non_normative_checks_are_not_declared() -> None:
    declared: set[str] = set()
    for relative in M65_POSITIVE_SUITES:
        suite = json.loads((ROOT / relative).read_text(encoding="utf-8"))
        declared.update(
            check["test_id"]
            for check in suite["checks"]
            if isinstance(check, dict) and isinstance(check.get("test_id"), str)
        )
    assert not (declared & REMOVED_NON_NORMATIVE_CHECKS)


def test_all_m65_positive_suites_pass_canonical_runner() -> None:
    reports = [run_suite(ROOT / relative) for relative in M65_POSITIVE_SUITES]
    assert all(report["passed"] for report in reports), [
        report["failures"] for report in reports if not report["passed"]
    ]
    assert completion_errors(ROOT) == []


@pytest.mark.parametrize(
    ("suite", "fixture", "transform"),
    [
        (
            "conformance/extensions/ID_IDENTITY_LC_0.1.json",
            "fixtures/extensions/identity_lc/IL-04_agent_migration_presence.jsonl",
            _migration_external_aid,
        ),
        (
            "conformance/extensions/PE_POLICY_EVAL_0.1.json",
            "fixtures/extensions/policy_eval/PE-05_policy_decision_attest_presence.jsonl",
            _set_payload(
                "POLICY_DECISION_ATTEST",
                "policy_decision_ref",
                "sha256:" + "0" * 64,
            ),
        ),
        (
            "conformance/extensions/DI_DELEGATED_IDENTITY_0.1.json",
            "fixtures/extensions/delegated_identity/DI-05_issue_and_revoke_binding_pass.jsonl",
            _standalone_binding_revoke,
        ),
    ],
)
def test_tier1_ordinary_and_evidence_semantics_accept_same_boundary_case(
    tmp_path: Path,
    suite: str,
    fixture: str,
    transform: Transform,
) -> None:
    suite_path = _write_case(tmp_path, suite, fixture, transform)
    messages = _messages(tmp_path / "case.jsonl")

    ordinary = run_suite(suite_path)
    evidence = evaluate_profile_transcript(messages, [suite_path.as_posix()])

    assert ordinary["passed"] is True, ordinary["failures"]
    assert evidence.accepted is True, evidence.errors


@pytest.mark.parametrize(
    ("suite", "fixture", "transform", "expected_check"),
    [
        (
            "conformance/extensions/ID_IDENTITY_LC_0.1.json",
            "fixtures/extensions/identity_lc/IL-05_valid_key_revoke_pass.jsonl",
            _identity_use_after_revoke,
            "ID-REVOKE-01",
        ),
        (
            "conformance/extensions/PE_POLICY_EVAL_0.1.json",
            "fixtures/extensions/policy_eval/PE-05_policy_decision_attest_presence.jsonl",
            _set_payload(
                "POLICY_EVAL_REQUEST",
                "evaluation_context",
                {
                    "context_id": "ctx-pe5",
                    "contract_head_version": "v1",
                    "subject": "agent:A",
                    "action": "content.publish",
                    "resource": "content:5",
                    "context_hash": "sha256:" + "0" * 64,
                },
            ),
            "PE-CONTEXT-HASH-01",
        ),
        (
            "conformance/extensions/DI_DELEGATED_IDENTITY_0.1.json",
            "fixtures/extensions/delegated_identity/DI-05_issue_and_revoke_binding_pass.jsonl",
            _delegated_use_after_revoke,
            "DI-REVOKE-01",
        ),
    ],
)
def test_tier1_ordinary_and_evidence_semantics_reject_same_normative_violation(
    tmp_path: Path,
    suite: str,
    fixture: str,
    transform: Transform,
    expected_check: str,
) -> None:
    suite_path = _write_case(tmp_path, suite, fixture, transform)
    messages = _messages(tmp_path / "case.jsonl")

    ordinary = run_suite(suite_path)
    evidence = evaluate_profile_transcript(messages, [suite_path.as_posix()])

    assert ordinary["passed"] is False
    assert expected_check in {item["test_id"] for item in ordinary["failures"]}
    assert evidence.accepted is False
    assert expected_check in {item["code"] for item in evidence.errors}
