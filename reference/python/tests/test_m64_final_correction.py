from __future__ import annotations

import base64
import inspect
import json
import secrets
import socket
import sys
from pathlib import Path
from typing import Any

import pytest


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = ROOT / "conformance" / "evidence"
if str(EVIDENCE_DIR) not in sys.path:
    sys.path.insert(0, str(EVIDENCE_DIR))

from aicp_live_binding_runner import (  # noqa: E402
    _control_environment,
    _scenario_payload,
)
from live_bindings.live_http_transport import (  # noqa: E402
    HttpLiveState,
    http_request,
    start_http_server,
    stop_http_server,
)
from live_bindings.live_mcp_transport import (  # noqa: E402
    McpState,
    SESSION_ID,
    mcp_client_loop,
    rpc_request,
)
from live_bindings import live_trace_normalization  # noqa: E402


def _arguments(request: dict[str, Any]) -> dict[str, Any]:
    return request["params"]["arguments"]


def test_reproduces_preconstructed_mcp_c1_then_requires_sequential_client() -> None:
    class LegacyDeterministicMcpState(McpState):
        def cursor_for_offset(self, session_id: str, offset: int) -> str:
            self._ensure_cursor_state(session_id)
            cursor = f"c{offset}"
            self.offset_cursors[session_id][offset] = cursor
            self.cursor_offsets[session_id][cursor] = offset
            return cursor

    deterministic = LegacyDeterministicMcpState()
    first = rpc_request(
        "poll-1",
        "aicp.pollMessages",
        {"session_id": SESSION_ID, "after_cursor": "c0", "limit": 1},
    )
    hardcoded_second = rpc_request(
        "poll-2",
        "aicp.pollMessages",
        {"session_id": SESSION_ID, "after_cursor": "c1", "limit": 1},
    )
    deterministic.messages[SESSION_ID] = [{"session_id": SESSION_ID}]
    first_response = deterministic.handle(first)
    assert _arguments(hardcoded_second)["after_cursor"] == first_response["result"]["next_cursor"]

    opaque = McpState()
    opaque.messages[SESSION_ID] = [{"session_id": SESSION_ID}]
    opaque_response = opaque.handle(first)
    assert (
        _arguments(hardcoded_second)["after_cursor"]
        != opaque_response["result"]["next_cursor"]
    )

    source = inspect.getsource(mcp_client_loop)
    assert "first_cursor =" in source
    assert "second_after = first_cursor" in source
    assert source.index("first_cursor =") < source.index("second_after = first_cursor")


def test_reference_runtime_values_are_opaque_and_per_run() -> None:
    first_state = HttpLiveState("bearer")
    second_state = HttpLiveState("bearer")
    first_session = first_state.create_session({})
    second_session = first_state.create_session({})
    repeat_session = second_state.create_session({})

    assert first_session.startswith("session:")
    assert second_session.startswith("session:")
    assert len({first_session, second_session, repeat_session}) == 3
    assert {first_session, second_session}.isdisjoint({"sGT1", "sGT2"})

    cursor = first_state.cursor_for_offset(first_session, 1)
    repeat_cursor = second_state.cursor_for_offset(repeat_session, 1)
    assert cursor.startswith("cursor:")
    assert cursor != repeat_cursor
    assert first_state.offset_for_cursor(first_session, cursor) == 1
    assert first_state.offset_for_cursor(first_session, "c1") is None


def test_mcp_reference_continuation_cursor_is_opaque() -> None:
    state = McpState()
    state.messages[SESSION_ID] = [{"session_id": SESSION_ID}]
    response = state.handle(
        rpc_request(
            "poll-1",
            "aicp.pollMessages",
            {"session_id": SESSION_ID, "after_cursor": "c0", "limit": 1},
        )
    )
    cursor = response["result"]["next_cursor"]
    assert cursor.startswith("cursor:")
    assert cursor != "c1"


