from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[3]
PAIRWISE = ROOT / "interop" / "pairwise"
VECTOR = PAIRWISE / "current_vectors" / "AICP-PAIRWISE-TCK-1.2.0"
for import_path in (PAIRWISE, ROOT / "scripts"):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from interop_submission_validation import (  # noqa: E402
    PAIRWISE_JOINT_EVIDENCE_ERROR,
    evaluate_strong_report_evidence,
)
from pairwise_process_v1_2 import (  # noqa: E402
    MAX_STDERR_BYTES,
    JsonLineProcess,
    ProcessBoundaryError,
    allowlisted_environment,
)
from pairwise_report_dispatcher import evaluate_pairwise_report  # noqa: E402


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture()
def pairwise_artifacts(tmp_path: Path) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for key, name in (
        ("a_profile", "a-profile.json"),
        ("a_binding", "a-binding.json"),
        ("b_profile", "b-profile.json"),
        ("b_binding", "b-binding.json"),
        ("joint", "joint.json"),
    ):
        target = tmp_path / name
        shutil.copy2(VECTOR / name, target)
        paths[key] = target
    return paths


def test_pairwise_cleanroom_joint_run_is_eligible(pairwise_artifacts: dict[str, Path]) -> None:
    result = evaluate_pairwise_report(_load(pairwise_artifacts["joint"]), base_dir=pairwise_artifacts["joint"].parent)
    assert result["status"] == "eligible"
    assert len(result["eligible_pairwise_relations"]) == 1
    assert result["eligible_marks"] == []


