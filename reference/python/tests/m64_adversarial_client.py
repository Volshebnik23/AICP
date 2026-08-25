#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import socket
import ssl
import sys
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = ROOT / "conformance" / "evidence"
if str(EVIDENCE_DIR) not in sys.path:
    sys.path.insert(0, str(EVIDENCE_DIR))

from live_bindings.live_binding_process import (  # noqa: E402
    LiveProcessError,
    atomic_write_json,
    validate_loopback_url,
    write_json_line,
)
from live_bindings import live_http_transport  # noqa: E402
from live_bindings.live_http_transport import (  # noqa: E402
    execute_http_client,
    load_messages,
    message_for_session,
)
from live_bindings.live_mcp_transport import (  # noqa: E402
    OBJECT_HASH,
    SESSION_ID,
    rpc_request,
)
from live_bindings.live_binding_test_implementation import _descriptor  # noqa: E402


def _required_environment(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"missing required live environment: {name}")
    return value


def _mcp_send_cursor_substitution() -> int:
    message = message_for_session(load_messages()[0], SESSION_ID)
    second = message_for_session(load_messages()[1], SESSION_ID)
    requests = [
        rpc_request("rpc-send-1", "aicp.sendMessage", {"message": message}),
        rpc_request("rpc-send-2", "aicp.sendMessage", {"message": message}),
        rpc_request("rpc-send-3", "aicp.sendMessage", {"message": second}),
        rpc_request(
            "rpc-poll-1",
            "aicp.pollMessages",
            {"session_id": SESSION_ID, "after_cursor": "c0", "limit": 1},
        ),
    ]
    responses: list[dict] = []
    for request in requests:
        write_json_line(sys.stdout.buffer, request)
        raw = sys.stdin.buffer.readline(1_048_577)
        if not raw:
            return 3
        response = json.loads(raw.decode("utf-8"))
        if not isinstance(response, dict):
            return 3
        responses.append(response)

    saved_send_cursor = str((responses[0].get("result") or {}).get("cursor", ""))
    remaining = [
        rpc_request(
            "rpc-poll-2",
            "aicp.pollMessages",
            {
                "session_id": SESSION_ID,
                "after_cursor": saved_send_cursor,
                "limit": 1,
            },
        ),
        rpc_request("rpc-head-1", "aicp.getHead", {"session_id": SESSION_ID}),
        rpc_request(
            "rpc-object-1",
            "aicp.getObject",
            {"object_hash": OBJECT_HASH},
        ),
        rpc_request(
            "rpc-object-2",
            "aicp.getObject",
            {"object_hash": "sha256:" + "A" * 43},
        ),
        rpc_request(
            "rpc-invalid-1",
            "aicp.sendMessage",
            {"message": {"session_id": SESSION_ID}},
        ),
    ]
    for request in remaining:
        write_json_line(sys.stdout.buffer, request)
        raw = sys.stdin.buffer.readline(1_048_577)
        if not raw:
            return 3
        json.loads(raw.decode("utf-8"))
    return 0


def _probe_challenge(url: str, *, plaintext: bool) -> None:
    parsed = urlsplit(validate_loopback_url(url))
    if parsed.scheme != "wss":
        raise LiveProcessError("TLS challenge endpoint must use wss")
    with socket.create_connection((parsed.hostname, parsed.port), timeout=3) as sock:
        if plaintext:
            sock.sendall(
                f"GET / HTTP/1.1\r\nHost: {parsed.hostname}:{parsed.port}\r\n\r\n".encode(
                    "ascii"
                )
            )


def _http_probe_then_disable_verification(*, plaintext: bool) -> int:
    challenge_url = _required_environment("AICP_LIVE_WSS_CHALLENGE_URL")
    real_websocket_pull = live_http_transport.websocket_pull

    def adversarial_websocket_pull(websocket_url: str, path: str, **kwargs):
        if websocket_url == challenge_url:
            _probe_challenge(websocket_url, plaintext=plaintext)
            raise ssl.SSLError("test-only non-TLS challenge probe")
        kwargs["tls_verify"] = False
        return real_websocket_pull(websocket_url, path, **kwargs)

    live_http_transport.websocket_pull = adversarial_websocket_pull
    live_http_transport.reject_untrusted_tls_certificate = (
        lambda websocket_url, **_kwargs: _probe_challenge(
            websocket_url, plaintext=plaintext
        )
    )
    execute_http_client(
        _required_environment("AICP_LIVE_ENDPOINT_URL"),
        _required_environment("AICP_LIVE_TEST_BEARER"),
        role="client_under_test",
        declared_features={
            "request_response": True,
            "sse": True,
            "websocket": True,
            "wss": True,
        },
        websocket_url=_required_environment("AICP_LIVE_WEBSOCKET_URL"),
        wss_challenge_url=challenge_url,
        tls_ca_file=_required_environment("AICP_LIVE_TLS_CA_FILE"),
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=(
            "mcp_use_send_cursor_for_poll2",
            "wss_tcp_probe_then_disable_verification",
            "wss_plaintext_probe_then_disable_verification",
        ),
        required=True,
    )
    args = parser.parse_args()
    binding = "mcp" if args.mode.startswith("mcp_") else "http"
    descriptor = _descriptor(
        binding=binding,
        role="client_under_test",
        kind="external_implementation",
        implementation_id=f"aicp-{binding}-external-test",
        implementation_version="1.0.0-test",
        mode="good",
    )
    atomic_write_json(Path(_required_environment("AICP_LIVE_READY_FILE")), descriptor)
    if binding == "mcp":
        return _mcp_send_cursor_substitution()
    return _http_probe_then_disable_verification(
        plaintext=args.mode == "wss_plaintext_probe_then_disable_verification"
    )


if __name__ == "__main__":
    raise SystemExit(main())
