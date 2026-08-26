from __future__ import annotations

import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[3]
PAIRWISE = ROOT / "interop" / "pairwise"
SCRIPTS = ROOT / "scripts"
for import_path in (PAIRWISE, SCRIPTS):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from interop_submission_validation import (  # noqa: E402
    PAIRWISE_JOINT_EVIDENCE_ERROR,
    evaluate_strong_report_evidence,
)
from pairwise_process import MAX_STDERR_BYTES, JsonLineProcess, ProcessBoundaryError, allowlisted_environment  # noqa: E402
from pairwise_report_dispatcher import evaluate_pairwise_report  # noqa: E402


def _run(command: list[str]) -> None:
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, shell=False, timeout=90)
    assert result.returncode == 0, result.stdout + result.stderr


def _command_json(command: list[str]) -> str:
    return json.dumps(command)


@pytest.fixture(scope="session")
def pairwise_artifacts(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Path]:
    output = tmp_path_factory.mktemp("m66-pairwise")
    node = shutil.which("node")
    assert node is not None
    python_peer = ROOT / "interop" / "pairwise" / "cleanroom" / "peer_a" / "peer_a.py"
    node_peer = ROOT / "interop" / "pairwise" / "cleanroom" / "peer_b" / "peer_b.mjs"
    paths = {
        "a_profile": output / "a-profile.json",
        "a_binding": output / "a-binding.json",
        "b_profile": output / "b-profile.json",
        "b_binding": output / "b-binding.json",
        "joint": output / "joint.json",
    }
    _run([sys.executable, str(python_peer), "self-test"])
    _run([node, str(node_peer), "self-test"])
    _run([
        sys.executable, "conformance/iut/aicp_iut_runner.py", "--cmd-json",
        _command_json([sys.executable, str(python_peer), "iut"]), "--profile", "AICP-BASE@0.1",
        "--mode", "full-profile", "--out", str(paths["a_profile"]),
    ])
    _run([
        sys.executable, "conformance/iut/aicp_iut_runner.py", "--cmd-json",
        _command_json([node, str(node_peer), "iut"]), "--profile", "AICP-BASE@0.1",
        "--mode", "full-profile", "--out", str(paths["b_profile"]),
    ])
    for side, command in (
        ("a", [sys.executable, str(python_peer)]),
        ("b", [node, str(node_peer)]),
    ):
        _run([
            sys.executable, "conformance/evidence/aicp_live_binding_runner.py", "--target", "BIND-MCP@0.1",
            "--server-cmd-json", _command_json([*command, "binding-server"]),
            "--client-cmd-json", _command_json([*command, "binding-client"]),
            "--mode", "full-binding", "--out", str(paths[f"{side}_binding"]),
        ])
    _run([
        sys.executable, "interop/pairwise/aicp_pairwise_runner_v1_1.py",
        "--peer-a-control-cmd-json", _command_json([sys.executable, str(python_peer), "pairwise-control"]),
        "--peer-a-server-cmd-json", _command_json([sys.executable, str(python_peer), "pairwise-server"]),
        "--peer-a-profile-report", str(paths["a_profile"]), "--peer-a-binding-report", str(paths["a_binding"]),
        "--peer-b-control-cmd-json", _command_json([node, str(node_peer), "pairwise-control"]),
        "--peer-b-server-cmd-json", _command_json([node, str(node_peer), "pairwise-server"]),
        "--peer-b-profile-report", str(paths["b_profile"]), "--peer-b-binding-report", str(paths["b_binding"]),
        "--out", str(paths["joint"]),
    ])
    return paths


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def test_pairwise_cleanroom_joint_run_is_eligible(pairwise_artifacts: dict[str, Path]) -> None:
    result = evaluate_pairwise_report(_load(pairwise_artifacts["joint"]), base_dir=pairwise_artifacts["joint"].parent)
    assert result["status"] == "eligible"
    assert len(result["eligible_pairwise_relations"]) == 1
    assert result["eligible_marks"] == []