def _mutate(case: str, report: dict[str, Any]) -> None:
    run0, run1 = report["runs"]
    direction = run0["directions"][0]
    messages = direction["messages"]
    exchanges = direction["exchanges"]
    events = direction["client_events"]
    if case == "one_sided": run0["directions"].pop()
    elif case == "duplicate_direction": run0["directions"][1] = copy.deepcopy(direction)
    elif case == "unrelated_side_report": report["participants"][0]["profile_report"] = copy.deepcopy(report["participants"][1]["profile_report"])
    elif case == "same_id": report["participants"][1]["implementation_id"] = report["participants"][0]["implementation_id"]
    elif case == "same_digest": report["participants"][1]["implementation_digest"] = report["participants"][0]["implementation_digest"]
    elif case == "participant_digest": report["participants"][0]["implementation_digest"] = "sha256:" + "0" * 64
    elif case == "report_digest": report["participants"][0]["profile_report"]["content_digest"] = "sha256:" + "0" * 64
    elif case == "wrong_profile": report["target"]["profile_id"] = "AICP-BASE-WRONG"
    elif case == "wrong_binding": report["target"]["binding_id"] = "BIND-HTTP"
    elif case == "hardcoded_hash": messages[1]["message"]["prev_msg_hash"] = "sha256:" + "A" * 43
    elif case == "previous_hash": messages[2]["message"]["prev_msg_hash"] = messages[0]["message"]["message_hash"]
    elif case == "wrong_session": messages[1]["message"]["session_id"] = "wrong-session"
    elif case == "wrong_contract": messages[1]["message"]["contract_id"] = "wrong-contract"
    elif case == "cross_run_replay": run1["directions"][0]["messages"][0] = copy.deepcopy(messages[0])
    elif case == "malformed_jsonrpc": exchanges[0]["request"]["jsonrpc"] = "1.0"
    elif case == "forged_passed": report["passed"] = False
    elif case == "semantic_digest": run0["semantic_digest"] = "sha256:" + "0" * 64
    elif case == "report_type": report["report_type"] = "aicp.report"
    elif case == "release_id": report["pairwise_tck_release"]["release_id"] = "AICP-PAIRWISE-TCK-9.9.9"
    elif case == "release_digest": report["pairwise_tck_release"]["registry_digest"] = "sha256:" + "0" * 64
    elif case == "target_digest": report["target"]["target_catalog_digest"] = "sha256:" + "0" * 64
    elif case == "scenario_digest": report["scenario"]["scenario_catalog_digest"] = "sha256:" + "0" * 64
    elif case == "one_run": report["runs"].pop()
    elif case == "run_id_replay": run1["run_id"] = run0["run_id"]
    elif case == "challenge_replay": run1["directions"][0]["challenge"] = direction["challenge"]
    elif case == "session_replay": run1["directions"][0]["session_id"] = direction["session_id"]
    elif case == "contract_replay": run1["directions"][0]["contract_id"] = direction["contract_id"]
    elif case == "message_id_replay": run1["directions"][0]["messages"][0]["message"]["message_id"] = messages[0]["message"]["message_id"]
    elif case == "rpc_id_replay": run1["directions"][0]["exchanges"][0]["request"]["id"] = exchanges[0]["request"]["id"]
    elif case == "process_id_replay": run1["role_instances"][0]["client_process_instance_id"] = run0["role_instances"][0]["client_process_instance_id"]
    elif case == "swapped_role": messages[0]["constructed_by"] = direction["consumer_side"]
    elif case == "sender": messages[0]["message"]["sender"] = "attacker"
    elif case == "message_hash": messages[0]["message"]["message_hash"] = "sha256:bad"
    elif case == "client_side": exchanges[0]["originating_client_side"] = "B"
    elif case == "server_side": exchanges[0]["destination_server_side"] = "A"
    elif case == "client_process": exchanges[0]["client_process_instance_id"] = "wrong-process"
    elif case == "server_process": exchanges[0]["server_process_instance_id"] = "wrong-process"
    elif case == "request_origin": exchanges[0]["request_origin"] = "repository_harness"
    elif case == "response_origin": exchanges[0]["response_origin"] = "repository_harness"
    elif case == "request_rewrite": exchanges[0]["forwarded_request_json"] += " "
    elif case == "response_rewrite": exchanges[0]["delivered_response_json"] += " "
    elif case == "request_digest": exchanges[0]["request_byte_digest"] = "sha256:" + "0" * 64
    elif case == "response_digest": exchanges[0]["response_byte_digest"] = "sha256:" + "0" * 64
    elif case == "first_seen_preseed": messages[0]["client_visible_hashes_before"] = [messages[0]["message"]["message_hash"]]
    elif case == "client_control_preseed": events[1]["request"]["input"]["preseed_challenge"] = direction["challenge"]
    elif case == "client_event_request": events[0]["response"]["result"]["request_json"] += " "
    elif case == "client_event_response": events[1]["request"]["input"]["response_json"] += " "
    elif case == "client_control_scope": events[0]["request"]["input"]["run_id"] = "wrong-run"
    elif case == "missing_final_poll": direction["exchanges"].pop()
    elif case == "client_descriptor": report["participants"][0]["client_descriptor_evidence"]["descriptor"]["implementation_id"] = "substitute"
    elif case == "server_descriptor": report["participants"][0]["server_descriptor_evidence"]["descriptor"]["implementation_id"] = "substitute"
    elif case == "forged_marks": report["compatibility_marks"] = ["AICP-PAIRWISE-FAKE"]
    elif case == "degraded": report["degraded"] = True; report["degraded_reasons"] = ["forged"]
    elif case == "skipped": report["skipped_checks"] = ["causality"]
    else: raise AssertionError(case)


NEGATIVE_CASES = (
    "one_sided", "duplicate_direction", "unrelated_side_report", "same_id", "same_digest",
    "participant_digest", "report_digest", "wrong_profile", "wrong_binding", "hardcoded_hash",
    "previous_hash", "wrong_session", "wrong_contract", "cross_run_replay", "malformed_jsonrpc",
    "forged_passed", "semantic_digest", "report_type", "release_id", "release_digest",
    "target_digest", "scenario_digest", "one_run", "run_id_replay", "challenge_replay",
    "session_replay", "contract_replay", "message_id_replay", "rpc_id_replay", "process_id_replay",
    "swapped_role", "sender", "message_hash", "client_side", "server_side", "client_process",
    "server_process", "request_origin", "response_origin", "request_rewrite", "response_rewrite",
    "request_digest", "response_digest", "first_seen_preseed", "client_control_preseed",
    "client_event_request", "client_event_response", "client_control_scope", "missing_final_poll",
    "client_descriptor", "server_descriptor", "forged_marks", "degraded", "skipped",
)


