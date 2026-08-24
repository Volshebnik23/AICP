from __future__ import annotations

import copy
from typing import Any

from live_bindings.live_http_capture import message_ref


def _arguments(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, Any] = {}
    for name in ("session_id", "after_cursor", "object_hash"):
        if isinstance(value.get(name), str):
            result[name] = value[name]
    if isinstance(value.get("limit"), int):
        result["limit"] = value["limit"]
    ref = message_ref(value.get("message"))
    if ref is not None:
        result["message_ref"] = ref
    elif "message" in value:
        result["malformed_message"] = True
    return result


def _result(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, Any] = {}
    for name in (
        "message_id",
        "message_hash",
        "cursor",
        "next_cursor",
        "status",
        "object_type",
    ):
        if isinstance(value.get(name), str):
            result[name] = value[name]
    if isinstance(value.get("accepted"), bool):
        result["accepted"] = value["accepted"]
    messages = value.get("messages")
    if isinstance(messages, list):
        result["message_refs"] = [item for item in (message_ref(message) for message in messages) if item]
    state = value.get("session_state")
    if isinstance(state, dict) and isinstance(state.get("session_id"), str):
        result["session_id"] = state["session_id"]
    if isinstance(value.get("object_json"), dict):
        obj = value["object_json"]
        result["object_content"] = {
            "contract_id": str(obj.get("contract_id", "")),
            "goal": str(obj.get("goal", "")),
            "roles": [str(item) for item in obj.get("roles", []) if isinstance(item, str)],
        }
    return result


def safe_mcp_exchange(request: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    params = request.get("params") if isinstance(request.get("params"), dict) else {}
    safe_response: dict[str, Any] = {
        "jsonrpc": str(response.get("jsonrpc", "")),
        "id": str(response.get("id", "")),
        "outcome": "result" if "result" in response and "error" not in response else "error",
    }
    if "result" in response:
        safe_response["result"] = _result(response.get("result"))
    if isinstance(response.get("error"), dict):
        safe_response["error_code"] = int(response["error"].get("code", 0))
    return {
        "request": {
            "jsonrpc": str(request.get("jsonrpc", "")),
            "id": str(request.get("id", "")),
            "method": str(request.get("method", "")),
            "tool": str(params.get("name", "")),
            "arguments": _arguments(params.get("arguments")),
        },
        "response": safe_response,
    }


def attach_mcp_transport_evidence(
    interactions: list[dict[str, Any]],
    exchanges: list[tuple[dict[str, Any], dict[str, Any]]],
    *,
    role: str,
) -> list[dict[str, Any]]:
    safe = [safe_mcp_exchange(request, response) for request, response in exchanges]
    for interaction in interactions:
        scenario_id = str(interaction.get("scenario_id", ""))
        selected: list[dict[str, Any]]
        if scenario_id.endswith("-SEND"):
            selected = safe[:1]
        elif scenario_id.endswith("-DUPLICATE"):
            selected = safe[:2]
        elif scenario_id.endswith("-POLL"):
            # Poll causality is evaluated from the complete client-visible
            # response prefix, not from an isolated pair that could hide an
            # earlier disclosure of the continuation token.
            selected = safe[:5] if role == "client_under_test" else safe[3:5]
        elif scenario_id.endswith("-HEAD"):
            selected = safe[5:6]
        elif scenario_id.endswith("-OBJECT"):
            selected = safe[6:8]
        else:
            selected = safe
        interaction.pop("observations", None)
        interaction["transport_evidence"] = {
            "kind": "mcp_stdio",
            "boundary": {
                "kind": "child_process_stdio",
                "transport_kind": "stdio",
                "child_process_role": role,
            },
            "exchanges": copy.deepcopy(selected),
        }
    return interactions
