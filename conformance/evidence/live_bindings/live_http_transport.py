from __future__ import annotations

import base64
import copy
import hashlib
import http.client
import json
import os
import secrets
import socket
import ssl
import struct
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = ROOT / "conformance" / "evidence"
REF_PY = ROOT / "reference" / "python"

import sys

for path in (EVIDENCE_DIR, REF_PY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from aicp_ref.hashing import message_hash_from_body  # noqa: E402
from target_catalog import canonical_digest  # noqa: E402
from live_bindings.live_binding_process import LiveProcessError, validate_loopback_url  # noqa: E402
from live_bindings.live_binding_trace import observation  # noqa: E402
from live_bindings.live_http_capture import (  # noqa: E402
    attach_http_transport_evidence,
    idempotency_key_valid,
)


MAX_BODY_BYTES = 1_048_576
MAX_SSE_BYTES = 262_144
MAX_WS_FRAME_BYTES = 262_144
ROLE_PREFIX = {
    "server_under_test": "LIVE-HTTP-SERVER",
    "client_under_test": "LIVE-HTTP-CLIENT",
}


def load_messages() -> list[dict[str, Any]]:
    path = ROOT / "fixtures/golden_transcripts/GT-01_happy_path_signed.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def message_for_session(message: dict[str, Any], session_id: str) -> dict[str, Any]:
    updated = copy.deepcopy(message)
    updated["session_id"] = session_id
    updated.pop("signatures", None)
    updated.pop("message_hash", None)
    updated["message_hash"] = message_hash_from_body(updated)
    return updated


def _cursor_index(value: str | None) -> int:
    if value in {None, "", "c0"}:
        return 0
    if isinstance(value, str) and value.startswith("c") and value[1:].isdigit():
        return int(value[1:])
    return 0


@dataclass
class HttpLiveState:
    bearer: str
    mode: str = "good"
    sessions: dict[str, dict[str, Any]] = field(default_factory=dict)
    records: list[dict[str, Any]] = field(default_factory=list)
    lock: threading.Lock = field(default_factory=threading.Lock)
    session_counter: int = 0

    def create_session(self, channel_properties: dict[str, Any]) -> str:
        with self.lock:
            self.session_counter += 1
            session_id = (
                self.bearer
                if self.mode == "secret_reflection" and self.session_counter == 1
                else f"sGT{self.session_counter}"
            )
            self.sessions[session_id] = {
                "messages": [],
                "message_ids": {},
                "closed": False,
                "ack": None,
                "channel_properties": channel_properties,
            }
            return session_id

    def add_record(self, record: dict[str, Any]) -> None:
        with self.lock:
            self.records.append(record)


class _NoRedirectHandler(BaseHTTPRequestHandler):
    server_version = "AICPLiveReference/1"
    protocol_version = "HTTP/1.1"

    @property
    def state(self) -> HttpLiveState:
        return self.server.live_state  # type: ignore[attr-defined]

    def log_message(self, _format: str, *_args: Any) -> None:
        return

    def _headers(self) -> dict[str, str]:
        return {str(key).lower(): str(value) for key, value in self.headers.items()}

    def _body(self) -> dict[str, Any] | None:
        raw_length = self.headers.get("Content-Length", "0")
        try:
            length = int(raw_length)
        except ValueError:
            length = MAX_BODY_BYTES + 1
        if length < 0 or length > MAX_BODY_BYTES:
            raise LiveProcessError("HTTP request body exceeded configured byte limit")
        raw = self.rfile.read(length) if length else b""
        if not raw:
            return None
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise LiveProcessError("HTTP request body is not valid UTF-8 JSON") from exc
        if not isinstance(value, dict):
            raise LiveProcessError("HTTP request body must be an object")
        return value

    def _record(
        self,
        *,
        status: int,
        body: dict[str, Any] | None,
        request_body: dict[str, Any] | None,
        response_headers: dict[str, str] | None = None,
        transport: str = "http",
    ) -> None:
        parsed = urlsplit(self.path)
        self.state.add_record(
            {
                "method": self.command,
                "path": parsed.path,
                "query": {key: values[-1] for key, values in parse_qs(parsed.query, keep_blank_values=True).items()},
                "headers": self._headers(),
                "body": request_body,
                "status": status,
                "response_body": body,
                "response_headers": {str(key).lower(): str(value) for key, value in (response_headers or {}).items()},
                "transport": transport,
            }
        )

    def _send_json(
        self,
        status: int,
        body: dict[str, Any] | None,
        *,
        request_body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        encoded = b"" if body is None else json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        if body is not None:
            self.send_header("Content-Type", "application/json")
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        if encoded:
            self.wfile.write(encoded)
        self._record(status=status, body=body, request_body=request_body, response_headers=headers)

    def _authorized(self, request_body: dict[str, Any] | None) -> bool:
        if self.state.mode == "auth_not_enforced":
            return True
        expected = f"Bearer {self.state.bearer}"
        if self.headers.get("Authorization") == expected:
            return True
        self._send_json(401, {"reason_code": "unauthorized"}, request_body=request_body)
        return False

    def do_POST(self) -> None:  # noqa: N802
        try:
            request_body = self._body()
            if not self._authorized(request_body):
                return
            if self.state.mode == "redirect_remote":
                self.send_response(302)
                self.send_header("Location", "http://192.0.2.1/escape")
                self.send_header("Content-Length", "0")
                self.end_headers()
                self._record(
                    status=302,
                    body=None,
                    request_body=request_body,
                    response_headers={"Location": "http://192.0.2.1/escape"},
                )
                return
            parsed = urlsplit(self.path)
            path = parsed.path
            if path == "/aicp/v1/sessions":
                if self.state.mode == "oversized_response":
                    self._send_json(
                        201,
                        {"session_id": "s1", "padding": "X" * (MAX_BODY_BYTES + 1)},
                        request_body=request_body,
                    )
                    return
                body = request_body or {}
                session_id = self.state.create_session(dict(body.get("channel_properties") or {}))
                self._send_json(
                    201,
                    {
                        "session_id": session_id,
                        "expires_at": "2030-01-01T00:00:00Z",
                        "auth_required": True,
                    },
                    request_body=request_body,
                )
                return
            parts = path.strip("/").split("/")
            if len(parts) != 5 or parts[:3] != ["aicp", "v1", "sessions"]:
                self._send_json(404, {"reason_code": "not_found"}, request_body=request_body)
                return
            session_id = parts[3]
            operation = parts[4]
            session = self.state.sessions.get(session_id)
            if session is None:
                self._send_json(404, {"reason_code": "unknown_session"}, request_body=request_body)
                return
            if operation == "messages":
                if session["closed"] and self.state.mode != "closed_accepts":
                    self._send_json(409, {"reason_code": "session_closed"}, request_body=request_body)
                    return
                message = request_body or {}
                if self.state.mode == "message_rewritten":
                    message = copy.deepcopy(message)
                    message["sender"] = "agent:rewritten"
                content_type = self.headers.get("Content-Type", "")
                idem = self.headers.get("Idempotency-Key", "")
                message_id = str(message.get("message_id", ""))
                if "application/json" not in content_type or not idempotency_key_valid(idem, message_id):
                    self._send_json(400, {"reason_code": "invalid_ingest_headers"}, request_body=request_body)
                    return
                if message.get("session_id") != session_id:
                    self._send_json(409, {"reason_code": "session_mismatch"}, request_body=request_body)
                    return
                existing = session["message_ids"].get(message_id)
                if existing is not None:
                    if self.state.mode == "duplicate_stored_twice":
                        session["messages"].append(copy.deepcopy(message))
                    self._send_json(
                        200,
                        {"accepted": True, "message_id": message_id},
                        request_body=request_body,
                        headers={"AICP-Replay": "true"},
                    )
                    return
                if self.state.mode == "cross_session_replay_leak" and any(
                    message_id in candidate["message_ids"]
                    for key, candidate in self.state.sessions.items()
                    if key != session_id
                ):
                    self._send_json(
                        200,
                        {"accepted": True, "message_id": message_id},
                        request_body=request_body,
                        headers={"AICP-Replay": "true"},
                    )
                    return
                session["message_ids"][message_id] = copy.deepcopy(message)
                session["messages"].append(copy.deepcopy(message))
                if self.state.mode == "ordering_broken" and len(session["messages"]) > 1:
                    session["messages"][-1]["prev_msg_hash"] = "sha256:" + "0" * 64
                self._send_json(202, {"accepted": True, "message_id": message_id}, request_body=request_body)
                return
            if operation == "ack":
                cursor = str((request_body or {}).get("cursor", ""))
                if self.state.mode == "ack_ignored":
                    self._send_json(409, {"reason_code": "ack_ignored"}, request_body=request_body)
                    return
                if self.state.mode == "wrong_cursor" and cursor == "c999":
                    self._send_json(409, {"reason_code": "unknown_cursor"}, request_body=request_body)
                    return
                session["ack"] = cursor
                self._send_json(204, None, request_body=request_body)
                return
            if operation == "close":
                session["closed"] = True
                self._send_json(204, None, request_body=request_body)
                return
            self._send_json(404, {"reason_code": "not_found"}, request_body=request_body)
        except LiveProcessError as exc:
            self._send_json(400, {"reason_code": "invalid_request", "detail": str(exc)}, request_body=None)

    def do_GET(self) -> None:  # noqa: N802
        request_body = None
        if not self._authorized(request_body):
            return
        parsed = urlsplit(self.path)
        path = parsed.path
        parts = path.strip("/").split("/")
        if len(parts) < 5 or parts[:3] != ["aicp", "v1", "sessions"]:
            self._send_json(404, {"reason_code": "not_found"})
            return
        session_id = parts[3]
        session = self.state.sessions.get(session_id)
        if session is None:
            self._send_json(404, {"reason_code": "unknown_session"})
            return
        if path.endswith("/messages/stream"):
            self._send_sse(session_id, session, parsed)
            return
        if path.endswith("/messages/ws") and self.headers.get("Upgrade", "").lower() == "websocket":
            self._serve_websocket(session_id, session)
            return
        if path.endswith("/messages"):
            query = {key: values[-1] for key, values in parse_qs(parsed.query, keep_blank_values=True).items()}
            after = query.get("after", "")
            if after == "expired" and self.state.mode != "expiry_wrong":
                self._send_json(410, {"reason_code": "cursor_expired", "min_cursor": "c1"})
                return
            try:
                limit = max(1, min(int(query.get("limit", "1")), 1000))
            except ValueError:
                limit = 1
            source = session["messages"]
            if self.state.mode == "poll_wrong_session":
                other = next((value for key, value in self.state.sessions.items() if key != session_id), session)
                source = other["messages"]
            start = _cursor_index(after)
            messages = copy.deepcopy(source[start : start + limit])
            next_cursor = f"c{start + len(messages)}"
            if self.state.mode == "wrong_cursor":
                next_cursor = "c999"
            self._send_json(200, {"messages": messages, "next_cursor": next_cursor})
            return
        if path.endswith("/head"):
            messages = session["messages"]
            actual_session = session_id
            if self.state.mode == "head_wrong_session":
                actual_session = "s-other"
            body: dict[str, Any] = {"session_id": actual_session, "branch_id": "main"}
            if messages:
                body.update(
                    {
                        "head_message_id": messages[-1].get("message_id"),
                        "head_message_hash": messages[-1].get("message_hash"),
                    }
                )
            self._send_json(200, body)
            return
        if path.endswith("/overload"):
            headers = {"Retry-After": "5", "RateLimit-Remaining": "0"}
            if self.state.mode == "overload_missing_retry":
                headers.pop("Retry-After")
            if self.state.mode == "overload_missing_hint":
                headers.pop("RateLimit-Remaining")
            self._send_json(429, {"reason_code": "overloaded"}, headers=headers)
            return
        self._send_json(404, {"reason_code": "not_found"})

    def _send_sse(self, session_id: str, session: dict[str, Any], parsed: Any) -> None:
        query = {key: values[-1] for key, values in parse_qs(parsed.query, keep_blank_values=True).items()}
        after = query.get("after", "")
        last_event = self.headers.get("Last-Event-ID")
        if (
            last_event is not None
            and after
            and last_event != after
            and self.state.mode != "sse_last_event_mismatch"
        ):
            self._send_json(400, {"reason_code": "cursor_mismatch"})
            return
        if last_event is not None:
            after = last_event
        try:
            limit = max(1, min(int(query.get("limit", "1")), 1000))
        except ValueError:
            limit = 1
        events: list[tuple[str | None, str, dict[str, Any]]] = []
        if after == "overload":
            retry = "5s" if self.state.mode != "sse_missing_retry" else ""
            events.append((None, "overload", {"retry_after": retry}))
        else:
            start = _cursor_index(after)
            if self.state.mode == "sse_reconnect_wrong_messages" and last_event is not None:
                start = 0
            take = limit + 1 if self.state.mode == "sse_delivered_over_limit" else limit
            delivered = copy.deepcopy(session["messages"][start : start + take])
            if (
                self.state.mode == "sse_delivered_over_limit"
                and delivered
                and len(delivered) <= limit
            ):
                delivered.append(copy.deepcopy(delivered[-1]))
            chunks = [delivered[index : index + 2] for index in range(0, len(delivered), 2)] or [[]]
            offset = start
            for index, chunk in enumerate(chunks):
                offset += len(chunk)
                cursor = f"c{offset}"
                event_id = "c999" if self.state.mode == "sse_wrong_event_id" else cursor
                more = index < len(chunks) - 1
                if self.state.mode == "sse_wrong_more":
                    more = True
                events.append(
                    (
                        event_id,
                        "messages",
                        {"messages": chunk, "cursor_after_last": cursor, "more": more},
                    )
                )
        raw_parts: list[bytes] = []
        for event_id, event_name, data in events:
            if event_id is not None:
                raw_parts.append(f"id: {event_id}\n".encode("utf-8"))
            raw_parts.append(f"event: {event_name}\n".encode("utf-8"))
            raw_parts.append(("data: " + json.dumps(data, separators=(",", ":"), ensure_ascii=False) + "\n\n").encode("utf-8"))
        encoded = b"".join(raw_parts)
        if self.state.mode == "oversized_sse_event":
            encoded = b"event: messages\ndata: " + b"X" * (MAX_SSE_BYTES + 1) + b"\n\n"
        elif self.state.mode == "malformed_sse_event":
            encoded = b"event: messages\ndata: {not-json}\n\n"
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)
        self.wfile.flush()
        self._record(
            status=200,
            body={
                "events": [
                    {"id": event_id, "event": event_name, "data": data}
                    for event_id, event_name, data in events
                ]
            },
            request_body=None,
            response_headers={"Content-Type": "text/event-stream"},
            transport="sse",
        )

    def _serve_websocket(self, session_id: str, session: dict[str, Any]) -> None:
        key = self.headers.get("Sec-WebSocket-Key", "")
        accept = base64.b64encode(hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")).digest()).decode("ascii")
        if self.state.mode == "websocket_malformed_headers":
            self.wfile.write(b"HTTP/1.1 101 Switching Protocols\r\nMalformed\r\n\r\n")
            self.wfile.flush()
        else:
            self.send_response(101, "Switching Protocols")
            if self.state.mode != "websocket_missing_upgrade":
                self.send_header(
                    "Upgrade",
                    "h2c" if self.state.mode == "websocket_wrong_upgrade" else "websocket",
                )
            if self.state.mode != "websocket_missing_connection":
                self.send_header(
                    "Connection",
                    "keep-alive" if self.state.mode == "websocket_wrong_connection" else "Upgrade",
                )
            self.send_header(
                "Sec-WebSocket-Accept",
                "wrong-accept" if self.state.mode == "websocket_wrong_accept" else accept,
            )
            self.end_headers()
        raw = _read_ws_frame(self.rfile, expect_masked=True)
        try:
            request = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            request = {}
        if request.get("after") == "overload":
            response: dict[str, Any] = {"type": "overload", "retry_after": "5s"}
            if self.state.mode == "ws_missing_retry":
                response.pop("retry_after")
        else:
            start = _cursor_index(str(request.get("after", "")))
            limit = max(1, min(int(request.get("limit", 1)), 1000))
            messages = copy.deepcopy(session["messages"][start : start + limit])
            if self.state.mode == "ws_ordering_broken" and len(messages) > 1:
                messages[1]["prev_msg_hash"] = "sha256:" + "0" * 64
            response = {
                "type": "messages",
                "messages": messages,
                "cursor_after_last": f"c{start + len(messages)}",
                "more": False,
            }
            if self.state.mode == "ws_wrong_frame":
                response["type"] = "invalid"
            if self.state.mode == "ws_wrong_cursor":
                response["cursor_after_last"] = "c999"
            if self.state.mode == "ws_wrong_more":
                response["more"] = True
        response_bytes = json.dumps(response, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        if self.state.mode == "oversized_ws_frame":
            response_bytes = b"X" * (MAX_WS_FRAME_BYTES + 1)
        _write_ws_frame(self.wfile, response_bytes, masked=False)
        self.state.add_record(
            {
                "method": "GET",
                "path": urlsplit(self.path).path,
                "query": {},
                "headers": self._headers(),
                "body": request,
                "status": 101,
                "response_body": response,
                "response_headers": {
                    "upgrade": (
                        ""
                        if self.state.mode == "websocket_missing_upgrade"
                        else "h2c"
                        if self.state.mode == "websocket_wrong_upgrade"
                        else "websocket"
                    ),
                    "connection": (
                        ""
                        if self.state.mode == "websocket_missing_connection"
                        else "keep-alive"
                        if self.state.mode == "websocket_wrong_connection"
                        else "Upgrade"
                    ),
                    "sec-websocket-accept": "wrong-accept" if self.state.mode == "websocket_wrong_accept" else accept,
                },
                "transport": "websocket",
                "scheme": getattr(self.server, "live_scheme", "ws"),
                "tls_verified": getattr(self.server, "live_scheme", "ws") == "wss",
            }
        )
        self.close_connection = True


def start_http_server(
    bearer: str,
    *,
    mode: str = "good",
    ssl_context: ssl.SSLContext | None = None,
    state: HttpLiveState | None = None,
) -> tuple[ThreadingHTTPServer, HttpLiveState, threading.Thread]:
    state = state or HttpLiveState(bearer=bearer, mode=mode)
    server = ThreadingHTTPServer(("127.0.0.1", 0), _NoRedirectHandler)
    if ssl_context is not None:
        server.socket = ssl_context.wrap_socket(server.socket, server_side=True)
        server.live_scheme = "wss"  # type: ignore[attr-defined]
    else:
        server.live_scheme = "ws"  # type: ignore[attr-defined]
    server.daemon_threads = True
    server.live_state = state  # type: ignore[attr-defined]
    thread = threading.Thread(target=server.serve_forever, name="aicp-live-http", daemon=True)
    thread.start()
    return server, state, thread


def stop_http_server(server: ThreadingHTTPServer, thread: threading.Thread) -> None:
    server.shutdown()
    server.server_close()
    thread.join(timeout=2)
    if thread.is_alive():
        raise LiveProcessError("reference HTTP server thread did not stop")


def _read_exact(stream: Any, length: int) -> bytes:
    chunks: list[bytes] = []
    remaining = length
    while remaining:
        chunk = stream.read(remaining)
        if not chunk:
            raise LiveProcessError("WebSocket frame ended prematurely")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _read_ws_frame(stream: Any, *, expect_masked: bool) -> bytes:
    header = _read_exact(stream, 2)
    first, second = header
    if first & 0x0F not in {1, 8}:
        raise LiveProcessError("unsupported WebSocket opcode")
    masked = bool(second & 0x80)
    if masked is not expect_masked:
        raise LiveProcessError("WebSocket masking direction is invalid")
    length = second & 0x7F
    if length == 126:
        length = struct.unpack("!H", _read_exact(stream, 2))[0]
    elif length == 127:
        length = struct.unpack("!Q", _read_exact(stream, 8))[0]
    if length > MAX_WS_FRAME_BYTES:
        raise LiveProcessError("WebSocket frame exceeded byte limit")
    mask = _read_exact(stream, 4) if masked else b""
    payload = bytearray(_read_exact(stream, length))
    if masked:
        for index in range(len(payload)):
            payload[index] ^= mask[index % 4]
    return bytes(payload)


def _write_ws_frame(stream: Any, payload: bytes, *, masked: bool) -> None:
    if len(payload) > MAX_WS_FRAME_BYTES:
        raise LiveProcessError("WebSocket frame exceeded byte limit")
    header = bytearray([0x81])
    mask_bit = 0x80 if masked else 0
    if len(payload) < 126:
        header.append(mask_bit | len(payload))
    elif len(payload) <= 65535:
        header.append(mask_bit | 126)
        header.extend(struct.pack("!H", len(payload)))
    else:
        header.append(mask_bit | 127)
        header.extend(struct.pack("!Q", len(payload)))
    data = bytearray(payload)
    if masked:
        key = secrets.token_bytes(4)
        header.extend(key)
        for index in range(len(data)):
            data[index] ^= key[index % 4]
    stream.write(bytes(header) + bytes(data))
    stream.flush()


class _NoRedirect(http.client.HTTPConnection):
    pass


class _NoRedirectHttps(http.client.HTTPSConnection):
    pass


def http_request(
    base_url: str,
    method: str,
    path: str,
    *,
    bearer: str | None,
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    capture: list[dict[str, Any]] | None = None,
    tls_ca_file: str | None = None,
) -> tuple[int, dict[str, str], dict[str, Any] | None, bytes]:
    base = validate_loopback_url(base_url)
    parsed = urlsplit(base)
    if parsed.scheme == "https":
        if not tls_ca_file:
            raise LiveProcessError("verified HTTPS requires an explicit per-run CA file")
        context = ssl.create_default_context(cafile=tls_ca_file)
        connection: http.client.HTTPConnection = _NoRedirectHttps(
            parsed.hostname,
            parsed.port,
            timeout=3,
            context=context,
        )
    elif parsed.scheme == "http":
        connection = _NoRedirect(parsed.hostname, parsed.port, timeout=3)
    else:
        raise LiveProcessError("HTTP request scheme is not supported")
    request_headers = dict(headers or {})
    if bearer is not None:
        request_headers["Authorization"] = f"Bearer {bearer}"
    encoded = None
    if body is not None:
        encoded = json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        request_headers.setdefault("Content-Type", "application/json")
    try:
        connection.request(method, path, body=encoded, headers=request_headers)
        response = connection.getresponse()
        raw = response.read(MAX_BODY_BYTES + 1)
        if len(raw) > MAX_BODY_BYTES:
            raise LiveProcessError("HTTP response body exceeded configured byte limit")
        response_headers = {key.lower(): value for key, value in response.getheaders()}
        value = None
        if raw and "application/json" in response_headers.get("content-type", ""):
            try:
                parsed_body = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise LiveProcessError("HTTP response body is not valid UTF-8 JSON") from exc
            if not isinstance(parsed_body, dict):
                raise LiveProcessError("HTTP response JSON must be an object")
            value = parsed_body
        if capture is not None:
            capture.append(
                {
                    "method": method,
                    "path": path.split("?", 1)[0],
                    "query": {
                        key: values[-1]
                        for key, values in parse_qs(
                            urlsplit(path).query,
                            keep_blank_values=True,
                        ).items()
                    },
                    "headers": {str(key).lower(): str(value) for key, value in request_headers.items()},
                    "body": copy.deepcopy(body),
                    "status": response.status,
                    "response_body": copy.deepcopy(value),
                    "response_headers": response_headers,
                    "transport": "http",
                }
            )
        return response.status, response_headers, value, raw
    finally:
        connection.close()


def read_sse(
    base_url: str,
    path: str,
    *,
    bearer: str,
    last_event_id: str | None = None,
    capture: list[dict[str, Any]] | None = None,
) -> tuple[int, dict[str, str], list[dict[str, Any]], bytes]:
    headers = {"Accept": "text/event-stream"}
    if last_event_id is not None:
        headers["Last-Event-ID"] = last_event_id
    status, response_headers, body, raw = http_request(
        base_url,
        "GET",
        path,
        bearer=bearer,
        headers=headers,
        capture=capture,
    )
    if body is not None:
        return status, response_headers, [], raw
    if len(raw) > MAX_SSE_BYTES:
        raise LiveProcessError("SSE stream exceeded byte limit")
    events: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    for raw_line in raw.decode("utf-8").splitlines():
        if not raw_line:
            if current:
                events.append(current)
                current = {}
            continue
        field, separator, value = raw_line.partition(":")
        if not separator:
            continue
        value = value.lstrip(" ")
        if field == "data":
            parsed_data = json.loads(value)
            current["data"] = parsed_data
        elif field in {"id", "event"}:
            current[field] = value
    if current:
        events.append(current)
    if capture is not None and capture:
        capture[-1]["transport"] = "sse"
        capture[-1]["events"] = copy.deepcopy(events)
    return status, response_headers, events, raw


def websocket_pull(
    websocket_url: str,
    path: str,
    *,
    bearer: str,
    after: str,
    limit: int,
    tls_ca_file: str | None = None,
    capture: list[dict[str, Any]] | None = None,
) -> tuple[int, dict[str, Any]]:
    parsed = urlsplit(validate_loopback_url(websocket_url))
    raw_sock = socket.create_connection((parsed.hostname, parsed.port), timeout=3)
    tls_verified = False
    if parsed.scheme == "wss":
        if not tls_ca_file:
            raw_sock.close()
            raise LiveProcessError("WSS requires an explicit per-run CA file")
        context = ssl.create_default_context(cafile=tls_ca_file)
        sock: socket.socket = context.wrap_socket(raw_sock, server_hostname=parsed.hostname)
        tls_verified = True
    elif parsed.scheme == "ws":
        sock = raw_sock
    else:
        raw_sock.close()
        raise LiveProcessError("WebSocket endpoint must use ws or wss")
    try:
        key = base64.b64encode(secrets.token_bytes(16)).decode("ascii")
        request = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {parsed.hostname}:{parsed.port}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            f"Authorization: Bearer {bearer}\r\n\r\n"
        ).encode("ascii")
        sock.sendall(request)
        response = b""
        while b"\r\n\r\n" not in response:
            chunk = sock.recv(4096)
            if not chunk:
                raise LiveProcessError("WebSocket handshake ended prematurely")
            response += chunk
            if len(response) > 32_768:
                raise LiveProcessError("WebSocket handshake exceeded byte limit")
        status_line = response.split(b"\r\n", 1)[0]
        try:
            status = int(status_line.split()[1])
        except (IndexError, ValueError) as exc:
            raise LiveProcessError("WebSocket handshake status is invalid") from exc
        header_lines = response.split(b"\r\n\r\n", 1)[0].split(b"\r\n")[1:]
        response_headers: dict[str, str] = {}
        for raw_line in header_lines:
            if b":" not in raw_line:
                raise LiveProcessError("WebSocket handshake response header is malformed")
            raw_name, raw_value = raw_line.split(b":", 1)
            try:
                name = raw_name.decode("ascii").strip().lower()
                value_text = raw_value.decode("ascii").strip()
            except UnicodeDecodeError as exc:
                raise LiveProcessError("WebSocket handshake response headers are not ASCII") from exc
            response_headers[name] = value_text
        tokens = lambda value: {part.strip().lower() for part in value.split(",")}
        expected_accept = base64.b64encode(
            hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode("ascii")).digest()
        ).decode("ascii")
        if (
            status != 101
            or "websocket" not in tokens(response_headers.get("upgrade", ""))
            or "upgrade" not in tokens(response_headers.get("connection", ""))
            or response_headers.get("sec-websocket-accept") != expected_accept
        ):
            raise LiveProcessError("WebSocket handshake validation failed")
        stream = sock.makefile("rwb", buffering=0)
        client_frame = {"type": "pull", "after": after, "limit": limit}
        _write_ws_frame(
            stream,
            json.dumps(client_frame, separators=(",", ":")).encode("utf-8"),
            masked=True,
        )
        raw = _read_ws_frame(stream, expect_masked=False)
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict):
            raise LiveProcessError("WebSocket response frame must be an object")
        if capture is not None:
            capture.append(
                {
                    "method": "GET",
                    "path": path,
                    "query": {},
                    "headers": {
                        "upgrade": "websocket",
                        "connection": "Upgrade",
                        "sec-websocket-key": key,
                        "sec-websocket-version": "13",
                        "authorization": f"Bearer {bearer}",
                    },
                    "body": copy.deepcopy(client_frame),
                    "status": status,
                    "response_body": copy.deepcopy(value),
                    "response_headers": response_headers,
                    "transport": "websocket",
                    "scheme": parsed.scheme,
                    "tls_verified": tls_verified,
                    "client_frame": copy.deepcopy(client_frame),
                    "server_frame": copy.deepcopy(value),
                }
            )
        return status, value
    finally:
        sock.close()


