#!/usr/bin/env python3
"""Independently implemented Python peer used only to exercise the M66 harness."""

from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any


CONTROL_VERSION = "aicp.pairwise_control.v1"
CLIENT_CONTROL_VERSION = "aicp.pairwise_client_control.v1"
PAIRWISE_DESCRIPTOR_VERSION = "aicp.pairwise_role_descriptor.v1"
PAIRWISE_TARGET = "AICP-BASE@0.1+BIND-MCP@0.1"
ADAPTER_VERSION = "1.1"
IMPLEMENTATION_ID = "aicp-cleanroom-python-a"
IMPLEMENTATION_VERSION = "1.0.0-test"
OBJECT_VALUE = {
    "contract_id": "cGT1",
    "goal": "golden_demo",
    "roles": ["initiator", "responder"],
}

if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8", errors="strict")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="strict")


def _b64url(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _canonical(value: Any) -> str:
    if isinstance(value, float):
        raise ValueError("floating-point values are outside this clean-room surface")
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _object_hash(object_type: str, value: Any) -> str:
    preimage = b"AICP1\0" + object_type.encode("utf-8") + b"\0" + _canonical(value).encode("utf-8")
    return "sha256:" + _b64url(hashlib.sha256(preimage).digest())


def _message_hash(message: dict[str, Any]) -> str:
    body = copy.deepcopy(message)
    body.pop("message_hash", None)
    body.pop("signatures", None)
    return _object_hash("message", body)


def _source_digest() -> str:
    root = Path(__file__).resolve().parent
    digest = hashlib.sha256()
    for path in sorted(root.glob("*.py")):
        digest.update(path.name.encode("utf-8") + b"\0")
        digest.update(path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n"))
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def _descriptor(role: str) -> dict[str, Any]:
    return {
        "protocol": "aicp.live_endpoint_descriptor.v2",
        "binding_id": "BIND-MCP",
        "binding_version": "0.1",
        "role": role,
        "implementation_kind": "external_implementation",
        "implementation_id": IMPLEMENTATION_ID,
        "implementation_version": IMPLEMENTATION_VERSION,
        "implementation_digest": _source_digest(),
        "declared_features": {
            "request_response": True,
            "sse": False,
            "websocket": False,
            "wss": False,
        },
        "transport": "stdio",
    }


def _write_ready(role: str) -> None:
    target = Path(os.environ["AICP_LIVE_READY_FILE"])
    temporary = target.with_suffix(".tmp")
    temporary.write_text(_canonical(_descriptor(role)), encoding="utf-8")
    temporary.replace(target)


def _pairwise_descriptor(role: str, behavior: str) -> dict[str, Any]:
    side = os.environ.get("AICP_PAIRWISE_SIDE")
    target = os.environ.get("AICP_PAIRWISE_TARGET")
    declared_role = os.environ.get("AICP_PAIRWISE_ROLE")
    if side not in {"A", "B"} or target != PAIRWISE_TARGET or declared_role != role:
        raise ValueError("strict Pairwise role environment is required")
    descriptor: dict[str, Any] = {
        "protocol": PAIRWISE_DESCRIPTOR_VERSION,
        "side": side,
        "role": role,
        "target_id": target,
        "implementation_kind": "external_implementation",
        "implementation_id": IMPLEMENTATION_ID,
        "implementation_version": IMPLEMENTATION_VERSION,
        "implementation_digest": _source_digest(),
        "transport": "stdio",
    }
    if behavior in {"server_report_identity_mismatch", "client_server_identity_mismatch", "wrong_implementation_id"}:
        descriptor["implementation_id"] = IMPLEMENTATION_ID + "-mismatch"
    elif behavior == "wrong_implementation_version":
        descriptor["implementation_version"] = "wrong-version"
    elif behavior == "wrong_implementation_digest":
        descriptor["implementation_digest"] = "sha256:" + "0" * 64
    elif behavior in {"wrong_server_target", "wrong_client_target"}:
        descriptor["target_id"] = "BIND-WRONG@9.9"
    return descriptor


def _write_pairwise_ready(behavior: str) -> None:
    if behavior == "missing_server_descriptor" or "AICP_PAIRWISE_READY_FILE" not in os.environ:
        return
    target = Path(os.environ["AICP_PAIRWISE_READY_FILE"])
    temporary = target.with_suffix(".tmp")
    if behavior == "malformed_server_descriptor":
        temporary.write_text("{malformed", encoding="utf-8")
    else:
        temporary.write_text(_canonical(_pairwise_descriptor("server", behavior)), encoding="utf-8")
    temporary.replace(target)


def _rpc_result(request_id: Any, value: dict[str, Any]) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "result": value}


def _rpc_error(request_id: Any, code: int, message: str) -> dict[str, Any]:
    return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}