@pytest.mark.parametrize("case", NEGATIVE_CASES)
def test_pairwise_mutations_fail_closed(case: str, pairwise_artifacts: dict[str, Path]) -> None:
    joint = _load(pairwise_artifacts["joint"])
    _mutate(case, joint)
    result = evaluate_pairwise_report(joint, base_dir=pairwise_artifacts["joint"].parent)
    assert result["status"] == "rejected", (case, result)
    assert result["eligible_pairwise_relations"] == [], case
    assert result["eligible_marks"] == [], case


def _manifest(report: dict[str, Any], *, reverse: bool = False) -> dict[str, Any]:
    participants = list(reversed(report["participants"])) if reverse else report["participants"]
    primary, peer = participants
    return {
        "submission_id": "m66-pairwise-test",
        "implementation_id": primary["implementation_id"],
        "implementation_version": primary["implementation_version"],
        "implementation_digest": primary["implementation_digest"],
        "peer_implementation_id": peer["implementation_id"],
        "peer_implementation_version": peer["implementation_version"],
        "peer_implementation_digest": peer["implementation_digest"],
        "profile_ids": ["AICP-BASE"],
        "profile_refs": [{"profile_id": "AICP-BASE", "profile_version": "0.1"}],
        "binding_refs": [{"binding_id": "BIND-MCP", "binding_version": "0.1"}],
        "evidence_types": ["profile_report", "binding_report", "pairwise_report"],
        "evidence_status": "pairwise",
        "report_refs": ["joint.json", "a-profile.json", "a-binding.json", "b-profile.json", "b-binding.json"],
        "joint_report_ref": "joint.json",
        "suite_refs": ["conformance/core/CT_CORE_0.1.json", "conformance/bindings/TB_MCP_0.1.json"],
        "claim_type": "pairwise_interop",
        "claim_scope": "pairwise",
        "generated_at": "2026-08-27T00:00:00Z",
        "disclosures": ["Repository-owned clean-room test peers; not external adoption."],
    }


def test_public_pairwise_evaluator_and_reciprocal_identity(pairwise_artifacts: dict[str, Path]) -> None:
    report = _load(pairwise_artifacts["joint"])
    manifest_path = pairwise_artifacts["joint"].parent / "submission.json"
    forward = evaluate_strong_report_evidence(manifest_path, _manifest(report))
    reverse = evaluate_strong_report_evidence(manifest_path, _manifest(report, reverse=True))
    assert forward.status == reverse.status == "eligible"
    assert forward.eligible_pairwise_relations == reverse.eligible_pairwise_relations
    assert forward.eligible_marks == reverse.eligible_marks == ()


@pytest.mark.parametrize(
    "vector",
    (
        PAIRWISE / "historical_vectors" / "AICP-PAIRWISE-TCK-1.0.0",
        PAIRWISE / "current_vectors" / "AICP-PAIRWISE-TCK-1.1.0",
    ),
)
def test_public_old_pairwise_reports_are_historical_strong_ineligible(vector: Path) -> None:
    report = _load(vector / "joint.json")
    result = evaluate_strong_report_evidence(vector / "submission.json", _manifest(report))
    assert result.status == "rejected"
    assert result.eligible_pairwise_relations == ()
    assert result.eligible_marks == ()
    assert any("PAIRWISE_RELEASE_HISTORICAL_INELIGIBLE" in error for error in result.errors)


