"""Bounded, shell-free JSON-lines subprocess support for the pairwise harness."""

from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
import time
from pathlib import Path
from typing import Any

MAX_LINE_BYTES = 1_048_576
MAX_STDERR_BYTES = 65_536
MAX_MESSAGES = 256
DEFAULT_TIMEOUT_SECONDS = 10.0
SAFE_ENV_NAMES = ("PATH", "PATHEXT", "SYSTEMROOT", "WINDIR", "TEMP", "TMP")


class ProcessBoundaryError(RuntimeError):
    """The external peer violated a bounded process boundary."""


def allowlisted_environment() -> dict[str, str]:
    return {
        name: os.environ[name]
        for name in SAFE_ENV_NAMES
        if name in os.environ and isinstance(os.environ[name], str)
    }


class JsonLineProcess:
    def __init__(self, command: list[str], *, cwd: Path, timeout: float = DEFAULT_TIMEOUT_SECONDS):
        if not command or not all(isinstance(item, str) and item for item in command):
            raise ProcessBoundaryError("command must be a non-empty string array")
        if len(command) > 32 or any(len(item) > 4096 for item in command):
            raise ProcessBoundaryError("command exceeds the bounded command-vector policy")
        self.command = tuple(command)
        self.timeout = timeout
        self._count = 0
        self._stderr = bytearray()
        self._stderr_done = threading.Event()
        self.process = subprocess.Popen(
            command,
            cwd=str(cwd),
            env=allowlisted_environment(),
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
        self._stderr_done.set()

    @property
    def bounded_stderr(self) -> str:
        return bytes(self._stderr).decode("utf-8", errors="replace")

    def exchange(self, request: dict[str, Any]) -> dict[str, Any]:
        self._count += 1
        if self._count > MAX_MESSAGES:
            raise ProcessBoundaryError("process message-count bound exceeded")
        encoded = (json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        if len(encoded) > MAX_LINE_BYTES:
            raise ProcessBoundaryError("request line-size bound exceeded")
        if self.process.poll() is not None:
            raise ProcessBoundaryError(f"peer exited before request; code={self.process.returncode}")
        assert self.process.stdin is not None
        self.process.stdin.write(encoded)
        self.process.stdin.flush()
        raw = self._readline_with_timeout()
        if len(raw) > MAX_LINE_BYTES:
            raise ProcessBoundaryError("response line-size bound exceeded")
        try:
            response = json.loads(raw.decode("utf-8", errors="strict"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ProcessBoundaryError("peer returned invalid UTF-8 JSON") from exc
        if not isinstance(response, dict):
            raise ProcessBoundaryError("peer response must be a JSON object")
        return response

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

    def __enter__(self) -> "JsonLineProcess":
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        if exc_type is None:
            self.close()
        else:
            self.abort()


def request_id(prefix: str, index: int) -> str:
    return f"{prefix}-{index}"
