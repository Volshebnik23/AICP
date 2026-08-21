from __future__ import annotations

import base64
import copy
import hashlib
from typing import Any

from target_catalog import canonical_digest


RFC6455_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
SESSION_FIELDS = {"session_id"}
CURSOR_FIELDS = {"cursor", "next_cursor", "after", "after_cursor", "min_cursor", "id"}


def websocket_accept(key: str) -> str:
    return base64.b64encode(
        hashlib.sha1((key + RFC6455_GUID).encode("ascii")).digest()
    ).decode("ascii")


def _collect(value: Any, field_names: set[str], result: dict[str, str], prefix: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if key in field_names and isinstance(child, str) and child:
                result.setdefault(child, f"{prefix}:{len(result) + 1}")
            _collect(child, field_names, result, prefix)
    elif isinstance(value, list):
        for child in value:
            _collect(child, field_names, result, prefix)


def _normalize_ws(exchange: dict[str, Any]) -> None:
    request_headers = exchange.get("request", {}).get("headers", {})
    response_headers = exchange.get("response", {}).get("headers", {})
    key = request_headers.get("sec-websocket-key")
    accept = response_headers.get("sec-websocket-accept")
    if isinstance(key, str) and key:
        valid = isinstance(accept, str) and accept == websocket_accept(key)
        request_headers["sec-websocket-key"] = "ws-key"
        if isinstance(accept, str):
            response_headers["sec-websocket-accept"] = (
                "valid-ws-accept" if valid else "invalid-ws-accept"
            )


def _replace(value: Any, mappings: list[dict[str, str]]) -> Any:
    if isinstance(value, dict):
        candidate = copy.deepcopy(value)
        if isinstance(candidate.get("scheme"), str):
            _normalize_ws(candidate)
        return {key: _replace(child, mappings) for key, child in candidate.items()}
    if isinstance(value, list):
        return [_replace(child, mappings) for child in value]
    if isinstance(value, str):
        for mapping in mappings:
            if value in mapping:
                return mapping[value]
        if value.startswith("/aicp/v1/sessions/"):
            result = value
            for mapping in mappings:
                for raw, symbol in sorted(mapping.items(), key=lambda item: -len(item[0])):
                    if raw and raw in result:
                        result = result.replace(raw, symbol)
            return result
        return value
    return value


def normalize_v2_run(run: dict[str, Any]) -> dict[str, Any]:
    interactions = run.get("interactions")
    ordered = sorted(
        copy.deepcopy(interactions if isinstance(interactions, list) else []),
        key=lambda item: (
            str(item.get("role", "")),
            str(item.get("scenario_id", "")),
            str(item.get("interaction_id", "")),
        ),
    )
    sessions: dict[str, str] = {}
    cursors: dict[str, str] = {}
    requests: dict[str, str] = {}
    _collect(ordered, SESSION_FIELDS, sessions, "session")
    _collect(ordered, CURSOR_FIELDS - {"id"}, cursors, "cursor")
    for interaction in ordered:
        evidence = interaction.get("transport_evidence", {})
        if evidence.get("kind") == "mcp_stdio":
            _collect(evidence.get("exchanges", []), {"id"}, requests, "request")
    return {"interactions": _replace(ordered, [sessions, cursors, requests])}


def semantic_digest_v2(run: dict[str, Any]) -> str:
    return canonical_digest(normalize_v2_run(run))