def _mutate(case: str, report: dict[str, Any], directory: Path) -> None:
    run0 = report["runs"][0]
    run1 = report["runs"][1]
    direction = run0["directions"][0]
    messages = direction["messages"]
    if case == "one_sided": run0["directions"].pop()
    elif case == "duplicate_direction": run0["directions"][1] = copy.deepcopy(run0["directions"][0])
    elif case == "unrelated_side_report": report["participants"][0]["profile_report"] = copy.deepcopy(report["participants"][1]["profile_report"])
    elif case == "same_id": report["participants"][1]["implementation_id"] = report["participants"][0]["implementation_id"]
    elif case == "same_digest": report["participants"][1]["implementation_digest"] = report["participants"][0]["implementation_digest"]
    elif case == "participant_digest": report["participants"][0]["implementation_digest"] += "x"
    elif case == "report_digest": report["participants"][0]["profile_report"]["content_digest"] = "sha256:" + "0" * 64
    elif case == "wrong_profile": report["target"]["profile_id"] = "AICP-BASE-WRONG"
    elif case == "wrong_binding": report["target"]["binding_id"] = "BIND-HTTP"
    elif case == "peer_hash": messages[1]["control_request"]["input"]["peer_message"]["message_hash"] = "sha256:bad"
    elif case == "hardcoded_hash": messages[1]["message"]["prev_msg_hash"] = "sha256:" + "A" * 43
    elif case == "previous_hash": messages[2]["message"]["prev_msg_hash"] = messages[0]["message"]["message_hash"]
    elif case == "wrong_session": messages[1]["message"]["session_id"] = "wrong-session"
    elif case == "wrong_contract": messages[1]["message"]["contract_id"] = "wrong-contract"
    elif case == "cross_run_replay": run1["directions"][0]["messages"][0] = copy.deepcopy(messages[0])
    elif case == "malformed_jsonrpc": messages[0]["mcp_send"]["request"]["jsonrpc"] = "1.0"
    elif case == "forged_passed": report["passed"] = False
    elif case == "semantic_digest": run0["semantic_digest"] = "sha256:" + "0" * 64
    elif case == "report_type": report["report_type"] = "aicp.report"
    elif case == "release_id": report["pairwise_tck_release"]["release_id"] = "AICP-PAIRWISE-TCK-9.9.9"
    elif case == "release_digest": report["pairwise_tck_release"]["registry_digest"] = "sha256:" + "0" * 64
    elif case == "target_digest": report["target"]["target_catalog_digest"] = "sha256:" + "0" * 64
    elif case == "scenario_digest": report["scenario"]["scenario_catalog_digest"] = "sha256:" + "0" * 64
    elif case == "one_run": report["runs"].pop()
    elif case == "run_id_replay": run1["run_id"] = run0["run_id"]
    elif case == "challenge_replay": run1["challenge"] = run0["challenge"]
    elif case == "session_replay": run1["directions"][0]["session_id"] = direction["session_id"]
    elif case == "contract_replay": run1["directions"][0]["contract_id"] = direction["contract_id"]
    elif case == "message_id_replay": run1["directions"][0]["messages"][0]["message"]["message_id"] = messages[0]["message"]["message_id"]
    elif case == "swapped_role": messages[0]["constructed_by"] = direction["consumer_side"]
    elif case == "sender": messages[0]["message"]["sender"] = "attacker"
    elif case == "message_hash": messages[0]["message"]["message_hash"] = "sha256:bad"
    elif case == "send_rewrite": messages[0]["mcp_send"]["request"]["params"]["arguments"]["message"]["payload"] = {"rewritten": True}
    elif case == "poll_rewrite": messages[0]["mcp_poll"]["response"]["result"]["messages"] = []
    elif case == "first_seen_preseed": messages[0]["first_seen"]["visible_hashes_before"] = [messages[0]["message"]["message_hash"]]
    elif case == "control_output": messages[0]["control_response"]["result"]["message"] = {}
    elif case == "control_correlation": messages[0]["control_response"]["request_id"] = "different"
    elif case == "mcp_correlation": messages[0]["mcp_poll"]["response"]["id"] = "different"
    elif case == "forged_marks": report["compatibility_marks"] = ["AICP-PAIRWISE-FAKE"]
    elif case == "degraded": report["degraded"] = True; report["degraded_reasons"] = ["forged"]
    elif case == "skipped": report["skipped_checks"] = ["causality"]
    elif case == "descriptor": report["participants"][0]["descriptor_evidence"]["response"]["result"]["implementation_id"] = "substitute"
    elif case == "forged_side_marks":
        profile_ref = report["participants"][0]["profile_report"]
        profile_path = directory / profile_ref["path"]
        profile = _load(profile_path)
        profile["compatibility_marks"] = ["AICP-Profile-BASE-0.1", "AICP-PAIRWISE-FAKE"]
        profile_path.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")
        profile_ref["content_digest"] = _digest(profile_path)
    else: raise AssertionError(case)


