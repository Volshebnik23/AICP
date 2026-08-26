from __future__ import annotations

import copy
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
REF_PY = ROOT / "reference" / "python"

import sys

if str(REF_PY) not in sys.path:
    sys.path.insert(0, str(REF_PY))

from aicp_ref.hashing import message_hash_from_body, object_hash  # noqa: E402
from live_bindings.live_http_capture import idempotency_key_valid  # noqa: E402
from live_bindings.live_trace_normalization import (  # noqa: E402
    semantic_digest_v2,
    valid_websocket_key,
    websocket_accept,
)
from target_catalog import canonical_digest  # noqa: E402


ROLE_NAMES = ("server_under_test", "client_under_test")


def _required_scenarios(catalog: dict[str, Any], roles: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    required: list[dict[str, Any]] = []
    for scenario in catalog.get("scenarios", []):
        descriptor = roles.get(str(scenario.get("tested_role")))
        if not isinstance(descriptor, dict):
            continue
        features = descriptor.get("declared_features", {})
        optional = scenario.get("optional_feature_requirements", [])
        if all(features.get(feature) is True for feature in optional):
            required.append(scenario)
    return required


def _expected_message(session_id: str, index: int) -> dict[str, Any]:
    path = ROOT / "fixtures/golden_transcripts/GT-01_happy_path_signed.jsonl"
    sources = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    previous_hash: str | None = None
    values: list[dict[str, Any]] = []
    for source in sources:
        value = copy.deepcopy(source)
        value["session_id"] = session_id
        value.pop("signatures", None)
        value.pop("message_hash", None)
        if previous_hash is None:
            value.pop("prev_msg_hash", None)
        else:
            value["prev_msg_hash"] = previous_hash
        value["message_hash"] = message_hash_from_body(value)
        previous_hash = str(value["message_hash"])
        values.append(value)
    return values[index]


def _headers_token(value: Any, token: str) -> bool:
    if not isinstance(value, str):
        return False
    return token.lower() in {part.strip().lower() for part in value.split(",")}


def _exchange_valid(exchange: dict[str, Any]) -> bool:
    request = exchange.get("request", {})
    response = exchange.get("response", {})
    return (
        request.get("jsonrpc") == "2.0"
        and request.get("method") == "tools/call"
        and response.get("jsonrpc") == "2.0"
        and request.get("id") == response.get("id")
        and response.get("outcome") in {"result", "error"}
    )


def _message_refs(exchange: dict[str, Any]) -> list[dict[str, Any]]:
    body = exchange.get("response", {}).get("body", {})
    refs = body.get("message_refs")
    return refs if isinstance(refs, list) else []


def _http_errors(
    interaction: dict[str, Any],
    family: str,
    *,
    trace_version: str,
) -> list[str]:
    evidence = interaction.get("transport_evidence", {})
    exchanges = evidence.get("exchanges") if isinstance(evidence, dict) else None
    if not isinstance(exchanges, list) or not exchanges:
        return ["authoritative HTTP transport exchanges are missing"]
    errors: list[str] = []
    boundary = evidence.get("boundary", {})
    if boundary.get("kind") != "loopback_socket" or boundary.get("local_host_class") != "loopback" or boundary.get("peer_host_class") != "loopback":
        errors.append("HTTP evidence does not describe a loopback socket boundary")

    if family == "authentication":
        unauth = any(
            not item["request"].get("authorization_present")
            and item["response"].get("status") in {401, 403}
            for item in exchanges
        )
        auth = any(
            item["request"].get("authorization_present")
            and item["request"].get("authorization_scheme") == "Bearer"
            and item["response"].get("status") == 201
            for item in exchanges
        )
        if not (unauth and auth):
            errors.append("authentication request structure or rejection is incomplete")
    elif family == "session_lifecycle":
        sessions = [item["response"].get("body", {}).get("session_id") for item in exchanges if item["response"].get("status") == 201]
        if len(sessions) < 2 or not all(isinstance(item, str) and item for item in sessions[:2]) or sessions[0] == sessions[1]:
            errors.append("two distinct session responses were not captured")
    elif family == "message_ingest":
        item = exchanges[0]
        request = item["request"]
        refs = request.get("body", {}).get("message_refs", [])
        ref = refs[0] if len(refs) == 1 else {}
        expected = _expected_message(str(ref.get("session_id", "")), 0)
        key = request.get("headers", {}).get("idempotency-key")
        if request.get("method") != "POST" or request.get("path") != f"/aicp/v1/sessions/{ref.get('session_id', '')}/messages":
            errors.append("HTTP ingest path is not bound to the message session")
        if "application/json" not in request.get("headers", {}).get("content-type", ""):
            errors.append("HTTP ingest content type is invalid")
        if not idempotency_key_valid(key, ref.get("message_id")):
            errors.append("HTTP Idempotency-Key delimiter relationship is invalid")
        if ref.get("message_id") != expected.get("message_id") or ref.get("message_hash") != expected.get("message_hash") or ref.get("canonical_digest") != canonical_digest(expected):
            errors.append("HTTP ingest deterministic message identity or digest changed")
        if item["response"].get("status") != 202:
            errors.append("HTTP ingest was not newly accepted")
    elif family == "idempotent_replay":
        if len(exchanges) < 2:
            errors.append("HTTP replay exchanges are incomplete")
        else:
            first, replay = exchanges[:2]
            first_ref = first["request"].get("body", {}).get("message_refs", [{}])[0]
            replay_ref = replay["request"].get("body", {}).get("message_refs", [{}])[0]
            if first_ref != replay_ref or first["response"].get("status") != 202 or replay["response"].get("status") not in {200, 208} or replay["response"].get("headers", {}).get("aicp-replay") != "true":
                errors.append("same-session replay evidence is not idempotent")
    elif family == "session_scoped_replay":
        refs = [item["request"].get("body", {}).get("message_refs", [{}])[0] for item in exchanges if item["request"].get("body", {}).get("message_refs")]
        sessions = {ref.get("session_id") for ref in refs if ref.get("message_id") == "m1"}
        if len(sessions) < 2 or not any(item["response"].get("status") == 202 and item["response"].get("headers", {}).get("aicp-replay") != "true" for item in exchanges[1:]):
            errors.append("replay scope is not independently session isolated")
    elif family == "polling_cursor":
        item = exchanges[0]
        request, response = item["request"], item["response"]
        session = request.get("path", "").split("/")[4] if len(request.get("path", "").split("/")) > 4 else ""
        limit = request.get("query", {}).get("limit")
        refs = _message_refs(item)
        if request.get("query", {}).get("after") != "c0" or not isinstance(limit, int) or len(refs) > limit or response.get("status") != 200 or not response.get("body", {}).get("next_cursor"):
            errors.append("HTTP poll cursor, limit, or response is incomplete")
        if any(ref.get("session_id") != session for ref in refs):
            errors.append("HTTP poll returned cross-session message evidence")
        for index, ref in enumerate(refs):
            expected = _expected_message(session, index)
            if ref.get("message_hash") != expected.get("message_hash") or ref.get("canonical_digest") != canonical_digest(expected):
                errors.append("HTTP poll message hash or digest changed")
    elif family == "head":
        item = exchanges[0]
        path_parts = item["request"].get("path", "").split("/")
        requested = path_parts[4] if len(path_parts) > 4 else ""
        if item["response"].get("status") != 200 or item["response"].get("body", {}).get("session_id") != requested:
            errors.append("HTTP head response is not session bound")
    elif family == "explicit_ack":
        if len(exchanges) < 2:
            errors.append("HTTP ACK lacks its prior poll exchange")
        else:
            cursor = exchanges[0]["response"].get("body", {}).get("next_cursor")
            ack = exchanges[1]
            if not cursor or ack["request"].get("body", {}).get("cursor") != cursor or ack["response"].get("status") != 204:
                errors.append("HTTP ACK did not reuse the exact returned cursor")
    elif family == "replay_window":
        item = exchanges[0]
        body = item["response"].get("body", {})
        if item["request"].get("query", {}).get("after") != "expired" or item["response"].get("status") != 410 or body.get("reason_code") != "cursor_expired" or not body.get("min_cursor"):
            errors.append("HTTP replay-window response is not exact")
    elif family == "ordering":
        refs = _message_refs(exchanges[0])
        if any(refs[index].get("prev_msg_hash") != refs[index - 1].get("message_hash") for index in range(1, len(refs))):
            errors.append("HTTP ordered message chain is broken")
    elif family == "overload":
        item = exchanges[0]
        headers = item["response"].get("headers", {})
        if item["response"].get("status") != 429 or not headers.get("retry-after") or not any(name.startswith("ratelimit-") for name in headers):
            errors.append("HTTP overload evidence lacks exact retry/rate-limit hints")
    elif family == "sse_stream":
        initial = next((item for item in exchanges if item.get("events") and any(event.get("event") == "messages" for event in item["events"])), None)
        overload = next((event for item in exchanges for event in item.get("events", []) if event.get("event") == "overload"), None)
        if initial is None:
            errors.append("SSE parsed message events are missing")
        else:
            events = [event for event in initial["events"] if event.get("event") == "messages"]
            refs = [ref for event in events for ref in event.get("message_refs", [])]
            limit = initial["request"].get("query", {}).get("limit")
            if initial["response"].get("status") != 200 or "text/event-stream" not in initial["response"].get("headers", {}).get("content-type", ""):
                errors.append("SSE status or content type is invalid")
            if any(event.get("id") != event.get("cursor_after_last") for event in events):
                errors.append("SSE event ID does not equal its cursor")
            flags = [event.get("more") for event in events]
            if not flags or flags[-1] is not False or any(flag is not True for flag in flags[:-1]):
                errors.append("SSE more progression is invalid")
            if not isinstance(limit, int) or len(refs) > limit:
                errors.append("SSE delivery exceeded its pull limit")
            if any(refs[index].get("prev_msg_hash") != refs[index - 1].get("message_hash") for index in range(1, len(refs))):
                errors.append("SSE ordered chain is broken")
        if not isinstance(overload, dict) or not overload.get("retry_after"):
            errors.append("SSE overload retry evidence is missing")
    elif family == "sse_reconnect":
        initial = exchanges[0]
        initial_events = initial.get("events", [])
        last = initial_events[-1].get("id") if initial_events else None
        reconnects = [item for item in exchanges[1:] if item["response"].get("status") == 200 and item.get("events") is not None]
        if not last or len(reconnects) < 2:
            errors.append("SSE reconnect exchanges are incomplete")
        else:
            for item in reconnects[:2]:
                if item["request"].get("query", {}).get("after") != last or item["request"].get("headers", {}).get("last-event-id") != last:
                    errors.append("SSE reconnect did not derive Last-Event-ID from the prior event")
                if any(event.get("id") != last or event.get("message_refs") for event in item.get("events", []) if event.get("event") == "messages"):
                    errors.append("SSE reconnect returned evidence from before the resume cursor")
            if reconnects[0].get("events") != reconnects[1].get("events"):
                errors.append("SSE reconnect churn changed the semantic events")
        if not any(item["response"].get("status") == 400 and item["response"].get("body", {}).get("reason_code") == "cursor_mismatch" for item in exchanges):
            errors.append("SSE mismatched resume was not rejected")
    elif family in {"websocket_pull", "wss_pull"}:
        connections = [item for item in exchanges if item.get("scheme") in {"ws", "wss"}]
        required_scheme = "wss" if family == "wss_pull" else "ws"
        if not connections:
            errors.append(f"{required_scheme.upper()} connection evidence is missing")
        for item in connections:
            request_headers = item["request"].get("headers", {})
            response_headers = item["response"].get("headers", {})
            key = request_headers.get("sec-websocket-key", "")
            if item.get("scheme") != required_scheme or item["response"].get("status") != 101:
                errors.append(f"{required_scheme.upper()} status or scheme is invalid")
            if not _headers_token(request_headers.get("upgrade"), "websocket") or not _headers_token(request_headers.get("connection"), "upgrade") or request_headers.get("sec-websocket-version") != "13":
                errors.append("WebSocket request handshake headers are invalid")
            if not _headers_token(response_headers.get("upgrade"), "websocket") or not _headers_token(response_headers.get("connection"), "upgrade") or not valid_websocket_key(key) or response_headers.get("sec-websocket-accept") != websocket_accept(key):
                errors.append("WebSocket response handshake or Sec-WebSocket-Accept is invalid")
            if required_scheme == "wss" and item.get("tls_verified") is not True:
                errors.append("WSS certificate verification was not executed")
        messages = next((item for item in connections if item.get("server_frame", {}).get("type") == "messages"), None)
        overload = next((item for item in connections if item.get("server_frame", {}).get("type") == "overload"), None)
        if messages is None:
            errors.append("WebSocket messages frame is missing")
        else:
            client, server = messages.get("client_frame", {}), messages.get("server_frame", {})
            poll_cursor = next(
                (
                    item.get("response", {}).get("body", {}).get("next_cursor")
                    for item in exchanges
                    if item.get("request", {}).get("method") == "GET"
                    and item.get("request", {}).get("query", {}).get("after") == "c0"
                ),
                None,
            )
            refs = server.get("message_refs", [])
            if client.get("type") != "pull" or client.get("after") != "c0" or not isinstance(client.get("limit"), int) or len(refs) > client.get("limit", -1) or server.get("more") is not False or not server.get("cursor_after_last") or (poll_cursor and server.get("cursor_after_last") != poll_cursor):
                errors.append("WebSocket pull frame or cursor relationship is invalid")
            if any(refs[index].get("prev_msg_hash") != refs[index - 1].get("message_hash") for index in range(1, len(refs))):
                errors.append("WebSocket ordered message chain is broken")
        if overload is None or not overload.get("server_frame", {}).get("retry_after"):
            errors.append("WebSocket overload retry frame is missing")
        if (
            family == "wss_pull"
            and interaction.get("role") == "client_under_test"
            and trace_version in {
                "aicp.live_binding_trace.v3",
                "aicp.live_binding_trace.v4",
            }
        ):
            challenges = evidence.get("tls_challenges")
            by_class = {
                item.get("endpoint_class"): item
                for item in challenges
                if isinstance(item, dict)
            } if isinstance(challenges, list) else {}
            if set(by_class) != {"trusted", "untrusted"} or len(challenges or []) != 2:
                errors.append("WSS client TLS challenge pair is missing or duplicated")
            else:
                untrusted = by_class["untrusted"]
                trusted = by_class["trusted"]
                if (
                    untrusted.get("connection_attempted") is not True
                    or untrusted.get("tls_handshake_completed") is not False
                    or untrusted.get("websocket_application_handshake_observed")
                    is not False
                ):
                    errors.append("untrusted WSS endpoint was skipped or accepted")
                if (
                    trusted.get("connection_attempted") is not True
                    or trusted.get("tls_handshake_completed") is not True
                    or trusted.get("websocket_application_handshake_observed")
                    is not True
                ):
                    errors.append("trusted WSS endpoint did not complete TLS and Upgrade")
                if trace_version == "aicp.live_binding_trace.v4":
                    if untrusted.get("tls_failure_class") != "certificate_rejected":
                        errors.append(
                            "untrusted WSS endpoint did not prove certificate rejection"
                        )
                    if trusted.get("tls_failure_class") != "tls_handshake_completed":
                        errors.append("trusted WSS endpoint TLS outcome is invalid")
                    if untrusted.get("tls_failure_order") is None:
                        errors.append("untrusted WSS TLS failure order is missing")
                    if trusted.get("tls_failure_order") is not None:
                        errors.append("trusted WSS endpoint recorded a TLS failure")
                untrusted_order = untrusted.get("connection_order")
                trusted_order = trusted.get("connection_order")
                if (
                    not isinstance(untrusted_order, int)
                    or not isinstance(trusted_order, int)
                    or untrusted_order >= trusted_order
                ):
                    errors.append("untrusted WSS challenge did not precede trusted WSS execution")
                if trace_version == "aicp.live_binding_trace.v4":
                    untrusted_failure_order = untrusted.get("tls_failure_order")
                    if (
                        not isinstance(untrusted_failure_order, int)
                        or not isinstance(untrusted_order, int)
                        or not isinstance(trusted_order, int)
                        or not untrusted_order
                        < untrusted_failure_order
                        < trusted_order
                    ):
                        errors.append(
                            "certificate rejection was not observed between challenge connect and trusted execution"
                        )
                trusted_tls_order = trusted.get("tls_handshake_order")
                trusted_upgrade_order = trusted.get(
                    "websocket_application_handshake_order"
                )
                if (
                    not isinstance(trusted_tls_order, int)
                    or not isinstance(trusted_upgrade_order, int)
                    or not trusted_order < trusted_tls_order < trusted_upgrade_order
                ):
                    errors.append("trusted WSS observation order is inconsistent")
    elif family == "close_session":
        if len(exchanges) < 2 or exchanges[0]["response"].get("status") != 204 or exchanges[1]["response"].get("status") not in {409, 410}:
            errors.append("closed HTTP session continued accepting traffic")
    return errors


def _mcp_errors(interaction: dict[str, Any], family: str) -> list[str]:
    evidence = interaction.get("transport_evidence", {})
    exchanges = evidence.get("exchanges") if isinstance(evidence, dict) else None
    if not isinstance(exchanges, list) or not exchanges:
        return ["authoritative MCP JSON-RPC exchanges are missing"]
    errors: list[str] = []
    boundary = evidence.get("boundary", {})
    if boundary.get("kind") != "child_process_stdio" or boundary.get("transport_kind") != "stdio" or boundary.get("child_process_role") != interaction.get("role"):
        errors.append("MCP evidence does not identify the tested child-process stdio role")
    if any(not _exchange_valid(item) for item in exchanges):
        errors.append("MCP JSON-RPC request/response correlation failed")
    if family == "send_message":
        item = exchanges[0]
        ref = item["request"].get("arguments", {}).get("message_ref", {})
        expected = _expected_message(str(ref.get("session_id", "")), 0)
        result = item["response"].get("result", {})
        if item["request"].get("tool") != "aicp.sendMessage" or ref.get("canonical_digest") != canonical_digest(expected) or ref.get("message_hash") != expected.get("message_hash") or result.get("accepted") is not True or result.get("message_id") != ref.get("message_id"):
            errors.append("MCP sendMessage transport evidence changed the deterministic envelope")
    elif family == "duplicate_send":
        if len(exchanges) < 2:
            errors.append("MCP duplicate exchanges are incomplete")
        else:
            first, second = exchanges[:2]
            first_ref = first["request"].get("arguments", {}).get("message_ref")
            second_ref = second["request"].get("arguments", {}).get("message_ref")
            second_result = second["response"].get("result", {})
            if first_ref != second_ref or second_result.get("accepted") is not True or second_result.get("message_hash") != (first_ref or {}).get("message_hash"):
                errors.append("MCP duplicate delivery is not hash-stable")
    elif family == "poll_messages":
        indexed_polls = [
            (index, item)
            for index, item in enumerate(exchanges)
            if item.get("request", {}).get("tool") == "aicp.pollMessages"
        ]
        if len(indexed_polls) != 2:
            errors.append("MCP pollMessages requires two correlated polls")
        else:
            (first_index, first), (second_index, second) = indexed_polls
            first_args = first["request"].get("arguments", {})
            second_args = second["request"].get("arguments", {})
            first_result = first["response"].get("result", {})
            second_result = second["response"].get("result", {})
            first_cursor = first_result.get("next_cursor")
            if not isinstance(first_cursor, str) or not first_cursor:
                errors.append("MCP first poll did not return a continuation cursor")
            if (
                interaction.get("role") == "client_under_test"
                and isinstance(first_cursor, str)
                and first_cursor
                and any(
                    isinstance(prior.get("response", {}).get("result"), dict)
                    and any(
                        prior["response"]["result"].get(name) == first_cursor
                        for name in ("cursor", "next_cursor")
                    )
                    for prior in exchanges[:first_index]
                )
            ):
                errors.append(
                    "MCP poll continuation appeared in an earlier client-visible response"
                )
            if first_args.get("after_cursor") != "c0" or second_args.get("after_cursor") != first_cursor:
                errors.append("MCP second poll did not consume the exact prior cursor")
            if second_index <= first_index:
                errors.append("MCP second poll did not follow the first poll response")
            if first_args.get("session_id") != second_args.get("session_id"):
                errors.append("MCP poll session changed between cursor steps")
            for args, result in ((first_args, first_result), (second_args, second_result)):
                refs = result.get("message_refs", [])
                if not isinstance(args.get("limit"), int) or len(refs) > args["limit"] or any(ref.get("session_id") != args.get("session_id") for ref in refs):
                    errors.append("MCP poll session or limit was not enforced")
            if second_result.get("next_cursor") == first_cursor:
                errors.append("MCP server did not advance after consuming after_cursor")
    elif family == "get_head":
        item = exchanges[0]
        if item["request"].get("tool") != "aicp.getHead" or item["request"].get("arguments", {}).get("session_id") != item["response"].get("result", {}).get("session_id"):
            errors.append("MCP getHead is not bound to the requested session")
    elif family == "get_object":
        if len(exchanges) < 2:
            errors.append("MCP getObject known/unknown exchanges are incomplete")
        else:
            known, unknown = exchanges[:2]
            content = known["response"].get("result", {}).get("object_content")
            expected_hash = known["request"].get("arguments", {}).get("object_hash")
            actual_hash = object_hash(known["response"].get("result", {}).get("object_type", ""), content) if isinstance(content, dict) else ""
            if known["request"].get("tool") != "aicp.getObject" or actual_hash != expected_hash or unknown["response"].get("result", {}).get("status") != "NOT_FOUND":
                errors.append("MCP getObject content hash or unknown-object result is invalid")
    elif family == "jsonrpc_integrity":
        ids = [item["request"].get("id") for item in exchanges]
        tools = [item["request"].get("tool") for item in exchanges]
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
        malformed = any(item["request"].get("arguments", {}).get("malformed_message") is True and item["response"].get("outcome") == "error" for item in exchanges)
        if len(ids) != len(set(ids)) or tools != expected_tools or not malformed:
            errors.append("MCP integrity evidence reused an ID or accepted a malformed envelope")
    return errors


def evaluate_v2_trace(
    artifact: dict[str, Any],
    catalog: dict[str, Any],
    *,
    full_binding: bool,
    disabled_families: frozenset[str] = frozenset(),
) -> list[str]:
    errors: list[str] = []
    if artifact.get("artifact_kind") != "live_binding_trace":
        return ["generated artifact is not a live binding trace"]
    content = artifact.get("content")
    if not isinstance(content, dict):
        return ["live binding trace content is missing"]
    trace_version = str(content.get("trace_version", ""))
    if trace_version not in {
        "aicp.live_binding_trace.v2",
        "aicp.live_binding_trace.v3",
        "aicp.live_binding_trace.v4",
    }:
        return ["live binding evidence requires transport evidence trace v2, v3, or v4"]
    if artifact.get("content_digest") != canonical_digest(content):
        errors.append("live trace content digest does not recompute")
    if artifact.get("repeat_content_digest") != artifact.get("content_digest"):
        errors.append("live trace repeat content digest differs")
    if content.get("binding") != {"binding_id": catalog.get("target", {}).get("target_id"), "binding_version": catalog.get("target", {}).get("target_version")}:
        errors.append("live trace binding identity differs from target")
    roles = content.get("roles")
    if not isinstance(roles, dict):
        return [*errors, "live trace roles are missing"]
    expected_roles = set(ROLE_NAMES if full_binding else ("server_under_test",))
    if set(roles) != expected_roles:
        errors.append("live trace role coverage is not exact")
    identities = {(role.get("implementation_kind"), role.get("implementation_id"), role.get("implementation_version"), role.get("implementation_digest")) for role in roles.values() if isinstance(role, dict)}
    if len(identities) != 1:
        errors.append("client/server roles do not identify the exact same build")
    for name, role in roles.items():
        if not isinstance(role, dict) or role.get("role") != name:
            errors.append(f"live trace role metadata is inconsistent: {name}")
    expected_features = {feature: any(isinstance(role, dict) and role.get("declared_features", {}).get(feature) is True for role in roles.values()) for feature in ("request_response", "sse", "websocket", "wss")}
    if content.get("feature_coverage") != expected_features:
        errors.append("live trace feature coverage does not recompute from role declarations")
    if expected_features["wss"] and not expected_features["websocket"]:
        errors.append("WSS declaration requires WebSocket declaration")
    runs = content.get("runs")
    if not isinstance(runs, list) or len(runs) != 2:
        return [*errors, "live trace must contain exactly two runs"]
    recomputed = [semantic_digest_v2(run) for run in runs]
    if content.get("semantic_digest") != recomputed[0]:
        errors.append("first v2 semantic digest does not recompute")
    if content.get("repeat_semantic_digest") != recomputed[1]:
        errors.append("repeat v2 semantic digest does not recompute")
    if recomputed[0] != recomputed[1]:
        errors.append("normalized v2 semantic repeat differs")
    required = _required_scenarios(catalog, roles)
    required_ids = Counter(str(item["scenario_id"]) for item in required)
    family_by_id = {str(item["scenario_id"]): str(item["semantic_family"]) for item in required}
    for role_name, descriptor in roles.items():
        if isinstance(descriptor, dict) and descriptor.get("declared_features", {}).get("wss") is True:
            prefix = "SERVER" if role_name == "server_under_test" else "CLIENT"
            scenario_id = f"LIVE-HTTP-{prefix}-WSS"
            required_ids[scenario_id] += 1
            family_by_id[scenario_id] = "wss_pull"
    for run in runs:
        interactions = run.get("interactions") if isinstance(run, dict) else None
        if not isinstance(interactions, list):
            errors.append("live run interactions are missing")
            continue
        observed = Counter(str(item.get("scenario_id")) for item in interactions if isinstance(item, dict))
        if observed != required_ids:
            errors.append("live mandatory scenario coverage is missing, duplicated, or unknown")
        for interaction in interactions:
            if not isinstance(interaction, dict):
                errors.append("live interaction is not an object")
                continue
            scenario_id = str(interaction.get("scenario_id"))
            family = family_by_id.get(scenario_id)
            if family is None or family in disabled_families:
                continue
            expected_role = (
                "server_under_test"
                if "-SERVER-" in scenario_id
                else "client_under_test"
            )
            if interaction.get("role") != expected_role:
                errors.append(
                    f"{scenario_id}: interaction role does not match scenario/build binding"
                )
            messages = (
                _http_errors(
                    interaction,
                    family,
                    trace_version=trace_version,
                )
                if scenario_id.startswith("LIVE-HTTP")
                else _mcp_errors(interaction, family)
            )
            errors.extend(f"{scenario_id}: {message}" for message in messages)
    return sorted(set(errors))
