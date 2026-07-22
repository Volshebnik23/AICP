#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RUNNER_DIR = ROOT / "conformance/runner"
if str(RUNNER_DIR) not in sys.path:
    sys.path.insert(0, str(RUNNER_DIR))

from _runner_io import write_json_report  # noqa: E402
from _runner_provenance import canonical_content_digest, runner_source_revision, sha256_file  # noqa: E402
from _runner_context import build_validator, load_json  # noqa: E402


PROTOCOL_VERSION = "1.0"
CASES_PATH = ROOT / "conformance/iut/cases.json"
PUBLIC_KEYS_PATH = ROOT / "fixtures/keys/GT_public_keys.json"
REPORT_SCHEMA_PATH = ROOT / "conformance/iut/iut_report_schema.json"


class IUTProtocolError(RuntimeError):
    pass


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _request(request_id: str, operation: str, input_obj: dict[str, Any]) -> dict[str, Any]:
    return {
        "adapter_protocol_version": PROTOCOL_VERSION,
        "request_id": request_id,
        "operation": operation,
        "input": input_obj,
    }


def invoke_adapter(
    command: list[str],
    requests: list[dict[str, Any]],
    *,
    timeout_seconds: float,
    max_stdout_bytes: int,
    max_stderr_bytes: int,
) -> tuple[list[dict[str, Any]], str]:
    if not command or not all(isinstance(part, str) and part for part in command):
        raise IUTProtocolError("adapter command must be a non-empty argument vector")
    payload = "".join(json.dumps(item, separators=(",", ":"), ensure_ascii=False) + "\n" for item in requests).encode("utf-8")
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
    )
    stdout_chunks: list[bytes] = []
    stderr_chunks: list[bytes] = []
    overflow: list[str] = []

    def drain(stream: Any, sink: list[bytes], limit: int, label: str) -> None:
        total = 0
        while True:
            chunk = stream.read(4096)
            if not chunk:
                return
            total += len(chunk)
            if total > limit:
                overflow.append(label)
                process.kill()
                return
            sink.append(chunk)

    stdout_thread = threading.Thread(target=drain, args=(process.stdout, stdout_chunks, max_stdout_bytes, "stdout"), daemon=True)
    stderr_thread = threading.Thread(target=drain, args=(process.stderr, stderr_chunks, max_stderr_bytes, "stderr"), daemon=True)
    stdout_thread.start()
    stderr_thread.start()
    assert process.stdin is not None
    process.stdin.write(payload)
    process.stdin.close()
    try:
        return_code = process.wait(timeout=timeout_seconds)
    except subprocess.TimeoutExpired as exc:
        process.kill()
        process.wait()
        raise IUTProtocolError(f"adapter timed out after {timeout_seconds:g} seconds") from exc
    finally:
        stdout_thread.join(timeout=2)
        stderr_thread.join(timeout=2)

    if overflow:
        raise IUTProtocolError(f"adapter {overflow[0]} exceeded configured byte limit")
    stderr_text = b"".join(stderr_chunks).decode("utf-8", errors="replace")
    if return_code != 0:
        raise IUTProtocolError(f"adapter exited with code {return_code}; stderr={stderr_text[:500]}")
    try:
        stdout_text = b"".join(stdout_chunks).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise IUTProtocolError("adapter stdout is not valid UTF-8") from exc

    response_lines = [line for line in stdout_text.splitlines() if line.strip()]
    if len(response_lines) != len(requests):
        raise IUTProtocolError(f"adapter returned {len(response_lines)} responses for {len(requests)} requests")
    responses: list[dict[str, Any]] = []
    for index, (raw, request) in enumerate(zip(response_lines, requests), start=1):
        try:
            response = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise IUTProtocolError(f"response line {index} is not deterministic JSON: {exc}") from exc
        if not isinstance(response, dict):
            raise IUTProtocolError(f"response line {index} must be a JSON object")
        for field in ("adapter_protocol_version", "request_id", "operation", "success"):
            if field not in response:
                raise IUTProtocolError(f"response line {index} missing field {field}")
        if response["adapter_protocol_version"] != PROTOCOL_VERSION:
            raise IUTProtocolError(f"response line {index} has unsupported adapter protocol version")
        if response["request_id"] != request["request_id"] or response["operation"] != request["operation"]:
            raise IUTProtocolError(f"response line {index} correlation mismatch")
        if response["success"] is not True:
            raise IUTProtocolError(f"adapter operation {response['operation']} failed: {response.get('error')}")
        if not isinstance(response.get("result"), dict):
            raise IUTProtocolError(f"response line {index} result must be an object")
        responses.append(response)
    return responses, stderr_text


