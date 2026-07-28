from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUNNER_DIR = ROOT / "conformance/runner"
if str(RUNNER_DIR) not in sys.path:
    sys.path.insert(0, str(RUNNER_DIR))
V02_RUNNER_DIR = ROOT / "conformance/core_v02_runner"
if str(V02_RUNNER_DIR) not in sys.path:
    sys.path.insert(0, str(V02_RUNNER_DIR))

from aicp_ref_v02.contract_agreement import (  # noqa: E402
    build_acceptance_binding,
    build_proposal_binding,
    compute_contract_hash,
    reduce_transcript,
    semantic_issue_ids,
    validate_contract_reference,
)
from aicp_ref.jcs import canonicalize_json  # noqa: E402
from aicp_conformance_runner import run_suite as run_v01_suite  # noqa: E402
from aicp_profile_runner import run_profile as run_v01_profile  # noqa: E402
from aicp_core_v02_runner import run_suite as run_v02_suite  # noqa: E402
from aicp_core_v02_profile_runner import run_profile as run_v02_profile  # noqa: E402


FROZEN_V01_SHA256 = {
    "docs/core/AICP_Core_v0.1_Normative.md": "40fb99cf5960c53879833e6b4b1299c5c195dcb2e06e2f63921fe2c498a8ab2e",
    "schemas/core/aicp-core-message.schema.json": "96c2ed0ed86a89d1d3517b21f4bf2cf9db4d5e2caf0b1647169526a863830f9d",
    "schemas/core/aicp-core-payloads.schema.json": "596add0a32fae283a1cd5322ed5ed5604f99a633bf4b2196854f19441e327f3c",
    "schemas/core/aicp-core-contract.schema.json": "3643765f7412fa237255a83ed3581a82c1a1862272267ce090acb727dfd518d6",
    "conformance/core/CT_CORE_0.1.json": "439ba0cc2f077a36d4fd866568bc727a066435b0bd711640a0bb572fb0393264",
    "conformance/profiles/PF_AICP_BASE_0.1.json": "1a641ccc0eb2dfde04aeee0db83331659e5173e15107b5db0ab61754b77bd7a5",
    "conformance/profiles/PF_AICP_AUTHENTICATED_BASE_0.1.json": "d4c0645d76e850c13aa6c382ee32c9f2f1d0fde29c409f460e90414cb40a2b63",
    "conformance/iut/tck_releases.json": "f41e319667a6f9a537eeed993a950621bd7d45ac37bcd8a1aac76044e9bf7b2e",
    "conformance/runner/_runner_state_projection_checks.py": "aaa60e7e28af33de11651f17cc86a129ca766c44ae042b06d929523413bccf54",
    "conformance/extensions/OR_SESSION_STATE_PROJECTION_V1.json": "42f6dd6b525ea54a183377e9b4393b85f1a455c88740f0bf23cda4d94d4de691",
    "conformance/extensions/CN_CAPNEG_0.1.json": "4023cefe55342461c4f36b5298adf375512f85e8db3bf771ea571a5628f23d00",
    "schemas/extensions/ext-capneg-payloads.schema.json": "ef31d4bf02fece06e062bf0f52db49c70d9a38ed1e6133ef45c2da2f9659d58e",
    "dropins/aicp-core/python/generate_minimal_core_transcript.py": "25c20ec2a9f3cf89996ad754a315c6b5ecfaaf8f5a7b1388f766496ffed16d02",
    "dropins/aicp-core/typescript/scripts/generate_minimal_core_transcript.mjs": "87e240d6df908e1b0f93de3947a1d813d39f710abd902e24dfff0933c7304d2d",
    "fixtures/golden_transcripts/GT-01_happy_path_signed.jsonl": "7e4761bf4253f56f826b41120c178c28e4a2abc0f90bd1d6b2dfd78cfa607a59",
    "fixtures/golden_transcripts/GT-02_conflict_choose_signed.jsonl": "f58f028beb7ee6ce12383ba84154cc580b125aec8779cf04d85f74118c2f2e64",
    "fixtures/golden_transcripts/GT-04_consent_required_and_grant.jsonl": "01d01dadc96a8bc07f0bf189a7d62168e6eec3c52381dadb434cc46161d44e3a",
    "fixtures/golden_transcripts/GT-05_consent_revoke.jsonl": "1f9a4095b64685be1dd2f4a3213cd645f63635d819e7f91bf092c0e424ae0462",
    "fixtures/golden_transcripts/GT-06_unknown_base_and_resync.jsonl": "33050d08659218875a04ad5fbf7e96a1f6270ec994e84a52f89d79bccc978cb0",
    "fixtures/golden_transcripts/GT-07_invalid_signature_reject.jsonl": "04f198913e971293d53b9e20360c596ec100ff72541640af330369b80ff1d0dd",
    "fixtures/golden_transcripts/GT-08_error_minimal.jsonl": "ea09ff71c0bc688870bbb8ba12d7fb27e3cc6d6248b42cc79b69c8e6b4547eed",
    "fixtures/golden_transcripts/GT-08_replay_duplicate_message_id.jsonl": "485b0e5b562bce529a4b41668f0706361646b29f3b0e0bd9fe9545b1e2c357d2",
    "fixtures/golden_transcripts/GT-09_missing_prev_msg_hash_expected_fail.jsonl": "50b3db2d9489d799e0cdd2a9e9fa9e247c1fd5d79c5808957b9506aec4bae27d",
    "fixtures/golden_transcripts/GT-11_empty_contract_id_expected_fail.jsonl": "502689d124465a11dd20d7e42ef41b33ca438ba11e0ff47655c9b40b773127cb",
}


