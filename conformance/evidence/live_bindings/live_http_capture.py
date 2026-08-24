from __future__ import annotations

import copy
from typing import Any
from urllib.parse import urlsplit


SAFE_HEADER_VALUES = {
    "content-type",
    "idempotency-key",
    "aicp-replay",
    "retry-after",
    "ratelimit-limit",
    "ratelimit-remaining",
    "ratelimit-reset",
    "last-event-id",
    "upgrade",
    "connection",
    "sec-websocket-key",
    "sec-websocket-accept",
    "sec-websocket-version",
}
FORBIDDEN_HEADERS = {
    "authorization",
    "cookie",
    "set-cookie",
    "proxy-authorization",
}


def idempotency_key_valid(key: Any, message_id: Any) -> bool:
    if not isinstance(key, str) or not key:
        return False
    if not isinstance(message_id, str) or not message_id:
        return False
    if key == message_id:
        return True
    if not key.endswith(message_id):
        return False
    prefix = key[: -len(message_id)]
    return bool(prefix) and prefix[-1] in "-:/"


def message_ref(message: Any) -> dict[str, Any] | None:
    if not isinstance(message, dict):
        return None
    required = ("session_id", "message_id", "message_hash")
    if not all(isinstance(message.get(name), str) and message.get(name) for name in required):
        return None
    from target_catalog import canonical_digest

    result = {
        "session_id": str(message["session_id"]),
        "message_id": str(message["message_id"]),
        "message_hash": str(message["message_hash"]),
        "canonical_digest": canonical_digest(message),
    }
    previous = message.get("prev_msg_hash")
    if isinstance(previous, str) and previous:
        result["prev_msg_hash"] = previous
    return result


def body_summary(body: Any) -> dict[str, Any]:
    from target_catalog import canonical_digest

    if body is None:
        return {"kind": "none"}
    if not isinstance(body, dict):
        return {"kind": "invalid"}
    direct = message_ref(body)
    if direct is not None:
        return {"kind": "message", "message_refs": [direct]}
    result: dict[str, Any] = {"kind": "semantic", "canonical_digest": canonical_digest(body)}
    messages = body.get("messages")
    if isinstance(messages, list):
        result["message_refs"] = [item for item in (message_ref(value) for value in messages) if item]
    for name in (
        "session_id",
        "cursor",
        "next_cursor",
        "reason_code",
        "min_cursor",
        "message_id",
        "message_hash",
        "branch_id",
        "head_message_id",
        "head_message_hash",
        "client_id",
        "retry_after",
    ):
        value = body.get(name)
        if isinstance(value, str):
            result[name] = value
    for name in ("accepted", "auth_required", "more"):
        value = body.get(name)
        if isinstance(value, bool):
            result[name] = value
    return result


def safe_headers(headers: Any) -> dict[str, str]:
    if not isinstance(headers, dict):
        return {}
    return {
        str(name).lower(): str(value)
        for name, value in headers.items()
        if str(name).lower() in SAFE_HEADER_VALUES
    }


def request_summary(record: dict[str, Any]) -> dict[str, Any]:
    headers = {
        str(name).lower(): str(value)
        for name, value in (record.get("headers") or {}).items()
    }
    parsed = urlsplit(str(record.get("path", "")))
    query = record.get("query") if isinstance(record.get("query"), dict) else {}
    safe_query: dict[str, Any] = {}
    for name in ("after", "limit"):
        value = query.get(name)
        if name == "limit" and isinstance(value, str) and value.isdigit():
            safe_query[name] = int(value)
        elif isinstance(value, (str, int)):
            safe_query[name] = value
    auth_value = headers.get("authorization", "")
    return {
        "method": str(record.get("method", "")),
        "path": parsed.path or str(record.get("path", "")),
        "query": safe_query,
        "header_names": sorted(
            name for name in headers if name not in FORBIDDEN_HEADERS
        ),
        "headers": safe_headers(headers),
        "authorization_present": bool(auth_value),
        "authorization_scheme": "Bearer" if auth_value.startswith("Bearer ") else "none",
        "body": body_summary(record.get("body")),
    }