NEGATIVE_CASES = (
    "one_sided", "duplicate_direction", "unrelated_side_report", "same_id", "same_digest",
    "participant_digest", "report_digest", "wrong_profile", "wrong_binding", "peer_hash",
    "hardcoded_hash", "previous_hash", "wrong_session", "wrong_contract", "cross_run_replay",
    "malformed_jsonrpc", "forged_passed", "semantic_digest", "report_type", "release_id",
    "release_digest", "target_digest", "scenario_digest", "one_run", "run_id_replay",
    "challenge_replay", "session_replay", "contract_replay", "message_id_replay", "swapped_role",
    "sender", "message_hash", "send_rewrite", "poll_rewrite", "first_seen_preseed",
    "control_output", "control_correlation", "mcp_correlation", "forged_marks", "degraded",
    "skipped", "descriptor", "forged_side_marks",
)


@pytest.mark.parametrize("case", NEGATIVE_CASES)
def test_pairwise_mutations_fail_closed(case: str, pairwise_artifacts: dict[str, Path], tmp_path: Path) -> None:
    for source in pairwise_artifacts.values():
        shutil.copy2(source, tmp_path / source.name)
    joint = _load(tmp_path / pairwise_artifacts["joint"].name)
    _mutate(case, joint, tmp_path)
    result = evaluate_pairwise_report(joint, base_dir=tmp_path)
    assert result["status"] == "rejected", case
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
        "generated_at": "2026-08-26T00:00:00Z",
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


def test_public_pairwise_1_0_report_is_historical_strong_ineligible() -> None:
    vector = PAIRWISE / "historical_vectors" / "AICP-PAIRWISE-TCK-1.0.0"
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
    assert result.errors[0].startswith("PAIRWISE_JOINT_EVIDENCE_REQUIRED:")


def test_cleanroom_sources_do_not_import_repository_semantic_or_answer_code() -> None:
    sources = [
        PAIRWISE / "cleanroom" / "peer_a" / "peer_a.py",
        PAIRWISE / "cleanroom" / "peer_b" / "peer_b.mjs",
    ]
    forbidden = ("aicp_ref", "reference/python", "conformance/", "fixtures/", "expected_result")
    for source in sources:
        lowered = source.read_text(encoding="utf-8").lower()
        assert not any(token in lowered for token in forbidden), (source, forbidden)


def test_process_environment_is_allowlisted_and_excludes_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_TOKEN", "secret")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secret")
    environment = allowlisted_environment()
    assert "GITHUB_TOKEN" not in environment
    assert "AWS_SECRET_ACCESS_KEY" not in environment


def test_process_boundary_rejects_stdout_flood(tmp_path: Path) -> None:
    command = [sys.executable, "-c", "import sys; sys.stdout.write('x'*1048577+'\\n'); sys.stdout.flush()"]
    with JsonLineProcess(command, cwd=ROOT, timeout=5.0) as process:
        with pytest.raises(ProcessBoundaryError, match="line-size"):
            process.exchange({"request": "bounded"})


def test_process_boundary_bounds_stderr(tmp_path: Path) -> None:
    command = [sys.executable, "-c", "import sys,json; sys.stderr.write('x'*100000); sys.stderr.flush(); print(json.dumps({'ok':True}),flush=True); sys.stdin.readline()"]
    process = JsonLineProcess(command, cwd=ROOT, timeout=5.0)
    try:
        assert process.exchange({"request": "bounded"}) == {"ok": True}
        process.close()
        assert len(process.bounded_stderr.encode("utf-8")) <= MAX_STDERR_BYTES
    finally:
        process.abort()


def test_pairwise_test_count_exceeds_required_negative_surface() -> None:
    assert len(NEGATIVE_CASES) >= 33
