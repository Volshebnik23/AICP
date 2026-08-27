from __future__ import annotations

import copy
import json
import shutil
import subprocess
import sys
import types
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[3]
PAIRWISE = ROOT / "interop" / "pairwise"
if str(PAIRWISE) not in sys.path:
    sys.path.insert(0, str(PAIRWISE))

import pairwise_report_evaluator as historical_evaluator  # noqa: E402


def _run(command: list[str], *, timeout: int = 120) -> None:
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        shell=False,
        timeout=timeout,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def _command_json(command: list[str]) -> str:
    return json.dumps(command)


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def correction_side_reports(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    output = tmp_path_factory.mktemp("m66-correction-reproduction")
    node = shutil.which("node")
    assert node is not None
    peer_a = PAIRWISE / "cleanroom" / "peer_a" / "peer_a.py"
    peer_b = PAIRWISE / "cleanroom" / "peer_b" / "peer_b.mjs"
    paths = {
        "a_profile": output / "a-profile.json",
        "a_binding": output / "a-binding.json",
        "b_profile": output / "b-profile.json",
        "b_binding": output / "b-binding.json",
    }
    for side, command in (
        ("a", [sys.executable, str(peer_a)]),
        ("b", [node, str(peer_b)]),
    ):
        _run(
            [
                sys.executable,
                "conformance/iut/aicp_iut_runner.py",
                "--cmd-json",
                _command_json([*command, "iut"]),
                "--profile",
                "AICP-BASE@0.1",
                "--mode",
                "full-profile",
                "--out",
                str(paths[f"{side}_profile"]),
            ]
        )
        _run(
            [
                sys.executable,
                "conformance/evidence/aicp_live_binding_runner.py",
                "--target",
                "BIND-MCP@0.1",
                "--server-cmd-json",
                _command_json([*command, "binding-server"]),
                "--client-cmd-json",
                _command_json([*command, "binding-client"]),
                "--mode",
                "full-binding",
                "--out",
                str(paths[f"{side}_binding"]),
            ]
        )
    return {"node": node, "peer_a": peer_a, "peer_b": peer_b, "paths": paths, "output": output}


def _historical_joint(
    fixture: dict[str, Any],
    *,
    behavior: str,
    output: Path,
) -> dict[str, Any]:
    paths = fixture["paths"]
    _run(
        [
            sys.executable,
            "interop/pairwise/aicp_pairwise_runner.py",
            "--peer-a-control-cmd-json",
            _command_json([sys.executable, str(fixture["peer_a"]), "pairwise-control", "--behavior", behavior]),
            "--peer-a-server-cmd-json",
            _command_json([sys.executable, str(fixture["peer_a"]), "pairwise-server"]),
            "--peer-a-profile-report",
            str(paths["a_profile"]),
            "--peer-a-binding-report",
            str(paths["a_binding"]),
            "--peer-b-control-cmd-json",
            _command_json([fixture["node"], str(fixture["peer_b"]), "pairwise-control"]),
            "--peer-b-server-cmd-json",
            _command_json([fixture["node"], str(fixture["peer_b"]), "pairwise-server"]),
            "--peer-b-profile-report",
            str(paths["b_profile"]),
            "--peer-b-binding-report",
            str(paths["b_binding"]),
            "--out",
            str(output),
        ]
    )
    return _load(output)


@pytest.mark.parametrize(
    "behavior",
    ("missing_contract_goal", "malformed_contract_ref", "ignore_challenge"),
)
def test_historical_1_0_reproduces_actual_traffic_bypasses(
    behavior: str,
    correction_side_reports: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    joint_path = correction_side_reports["output"] / f"{behavior}.json"
    joint = _historical_joint(correction_side_reports, behavior=behavior, output=joint_path)
    copied_root, copied_pairwise = _copy_historical_authority(tmp_path)
    monkeypatch.setattr(historical_evaluator, "ROOT", copied_root)
    monkeypatch.setattr(historical_evaluator, "HERE", copied_pairwise)
    result = historical_evaluator.evaluate_pairwise_report(
        joint,
        base_dir=joint_path.parent,
        profile_validator=lambda *args, **kwargs: [],
    )
    assert result["status"] == "rejected", (behavior, result["errors"])
    assert {
        item["code"] for item in result["errors"]
    } == {"PAIRWISE_TCK_UNDERLYING_AUTHORITY_DRIFT"}
    proposal = joint["runs"][0]["directions"][0]["messages"][0]["message"]
    if behavior == "missing_contract_goal":
        assert "goal" not in proposal["payload"]["contract"]
    elif behavior == "malformed_contract_ref":
        assert proposal["contract_ref"] == {"branch_id": "main"}
    else:
        assert proposal["payload"]["contract"]["goal"] != joint["runs"][0]["challenge"]


def _copy_historical_authority(destination: Path) -> tuple[Path, Path]:
    copied_root = destination / "repo"
    copied_pairwise = copied_root / "interop" / "pairwise"
    shutil.copytree(PAIRWISE, copied_pairwise)
    vector = PAIRWISE / "historical_vectors" / "AICP-PAIRWISE-TCK-1.0.0"
    shutil.copy2(vector / "issued-targets.json", copied_pairwise / "targets.json")
    shutil.copy2(vector / "issued-scenarios.json", copied_pairwise / "scenarios.json")
    snapshot = _load(PAIRWISE / "release_registry_snapshots" / "AICP-PAIRWISE-TCK-1.0.0.json")
    release = snapshot["releases"][0]
    refs = [item["path"] for item in release["underlying_authorities"]]
    refs.append(release["runner_bundle"]["path"])
    bundle = _load(ROOT / release["runner_bundle"]["path"])
    refs.extend(item["path"] for item in bundle["entries"])
    for ref in sorted(set(refs)):
        source = ROOT / ref
        target = copied_root / ref
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    return copied_root, copied_pairwise


@pytest.mark.parametrize(
    ("registry_ref", "collection"),
    (
        ("conformance/evidence/evidence_tck_releases.json", "releases"),
        ("conformance/evidence/targets.json", "targets"),
    ),
)
def test_historical_1_0_reproduces_mutable_current_registry_dependency(
    registry_ref: str,
    collection: str,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    copied_root, copied_pairwise = _copy_historical_authority(tmp_path)
    target = copied_root / registry_ref
    value = _load(target)
    value[collection].append({"future_only": "unrelated-hypothetical-entry"})
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    vector_dir = PAIRWISE / "historical_vectors" / "AICP-PAIRWISE-TCK-1.0.0"
    report = _load(vector_dir / "joint.json")
    monkeypatch.setattr(historical_evaluator, "ROOT", copied_root)
    monkeypatch.setattr(historical_evaluator, "HERE", copied_pairwise)
    result = historical_evaluator.evaluate_pairwise_report(
        report,
        base_dir=vector_dir,
        profile_validator=lambda *args, **kwargs: [],
    )
    assert result["status"] == "rejected"
    assert any(item["code"] == "PAIRWISE_TCK_UNDERLYING_AUTHORITY_DRIFT" for item in result["errors"])


def test_historical_1_0_reproduces_mutable_side_evaluator_dependencies(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    vector_dir = PAIRWISE / "historical_vectors" / "AICP-PAIRWISE-TCK-1.0.0"
    report = _load(vector_dir / "joint.json")
    unchanged_joint = copy.deepcopy(report)

    fake_public = types.ModuleType("interop_submission_validation")
    fake_public._eligible_external_profile_report = lambda *args, **kwargs: ["substituted Base evaluator"]  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "interop_submission_validation", fake_public)
    profile_changed = historical_evaluator.evaluate_pairwise_report(report, base_dir=vector_dir)
    assert profile_changed["status"] == "rejected"
    assert any(item["code"] == "PAIRWISE_PROFILE_REPORT_INELIGIBLE" for item in profile_changed["errors"])

    monkeypatch.setattr(
        historical_evaluator,
        "evaluate_binding_report",
        lambda *args, **kwargs: {"status": "rejected", "errors": ["substituted binding evaluator"], "eligible_targets": []},
    )
    binding_changed = historical_evaluator.evaluate_pairwise_report(
        report,
        base_dir=vector_dir,
        profile_validator=lambda *args, **kwargs: [],
    )
    assert binding_changed["status"] == "rejected"
    assert any(item["code"] == "PAIRWISE_BINDING_REPORT_INELIGIBLE" for item in binding_changed["errors"])
    assert report == unchanged_joint
