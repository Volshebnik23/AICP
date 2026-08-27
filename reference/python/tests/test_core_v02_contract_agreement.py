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
    "docs/core/AICP_Core_v0.1_Normative.md": "42d0bdd138e53c83d6a39679f38ab5bcf8fc7e89225b082a83eff20ec4fb90ab",
    "schemas/core/aicp-core-message.schema.json": "55fcf0b9e32028deaea132787aa4237fd5e941c5fecf9b5d03f9dbaf8731716c",
    "schemas/core/aicp-core-payloads.schema.json": "55c119e338fd06abc9d00ed16fa6f7aea3e92fa75ca6b302a08c7f5d509076d5",
    "schemas/core/aicp-core-contract.schema.json": "68cdae7d538706b8297634b48ec50c7f20edb9b2296f8c013eb4cdd950accbc7",
    "conformance/core/CT_CORE_0.1.json": "51272d58c2f284db18a8b8b2a4c7b3bc616ae597b0e6286e39a696d1a316816a",
    "conformance/profiles/PF_AICP_BASE_0.1.json": "3a0a68426ff468e6d674fcd87b4449437f28f3d03d5660de92021ac8caf99938",
    "conformance/profiles/PF_AICP_AUTHENTICATED_BASE_0.1.json": "1bb2ed7493f7cd2bc5356a27ed7222e9747af119d1f8c7df569bf3e54f909152",
    "conformance/iut/tck_releases.json": "f89c7dc476041f79558157bb6d0178d7b43158913a2dbe5ee0191d017903a25e",
    "conformance/runner/_runner_state_projection_checks.py": "8f8baa773766e590d5f9491d880a6b15f662ae911d8a2a306185a7e36b178c8b",
    "conformance/extensions/OR_SESSION_STATE_PROJECTION_V1.json": "9efd654774ff514cd55c30c19f94e46cdff16ee8e85dda7108637ef24b52e1a8",
    "schemas/extensions/ext-capneg-payloads.schema.json": "a686222de7b00695d54080e4daa015a85dda888ffd91c7e82b834467d2120598",
    "dropins/aicp-core/python/generate_minimal_core_transcript.py": "73edf9101cc7288d698152acb16a166e08ef831084684fbccd47e60101cc24c2",
    "dropins/aicp-core/typescript/scripts/generate_minimal_core_transcript.mjs": "704ced502aa9a36ba094a425dd3dd8af8e4480e572d28d1e67b4d55e19abc42b",
    "fixtures/golden_transcripts/GT-01_happy_path_signed.jsonl": "fd110495227b1636fccbd295b5b87be0b16d4a3776e9c1e0dd29ccacab5ad74d",
    "fixtures/golden_transcripts/GT-02_conflict_choose_signed.jsonl": "5e45840d7d38e8358034530f6746a62fa7189392741ad006836de475e6bcac30",
    "fixtures/golden_transcripts/GT-04_consent_required_and_grant.jsonl": "c51b9e98242bde50958a57662f46d7e8b554629023215ddc079581bdb2267c47",
    "fixtures/golden_transcripts/GT-05_consent_revoke.jsonl": "b3a17d98cbb8b19cf39833993c27a8f8bf92374775cd375c696c920b10c71333",
    "fixtures/golden_transcripts/GT-06_unknown_base_and_resync.jsonl": "6031ea69eb5c680cdaf434f0b92cf9f8838fb6855078ace938210f3b80c03b7b",
    "fixtures/golden_transcripts/GT-07_invalid_signature_reject.jsonl": "390a9ab376fc06ccf6e41b0dd4af06daabf40e4b33acc6903def5410eda36eff",
    "fixtures/golden_transcripts/GT-08_error_minimal.jsonl": "a90750ba0adcf7c48d288f0a74b59a7b32abcc752cbd6710053d410c252f55e7",
    "fixtures/golden_transcripts/GT-08_replay_duplicate_message_id.jsonl": "1d1c6b003945175836127e066eaa7200ab141fd4a98c032f7b757ecc7382c612",
    "fixtures/golden_transcripts/GT-09_missing_prev_msg_hash_expected_fail.jsonl": "22b33be97a56de1613f5d1cdd0f57aaaab792a483f742628af7a4297cedc91b4",
    "fixtures/golden_transcripts/GT-11_empty_contract_id_expected_fail.jsonl": "08983c7cd566d6140d546fc3a5e7a26ba870ec524fc91ec279a1dff6c0ef1d71",
}


