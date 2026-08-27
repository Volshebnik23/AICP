#!/usr/bin/env python3
"""Run Pairwise TCK 1.2 with participant-authored MCP traffic and role binding."""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import json
import secrets
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from pairwise_process_v1_2 import JsonLineProcess, ProcessBoundaryError, compact_json  # noqa: E402
from pairwise_semantic_normalizer_v1_2 import semantic_digest  # noqa: E402
from pairwise_side_report_evaluator_v1_1 import evaluate_side_report  # noqa: E402


TARGET_ID = "AICP-BASE@0.1+BIND-MCP@0.1"
SCENARIO_ID = "PAIRWISE-MCP-ROLE-BOUND-CROSS-CONSUMPTION-02"
RELEASE_ID = "AICP-PAIRWISE-TCK-1.2.0"
CLIENT_CONTROL_VERSION = "aicp.pairwise_client_control.v1"
ROLE_DESCRIPTOR_VERSION = "aicp.pairwise_role_descriptor.v1"
TEXT_SUFFIXES = {".json", ".jsonl", ".md", ".py", ".ts", ".mjs", ".yml", ".yaml"}


def canonical_bytes(value: Any) -> bytes:
    return compact_json(value).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix.lower() in TEXT_SUFFIXES:
        data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return sha256_bytes(data)


def load_command(raw: str) -> list[str]:
    value = json.loads(raw)
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item for item in value):
        raise ValueError("commands must be non-empty JSON string arrays")
    return value


def report_ref(path: Path, output: Path) -> dict[str, str]:
    try:
        relative = path.resolve().relative_to(output.resolve().parent).as_posix()
    except ValueError as exc:
        raise ValueError("side reports must be beneath the joint report directory") from exc
    return {"path": relative, "content_digest": sha256_file(path)}


def _module_path(module: str) -> Path | None:
    relative = Path(*module.split("."))
    for root in (HERE, ROOT, ROOT / "reference" / "python"):
        candidate = root / relative.with_suffix(".py")
        if candidate.is_file():
            return candidate.resolve()
        package = root / relative / "__init__.py"
        if package.is_file():
            return package.resolve()
    return None


