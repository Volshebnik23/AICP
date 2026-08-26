from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[3]
PAIRWISE = ROOT / "interop" / "pairwise"
for path in (PAIRWISE, ROOT / "scripts", ROOT / "reference" / "python"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import aicp_pairwise_runner_v1_1 as issued_runner  # noqa: E402
from pairwise_report_evaluator_v1_1 import evaluate_pairwise_report as evaluate_issued_report  # noqa: E402


def _command_json(command: list[str]) -> str:
    return json.dumps(command)


def _run(command: list[str], *, timeout: int = 180) -> None:
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        shell=False,
        timeout=timeout,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.fixture(scope="session")
def role_reproduction_side_reports(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Any]:
    output = tmp_path_factory.mktemp("m66-role-binding-reproduction")
    node = shutil.which("node")
    assert node is not None
    peer_a = PAIRWISE / "cleanroom" / "peer_a" / "peer_a.py"
    peer_b = PAIRWISE / "cleanroom" / "peer_b" / "peer_b.mjs"
    reports: dict[str, Path] = {}
    for side, command in (("a", [sys.executable, str(peer_a)]), ("b", [node, str(peer_b)])):
        reports[f"{side}_profile"] = output / f"{side}-profile.json"
        reports[f"{side}_binding"] = output / f"{side}-binding.json"
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
                str(reports[f"{side}_profile"]),
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
                str(reports[f"{side}_binding"]),
            ]
        )
    return {"node": node, "peer_a": peer_a, "peer_b": peer_b, "reports": reports}


def _issued_args(
    fixture: dict[str, Any],
    destination: Path,
    *,
    substitute_b_server: bool = False,
) -> argparse.Namespace:
    destination.mkdir(parents=True, exist_ok=True)
    for side in ("a", "b"):
        for kind in ("profile", "binding"):
            shutil.copy2(fixture["reports"][f"{side}_{kind}"], destination / f"{side}-{kind}.json")
    peer_a = fixture["peer_a"]
    peer_b = fixture["peer_b"]
    node = fixture["node"]
    b_server = [sys.executable, str(peer_a), "pairwise-server"] if substitute_b_server else [node, str(peer_b), "pairwise-server"]
    return argparse.Namespace(
        peer_a_control_cmd_json=_command_json([sys.executable, str(peer_a), "pairwise-control"]),
        peer_a_server_cmd_json=_command_json([sys.executable, str(peer_a), "pairwise-server"]),
        peer_a_profile_report=str(destination / "a-profile.json"),
        peer_a_binding_report=str(destination / "a-binding.json"),
        peer_b_control_cmd_json=_command_json([node, str(peer_b), "pairwise-control"]),
        peer_b_server_cmd_json=_command_json(b_server),
        peer_b_profile_report=str(destination / "b-profile.json"),
        peer_b_binding_report=str(destination / "b-binding.json"),
        out=str(destination / "joint.json"),
    )


def _mode(command: tuple[str, ...]) -> str:
    return next(
        (item for item in command if item in {"pairwise-control", "pairwise-server", "pairwise-client"}),
        "unknown",
    )


def test_issued_1_1_runner_is_the_actual_mcp_client_and_starts_no_peer_clients(
    role_reproduction_side_reports: dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    launched: list[tuple[str, ...]] = []
    exchanges: list[tuple[tuple[str, ...], dict[str, Any]]] = []
    constructed_by_runner: list[dict[str, Any]] = []
    original_process = issued_runner.JsonLineProcess
    original_rpc = issued_runner.rpc

    class ObservedProcess:
        def __init__(self, command: list[str], **kwargs: Any):
            self.command = tuple(command)
            launched.append(self.command)
            self.inner = original_process(command, **kwargs)

        def exchange(self, request: dict[str, Any]) -> dict[str, Any]:
            exchanges.append((self.command, request))
            return self.inner.exchange(request)

        def close(self) -> None:
            self.inner.close()

        def abort(self) -> None:
            self.inner.abort()

    def observed_rpc(request_id: str, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
        request = original_rpc(request_id, tool, arguments)
        constructed_by_runner.append(request)
        return request

    monkeypatch.setattr(issued_runner, "JsonLineProcess", ObservedProcess)
    monkeypatch.setattr(issued_runner, "rpc", observed_rpc)
    report = issued_runner.run(_issued_args(role_reproduction_side_reports, tmp_path))

    assert report["passed"] is True
    assert [_mode(command) for command in launched].count("pairwise-control") == 4
    assert [_mode(command) for command in launched].count("pairwise-server") == 4
    assert [_mode(command) for command in launched].count("pairwise-client") == 0
    semantic_requests = [
        request
        for request in constructed_by_runner
        if request.get("params", {}).get("name") in {"aicp.sendMessage", "aicp.pollMessages"}
    ]
    assert len(semantic_requests) == 24
    observed_server_requests = [
        request
        for command, request in exchanges
        if _mode(command) == "pairwise-server"
        and request.get("params", {}).get("name") in {"aicp.sendMessage", "aicp.pollMessages"}
    ]
    assert observed_server_requests == semantic_requests


def test_issued_1_1_accepts_peer_a_server_substituted_for_peer_b(
    role_reproduction_side_reports: dict[str, Any],
    tmp_path: Path,
) -> None:
    args = _issued_args(role_reproduction_side_reports, tmp_path, substitute_b_server=True)
    report = issued_runner.run(args)
    result = evaluate_issued_report(report, base_dir=tmp_path)

    assert report["participants"][0]["implementation_id"] == "aicp-cleanroom-python-a"
    assert report["participants"][1]["implementation_id"] == "aicp-cleanroom-node-b"
    assert result["status"] == "eligible"
    assert len(result["eligible_pairwise_relations"]) == 1
    assert result["eligible_marks"] == []
