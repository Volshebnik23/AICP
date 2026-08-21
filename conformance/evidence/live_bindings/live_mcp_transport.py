from __future__ import annotations

import copy
import json
import subprocess
import time
from pathlib import Path
from typing import Any, BinaryIO


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = ROOT / "conformance" / "evidence"
REF_PY = ROOT / "reference" / "python"

import sys

for path in (EVIDENCE_DIR, REF_PY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from aicp_ref.hashing import object_hash  # noqa: E402
from target_catalog import canonical_digest  # noqa: E402
from live_bindings.live_binding_process import (  # noqa: E402
    LiveProcessError,
    parse_json_line,
    read_bounded_line,
    write_json_line,
)
from live_bindings.live_http_transport import load_messages, message_for_session  # noqa: E402
from live_bindings.live_binding_trace import observation  # noqa: E402
from live_bindings.live_mcp_capture import attach_mcp_transport_evidence  # noqa: E402


SESSION_ID = "sGT1"
OBJECT_VALUE = {
    "contract_id": "cGT1",
    "goal": "golden_demo",
    "roles": ["initiator", "responder"],
}
OBJECT_HASH = "sha256:wKY_CpI6-HtaTMTpufl-eTjXYQXv8Igzv7DFBjdDkS4"
ROLE_PREFIX = {
    "server_under_test": "LIVE-MCP-SERVER",
    "client_under_test": "LIVE-MCP-CLIENT",
}


def rpc_request(request_id: str, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "tools/call",
        "params": {"name": tool, "arguments": arguments},
    }


def rpc_result(request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def rpc_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


class McpState:
    def __init__(self, mode: str = "good") -> None:
        self.mode = mode
        self.messages: dict[str, list[dict[str, Any]]] = {}
        self.message_ids: dict[tuple[str, str], dict[str, Any]] = {}

    def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        request_id = request.get("id")
        if request.get("jsonrpc") != "2.0" or request.get("method") != "tools/call":
            return rpc_error(request_id, -32600, "invalid request")
        params = request.get("params")
        if not isinstance(params, dict):
            return rpc_error(request_id, -32602, "invalid params")
        tool = params.get("name")
        arguments = params.get("arguments")
        if not isinstance(arguments, dict):
            return rpc_error(request_id, -32602, "invalid arguments")
        if tool == "aicp.sendMessage":
            message = arguments.get("message")
            if not isinstance(message, dict) or not all(message.get(field) for field in ("session_id", "message_id", "message_hash")):
                if self.mode == "send_accepts_malformed":
                    return rpc_result(request_id, {"accepted": True})
                return rpc_error(request_id, -32602, "invalid AICP envelope")
            session_id = str(message["session_id"])
            message_id = str(message["message_id"])
            key = (session_id, message_id)
            existing = self.message_ids.get(key)
            if existing is None:
                self.message_ids[key] = copy.deepcopy(message)
                self.messages.setdefault(session_id, []).append(copy.deepcopy(message))
            elif self.mode == "duplicate_conflicting_hash":
                changed = copy.deepcopy(message)
                changed["message_hash"] = "sha256:" + "x" * 43
                self.messages.setdefault(session_id, []).append(changed)
            stored_hash = str(self.message_ids.get(key, {}).get("message_hash", ""))
            if self.mode == "duplicate_conflicting_hash" and existing is not None:
                stored_hash = "sha256:" + "x" * 43
            return rpc_result(
                request_id,
                {
                    "accepted": True,
                    "message_id": message_id,
                    "message_hash": stored_hash,
                    "cursor": f"c{len(self.messages.get(session_id, []))}",
                },
            )
        if tool == "aicp.pollMessages":
            if self.mode == "missing_poll_tool":
                return rpc_error(request_id, -32601, "tool not found")
            session_id = str(arguments.get("session_id", ""))
            if self.mode == "poll_wrong_session":
                session_id = "other-session"
            try:
                limit = int(arguments.get("limit", 1000))
            except (TypeError, ValueError):
                limit = 1000
            after_cursor = str(arguments.get("after_cursor", "c0"))
            start = 0
            if after_cursor.startswith("c") and after_cursor[1:].isdigit():
                start = int(after_cursor[1:])
            if self.mode == "mcp_server_ignores_after_cursor":
                start = 0
            messages = list(self.messages.get(session_id, []))[start:]
            if self.mode != "poll_ignores_limit":
                messages = messages[: max(0, limit)]
            return rpc_result(
                request_id,
                {"messages": copy.deepcopy(messages), "next_cursor": f"c{start + len(messages)}"},
            )
        if tool == "aicp.getHead":
            session_id = str(arguments.get("session_id", ""))
            if self.mode == "head_wrong_session":
                session_id = "other-session"
            messages = self.messages.get(session_id, [])
            return rpc_result(
                request_id,
                {
                    "session_state": {"session_id": session_id},
                    "branch_heads": [
                        {
                            "branch_id": "main",
                            "head_message_id": messages[-1].get("message_id") if messages else None,
                        }
                    ],
                    "active_head_version": "v1",
                },
            )
        if tool == "aicp.getObject":
            requested = str(arguments.get("object_hash", ""))
            if requested != OBJECT_HASH:
                return rpc_result(request_id, {"status": "NOT_FOUND"})
            value = copy.deepcopy(OBJECT_VALUE)
            if self.mode == "object_hash_mismatch":
                value["goal"] = "rewritten"
            return rpc_result(
                request_id,
                {"status": "FOUND", "object_type": "contract", "object_json": value},
            )
        return rpc_error(request_id, -32601, "tool not found")


def mcp_server_loop(stdin: BinaryIO, stdout: BinaryIO, *, mode: str = "good") -> int:
    state = McpState(mode)
    count = 0
    while True:
        raw = stdin.readline(1_048_577)
        if not raw:
            return 0
        count += 1
        if count > 64:
            return 2
        if mode == "timeout" and count == 1:
            time.sleep(30)
        if mode == "malformed_json" and count == 1:
            stdout.write(b"{not-json}\n")
            stdout.flush()
            continue
        if mode == "oversized_line" and count == 1:
            stdout.write(b"X" * 1_048_577 + b"\n")
            stdout.flush()
            continue
        try:
            request = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            write_json_line(stdout, rpc_error(None, -32700, "parse error"))
            continue
        if not isinstance(request, dict):
            write_json_line(stdout, rpc_error(None, -32600, "invalid request"))
            continue
        response = state.handle(request)
        if mode == "wrong_jsonrpc_id" and count == 1:
            response["id"] = "wrong-id"
        write_json_line(stdout, response)


def _exchange(
    process: subprocess.Popen[bytes],
    request: dict[str, Any],
    *,
    deadline: float,
) -> dict[str, Any]:
    if process.stdin is None or process.stdout is None:
        raise LiveProcessError("MCP process pipes are unavailable")
    write_json_line(process.stdin, request)
    raw = read_bounded_line(process.stdout, deadline=deadline)
    response = parse_json_line(raw)
    if response.get("jsonrpc") != "2.0":
        raise LiveProcessError("MCP response does not declare JSON-RPC 2.0")
    if response.get("id") != request.get("id"):
        raise LiveProcessError("MCP response request ID correlation mismatch")
    if ("result" in response) == ("error" in response):
        raise LiveProcessError("MCP response must contain exactly one result or error")
    return response


def _interaction(role: str, suffix: str, operation: str, facts: dict[str, Any]) -> dict[str, Any]:
    scenario_id = f"{ROLE_PREFIX[role]}-{suffix}"
    base = {
        "process_boundary": True,
        "jsonrpc_version": "2.0",
        "request_response_correlated": True,
        "response_count": 1,
        "valid_utf8": True,
    }
    base.update(facts)
    return {
        "interaction_id": scenario_id.lower(),
        "role": role,
        "scenario_id": scenario_id,
        "transport": "mcp_stdio",
        "operation": operation,
        "observations": [observation(name, value) for name, value in sorted(base.items())],
    }


def execute_mcp_server(
    process: subprocess.Popen[bytes],
    *,
    role: str,
    deadline: float,
) -> list[dict[str, Any]]:
    message = message_for_session(load_messages()[0], SESSION_ID)
    second = message_for_session(load_messages()[1], SESSION_ID)
    initial_requests = [
        rpc_request("rpc-send-1", "aicp.sendMessage", {"message": message}),
        rpc_request("rpc-send-2", "aicp.sendMessage", {"message": message}),
        rpc_request("rpc-send-3", "aicp.sendMessage", {"message": second}),
        rpc_request("rpc-poll-1", "aicp.pollMessages", {"session_id": SESSION_ID, "after_cursor": "c0", "limit": 1}),
    ]
    initial_responses = [_exchange(process, request, deadline=deadline) for request in initial_requests]
    first_cursor = str((initial_responses[3].get("result") or {}).get("next_cursor", ""))
    remaining_requests = [
        rpc_request("rpc-poll-2", "aicp.pollMessages", {"session_id": SESSION_ID, "after_cursor": first_cursor, "limit": 1}),
        rpc_request("rpc-head-1", "aicp.getHead", {"session_id": SESSION_ID}),
        rpc_request("rpc-object-1", "aicp.getObject", {"object_hash": OBJECT_HASH}),
        rpc_request("rpc-object-2", "aicp.getObject", {"object_hash": "sha256:" + "A" * 43}),
        rpc_request("rpc-invalid-1", "aicp.sendMessage", {"message": {"session_id": SESSION_ID}}),
    ]
    remaining_responses = [_exchange(process, request, deadline=deadline) for request in remaining_requests]
    requests = [*initial_requests, *remaining_requests]
    responses = [*initial_responses, *remaining_responses]
    send_result = responses[0].get("result") or {}
    duplicate_result = responses[1].get("result") or {}
    poll_result = responses[3].get("result") or {}
    head_result = responses[5].get("result") or {}
    object_result = responses[6].get("result") or {}
    unknown_result = responses[7].get("result") or {}
    polled = poll_result.get("messages") or []
    actual_object = object_result.get("object_json")
    actual_hash = object_hash("contract", actual_object) if isinstance(actual_object, dict) else ""
    interactions = [
        _interaction(role, "SEND", "send_message", {"request_id": "rpc-send-1", "response_id": str(responses[0].get("id", "")), "tool_name": "aicp.sendMessage", "expected_message_id": str(message["message_id"]), "observed_message_id": str(send_result.get("message_id", "")), "expected_message_hash": str(message["message_hash"]), "observed_message_hash": str(message["message_hash"]), "message_digest_equal": send_result.get("accepted") is True and send_result.get("message_id") == message["message_id"]}),
        _interaction(role, "DUPLICATE", "duplicate_send", {"request_id": "rpc-send-2", "response_id": str(responses[1].get("id", "")), "tool_name": "aicp.sendMessage", "logical_accept_count": 1 if duplicate_result.get("accepted") is True else 2, "duplicate_hash_stable": duplicate_result.get("message_id") == message["message_id"] and duplicate_result.get("message_hash") == message["message_hash"]}),
        _interaction(role, "POLL", "poll_messages", {"request_id": "rpc-poll-1", "response_id": str(responses[3].get("id", "")), "tool_name": "aicp.pollMessages", "poll_session_match": all(item.get("session_id") == SESSION_ID for item in polled), "poll_limit": 1, "delivered_count": len(polled), "poll_limit_respected": len(polled) <= 1, "message_hashes_intact": bool(polled) and polled[0].get("message_hash") == message["message_hash"], "next_cursor": str(poll_result.get("next_cursor", "")), "ordering_not_assumed": True}),
        _interaction(role, "HEAD", "get_head", {"request_id": "rpc-head-1", "response_id": str(responses[5].get("id", "")), "tool_name": "aicp.getHead", "head_session_match": (head_result.get("session_state") or {}).get("session_id") == SESSION_ID}),
        _interaction(role, "OBJECT", "get_object", {"request_id": "rpc-object-1", "response_id": str(responses[6].get("id", "")), "tool_name": "aicp.getObject", "object_expected_hash": OBJECT_HASH, "object_actual_hash": actual_hash, "object_hash_recomputed": actual_hash == OBJECT_HASH, "unknown_object_failed": unknown_result.get("status") == "NOT_FOUND"}),
        _interaction(role, "INTEGRITY", "jsonrpc_integrity", {"request_id": "rpc-invalid-1", "response_id": str(responses[8].get("id", "")), "tool_name": "aicp.sendMessage", "request_response_correlated": all(response.get("id") == request.get("id") for request, response in zip(requests, responses)), "valid_utf8": True, "response_count": 1, "malformed_envelope_rejected": "error" in responses[8]}),
    ]
    return attach_mcp_transport_evidence(
        interactions,
        list(zip(requests, responses)),
        role=role,
    )


def _response_for_client_request(state: McpState, request: dict[str, Any]) -> dict[str, Any]:
    return state.handle(request)


def serve_mcp_client(
    process: subprocess.Popen[bytes],
    *,
    role: str,
    deadline: float,
) -> list[dict[str, Any]]:
    if process.stdin is None or process.stdout is None:
        raise LiveProcessError("MCP client pipes are unavailable")
    state = McpState()
    captured: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for _ in range(9):
        raw = read_bounded_line(process.stdout, deadline=deadline)
        request = parse_json_line(raw)
        response = _response_for_client_request(state, request)
        write_json_line(process.stdin, response)
        captured.append((request, response))
    try:
        process.stdin.close()
    except OSError:
        pass
    remaining = max(0.01, deadline - time.monotonic())
    try:
        process.wait(timeout=remaining)
    except subprocess.TimeoutExpired as exc:
        raise LiveProcessError("MCP client did not exit after scenario completion") from exc
    if process.returncode != 0:
        raise LiveProcessError(f"MCP client exited with code {process.returncode}")

    expected_tools = [
        "aicp.sendMessage",
        "aicp.sendMessage",
        "aicp.sendMessage",
        "aicp.pollMessages",
        "aicp.pollMessages",
        "aicp.getHead",
        "aicp.getObject",
        "aicp.getObject",
        "aicp.sendMessage",
    ]
    requests = [item[0] for item in captured]
    responses = [item[1] for item in captured]
    params = [item.get("params") if isinstance(item.get("params"), dict) else {} for item in requests]
    args = [item.get("arguments") if isinstance(item.get("arguments"), dict) else {} for item in params]
    tools = [item.get("name") for item in params]
    message = message_for_session(load_messages()[0], SESSION_ID)
    send_message = args[0].get("message") if args else None
    duplicate_message = args[1].get("message") if len(args) > 1 else None
    poll_result = responses[3].get("result") or {}
    polled = poll_result.get("messages") or []
    head_result = responses[5].get("result") or {}
    object_result = responses[6].get("result") or {}
    actual_object = object_result.get("object_json")
    actual_hash = object_hash("contract", actual_object) if isinstance(actual_object, dict) else ""
    correlation = all(
        request.get("jsonrpc") == "2.0"
        and request.get("method") == "tools/call"
        and response.get("id") == request.get("id")
        for request, response in captured
    )
    ids = [item.get("id") for item in requests]
    interactions = [
        _interaction(role, "SEND", "send_message", {"request_id": str(requests[0].get("id", "")), "response_id": str(responses[0].get("id", "")), "tool_name": str(tools[0]), "expected_message_id": str(message["message_id"]), "observed_message_id": str((send_message or {}).get("message_id", "")), "expected_message_hash": str(message["message_hash"]), "observed_message_hash": str((send_message or {}).get("message_hash", "")), "message_digest_equal": isinstance(send_message, dict) and canonical_digest(send_message) == canonical_digest(message)}),
        _interaction(role, "DUPLICATE", "duplicate_send", {"request_id": str(requests[1].get("id", "")), "response_id": str(responses[1].get("id", "")), "tool_name": str(tools[1]), "logical_accept_count": 1 if isinstance(duplicate_message, dict) and duplicate_message == send_message else 2, "duplicate_hash_stable": isinstance(duplicate_message, dict) and duplicate_message.get("message_hash") == (send_message or {}).get("message_hash")}),
        _interaction(role, "POLL", "poll_messages", {"request_id": str(requests[3].get("id", "")), "response_id": str(responses[3].get("id", "")), "tool_name": str(tools[3]), "poll_session_match": args[3].get("session_id") == SESSION_ID and all(item.get("session_id") == SESSION_ID for item in polled), "poll_limit": int(args[3].get("limit", 0) or 0), "delivered_count": len(polled), "poll_limit_respected": len(polled) <= int(args[3].get("limit", 0) or 0), "message_hashes_intact": bool(polled) and polled[0].get("message_hash") == message["message_hash"], "next_cursor": str(poll_result.get("next_cursor", "")), "ordering_not_assumed": True}),
        _interaction(role, "HEAD", "get_head", {"request_id": str(requests[5].get("id", "")), "response_id": str(responses[5].get("id", "")), "tool_name": str(tools[5]), "head_session_match": args[5].get("session_id") == SESSION_ID and (head_result.get("session_state") or {}).get("session_id") == SESSION_ID}),
        _interaction(role, "OBJECT", "get_object", {"request_id": str(requests[6].get("id", "")), "response_id": str(responses[6].get("id", "")), "tool_name": str(tools[6]), "object_expected_hash": OBJECT_HASH, "object_actual_hash": actual_hash, "object_hash_recomputed": args[6].get("object_hash") == OBJECT_HASH and actual_hash == OBJECT_HASH, "unknown_object_failed": args[7].get("object_hash") != OBJECT_HASH and (responses[7].get("result") or {}).get("status") == "NOT_FOUND"}),
        _interaction(role, "INTEGRITY", "jsonrpc_integrity", {"request_id": str(requests[8].get("id", "")), "response_id": str(responses[8].get("id", "")), "tool_name": str(tools[8]), "request_response_correlated": correlation and len(ids) == len(set(ids)) and tools == expected_tools, "valid_utf8": True, "response_count": 1, "malformed_envelope_rejected": "error" in responses[8]}),
    ]
    return attach_mcp_transport_evidence(interactions, captured, role=role)


def mcp_client_loop(stdin: BinaryIO, stdout: BinaryIO, *, mode: str = "good") -> int:
    message = message_for_session(load_messages()[0], SESSION_ID)
    second = message_for_session(load_messages()[1], SESSION_ID)
    requests = [
        rpc_request("rpc-send-1", "aicp.sendMessage", {"message": message}),
        rpc_request("rpc-send-2", "aicp.sendMessage", {"message": message}),
        rpc_request("rpc-send-3", "aicp.sendMessage", {"message": second}),
        rpc_request("rpc-poll-1", "aicp.pollMessages", {"session_id": SESSION_ID, "after_cursor": "c0", "limit": 1}),
        rpc_request("rpc-poll-2", "aicp.pollMessages", {"session_id": SESSION_ID, "after_cursor": "c1", "limit": 1}),
        rpc_request("rpc-head-1", "aicp.getHead", {"session_id": SESSION_ID}),
        rpc_request("rpc-object-1", "aicp.getObject", {"object_hash": OBJECT_HASH}),
        rpc_request("rpc-object-2", "aicp.getObject", {"object_hash": "sha256:" + "A" * 43}),
        rpc_request("rpc-invalid-1", "aicp.sendMessage", {"message": {"session_id": SESSION_ID}}),
    ]
    if mode == "wrong_tool":
        requests[0]["params"]["name"] = "aicp.send"
    elif mode == "missing_message":
        requests[0]["params"]["arguments"] = {}
    elif mode == "rewritten_message":
        requests[0]["params"]["arguments"]["message"]["sender"] = "agent:rewritten"
    elif mode == "wrong_session":
        requests[3]["params"]["arguments"]["session_id"] = "other-session"
        requests[4]["params"]["arguments"]["session_id"] = "other-session"
    elif mode == "mcp_missing_after_cursor":
        requests[4]["params"]["arguments"].pop("after_cursor", None)
    elif mode == "mcp_wrong_after_cursor":
        requests[4]["params"]["arguments"]["after_cursor"] = "unrelated-cursor"
    elif mode == "wrong_object_hash":
        requests[6]["params"]["arguments"]["object_hash"] = "sha256:" + "B" * 43
    elif mode == "request_id_reuse":
        requests[1]["id"] = requests[0]["id"]
    for index, request in enumerate(requests):
        if mode == "malformed_json" and index == 0:
            stdout.write(b"{not-json}\n")
            stdout.flush()
        else:
            write_json_line(stdout, request)
        raw = stdin.readline(1_048_577)
        if not raw:
            return 3
        try:
            response = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return 4
        if not isinstance(response, dict):
            return 5
    return 0