class MessageStore:
    def __init__(self, behavior: str = "good") -> None:
        self.behavior = behavior
        self.messages: dict[str, list[dict[str, Any]]] = {}
        self.ids: dict[tuple[str, str], dict[str, Any]] = {}
        self.cursors: dict[str, dict[str, int]] = {}

    def _cursor(self, session: str, offset: int) -> str:
        values = self.cursors.setdefault(session, {"c0": 0})
        for cursor, known in values.items():
            if known == offset:
                return cursor
        token = "c" + str(offset) + "-" + hashlib.sha256(
            f"{session}:{offset}".encode("utf-8")
        ).hexdigest()[:16]
        values[token] = offset
        return token

    def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        request_id = request.get("id")
        if request.get("jsonrpc") != "2.0" or request.get("method") != "tools/call":
            return _rpc_error(request_id, -32600, "invalid request")
        params = request.get("params")
        if not isinstance(params, dict) or not isinstance(params.get("arguments"), dict):
            return _rpc_error(request_id, -32602, "invalid params")
        tool = params.get("name")
        arguments = params["arguments"]
        if tool == "aicp.sendMessage":
            message = arguments.get("message")
            if not isinstance(message, dict) or not all(
                isinstance(message.get(field), str) and message.get(field)
                for field in ("session_id", "message_id", "message_hash")
            ):
                return _rpc_error(request_id, -32602, "invalid AICP envelope")
            if _message_hash(message) != message.get("message_hash"):
                return _rpc_error(request_id, -32602, "message hash mismatch")
            session = message["session_id"]
            key = (session, message["message_id"])
            prior = self.ids.get(key)
            if prior is not None and prior != message:
                return _rpc_error(request_id, -32602, "conflicting duplicate message id")
            if prior is None:
                stored = copy.deepcopy(message)
                if self.behavior == "server_rewrites_message":
                    stored["sender"] = "rewritten-by-server"
                self.ids[key] = stored
                self.messages.setdefault(session, []).append(stored)
            return _rpc_result(
                request_id,
                {
                    "accepted": True,
                    "message_id": message["message_id"],
                    "message_hash": message["message_hash"],
                },
            )
        if tool == "aicp.pollMessages":
            session = arguments.get("session_id")
            after = arguments.get("after_cursor")
            if not isinstance(session, str) or not isinstance(after, str):
                return _rpc_error(request_id, -32602, "session_id and after_cursor are required")
            values = self.cursors.setdefault(session, {"c0": 0})
            if after not in values:
                return _rpc_error(request_id, -32602, "unknown after_cursor")
            try:
                limit = max(0, min(int(arguments.get("limit", 1000)), 1000))
            except (TypeError, ValueError):
                return _rpc_error(request_id, -32602, "invalid limit")
            start = values[after]
            selected = copy.deepcopy(self.messages.get(session, [])[start : start + limit])
            if self.behavior == "server_returns_another_session_message" and selected:
                selected[0]["session_id"] = "another-session"
            return _rpc_result(
                request_id,
                {"messages": selected, "next_cursor": self._cursor(session, start + len(selected))},
            )
        if tool == "aicp.getHead":
            session = str(arguments.get("session_id", ""))
            messages = self.messages.get(session, [])
            return _rpc_result(
                request_id,
                {
                    "session_state": {"session_id": session},
                    "branch_heads": [
                        {
                            "branch_id": "main",
                            "head_message_id": messages[-1]["message_id"] if messages else None,
                        }
                    ],
                    "active_head_version": "v1",
                },
            )
        if tool == "aicp.getObject":
            requested = arguments.get("object_hash")
            expected = _object_hash("contract", OBJECT_VALUE)
            if requested != expected:
                return _rpc_result(request_id, {"status": "NOT_FOUND"})
            return _rpc_result(
                request_id,
                {"status": "FOUND", "object_type": "contract", "object_json": OBJECT_VALUE},
            )
        return _rpc_error(request_id, -32601, "tool not found")