def _interaction(
    role: str,
    suffix: str,
    transport: str,
    operation: str,
    facts: dict[str, Any],
) -> dict[str, Any]:
    scenario_id = f"{ROLE_PREFIX[role]}-{suffix}"
    return {
        "interaction_id": scenario_id.lower(),
        "role": role,
        "scenario_id": scenario_id,
        "transport": transport,
        "operation": operation,
        "observations": [observation(name, value) for name, value in sorted(facts.items())],
    }


def execute_http_client(
    base_url: str,
    bearer: str,
    *,
    role: str,
    mode: str = "good",
    declared_features: dict[str, Any] | None = None,
    websocket_url: str | None = None,
    tls_ca_file: str | None = None,
) -> list[dict[str, Any]]:
    messages = load_messages()
    features = declared_features or {
        "request_response": True,
        "sse": True,
        "websocket": True,
        "wss": False,
    }
    records: list[dict[str, Any]] = []

    def request(
        method: str,
        path: str,
        *,
        bearer: str | None,
        body: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, str], dict[str, Any] | None, bytes]:
        return http_request(
            base_url,
            method,
            path,
            bearer=bearer,
            body=body,
            headers=headers,
            capture=records,
        )

    boundary = {"network_boundary": "loopback_socket"}
    unauthorized_status, _, _, _ = request("POST", "/aicp/v1/sessions", bearer=None, body={"client_id": "live-client"})
    auth_bearer = None if mode == "missing_authorization" else bearer
    status1, _, created1, _ = request(
        "POST",
        "/aicp/v1/sessions",
        bearer=auth_bearer,
        body={
            "client_id": "live-client",
            "channel_properties": {
                "CP-ACK-0.1": "explicit",
                "CP-ORDERING-0.1": "ordered",
                "CP-REPLAY-WINDOW-0.1": 2,
            },
        },
    )
    if status1 != 201 or not isinstance(created1, dict):
        raise LiveProcessError("HTTP client could not create primary session")
    status2, _, created2, _ = request("POST", "/aicp/v1/sessions", bearer=bearer, body={"client_id": "live-client-secondary"})
    if status2 != 201 or not isinstance(created2, dict):
        raise LiveProcessError("HTTP client could not create secondary session")
    first = str(created1["session_id"])
    second = str(created2["session_id"])
    primary_messages = [message_for_session(item, first) for item in messages]
    secondary_message = message_for_session(messages[0], second)
    sent = copy.deepcopy(primary_messages[0])
    if mode == "rewritten_envelope":
        sent["sender"] = "agent:rewritten"
    ingest_path_session = second if mode == "wrong_session_path" else first
    idempotency = "wrong" if mode == "wrong_idempotency_key" else str(sent["message_id"])
    if mode == "invalid_idempotency_delimiter":
        idempotency = "prefix" + str(sent["message_id"])
    ingest_headers = {} if mode == "missing_idempotency_key" else {"Idempotency-Key": idempotency}
    ingest_status, _, ingest_body, _ = request(
        "POST",
        f"/aicp/v1/sessions/{ingest_path_session}/messages",
        bearer=bearer,
        body=sent,
        headers=ingest_headers,
    )
    replay_status, replay_headers, _, _ = request(
        "POST",
        f"/aicp/v1/sessions/{first}/messages",
        bearer=bearer,
        body=primary_messages[0],
        headers={"Idempotency-Key": str(primary_messages[0]["message_id"])},
    )
    secondary_status, secondary_headers, _, _ = request(
        "POST",
        f"/aicp/v1/sessions/{second}/messages",
        bearer=bearer,
        body=secondary_message,
        headers={"Idempotency-Key": str(secondary_message["message_id"])},
    )
    for message in primary_messages[1:]:
        request(
            "POST",
            f"/aicp/v1/sessions/{first}/messages",
            bearer=bearer,
            body=message,
            headers={"Idempotency-Key": str(message["message_id"])},
        )
    poll_status, _, poll_body, _ = request(
        "GET",
        f"/aicp/v1/sessions/{first}/messages?{urlencode({'after': 'c0', 'limit': 2})}",
        bearer=bearer,
    )
    poll_messages = list((poll_body or {}).get("messages", []))
    next_cursor = str((poll_body or {}).get("next_cursor", ""))
    head_status, _, head_body, _ = request("GET", f"/aicp/v1/sessions/{first}/head", bearer=bearer)
    ack_body = {"cursor": "wrong" if mode == "missing_ack" else next_cursor}
    ack_status, _, _, _ = request("POST", f"/aicp/v1/sessions/{first}/ack", bearer=bearer, body=ack_body)
    expired_status, _, expired_body, _ = request("GET", f"/aicp/v1/sessions/{first}/messages?after=expired&limit=2", bearer=bearer)
    overload_status, overload_headers, _, _ = request("GET", f"/aicp/v1/sessions/{first}/overload", bearer=bearer)
    sse_status = overload_sse_status = reconnect_status = churn_status = mismatch_status = 0
    sse_headers: dict[str, str] = {}
    sse_events: list[dict[str, Any]] = []
    overload_events: list[dict[str, Any]] = []
    reconnect_events: list[dict[str, Any]] = []
    churn_events: list[dict[str, Any]] = []
    sse_raw = overload_raw = reconnect_raw = churn_raw = b""
    final_cursor = ""
    if features.get("sse") is True:
        sse_status, sse_headers, sse_events, sse_raw = read_sse(base_url, f"/aicp/v1/sessions/{first}/messages/stream?after=c0&limit=3", bearer=bearer, capture=records)
        overload_sse_status, _, overload_events, overload_raw = read_sse(base_url, f"/aicp/v1/sessions/{first}/messages/stream?after=overload&limit=1", bearer=bearer, capture=records)
        final_cursor = str(sse_events[-1].get("id", "")) if sse_events else ""
        reconnect_after = "c0" if mode == "invalid_sse_reconnect" else final_cursor
        reconnect_status, _, reconnect_events, reconnect_raw = read_sse(
            base_url,
            f"/aicp/v1/sessions/{first}/messages/stream?after={final_cursor}&limit=2",
            bearer=bearer,
            last_event_id=reconnect_after,
            capture=records,
        )
        churn_status, _, churn_events, churn_raw = read_sse(
            base_url,
            f"/aicp/v1/sessions/{first}/messages/stream?after={final_cursor}&limit=2",
            bearer=bearer,
            last_event_id=reconnect_after,
            capture=records,
        )
        mismatch_status, _, _, _ = read_sse(
            base_url,
            f"/aicp/v1/sessions/{first}/messages/stream?after=c0&limit=1",
            bearer=bearer,
            last_event_id=final_cursor,
            capture=records,
        )
    ws_status = ws_overload_status = 0
    ws_frame: dict[str, Any] = {}
    ws_overload: dict[str, Any] = {}
    if features.get("websocket") is True:
        ws_after = "c1" if mode == "invalid_ws_pull" else "c0"
        parsed_base = urlsplit(validate_loopback_url(base_url))
        plain_ws_url = f"ws://{parsed_base.hostname}:{parsed_base.port}"
        ws_status, ws_frame = websocket_pull(plain_ws_url, f"/aicp/v1/sessions/{first}/messages/ws", bearer=bearer, after=ws_after, limit=2, capture=records)
        ws_overload_status, ws_overload = websocket_pull(plain_ws_url, f"/aicp/v1/sessions/{first}/messages/ws", bearer=bearer, after="overload", limit=1, capture=records)
    wss_status = wss_overload_status = 0
    wss_frame: dict[str, Any] = {}
    wss_overload: dict[str, Any] = {}
    if features.get("wss") is True:
        if not websocket_url or not websocket_url.startswith("wss://"):
            raise LiveProcessError("WSS was declared without an executable WSS endpoint")
        wss_status, wss_frame = websocket_pull(websocket_url, f"/aicp/v1/sessions/{first}/messages/ws", bearer=bearer, after="c0", limit=2, tls_ca_file=tls_ca_file, capture=records)
        wss_overload_status, wss_overload = websocket_pull(websocket_url, f"/aicp/v1/sessions/{first}/messages/ws", bearer=bearer, after="overload", limit=1, tls_ca_file=tls_ca_file, capture=records)
    close_status, _, _, _ = request("POST", f"/aicp/v1/sessions/{first}/close", bearer=bearer)
    closed_status, _, _, _ = request(
        "POST",
        f"/aicp/v1/sessions/{first}/messages",
        bearer=bearer,
        body=primary_messages[0],
        headers={"Idempotency-Key": str(primary_messages[0]["message_id"])},
    )

    delivered_sse = [message for event in sse_events if event.get("event") == "messages" for message in event.get("data", {}).get("messages", [])]
    more_flags = [event.get("data", {}).get("more") for event in sse_events if event.get("event") == "messages"]
    event_ids_valid = all(
        event.get("id") == event.get("data", {}).get("cursor_after_last")
        for event in sse_events
        if event.get("event") == "messages"
    )
    chain_valid = all(
        poll_messages[index].get("prev_msg_hash") == poll_messages[index - 1].get("message_hash")
        for index in range(1, len(poll_messages))
    )
    sse_chain_valid = all(
        delivered_sse[index].get("prev_msg_hash") == delivered_sse[index - 1].get("message_hash")
        for index in range(1, len(delivered_sse))
    )
    ws_messages = ws_frame.get("messages", []) if isinstance(ws_frame.get("messages"), list) else []
    ws_chain_valid = all(
        ws_messages[index].get("prev_msg_hash") == ws_messages[index - 1].get("message_hash")
        for index in range(1, len(ws_messages))
    )
    ws_cursor_relationship_valid = str(ws_frame.get("cursor_after_last", "")) == next_cursor
    interactions = [
        _interaction(role, "AUTH", "http", "authentication", {**boundary, "auth_present": status1 == 201, "auth_rejected": unauthorized_status in {401, 403}}),
        _interaction(role, "SESSION", "http", "session_lifecycle", {**boundary, "session_id": first, "second_session_id": second, "session_distinct": first != second and status1 == 201 and status2 == 201}),
        _interaction(role, "INGEST", "http", "message_ingest", {**boundary, "request_path_valid": ingest_path_session == first, "content_type_valid": True, "idempotency_key_valid": bool(ingest_headers) and idempotency.endswith(str(sent["message_id"])), "expected_message_id": str(primary_messages[0]["message_id"]), "observed_message_id": str((ingest_body or {}).get("message_id", "")), "expected_message_hash": str(primary_messages[0]["message_hash"]), "observed_message_hash": str((poll_messages[0] if poll_messages else {}).get("message_hash", "")), "message_digest_equal": bool(poll_messages) and canonical_digest(poll_messages[0]) == canonical_digest(primary_messages[0]) and ingest_status == 202}),
        _interaction(role, "REPLAY", "http", "idempotent_replay", {**boundary, "logical_accept_count": 1 if replay_status in {200, 208} else 2, "duplicate_count": 0 if replay_status in {200, 208} else 1, "replay_observed": replay_headers.get("aicp-replay") == "true"}),
        _interaction(role, "REPLAY-SCOPE", "http", "session_scoped_replay", {**boundary, "replay_scope_isolated": secondary_status == 202 and secondary_headers.get("aicp-replay") != "true"}),
        _interaction(role, "POLL", "http", "poll_messages", {**boundary, "session_id": first, "session_match": poll_status == 200 and all(item.get("session_id") == first for item in poll_messages), "poll_after": "c0", "poll_limit": 2, "delivered_count": len(poll_messages), "next_cursor": next_cursor, "no_cross_session_leakage": all(item.get("session_id") == first for item in poll_messages), "message_hashes_intact": [(item.get("message_id"), item.get("message_hash")) for item in poll_messages] == [(item.get("message_id"), item.get("message_hash")) for item in primary_messages[:len(poll_messages)]]}),
        _interaction(role, "HEAD", "http", "get_head", {**boundary, "session_id": first, "head_session_match": head_status == 200 and (head_body or {}).get("session_id") == first}),
        _interaction(role, "ACK", "http", "ack_cursor", {**boundary, "ack_cursor": str(ack_body["cursor"]), "ack_matches": ack_status == 204 and ack_body["cursor"] == next_cursor}),
        _interaction(role, "REPLAY-WINDOW", "http", "expired_cursor", {**boundary, "expired_cursor": "expired", "status": expired_status, "reason_code": str((expired_body or {}).get("reason_code", "")), "min_cursor": str((expired_body or {}).get("min_cursor", ""))}),
        _interaction(role, "ORDERING", "http", "ordered_delivery", {**boundary, "ordered_chain_valid": chain_valid}),
        _interaction(role, "OVERLOAD", "http", "overload", {**boundary, "status": overload_status, "retry_after_present": bool(overload_headers.get("retry-after")), "rate_limit_hint_present": any(key.startswith("ratelimit-") for key in overload_headers)}),
        _interaction(role, "SSE", "sse", "sse_pull", {**boundary, "live_bytes": bool(sse_raw) and bool(overload_raw), "status": sse_status if overload_sse_status == 200 else overload_sse_status, "sse_content_type_valid": "text/event-stream" in sse_headers.get("content-type", ""), "event_ids_match_cursors": event_ids_valid, "more_flags_valid": bool(more_flags) and more_flags[-1] is False and all(value is True for value in more_flags[:-1]), "poll_limit": 3, "delivered_count": len(delivered_sse), "ordered_chain_valid": sse_chain_valid, "overload_retry_present": any(bool(event.get("data", {}).get("retry_after")) for event in overload_events)}),
        _interaction(role, "SSE-RECONNECT", "sse", "sse_reconnect", {**boundary, "live_bytes": bool(reconnect_raw) and bool(churn_raw), "last_event_id": final_cursor, "last_event_relationship_valid": reconnect_status == 200 and all(event.get("id") == final_cursor for event in reconnect_events), "mismatched_resume_rejected": mismatch_status == 400, "reconnect_stable": reconnect_events == churn_events, "reconnect_churn_valid": churn_status == 200}),
        _interaction(role, "WEBSOCKET", "websocket", "websocket_pull", {**boundary, "live_frames": bool(ws_frame) and bool(ws_overload), "websocket_handshake_valid": ws_status == 101 and ws_overload_status == 101, "websocket_frame_shape_valid": ws_frame.get("type") == "messages" and isinstance(ws_frame.get("messages"), list) and isinstance(ws_frame.get("more"), bool), "cursor_after_last": str(ws_frame.get("cursor_after_last", "")), "cursor_relationship_valid": ws_cursor_relationship_valid, "more_flags_valid": ws_frame.get("more") is False, "poll_limit": 2, "delivered_count": len(ws_messages), "ordered_chain_valid": ws_chain_valid, "overload_retry_present": ws_overload.get("type") == "overload" and bool(ws_overload.get("retry_after"))}),
        _interaction(role, "WSS", "wss", "wss_pull", {**boundary, "live_frames": bool(wss_frame) and bool(wss_overload), "websocket_handshake_valid": wss_status == 101 and wss_overload_status == 101}),
        _interaction(role, "CLOSE", "http", "close_session", {**boundary, "closed_session_rejected": close_status == 204 and closed_status in {409, 410}}),
    ]
    if features.get("sse") is not True:
        interactions = [item for item in interactions if item["transport"] != "sse"]
    if features.get("websocket") is not True:
        interactions = [item for item in interactions if item["transport"] != "websocket"]
    if features.get("wss") is not True:
        interactions = [item for item in interactions if item["transport"] != "wss"]
    return attach_http_transport_evidence(interactions, records)