def _load_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _load_jsonl(path: str) -> list[dict]:
    return [
        json.loads(line)
        for line in (ROOT / path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_core_v02_suite_has_exact_fixture_totals_and_marks() -> None:
    suite_path = ROOT / "conformance/core/CT_CORE_0.2.json"
    suite = _load_json("conformance/core/CT_CORE_0.2.json")
    positives = [item for item in suite["transcripts"] if item.get("expect_pass", True)]
    negatives = [item for item in suite["transcripts"] if not item.get("expect_pass", True)]
    assert len(positives) == 8
    assert len(negatives) == 30

    report = run_v02_suite(suite_path)
    assert report["passed"] is True
    assert report["failures"] == []
    assert report["degraded"] is False
    assert report["compatibility_marks"] == ["AICP-Core-0.2"]


def test_base_v02_profile_has_only_internal_core_and_profile_marks() -> None:
    report = run_v02_profile(ROOT / "conformance/profiles/PF_AICP_BASE_0.2.json")
    assert report["aicp_version"] == "0.2"
    assert report["passed"] is True
    assert report["compatibility_marks"] == [
        "AICP-Profile-BASE-0.2",
        "AICP-Core-0.2",
    ]


def test_cross_language_vectors_cover_all_state_transitions_and_failures() -> None:
    vectors = _load_json(
        "fixtures/core_v0_2/exact_contract_agreement/cross_language_vectors.json"
    )
    assert canonicalize_json(vectors["contract"]) == vectors["canonical_json"]
    assert compute_contract_hash(vectors["contract"]) == vectors["contract_hash"]
    assert validate_contract_reference(vectors["contract_ref"]) == []

    for vector in vectors["positive"]:
        state = reduce_transcript(_load_jsonl(vector["path"]))
        assert state.issues == [], vector["path"]
        assert state.state == vector["expected_state"], vector["path"]
        assert state.active_head == vector["expected_active_head"], vector["path"]

    for vector in vectors["negative"]:
        assert semantic_issue_ids(_load_jsonl(vector["path"])) == vector[
            "expected_semantic_issue_ids"
        ], vector["path"]


def test_binding_helpers_use_existing_contract_hash_domain() -> None:
    vector = _load_json("fixtures/core_tv.json")["TV-01"]
    assert vector["object_type"] == "contract"
    assert compute_contract_hash(vector["object"]) == vector["object_hash"]

    contract = {
        "contract_id": "opaque-version-contract",
        "contract_version": "release-blue",
        "goal": "No numeric ordering",
        "roles": ["a", "b"],
    }
    proposal = build_proposal_binding(contract)
    assert proposal["contract_ref"]["head"]["version"] == "release-blue"
    assert "base" not in proposal["contract_ref"]

    message = {
        "message_type": "CONTRACT_PROPOSE",
        "message_id": "proposal-1",
        "message_hash": "sha256:" + ("A" * 43),
        "payload": {"contract_hash": proposal["contract_hash"]},
    }
    acceptance = build_acceptance_binding(message, accepted=True)
    assert acceptance == {
        "accepted": True,
        "proposal_message_id": "proposal-1",
        "proposal_message_hash": "sha256:" + ("A" * 43),
        "contract_hash": proposal["contract_hash"],
    }


def test_invalid_conflict_does_not_advance_the_active_head() -> None:
    messages = _load_jsonl(
        "fixtures/core_v0_2/exact_contract_agreement/negative/"
        "25_duplicate_candidate_expected_fail.jsonl"
    )
    state = reduce_transcript(messages)
    initial_proposal = messages[0]
    assert state.active_head == {
        "branch_id": "main",
        "head": initial_proposal["contract_ref"]["head"],
    }
    assert state.selected_conflict_result is None


def test_core_v01_frozen_bytes_and_golden_transcripts_are_unchanged() -> None:
    for relative, expected in FROZEN_V01_SHA256.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected


def test_external_iut_surface_and_tck_releases_are_unchanged() -> None:
    files = sorted(
        path
        for path in (ROOT / "conformance/iut").rglob("*")
        if path.is_file()
        and not path.name.startswith("report_")
        and "__pycache__" not in path.parts
    )
    digest = hashlib.sha256()
    for path in files:
        digest.update(f"{path.relative_to(ROOT).as_posix()}\0".encode())
        digest.update(path.read_bytes())
    assert len(files) == 10
    assert (
        digest.hexdigest()
        == "bfc516081cd17fa7e4f77b748585409467588c98fb72d45d4a22c4bd1cbf6e33"
    )

    registry = _load_json("conformance/iut/tck_releases.json")
    assert [item["release_id"] for item in registry["releases"]] == [
        "AICP-IUT-TCK-1.0.0",
        "AICP-IUT-TCK-1.1.0",
    ]
    cases = _load_json("conformance/iut/cases.json")
    assert set(cases["profiles"]) == {
        "AICP-BASE@0.1",
        "AICP-AUTHENTICATED-BASE@0.1",
    }


def test_v01_legacy_reports_and_marks_remain_unchanged() -> None:
    suite_report = run_v01_suite(ROOT / "conformance/core/CT_CORE_0.1.json")
    assert set(suite_report) == {
        "aicp_version",
        "suite_id",
        "suite_version",
        "timestamp",
        "passed",
        "failures",
        "compatibility_marks",
        "degraded",
        "degraded_reasons",
        "skipped_checks",
    }
    assert suite_report["compatibility_marks"] == ["AICP-Core-0.1"]

    profile_report = run_v01_profile(
        ROOT / "conformance/profiles/PF_AICP_BASE_0.1.json"
    )
    assert profile_report["compatibility_marks"] == [
        "AICP-Profile-BASE-0.1",
        "AICP-Core-0.1",
    ]


def test_registry_has_no_authenticated_base_v02_or_external_iut_target() -> None:
    profiles = _load_json("registry/aicp_profiles.json")
    ids = {item["id"] for item in profiles}
    assert "AICP-BASE@0.2" in ids
    assert "AICP-AUTHENTICATED-BASE@0.2" not in ids

    cases = _load_json("conformance/iut/cases.json")
    assert "AICP-BASE@0.2" not in cases["profiles"]