def response_summary(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": int(record.get("status", 0)),
        "headers": safe_headers(record.get("response_headers")),
        "body": body_summary(record.get("response_body")),
    }


def safe_exchange(record: dict[str, Any]) -> dict[str, Any]:
    exchange: dict[str, Any] = {
        "request": request_summary(record),
        "response": response_summary(record),
    }
    events = record.get("events")
    if not isinstance(events, list):
        candidate = record.get("response_body")
        events = candidate.get("events") if isinstance(candidate, dict) else None
    if isinstance(events, list):
        safe_events: list[dict[str, Any]] = []
        for event in events:
            if not isinstance(event, dict):
                continue
            data = event.get("data") if isinstance(event.get("data"), dict) else {}
            safe: dict[str, Any] = {
                "event": str(event.get("event", "")),
                "message_refs": [
                    item
                    for item in (message_ref(value) for value in data.get("messages", []))
                    if item
                ],
            }
            if isinstance(event.get("id"), str):
                safe["id"] = event["id"]
            for name in ("cursor_after_last", "retry_after"):
                if isinstance(data.get(name), str):
                    safe[name] = data[name]
            if isinstance(data.get("more"), bool):
                safe["more"] = data["more"]
            safe_events.append(safe)
        exchange["events"] = safe_events
    client_frame = record.get("client_frame")
    if not isinstance(client_frame, dict) and record.get("transport") == "websocket":
        client_frame = record.get("body")
    if isinstance(client_frame, dict):
        frame = client_frame
        exchange["client_frame"] = {
            "type": str(frame.get("type", "")),
            "after": str(frame.get("after", "")),
            "limit": int(frame.get("limit", 0)),
        }
    server_frame = record.get("server_frame")
    if not isinstance(server_frame, dict) and record.get("transport") == "websocket":
        server_frame = record.get("response_body")
    if isinstance(server_frame, dict):
        frame = server_frame
        safe_frame: dict[str, Any] = {
            "type": str(frame.get("type", "")),
            "message_refs": [
                item
                for item in (message_ref(value) for value in frame.get("messages", []))
                if item
            ],
        }
        for name in ("cursor_after_last", "retry_after"):
            if isinstance(frame.get(name), str):
                safe_frame[name] = frame[name]
        if isinstance(frame.get("more"), bool):
            safe_frame["more"] = frame["more"]
        exchange["server_frame"] = safe_frame
    if record.get("scheme") in {"ws", "wss"}:
        exchange["scheme"] = record["scheme"]
        exchange["tls_verified"] = record.get("tls_verified") is True
    return exchange


def _primary_session(records: list[dict[str, Any]]) -> str:
    for record in records:
        if (
            record.get("method") == "POST"
            and record.get("path") == "/aicp/v1/sessions"
            and record.get("status") == 201
        ):
            value = (record.get("response_body") or {}).get("session_id")
            if isinstance(value, str):
                return value
    return ""