def test_builder_creates_and_validates_five_report_pairwise_package(
    pairwise_artifacts: dict[str, Path], tmp_path: Path
) -> None:
    joint = _load(pairwise_artifacts["joint"])
    primary, peer = joint["participants"]
    command = [
        sys.executable, "interop/tools/build_submission.py", "--out-root", str(tmp_path),
        "--submission-id", "valid-pairwise", "--implementation-id", primary["implementation_id"],
        "--implementation-version", primary["implementation_version"], "--implementation-digest", primary["implementation_digest"],
        "--peer-implementation-id", peer["implementation_id"], "--peer-implementation-version", peer["implementation_version"],
        "--peer-implementation-digest", peer["implementation_digest"], "--profile-id", "AICP-BASE",
        "--profile-ref", "AICP-BASE@0.1", "--binding-ref", "BIND-MCP@0.1",
        "--claim-type", "pairwise_interop", "--claim-scope", "pairwise", "--evidence-status", "pairwise",
    ]
    for key in ("a_profile", "a_binding", "b_profile", "b_binding"):
        command.extend(["--report-path", str(pairwise_artifacts[key])])
    command.extend([
        "--joint-report-path", str(pairwise_artifacts["joint"]),
        "--suite-ref", "conformance/core/CT_CORE_0.1.json", "--suite-ref", "conformance/bindings/TB_MCP_0.1.json",
        "--evidence-type", "profile_report", "--evidence-type", "binding_report", "--evidence-type", "pairwise_report",
        "--disclosure", "Repository-owned clean-room test only; not external adoption.", "--with-integrity", "--validate",
    ])
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, shell=False, timeout=60)
    assert result.returncode == 0, result.stdout + result.stderr
    built = tmp_path / "valid-pairwise"
    assert (built / "bundle-integrity.json").is_file()
    assert evaluate_strong_report_evidence(built / "submission.json", _load(built / "submission.json")).status == "eligible"


def test_missing_joint_report_keeps_deterministic_fail_closed_error(pairwise_artifacts: dict[str, Path]) -> None:
    report = _load(pairwise_artifacts["joint"])
    manifest = _manifest(report)
    manifest["joint_report_ref"] = "missing.json"
    manifest["report_refs"][0] = "missing.json"
    result = evaluate_strong_report_evidence(pairwise_artifacts["joint"].parent / "submission.json", manifest)
    assert result.status == "rejected"
    assert result.errors[0].startswith(PAIRWISE_JOINT_EVIDENCE_ERROR)


def test_cleanroom_sources_do_not_import_repository_semantic_or_answer_code() -> None:
    sources = [PAIRWISE / "cleanroom" / "peer_a" / "peer_a.py", PAIRWISE / "cleanroom" / "peer_b" / "peer_b.mjs"]
    forbidden = ("aicp_ref", "reference/python", "conformance/", "fixtures/", "expected_result")
    for source in sources:
        lowered = source.read_text(encoding="utf-8").lower()
        assert not any(token in lowered for token in forbidden), source


def test_process_environment_is_allowlisted_and_excludes_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "secret")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secret")
    environment = allowlisted_environment()
    assert "GITHUB_TOKEN" not in environment
    assert "AWS_SECRET_ACCESS_KEY" not in environment


def test_process_boundary_rejects_stdout_flood() -> None:
    command = [sys.executable, "-c", "import sys; sys.stdout.write('x'*1048577+'\\n'); sys.stdout.flush()"]
    process = JsonLineProcess(command, cwd=ROOT, timeout=5.0, instance_id="stdout-flood")
    try:
        with pytest.raises(ProcessBoundaryError, match="line-size"):
            process.exchange({"request": "bounded"})
    finally:
        process.abort()


def test_process_boundary_bounds_stderr() -> None:
    command = [sys.executable, "-c", "import sys,json; sys.stderr.write('x'*100000); sys.stderr.flush(); print(json.dumps({'ok':True}),flush=True); sys.stdin.readline()"]
    process = JsonLineProcess(command, cwd=ROOT, timeout=5.0, instance_id="stderr-bound")
    try:
        assert process.exchange({"request": "bounded"}) == {"ok": True}
        process.close()
        assert len(process.bounded_stderr.encode("utf-8")) <= MAX_STDERR_BYTES
    finally:
        process.abort()


def test_pairwise_test_count_exceeds_required_negative_surface() -> None:
    assert len(NEGATIVE_CASES) >= 45