def _imports(path: Path) -> set[Path]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    result: set[Path] = set()
    for node in ast.walk(tree):
        modules: list[str] = []
        if isinstance(node, ast.Import):
            modules.extend(item.name for item in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules.append(node.module)
        for module in modules:
            resolved = _module_path(module)
            if resolved is not None and resolved.is_relative_to(ROOT):
                result.add(resolved)
    return result


def discover_runner_import_closure(seed: Path | None = None) -> list[Path]:
    pending = [Path(seed or __file__).resolve()]
    discovered: set[Path] = set()
    while pending:
        current = pending.pop()
        if current in discovered:
            continue
        if not current.is_file() or not current.is_relative_to(ROOT):
            raise ProcessBoundaryError(f"runner import closure escaped repository root: {current}")
        discovered.add(current)
        pending.extend(sorted(_imports(current) - discovered))
    return sorted(discovered)


def verify_runner_bundle(*, bundle_path: Path | None = None, seed: Path | None = None) -> None:
    path = Path(bundle_path or HERE / "pairwise_runner_bundle_v1_2.json")
    bundle = json.loads(path.read_text(encoding="utf-8"))
    entries = bundle.get("entries")
    if bundle.get("release_id") != RELEASE_ID or not isinstance(entries, list):
        raise ProcessBoundaryError("Pairwise 1.2 runner bundle is malformed")
    discovered = discover_runner_import_closure(seed)
    actual = {item.relative_to(ROOT).as_posix(): sha256_file(item) for item in discovered}
    expected = {
        item.get("path"): item.get("digest")
        for item in entries
        if isinstance(item, dict) and item.get("role") == "generated_import_closure"
    }
    if actual != expected:
        raise ProcessBoundaryError("runtime Pairwise 1.2 runner import closure differs from its frozen bundle")


def identity_from_report(report: dict[str, Any]) -> dict[str, str]:
    subject = report.get("execution_subject")
    if not isinstance(subject, dict):
        raise ValueError("side report execution_subject is missing")
    identity = {
        "kind": subject.get("kind"),
        "implementation_id": subject.get("implementation_id"),
        "implementation_version": subject.get("implementation_version"),
        "implementation_digest": subject.get("implementation_digest"),
    }
    if not all(isinstance(value, str) and value for value in identity.values()):
        raise ValueError("side report identity is incomplete")
    return identity  # type: ignore[return-value]


def prevalidate_side_reports(
    profile_paths: dict[str, Path],
    binding_paths: dict[str, Path],
) -> tuple[dict[str, dict[str, str]], dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    identities: dict[str, dict[str, str]] = {}
    profiles: dict[str, dict[str, Any]] = {}
    bindings: dict[str, dict[str, Any]] = {}
    for side in ("A", "B"):
        profile = json.loads(profile_paths[side].read_text(encoding="utf-8"))
        binding = json.loads(binding_paths[side].read_text(encoding="utf-8"))
        profile_identity = identity_from_report(profile)
        binding_identity = identity_from_report(binding)
        if profile_identity != binding_identity:
            raise ValueError(f"side {side} profile/binding subjects differ")
        profile_errors = evaluate_side_report(profile, kind="profile", identity=profile_identity)
        binding_errors = evaluate_side_report(binding, kind="binding", identity=profile_identity)
        if profile_errors or binding_errors:
            raise ValueError(f"side {side} evidence is ineligible: {profile_errors + binding_errors}")
        identities[side] = profile_identity
        profiles[side] = profile
        bindings[side] = binding
    if identities["A"]["implementation_id"] == identities["B"]["implementation_id"]:
        raise ValueError("pairwise sides require distinct implementation IDs")
    if identities["A"]["implementation_digest"] == identities["B"]["implementation_digest"]:
        raise ValueError("pairwise sides require distinct implementation digests")
    return identities, profiles, bindings


def client_control(request_id: str, operation: str, input_value: dict[str, Any] | None = None) -> dict[str, Any]:
    request: dict[str, Any] = {
        "control_version": CLIENT_CONTROL_VERSION,
        "request_id": request_id,
        "operation": operation,
    }
    if input_value is not None:
        request["input"] = input_value
    return request


def successful_client_result(
    process: JsonLineProcess,
    request: dict[str, Any],
    *,
    label: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    response = process.exchange(request)
    if (
        response.get("control_version") != CLIENT_CONTROL_VERSION
        or response.get("request_id") != request.get("request_id")
        or response.get("operation") != request.get("operation")
        or response.get("success") is not True
        or not isinstance(response.get("result"), dict)
    ):
        raise ProcessBoundaryError(f"{label} returned an invalid client-control response: {response}")
    return response, response["result"]


def strict_descriptor(value: Any, *, side: str, role: str) -> dict[str, str]:
    required = {
        "protocol",
        "side",
        "role",
        "target_id",
        "implementation_kind",
        "implementation_id",
        "implementation_version",
        "implementation_digest",
        "transport",
    }
    if not isinstance(value, dict) or set(value) != required:
        raise ProcessBoundaryError(f"side {side} {role} descriptor has the wrong shape")
    if (
        value.get("protocol") != ROLE_DESCRIPTOR_VERSION
        or value.get("side") != side
        or value.get("role") != role
        or value.get("target_id") != TARGET_ID
        or value.get("transport") != "stdio"
    ):
        raise ProcessBoundaryError(f"side {side} {role} descriptor has invalid role/target fields")
    for field in ("implementation_kind", "implementation_id", "implementation_version", "implementation_digest"):
        if not isinstance(value.get(field), str) or not value[field]:
            raise ProcessBoundaryError(f"side {side} {role} descriptor identity is incomplete")
    return value  # type: ignore[return-value]


def descriptor_identity(descriptor: dict[str, Any]) -> dict[str, str]:
    return {
        "kind": descriptor["implementation_kind"],
        "implementation_id": descriptor["implementation_id"],
        "implementation_version": descriptor["implementation_version"],
        "implementation_digest": descriptor["implementation_digest"],
    }


def wait_server_descriptor(path: Path, process: JsonLineProcess, *, side: str) -> dict[str, str]:
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline:
        if path.is_file():
            try:
                return strict_descriptor(json.loads(path.read_text(encoding="utf-8")), side=side, role="server")
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise ProcessBoundaryError(f"side {side} server descriptor is malformed") from exc
        if process.process.poll() is not None:
            raise ProcessBoundaryError(f"side {side} server exited before publishing its descriptor")
        time.sleep(0.02)
    raise ProcessBoundaryError(f"side {side} server descriptor was not published")


def _input_contains(value: Any, needle: str) -> bool:
    if isinstance(value, dict):
        return any(_input_contains(item, needle) for item in value.values())
    if isinstance(value, list):
        return any(_input_contains(item, needle) for item in value)
    return value == needle


def relay_phase(
    *,
    phase: str,
    client_side: str,
    expected_server_side: str,
    begin_input: dict[str, Any],
    clients: dict[str, JsonLineProcess],
    servers: dict[str, JsonLineProcess],
    client_events: list[dict[str, Any]],
    exchanges: list[dict[str, Any]],
    test_behavior: str,
) -> dict[str, Any]:
    client = clients[client_side]
    begin_request = client_control(
        f"{begin_input['run_id']}-{begin_input['direction']}-{phase}-begin",
        "begin_phase",
        begin_input,
    )
    begin_response, event = successful_client_result(client, begin_request, label=f"{client_side} {phase}")
    client_events.append(
        {
            "sequence": len(client_events) + 1,
            "client_side": client_side,
            "client_process_instance_id": client.instance_id,
            "request": begin_request,
            "response": begin_response,
        }
    )
    if event.get("event") != "mcp_request" or event.get("phase") != phase:
        raise ProcessBoundaryError(f"side {client_side} did not emit an MCP request for {phase}")
    if event.get("destination_side") != expected_server_side:
        raise ProcessBoundaryError(f"side {client_side} routed {phase} to the wrong server")
    request = event.get("request")
    request_json = event.get("request_json")
    if not isinstance(request, dict) or not isinstance(request_json, str) or json.loads(request_json) != request:
        raise ProcessBoundaryError("participant client did not provide exact request JSON")
    exchange_sequence = len(exchanges) + 1
    destination = expected_server_side
    forwarded_request = copy.deepcopy(request)
    forwarded_request_json = request_json
    request_origin = "participant_client"
    response_origin = "participant_server"
    if test_behavior == "harness_constructed_send" and exchange_sequence == 1:
        request_origin = "repository_harness"
    if test_behavior == "relay_rewrites_request" and exchange_sequence == 1:
        forwarded_request["relay_extension"] = "rewritten"
        forwarded_request_json = compact_json(forwarded_request)
    if test_behavior == "relay_changes_message" and exchange_sequence == 1:
        forwarded_request.setdefault("params", {})["relay_extension"] = "rewritten-message-path"
        forwarded_request_json = compact_json(forwarded_request)
    if test_behavior == "relay_routes_to_wrong_server_side" and exchange_sequence == 1:
        destination = "B" if expected_server_side == "A" else "A"

    server = servers[destination]
    if test_behavior == "relay_synthesizes_success_response" and exchange_sequence == 1:
        message = request.get("params", {}).get("arguments", {}).get("message", {})
        server_response = {
            "jsonrpc": "2.0",
            "id": request.get("id"),
            "result": {
                "accepted": True,
                "message_id": message.get("message_id"),
                "message_hash": message.get("message_hash"),
            },
        }
        server_response_json = compact_json(server_response)
        response_origin = "repository_harness"
    else:
        server_response, server_response_json = server.exchange_json(forwarded_request_json)
    delivered_response = copy.deepcopy(server_response)
    delivered_response_json = server_response_json
    if test_behavior == "relay_rewrites_response" and exchange_sequence == 1:
        delivered_response["relay_extension"] = "rewritten"
        delivered_response_json = compact_json(delivered_response)
    if test_behavior == "relay_changes_jsonrpc_id" and exchange_sequence == 1:
        delivered_response["id"] = "relay-rewritten-id"
        delivered_response_json = compact_json(delivered_response)

    response_request = client_control(
        f"{begin_input['run_id']}-{begin_input['direction']}-{phase}-response",
        "mcp_response",
        {
            "phase": phase,
            "side": client_side,
            "run_id": begin_input["run_id"],
            "direction": begin_input["direction"],
            "exchange_id": event.get("exchange_id"),
            "source_side": destination,
            "response_json": delivered_response_json,
        },
    )
    response_response, completion = successful_client_result(
        client,
        response_request,
        label=f"{client_side} {phase} response",
    )
    client_events.append(
        {
            "sequence": len(client_events) + 1,
            "client_side": client_side,
            "client_process_instance_id": client.instance_id,
            "request": response_request,
            "response": response_response,
        }
    )
    operation = request.get("params", {}).get("name")
    exchanges.append(
        {
            "sequence": exchange_sequence,
            "phase": phase,
            "operation": operation,
            "originating_client_side": client_side,
            "destination_server_side": destination,
            "client_process_instance_id": client.instance_id,
            "server_process_instance_id": server.instance_id,
            "request_origin": request_origin,
            "response_origin": response_origin,
            "client_request": request,
            "request": forwarded_request,
            "response": server_response,
            "client_delivered_response": delivered_response,
            "request_json": request_json,
            "forwarded_request_json": forwarded_request_json,
            "response_json": server_response_json,
            "delivered_response_json": delivered_response_json,
            "request_byte_digest": sha256_bytes(request_json.encode("utf-8")),
            "response_byte_digest": sha256_bytes(server_response_json.encode("utf-8")),
        }
    )
    if completion.get("event") != "phase_complete" or completion.get("phase") != phase:
        raise ProcessBoundaryError(f"side {client_side} did not complete {phase}")
    return completion


def execute_direction(
    *,
    run_number: int,
    run_id: str,
    direction: str,
    clients: dict[str, JsonLineProcess],
    servers: dict[str, JsonLineProcess],
    test_behavior: str,
) -> dict[str, Any]:
    producer, consumer = ("A", "B") if direction == "A_TO_B" else ("B", "A")
    challenge = f"challenge-{run_number}-{direction.lower()}-{secrets.token_hex(32)}"
    session_id = f"session-{run_number}-{direction.lower()}-{secrets.token_hex(16)}"
    contract_id = f"contract-{run_number}-{direction.lower()}-{secrets.token_hex(16)}"
    client_events: list[dict[str, Any]] = []
    exchanges: list[dict[str, Any]] = []

    def neutral(side: str, phase: str, destination: str, *, with_message_fields: bool = False) -> dict[str, Any]:
        value: dict[str, Any] = {
            "phase": phase,
            "side": side,
            "run_id": run_id,
            "direction": direction,
            "session_id": session_id,
            "contract_id": contract_id,
            "destination_side": destination,
        }
        if with_message_fields:
            value.update(
                {
                    "message_id": f"m-{secrets.token_hex(12)}",
                    "timestamp": f"2026-07-{run_number:02d}T00:00:{len(exchanges) + 1:02d}Z",
                }
            )
        return value

    proposal_input = neutral(producer, "propose", consumer, with_message_fields=True)
    proposal_input["challenge"] = challenge
    proposal_complete = relay_phase(
        phase="propose",
        client_side=producer,
        expected_server_side=consumer,
        begin_input=proposal_input,
        clients=clients,
        servers=servers,
        client_events=client_events,
        exchanges=exchanges,
        test_behavior=test_behavior,
    )
    proposal = proposal_complete["message"]

    skip_proposal_poll = test_behavior in {
        "consumer_does_not_poll",
        "consumer_uses_preseeded_peer_message",
        "consumer_uses_preseeded_peer_hash",
        "preseed_consumer_peer_hash",
    }
    proposal_poll_complete: dict[str, Any] | None = None
    if not skip_proposal_poll:
        poll_input = neutral(consumer, "poll_proposal", consumer)
        if test_behavior in {"consumer_uses_preseeded_challenge", "preseed_consumer_challenge"}:
            poll_input["preseed_challenge"] = challenge
        proposal_poll_complete = relay_phase(
            phase="poll_proposal",
            client_side=consumer,
            expected_server_side=consumer,
            begin_input=poll_input,
            clients=clients,
            servers=servers,
            client_events=client_events,
            exchanges=exchanges,
            test_behavior=test_behavior,
        )

    accept_input = neutral(consumer, "accept", producer, with_message_fields=True)
    if skip_proposal_poll:
        accept_input["preseed_peer_message"] = copy.deepcopy(proposal)
        if test_behavior in {"consumer_uses_preseeded_peer_hash", "preseed_consumer_peer_hash"}:
            accept_input["preseed_peer_hash"] = proposal["message_hash"]
    accept_complete = relay_phase(
        phase="accept",
        client_side=consumer,
        expected_server_side=producer,
        begin_input=accept_input,
        clients=clients,
        servers=servers,
        client_events=client_events,
        exchanges=exchanges,
        test_behavior=test_behavior,
    )
    acceptance = accept_complete["message"]

    acceptance_poll_complete = relay_phase(
        phase="poll_acceptance",
        client_side=producer,
        expected_server_side=producer,
        begin_input=neutral(producer, "poll_acceptance", producer),
        clients=clients,
        servers=servers,
        client_events=client_events,
        exchanges=exchanges,
        test_behavior=test_behavior,
    )
    attest_complete = relay_phase(
        phase="attest",
        client_side=producer,
        expected_server_side=consumer,
        begin_input=neutral(producer, "attest", consumer, with_message_fields=True),
        clients=clients,
        servers=servers,
        client_events=client_events,
        exchanges=exchanges,
        test_behavior=test_behavior,
    )
    attestation = attest_complete["message"]

    final_poll_complete: dict[str, Any] | None = None
    if test_behavior != "missing_final_consumer_poll":
        final_poll_complete = relay_phase(
            phase="poll_attestation",
            client_side=consumer,
            expected_server_side=consumer,
            begin_input=neutral(consumer, "poll_attestation", consumer),
            clients=clients,
            servers=servers,
            client_events=client_events,
            exchanges=exchanges,
            test_behavior=test_behavior,
        )

    def exchange_sequence(phase: str) -> int | None:
        return next((item["sequence"] for item in exchanges if item["phase"] == phase), None)

    messages = [
        {
            "sequence": 1,
            "sender_side": producer,
            "constructed_by": producer,
            "consumed_by": consumer,
            "message": proposal,
            "send_exchange_sequence": exchange_sequence("propose"),
            "consume_exchange_sequence": exchange_sequence("poll_proposal"),
            "client_visible_hashes_before": (proposal_poll_complete or {}).get("client_visible_hashes_before", []),
            "client_visible_hashes_after": (proposal_poll_complete or {}).get("client_visible_hashes_after", []),
        },
        {
            "sequence": 2,
            "sender_side": consumer,
            "constructed_by": consumer,
            "consumed_by": producer,
            "message": acceptance,
            "send_exchange_sequence": exchange_sequence("accept"),
            "consume_exchange_sequence": exchange_sequence("poll_acceptance"),
            "client_visible_hashes_before": acceptance_poll_complete.get("client_visible_hashes_before", []),
            "client_visible_hashes_after": acceptance_poll_complete.get("client_visible_hashes_after", []),
        },
        {
            "sequence": 3,
            "sender_side": producer,
            "constructed_by": producer,
            "consumed_by": consumer,
            "message": attestation,
            "send_exchange_sequence": exchange_sequence("attest"),
            "consume_exchange_sequence": exchange_sequence("poll_attestation"),
            "client_visible_hashes_before": (final_poll_complete or {}).get("client_visible_hashes_before", []),
            "client_visible_hashes_after": (final_poll_complete or {}).get("client_visible_hashes_after", []),
        },
    ]
    return {
        "direction": direction,
        "producer_side": producer,
        "consumer_side": consumer,
        "challenge": challenge,
        "session_id": session_id,
        "contract_id": contract_id,
        "client_events": client_events,
        "exchanges": exchanges,
        "messages": messages,
    }


def load_release() -> tuple[dict[str, Any], str]:
    snapshot_path = HERE / "release_registry_snapshots" / f"{RELEASE_ID}.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    release = next((item for item in snapshot.get("releases", []) if item.get("release_id") == RELEASE_ID), None)
    if not isinstance(release, dict):
        raise ValueError(f"{RELEASE_ID} immutable release snapshot is missing")
    return release, sha256_file(snapshot_path)


def run(args: argparse.Namespace) -> dict[str, Any]:
    output = Path(args.out).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    profile_paths = {
        "A": Path(args.peer_a_profile_report).resolve(),
        "B": Path(args.peer_b_profile_report).resolve(),
    }
    binding_paths = {
        "A": Path(args.peer_a_binding_report).resolve(),
        "B": Path(args.peer_b_binding_report).resolve(),
    }
    identities, _, _ = prevalidate_side_reports(profile_paths, binding_paths)
    verify_runner_bundle()
    release, registry_digest = load_release()
    commands = {
        "A": {
            "client": load_command(args.peer_a_client_cmd_json),
            "server": load_command(args.peer_a_server_cmd_json),
        },
        "B": {
            "client": load_command(args.peer_b_client_cmd_json),
            "server": load_command(args.peer_b_server_cmd_json),
        },
    }
    participants = [
        {
            "side": side,
            "implementation_kind": identities[side]["kind"],
            "implementation_id": identities[side]["implementation_id"],
            "implementation_version": identities[side]["implementation_version"],
            "implementation_digest": identities[side]["implementation_digest"],
            "profile_report": report_ref(profile_paths[side], output),
            "binding_report": report_ref(binding_paths[side], output),
            "client_descriptor_evidence": {"descriptor": None, "runs": []},
            "server_descriptor_evidence": {"descriptor": None, "runs": []},
        }
        for side in ("A", "B")
    ]
    by_side = {item["side"]: item for item in participants}
    runs: list[dict[str, Any]] = []
    test_behavior = getattr(args, "test_behavior", "good")
    for run_number in (1, 2):
        run_id = f"run-{run_number}-{secrets.token_hex(16)}"
        resources: list[JsonLineProcess] = []
        with tempfile.TemporaryDirectory(prefix="aicp-pairwise-v1-2-") as temporary:
            ready_root = Path(temporary)
            try:
                clients = {
                    side: JsonLineProcess(
                        commands[side]["client"],
                        cwd=ROOT,
                        instance_id=f"proc-{run_id}-{side}-client-{secrets.token_hex(8)}",
                        environment={
                            "AICP_PAIRWISE_SIDE": side,
                            "AICP_PAIRWISE_ROLE": "client",
                            "AICP_PAIRWISE_TARGET": TARGET_ID,
                        },
                    )
                    for side in ("A", "B")
                }
                resources.extend(clients.values())
                client_evidence: dict[str, dict[str, Any]] = {}
                client_descriptors: dict[str, dict[str, str]] = {}
                for side in ("A", "B"):
                    request = client_control(f"{run_id}-{side}-client-describe", "describe")
                    response, result = successful_client_result(clients[side], request, label=f"{side} client describe")
                    descriptor = strict_descriptor(result, side=side, role="client")
                    client_descriptors[side] = descriptor
                    client_evidence[side] = {
                        "run_id": run_id,
                        "process_instance_id": clients[side].instance_id,
                        "request": request,
                        "response": response,
                    }

                ready_paths = {side: ready_root / f"{side}-server-ready.json" for side in ("A", "B")}
                servers = {
                    side: JsonLineProcess(
                        commands[side]["server"],
                        cwd=ROOT,
                        instance_id=f"proc-{run_id}-{side}-server-{secrets.token_hex(8)}",
                        environment={
                            "AICP_PAIRWISE_READY_FILE": str(ready_paths[side]),
                            "AICP_PAIRWISE_SIDE": side,
                            "AICP_PAIRWISE_ROLE": "server",
                            "AICP_PAIRWISE_TARGET": TARGET_ID,
                        },
                    )
                    for side in ("A", "B")
                }
                resources.extend(servers.values())
                server_descriptors = {
                    side: wait_server_descriptor(ready_paths[side], servers[side], side=side)
                    for side in ("A", "B")
                }
                for side in ("A", "B"):
                    expected = identities[side]
                    if descriptor_identity(client_descriptors[side]) != expected:
                        raise ProcessBoundaryError(f"side {side} client descriptor does not match side reports")
                    if descriptor_identity(server_descriptors[side]) != expected:
                        raise ProcessBoundaryError(f"side {side} server descriptor does not match side reports")
                    if client_descriptors[side] != {**server_descriptors[side], "role": "client"}:
                        raise ProcessBoundaryError(f"side {side} client/server descriptors are not build-coherent")
                    participant = by_side[side]
                    if participant["client_descriptor_evidence"]["descriptor"] is None:
                        participant["client_descriptor_evidence"]["descriptor"] = client_descriptors[side]
                        participant["server_descriptor_evidence"]["descriptor"] = server_descriptors[side]
                    elif (
                        participant["client_descriptor_evidence"]["descriptor"] != client_descriptors[side]
                        or participant["server_descriptor_evidence"]["descriptor"] != server_descriptors[side]
                    ):
                        raise ProcessBoundaryError(f"side {side} role descriptor changed between clean runs")
                    participant["client_descriptor_evidence"]["runs"].append(client_evidence[side])
                    participant["server_descriptor_evidence"]["runs"].append(
                        {
                            "run_id": run_id,
                            "process_instance_id": servers[side].instance_id,
                            "descriptor": server_descriptors[side],
                        }
                    )
                run_record = {
                    "run_id": run_id,
                    "semantic_digest": "",
                    "role_instances": [
                        {
                            "side": side,
                            "client_process_instance_id": clients[side].instance_id,
                            "server_process_instance_id": servers[side].instance_id,
                        }
                        for side in ("A", "B")
                    ],
                    "directions": [
                        execute_direction(
                            run_number=run_number,
                            run_id=run_id,
                            direction=direction,
                            clients=clients,
                            servers=servers,
                            test_behavior=test_behavior,
                        )
                        for direction in ("A_TO_B", "B_TO_A")
                    ],
                }
                run_record["semantic_digest"] = semantic_digest(run_record)
                runs.append(run_record)
                for resource in reversed(resources):
                    resource.close()
                resources.clear()
            finally:
                for resource in resources:
                    resource.abort()
    if runs[0]["semantic_digest"] != runs[1]["semantic_digest"]:
        raise ProcessBoundaryError("two clean Pairwise runs did not normalize to identical role semantics")
    tck = {
        "release_id": RELEASE_ID,
        "registry_digest": registry_digest,
        "runner_bundle_digest": release["runner_bundle"]["digest"],
        "report_schema_digest": release["report_schema"]["content_digest"],
        "evaluator_digest": release["evaluator"]["content_digest"],
        "normalizer_digest": release["normalizer"]["content_digest"],
    }
    return {
        "report_format_version": "1.2",
        "report_type": "aicp.pairwise_joint_execution",
        "pairwise_tck_release": tck,
        "target": {
            "profile_id": "AICP-BASE",
            "profile_version": "0.1",
            "binding_id": "BIND-MCP",
            "binding_version": "0.1",
            "target_catalog_digest": release["target_registry"]["content_digest"],
        },
        "scenario": {
            "scenario_id": SCENARIO_ID,
            "scenario_catalog_digest": release["scenario_catalog"]["content_digest"],
            "scenario_schema_digest": release["scenario_catalog"]["schema_digest"],
        },
        "participants": participants,
        "side_evidence": [
            {"side": item["side"], "profile_report": item["profile_report"], "binding_report": item["binding_report"]}
            for item in participants
        ],
        "runs": runs,
        "passed": True,
        "failures": [],
        "degraded": False,
        "degraded_reasons": [],
        "skipped_checks": [],
        "compatibility_marks": [],
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    for side in ("a", "b"):
        parser.add_argument(f"--peer-{side}-client-cmd-json", required=True)
        parser.add_argument(f"--peer-{side}-server-cmd-json", required=True)
        parser.add_argument(f"--peer-{side}-profile-report", required=True)
        parser.add_argument(f"--peer-{side}-binding-report", required=True)
    parser.add_argument("--test-behavior", default="good")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    try:
        report = run(args)
        output = Path(args.out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except Exception as exc:
        print(f"Pairwise execution FAILED: {exc}", file=sys.stderr)
        return 1
    print("Pairwise role path PASSED: A client -> B server")
    print("Pairwise role path PASSED: B client -> A server")
    print(f"Pairwise execution PASSED: {TARGET_ID}; out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