def _select_records(scenario_id: str, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    primary = _primary_session(records)
    http = [item for item in records if item.get("transport", "http") == "http"]
    sse = [item for item in records if item.get("transport") == "sse"]
    ws = [item for item in records if item.get("transport") == "websocket"]
    if scenario_id.endswith("-AUTH"):
        return [item for item in http if item.get("path") == "/aicp/v1/sessions"][:2]
    if scenario_id.endswith("-SESSION"):
        return [item for item in http if item.get("path") == "/aicp/v1/sessions" and item.get("status") == 201][:2]
    ingests = [item for item in http if item.get("method") == "POST" and item.get("path", "").endswith("/messages")]
    if scenario_id.endswith("-INGEST"):
        return ingests[:1]
    if scenario_id.endswith("-REPLAY"):
        return [item for item in ingests if (item.get("body") or {}).get("session_id") == primary and (item.get("body") or {}).get("message_id") == "m1"][:2]
    if scenario_id.endswith("-REPLAY-SCOPE"):
        return [item for item in ingests if (item.get("body") or {}).get("message_id") == "m1"][:3]
    polls = [item for item in http if item.get("method") == "GET" and item.get("path", "").endswith("/messages")]
    if scenario_id.endswith("-POLL"):
        return [item for item in polls if (item.get("query") or {}).get("after") == "c0"][:1]
    if scenario_id.endswith("-HEAD"):
        return [item for item in http if item.get("path", "").endswith("/head")][:1]
    if scenario_id.endswith("-ACK"):
        return [item for item in polls if (item.get("query") or {}).get("after") == "c0"][:1] + [item for item in http if item.get("path", "").endswith("/ack")][:1]
    if scenario_id.endswith("-REPLAY-WINDOW"):
        return [item for item in polls if (item.get("query") or {}).get("after") == "expired"][:1]
    if scenario_id.endswith("-ORDERING"):
        return [item for item in polls if (item.get("query") or {}).get("after") == "c0"][:1]
    if scenario_id.endswith("-OVERLOAD"):
        return [item for item in http if item.get("path", "").endswith("/overload")][:1]
    if scenario_id.endswith("-SSE"):
        return [item for item in sse if (item.get("query") or {}).get("after") in {"c0", "overload"} and "last-event-id" not in (item.get("headers") or {})]
    if scenario_id.endswith("-SSE-RECONNECT"):
        initial = [item for item in sse if (item.get("query") or {}).get("after") == "c0" and "last-event-id" not in (item.get("headers") or {})][:1]
        reconnect = [item for item in sse if "last-event-id" in (item.get("headers") or {})]
        mismatch = [item for item in http if item.get("status") == 400 and (item.get("response_body") or {}).get("reason_code") == "cursor_mismatch"]
        return initial + reconnect + mismatch
    if scenario_id.endswith("-WSS"):
        return [item for item in ws if item.get("scheme") == "wss"]
    if scenario_id.endswith("-WEBSOCKET"):
        poll = [item for item in polls if (item.get("query") or {}).get("after") == "c0"][:1]
        return poll + [item for item in ws if item.get("scheme", "ws") == "ws"]
    if scenario_id.endswith("-CLOSE"):
        closes = [item for item in http if item.get("path", "").endswith("/close")]
        rejected = [item for item in ingests if item.get("status") in {409, 410}]
        return closes[-1:] + rejected[-1:]
    return []


def attach_http_transport_evidence(
    interactions: list[dict[str, Any]],
    records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    result = copy.deepcopy(interactions)
    for interaction in result:
        scenario_id = str(interaction.get("scenario_id", ""))
        selected = _select_records(scenario_id, records)
        kind = "http"
        if "SSE" in scenario_id:
            kind = "sse"
        elif scenario_id.endswith("-WSS"):
            kind = "wss"
        elif scenario_id.endswith("-WEBSOCKET"):
            kind = "websocket"
        interaction.pop("observations", None)
        interaction["transport_evidence"] = {
            "kind": kind,
            "boundary": {
                "kind": "loopback_socket",
                "transport_kind": "tls_tcp" if kind == "wss" else "tcp",
                "address_family": "ipv4",
                "local_host_class": "loopback",
                "peer_host_class": "loopback",
            },
            "exchanges": [safe_exchange(item) for item in selected],
        }
    return result


def attach_tls_challenge_evidence(
    interactions: list[dict[str, Any]],
    challenges: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    result = copy.deepcopy(interactions)
    for interaction in result:
        if interaction.get("transport") != "wss":
            continue
        evidence = interaction.get("transport_evidence")
        if isinstance(evidence, dict) and evidence.get("kind") == "wss":
            evidence["tls_challenges"] = copy.deepcopy(challenges)
    return result
