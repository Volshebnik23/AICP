#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import os
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = ROOT / "conformance" / "evidence"
if str(EVIDENCE_DIR) not in sys.path:
    sys.path.insert(0, str(EVIDENCE_DIR))

from live_bindings.live_binding_process import atomic_write_json  # noqa: E402
from live_bindings.live_http_transport import (  # noqa: E402
    execute_http_client,
    start_http_server,
)
from live_bindings.live_mcp_transport import mcp_client_loop, mcp_server_loop  # noqa: E402
from live_bindings.live_tls import EphemeralTlsMaterial, server_ssl_context  # noqa: E402


SERVER_MODES = {
    "good",
    "redirect_remote",
    "oversized_response",
    "oversized_sse_event",
    "oversized_ws_frame",
    "malformed_sse_event",
    "auth_not_enforced",
    "message_rewritten",
    "duplicate_stored_twice",
    "cross_session_replay_leak",
    "poll_wrong_session",
    "wrong_cursor",
    "ordering_broken",
    "head_wrong_session",
    "ack_ignored",
    "expiry_wrong",
    "overload_missing_retry",
    "overload_missing_hint",
    "closed_accepts",
    "sse_wrong_event_id",
    "sse_wrong_more",
    "sse_delivered_over_limit",
    "sse_last_event_mismatch",
    "sse_reconnect_wrong_messages",
    "sse_missing_retry",
    "ws_wrong_frame",
    "ws_wrong_cursor",
    "ws_wrong_more",
    "ws_ordering_broken",
    "ws_missing_retry",
    "websocket_wrong_accept",
    "websocket_missing_upgrade",
    "websocket_wrong_upgrade",
    "websocket_missing_connection",
    "websocket_wrong_connection",
    "websocket_malformed_headers",
    "secret_reflection",
}
CONTROL_NEGATIVE_MODES = {
    "no_ready",
    "ready_timeout",
    "wrong_binding",
    "wrong_version",
    "subject_mismatch",
    "non_loopback_endpoint",
    "redirect_remote",
    "premature_exit",
    "oversized_output",
    "malformed_descriptor",
    "forged_mark",
}
HTTP_SERVER_NEGATIVE_MODES = SERVER_MODES - {"good"}
HTTP_CLIENT_NEGATIVE_MODES = {
    "missing_authorization",
    "missing_idempotency_key",
    "wrong_idempotency_key",
    "wrong_session_path",
    "rewritten_envelope",
    "missing_ack",
    "invalid_sse_reconnect",
    "invalid_ws_pull",
    "invalid_idempotency_delimiter",
    "wss_untrusted_certificate",
}
MCP_SERVER_NEGATIVE_MODES = {
    "missing_poll_tool",
    "wrong_jsonrpc_id",
    "send_accepts_malformed",
    "duplicate_conflicting_hash",
    "poll_wrong_session",
    "poll_ignores_limit",
    "head_wrong_session",
    "object_hash_mismatch",
    "malformed_json",
    "oversized_line",
    "timeout",
    "mcp_server_ignores_after_cursor",
}
MCP_CLIENT_NEGATIVE_MODES = {
    "wrong_tool",
    "missing_message",
    "rewritten_message",
    "wrong_session",
    "wrong_object_hash",
    "malformed_json",
    "request_id_reuse",
    "mcp_missing_after_cursor",
    "mcp_wrong_after_cursor",
}

CORRECTION_NEGATIVE_MODES = {
    "environment_sentinel_inheritance",
    "secret_reflection",
    "observation_only_trace",
    "invalid_idempotency_delimiter",
    "websocket_wrong_accept",
    "websocket_missing_upgrade",
    "websocket_wrong_upgrade",
    "websocket_missing_connection",
    "websocket_wrong_connection",
    "wss_declared_without_wss_execution",
    "wss_untrusted_certificate",
    "mcp_missing_after_cursor",
    "mcp_wrong_after_cursor",
    "mcp_server_ignores_after_cursor",
}


