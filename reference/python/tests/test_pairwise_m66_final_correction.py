from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable

import pytest


ROOT = Path(__file__).resolve().parents[3]
PAIRWISE = ROOT / "interop" / "pairwise"
VECTOR = PAIRWISE / "current_vectors" / "AICP-PAIRWISE-TCK-1.3.0"
for path in (PAIRWISE, ROOT / "scripts"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import pairwise_release_router as router  # noqa: E402
from generate_pairwise_tck import (  # noqa: E402
    FROZEN_1_0_REPOSITORY_SHA256,
    FROZEN_1_1_REPOSITORY_SHA256,
    FROZEN_1_2_REPOSITORY_SHA256,
    discover_process_import_closure,
    repository_sha256,
)
from interop_submission_validation import evaluate_strong_report_evidence  # noqa: E402
from pairwise_report_evaluator_v1_3 import evaluate_pairwise_report  # noqa: E402
from pairwise_semantic_normalizer_v1_3 import semantic_digest  # noqa: E402


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture()
def package(tmp_path: Path) -> Path:
    for name in ("a-profile.json", "a-binding.json", "b-profile.json", "b-binding.json", "joint.json"):
        shutil.copy2(VECTOR / name, tmp_path / name)
    return tmp_path


def _evaluate(package: Path, report: dict[str, Any]) -> dict[str, Any]:
    result = evaluate_pairwise_report(report, base_dir=package)
    assert result["eligible_pairwise_relations"] == []
    assert result["eligible_marks"] == []
    return result


def _descriptor_mutation(case: str, report: dict[str, Any]) -> None:
    participant = report["participants"][0]
    client = participant["client_descriptor_evidence"]
    server = participant["server_descriptor_evidence"]
    if case == "raw_client_run_1_id":
        client["runs"][0]["response"]["result"]["implementation_id"] = "substituted-client-build"
    elif case == "raw_client_run_2_digest":
        client["runs"][1]["response"]["result"]["implementation_digest"] = "sha256:" + "0" * 64
    elif case == "raw_server_run_1_id":
        server["runs"][0]["descriptor"]["implementation_id"] = "substituted-server-build"
    elif case == "raw_server_run_2_digest":
        server["runs"][1]["descriptor"]["implementation_digest"] = "sha256:" + "0" * 64
    elif case == "summary_raw_contradiction":
        client["descriptor"]["implementation_id"] = "summary-only-build"
    elif case == "client_changes_between_runs":
        client["runs"][1]["response"]["result"]["implementation_version"] = "different-run-build"
    elif case == "server_changes_between_runs":
        server["runs"][1]["descriptor"]["implementation_version"] = "different-run-build"
    elif case == "wrong_run_id":
        client["runs"][0]["run_id"] = "run-unknown-000000000000"
    elif case == "wrong_process_instance":
        server["runs"][0]["process_instance_id"] = "proc-wrong-000000000000"
    elif case == "duplicate_raw_record":
        client["runs"][1] = copy.deepcopy(client["runs"][0])
    elif case == "missing_raw_record":
        server["runs"].pop()
    else:
        raise AssertionError(case)


@pytest.mark.parametrize(
    "case",
    (
        "raw_client_run_1_id",
        "raw_client_run_2_digest",
        "raw_server_run_1_id",
        "raw_server_run_2_digest",
        "summary_raw_contradiction",
        "client_changes_between_runs",
        "server_changes_between_runs",
        "wrong_run_id",
        "wrong_process_instance",
        "duplicate_raw_record",
        "missing_raw_record",
    ),
)
def test_raw_role_evidence_is_independently_load_bearing(case: str, package: Path) -> None:
    report = _load(package / "joint.json")
    _descriptor_mutation(case, report)
    result = _evaluate(package, report)
    assert result["status"] == "rejected", (case, result)
    assert any(
        item["code"].startswith("PAIRWISE_RAW_")
        or item["code"] in {"PAIRWISE_ROLE_SUMMARY_NOT_DERIVED", "PAIRWISE_CLIENT_SERVER_BUILD_MISMATCH"}
        for item in result["errors"]
    )


def _future_value(report: dict[str, Any], field: str) -> str:
    future = report["runs"][0]["directions"][1]
    if field == "hash":
        return future["messages"][0]["message"]["message_hash"]
    return future["challenge"]


@pytest.mark.parametrize(
    ("field", "expected_code"),
    (
        ("hash", "PAIRWISE_CLIENT_ARTIFACT_PRESEEDED"),
        ("challenge", "PAIRWISE_CONSUMER_CHALLENGE_PRESEEDED"),
    ),
)
def test_cross_direction_future_value_preseed_is_rejected_by_run_global_ledger(
    field: str, expected_code: str, package: Path
) -> None:
    report = _load(package / "joint.json")
    run = report["runs"][0]
    earlier_a_event = next(
        event
        for event in run["directions"][0]["client_events"]
        if event["client_side"] == "A"
        and event["request"]["operation"] == "begin_phase"
    )
    earlier_a_event["response"]["result"]["client_visible_hashes_before"].append(
        _future_value(report, field)
    )
    run["semantic_digest"] = semantic_digest(run)
    result = _evaluate(package, report)
    assert result["status"] == "rejected"
    assert expected_code in {item["code"] for item in result["errors"]}


@pytest.mark.parametrize("mutation", ("duplicate", "missing"))
def test_global_event_sequence_must_be_exact_and_contiguous(mutation: str, package: Path) -> None:
    report = _load(package / "joint.json")
    events = report["runs"][0]["directions"][0]["client_events"]
    events[1]["global_event_sequence"] = (
        events[0]["global_event_sequence"] if mutation == "duplicate" else 99
    )
    report["runs"][0]["semantic_digest"] = semantic_digest(report["runs"][0])
    result = _evaluate(package, report)
    assert result["status"] == "rejected"
    assert "PAIRWISE_GLOBAL_EVENT_SEQUENCE_INVALID" in {item["code"] for item in result["errors"]}


def _compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _digest_text(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _mutate_poll_request(report: dict[str, Any], mutate: Callable[[dict[str, Any]], None]) -> None:
    run = report["runs"][0]
    direction = run["directions"][0]
    exchange = next(item for item in direction["exchanges"] if item["phase"] == "poll_attestation")
    request = copy.deepcopy(exchange["request"])
    mutate(request["params"]["arguments"])
    request_json = _compact(request)
    exchange["client_request"] = copy.deepcopy(request)
    exchange["request"] = copy.deepcopy(request)
    exchange["request_json"] = request_json
    exchange["forwarded_request_json"] = request_json
    exchange["request_byte_digest"] = _digest_text(request_json)
    begin = next(
        event
        for event in direction["client_events"]
        if event["request"]["operation"] == "begin_phase"
        and event["request"]["input"]["phase"] == "poll_attestation"
    )
    begin["response"]["result"]["request"] = copy.deepcopy(request)
    begin["response"]["result"]["request_json"] = request_json
    run["semantic_digest"] = semantic_digest(run)


@pytest.mark.parametrize(
    ("case", "mutate"),
    (
        ("stale_final_cursor", lambda args: args.__setitem__("after_cursor", "stale-cursor")),
        ("hardcoded_c0_final_cursor", lambda args: args.__setitem__("after_cursor", "c0")),
        ("unrelated_cursor", lambda args: args.__setitem__("after_cursor", "unrelated-cursor")),
        ("missing_limit", lambda args: args.pop("limit")),
        ("wrong_limit", lambda args: args.__setitem__("limit", 2)),
        ("wrong_session", lambda args: args.__setitem__("session_id", "wrong-session")),
    ),
)
def test_exact_poll_cursor_progression_rejects_mutations(
    case: str, mutate: Callable[[dict[str, Any]], None], package: Path
) -> None:
    report = _load(package / "joint.json")
    _mutate_poll_request(report, mutate)
    result = _evaluate(package, report)
    assert result["status"] == "rejected", (case, result)
    assert "PAIRWISE_CLIENT_POLL_RESULT_INVALID" in {item["code"] for item in result["errors"]}


def _future_registry(path: Path) -> None:
    value = _load(PAIRWISE / "tck_releases.json")
    release_1_3 = value["releases"][-1]
    policy_1_3 = value["release_policies"][-1]
    policy_1_3["lifecycle"] = "historical"
    future = copy.deepcopy(release_1_3)
    future["release_id"] = "AICP-PAIRWISE-TCK-1.4.0"
    value["releases"].append(future)
    value["release_policies"].append(
        {
            "release_id": "AICP-PAIRWISE-TCK-1.4.0",
            "lifecycle": "current",
            "strong_eligible": True,
            "reason": "hypothetical future-release simulation",
        }
    )
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _manifest(report: dict[str, Any]) -> dict[str, Any]:
    primary, peer = report["participants"]
    return {
        "submission_id": "m66-final-historical-test",
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


def test_historical_strong_eligible_1_3_survives_future_1_4_low_and_public_paths(
    package: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry = tmp_path / "future-registry.json"
    _future_registry(registry)
    report = _load(package / "joint.json")
    low = router.evaluate_pairwise_report(report, base_dir=package, registry_path=registry)
    assert low["status"] == "eligible", low
    monkeypatch.setattr(router, "REGISTRY_PATH", registry)
    public = evaluate_strong_report_evidence(package / "submission.json", _manifest(report))
    assert public.status == "eligible", public.errors
    assert len(public.eligible_pairwise_relations) == 1


def _isolated_pairwise(tmp_path: Path) -> tuple[Path, Path]:
    isolated_root = tmp_path / "isolated"
    isolated_pairwise = isolated_root / "interop" / "pairwise"
    shutil.copytree(PAIRWISE, isolated_pairwise, ignore=shutil.ignore_patterns("__pycache__"))
    return isolated_root, isolated_pairwise


def _isolated_result(root: Path, pairwise: Path) -> dict[str, Any]:
    joint = pairwise / "current_vectors" / "AICP-PAIRWISE-TCK-1.3.0" / "joint.json"
    result = subprocess.run(
        [sys.executable, str(pairwise / "pairwise_release_router.py"), str(joint)],
        cwd=root,
        text=True,
        capture_output=True,
        shell=False,
        timeout=120,
    )
    assert result.stdout, result.stderr
    return json.loads(result.stdout)


def test_unrelated_current_source_mutation_does_not_invalidate_1_3(tmp_path: Path) -> None:
    root, pairwise = _isolated_pairwise(tmp_path)
    unrelated = root / "conformance" / "evidence" / "live_bindings" / "live_http_capture.py"
    unrelated.parent.mkdir(parents=True, exist_ok=True)
    unrelated.write_text("# unrelated mutable current source mutation\n", encoding="utf-8")
    assert _isolated_result(root, pairwise)["status"] == "eligible"


def test_actual_frozen_authority_mutation_invalidates_1_3(tmp_path: Path) -> None:
    root, pairwise = _isolated_pairwise(tmp_path)
    authority = (
        pairwise
        / "release_artifacts"
        / "AICP-PAIRWISE-TCK-1.1.0"
        / "authority_root"
        / "pairwise_side_authorities.json"
    )
    authority.write_text(authority.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    result = _isolated_result(root, pairwise)
    assert result["status"] == "rejected"
    assert result["eligible_pairwise_relations"] == []


def test_release_specific_evaluator_closure_excludes_mutable_router_and_current_sources() -> None:
    bundle = _load(PAIRWISE / "pairwise_evaluator_bundle_v1_3.json")
    paths = {item["path"] for item in bundle["entries"]}
    assert paths == {
        "interop/pairwise/pairwise_report_evaluator_v1_3.py",
        "interop/pairwise/pairwise_semantic_normalizer_v1_3.py",
        "interop/pairwise/pairwise_side_authority_client_v1_3.py",
    }
    assert "interop/pairwise/pairwise_release_router.py" not in paths
    assert "interop/pairwise/pairwise_report_dispatcher.py" not in paths
    assert not any(path.startswith(("conformance/", "reference/")) for path in paths)


def test_side_authority_bundle_matches_frozen_subprocess_import_and_data_roots() -> None:
    bundle = _load(PAIRWISE / "pairwise_side_authority_bundle_v1_3.json")
    code_paths = {
        item["path"]
        for item in bundle["entries"]
        if item["role"] != "shared_content_addressed_1_1_authority_data"
    }
    authority_root = PAIRWISE / "release_artifacts" / "AICP-PAIRWISE-TCK-1.1.0" / "authority_root"
    discovered = {
        path.relative_to(ROOT).as_posix()
        for path in discover_process_import_closure(
            [PAIRWISE / "pairwise_authority_bridge_v1_3.py"],
            (
                authority_root / "conformance" / "runner",
                authority_root / "conformance" / "evidence",
                authority_root / "reference" / "python",
                authority_root / "interop" / "pairwise",
                authority_root,
            ),
        )
    }
    assert code_paths == discovered
    assert not any(path.endswith("pairwise_report_dispatcher.py") for path in code_paths)
    assert any(
        item["path"].endswith("pairwise_side_authorities.json")
        and item["role"] == "shared_content_addressed_1_1_authority_data"
        for item in bundle["entries"]
    )


def _isolated_runner_check(root: Path, pairwise: Path) -> subprocess.CompletedProcess[str]:
    expression = (
        "import sys; "
        f"sys.path.insert(0, {str(pairwise)!r}); "
        "from aicp_pairwise_runner_v1_3 import verify_runner_bundle; "
        "verify_runner_bundle()"
    )
    return subprocess.run(
        [sys.executable, "-c", expression],
        cwd=root,
        text=True,
        capture_output=True,
        shell=False,
        timeout=60,
    )


def test_runner_closure_ignores_unrelated_current_source_but_rejects_actual_dependency(
    tmp_path: Path,
) -> None:
    root, pairwise = _isolated_pairwise(tmp_path)
    unrelated = root / "conformance" / "evidence" / "live_bindings" / "live_http_capture.py"
    unrelated.parent.mkdir(parents=True, exist_ok=True)
    unrelated.write_text("# unrelated current mutation\n", encoding="utf-8")
    clean = _isolated_runner_check(root, pairwise)
    assert clean.returncode == 0, clean.stdout + clean.stderr
    dependency = pairwise / "pairwise_semantic_normalizer_v1_3.py"
    dependency.write_text(dependency.read_text(encoding="utf-8") + "\n# drift\n", encoding="utf-8")
    drift = _isolated_runner_check(root, pairwise)
    assert drift.returncode != 0
    assert "import closure differs" in drift.stderr


@pytest.mark.parametrize(
    ("release_id", "frozen"),
    (
        ("AICP-PAIRWISE-TCK-1.0.0", FROZEN_1_0_REPOSITORY_SHA256),
        ("AICP-PAIRWISE-TCK-1.1.0", FROZEN_1_1_REPOSITORY_SHA256),
        ("AICP-PAIRWISE-TCK-1.2.0", FROZEN_1_2_REPOSITORY_SHA256),
    ),
)
def test_all_issued_pairwise_release_bytes_remain_frozen(
    release_id: str, frozen: dict[str, str]
) -> None:
    assert frozen, release_id
    for relative, expected in frozen.items():
        assert repository_sha256(ROOT / relative) == expected, relative