def _profile_parts(target: str) -> tuple[str, str]:
    if "@" not in target:
        raise ValueError("profile must be an exact ID/version such as AICP-BASE@0.1")
    return tuple(target.rsplit("@", 1))  # type: ignore[return-value]


def run_iut(
    command: list[str],
    profile: str,
    *,
    include_session_state_projection: bool = False,
    timeout_seconds: float = 20,
    max_stdout_bytes: int = 1_048_576,
    max_stderr_bytes: int = 262_144,
) -> dict[str, Any]:
    catalog = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    profile_config = catalog.get("profiles", {}).get(profile)
    if not isinstance(profile_config, dict):
        raise ValueError(f"unsupported IUT target profile: {profile}")
    public_keys = json.loads(PUBLIC_KEYS_PATH.read_text(encoding="utf-8"))
    vector_path = ROOT / catalog["canonicalization_vector"]
    vector = json.loads(vector_path.read_text(encoding="utf-8"))

    requests: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []
    requests.append(_request("describe-1", "describe", {}))
    checks.append({"kind": "describe_start"})
    requests.append(
        _request(
            "canonicalize-1",
            "canonicalize_hash",
            {"object_type": vector["object_type"], "object": vector["object"]},
        )
    )
    checks.append({"kind": "canonicalize", "case_id": vector["vector_id"], "expected": vector})

    producer = profile_config["producer_case"]
    requests.append(_request("generate-profile", "generate_case", {"case_id": producer["case_id"], "parameters": {"seed": 1}}))
    checks.append({"kind": "generate", **producer})
    for index, case in enumerate(profile_config["consumer_cases"], start=1):
        transcript = _load_jsonl(ROOT / case["fixture"])
        requests.append(
            _request(
                f"validate-profile-{index}",
                "validate_transcript",
                {"case_id": case["case_id"], "target": profile, "transcript": transcript, "public_keys": public_keys},
            )
        )
        checks.append({"kind": "validate", "target": profile, **case})

    if include_session_state_projection:
        state_config = catalog["session_state_projection"]
        state_producer = state_config["producer_case"]
        state_transcript = _load_jsonl(ROOT / state_producer["fixture"])
        state_response = state_transcript[-1]
        state = state_response["payload"]["session_state"]
        requests.append(_request("generate-state", "generate_case", {"case_id": state_producer["case_id"], "parameters": {"seed": 1}}))
        checks.append({"kind": "generate", **state_producer})
        requests.append(
            _request(
                "project-state",
                "project_session_state",
                {"transcript": state_transcript, "context": state},
            )
        )
        checks.append(
            {
                "kind": "project",
                "case_id": "SESSION-STATE-PROJECTION-V1-PRODUCER",
                "projection": state,
                "session_state_hash": state_response["payload"]["session_state_hash"],
            }
        )
        for index, case in enumerate(state_config["consumer_cases"], start=1):
            requests.append(
                _request(
                    f"validate-state-{index}",
                    "validate_transcript",
                    {"case_id": case["case_id"], "target": "SESSION-STATE-PROJECTION-V1", "transcript": _load_jsonl(ROOT / case["fixture"]), "public_keys": public_keys},
                )
            )
            checks.append({"kind": "validate", "target": "SESSION-STATE-PROJECTION-V1", **case})

    requests.append(_request("describe-2", "describe", {}))
    checks.append({"kind": "describe_end"})
    responses, stderr_text = invoke_adapter(
        command,
        requests,
        timeout_seconds=timeout_seconds,
        max_stdout_bytes=max_stdout_bytes,
        max_stderr_bytes=max_stderr_bytes,
    )

    failures: list[dict[str, str]] = []
    case_results: list[dict[str, Any]] = []
    generated_artifacts: list[dict[str, str]] = []
    degraded = False
    degraded_reasons: list[str] = []
    first_metadata: dict[str, Any] | None = None
    final_metadata: dict[str, Any] | None = None

    def record(case_id: str, passed: bool, message: str) -> None:
        case_results.append({"case_id": case_id, "passed": passed, "message": message})
        if not passed:
            failures.append({"test_id": case_id, "message": message})

    for response, check in zip(responses, checks):
        result = response["result"]
        kind = check["kind"]
        if kind == "describe_start":
            first_metadata = result
            required = ["implementation_kind", "implementation_id", "implementation_version", "implementation_digest", "supported_aicp_profiles", "supported_crypto_profiles", "adapter_protocol_version"]
            missing = [field for field in required if not result.get(field) and result.get(field) != []]
            record("IUT-DESCRIBE-01", not missing, "metadata complete" if not missing else f"missing implementation metadata: {missing}")
        elif kind == "describe_end":
            final_metadata = result
        elif kind == "canonicalize":
            expected = check["expected"]
            passed = result.get("canonical_json") == expected["canonical_json"] and result.get("object_hash") == expected["object_hash"]
            record(check["case_id"], passed, "canonical bytes/hash match" if passed else "canonical bytes or hash mismatch")
        elif kind == "generate":
            expected_artifact = _load_jsonl(ROOT / check["fixture"])
            actual_artifact = result.get("artifact")
            passed = canonical_content_digest(actual_artifact) == canonical_content_digest(expected_artifact)
            record(check["case_id"], passed, "generated artifact matches canonical case" if passed else "generated artifact digest mismatch")
            if actual_artifact is not None:
                generated_artifacts.append({"artifact_id": check["case_id"], "path": "", "content_digest": canonical_content_digest(actual_artifact)})
        elif kind == "project":
            passed = result.get("projection") == check["projection"] and result.get("session_state_hash") == check["session_state_hash"]
            record(check["case_id"], passed, "projection and hash match" if passed else "projection or projection hash mismatch")
            if isinstance(result.get("projection"), dict):
                generated_artifacts.append({"artifact_id": check["case_id"], "path": "", "content_digest": canonical_content_digest(result)})
        elif kind == "validate":
            if result.get("degraded"):
                degraded = True
                for reason in result.get("degraded_reasons", []) or []:
                    if isinstance(reason, str) and reason not in degraded_reasons:
                        degraded_reasons.append(reason)
            accepted = result.get("accepted")
            expected_accept = check["accepted"]
            errors = result.get("errors")
            passed = accepted is expected_accept and isinstance(errors, list)
            if expected_accept is False:
                passed = passed and bool(errors)
            else:
                passed = passed and not errors
            record(check["case_id"], passed, f"consumer accepted={accepted}, expected={expected_accept}")

    if first_metadata is None or final_metadata is None or first_metadata != final_metadata:
        record("IUT-DESCRIBE-STABILITY-01", False, "implementation metadata changed during execution")
    else:
        record("IUT-DESCRIBE-STABILITY-01", True, "implementation metadata stable")

    metadata = first_metadata or {}
    if profile not in (metadata.get("supported_aicp_profiles") or []):
        record("IUT-PROFILE-SUPPORT-01", False, f"adapter does not declare support for {profile}")
    if profile == "AICP-AUTHENTICATED-BASE@0.1" and "aicp.crypto.ed25519.v1" not in (metadata.get("supported_crypto_profiles") or []):
        record("IUT-CRYPTO-SUPPORT-01", False, "adapter does not declare aicp.crypto.ed25519.v1")
    if include_session_state_projection and "aicp.session_state_projection.v1" not in (metadata.get("supported_capabilities") or []):
        record("IUT-STATE-SUPPORT-01", False, "adapter does not declare strict state-projection capability")

    passed = not failures
    implementation_kind = metadata.get("implementation_kind")
    subject_kind = "external_implementation" if implementation_kind == "external_implementation" else "reference_corpus"
    profile_id, profile_version = _profile_parts(profile)
    profile_path = ROOT / profile_config["profile_catalog"]
    used_paths = {
        catalog["canonicalization_vector"],
        profile_config["profile_catalog"],
        producer["fixture"],
        "fixtures/keys/GT_public_keys.json",
    }
    used_paths.update(case["fixture"] for case in profile_config["consumer_cases"])
    if include_session_state_projection:
        state_config = catalog["session_state_projection"]
        used_paths.add(state_config["producer_case"]["fixture"])
        used_paths.update(case["fixture"] for case in state_config["consumer_cases"])
    input_artifacts = [
        {"artifact_id": Path(path).stem, "path": path, "content_digest": sha256_file(ROOT / path)}
        for path in sorted(used_paths)
    ]
    input_artifacts.insert(0, {"artifact_id": "AICP-IUT-TCK-CASES", "path": "conformance/iut/cases.json", "content_digest": sha256_file(CASES_PATH)})
    marks: list[str] = []
    eligible = passed and not degraded and subject_kind == "external_implementation"
    if eligible:
        marks.append(profile_config["expected_mark"])
        if include_session_state_projection:
            marks.append(catalog["session_state_projection"]["expected_mark"])

    return {
        "report_format_version": "1.0",
        "execution_subject": {
            "kind": subject_kind,
            "implementation_id": str(metadata.get("implementation_id", "unknown")),
            "implementation_version": str(metadata.get("implementation_version", "unknown")),
            "implementation_digest": str(metadata.get("implementation_digest", "unknown")),
        },
        "runner": {
            "name": "aicp-iut-runner",
            "version": "1.0",
            "source_revision": runner_source_revision([Path(__file__)]),
        },
        "suite": {"suite_id": catalog["suite_id"], "suite_version": catalog["suite_version"], "suite_digest": sha256_file(CASES_PATH)},
        "profile": {"profile_id": profile_id, "profile_version": profile_version, "profile_digest": sha256_file(profile_path)},
        "input_artifacts": input_artifacts,
        "generated_artifacts": generated_artifacts,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "case_results": case_results,
        "failures": failures,
        "degraded": degraded,
        "degraded_reasons": degraded_reasons,
        "skipped_checks": [],
        "compatibility_marks": marks,
        "adapter_stderr": stderr_text[:2000],
    }


