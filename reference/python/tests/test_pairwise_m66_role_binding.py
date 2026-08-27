from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[3]
PAIRWISE = ROOT / "interop" / "pairwise"
VECTOR = PAIRWISE / "current_vectors" / "AICP-PAIRWISE-TCK-1.3.0"
PEER_A = PAIRWISE / "cleanroom" / "peer_a" / "peer_a_v1_3.py"
PEER_B = PAIRWISE / "cleanroom" / "peer_b" / "peer_b_v1_3.mjs"
for path in (PAIRWISE, ROOT / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from aicp_pairwise_runner_v1_3 import verify_runner_bundle  # noqa: E402
from pairwise_process_v1_2 import ProcessBoundaryError  # noqa: E402
from pairwise_release_router import evaluate_pairwise_report  # noqa: E402


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _command_json(command: list[str]) -> str:
    return json.dumps(command)


def _peer(side: str, mode: str, behavior: str = "good") -> list[str]:
    node = shutil.which("node")
    assert node is not None
    base = [sys.executable, str(PEER_A)] if side == "A" else [node, str(PEER_B)]
    command = [*base, mode]
    if behavior != "good":
        command.extend(["--behavior", behavior])
    return command


def _run_pairwise(
    destination: Path,
    *,
    a_client: list[str] | None = None,
    a_server: list[str] | None = None,
    b_client: list[str] | None = None,
    b_server: list[str] | None = None,
    test_behavior: str = "good",
    profile_overrides: dict[str, Path] | None = None,
) -> tuple[subprocess.CompletedProcess[str], Path]:
    destination.mkdir(parents=True, exist_ok=True)
    reports: dict[str, Path] = {}
    for key, name in (
        ("a_profile", "a-profile.json"),
        ("a_binding", "a-binding.json"),
        ("b_profile", "b-profile.json"),
        ("b_binding", "b-binding.json"),
    ):
        target = destination / name
        source = (profile_overrides or {}).get(key, VECTOR / name)
        if source.resolve() != target.resolve():
            shutil.copy2(source, target)
        reports[key] = target
    joint = destination / "joint.json"
    command = [
        sys.executable,
        "interop/pairwise/aicp_pairwise_runner_v1_3.py",
        "--peer-a-client-cmd-json", _command_json(a_client or _peer("A", "pairwise-client")),
        "--peer-a-server-cmd-json", _command_json(a_server or _peer("A", "pairwise-server")),
        "--peer-a-profile-report", str(reports["a_profile"]),
        "--peer-a-binding-report", str(reports["a_binding"]),
        "--peer-b-client-cmd-json", _command_json(b_client or _peer("B", "pairwise-client")),
        "--peer-b-server-cmd-json", _command_json(b_server or _peer("B", "pairwise-server")),
        "--peer-b-profile-report", str(reports["b_profile"]),
        "--peer-b-binding-report", str(reports["b_binding"]),
        "--test-behavior", test_behavior,
        "--out", str(joint),
    ]
    return subprocess.run(command, cwd=ROOT, text=True, capture_output=True, shell=False, timeout=90), joint


def _assert_no_eligible(result: subprocess.CompletedProcess[str], joint: Path) -> None:
    if joint.is_file():
        evaluation = evaluate_pairwise_report(_load(joint), base_dir=joint.parent)
        assert evaluation["status"] == "rejected", evaluation
        assert evaluation["eligible_pairwise_relations"] == []
        assert evaluation["eligible_marks"] == []
    else:
        assert result.returncode != 0, result.stdout + result.stderr


def test_actual_peer_client_server_joint_execution_and_process_accounting(tmp_path: Path) -> None:
    result, joint = _run_pairwise(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Pairwise role path PASSED: A client -> B server" in result.stdout
    assert "Pairwise role path PASSED: B client -> A server" in result.stdout
    report = _load(joint)
    assert evaluate_pairwise_report(report, base_dir=tmp_path)["status"] == "eligible"
    participants = {item["side"]: item for item in report["participants"]}
    for run in report["runs"]:
        instances = {item["side"]: item for item in run["role_instances"]}
        process_ids = {
            item[field]
            for item in instances.values()
            for field in ("client_process_instance_id", "server_process_instance_id")
        }
        assert len(process_ids) == 4
        for side in ("A", "B"):
            participant = participants[side]
            assert participant["client_descriptor_evidence"]["runs"]
            assert participant["server_descriptor_evidence"]["runs"]
        for direction in run["directions"]:
            producer, consumer = direction["producer_side"], direction["consumer_side"]
            routes = [(producer, consumer), (consumer, consumer), (consumer, producer), (producer, producer), (producer, consumer), (consumer, consumer)]
            assert len(direction["exchanges"]) == 6
            for exchange, route in zip(direction["exchanges"], routes, strict=True):
                assert (exchange["originating_client_side"], exchange["destination_server_side"]) == route
                assert exchange["request_origin"] == "participant_client"
                assert exchange["response_origin"] == "participant_server"
                assert exchange["request_json"] == exchange["forwarded_request_json"]
                assert exchange["response_json"] == exchange["delivered_response_json"]


@pytest.mark.parametrize(
    ("overrides", "expected_fragment"),
    (
        ({"b_server": _peer("A", "pairwise-server")}, "side B server descriptor"),
        ({"a_server": _peer("B", "pairwise-server")}, "side A server descriptor"),
        ({"a_server": _peer("A", "pairwise-server"), "b_server": _peer("A", "pairwise-server")}, "side B server descriptor"),
        ({"a_server": _peer("B", "pairwise-server"), "b_server": _peer("B", "pairwise-server")}, "side A server descriptor"),
    ),
)
def test_server_substitution_fails_before_semantic_execution(
    overrides: dict[str, list[str]], expected_fragment: str, tmp_path: Path
) -> None:
    result, joint = _run_pairwise(tmp_path, **overrides)
    assert result.returncode != 0
    assert expected_fragment in result.stderr
    assert not joint.exists()


@pytest.mark.parametrize(
    "overrides",
    (
        {"b_client": _peer("A", "pairwise-client")},
        {"a_client": _peer("B", "pairwise-client")},
        {"a_client": _peer("A", "pairwise-client"), "b_client": _peer("A", "pairwise-client")},
        {"a_client": _peer("B", "pairwise-client"), "b_client": _peer("B", "pairwise-client")},
    ),
)
def test_client_substitution_fails_before_semantic_execution(overrides: dict[str, list[str]], tmp_path: Path) -> None:
    result, joint = _run_pairwise(tmp_path, **overrides)
    assert result.returncode != 0
    assert "client descriptor" in result.stderr
    assert not joint.exists()


@pytest.mark.parametrize(
    "behavior",
    (
        "wrong_implementation_id",
        "wrong_implementation_version",
        "wrong_implementation_digest",
        "wrong_server_target",
        "server_report_identity_mismatch",
        "missing_server_descriptor",
        "malformed_server_descriptor",
    ),
)
def test_server_descriptor_negatives_fail_closed(behavior: str, tmp_path: Path) -> None:
    result, joint = _run_pairwise(tmp_path, a_server=_peer("A", "pairwise-server", behavior))
    assert result.returncode != 0
    assert "server" in result.stderr.lower()
    assert not joint.exists()


@pytest.mark.parametrize(
    "behavior",
    (
        "wrong_implementation_id",
        "wrong_implementation_version",
        "wrong_implementation_digest",
        "wrong_client_target",
        "client_server_identity_mismatch",
    ),
)
def test_client_descriptor_negatives_fail_closed(behavior: str, tmp_path: Path) -> None:
    result, joint = _run_pairwise(tmp_path, a_client=_peer("A", "pairwise-client", behavior))
    assert result.returncode != 0
    assert "client" in result.stderr.lower()
    assert not joint.exists()


@pytest.mark.parametrize(
    "behavior",
    (
        "harness_constructed_send",
        "relay_rewrites_request",
        "relay_rewrites_response",
        "relay_changes_jsonrpc_id",
        "relay_changes_message",
        "relay_synthesizes_success_response",
        "relay_routes_to_wrong_server_side",
        "consumer_does_not_poll",
        "consumer_uses_preseeded_peer_message",
        "consumer_uses_preseeded_peer_hash",
        "consumer_uses_preseeded_challenge",
        "preseed_consumer_challenge",
        "preseed_consumer_peer_hash",
        "missing_final_consumer_poll",
    ),
)
def test_relay_and_causality_negative_modes_have_no_relation(behavior: str, tmp_path: Path) -> None:
    result, joint = _run_pairwise(tmp_path, test_behavior=behavior)
    _assert_no_eligible(result, joint)


@pytest.mark.parametrize(
    "behavior",
    (
        "hardcoded_peer_hash",
        "stale_peer_hash",
        "previous_run_peer_hash",
        "wrong_prev_msg_hash",
        "wrong_session",
        "wrong_contract",
        "rewritten_peer_message",
        "missing_contract_goal",
        "malformed_contract_ref",
        "invalid_contract_accept_payload",
        "invalid_attest_action_payload",
        "ignore_challenge",
        "previous_run_challenge",
        "prebuilt_proposal",
        "stale_final_poll_cursor",
        "hardcoded_c0_final_poll",
        "unrelated_cursor",
        "missing_poll_limit",
        "wrong_poll_limit",
        "wrong_poll_session",
    ),
)
def test_real_client_core_and_challenge_adversaries_have_no_relation(behavior: str, tmp_path: Path) -> None:
    result, joint = _run_pairwise(tmp_path, a_client=_peer("A", "pairwise-client", behavior))
    _assert_no_eligible(result, joint)


@pytest.mark.parametrize("behavior", ("server_rewrites_message", "server_returns_another_session_message"))
def test_separately_valid_side_evidence_does_not_substitute_for_joint_compatibility(behavior: str, tmp_path: Path) -> None:
    result, joint = _run_pairwise(tmp_path, b_server=_peer("B", "pairwise-server", behavior))
    _assert_no_eligible(result, joint)


def test_invalid_side_report_prevalidation_spawns_no_peer_process(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid-a-profile.json"
    value = _load(VECTOR / "a-profile.json")
    value["passed"] = False
    invalid.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    marker = tmp_path / "spawned.txt"
    forbidden_command = [sys.executable, "-c", f"from pathlib import Path; Path({str(marker)!r}).write_text('spawned')"]
    result, joint = _run_pairwise(
        tmp_path / "run",
        a_client=forbidden_command,
        a_server=forbidden_command,
        b_client=forbidden_command,
        b_server=forbidden_command,
        profile_overrides={"a_profile": invalid},
    )
    assert result.returncode != 0
    assert "side A evidence is ineligible" in result.stderr
    assert not marker.exists()
    assert not joint.exists()


def test_runtime_runner_bundle_mutation_fails_closed(tmp_path: Path) -> None:
    bundle = _load(PAIRWISE / "pairwise_runner_bundle_v1_3.json")
    bundle["entries"][0]["digest"] = "sha256:" + "0" * 64
    mutated = tmp_path / "pairwise_runner_bundle_v1_3.json"
    mutated.write_text(json.dumps(bundle, indent=2) + "\n", encoding="utf-8")
    with pytest.raises(ProcessBoundaryError, match="import closure differs"):
        verify_runner_bundle(bundle_path=mutated)
