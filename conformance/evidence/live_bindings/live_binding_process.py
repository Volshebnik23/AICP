from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, BinaryIO
from urllib.parse import urlsplit


MAX_READY_BYTES = 32_768
MAX_STDOUT_BYTES = 262_144
MAX_STDERR_BYTES = 262_144
MAX_MCP_LINE_BYTES = 1_048_576


class LiveProcessError(RuntimeError):
    """Fail-closed live implementation process or control error."""


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    encoded = (json.dumps(value, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(encoded)
    os.replace(temporary, path)


def validate_loopback_url(value: str) -> str:
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https", "ws", "wss"}:
        raise LiveProcessError("live endpoint scheme is not allowed")
    if parsed.hostname not in {"127.0.0.1", "::1"}:
        raise LiveProcessError("live endpoint must use a literal loopback address")
    if parsed.username is not None or parsed.password is not None:
        raise LiveProcessError("live endpoint userinfo is forbidden")
    if parsed.query or parsed.fragment:
        raise LiveProcessError("live endpoint descriptor must not contain query or fragment")
    try:
        port = parsed.port
    except ValueError as exc:
        raise LiveProcessError("live endpoint port is invalid") from exc
    if port is None or port < 1 or port > 65535:
        raise LiveProcessError("live endpoint must include a bounded port")
    if parsed.path not in {"", "/"}:
        raise LiveProcessError("live endpoint descriptor base URL must not contain a path")
    return value.rstrip("/")


def explicit_environment(values: dict[str, str]) -> dict[str, str]:
    # Runtime discovery variables are retained so an independently installed
    # executable can start; only AICP_LIVE_* test-control values are added.
    environment = os.environ.copy()
    for key in list(environment):
        if key.startswith("AICP_LIVE_"):
            environment.pop(key, None)
    environment.update(values)
    return environment


class BoundedCollector:
    def __init__(self, stream: BinaryIO, limit: int, label: str) -> None:
        self._stream = stream
        self._limit = limit
        self._label = label
        self._chunks: list[bytes] = []
        self._overflow = False
        self._thread = threading.Thread(target=self._drain, name=f"aicp-live-{label}", daemon=True)

    def _drain(self) -> None:
        total = 0
        try:
            while True:
                chunk = self._stream.read(4096)
                if not chunk:
                    return
                total += len(chunk)
                if total > self._limit:
                    self._overflow = True
                    return
                self._chunks.append(chunk)
        except (OSError, ValueError):
            return

    def start(self) -> None:
        self._thread.start()

    def finish(self) -> str:
        self._thread.join(timeout=2)
        if self._overflow:
            raise LiveProcessError(f"live process {self._label} exceeded configured byte limit")
        return b"".join(self._chunks).decode("utf-8", errors="replace")


def spawn_process(
    command: list[str],
    *,
    environment: dict[str, str],
    root: Path,
    stdout_transport: bool = False,
) -> tuple[subprocess.Popen[bytes], BoundedCollector | None, BoundedCollector]:
    if not command or not all(isinstance(part, str) and part for part in command):
        raise LiveProcessError("live command must be a non-empty argument vector")
    try:
        process = subprocess.Popen(
            command,
            cwd=root,
            env=environment,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
        )
    except OSError as exc:
        raise LiveProcessError(f"live process creation failed: {exc}") from exc
    assert process.stdout is not None and process.stderr is not None
    stdout_collector = None
    if not stdout_transport:
        stdout_collector = BoundedCollector(process.stdout, MAX_STDOUT_BYTES, "stdout")
        stdout_collector.start()
    stderr_collector = BoundedCollector(process.stderr, MAX_STDERR_BYTES, "stderr")
    stderr_collector.start()
    return process, stdout_collector, stderr_collector


def wait_ready_descriptor(
    process: subprocess.Popen[bytes],
    ready_path: Path,
    *,
    deadline: float,
) -> dict[str, Any]:
    while time.monotonic() < deadline:
        if ready_path.is_file():
            data = ready_path.read_bytes()
            if len(data) > MAX_READY_BYTES:
                raise LiveProcessError("live ready descriptor exceeded byte limit")
            try:
                value = json.loads(data.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise LiveProcessError("live ready descriptor is not valid UTF-8 JSON") from exc
            if not isinstance(value, dict):
                raise LiveProcessError("live ready descriptor must be an object")
            return value
        if process.poll() is not None:
            raise LiveProcessError(f"live process exited before readiness with code {process.returncode}")
        time.sleep(0.01)
    raise LiveProcessError("live ready descriptor timed out")


def terminate_and_reap(process: subprocess.Popen[bytes], *, deadline_seconds: float = 2.0) -> None:
    if process.poll() is None:
        try:
            process.terminate()
        except OSError:
            pass
    try:
        process.wait(timeout=deadline_seconds)
    except subprocess.TimeoutExpired:
        try:
            process.kill()
        except OSError:
            pass
        try:
            process.wait(timeout=deadline_seconds)
        except subprocess.TimeoutExpired as exc:  # pragma: no cover - platform failure
            raise LiveProcessError("live child process could not be reaped") from exc


def read_bounded_line(
    stream: BinaryIO,
    *,
    deadline: float,
    limit: int = MAX_MCP_LINE_BYTES,
) -> bytes:
    result: queue.Queue[bytes | BaseException] = queue.Queue(maxsize=1)

    def read() -> None:
        try:
            result.put(stream.readline(limit + 1))
        except BaseException as exc:  # pragma: no cover - OS pipe failure
            result.put(exc)

    thread = threading.Thread(target=read, name="aicp-live-readline", daemon=True)
    thread.start()
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise LiveProcessError("live phase deadline expired")
    try:
        value = result.get(timeout=remaining)
    except queue.Empty as exc:
        raise LiveProcessError("live transport timed out waiting for a line") from exc
    if isinstance(value, BaseException):
        raise LiveProcessError(f"live transport read failed: {value}") from value
    if len(value) > limit:
        raise LiveProcessError("live transport line exceeded byte limit")
    if not value:
        raise LiveProcessError("live transport closed before a complete response")
    return value


def write_json_line(stream: BinaryIO, value: dict[str, Any]) -> None:
    encoded = (json.dumps(value, separators=(",", ":"), ensure_ascii=False) + "\n").encode("utf-8")
    if len(encoded) > MAX_MCP_LINE_BYTES:
        raise LiveProcessError("live JSON-RPC request exceeded line limit")
    try:
        stream.write(encoded)
        stream.flush()
    except (BrokenPipeError, OSError, ValueError) as exc:
        raise LiveProcessError("live transport closed while writing") from exc


def parse_json_line(raw: bytes) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except UnicodeDecodeError as exc:
        raise LiveProcessError("live transport response is not valid UTF-8") from exc
    except json.JSONDecodeError as exc:
        raise LiveProcessError("live transport response is malformed JSON") from exc
    if not isinstance(value, dict):
        raise LiveProcessError("live transport response must be a JSON object")
    return value