def test_public_scenario_projection_contains_no_private_oracle_metadata() -> None:
    private_check_ids = {
        check_id
        for binding in ("BIND-HTTP", "BIND-MCP")
        for scenario in json.loads(
            (
                EVIDENCE_DIR
                / "live_bindings"
                / ("http_v01_scenarios.json" if binding == "BIND-HTTP" else "mcp_v01_scenarios.json")
            ).read_text(encoding="utf-8")
        )["scenarios"]
        for check_id in scenario["required_static_suite_checks"]
    }
    forbidden_fields = {
        "message_fixture",
        "required_static_suite_checks",
        "normative_source_refs",
        "expected",
        "expected_result",
        "expected_failure_code",
    }

    for binding in ("BIND-HTTP", "BIND-MCP"):
        for role in ("server_under_test", "client_under_test"):
            payload = _scenario_payload(binding, role, 1)
            serialized = json.dumps(payload, ensure_ascii=False)
            assert forbidden_fields.isdisjoint(_all_keys(payload))
            assert not any(
                value.startswith(("fixtures/", "conformance/", "docs/"))
                or value in private_check_ids
                for value in _all_strings(payload)
            ), serialized


def _all_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        return set(value) | {
            key for child in value.values() for key in _all_keys(child)
        }
    if isinstance(value, list):
        return {key for child in value for key in _all_keys(child)}
    return set()


def _all_strings(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        return [item for child in value.values() for item in _all_strings(child)]
    if isinstance(value, list):
        return [item for child in value for item in _all_strings(child)]
    return []


def test_rfc6455_client_key_requires_valid_base64_and_exactly_16_bytes() -> None:
    valid_key = base64.b64encode(secrets.token_bytes(16)).decode("ascii")
    validator = getattr(live_trace_normalization, "valid_websocket_key", None)
    assert callable(validator)
    assert validator(valid_key) is True
    assert validator("not-base64") is False
    assert validator(base64.b64encode(b"fifteen-bytes!!").decode("ascii")) is False
    assert validator(base64.b64encode(b"seventeen-bytes!!!").decode("ascii")) is False


@pytest.mark.parametrize(
    "invalid_key",
    [
        "not-base64",
        base64.b64encode(b"fifteen-bytes!!").decode("ascii"),
        base64.b64encode(b"seventeen-bytes!!!").decode("ascii"),
    ],
)
def test_reference_server_rejects_invalid_rfc6455_key(invalid_key: str) -> None:
    bearer = "rfc6455-key-test"
    server, state, thread = start_http_server(bearer)
    try:
        base = f"http://127.0.0.1:{server.server_address[1]}"
        status, _, created, _ = http_request(
            base,
            "POST",
            "/aicp/v1/sessions",
            bearer=bearer,
            body={"client_id": "rfc6455-key-test"},
        )
        assert status == 201 and created
        request = (
            f"GET /aicp/v1/sessions/{created['session_id']}/messages/ws HTTP/1.1\r\n"
            f"Host: 127.0.0.1:{server.server_address[1]}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {invalid_key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            f"Authorization: Bearer {bearer}\r\n\r\n"
        ).encode("ascii")
        with socket.create_connection(server.server_address, timeout=3) as client:
            client.sendall(request)
            response = client.recv(4096)
        assert response.startswith(b"HTTP/1.1 400")
        assert not any(record.get("transport") == "websocket" for record in state.records)
    finally:
        stop_http_server(server, thread)


def test_wss_challenge_control_exposes_no_untrusted_ca(tmp_path: Path) -> None:
    environment = _control_environment(
        binding_id="BIND-HTTP",
        role="client_under_test",
        run_index=1,
        ready_path=tmp_path / "ready.json",
        scenario_path=tmp_path / "scenario.json",
        bearer="test-bearer",
        websocket_url="wss://127.0.0.1:7443",
        wss_challenge_url="wss://127.0.0.1:7444",
        tls_ca_file=tmp_path / "trusted-ca.pem",
    )
    assert environment["AICP_LIVE_WSS_CHALLENGE_URL"].endswith(":7444")
    assert environment["AICP_LIVE_TLS_CA_FILE"].endswith("trusted-ca.pem")
    assert "AICP_LIVE_TLS_WRONG_CA_FILE" not in environment
