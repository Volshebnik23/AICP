"""Bounded subprocess and exact-JSON relay support for Pairwise TCK 1.2."""

from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
from pathlib import Path
from typing import Any


MAX_LINE_BYTES = 1_048_576
MAX_STDERR_BYTES = 65_536
MAX_MESSAGES = 512
DEFAULT_TIMEOUT_SECONDS = 10.0
SAFE_ENV_NAMES = ("PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "TEMP", "TMP")
PAIRWISE_ENV_NAMES = (
    "AICP_PAIRWISE_READY_FILE",
    "AICP_PAIRWISE_SIDE",
    "AICP_PAIRWISE_ROLE",
    "AICP_PAIRWISE_TARGET",
)


class ProcessBoundaryError(RuntimeError):
    """A participant process violated the bounded test-infrastructure protocol."""


def allowlisted_environment(extra: dict[str, str] | None = None) -> dict[str, str]:
    result = {
        name: os.environ[name]
        for name in SAFE_ENV_NAMES
        if name in os.environ and isinstance(os.environ[name], str)
    }
    for name, value in (extra or {}).items():
        if name not in PAIRWISE_ENV_NAMES:
            raise ProcessBoundaryError(f"unsupported participant environment key: {name}")
        if not isinstance(value, str) or not value or len(value) > 4096:
            raise ProcessBoundaryError(f"invalid participant environment value: {name}")
        result[name] = value
    return result


def compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class JsonLineProcess:
    def __init__(
        self,
        command: list[str],
        *,
        cwd: Path,
        instance_id: str,
        environment: dict[str, str] | None = None,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
    ):
        if not command or not all(isinstance(item, str) and item for item in command):
            raise ProcessBoundaryError("command must be a non-empty string array")
        if len(command) > 32 or any(len(item) > 4096 for item in command):
            raise ProcessBoundaryError("command exceeds the bounded command-vector policy")
        if not isinstance(instance_id, str) or not instance_id:
            raise ProcessBoundaryError("process instance ID is required")
        self.command = tuple(command)
        self.instance_id = instance_id
        self.timeout = timeout
        self._count = 0
        self._stderr = bytearray()
        self.process = subprocess.Popen(
            command,
            cwd=str(cwd),
            env=allowlisted_environment(environment),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
            shell=False,
            bufsize=0,
        )
        assert self.process.stderr is not None
        self._stderr_thread = threading.Thread(target=self._collect_stderr, daemon=True)
        self._stderr_thread.start()

    def _collect_stderr(self) -> None:
        assert self.process.stderr is not None
        while True:
            chunk = self.process.stderr.read(4096)
            if not chunk:
                break
            remaining = MAX_STDERR_BYTES - len(self._stderr)
            if remaining > 0:
                self._stderr.extend(chunk[:remaining])

    @property
    def bounded_stderr(self) -> str:
        return bytes(self._stderr).decode("utf-8", errors="replace")

    def exchange(self, request: dict[str, Any]) -> dict[str, Any]:
        response, _ = self.exchange_json(compact_json(request))
        return response

    def exchange_json(self, request_json: str) -> tuple[dict[str, Any], str]:
        self._count += 1
        if self._count > MAX_MESSAGES:
            raise ProcessBoundaryError("process message-count bound exceeded")
        if not isinstance(request_json, str) or not request_json:
            raise ProcessBoundaryError("request JSON must be a non-empty string")
        encoded = (request_json + "\n").encode("utf-8")
        if len(encoded) > MAX_LINE_BYTES:
            raise ProcessBoundaryError("request line-size bound exceeded")
        try:
            request = json.loads(request_json)
        except json.JSONDecodeError as exc:
            raise ProcessBoundaryError("request JSON is malformed") from exc
        if not isinstance(request, dict):
            raise ProcessBoundaryError("request JSON must encode an object")
        if self.process.poll() is not None:
            raise ProcessBoundaryError(f"peer exited before request; code={self.process.returncode}")
        assert self.process.stdin is not None
        self.process.stdin.write(encoded)
        self.process.stdin.flush()
        raw = self._readline_with_timeout()
        if len(raw) > MAX_LINE_BYTES:
            raise ProcessBoundaryError("response line-size bound exceeded")
        try:
            response_json = raw.decode("utf-8", errors="strict").rstrip("\r\n")
            response = json.loads(response_json)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProcessBoundaryError("peer returned invalid UTF-8 JSON") from exc
        if not isinstance(response, dict):
            raise ProcessBoundaryError("peer response must be a JSON object")
        return response, response_json

    def _readline_with_timeout(self) -> bytes:
        assert self.process.stdout is not None
        result: queue.Queue[bytes | BaseException] = queue.Queue(maxsize=1)

        def read() -> None:
            try:
                result.put(self.process.stdout.readline(MAX_LINE_BYTES + 1))
            except BaseException as exc:  # pragma: no cover - OS pipe error
                result.put(exc)

        thread = threading.Thread(target=read, daemon=True)
        thread.start()
        try:
            item = result.get(timeout=self.timeout)
        except queue.Empty as exc:
            self.abort()
            raise ProcessBoundaryError("peer response timeout") from exc
        if isinstance(item, BaseException):
            raise ProcessBoundaryError(f"peer pipe failed: {item}") from item
        if not item:
            raise ProcessBoundaryError(
                f"peer closed stdout; code={self.process.poll()}; stderr={self.bounded_stderr!r}"
            )
        return item

    def close(self) -> None:
        if self.process.poll() is None and self.process.stdin is not None:
            self.process.stdin.close()
        try:
            self.process.wait(timeout=self.timeout)
        except subprocess.TimeoutExpired:
            self.abort()
            raise ProcessBoundaryError("peer did not exit after stdin closure")
        if self.process.returncode != 0:
            raise ProcessBoundaryError(
                f"peer exited with code {self.process.returncode}; stderr={self.bounded_stderr!r}"
            )

    def abort(self) -> None:
        if self.process.poll() is None:
            self.process.kill()
        try:
            self.process.wait(timeout=2.0)
        except subprocess.TimeoutExpired:  # pragma: no cover - kill should be terminal
            pass
