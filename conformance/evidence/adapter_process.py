from __future__ import annotations

import json
import subprocess
import threading
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
PROTOCOL_VERSION = "1.1"


class AdapterProcessError(RuntimeError):
    """Deterministic evidence-adapter process or protocol failure."""


def _kill_and_reap(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is None:
        try:
            process.kill()
        except OSError:
            pass
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired as exc:  # pragma: no cover
        raise AdapterProcessError(
            "adapter could not be reaped after termination"
        ) from exc


def invoke_adapter(
    command: list[str],
    requests: list[dict[str, Any]],
    *,
    timeout_seconds: float,
    max_stdout_bytes: int,
    max_stderr_bytes: int,
) -> tuple[list[dict[str, Any]], str]:
    if not command or not all(isinstance(part, str) and part for part in command):
        raise AdapterProcessError(
            "adapter command must be a non-empty argument vector"
        )
    if timeout_seconds <= 0:
        raise AdapterProcessError("adapter timeout must be positive")
    if max_stdout_bytes <= 0 or max_stderr_bytes <= 0:
        raise AdapterProcessError("adapter output limits must be positive")

    payload = "".join(
        json.dumps(item, separators=(",", ":"), ensure_ascii=False) + "\n"
        for item in requests
    ).encode("utf-8")
    deadline = time.monotonic() + timeout_seconds
    try:
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
        )
    except OSError as exc:
        raise AdapterProcessError(
            f"adapter process creation failed: {exc}"
        ) from exc

    assert (
        process.stdin is not None
        and process.stdout is not None
        and process.stderr is not None
    )
    stdout_chunks: list[bytes] = []
    stderr_chunks: list[bytes] = []
    overflow: list[str] = []
    writer_errors: list[str] = []

    def write_payload() -> None:
        try:
            for offset in range(0, len(payload), 65536):
                process.stdin.write(payload[offset : offset + 65536])
                process.stdin.flush()
        except (BrokenPipeError, OSError, ValueError) as exc:
            writer_errors.append(type(exc).__name__)
        finally:
            try:
                process.stdin.close()
            except OSError:
                pass

    def drain(
        stream: Any,
        sink: list[bytes],
        limit: int,
        label: str,
    ) -> None:
        total = 0
        try:
            while True:
                chunk = stream.read(4096)
                if not chunk:
                    return
                total += len(chunk)
                if total > limit:
                    if not overflow:
                        overflow.append(label)
                    try:
                        process.kill()
                    except OSError:
                        pass
                    return
                sink.append(chunk)
        except (OSError, ValueError):
            return

    threads = [
        threading.Thread(
            target=write_payload,
            name="aicp-evidence-stdin",
            daemon=True,
        ),
        threading.Thread(
            target=drain,
            args=(
                process.stdout,
                stdout_chunks,
                max_stdout_bytes,
                "stdout",
            ),
            name="aicp-evidence-stdout",
            daemon=True,
        ),
        threading.Thread(
            target=drain,
            args=(
                process.stderr,
                stderr_chunks,
                max_stderr_bytes,
                "stderr",
            ),
            name="aicp-evidence-stderr",
            daemon=True,
        ),
    ]
    for thread in threads:
        thread.start()

    timed_out = False
    while process.poll() is None:
        if overflow:
            break
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            timed_out = True
            break
        try:
            process.wait(timeout=min(remaining, 0.05))
        except subprocess.TimeoutExpired:
            continue

    if timed_out or overflow:
        _kill_and_reap(process)
    else:
        process.wait()
    for stream in (process.stdout, process.stderr):
        try:
            stream.close()
        except OSError:
            pass
    for thread in threads:
        thread.join(timeout=1)

    if overflow:
        raise AdapterProcessError(
            f"adapter {overflow[0]} exceeded configured byte limit"
        )
    if timed_out:
        raise AdapterProcessError(
            f"adapter timed out after {timeout_seconds:g} seconds"
        )

    stderr_text = b"".join(stderr_chunks).decode("utf-8", errors="replace")
    if writer_errors:
        raise AdapterProcessError(
            "adapter exited before consuming complete input"
        )
    if process.returncode != 0:
        raise AdapterProcessError(
            f"adapter exited with code {process.returncode}; "
            f"stderr={stderr_text[:500]}"
        )
    try:
        stdout_text = b"".join(stdout_chunks).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise AdapterProcessError(
            "adapter stdout is not valid UTF-8"
        ) from exc

    response_lines = [
        line for line in stdout_text.splitlines() if line.strip()
    ]
    if len(response_lines) != len(requests):
        raise AdapterProcessError(
            f"adapter returned {len(response_lines)} responses for "
            f"{len(requests)} requests"
        )
    responses: list[dict[str, Any]] = []
    for index, (raw, request) in enumerate(
        zip(response_lines, requests),
        start=1,
    ):
        try:
            response = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise AdapterProcessError(
                f"response line {index} is not deterministic JSON: {exc}"
            ) from exc
        if not isinstance(response, dict):
            raise AdapterProcessError(
                f"response line {index} must be a JSON object"
            )
        for field in (
            "adapter_protocol_version",
            "request_id",
            "operation",
            "success",
        ):
            if field not in response:
                raise AdapterProcessError(
                    f"response line {index} missing field {field}"
                )
        if response["adapter_protocol_version"] != PROTOCOL_VERSION:
            raise AdapterProcessError(
                f"response line {index} has unsupported adapter protocol version"
            )
        if (
            response["request_id"] != request["request_id"]
            or response["operation"] != request["operation"]
        ):
            raise AdapterProcessError(
                f"response line {index} correlation mismatch"
            )
        if response["success"] is not True:
            raise AdapterProcessError(
                f"adapter operation {response['operation']} failed: "
                f"{response.get('error')}"
            )
        if not isinstance(response.get("result"), dict):
            raise AdapterProcessError(
                f"response line {index} result must be an object"
            )
        responses.append(response)
    return responses, stderr_text