def interactions_from_capture(
    state: HttpLiveState,
    *,
    role: str,
    declared_features: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    records = list(state.records)
    sessions = list(state.sessions)
    auth_records = [item for item in records if item["path"] == "/aicp/v1/sessions"]
    ingests = [item for item in records if item["path"].endswith("/messages") and item["method"] == "POST"]
    polls = [item for item in records if item["path"].endswith("/messages") and item["method"] == "GET" and item["query"].get("after") == "c0"]
    heads = [item for item in records if item["path"].endswith("/head")]
    acks = [item for item in records if item["path"].endswith("/ack")]
    expired = [item for item in records if item["query"].get("after") == "expired"]
    overloads = [item for item in records if item["path"].endswith("/overload")]
    sse = [item for item in records if item["transport"] == "sse"]
    ws = [item for item in records if item["transport"] == "websocket"]
    closes = [item for item in records if item["path"].endswith("/close")]
    primary = sessions[0] if sessions else ""
    secondary = sessions[1] if len(sessions) > 1 else ""
    primary_messages = state.sessions.get(primary, {}).get("messages", [])
    first_expected = message_for_session(load_messages()[0], primary) if primary else {}
    first_ingest = next((item for item in ingests if item.get("status") == 202 and item.get("body", {}).get("session_id") == primary), {})
    replay_records = [item for item in ingests if item.get("body", {}).get("session_id") == primary and item.get("body", {}).get("message_id") == "m1"]
    secondary_records = [item for item in ingests if item.get("body", {}).get("session_id") == secondary and item.get("body", {}).get("message_id") == "m1"]
    poll = polls[0] if polls else {}
    poll_body = poll.get("response_body") or {}
    polled = poll_body.get("messages") or []
    head = heads[0] if heads else {}
    ack = acks[0] if acks else {}
    expiry = expired[0] if expired else {}
    overload = overloads[0] if overloads else {}
    sse_initial = next((item for item in sse if item["query"].get("after") == "c0" and "last-event-id" not in item["headers"]), {})
    sse_overload = next((item for item in sse if item["query"].get("after") == "overload"), {})
    sse_reconnects = [item for item in sse if "last-event-id" in item["headers"] and item["status"] == 200]
    sse_mismatch = next((item for item in records if item["transport"] == "http" and item["status"] == 400 and (item.get("response_body") or {}).get("reason_code") == "cursor_mismatch"), {})
    ws_messages = next((item for item in ws if (item.get("response_body") or {}).get("type") == "messages" or (item.get("body") or {}).get("after") != "overload"), {})
    ws_overload = next((item for item in ws if (item.get("body") or {}).get("after") == "overload"), {})
    chain_valid = all(
        primary_messages[index].get("prev_msg_hash") == primary_messages[index - 1].get("message_hash")
        for index in range(1, len(primary_messages))
    )
    events = (sse_initial.get("response_body") or {}).get("events") or []
    delivered_sse = [message for event in events if "messages" in event for message in event.get("messages", [])]
    sse_chain_valid = all(
        delivered_sse[index].get("prev_msg_hash") == delivered_sse[index - 1].get("message_hash")
        for index in range(1, len(delivered_sse))
    )
    captured_ws_messages = (ws_messages.get("response_body") or {}).get("messages", [])
    ws_chain_valid = all(
        captured_ws_messages[index].get("prev_msg_hash")
        == captured_ws_messages[index - 1].get("message_hash")
        for index in range(1, len(captured_ws_messages))
    )
    ws_cursor_relationship_valid = (
        (ws_messages.get("response_body") or {}).get("cursor_after_last")
        == poll_body.get("next_cursor")
    )
    event_cursor_count = sum(1 for record in sse if record.get("status") == 200)
    boundary = {"network_boundary": "loopback_socket"}
    interactions = [
        _interaction(role, "AUTH", "http", "authentication", {**boundary, "auth_present": any(item["status"] == 201 and "authorization" in item["headers"] for item in auth_records), "auth_rejected": any(item["status"] in {401, 403} and "authorization" not in item["headers"] for item in auth_records)}),
        _interaction(role, "SESSION", "http", "session_lifecycle", {**boundary, "session_id": primary, "second_session_id": secondary, "session_distinct": bool(primary and secondary and primary != secondary)}),
        _interaction(role, "INGEST", "http", "message_ingest", {**boundary, "request_path_valid": bool(first_ingest) and f"/{primary}/messages" in first_ingest.get("path", ""), "content_type_valid": "application/json" in first_ingest.get("headers", {}).get("content-type", ""), "idempotency_key_valid": first_ingest.get("headers", {}).get("idempotency-key", "").endswith("m1"), "expected_message_id": "m1", "observed_message_id": str(first_ingest.get("body", {}).get("message_id", "")), "expected_message_hash": str(first_expected.get("message_hash", "")), "observed_message_hash": str(first_ingest.get("body", {}).get("message_hash", "")), "message_digest_equal": bool(first_ingest) and canonical_digest(first_ingest.get("body")) == canonical_digest(first_expected)}),
        _interaction(role, "REPLAY", "http", "idempotent_replay", {**boundary, "logical_accept_count": 1 if len(state.sessions.get(primary, {}).get("message_ids", {})) >= 1 and any(item["status"] in {200, 208} for item in replay_records) else 2, "duplicate_count": max(0, len([item for item in primary_messages if item.get("message_id") == "m1"]) - 1), "replay_observed": any(item.get("response_headers", {}).get("aicp-replay") == "true" for item in replay_records)}),
        _interaction(role, "REPLAY-SCOPE", "http", "session_scoped_replay", {**boundary, "replay_scope_isolated": any(item["status"] == 202 and item.get("response_headers", {}).get("aicp-replay") != "true" for item in secondary_records)}),
        _interaction(role, "POLL", "http", "poll_messages", {**boundary, "session_id": primary, "session_match": bool(poll) and all(item.get("session_id") == primary for item in polled), "poll_after": str(poll.get("query", {}).get("after", "")), "poll_limit": int(poll.get("query", {}).get("limit", 0) or 0), "delivered_count": len(polled), "next_cursor": str(poll_body.get("next_cursor", "")), "no_cross_session_leakage": all(item.get("session_id") == primary for item in polled), "message_hashes_intact": [(item.get("message_id"), item.get("message_hash")) for item in polled] == [(item.get("message_id"), item.get("message_hash")) for item in primary_messages[:len(polled)]]}),
        _interaction(role, "HEAD", "http", "get_head", {**boundary, "session_id": primary, "head_session_match": head.get("status") == 200 and (head.get("response_body") or {}).get("session_id") == primary}),
        _interaction(role, "ACK", "http", "ack_cursor", {**boundary, "ack_cursor": str((ack.get("body") or {}).get("cursor", "")), "ack_matches": ack.get("status") == 204 and state.sessions.get(primary, {}).get("ack") == poll_body.get("next_cursor") and (ack.get("body") or {}).get("cursor") == poll_body.get("next_cursor")}),
        _interaction(role, "REPLAY-WINDOW", "http", "expired_cursor", {**boundary, "expired_cursor": "expired", "status": int(expiry.get("status", 0)), "reason_code": str((expiry.get("response_body") or {}).get("reason_code", "")), "min_cursor": str((expiry.get("response_body") or {}).get("min_cursor", ""))}),
        _interaction(role, "ORDERING", "http", "ordered_delivery", {**boundary, "ordered_chain_valid": chain_valid}),
        _interaction(role, "OVERLOAD", "http", "overload", {**boundary, "status": int(overload.get("status", 0)), "retry_after_present": bool(overload.get("response_headers", {}).get("retry-after")), "rate_limit_hint_present": any(key.startswith("ratelimit-") for key in overload.get("response_headers", {}))}),
        _interaction(role, "SSE", "sse", "sse_pull", {**boundary, "live_bytes": bool(sse_initial) and bool(sse_overload), "status": int(sse_initial.get("status", 0)), "sse_content_type_valid": "text/event-stream" in sse_initial.get("response_headers", {}).get("content-type", ""), "event_ids_match_cursors": all(event.get("cursor_after_last") for event in events if "messages" in event), "more_flags_valid": bool(events) and events[-1].get("more") is False, "poll_limit": int(sse_initial.get("query", {}).get("limit", 0) or 0), "delivered_count": len(delivered_sse), "ordered_chain_valid": sse_chain_valid, "overload_retry_present": any(bool(event.get("retry_after")) for event in (sse_overload.get("response_body") or {}).get("events", []))}),
        _interaction(role, "SSE-RECONNECT", "sse", "sse_reconnect", {**boundary, "live_bytes": event_cursor_count >= 3, "last_event_id": str(sse_reconnects[0].get("headers", {}).get("last-event-id", "")) if sse_reconnects else "", "last_event_relationship_valid": bool(sse_reconnects) and all(item.get("headers", {}).get("last-event-id") == item.get("query", {}).get("after") for item in sse_reconnects), "mismatched_resume_rejected": bool(sse_mismatch), "reconnect_stable": len(sse_reconnects) >= 2 and sse_reconnects[0].get("response_body") == sse_reconnects[1].get("response_body"), "reconnect_churn_valid": len(sse_reconnects) >= 2}),
        _interaction(role, "WEBSOCKET", "websocket", "websocket_pull", {**boundary, "live_frames": bool(ws_messages) and bool(ws_overload), "websocket_handshake_valid": ws_messages.get("status") == 101 and ws_overload.get("status") == 101, "websocket_frame_shape_valid": (ws_messages.get("response_body") or {}).get("type") == "messages" and isinstance((ws_messages.get("response_body") or {}).get("messages"), list), "cursor_after_last": str((ws_messages.get("response_body") or {}).get("cursor_after_last", "")), "cursor_relationship_valid": ws_cursor_relationship_valid, "more_flags_valid": (ws_messages.get("response_body") or {}).get("more") is False, "poll_limit": int((ws_messages.get("body") or {}).get("limit", 0)), "delivered_count": len(captured_ws_messages), "ordered_chain_valid": ws_chain_valid, "overload_retry_present": bool((ws_overload.get("response_body") or {}).get("retry_after"))}),
        _interaction(role, "CLOSE", "http", "close_session", {**boundary, "closed_session_rejected": bool(closes) and any(item["status"] in {409, 410} for item in ingests[len(primary_messages) + 2 :])}),
    ]
    features = declared_features or {"sse": True, "websocket": True}
    if features.get("sse") is not True:
        interactions = [item for item in interactions if item["transport"] != "sse"]
    if features.get("websocket") is not True:
        interactions = [item for item in interactions if item["transport"] != "websocket"]
    if features.get("wss") is True:
        interactions.insert(
            -1,
            _interaction(
                role,
                "WSS",
                "wss",
                "wss_pull",
                {"network_boundary": "loopback_socket"},
            ),
        )
    return attach_http_transport_evidence(interactions, records)
