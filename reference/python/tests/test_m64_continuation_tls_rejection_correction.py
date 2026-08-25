from __future__ import annotations

import json
import socket
import ssl
import sys
import time
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = ROOT / "conformance" / "evidence"
if str(EVIDENCE_DIR) not in sys.path:
    sys.path.insert(0, str(EVIDENCE_DIR))

from aicp_live_binding_runner import run_live_binding_evidence  # noqa: E402
from live_bindings.live_mcp_transport import McpState, SESSION_ID, rpc_request  # noqa: E402
from live_bindings.live_http_transport import (  # noqa: E402
    HttpLiveState,
    TlsChallengeObservation,
    reject_untrusted_tls_certificate,
    start_http_server,
    stop_http_server,
    websocket_pull,
)
from live_bindings.live_tls import (  # noqa: E402
    challenge_server_ssl_context,
    generate_ephemeral_tls_material,
)


IMPLEMENTATION = "conformance/evidence/live_bindings/live_binding_test_implementation.py"
ADVERSARIAL_CLIENT = "reference/python/tests/m64_adversarial_client.py"


def _command(binding: str, role: str, mode: str) -> list[str]:
    return [
        sys.executable,
        IMPLEMENTATION,
        "--binding",
        binding,
        "--role",
        role,
        "--kind",
        "external_implementation",
        "--mode",
        mode,
    ]


def _run_bad_client(binding: str, mode: str) -> dict:
    target = "BIND-HTTP@0.1" if binding == "http" else "BIND-MCP@0.1"
    return run_live_binding_evidence(
        _command(binding, "server_under_test", "good"),
        [sys.executable, ADVERSARIAL_CLIENT, "--mode", mode],
        target=target,
        mode="full-binding",
        timeout_seconds=3,
        timestamp="2026-08-24T00:00:00Z",
    )


def test_mcp_send_cursor_cannot_substitute_for_poll_continuation() -> None:
    report = _run_bad_client("mcp", "mcp_use_send_cursor_for_poll2")
    assert report["passed"] is False
    assert report["compatibility_marks"] == []
    evaluation_failures = [
        failure
        for failure in report["failures"]
        if failure["test_id"] == "EVIDENCE-LIVE-TRACE-EVALUATION-01"
    ]
    assert evaluation_failures
    assert "exact prior cursor" in evaluation_failures[0]["message"]


def test_mcp_poll_continuation_is_first_disclosed_by_poll_response() -> None:
    state = McpState()
    send = state.handle(
        rpc_request(
            "send",
            "aicp.sendMessage",
            {
                "message": {
                    "session_id": SESSION_ID,
                    "message_id": "message-1",
                    "message_hash": "sha256:" + "a" * 43,
                }
            },
        )
    )
    assert "cursor" not in send["result"]
    poll = state.handle(
        rpc_request(
            "poll",
            "aicp.pollMessages",
            {"session_id": SESSION_ID, "after_cursor": "c0", "limit": 1},
        )
    )
    continuation = poll["result"]["next_cursor"]
    assert continuation.startswith("cursor:")
    assert continuation not in json.dumps(send, sort_keys=True)


def test_raw_tcp_probe_is_not_certificate_rejection() -> None:
    report = _run_bad_client("http", "wss_tcp_probe_then_disable_verification")
    assert report["passed"] is False
    assert report["compatibility_marks"] == []
    assert any(
        failure["test_id"] == "EVIDENCE-LIVE-TRACE-EVALUATION-01"
        and "certificate rejection" in failure["message"]
        for failure in report["failures"]
    )


def test_plaintext_probe_is_not_certificate_rejection() -> None:
    report = _run_bad_client(
        "http", "wss_plaintext_probe_then_disable_verification"
    )
    assert report["passed"] is False
    assert report["compatibility_marks"] == []
    assert any(
        failure["test_id"] == "EVIDENCE-LIVE-TRACE-EVALUATION-01"
        and "certificate rejection" in failure["message"]
        for failure in report["failures"]
    )


def _wait_for_observation(
    observation: TlsChallengeObservation, predicate
) -> dict:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        evidence = observation.evidence()
        if predicate(evidence):
            return evidence
        time.sleep(0.01)
    return observation.evidence()


def test_real_tls_observer_distinguishes_required_outcomes(tmp_path: Path) -> None:
    trusted = generate_ephemeral_tls_material(tmp_path, stem="trusted")
    wrong = generate_ephemeral_tls_material(tmp_path, stem="wrong")

    def observe(action) -> dict:
        bearer = "tls-classifier-test"
        state = HttpLiveState(bearer)
        session = state.create_session({})
        observation = TlsChallengeObservation(endpoint_class="untrusted")
        server, _state, thread = start_http_server(
            bearer,
            ssl_context=challenge_server_ssl_context(trusted),
            state=state,
            tls_observation=observation,
        )
        try:
            action(server.server_address, session, bearer)
            return _wait_for_observation(
                observation,
                lambda value: value["tls_failure_class"] != "none"
                or value["tls_handshake_completed"]
                or value["websocket_application_handshake_observed"],
            )
        finally:
            stop_http_server(server, thread)

    def raw_tcp(address, _session, _bearer) -> None:
        with socket.create_connection(address, timeout=3):
            pass

    def plaintext(address, _session, _bearer) -> None:
        with socket.create_connection(address, timeout=3) as client:
            client.sendall(b"GET / HTTP/1.1\r\nHost: localhost\r\n\r\n")

    def wrong_root(address, _session, _bearer) -> None:
        reject_untrusted_tls_certificate(
            f"wss://127.0.0.1:{address[1]}",
            tls_ca_file=str(wrong.ca_file),
        )

    def client_hello_abort(address, _session, _bearer) -> None:
        context = ssl.create_default_context()
        incoming = ssl.MemoryBIO()
        outgoing = ssl.MemoryBIO()
        tls = context.wrap_bio(
            incoming,
            outgoing,
            server_side=False,
            server_hostname="127.0.0.1",
        )
        with pytest.raises(ssl.SSLWantReadError):
            tls.do_handshake()
        client_hello = outgoing.read()
        assert client_hello.startswith(b"\x16")
        with socket.create_connection(address, timeout=3) as client:
            client.sendall(client_hello)
            assert client.recv(4096)

    def trusted_tls(address, _session, _bearer) -> None:
        context = ssl.create_default_context(cafile=str(trusted.ca_file))
        with socket.create_connection(address, timeout=3) as raw:
            with context.wrap_socket(raw, server_hostname="127.0.0.1"):
                pass

    def trusted_websocket(address, session, bearer) -> None:
        status, _frame = websocket_pull(
            f"wss://127.0.0.1:{address[1]}",
            f"/aicp/v1/sessions/{session}/messages/ws",
            bearer=bearer,
            after="c0",
            limit=1,
            tls_ca_file=str(trusted.ca_file),
        )
        assert status == 101

    raw = observe(raw_tcp)
    plain = observe(plaintext)
    aborted = observe(client_hello_abort)
    rejected = observe(wrong_root)
    completed = observe(trusted_tls)
    upgraded = observe(trusted_websocket)

    assert raw["tls_failure_class"] == "no_tls_handshake"
    assert plain["tls_failure_class"] == "non_tls_protocol"
    assert aborted["tls_failure_class"] == "tls_pre_certificate_abort"
    assert rejected["tls_failure_class"] == "certificate_rejected"
    assert completed["tls_failure_class"] == "tls_handshake_completed"
    assert completed["websocket_application_handshake_observed"] is False
    assert upgraded["tls_failure_class"] == "tls_handshake_completed"
    assert upgraded["websocket_application_handshake_observed"] is True