def _required_environment(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise SystemExit(f"missing required live environment: {name}")
    return value


def _descriptor(
    *,
    binding: str,
    role: str,
    kind: str,
    implementation_id: str,
    implementation_version: str,
    mode: str,
    base_url: str | None = None,
    websocket_url: str | None = None,
) -> dict[str, object]:
    binding_id = "BIND-HTTP" if binding == "http" else "BIND-MCP"
    if mode == "wrong_binding":
        binding_id = "BIND-MCP" if binding == "http" else "BIND-HTTP"
    version = "9.9" if mode == "wrong_version" else "0.1"
    actual_id = implementation_id
    if mode == "subject_mismatch" and role == "client_under_test":
        actual_id += "-mismatch"
    digest = "sha256:" + hashlib.sha256(
        f"{kind}:{actual_id}:{implementation_version}:{binding}".encode("utf-8")
    ).hexdigest()
    features = {
        "request_response": True,
        "sse": binding == "http" and mode not in {"no_sse", "request_response_only"},
        "websocket": binding == "http" and mode not in {"no_websocket", "request_response_only"},
        "wss": binding == "http" and mode not in {"no_websocket", "request_response_only"},
    }
    if mode == "wss_declared_without_wss_execution":
        features["websocket"] = True
        features["wss"] = True
    descriptor: dict[str, object] = {
        "protocol": "aicp.live_endpoint_descriptor.v2",
        "binding_id": binding_id,
        "binding_version": version,
        "role": role,
        "implementation_kind": kind,
        "implementation_id": actual_id,
        "implementation_version": implementation_version,
        "implementation_digest": digest,
        "declared_features": features,
    }
    if binding == "http" and role == "server_under_test":
        descriptor["base_url"] = base_url
        if features["websocket"] and mode != "wss_declared_without_wss_execution":
            descriptor["websocket_url"] = websocket_url
    if binding == "mcp":
        descriptor["transport"] = "stdio"
    if mode == "non_loopback_endpoint":
        descriptor["base_url"] = "http://192.0.2.1:6553"
    if mode == "forged_mark":
        descriptor["claimed_compatibility_marks"] = ["AICP-BIND-HTTP-0.1"]
    return descriptor


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--binding", choices=("http", "mcp"), required=True)
    parser.add_argument("--role", choices=("server_under_test", "client_under_test"), required=True)
    parser.add_argument("--kind", choices=("reference_corpus", "external_implementation"), required=True)
    parser.add_argument("--mode", default="good")
    parser.add_argument("--implementation-id")
    parser.add_argument("--implementation-version", default="1.0.0-test")
    args = parser.parse_args()

    ready_path = Path(_required_environment("AICP_LIVE_READY_FILE"))
    _required_environment("AICP_LIVE_RUN_ID")
    _required_environment("AICP_LIVE_BINDING_ID")
    _required_environment("AICP_LIVE_BINDING_VERSION")
    _required_environment("AICP_LIVE_ROLE")
    if args.mode == "premature_exit":
        return 17
    if args.mode in {"no_ready", "ready_timeout"}:
        time.sleep(30)
        return 18
    if args.mode == "oversized_output":
        sys.stdout.write("X" * 300_000)
        sys.stdout.flush()
        time.sleep(30)
        return 19
    if args.mode == "malformed_descriptor":
        ready_path.write_text("{not-json", encoding="utf-8")
        time.sleep(30)
        return 20

    implementation_id = args.implementation_id or (
        f"aicp-{args.binding}-reference"
        if args.kind == "reference_corpus"
        else f"aicp-{args.binding}-external-test"
    )
    bearer = os.environ.get("AICP_LIVE_TEST_BEARER", "")

    if args.binding == "http" and args.role == "server_under_test":
        server_mode = args.mode if args.mode in SERVER_MODES else "good"
        server, state, _thread = start_http_server(bearer, mode=server_mode)
        base_url = f"http://127.0.0.1:{server.server_address[1]}"
        tls_material = EphemeralTlsMaterial(
            ca_file=Path(_required_environment("AICP_LIVE_TLS_CA_FILE")),
            cert_file=Path(_required_environment("AICP_LIVE_TLS_CERT_FILE")),
            key_file=Path(_required_environment("AICP_LIVE_TLS_KEY_FILE")),
            private_key_pem="",
        )
        tls_server, _tls_state, _tls_thread = start_http_server(
            bearer,
            mode=server_mode,
            ssl_context=server_ssl_context(tls_material),
            state=state,
        )
        websocket_url = f"wss://127.0.0.1:{tls_server.server_address[1]}"
        descriptor = _descriptor(
            binding=args.binding,
            role=args.role,
            kind=args.kind,
            implementation_id=implementation_id,
            implementation_version=args.implementation_version,
            mode=args.mode,
            base_url=base_url,
            websocket_url=websocket_url,
        )
        atomic_write_json(ready_path, descriptor)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            return 0

    descriptor = _descriptor(
        binding=args.binding,
        role=args.role,
        kind=args.kind,
        implementation_id=implementation_id,
        implementation_version=args.implementation_version,
        mode=args.mode,
    )
    atomic_write_json(ready_path, descriptor)

    if args.binding == "http":
        endpoint = _required_environment("AICP_LIVE_ENDPOINT_URL")
        websocket_url = os.environ.get("AICP_LIVE_WEBSOCKET_URL")
        tls_ca_file = os.environ.get("AICP_LIVE_TLS_CA_FILE")
        if args.mode == "wss_untrusted_certificate":
            tls_ca_file = os.environ.get("AICP_LIVE_TLS_WRONG_CA_FILE")
        execute_http_client(
            endpoint,
            bearer,
            role="client_under_test",
            mode=args.mode,
            declared_features=descriptor["declared_features"],
            websocket_url=websocket_url,
            tls_ca_file=tls_ca_file,
        )
        return 0
    if args.role == "server_under_test":
        return mcp_server_loop(sys.stdin.buffer, sys.stdout.buffer, mode=args.mode)
    return mcp_client_loop(sys.stdin.buffer, sys.stdout.buffer, mode=args.mode)


if __name__ == "__main__":
    raise SystemExit(main())