def _server_loop(behavior: str = "good") -> int:
    store = MessageStore(behavior)
    for index, raw in enumerate(sys.stdin.buffer, start=1):
        if index > 256 or len(raw) > 1_048_576:
            return 2
        try:
            request = json.loads(raw.decode("utf-8"))
            response = store.handle(request) if isinstance(request, dict) else _rpc_error(None, -32600, "invalid request")
        except (UnicodeDecodeError, json.JSONDecodeError):
            response = _rpc_error(None, -32700, "parse error")
        sys.stdout.write(_canonical(response) + "\n")
        sys.stdout.flush()
    return 0


def _rpc_request(request_id: str, tool: str, arguments: dict[str, Any]) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": "tools/call",
        "params": {"name": tool, "arguments": arguments},
    }


def _binding_client_loop() -> int:
    scenario = json.loads(Path(os.environ["AICP_LIVE_SCENARIO_FILE"]).read_text(encoding="utf-8"))
    messages: list[dict[str, Any]] = []
    for source in scenario["input_messages"]:
        message = copy.deepcopy(source)
        message["session_id"] = "sGT1"
        message.pop("signatures", None)
        message.pop("message_hash", None)
        message["message_hash"] = _message_hash(message)
        messages.append(message)
    requests = [
        _rpc_request("rpc-send-1", "aicp.sendMessage", {"message": messages[0]}),
        _rpc_request("rpc-send-2", "aicp.sendMessage", {"message": messages[0]}),
        _rpc_request("rpc-send-3", "aicp.sendMessage", {"message": messages[1]}),
        _rpc_request(
            "rpc-poll-1",
            "aicp.pollMessages",
            {"session_id": messages[0]["session_id"], "after_cursor": "c0", "limit": 1},
        ),
    ]
    responses: list[dict[str, Any]] = []
    for request in requests:
        sys.stdout.write(_canonical(request) + "\n")
        sys.stdout.flush()
        response = json.loads(sys.stdin.readline())
        responses.append(response)
    cursor = responses[-1]["result"]["next_cursor"]
    remaining = [
        _rpc_request("rpc-poll-2", "aicp.pollMessages", {"session_id": messages[0]["session_id"], "after_cursor": cursor, "limit": 1}),
        _rpc_request("rpc-head-1", "aicp.getHead", {"session_id": messages[0]["session_id"]}),
        _rpc_request("rpc-object-1", "aicp.getObject", {"object_hash": _object_hash("contract", OBJECT_VALUE)}),
        _rpc_request("rpc-object-2", "aicp.getObject", {"object_hash": "sha256:" + "A" * 43}),
        _rpc_request("rpc-invalid-1", "aicp.sendMessage", {"message": {"session_id": messages[0]["session_id"]}}),
    ]
    for request in remaining:
        sys.stdout.write(_canonical(request) + "\n")
        sys.stdout.flush()
        if not sys.stdin.readline():
            return 3
    return 0


def _make_message(
    *,
    session: str,
    contract: str,
    message_id: str,
    sender: str,
    message_type: str,
    payload: dict[str, Any],
    previous: str | None,
    timestamp: str,
) -> dict[str, Any]:
    message: dict[str, Any] = {
        "session_id": session,
        "message_id": message_id,
        "timestamp": timestamp,
        "sender": sender,
        "message_type": message_type,
        "contract_id": contract,
        "contract_ref": {"branch_id": "main", "base_version": "v1", "head_version": "v1"},
        "payload": payload,
    }
    if previous is not None:
        message["prev_msg_hash"] = previous
    message["message_hash"] = _message_hash(message)
    return message


