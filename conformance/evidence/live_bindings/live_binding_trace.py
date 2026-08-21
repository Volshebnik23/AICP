from __future__ import annotations

import copy
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = ROOT / "conformance" / "evidence"

import sys

if str(EVIDENCE_DIR) not in sys.path:
    sys.path.insert(0, str(EVIDENCE_DIR))

from target_catalog import canonical_digest, load_json  # noqa: E402
from live_bindings.live_trace_evaluator import evaluate_v2_trace  # noqa: E402
from live_bindings.live_trace_normalization import semantic_digest_v2  # noqa: E402


ROLE_NAMES = ("server_under_test", "client_under_test")
SESSION_FACTS = {
    "session_id",
    "second_session_id",
}
CURSOR_FACTS = {
    "poll_after",
    "next_cursor",
    "cursor_after_last",
    "ack_cursor",
    "expired_cursor",
    "min_cursor",
    "last_event_id",
}
REQUEST_ID_FACTS = {"request_id", "response_id"}


def observation(name: str, value: Any) -> dict[str, Any]:
    return {"name": name, "value": value}


def observation_map(interaction: dict[str, Any]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for item in interaction.get("observations", []):
        if isinstance(item, dict) and isinstance(item.get("name"), str):
            name = str(item["name"])
            if name in values:
                raise ValueError(f"duplicate live observation: {name}")
            values[name] = item.get("value")
    return values


def _symbolize(value: Any, mapping: dict[str, str], prefix: str) -> Any:
    if not isinstance(value, str) or not value:
        return value
    if value not in mapping:
        mapping[value] = f"{prefix}:{len(mapping) + 1}"
    return mapping[value]


def normalize_run(run: dict[str, Any]) -> dict[str, Any]:
    session_symbols: dict[str, str] = {}
    cursor_symbols: dict[str, str] = {}
    request_symbols: dict[str, str] = {}
    interactions: list[dict[str, Any]] = []
    raw_interactions = run.get("interactions", [])
    ordered_interactions = sorted(
        raw_interactions,
        key=lambda item: (
            str(item.get("role", "")),
            str(item.get("scenario_id", "")),
            str(item.get("interaction_id", "")),
        ),
    ) if isinstance(raw_interactions, list) else []
    for interaction in ordered_interactions:
        normalized = {
            "interaction_id": interaction.get("interaction_id"),
            "role": interaction.get("role"),
            "scenario_id": interaction.get("scenario_id"),
            "transport": interaction.get("transport"),
            "operation": interaction.get("operation"),
            "observations": [],
        }
        facts = observation_map(interaction)
        for name in sorted(facts):
            value = copy.deepcopy(facts[name])
            if name in SESSION_FACTS:
                value = _symbolize(value, session_symbols, "session")
            elif name in CURSOR_FACTS:
                value = _symbolize(value, cursor_symbols, "cursor")
            elif name in REQUEST_ID_FACTS:
                value = _symbolize(value, request_symbols, "request")
            normalized["observations"].append(observation(name, value))
        interactions.append(normalized)
    return {"interactions": interactions}


def semantic_digest(run: dict[str, Any]) -> str:
    interactions = run.get("interactions") if isinstance(run, dict) else None
    if isinstance(interactions, list) and any(
        isinstance(item, dict) and "transport_evidence" in item
        for item in interactions
    ):
        return semantic_digest_v2(run)
    return canonical_digest(normalize_run(run))


def build_trace_artifact(
    *,
    binding_id: str,
    roles: dict[str, dict[str, Any]],
    runs: list[dict[str, Any]],
) -> dict[str, Any]:
    if len(runs) != 2:
        raise ValueError("live binding evidence requires exactly two clean runs")
    feature_coverage = {
        feature: any(
            bool(role.get("declared_features", {}).get(feature))
            for role in roles.values()
        )
        for feature in ("request_response", "sse", "websocket", "wss")
    }
    first_digest = semantic_digest(runs[0])
    repeat_digest = semantic_digest(runs[1])
    content = {
        "trace_version": "aicp.live_binding_trace.v2",
        "binding": {
            "binding_id": binding_id,
            "binding_version": "0.1",
        },
        "roles": roles,
        "feature_coverage": feature_coverage,
        "runs": runs,
        "semantic_digest": first_digest,
        "repeat_semantic_digest": repeat_digest,
    }
    content_digest = canonical_digest(content)
    return {
        "artifact_id": f"LIVE-BINDING-TRACE-{binding_id}-0.1",
        "artifact_kind": "live_binding_trace",
        "content_digest": content_digest,
        "repeat_content_digest": content_digest,
        "content": content,
    }


def _required_scenarios(
    catalog: dict[str, Any],
    roles: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    required: list[dict[str, Any]] = []
    for scenario in catalog.get("scenarios", []):
        role_name = scenario.get("tested_role")
        descriptor = roles.get(str(role_name))
        if not isinstance(descriptor, dict):
            continue
        features = descriptor.get("declared_features", {})
        optional = scenario.get("optional_feature_requirements", [])
        if all(features.get(feature) is True for feature in optional):
            required.append(scenario)
    return required


def _expect(facts: dict[str, Any], name: str, expected: Any = True) -> bool:
    return facts.get(name) == expected


def _interaction_errors(
    interaction: dict[str, Any],
    family: str,
) -> list[str]:
    facts = observation_map(interaction)
    errors: list[str] = []
    binding = "HTTP" if str(interaction.get("scenario_id", "")).startswith("LIVE-HTTP") else "MCP"
    role = str(interaction.get("role"))

    if binding == "HTTP":
        if not _expect(facts, "network_boundary", "loopback_socket"):
            errors.append("HTTP interaction did not cross a loopback socket")
        if family == "authentication":
            if not _expect(facts, "auth_present"):
                errors.append("authenticated request was not observed")
            if role == "server_under_test" and not _expect(facts, "auth_rejected"):
                errors.append("unauthenticated protected request was not rejected")
        elif family == "session_lifecycle":
            if not _expect(facts, "session_distinct"):
                errors.append("two distinct coherent sessions were not observed")
        elif family == "message_ingest":
            for name in ("request_path_valid", "content_type_valid", "idempotency_key_valid", "message_digest_equal"):
                if not _expect(facts, name):
                    errors.append(f"HTTP ingest fact failed: {name}")
            if facts.get("expected_message_id") != facts.get("observed_message_id"):
                errors.append("HTTP message_id changed across transport")
            if facts.get("expected_message_hash") != facts.get("observed_message_hash"):
                errors.append("HTTP message_hash changed across transport")
        elif family == "idempotent_replay":
            if facts.get("logical_accept_count") != 1 or facts.get("duplicate_count") != 0:
                errors.append("same-session replay created duplicate logical state")
        elif family == "session_scoped_replay":
            if not _expect(facts, "replay_scope_isolated"):
                errors.append("replay state leaked across sessions")
        elif family == "polling_cursor":
            if not _expect(facts, "session_match") or not _expect(facts, "no_cross_session_leakage"):
                errors.append("polling was not session scoped")
            if not _expect(facts, "message_hashes_intact"):
                errors.append("polling changed message identity or hashes")
            if not isinstance(facts.get("poll_limit"), int) or facts.get("delivered_count", 1000001) > facts.get("poll_limit", -1):
                errors.append("polling exceeded its requested limit")
            if not isinstance(facts.get("next_cursor"), str) or not facts.get("next_cursor"):
                errors.append("polling cursor relationship is missing")
        elif family == "head":
            if not _expect(facts, "head_session_match"):
                errors.append("head metadata belonged to another session")
        elif family == "explicit_ack":
            if not _expect(facts, "ack_matches"):
                errors.append("explicit cursor acknowledgement did not match")
        elif family == "replay_window":
            if facts.get("status") != 410 or facts.get("reason_code") != "cursor_expired" or not facts.get("min_cursor"):
                errors.append("expired cursor did not produce exact 410 semantics")
        elif family == "ordering":
            if not _expect(facts, "ordered_chain_valid"):
                errors.append("ordered adjacent message chain was broken")
        elif family == "overload":
            if facts.get("status") != 429 or not _expect(facts, "retry_after_present") or not _expect(facts, "rate_limit_hint_present"):
                errors.append("deterministic HTTP 429 hints were incomplete")
        elif family == "sse_stream":
            for name in ("live_bytes", "sse_content_type_valid", "event_ids_match_cursors", "more_flags_valid", "ordered_chain_valid", "overload_retry_present"):
                if not _expect(facts, name):
                    errors.append(f"SSE fact failed: {name}")
            if facts.get("status") != 200 or facts.get("delivered_count", 1000001) > facts.get("poll_limit", -1):
                errors.append("SSE response status or pull limit was invalid")
        elif family == "sse_reconnect":
            for name in ("live_bytes", "last_event_relationship_valid", "mismatched_resume_rejected", "reconnect_stable", "reconnect_churn_valid"):
                if not _expect(facts, name):
                    errors.append(f"SSE reconnect fact failed: {name}")
        elif family == "websocket_pull":
            for name in ("live_frames", "websocket_handshake_valid", "websocket_frame_shape_valid", "cursor_relationship_valid", "more_flags_valid", "ordered_chain_valid", "overload_retry_present"):
                if not _expect(facts, name):
                    errors.append(f"WebSocket fact failed: {name}")
            if facts.get("delivered_count", 1000001) > facts.get("poll_limit", -1):
                errors.append("WebSocket pull exceeded its requested limit")
        elif family == "close_session":
            if not _expect(facts, "closed_session_rejected"):
                errors.append("closed session continued accepting traffic")
    else:
        if not _expect(facts, "process_boundary"):
            errors.append("MCP JSON-RPC bytes did not cross a process boundary")
        if facts.get("jsonrpc_version") != "2.0" or facts.get("request_id") != facts.get("response_id"):
            errors.append("MCP JSON-RPC correlation failed")
        if not _expect(facts, "request_response_correlated") or facts.get("response_count") != 1 or not _expect(facts, "valid_utf8"):
            errors.append("MCP response integrity failed")
        if family == "send_message":
            if facts.get("tool_name") != "aicp.sendMessage" or not _expect(facts, "message_digest_equal"):
                errors.append("MCP sendMessage rewrote or omitted the envelope")
        elif family == "duplicate_send":
            if not _expect(facts, "duplicate_hash_stable") or facts.get("logical_accept_count") != 1:
                errors.append("MCP duplicate delivery created conflicting state")
        elif family == "poll_messages":
            if facts.get("tool_name") != "aicp.pollMessages" or not _expect(facts, "poll_session_match") or not _expect(facts, "poll_limit_respected") or not _expect(facts, "message_hashes_intact"):
                errors.append("MCP pollMessages scope, limit, or hashes failed")
            if not _expect(facts, "ordering_not_assumed"):
                errors.append("MCP live evidence falsely imposed ordering")
        elif family == "get_head":
            if facts.get("tool_name") != "aicp.getHead" or not _expect(facts, "head_session_match"):
                errors.append("MCP getHead returned another session")
        elif family == "get_object":
            if facts.get("tool_name") != "aicp.getObject" or facts.get("object_expected_hash") != facts.get("object_actual_hash") or not _expect(facts, "object_hash_recomputed") or not _expect(facts, "unknown_object_failed"):
                errors.append("MCP getObject hash or unknown-object behavior failed")
        elif family == "jsonrpc_integrity":
            if not _expect(facts, "process_boundary") or not _expect(
                facts, "malformed_envelope_rejected"
            ):
                errors.append("MCP integrity scenario did not use stdio or reject a malformed envelope")
    return errors


def evaluate_live_binding_trace(
    artifact: dict[str, Any],
    catalog: dict[str, Any],
    *,
    full_binding: bool,
    disabled_families: frozenset[str] = frozenset(),
) -> list[str]:
    content = artifact.get("content")
    if isinstance(content, dict) and content.get("trace_version") == "aicp.live_binding_trace.v2":
        return evaluate_v2_trace(
            artifact,
            catalog,
            full_binding=full_binding,
            disabled_families=disabled_families,
        )
    errors: list[str] = []
    if artifact.get("artifact_kind") != "live_binding_trace":
        return ["generated artifact is not a live binding trace"]
    content = artifact.get("content")
    if not isinstance(content, dict):
        return ["live binding trace content is missing"]
    if artifact.get("content_digest") != canonical_digest(content):
        errors.append("live trace content digest does not recompute")
    if artifact.get("repeat_content_digest") != artifact.get("content_digest"):
        errors.append("live trace repeat content digest differs")
    if content.get("binding") != {
        "binding_id": catalog.get("target", {}).get("target_id"),
        "binding_version": catalog.get("target", {}).get("target_version"),
    }:
        errors.append("live trace binding identity differs from target")
    roles = content.get("roles")
    if not isinstance(roles, dict):
        return [*errors, "live trace roles are missing"]
    expected_roles = set(ROLE_NAMES if full_binding else ("server_under_test",))
    if set(roles) != expected_roles:
        errors.append("live trace role coverage is not exact")
    identities = {
        (
            role.get("implementation_kind"),
            role.get("implementation_id"),
            role.get("implementation_version"),
            role.get("implementation_digest"),
        )
        for role in roles.values()
        if isinstance(role, dict)
    }
    if len(identities) != 1:
        errors.append("client/server roles do not identify the exact same build")
    for name, role in roles.items():
        if not isinstance(role, dict) or role.get("role") != name:
            errors.append(f"live trace role metadata is inconsistent: {name}")
    expected_feature_coverage = {
        feature: any(
            isinstance(role, dict)
            and role.get("declared_features", {}).get(feature) is True
            for role in roles.values()
        )
        for feature in ("request_response", "sse", "websocket", "wss")
    }
    if content.get("feature_coverage") != expected_feature_coverage:
        errors.append("live trace feature coverage does not recompute from role declarations")
    runs = content.get("runs")
    if not isinstance(runs, list) or len(runs) != 2:
        return [*errors, "live trace must contain exactly two runs"]
    recomputed = [semantic_digest(run) for run in runs]
    if content.get("semantic_digest") != recomputed[0]:
        errors.append("first semantic digest does not recompute")
    if content.get("repeat_semantic_digest") != recomputed[1]:
        errors.append("repeat semantic digest does not recompute")
    if recomputed[0] != recomputed[1]:
        errors.append("normalized semantic repeat differs")

    required = _required_scenarios(catalog, roles)
    required_ids = Counter(str(item["scenario_id"]) for item in required)
    family_by_id = {
        str(item["scenario_id"]): str(item["semantic_family"])
        for item in required
    }
    for run in runs:
        interactions = run.get("interactions") if isinstance(run, dict) else None
        if not isinstance(interactions, list):
            errors.append("live run interactions are missing")
            continue
        observed = Counter(
            str(item.get("scenario_id"))
            for item in interactions
            if isinstance(item, dict)
        )
        if observed != required_ids:
            errors.append("live mandatory scenario coverage is missing, duplicated, or unknown")
        for interaction in interactions:
            if not isinstance(interaction, dict):
                errors.append("live interaction is not an object")
                continue
            scenario_id = str(interaction.get("scenario_id"))
            family = family_by_id.get(scenario_id)
            if family is None:
                continue
            try:
                errors.extend(
                    f"{scenario_id}: {message}"
                    for message in _interaction_errors(interaction, family)
                )
            except ValueError as exc:
                errors.append(f"{scenario_id}: {exc}")
    return sorted(set(errors))


def scenario_catalog_path(binding_id: str) -> Path:
    name = "http_v01_scenarios.json" if binding_id == "BIND-HTTP" else "mcp_v01_scenarios.json"
    return EVIDENCE_DIR / "live_bindings" / name


def load_scenario_catalog(binding_id: str) -> dict[str, Any]:
    return load_json(scenario_catalog_path(binding_id))
