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
CURRENT_VECTOR = PAIRWISE / "current_vectors" / "AICP-PAIRWISE-TCK-1.1.0"
HISTORICAL_VECTOR = PAIRWISE / "historical_vectors" / "AICP-PAIRWISE-TCK-1.0.0"
for path in (PAIRWISE, ROOT / "scripts", ROOT / "reference" / "python"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from aicp_ref.hashing import message_hash_from_body, object_hash  # noqa: E402
from aicp_ref.jcs import canonicalize_json  # noqa: E402
from generate_pairwise_tck import (  # noqa: E402
    FROZEN_1_0_RAW_SHA256,
    discover_import_closure,
    raw_sha256,
)
from pairwise_report_dispatcher import evaluate_pairwise_report  # noqa: E402
from pairwise_side_report_evaluator_v1_1 import (  # noqa: E402
    evaluate_side_report,
    frozen_hash,
    validate_core_transcript,
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _command_json(command: list[str]) -> str:
    return json.dumps(command)


def _run(command: list[str], *, cwd: Path = ROOT, timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=cwd,
        text=True,
        capture_output=True,
        shell=False,
        timeout=timeout,
    )


def _copy_current_side_reports(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("a-profile.json", "a-binding.json", "b-profile.json", "b-binding.json"):
        shutil.copy2(CURRENT_VECTOR / name, destination / name)


def _run_behavior(behavior: str, destination: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    _copy_current_side_reports(destination)
    node = shutil.which("node")
    assert node is not None
    peer_a = PAIRWISE / "cleanroom" / "peer_a" / "peer_a.py"
    peer_b = PAIRWISE / "cleanroom" / "peer_b" / "peer_b.mjs"
    joint = destination / "joint.json"
    command = [
        sys.executable,
        "interop/pairwise/aicp_pairwise_runner_v1_1.py",
        "--peer-a-control-cmd-json",
        _command_json([sys.executable, str(peer_a), "pairwise-control", "--behavior", behavior]),
        "--peer-a-server-cmd-json",
        _command_json([sys.executable, str(peer_a), "pairwise-server"]),
        "--peer-a-profile-report",
        str(destination / "a-profile.json"),
        "--peer-a-binding-report",
        str(destination / "a-binding.json"),
        "--peer-b-control-cmd-json",
        _command_json([node, str(peer_b), "pairwise-control"]),
        "--peer-b-server-cmd-json",
        _command_json([node, str(peer_b), "pairwise-server"]),
        "--peer-b-profile-report",
        str(destination / "b-profile.json"),
        "--peer-b-binding-report",
        str(destination / "b-binding.json"),
        "--out",
        str(joint),
    ]
    result = _run(command)
    assert result.returncode == 0, result.stdout + result.stderr
    report = _load(joint)
    return report, evaluate_pairwise_report(report, base_dir=destination)


def _copy_isolated_pairwise(tmp_path: Path) -> tuple[Path, Path]:
    isolated_root = tmp_path / "repo"
    isolated_pairwise = isolated_root / "interop" / "pairwise"
    shutil.copytree(PAIRWISE, isolated_pairwise)
    evidence_source = ROOT / "conformance" / "evidence" / "evidence_tck_releases.json"
    evidence_target = isolated_root / "conformance" / "evidence" / evidence_source.name
    evidence_target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(evidence_source, evidence_target)
    return isolated_root, isolated_pairwise


def _dispatch_isolated(isolated_root: Path, isolated_pairwise: Path) -> dict[str, Any]:
    joint = isolated_pairwise / "current_vectors" / "AICP-PAIRWISE-TCK-1.1.0" / "joint.json"
    result = _run(
        [sys.executable, str(isolated_pairwise / "pairwise_report_dispatcher.py"), str(joint)],
        cwd=isolated_root,
    )
    assert result.stdout, result.stderr
    return json.loads(result.stdout)


def test_pairwise_1_0_byte_freeze_and_historical_policy() -> None:
    for relative, expected in FROZEN_1_0_RAW_SHA256.items():
        assert raw_sha256(ROOT / relative) == expected
    report = _load(HISTORICAL_VECTOR / "joint.json")
    result = evaluate_pairwise_report(report, base_dir=HISTORICAL_VECTOR)
    assert result["status"] == "ineligible"
    assert result["errors"][0]["code"] == "PAIRWISE_RELEASE_HISTORICAL_INELIGIBLE"
    assert result["eligible_pairwise_relations"] == []
    assert result["eligible_marks"] == []


def test_pairwise_1_1_current_vector_and_side_authorities_are_eligible() -> None:
    report = _load(CURRENT_VECTOR / "joint.json")
    result = evaluate_pairwise_report(report, base_dir=CURRENT_VECTOR)
    assert result["status"] == "eligible"
    assert len(result["eligible_pairwise_relations"]) == 1
    assert result["eligible_marks"] == []
    participants = {item["side"]: item for item in report["participants"]}
    for side, prefix in (("A", "a"), ("B", "b")):
        identity = {
            "kind": participants[side]["implementation_kind"],
            "implementation_id": participants[side]["implementation_id"],
            "implementation_version": participants[side]["implementation_version"],
            "implementation_digest": participants[side]["implementation_digest"],
        }
        assert evaluate_side_report(_load(CURRENT_VECTOR / f"{prefix}-profile.json"), kind="profile", identity=identity) == []
        assert evaluate_side_report(_load(CURRENT_VECTOR / f"{prefix}-binding.json"), kind="binding", identity=identity) == []


def test_clean_directions_pass_frozen_core_and_bind_every_control_field() -> None:
    report = _load(CURRENT_VECTOR / "joint.json")
    semantic_digests = []
    for run in report["runs"]:
        semantic_digests.append(run["semantic_digest"])
        for direction in run["directions"]:
            assert validate_core_transcript([item["message"] for item in direction["messages"]]) == []
            for item in direction["messages"]:
                control = item["control_request"]["input"]
                message = item["message"]
                assert control["run_id"] == run["run_id"]
                assert control["challenge"] == run["challenge"]
                assert control["side"] == item["constructed_by"]
                assert control["session_id"] == direction["session_id"]
                assert control["contract_id"] == direction["contract_id"]
                assert control["message_id"] == message["message_id"]
                assert control["timestamp"] == message["timestamp"]
            assert direction["messages"][0]["message"]["payload"]["contract"]["goal"] == run["challenge"]
    assert semantic_digests[0] == semantic_digests[1]


@pytest.mark.parametrize(
    "behavior",
    (
        "missing_contract_goal",
        "malformed_contract_ref",
        "invalid_contract_accept_payload",
        "invalid_attest_action_payload",
        "ignore_challenge",
        "previous_run_challenge",
        "prebuilt_proposal",
    ),
)
def test_real_process_core_and_challenge_adversaries_fail_closed(
    behavior: str,
    tmp_path: Path,
) -> None:
    report, result = _run_behavior(behavior, tmp_path)
    assert result["status"] == "rejected", behavior
    assert result["eligible_pairwise_relations"] == [], behavior
    assert result["eligible_marks"] == [], behavior
    assert all(item["message"]["message_hash"] for run in report["runs"] for direction in run["directions"] for item in direction["messages"])
    codes = {item["code"] for item in result["errors"]}
    if behavior in {"missing_contract_goal", "malformed_contract_ref", "invalid_contract_accept_payload", "invalid_attest_action_payload"}:
        assert "PAIRWISE_CORE_TRANSCRIPT_INVALID" in codes
    else:
        assert "PAIRWISE_PROPOSAL_SEMANTICS_INVALID" in codes


@pytest.mark.parametrize(
    "mutation",
    (
        "future_evidence_release",
        "future_pairwise_target",
        "future_pairwise_scenario",
        "future_pairwise_release",
        "unrelated_registry_reordering",
    ),
)
def test_future_current_registry_changes_do_not_invalidate_1_1(
    mutation: str,
    tmp_path: Path,
) -> None:
    isolated_root, isolated_pairwise = _copy_isolated_pairwise(tmp_path)
    if mutation == "future_evidence_release":
        path = isolated_root / "conformance/evidence/evidence_tck_releases.json"
        value = _load(path)
        value["releases"].append({"release_id": "AICP-EVIDENCE-TCK-99.0.0", "future_only": True})
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    elif mutation == "future_pairwise_target":
        path = isolated_pairwise / "targets.json"
        value = _load(path)
        value["targets"].append({"target_id": "FUTURE-UNRELATED@9.9"})
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    elif mutation == "future_pairwise_scenario":
        path = isolated_pairwise / "scenarios.json"
        value = _load(path)
        value["future_scenarios"] = [{"scenario_id": "PAIRWISE-FUTURE-UNRELATED-99"}]
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    else:
        path = isolated_pairwise / "tck_releases.json"
        value = _load(path)
        if mutation == "future_pairwise_release":
            future = json.loads(json.dumps(value["releases"][-1]))
            future["release_id"] = "AICP-PAIRWISE-TCK-9.9.9"
            value["releases"].append(future)
            value["release_policies"][-1]["lifecycle"] = "historical"
            value["release_policies"].append(
                {"release_id": future["release_id"], "lifecycle": "current", "strong_eligible": False, "reason": "hypothetical"}
            )
        else:
            value["releases"].reverse()
            value["release_policies"].reverse()
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    result = _dispatch_isolated(isolated_root, isolated_pairwise)
    assert result["status"] == "eligible", (mutation, result)


@pytest.mark.parametrize(
    "relative",
    (
        "pairwise_joint_report_v1_1.schema.json",
        "pairwise_report_evaluator_v1_1.py",
        "release_artifacts/AICP-PAIRWISE-TCK-1.1.0/targets.json",
        "release_artifacts/AICP-PAIRWISE-TCK-1.1.0/scenarios.json",
        "release_artifacts/AICP-PAIRWISE-TCK-1.1.0/authority_root/pairwise_side_authorities.json",
    ),
)
def test_immutable_1_1_artifact_mutation_fails_closed(relative: str, tmp_path: Path) -> None:
    isolated_root, isolated_pairwise = _copy_isolated_pairwise(tmp_path)
    path = isolated_pairwise / relative
    if path.suffix == ".py":
        path.write_text(path.read_text(encoding="utf-8") + "\n# immutable mutation\n", encoding="utf-8")
    else:
        value = _load(path)
        value["x_immutable_mutation"] = True
        path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    result = _dispatch_isolated(isolated_root, isolated_pairwise)
    assert result["status"] == "rejected", (relative, result)
    assert result["eligible_pairwise_relations"] == []
    assert result["eligible_marks"] == []


def test_normative_jcs_and_hash_parity() -> None:
    vectors: list[Any] = [
        {"é": "non-ascii", "a": "first", "中": "last"},
        {"nested": {"z": 1, "a": [True, False, None]}},
        ["array", {"n": 9007199254740991}, 0, -7, 1.5],
        {"bool": True, "null": None, "safe": 42},
    ]
    for value in vectors:
        result = frozen_hash("parity", value)
        assert result["canonical_json"] == canonicalize_json(value)
        assert result["object_hash"] == object_hash("parity", value)
    message = {"session_id": "s", "payload": {"é": [True, None, 7]}}
    result = frozen_hash("message", message)
    assert result["message_hash"] == message_hash_from_body(message)


def test_evaluator_manifest_equals_mechanically_discovered_import_closure() -> None:
    discovered = discover_import_closure(
        [
            PAIRWISE / "pairwise_report_dispatcher.py",
            PAIRWISE / "pairwise_report_evaluator_v1_1.py",
            PAIRWISE / "pairwise_semantic_normalizer_v1_1.py",
            PAIRWISE / "pairwise_side_report_evaluator_v1_1.py",
            PAIRWISE / "pairwise_authority_bridge_v1_1.py",
        ]
    )
    expected_snapshot_paths = {
        (
            "interop/pairwise/release_artifacts/AICP-PAIRWISE-TCK-1.1.0/authority_root/"
            + path.relative_to(ROOT).as_posix()
        )
        for path in discovered
    }
    manifest = _load(PAIRWISE / "pairwise_evaluator_bundle_v1_1.json")
    actual_snapshot_paths = {
        item["path"]
        for item in manifest["entries"]
        if item["role"] == "generated_import_closure"
    }
    assert actual_snapshot_paths == expected_snapshot_paths


def test_no_genuine_external_pairwise_1_0_or_1_1_adoption() -> None:
    real_pairwise: list[Path] = []
    submissions = ROOT / "interop" / "submissions"
    for manifest_path in submissions.rglob("submission.json"):
        if {"examples", "templates"}.intersection(manifest_path.relative_to(submissions).parts):
            continue
        manifest = _load(manifest_path)
        if manifest.get("claim_type") == "pairwise_interop" and manifest.get("evidence_status") == "pairwise":
            real_pairwise.append(manifest_path)
    assert real_pairwise == []
