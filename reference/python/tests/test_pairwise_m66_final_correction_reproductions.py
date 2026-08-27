from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
PAIRWISE = ROOT / "interop" / "pairwise"
ISSUED_VECTOR = PAIRWISE / "current_vectors" / "AICP-PAIRWISE-TCK-1.2.0"
if str(PAIRWISE) not in sys.path:
    sys.path.insert(0, str(PAIRWISE))

from pairwise_report_evaluator_v1_2 import evaluate_pairwise_report as evaluate_issued_1_2  # noqa: E402


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _issued_report() -> dict[str, Any]:
    return _load(ISSUED_VECTOR / "joint.json")


def _assert_issued_evaluator_still_accepts(report: dict[str, Any]) -> None:
    result = evaluate_issued_1_2(report, base_dir=ISSUED_VECTOR)
    assert result["status"] == "eligible", result
    assert len(result["eligible_pairwise_relations"]) == 1
    assert result["eligible_marks"] == []


def _copy_issued_runtime(tmp_path: Path) -> tuple[Path, Path]:
    isolated_root = tmp_path / "repo"
    isolated_pairwise = isolated_root / "interop" / "pairwise"
    shutil.copytree(PAIRWISE, isolated_pairwise, ignore=shutil.ignore_patterns("__pycache__"))
    bundle = _load(PAIRWISE / "pairwise_evaluator_bundle_v1_2.json")
    for entry in bundle["entries"]:
        relative = Path(entry["path"])
        if relative.parts[:2] == ("interop", "pairwise"):
            continue
        destination = isolated_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, destination)
    return isolated_root, isolated_pairwise


def _dispatch_issued(isolated_root: Path, isolated_pairwise: Path) -> dict[str, Any]:
    joint = isolated_pairwise / "current_vectors" / "AICP-PAIRWISE-TCK-1.2.0" / "joint.json"
    completed = subprocess.run(
        [sys.executable, str(isolated_pairwise / "pairwise_report_dispatcher.py"), str(joint)],
        cwd=isolated_root,
        text=True,
        capture_output=True,
        shell=False,
        timeout=120,
    )
    assert completed.stdout, completed.stderr
    return json.loads(completed.stdout)


def _evaluate_issued_isolated(isolated_root: Path, isolated_pairwise: Path) -> dict[str, Any]:
    joint = isolated_pairwise / "current_vectors" / "AICP-PAIRWISE-TCK-1.2.0" / "joint.json"
    completed = subprocess.run(
        [sys.executable, str(isolated_pairwise / "pairwise_report_evaluator_v1_2.py"), str(joint)],
        cwd=isolated_root,
        text=True,
        capture_output=True,
        shell=False,
        timeout=120,
    )
    assert completed.stdout, completed.stderr
    return json.loads(completed.stdout)


def test_issued_1_2_reproduces_raw_client_descriptor_summary_trust() -> None:
    report = _issued_report()
    participant_a = next(item for item in report["participants"] if item["side"] == "A")
    participant_a["client_descriptor_evidence"]["runs"][0]["response"]["result"][
        "implementation_id"
    ] = "substituted-client-build"

    _assert_issued_evaluator_still_accepts(report)


def test_issued_1_2_reproduces_raw_server_descriptor_summary_trust() -> None:
    report = _issued_report()
    participant_b = next(item for item in report["participants"] if item["side"] == "B")
    participant_b["server_descriptor_evidence"]["runs"][0]["descriptor"][
        "implementation_id"
    ] = "substituted-server-build"

    _assert_issued_evaluator_still_accepts(report)


def _preseed_future_direction_value(report: dict[str, Any], *, value_kind: str) -> None:
    for run in report["runs"]:
        directions = {item["direction"]: item for item in run["directions"]}
        earlier = directions["A_TO_B"]
        future = directions["B_TO_A"]
        if value_kind == "peer_hash":
            value = future["messages"][0]["message"]["message_hash"]
        else:
            value = future["challenge"]
        event = next(
            item
            for item in earlier["client_events"]
            if item["client_side"] == "A" and item["request"]["operation"] == "begin_phase"
        )
        event["request"]["input"]["future_answer"] = value


def test_issued_1_2_reproduces_cross_direction_future_peer_hash_preseed() -> None:
    report = _issued_report()
    _preseed_future_direction_value(report, value_kind="peer_hash")

    _assert_issued_evaluator_still_accepts(report)


def test_issued_1_2_reproduces_cross_direction_future_challenge_preseed() -> None:
    report = _issued_report()
    _preseed_future_direction_value(report, value_kind="challenge")

    _assert_issued_evaluator_still_accepts(report)


def test_issued_1_2_reproduces_historical_transition_rejection(tmp_path: Path) -> None:
    isolated_root, isolated_pairwise = _copy_issued_runtime(tmp_path)
    registry_path = isolated_pairwise / "tck_releases.json"
    registry = _load(registry_path)
    policy_1_2 = next(
        item
        for item in registry["release_policies"]
        if item["release_id"] == "AICP-PAIRWISE-TCK-1.2.0"
    )
    policy_1_2["lifecycle"] = "historical"
    policy_1_2["strong_eligible"] = True
    future_release = copy.deepcopy(registry["releases"][-1])
    future_release["release_id"] = "AICP-PAIRWISE-TCK-1.3.0-hypothetical"
    registry["releases"].append(future_release)
    registry["release_policies"].append(
        {
            "release_id": future_release["release_id"],
            "lifecycle": "current",
            "strong_eligible": True,
            "reason": "hypothetical future current release",
        }
    )
    registry_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")

    result = _dispatch_issued(isolated_root, isolated_pairwise)
    assert result["status"] == "rejected", result
    assert result["errors"][0]["code"] == "PAIRWISE_RELEASE_POLICY_INVALID"
    assert result["eligible_pairwise_relations"] == []
    assert result["eligible_marks"] == []


def test_issued_1_2_reproduces_false_mutable_source_dependency(tmp_path: Path) -> None:
    isolated_root, isolated_pairwise = _copy_issued_runtime(tmp_path)
    unrelated = isolated_root / "conformance" / "evidence" / "live_bindings" / "live_http_capture.py"
    unrelated.write_text(unrelated.read_text(encoding="utf-8") + "\n# unrelated current mutation\n", encoding="utf-8")

    result = _evaluate_issued_isolated(isolated_root, isolated_pairwise)
    assert result["status"] == "rejected", result
    assert any(item["code"] == "PAIRWISE_RELEASE_ARTIFACT_DRIFT" for item in result["errors"])
    assert result["eligible_pairwise_relations"] == []
    assert result["eligible_marks"] == []
