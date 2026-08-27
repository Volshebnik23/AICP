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
CURRENT_VECTOR = PAIRWISE / "current_vectors" / "AICP-PAIRWISE-TCK-1.3.0"
ISSUED_1_1_VECTOR = PAIRWISE / "current_vectors" / "AICP-PAIRWISE-TCK-1.1.0"
ISSUED_1_2_VECTOR = PAIRWISE / "current_vectors" / "AICP-PAIRWISE-TCK-1.2.0"
HISTORICAL_1_0_VECTOR = PAIRWISE / "historical_vectors" / "AICP-PAIRWISE-TCK-1.0.0"
for path in (PAIRWISE, ROOT / "scripts", ROOT / "reference" / "python"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from aicp_pairwise_runner_v1_3 import verify_runner_bundle  # noqa: E402
from aicp_ref.hashing import message_hash_from_body, object_hash  # noqa: E402
from aicp_ref.jcs import canonicalize_json  # noqa: E402
from generate_pairwise_tck import (  # noqa: E402
    FROZEN_1_0_REPOSITORY_SHA256,
    FROZEN_1_1_MANIFEST_SHA256,
    FROZEN_1_1_REPOSITORY_SHA256,
    FROZEN_1_2_MANIFEST_SHA256,
    FROZEN_1_2_REPOSITORY_SHA256,
    discover_import_closure,
    repository_sha256,
)
from pairwise_release_router import evaluate_pairwise_report  # noqa: E402
from pairwise_side_report_evaluator_v1_1 import (  # noqa: E402
    evaluate_side_report,
    frozen_hash,
    validate_core_transcript,
)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _run(command: list[str], *, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, text=True, capture_output=True, shell=False, timeout=120)


def _copy_isolated_pairwise(tmp_path: Path) -> tuple[Path, Path]:
    isolated_root = tmp_path / "repo"
    isolated_pairwise = isolated_root / "interop" / "pairwise"
    shutil.copytree(PAIRWISE, isolated_pairwise, ignore=shutil.ignore_patterns("__pycache__"))
    evaluator_bundle = _load(PAIRWISE / "pairwise_evaluator_bundle_v1_3.json")
    for entry in evaluator_bundle["entries"]:
        relative = Path(entry["path"])
        if relative.parts[:2] == ("interop", "pairwise"):
            continue
        target = isolated_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    return isolated_root, isolated_pairwise


def _dispatch_isolated(isolated_root: Path, isolated_pairwise: Path) -> dict[str, Any]:
    joint = isolated_pairwise / "current_vectors" / "AICP-PAIRWISE-TCK-1.3.0" / "joint.json"
    result = _run([sys.executable, str(isolated_pairwise / "pairwise_release_router.py"), str(joint)], cwd=isolated_root)
    assert result.stdout, result.stderr
    return json.loads(result.stdout)


@pytest.mark.parametrize(
    ("vector", "release_id"),
    (
        (HISTORICAL_1_0_VECTOR, "AICP-PAIRWISE-TCK-1.0.0"),
        (ISSUED_1_1_VECTOR, "AICP-PAIRWISE-TCK-1.1.0"),
        (ISSUED_1_2_VECTOR, "AICP-PAIRWISE-TCK-1.2.0"),
    ),
)
def test_old_pairwise_releases_are_byte_frozen_and_historical(vector: Path, release_id: str) -> None:
    frozen = {
        "AICP-PAIRWISE-TCK-1.0.0": FROZEN_1_0_REPOSITORY_SHA256,
        "AICP-PAIRWISE-TCK-1.1.0": FROZEN_1_1_REPOSITORY_SHA256,
        "AICP-PAIRWISE-TCK-1.2.0": FROZEN_1_2_REPOSITORY_SHA256,
    }[release_id]
    for relative, expected in frozen.items():
        if not relative.startswith("interop/pairwise/"):
            continue
        assert repository_sha256(ROOT / relative) == expected
    if release_id.endswith("1.1.0"):
        freeze = PAIRWISE / "release_freezes" / "AICP-PAIRWISE-TCK-1.1.0.json"
        assert repository_sha256(freeze) == FROZEN_1_1_MANIFEST_SHA256
    if release_id.endswith("1.2.0"):
        freeze = PAIRWISE / "release_freezes" / "AICP-PAIRWISE-TCK-1.2.0.json"
        assert repository_sha256(freeze) == FROZEN_1_2_MANIFEST_SHA256
    result = evaluate_pairwise_report(_load(vector / "joint.json"), base_dir=vector)
    assert result["status"] == "ineligible"
    assert result["errors"][0]["code"] == "PAIRWISE_RELEASE_HISTORICAL_INELIGIBLE"
    assert result["eligible_pairwise_relations"] == []
    assert result["eligible_marks"] == []


def test_pairwise_1_3_vector_and_frozen_side_authorities_are_eligible() -> None:
    report = _load(CURRENT_VECTOR / "joint.json")
    result = evaluate_pairwise_report(report, base_dir=CURRENT_VECTOR)
    assert result["status"] == "eligible"
    assert len(result["eligible_pairwise_relations"]) == 1
    assert result["eligible_marks"] == []
    participants = {item["side"]: item for item in report["participants"]}
    for side, prefix in (("A", "a"), ("B", "b")):
        participant = participants[side]
        identity = {
            "kind": participant["implementation_kind"],
            "implementation_id": participant["implementation_id"],
            "implementation_version": participant["implementation_version"],
            "implementation_digest": participant["implementation_digest"],
        }
        assert evaluate_side_report(_load(CURRENT_VECTOR / f"{prefix}-profile.json"), kind="profile", identity=identity) == []
        assert evaluate_side_report(_load(CURRENT_VECTOR / f"{prefix}-binding.json"), kind="binding", identity=identity) == []
        for descriptor_field in ("client_descriptor_evidence", "server_descriptor_evidence"):
            descriptor = participant[descriptor_field]["descriptor"]
            assert {
                "kind": descriptor["implementation_kind"],
                "implementation_id": descriptor["implementation_id"],
                "implementation_version": descriptor["implementation_version"],
                "implementation_digest": descriptor["implementation_digest"],
            } == identity
    assert participants["A"]["implementation_digest"] != participants["B"]["implementation_digest"]


def test_exact_role_paths_core_and_client_first_seen_are_load_bearing() -> None:
    report = _load(CURRENT_VECTOR / "joint.json")
    semantic_digests = []
    for run in report["runs"]:
        semantic_digests.append(run["semantic_digest"])
        instances = {item["side"]: item for item in run["role_instances"]}
        visible = {"A": [], "B": []}
        for direction in run["directions"]:
            producer = direction["producer_side"]
            consumer = direction["consumer_side"]
            expected_routes = [
                (producer, consumer),
                (consumer, consumer),
                (consumer, producer),
                (producer, producer),
                (producer, consumer),
                (consumer, consumer),
            ]
            assert validate_core_transcript([item["message"] for item in direction["messages"]]) == []
            assert len(direction["exchanges"]) == 6
            for exchange, (client_side, server_side) in zip(direction["exchanges"], expected_routes, strict=True):
                assert exchange["originating_client_side"] == client_side
                assert exchange["destination_server_side"] == server_side
                assert exchange["client_process_instance_id"] == instances[client_side]["client_process_instance_id"]
                assert exchange["server_process_instance_id"] == instances[server_side]["server_process_instance_id"]
                assert exchange["request_origin"] == "participant_client"
                assert exchange["response_origin"] == "participant_server"
                assert exchange["request_json"] == exchange["forwarded_request_json"]
                assert exchange["response_json"] == exchange["delivered_response_json"]
            proposal, acceptance, attestation = direction["messages"]
            assert proposal["message"]["payload"]["contract"]["goal"] == direction["challenge"]
            for evidence, consuming_side in (
                (proposal, consumer),
                (acceptance, producer),
                (attestation, consumer),
            ):
                assert evidence["client_visible_hashes_before"] == visible[consuming_side]
                visible[consuming_side] = [
                    *visible[consuming_side],
                    evidence["message"]["message_hash"],
                ]
                assert evidence["client_visible_hashes_after"] == visible[consuming_side]
            assert acceptance["message"]["prev_msg_hash"] == proposal["message"]["message_hash"]
            assert attestation["message"]["prev_msg_hash"] == acceptance["message"]["message_hash"]
            assert attestation["consume_exchange_sequence"] == 6
    assert semantic_digests[0] == semantic_digests[1]


@pytest.mark.parametrize(
    "mutation",
    (
        "future_pairwise_target",
        "future_pairwise_scenario",
        "future_pairwise_release",
        "unrelated_registry_reordering",
        "future_top_level_registry_schema",
    ),
)
def test_future_current_registry_changes_do_not_invalidate_1_3(mutation: str, tmp_path: Path) -> None:
    isolated_root, isolated_pairwise = _copy_isolated_pairwise(tmp_path)
    if mutation == "future_pairwise_target":
        path = isolated_pairwise / "targets.json"
        value = _load(path)
        value["targets"].append({"target_id": "FUTURE-UNRELATED@9.9"})
    elif mutation == "future_pairwise_scenario":
        path = isolated_pairwise / "scenarios.json"
        value = _load(path)
        value["future_scenarios"] = [{"scenario_id": "PAIRWISE-FUTURE-UNRELATED-99"}]
    elif mutation == "future_top_level_registry_schema":
        path = isolated_pairwise / "tck_releases_v4.schema.json"
        value = _load(path)
        value["title"] = "future mutable top-level schema"
    else:
        path = isolated_pairwise / "tck_releases.json"
        value = _load(path)
        if mutation == "future_pairwise_release":
            future = json.loads(json.dumps(value["releases"][-1]))
            future["release_id"] = "AICP-PAIRWISE-TCK-9.9.9"
            value["releases"].append(future)
            value["release_policies"].append(
                {"release_id": future["release_id"], "lifecycle": "historical", "strong_eligible": False, "reason": "hypothetical"}
            )
        else:
            value["releases"] = list(reversed(value["releases"][:-1])) + [value["releases"][-1]]
            value["release_policies"] = list(reversed(value["release_policies"][:-1])) + [value["release_policies"][-1]]
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    result = _dispatch_isolated(isolated_root, isolated_pairwise)
    assert result["status"] == "eligible", (mutation, result)


@pytest.mark.parametrize(
    "relative",
    (
        "pairwise_joint_report_v1_3.schema.json",
        "pairwise_report_evaluator_v1_3.py",
        "pairwise_semantic_normalizer_v1_3.py",
        "release_artifacts/AICP-PAIRWISE-TCK-1.3.0/targets.json",
        "release_artifacts/AICP-PAIRWISE-TCK-1.3.0/scenarios.json",
        "release_artifacts/AICP-PAIRWISE-TCK-1.3.0/tck_releases_v4.schema.json",
        "release_artifacts/AICP-PAIRWISE-TCK-1.1.0/authority_root/pairwise_side_authorities.json",
    ),
)
def test_immutable_1_3_artifact_or_reused_authority_mutation_fails_closed(relative: str, tmp_path: Path) -> None:
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
    assert frozen_hash("message", message)["message_hash"] == message_hash_from_body(message)


def test_runner_bundle_matches_runtime_import_closure() -> None:
    verify_runner_bundle()
    manifest = _load(PAIRWISE / "pairwise_runner_bundle_v1_3.json")
    discovered = {
        path.relative_to(ROOT).as_posix()
        for path in discover_import_closure([PAIRWISE / "aicp_pairwise_runner_v1_3.py"])
    }
    assert {item["path"] for item in manifest["entries"]} == discovered


def test_no_genuine_external_pairwise_adoption() -> None:
    real_pairwise: list[Path] = []
    submissions = ROOT / "interop" / "submissions"
    for manifest_path in submissions.rglob("submission.json"):
        relative_parts = manifest_path.relative_to(submissions).parts
        if {"examples", "templates"}.intersection(relative_parts) or any(part.startswith("dryrun-") for part in relative_parts):
            continue
        manifest = _load(manifest_path)
        if manifest.get("claim_type") == "pairwise_interop" and manifest.get("evidence_status") == "pairwise":
            real_pairwise.append(manifest_path)
    assert real_pairwise == []