def _load_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _load_jsonl(path: str) -> list[dict]:
    return [
        json.loads(line)
        for line in (ROOT / path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _normalized_text_bytes(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def test_core_v02_suite_has_exact_fixture_totals_and_marks() -> None:
    suite_path = ROOT / "conformance/core/CT_CORE_0.2.json"
    suite = _load_json("conformance/core/CT_CORE_0.2.json")
    positives = [item for item in suite["transcripts"] if item.get("expect_pass", True)]
    negatives = [item for item in suite["transcripts"] if not item.get("expect_pass", True)]
    assert len(positives) == 9
    assert len(negatives) == 41

    report = run_v02_suite(suite_path)
    assert report["passed"] is True
    assert report["failures"] == []
    assert report["degraded"] is False
    assert report["degraded_reasons"] == []
    assert report["skipped_checks"] == []
    assert report["compatibility_marks"] == ["AICP-Core-0.2"]


def test_base_v02_profile_has_only_internal_core_and_profile_marks() -> None:
    report = run_v02_profile(ROOT / "conformance/profiles/PF_AICP_BASE_0.2.json")
    assert report["aicp_version"] == "0.2"
    assert report["passed"] is True
    assert report["degraded"] is False
    assert report["degraded_reasons"] == []
    assert report["skipped_checks"] == []
    assert report["compatibility_marks"] == [
        "AICP-Profile-BASE-0.2",
        "AICP-Core-0.2",
    ]


def test_core_v02_suite_and_profile_report_shapes_expose_eligibility_truth() -> None:
    suite_report = run_v02_suite(
        ROOT / "conformance/core/CT_CORE_0.2.json"
    )
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
    profile_report = run_v02_profile(
        ROOT / "conformance/profiles/PF_AICP_BASE_0.2.json"
    )
    assert set(profile_report) == {
        "aicp_version",
        "profile_id",
        "profile_version",
        "timestamp",
        "passed",
        "suite_reports",
        "failures",
        "compatibility_marks",
        "degraded",
        "degraded_reasons",
        "skipped_checks",
    }


def test_cross_language_vectors_cover_all_state_transitions_and_failures() -> None:
    vectors = _load_json(
        "fixtures/core_v0_2/exact_contract_agreement/cross_language_vectors.json"
    )
    assert canonicalize_json(vectors["contract"]) == vectors["canonical_json"]
    assert compute_contract_hash(vectors["contract"]) == vectors["contract_hash"]
    assert validate_contract_reference(vectors["contract_ref"]) == []

    for vector in vectors["positive"]:
        state = reduce_transcript(
            _load_jsonl(vector["path"]),
            vector["invalid_message_indices"],
        )
        assert state.issues == [], vector["path"]
        assert state.state == vector["expected_state"], vector["path"]
        assert state.active_head == vector["expected_active_head"], vector["path"]
        assert sorted(state.proposals) == vector["expected_proposal_ids"], vector["path"]
        assert (
            state.selected_conflict_result
            == vector["expected_selected_conflict_result"]
        ), vector["path"]
        assert len(state.acceptance_tuples) == vector[
            "expected_accepted_tuple_count"
        ], vector["path"]
        assert len(state.rejected_tuples) == vector[
            "expected_rejected_tuple_count"
        ], vector["path"]

    for vector in vectors["negative"]:
        messages = _load_jsonl(vector["path"])
        invalid_indices = vector["invalid_message_indices"]
        assert semantic_issue_ids(messages, invalid_indices) == vector[
            "expected_semantic_issue_ids"
        ], vector["path"]
        state = reduce_transcript(messages, invalid_indices)
        assert state.state == vector["expected_state"], vector["path"]
        assert state.active_head == vector["expected_active_head"], vector["path"]
        assert sorted(state.proposals) == vector["expected_proposal_ids"], vector["path"]
        assert (
            state.selected_conflict_result
            == vector["expected_selected_conflict_result"]
        ), vector["path"]
        assert len(state.acceptance_tuples) == vector[
            "expected_accepted_tuple_count"
        ], vector["path"]
        assert len(state.rejected_tuples) == vector[
            "expected_rejected_tuple_count"
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


def test_runner_invalid_acceptance_index_cannot_activate_a_head() -> None:
    vectors = _load_json(
        "fixtures/core_v0_2/exact_contract_agreement/cross_language_vectors.json"
    )
    vector = next(
        item
        for item in vectors["negative"]
        if item["path"].endswith(
            "32_acceptance_invalid_message_hash_expected_fail.jsonl"
        )
    )
    state = reduce_transcript(
        _load_jsonl(vector["path"]),
        vector["invalid_message_indices"],
    )
    assert state.state == "CANDIDATE_PROPOSED"
    assert state.active_head is None
    assert len(state.acceptance_tuples) == 0


def test_core_v01_frozen_bytes_and_golden_transcripts_are_unchanged() -> None:
    for relative, expected in FROZEN_V01_SHA256.items():
        assert hashlib.sha256(_normalized_text_bytes(ROOT / relative)).hexdigest() == expected


def test_external_iut_surface_and_tck_releases_are_unchanged() -> None:
    files = sorted(
        (
            path
            for path in (ROOT / "conformance/iut").rglob("*")
            if path.is_file()
            and not path.name.startswith("report_")
            and "__pycache__" not in path.parts
        ),
        key=lambda path: path.relative_to(ROOT).as_posix(),
    )
    digest = hashlib.sha256()
    for path in files:
        digest.update(f"{path.relative_to(ROOT).as_posix()}\0".encode())
        digest.update(_normalized_text_bytes(path))
    assert len(files) == 10
    assert (
        digest.hexdigest()
        == "ae23ec3fa2069ee4535060e382b57250ec079a017e766e46dd70a01a60a6aa10"
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