def _scenario_messages(scenario: dict[str, Any]) -> list[dict[str, Any]]:
    session = str(scenario["session_id"])
    contract_id = str(scenario["contract_id"])
    seed = str(scenario["deterministic_seed"])
    desired = list(scenario["desired_message_types"])
    messages: list[dict[str, Any]] = []
    previous: str | None = None
    amendments: list[dict[str, Any]] = []
    for index, message_type in enumerate(desired, start=1):
        sender = "agent:A" if index % 2 else "agent:B"
        if message_type == "CONTRACT_PROPOSE":
            contract = {"contract_id": contract_id, "goal": seed, "roles": list(scenario["participants"])}
            if "consent-grant" in seed:
                contract["policies"] = [{"policy_id": "consent", "category": "user_consent", "parameters": {"required": True, "scope": "share_profile"}, "status": "active"}]
            elif "consent-revoke" in seed:
                contract["policies"] = [{"policy_id": "consent", "category": "user_consent", "parameters": {"required": True, "scope": "payments"}, "status": "active"}]
            payload = {"contract": contract, "contract_hash": _object_hash("contract", contract)}
        elif message_type == "CONTRACT_ACCEPT":
            payload = {"accepted": True}
        elif message_type == "CONTEXT_AMEND":
            if "consent-grant" in seed:
                payload = {"amendment": {"consent_ref": "consent:a", "consent_status": "granted", "consent_scope": "share_profile"}}
            elif "consent-revoke" in seed:
                status = "granted" if not amendments else "revoked"
                payload = {"amendment": {"consent_ref": "consent:a", "consent_status": status, **({"consent_scope": "payments"} if status == "granted" else {"reason": "user_revoked"})}}
            else:
                payload = {"amendment": {"amend_id": f"a{index}", "base_version": "v1", "changes": {"choice": index}}}
            amendments.append({"message_id": f"m{index}"})
        elif message_type == "RESOLVE_CONFLICT":
            candidates = [
                {"message_id": item["message_id"], "message_hash": messages[int(item["message_id"][1:]) - 1]["message_hash"]}
                for item in amendments[-2:]
            ]
            payload = {"conflict_id": "conflict-a", "conflict_class": "CONCURRENT_AMEND", "candidates": candidates, "resolution": {"type": "CHOOSE", "chosen_message_id": candidates[0]["message_id"], "chosen_message_hash": candidates[0]["message_hash"]}}
        elif message_type == "STATE_SYNC_REQUEST":
            payload = {"request_id": "sync-a", "known_heads": ["v999"]}
        elif message_type == "STATE_SYNC_RESPONSE":
            payload = {"request_id": "sync-a", "session_state": "active", "branch_heads": ["v1"], "active_head_version": "v1"}
        elif message_type == "ATTEST_ACTION":
            if "consent-grant" in seed:
                payload = {"action_id": "act-a", "action_type": "share_profile", "consent_ref": "consent:a"}
            elif "consent-revoke" in seed:
                payload = {"action_id": "act-a", "action_type": "payment_attempt", "consent_ref": "consent:a"}
            else:
                payload = {"action_id": "act-a", "action_type": "tools/call", "result_hash": _object_hash("result", {"seed": seed})}
        elif message_type == "ERROR":
            payload = {"error_code": "TEST_ERROR", "error_class": "VALIDATION", "severity": "low", "applies_to": {"message_id": "none"}, "disposition": "REJECTED"}
        else:
            raise ValueError(f"unsupported producer message type: {message_type}")
        message = _make_message(
            session=session,
            contract=contract_id,
            message_id=f"m{index}",
            sender=sender,
            message_type=message_type,
            payload=payload,
            previous=previous,
            timestamp=f"2026-01-01T00:00:{index:02d}Z",
        )
        messages.append(message)
        previous = message["message_hash"]
    return messages


def _verify_signatures(message: dict[str, Any], keys: dict[str, Any]) -> bool:
    signatures = message.get("signatures")
    if not signatures:
        return True
    try:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

        for signature in signatures:
            if signature.get("object_type") != "message" or signature.get("object_hash") != message.get("message_hash"):
                return False
            material = keys[signature["signer"]]
            if material["kid"] != signature["kid"]:
                return False
            raw_key = base64.urlsafe_b64decode(material["public_key_b64url"] + "==")
            raw_sig = base64.urlsafe_b64decode(signature["sig_b64url"] + "==")
            signed = f"AICP1\0SIG\0{message['message_hash']}".encode("utf-8")
            Ed25519PublicKey.from_public_bytes(raw_key).verify(raw_sig, signed)
        return True
    except Exception:
        return False


