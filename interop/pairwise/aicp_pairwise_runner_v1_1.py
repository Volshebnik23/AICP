#!/usr/bin/env python3
"""Run Pairwise TCK 1.1 with release-bound authorities and runtime challenges."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

from pairwise_process import JsonLineProcess, ProcessBoundaryError  # noqa: E402

TARGET_ID = "AICP-BASE@0.1+BIND-MCP@0.1"
SCENARIO_ID = "PAIRWISE-MCP-CROSS-CONSUMPTION-01"
RELEASE_ID = "AICP-PAIRWISE-TCK-1.1.0"
CONTROL_VERSION = "aicp.pairwise_control.v1"


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_file(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix.lower() in {".json", ".jsonl", ".md", ".py", ".ts", ".mjs", ".yml", ".yaml"}:
        data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def report_ref(path: Path, output: Path) -> dict[str, str]:
    try:
        relative = path.resolve().relative_to(output.resolve().parent).as_posix()
    except ValueError as exc:
        raise ValueError("side reports must be beneath the joint report directory") from exc
    return {"path": relative, "content_digest": sha256_file(path)}


def load_command(raw: str) -> list[str]:
    value = json.loads(raw)
    if not isinstance(value, list) or not value or not all(isinstance(item, str) and item for item in value):
        raise ValueError("commands must be non-empty JSON string arrays")
    return value


def rpc(request_id: str, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "method": "tools/call", "params": {"name": tool, "arguments": arguments}}


def control(request_id: str, operation: str, input_value: dict[str, Any] | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"control_version": CONTROL_VERSION, "request_id": request_id, "operation": operation}
    if input_value is not None:
        result["input"] = input_value
    return result


def successful_result(response: dict[str, Any], *, label: str) -> dict[str, Any]:
    if response.get("success") is not True or not isinstance(response.get("result"), dict):
        raise ProcessBoundaryError(f"{label} did not return a successful result")
    return response["result"]


def rpc_result(response: dict[str, Any], request: dict[str, Any], *, label: str) -> dict[str, Any]:
    if response.get("jsonrpc") != "2.0" or response.get("id") != request.get("id"):
        raise ProcessBoundaryError(f"{label} broke JSON-RPC request/response correlation")
    if "error" in response or not isinstance(response.get("result"), dict):
        raise ProcessBoundaryError(f"{label} returned an MCP error")
    return response["result"]


def runner_semantic_digest(run: dict[str, Any]) -> str:
    # Kept deliberately local: the runner does not import the evaluator's normalizer.
    directions: list[dict[str, Any]] = []
    for direction in run["directions"]:
        messages = direction["messages"]
        positions = {item["message"]["message_hash"]: index for index, item in enumerate(messages)}
        normalized: list[dict[str, Any]] = []
        for item in messages:
            message = item["message"]
            payload = message["payload"]
            if message["message_type"] == "CONTRACT_PROPOSE":
                shape = {
                    "contract_roles": payload["contract"].get("roles"),
                    "has_contract_hash": isinstance(payload.get("contract_hash"), str),
                    "goal_is_runtime_challenge": payload["contract"].get("goal") == run.get("challenge"),
                }
            elif message["message_type"] == "CONTRACT_ACCEPT":
                shape = {"accepted": payload.get("accepted")}
            else:
                shape = {"action_type": payload.get("action_type"), "has_result_hash": isinstance(payload.get("result_hash"), str)}
            normalized.append({
                "sequence": item["sequence"], "constructed_by": item["constructed_by"], "consumed_by": item["consumed_by"],
                "message_type": message["message_type"], "sender_side": item["sender_side"],
                "previous_sequence": positions.get(message.get("prev_msg_hash")) if message.get("prev_msg_hash") is not None else None,
                "payload_semantics": shape,
                "mcp_tools": [item["mcp_send"]["request"]["params"]["name"], item["mcp_poll"]["request"]["params"]["name"]],
                "control_is_run_bound": (
                    item["control_request"]["input"].get("run_id") == run.get("run_id")
                    and item["control_request"]["input"].get("challenge") == run.get("challenge")
                ),
            })
        directions.append({"direction": direction["direction"], "producer_side": direction["producer_side"], "consumer_side": direction["consumer_side"], "messages": normalized})
    return "sha256:" + hashlib.sha256(canonical_bytes({"directions": directions})).hexdigest()


def deliver(
    server: JsonLineProcess,
    *,
    message: dict[str, Any],
    cursor: str,
    visible: list[str],
    prefix: str,
) -> tuple[dict[str, Any], str, list[str]]:
    send_request = rpc(f"{prefix}-send", "aicp.sendMessage", {"message": message})
    send_response = server.exchange(send_request)
    send_result = rpc_result(send_response, send_request, label="sendMessage")
    if send_result.get("accepted") is not True or send_result.get("message_hash") != message.get("message_hash"):
        raise ProcessBoundaryError("MCP peer did not accept the exact sent envelope")
    poll_request = rpc(
        f"{prefix}-poll",
        "aicp.pollMessages",
        {"session_id": message["session_id"], "after_cursor": cursor, "limit": 1},
    )
    poll_response = server.exchange(poll_request)
    poll_result = rpc_result(poll_response, poll_request, label="pollMessages")
    messages = poll_result.get("messages")
    if not isinstance(messages, list) or len(messages) != 1 or messages[0] != message:
        raise ProcessBoundaryError("MCP peer did not return the exact first-seen envelope")
    next_cursor = poll_result.get("next_cursor")
    if not isinstance(next_cursor, str) or not next_cursor:
        raise ProcessBoundaryError("MCP peer did not return a bounded continuation cursor")
    before = list(visible)
    after = [*visible, message["message_hash"]]
    return {
        "mcp_send": {"request": send_request, "response": send_response},
        "mcp_poll": {"request": poll_request, "response": poll_response},
        "first_seen": {"visible_hashes_before": before, "visible_hashes_after": after},
        "delivered_message": copy.deepcopy(messages[0]),
    }, next_cursor, after


def construct(
    peer: JsonLineProcess,
    *,
    request_id: str,
    phase: str,
    run_id: str,
    side: str,
    session_id: str,
    contract_id: str,
    message_id: str,
    timestamp: str,
    challenge: str,
    visible_hashes: list[str],
    peer_message: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    input_value: dict[str, Any] = {
        "phase": phase, "run_id": run_id, "side": side, "session_id": session_id,
        "contract_id": contract_id, "message_id": message_id, "timestamp": timestamp,
        "challenge": challenge, "visible_message_hashes": list(visible_hashes),
    }
    if peer_message is not None:
        input_value["peer_message"] = copy.deepcopy(peer_message)
    request = control(request_id, "construct", input_value)
    response = peer.exchange(request)
    result = successful_result(response, label=f"{side} {phase}")
    message = result.get("message")
    if not isinstance(message, dict):
        raise ProcessBoundaryError("peer construction result did not contain a message")
    return request, response, message


def execute_direction(
    *,
    run_number: int,
    run_id: str,
    challenge: str,
    direction: str,
    controls: dict[str, JsonLineProcess],
    servers: dict[str, JsonLineProcess],
) -> dict[str, Any]:
    producer, consumer = ("A", "B") if direction == "A_TO_B" else ("B", "A")
    token = secrets.token_hex(16)
    session_id = f"session-{run_number}-{direction.lower()}-{token}"
    contract_id = f"contract-{run_number}-{direction.lower()}-{secrets.token_hex(16)}"
    visible = {"A": [], "B": []}
    cursors = {"A": "c0", "B": "c0"}
    records: list[dict[str, Any]] = []

    request, response, proposal = construct(
        controls[producer], request_id=f"{run_id}-{direction}-propose", phase="propose", run_id=run_id,
        side=producer, session_id=session_id, contract_id=contract_id, message_id=f"m-{secrets.token_hex(12)}",
        timestamp=f"2026-06-{run_number:02d}T00:00:01Z", challenge=challenge, visible_hashes=visible[producer],
    )
    delivery, cursors[consumer], visible[consumer] = deliver(
        servers[consumer], message=proposal, cursor=cursors[consumer], visible=visible[consumer], prefix=f"{run_id}-{direction}-1"
    )
    delivered_proposal = delivery.pop("delivered_message")
    records.append({"sequence": 1, "sender_side": producer, "constructed_by": producer, "consumed_by": consumer, "message": proposal, "control_request": request, "control_response": response, **delivery})

    request, response, acceptance = construct(
        controls[consumer], request_id=f"{run_id}-{direction}-accept", phase="accept", run_id=run_id,
        side=consumer, session_id=session_id, contract_id=contract_id, message_id=f"m-{secrets.token_hex(12)}",
        timestamp=f"2026-06-{run_number:02d}T00:00:02Z", challenge=challenge, visible_hashes=visible[consumer], peer_message=delivered_proposal,
    )
    delivery, cursors[producer], visible[producer] = deliver(
        servers[producer], message=acceptance, cursor=cursors[producer], visible=visible[producer], prefix=f"{run_id}-{direction}-2"
    )
    delivered_acceptance = delivery.pop("delivered_message")
    records.append({"sequence": 2, "sender_side": consumer, "constructed_by": consumer, "consumed_by": producer, "message": acceptance, "control_request": request, "control_response": response, **delivery})

    request, response, attestation = construct(
        controls[producer], request_id=f"{run_id}-{direction}-attest", phase="attest", run_id=run_id,
        side=producer, session_id=session_id, contract_id=contract_id, message_id=f"m-{secrets.token_hex(12)}",
        timestamp=f"2026-06-{run_number:02d}T00:00:03Z", challenge=challenge, visible_hashes=visible[producer], peer_message=delivered_acceptance,
    )
    delivery, cursors[consumer], visible[consumer] = deliver(
        servers[consumer], message=attestation, cursor=cursors[consumer], visible=visible[consumer], prefix=f"{run_id}-{direction}-3"
    )
    delivery.pop("delivered_message")
    records.append({"sequence": 3, "sender_side": producer, "constructed_by": producer, "consumed_by": consumer, "message": attestation, "control_request": request, "control_response": response, **delivery})
    return {"direction": direction, "producer_side": producer, "consumer_side": consumer, "session_id": session_id, "contract_id": contract_id, "messages": records}


def participant(
    side: str,
    descriptor: dict[str, Any],
    descriptor_evidence: dict[str, Any],
    profile_path: Path,
    binding_path: Path,
    output: Path,
) -> dict[str, Any]:
    return {
        "side": side,
        "implementation_kind": descriptor.get("implementation_kind"),
        "implementation_id": descriptor.get("implementation_id"),
        "implementation_version": descriptor.get("implementation_version"),
        "implementation_digest": descriptor.get("implementation_digest"),
        "profile_report": report_ref(profile_path, output),
        "binding_report": report_ref(binding_path, output),
        "descriptor_evidence": descriptor_evidence,
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
    profile_paths = {"A": Path(args.peer_a_profile_report).resolve(), "B": Path(args.peer_b_profile_report).resolve()}
    binding_paths = {"A": Path(args.peer_a_binding_report).resolve(), "B": Path(args.peer_b_binding_report).resolve()}
    commands = {
        "A": {"control": load_command(args.peer_a_control_cmd_json), "server": load_command(args.peer_a_server_cmd_json)},
        "B": {"control": load_command(args.peer_b_control_cmd_json), "server": load_command(args.peer_b_server_cmd_json)},
    }
    release, registry_digest = load_release()
    participants: list[dict[str, Any]] | None = None
    runs: list[dict[str, Any]] = []
    for run_number in (1, 2):
        run_id = f"run-{run_number}-{secrets.token_hex(16)}"
        challenge = f"challenge-{run_number}-{secrets.token_hex(32)}"
        resources: list[JsonLineProcess] = []
        try:
            controls = {side: JsonLineProcess(commands[side]["control"], cwd=ROOT) for side in ("A", "B")}
            resources.extend(controls.values())
            servers = {side: JsonLineProcess(commands[side]["server"], cwd=ROOT) for side in ("A", "B")}
            resources.extend(servers.values())
            descriptors: dict[str, dict[str, Any]] = {}
            descriptor_evidence: dict[str, dict[str, Any]] = {}
            for side in ("A", "B"):
                describe_request = control(f"{run_id}-{side}-describe", "describe")
                response = controls[side].exchange(describe_request)
                descriptors[side] = successful_result(response, label=f"{side} describe")
                descriptor_evidence[side] = {"request": describe_request, "response": response}
                if descriptors[side].get("supported_target") != TARGET_ID:
                    raise ProcessBoundaryError(f"side {side} did not declare the exact pairwise target")
            current = [participant(side, descriptors[side], descriptor_evidence[side], profile_paths[side], binding_paths[side], output) for side in ("A", "B")]
            if participants is None:
                participants = current
            elif any(
                {key: value for key, value in item.items() if key != "descriptor_evidence"}
                != {key: value for key, value in participants[index].items() if key != "descriptor_evidence"}
                for index, item in enumerate(current)
            ):
                raise ProcessBoundaryError("participant identity changed between clean runs")
            run_record = {"run_id": run_id, "challenge": challenge, "semantic_digest": "", "directions": [
                execute_direction(run_number=run_number, run_id=run_id, challenge=challenge, direction=direction, controls=controls, servers=servers)
                for direction in ("A_TO_B", "B_TO_A")
            ]}
            run_record["semantic_digest"] = runner_semantic_digest(run_record)
            runs.append(run_record)
            for resource in reversed(resources):
                resource.close()
            resources.clear()
        finally:
            for resource in resources:
                resource.abort()
    assert participants is not None
    if participants[0]["implementation_id"] == participants[1]["implementation_id"] or participants[0]["implementation_digest"] == participants[1]["implementation_digest"]:
        raise ValueError("pairwise execution requires two distinct implementation IDs and build digests")
    tck = {
        "release_id": RELEASE_ID,
        "registry_digest": registry_digest,
        "runner_bundle_digest": release["runner_bundle"]["digest"],
        "report_schema_digest": release["report_schema"]["content_digest"],
        "evaluator_digest": release["evaluator"]["content_digest"],
        "normalizer_digest": release["normalizer"]["content_digest"],
    }
    return {
        "report_format_version": "1.1", "report_type": "aicp.pairwise_joint_execution", "pairwise_tck_release": tck,
        "target": {"profile_id": "AICP-BASE", "profile_version": "0.1", "binding_id": "BIND-MCP", "binding_version": "0.1", "target_catalog_digest": release["target_registry"]["content_digest"]},
        "scenario": {"scenario_id": SCENARIO_ID, "scenario_catalog_digest": release["scenario_catalog"]["content_digest"], "scenario_schema_digest": release["scenario_catalog"]["schema_digest"]},
        "participants": participants,
        "side_evidence": [
            {"side": item["side"], "profile_report": item["profile_report"], "binding_report": item["binding_report"]}
            for item in participants
        ],
        "runs": runs, "passed": True, "failures": [], "degraded": False,
        "degraded_reasons": [], "skipped_checks": [], "compatibility_marks": [],
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    for side in ("a", "b"):
        parser.add_argument(f"--peer-{side}-control-cmd-json", required=True)
        parser.add_argument(f"--peer-{side}-server-cmd-json", required=True)
        parser.add_argument(f"--peer-{side}-profile-report", required=True)
        parser.add_argument(f"--peer-{side}-binding-report", required=True)
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
    print(f"Pairwise execution PASSED: {TARGET_ID}; out={args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