def _parse_command(args: argparse.Namespace) -> list[str]:
    if args.cmd_json:
        value = json.loads(args.cmd_json)
        if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
            raise ValueError("--cmd-json must be a JSON array of non-empty strings")
        return value
    return shlex.split(args.cmd, posix=os.name != "nt")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run AICP conformance against an external JSONL IUT adapter")
    command_group = parser.add_mutually_exclusive_group(required=True)
    command_group.add_argument("--cmd", help="Adapter command parsed to argv; never passed to a shell")
    command_group.add_argument("--cmd-json", help="Adapter argv as a JSON string array")
    parser.add_argument("--profile", required=True, choices=["AICP-BASE@0.1", "AICP-AUTHENTICATED-BASE@0.1"])
    parser.add_argument("--include-session-state-projection", action="store_true")
    parser.add_argument("--timeout", type=float, default=20)
    parser.add_argument("--max-stdout-bytes", type=int, default=1_048_576)
    parser.add_argument("--max-stderr-bytes", type=int, default=262_144)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    try:
        report = run_iut(
            _parse_command(args),
            args.profile,
            include_session_state_projection=args.include_session_state_projection,
            timeout_seconds=args.timeout,
            max_stdout_bytes=args.max_stdout_bytes,
            max_stderr_bytes=args.max_stderr_bytes,
        )
    except Exception as exc:
        print(f"[FAIL] IUT protocol error: {exc}")
        return 1
    report_schema = load_json(REPORT_SCHEMA_PATH)
    report_validator = build_validator(report_schema, REPORT_SCHEMA_PATH)
    if report_validator is not None:
        report_validator.validate(report)
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    write_json_report(out_path, report)
    status = "PASSED" if report["passed"] else "FAILED"
    if report["degraded"]:
        status += " (DEGRADED)"
    print(f"IUT conformance {status}: {args.profile} -> {out_path}")
    for failure in report["failures"]:
        print(f" - [{failure['test_id']}] {failure['message']}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