def _validate_transcript(input_obj: dict[str, Any]) -> dict[str, Any]:
    messages = input_obj.get("transcript")
    keys = input_obj.get("public_verification_material") or {}
    errors: list[dict[str, str]] = []
    if not isinstance(messages, list):
        errors.append({"code": "schema", "message": "transcript must be an array"})
    else:
        seen: set[str] = set()
        previous: str | None = None
        for index, message in enumerate(messages):
            if not isinstance(message, dict):
                errors.append({"code": "schema", "message": f"message {index} is not an object"})
                continue
            for field in ("session_id", "message_id", "timestamp", "sender", "message_type"):
                if not isinstance(message.get(field), str) or not message[field]:
                    errors.append({"code": "schema", "message": f"message {index} has invalid {field}"})
            if not isinstance(message.get("contract_id"), str) or not message["contract_id"]:
                errors.append({"code": "schema", "message": f"message {index} has invalid contract_id"})
            message_id = message.get("message_id")
            if message_id in seen:
                errors.append({"code": "replay", "message": "duplicate message_id"})
            if isinstance(message_id, str):
                seen.add(message_id)
            if index and message.get("prev_msg_hash") != previous:
                errors.append({"code": "chain", "message": "prev_msg_hash mismatch"})
            expected = _message_hash(message)
            if message.get("message_hash") != expected:
                errors.append({"code": "hash", "message": "message_hash mismatch"})
            if not _verify_signatures(message, keys):
                errors.append({"code": "signature", "message": "signature verification failed"})
            previous = message.get("message_hash")
    return {"accepted": not errors, "errors": errors, "degraded": False, "degraded_reasons": [], "skipped_checks": []}


def _iut_loop() -> int:
    for raw in sys.stdin:
        if not raw.strip():
            continue
        request: dict[str, Any] = {}
        try:
            request = json.loads(raw)
            operation = request.get("operation")
            input_obj = request.get("input") or {}
            if operation == "describe":
                result = {
                    "adapter_protocol_version": ADAPTER_VERSION,
                    "implementation_kind": "external_implementation",
                    "implementation_id": IMPLEMENTATION_ID,
                    "implementation_version": IMPLEMENTATION_VERSION,
                    "implementation_digest": _source_digest(),
                    "supported_aicp_profiles": ["AICP-BASE@0.1"],
                    "supported_crypto_profiles": ["aicp.crypto.ed25519.v1"],
                    "supported_capabilities": [],
                }
            elif operation == "canonicalize_hash":
                result = {"canonical_json": _canonical(input_obj.get("object")), "object_hash": _object_hash(str(input_obj.get("object_type")), input_obj.get("object"))}
            elif operation == "validate_transcript":
                result = _validate_transcript(input_obj)
            elif operation == "generate_scenario":
                result = {"artifact": _scenario_messages(input_obj["scenario"])}
            else:
                raise ValueError(f"unsupported operation: {operation}")
            response = {"adapter_protocol_version": ADAPTER_VERSION, "request_id": request.get("request_id"), "operation": operation, "success": True, "result": result}
        except Exception as exc:
            response = {"adapter_protocol_version": ADAPTER_VERSION, "request_id": request.get("request_id"), "operation": request.get("operation"), "success": False, "error": {"code": "adapter_error", "message": str(exc)}}
        sys.stdout.write(_canonical(response) + "\n")
        sys.stdout.flush()
    return 0


def _construct(control: dict[str, Any], behavior: str) -> dict[str, Any]:
    input_obj = control.get("input") or {}
    phase = input_obj.get("phase")
    session = str(input_obj["session_id"])
    contract = str(input_obj["contract_id"])
    side = str(input_obj["side"])
    sender = IMPLEMENTATION_ID
    peer = input_obj.get("peer_message")
    if phase == "propose":
        payload = {"contract": {"contract_id": contract, "goal": str(input_obj["challenge"]), "roles": ["initiator", "responder"]}}
        if behavior == "missing_contract_goal":
            payload["contract"].pop("goal")
        elif behavior in {"ignore_challenge", "prebuilt_proposal"}:
            payload["contract"]["goal"] = "static-prebuilt-pairwise-goal"
        elif behavior == "previous_run_challenge":
            payload["contract"]["goal"] = "challenge-from-a-previous-run"
        payload["contract_hash"] = _object_hash("contract", payload["contract"])
        previous = None
        message_type = "CONTRACT_PROPOSE"
    elif phase == "accept":
        if not isinstance(peer, dict) or peer.get("message_type") != "CONTRACT_PROPOSE" or _message_hash(peer) != peer.get("message_hash"):
            raise ValueError("accept requires the actual valid peer proposal")
        payload = {"accepted": True}
        previous = str(peer["message_hash"])
        message_type = "CONTRACT_ACCEPT"
    elif phase == "attest":
        if not isinstance(peer, dict) or peer.get("message_type") != "CONTRACT_ACCEPT" or _message_hash(peer) != peer.get("message_hash"):
            raise ValueError("attest requires the actual valid peer acceptance")
        payload = {"action_id": f"{input_obj['run_id']}:{side}:final", "action_type": "pairwise_cross_consumption", "result_hash": _object_hash("result", {"peer_hash": peer["message_hash"]})}
        previous = str(peer["message_hash"])
        message_type = "ATTEST_ACTION"
    else:
        raise ValueError("unsupported construction phase")
    if behavior == "hardcoded_hash" and phase in {"accept", "attest"}:
        previous = "sha256:" + "A" * 43
    message = _make_message(
        session=session,
        contract=contract,
        message_id=str(input_obj["message_id"]),
        sender=sender,
        message_type=message_type,
        payload=payload,
        previous=previous,
        timestamp=str(input_obj["timestamp"]),
    )
    if behavior == "wrong_session" and phase != "propose":
        message["session_id"] = "wrong-session"
        message["message_hash"] = _message_hash(message)
    if behavior == "wrong_contract" and phase != "propose":
        message["contract_id"] = "wrong-contract"
        message["message_hash"] = _message_hash(message)
    if behavior == "malformed_contract_ref" and phase == "propose":
        message["contract_ref"] = {"branch_id": "main"}
        message["message_hash"] = _message_hash(message)
    if behavior == "invalid_contract_accept_payload" and phase == "accept":
        message["payload"] = {"accepted": True, "unexpected": "not-in-Core-v0.1"}
        message["message_hash"] = _message_hash(message)
    if behavior == "invalid_attest_action_payload" and phase == "attest":
        message["payload"]["unexpected"] = "not-in-Core-v0.1"
        message["message_hash"] = _message_hash(message)
    return message


def _control_loop(behavior: str) -> int:
    for raw in sys.stdin:
        if not raw.strip():
            continue
        request: dict[str, Any] = {}
        try:
            request = json.loads(raw)
            if request.get("control_version") != CONTROL_VERSION:
                raise ValueError("unsupported control version")
            operation = request.get("operation")
            if operation == "describe":
                result = {
                    "implementation_kind": "external_implementation",
                    "implementation_id": IMPLEMENTATION_ID,
                    "implementation_version": IMPLEMENTATION_VERSION,
                    "implementation_digest": _source_digest(),
                    "supported_target": "AICP-BASE@0.1+BIND-MCP@0.1",
                }
            elif operation == "construct":
                result = {"message": _construct(request, behavior)}
            else:
                raise ValueError("unsupported control operation")
            response = {"control_version": CONTROL_VERSION, "request_id": request.get("request_id"), "operation": operation, "success": True, "result": result}
        except Exception as exc:
            response = {"control_version": CONTROL_VERSION, "request_id": request.get("request_id"), "operation": request.get("operation"), "success": False, "error": {"code": "peer_error", "message": str(exc)}}
        sys.stdout.write(_canonical(response) + "\n")
        sys.stdout.flush()
    return 0


def _client_control_response(request: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    return {
        "control_version": CLIENT_CONTROL_VERSION,
        "request_id": request.get("request_id"),
        "operation": request.get("operation"),
        "success": True,
        "result": result,
    }


def _pairwise_client_loop(behavior: str) -> int:
    sessions: dict[str, dict[str, Any]] = {}
    pending: dict[str, dict[str, Any]] = {}
    process_visible_hashes: list[str] = []
    counter = 0
    for raw in sys.stdin:
        if not raw.strip():
            continue
        request: dict[str, Any] = {}
        try:
            request = json.loads(raw)
            if request.get("control_version") != CLIENT_CONTROL_VERSION:
                raise ValueError("unsupported Pairwise client control version")
            operation = request.get("operation")
            input_obj = request.get("input") or {}
            if operation == "describe":
                result = _pairwise_descriptor("client", behavior)
            elif operation == "begin_phase":
                counter += 1
                phase = str(input_obj.get("phase"))
                session = str(input_obj["session_id"])
                state = sessions.setdefault(
                    session,
                    {
                        "cursor": "c0",
                        "visible": process_visible_hashes,
                        "proposal": None,
                        "acceptance": None,
                        "attestation": None,
                        "challenge": None,
                    },
                )
                if "preseed_challenge" in input_obj:
                    state["challenge"] = input_obj["preseed_challenge"]
                if isinstance(input_obj.get("preseed_peer_message"), dict):
                    preseed = copy.deepcopy(input_obj["preseed_peer_message"])
                    if preseed.get("message_type") == "CONTRACT_PROPOSE":
                        state["proposal"] = preseed
                    elif preseed.get("message_type") == "CONTRACT_ACCEPT":
                        state["acceptance"] = preseed
                if phase == "propose":
                    state["challenge"] = input_obj["challenge"]
                    message_input = dict(input_obj)
                    message_input["peer_message"] = None
                    message = _construct({"input": message_input}, behavior)
                    tool = "aicp.sendMessage"
                    arguments = {"message": message}
                    expected_type = None
                elif phase in {"accept", "attest"}:
                    peer_key = "proposal" if phase == "accept" else "acceptance"
                    peer = state.get(peer_key)
                    if not isinstance(peer, dict):
                        raise ValueError(f"{phase} requires a peer artifact learned by this client")
                    message_input = dict(input_obj)
                    message_input["challenge"] = state.get("challenge") or "not-preseeded"
                    message_input["peer_message"] = copy.deepcopy(peer)
                    peer_behavior = "hardcoded_hash" if behavior == "hardcoded_peer_hash" else behavior
                    message = _construct({"input": message_input}, peer_behavior)
                    if behavior in {"stale_peer_hash", "previous_run_peer_hash", "wrong_prev_msg_hash"}:
                        suffix = {
                            "stale_peer_hash": "B",
                            "previous_run_peer_hash": "C",
                            "wrong_prev_msg_hash": "D",
                        }[behavior]
                        message["prev_msg_hash"] = "sha256:" + suffix * 43
                        message["message_hash"] = _message_hash(message)
                    tool = "aicp.sendMessage"
                    arguments = {"message": message}
                    expected_type = None
                elif phase in {"poll_proposal", "poll_acceptance", "poll_attestation"}:
                    message = None
                    tool = "aicp.pollMessages"
                    arguments = {
                        "session_id": session,
                        "after_cursor": state["cursor"],
                        "limit": 1,
                    }
                    if phase == "poll_attestation" and behavior in {
                        "stale_final_poll_cursor",
                        "hardcoded_c0_final_poll",
                    }:
                        arguments["after_cursor"] = "c0"
                    if behavior == "unrelated_cursor":
                        arguments["after_cursor"] = "c-unrelated"
                    if behavior == "missing_poll_limit":
                        arguments.pop("limit")
                    if behavior == "wrong_poll_limit":
                        arguments["limit"] = 2
                    if behavior == "wrong_poll_session":
                        arguments["session_id"] = session + "-wrong"
                    expected_type = {
                        "poll_proposal": "CONTRACT_PROPOSE",
                        "poll_acceptance": "CONTRACT_ACCEPT",
                        "poll_attestation": "ATTEST_ACTION",
                    }[phase]
                else:
                    raise ValueError("unsupported Pairwise client phase")
                rpc_id = "rpc-" + hashlib.sha256(
                    f"{request.get('request_id')}:{counter}:{tool}".encode("utf-8")
                ).hexdigest()[:24]
                mcp_request = _rpc_request(rpc_id, tool, arguments)
                exchange_id = "exchange-" + hashlib.sha256(
                    f"{request.get('request_id')}:{counter}".encode("utf-8")
                ).hexdigest()[:24]
                pending[exchange_id] = {
                    "phase": phase,
                    "session": session,
                    "destination_side": str(input_obj["destination_side"]),
                    "request": copy.deepcopy(mcp_request),
                    "message": copy.deepcopy(message),
                    "expected_type": expected_type,
                }
                result = {
                    "event": "mcp_request",
                    "phase": phase,
                    "exchange_id": exchange_id,
                    "destination_side": str(input_obj["destination_side"]),
                    "request": mcp_request,
                    "request_json": _canonical(mcp_request),
                    "client_visible_hashes_before": list(state["visible"]),
                }
            elif operation == "mcp_response":
                exchange_id = str(input_obj.get("exchange_id"))
                item = pending.pop(exchange_id, None)
                if not isinstance(item, dict):
                    raise ValueError("unknown Pairwise client exchange")
                if input_obj.get("source_side") != item["destination_side"]:
                    raise ValueError("MCP response came from the wrong server side")
                response_json = input_obj.get("response_json")
                if not isinstance(response_json, str):
                    raise ValueError("exact MCP response JSON is required")
                response = json.loads(response_json)
                if not isinstance(response, dict) or response.get("jsonrpc") != "2.0":
                    raise ValueError("invalid MCP response")
                if response.get("id") != item["request"].get("id") or "error" in response:
                    raise ValueError("MCP response correlation failed")
                response_result = response.get("result")
                if not isinstance(response_result, dict):
                    raise ValueError("MCP response result is required")
                state = sessions[item["session"]]
                phase = item["phase"]
                if item["request"]["params"]["name"] == "aicp.sendMessage":
                    message = item["message"]
                    if response_result.get("accepted") is not True or response_result.get("message_hash") != message.get("message_hash"):
                        raise ValueError("server did not accept the exact client-authored message")
                    result = {"event": "phase_complete", "phase": phase, "message": message}
                else:
                    messages = response_result.get("messages")
                    if not isinstance(messages, list) or len(messages) != 1 or not isinstance(messages[0], dict):
                        raise ValueError("client poll must consume exactly one peer message")
                    observed = copy.deepcopy(messages[0])
                    if observed.get("message_type") != item["expected_type"]:
                        raise ValueError("client poll returned the wrong message type")
                    if observed.get("session_id") != item["session"] or _message_hash(observed) != observed.get("message_hash"):
                        raise ValueError("client poll returned an invalid peer message")
                    before = list(state["visible"])
                    state["visible"].append(observed["message_hash"])
                    state["cursor"] = response_result.get("next_cursor")
                    if not isinstance(state["cursor"], str) or not state["cursor"]:
                        raise ValueError("client poll returned no continuation cursor")
                    key = {
                        "CONTRACT_PROPOSE": "proposal",
                        "CONTRACT_ACCEPT": "acceptance",
                        "ATTEST_ACTION": "attestation",
                    }[observed["message_type"]]
                    stored = copy.deepcopy(observed)
                    if behavior == "rewritten_peer_message" and key in {"proposal", "acceptance"}:
                        stored["sender"] = "client-local-rewrite"
                        stored["message_hash"] = _message_hash(stored)
                    state[key] = stored
                    if key == "proposal":
                        state["challenge"] = observed.get("payload", {}).get("contract", {}).get("goal")
                    result = {
                        "event": "phase_complete",
                        "phase": phase,
                        "observed_message": observed,
                        "client_visible_hashes_before": before,
                        "client_visible_hashes_after": list(state["visible"]),
                    }
            else:
                raise ValueError("unsupported Pairwise client operation")
            response = _client_control_response(request, result)
        except Exception as exc:
            response = {
                "control_version": CLIENT_CONTROL_VERSION,
                "request_id": request.get("request_id"),
                "operation": request.get("operation"),
                "success": False,
                "error": {"code": "pairwise_client_error", "message": str(exc)},
            }
        sys.stdout.write(_canonical(response) + "\n")
        sys.stdout.flush()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("iut", "binding-server", "binding-client", "pairwise-server", "pairwise-client", "pairwise-control", "self-test"))
    parser.add_argument("--behavior", default="good")
    args = parser.parse_args()
    if args.mode == "iut":
        return _iut_loop()
    if args.mode == "binding-server":
        _write_ready("server_under_test")
        return _server_loop()
    if args.mode == "binding-client":
        _write_ready("client_under_test")
        return _binding_client_loop()
    if args.mode == "pairwise-server":
        _write_pairwise_ready(args.behavior)
        return _server_loop(args.behavior)
    if args.mode == "pairwise-client":
        return _pairwise_client_loop(args.behavior)
    if args.mode == "pairwise-control":
        return _control_loop(args.behavior)
    assert _object_hash("contract", OBJECT_VALUE) == "sha256:wKY_CpI6-HtaTMTpufl-eTjXYQXv8Igzv7DFBjdDkS4"
    assert _source_digest().startswith("sha256:")
    print("peer A self-test passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
