#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import threading
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RUNNER_DIR = ROOT / "conformance/runner"
IUT_DIR = ROOT / "conformance/iut"
for path in (RUNNER_DIR, IUT_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from _iut_evaluator import validate_generated_artifact  # noqa: E402
from _runner_context import build_validator, load_json  # noqa: E402
from _runner_io import write_json_report  # noqa: E402
from _runner_provenance import canonical_content_digest, sha256_file  # noqa: E402
from aicp_iut_catalog import (  # noqa: E402
    CASES_PATH,
    PUBLIC_KEYS_REF,
    TCK_RELEASES_PATH,
    bundle_digest,
    load_tck_release,
    mandatory_case_ids,
    normalized_file_digest,
    profile_config,
    required_input_paths,
    runner_bundle_paths,
    selected_cases,
    validate_catalog_coverage,
)


PROTOCOL_VERSION = "1.1"
REPORT_SCHEMA_PATH = ROOT / "conformance/iut/iut_report_v1.schema.json"


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


def _kill_and_reap(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is None:
        try:
            process.kill()
        except OSError:
            pass
    try:
        process.wait(timeout=2)
    except subprocess.TimeoutExpired as exc:  # pragma: no cover - kill should be terminal
        raise IUTProtocolError("adapter could not be reaped after termination") from exc


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
    if timeout_seconds <= 0:
        raise IUTProtocolError("adapter timeout must be positive")
    if max_stdout_bytes <= 0 or max_stderr_bytes <= 0:
        raise IUTProtocolError("adapter output limits must be positive")

    payload = "".join(
        json.dumps(item, separators=(",", ":"), ensure_ascii=False) + "\n" for item in requests
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
        raise IUTProtocolError(f"adapter process creation failed: {exc}") from exc

    assert process.stdin is not None and process.stdout is not None and process.stderr is not None
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

    def drain(stream: Any, sink: list[bytes], limit: int, label: str) -> None:
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
        threading.Thread(target=write_payload, name="aicp-iut-stdin", daemon=True),
        threading.Thread(
            target=drain,
            args=(process.stdout, stdout_chunks, max_stdout_bytes, "stdout"),
            name="aicp-iut-stdout",
            daemon=True,
        ),
        threading.Thread(
            target=drain,
            args=(process.stderr, stderr_chunks, max_stderr_bytes, "stderr"),
            name="aicp-iut-stderr",
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
        raise IUTProtocolError(f"adapter {overflow[0]} exceeded configured byte limit")
    if timed_out:
        raise IUTProtocolError(f"adapter timed out after {timeout_seconds:g} seconds")

    stderr_text = b"".join(stderr_chunks).decode("utf-8", errors="replace")
    return_code = process.returncode
    if writer_errors:
        raise IUTProtocolError("adapter exited before consuming complete input")
    if return_code != 0:
        raise IUTProtocolError(f"adapter exited with code {return_code}; stderr={stderr_text[:500]}")
    try:
        stdout_text = b"".join(stdout_chunks).decode("utf-8")
    except UnicodeDecodeError as exc:
        raise IUTProtocolError("adapter stdout is not valid UTF-8") from exc

    response_lines = [line for line in stdout_text.splitlines() if line.strip()]
    if len(response_lines) != len(requests):
        raise IUTProtocolError(
            f"adapter returned {len(response_lines)} responses for {len(requests)} requests"
        )
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
            raise IUTProtocolError(
                f"adapter operation {response['operation']} failed: {response.get('error')}"
            )
        if not isinstance(response.get("result"), dict):
            raise IUTProtocolError(f"response line {index} result must be an object")
        responses.append(response)
    return responses, stderr_text


def _profile_parts(target: str) -> tuple[str, str]:
    if "@" not in target:
        raise ValueError("profile must be an exact ID/version such as AICP-BASE@0.1")
    return tuple(target.rsplit("@", 1))  # type: ignore[return-value]


def build_execution_plan(
    profile: str,
    mode: str,
    *,
    include_session_state_projection: bool = False,
) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    catalog = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    config = profile_config(catalog, profile)
    producers, consumers = selected_cases(catalog, profile, mode)
    public_keys = json.loads((ROOT / PUBLIC_KEYS_REF).read_text(encoding="utf-8"))
    requests: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []
    counter = 0

    def append(operation: str, input_obj: dict[str, Any], check: dict[str, Any]) -> None:
        nonlocal counter
        counter += 1
        requests.append(_request(f"challenge-{counter:06d}", operation, input_obj))
        checks.append(check)

    append("describe", {}, {"kind": "describe_start"})
    for vector_ref in catalog["canonicalization_vectors"]:
        vector = json.loads((ROOT / vector_ref).read_text(encoding="utf-8"))
        append(
            "canonicalize_hash",
            {"object_type": vector["object_type"], "object": vector["object"]},
            {"kind": "canonicalize", "case_id": vector["vector_id"], "expected": vector},
        )
    for producer in producers:
        append(
            "generate_scenario",
            {"target_profile": profile, "scenario": producer["scenario"]},
            {"kind": "generate", "required_suites": config["required_suites"], **producer},
        )
    for case in consumers:
        append(
            "validate_transcript",
            {
                "target_profile": profile,
                "transcript": _load_jsonl(ROOT / case["fixture"]),
                "public_verification_material": public_keys,
                "runtime_options": case.get("runtime_options", {}),
            },
            {"kind": "validate", **case},
        )

    if include_session_state_projection:
        state = catalog["session_state_projection"]
        state_transcript = _load_jsonl(ROOT / state["producer_case"]["fixture"])
        state_response = state_transcript[-1]
        append(
            "project_session_state",
            {
                "transcript": state_transcript,
                "context": state_response["payload"]["session_state"],
            },
            {
                "kind": "project",
                "case_id": state["producer_case"]["case_id"],
                "projection": state_response["payload"]["session_state"],
                "session_state_hash": state_response["payload"]["session_state_hash"],
            },
        )
        for case in state["consumer_cases"]:
            append(
                "validate_transcript",
                {
                    "target_profile": "aicp.session_state_projection.v1",
                    "transcript": _load_jsonl(ROOT / case["fixture"]),
                    "public_verification_material": public_keys,
                    "runtime_options": {},
                },
                {"kind": "validate", **case},
            )
    append("describe", {}, {"kind": "describe_end"})
    return catalog, requests, checks


def run_iut(
    command: list[str],
    profile: str,
    *,
    mode: str,
    include_session_state_projection: bool = False,
    timeout_seconds: float = 20,
    max_stdout_bytes: int = 8_388_608,
    max_stderr_bytes: int = 262_144,
) -> dict[str, Any]:
    catalog, requests, checks = build_execution_plan(
        profile,
        mode,
        include_session_state_projection=include_session_state_projection,
    )
    config = profile_config(catalog, profile)
    catalog_errors = validate_catalog_coverage(catalog, profile)
    release = load_tck_release(catalog)
    expected_bundle_digest = bundle_digest(runner_bundle_paths())
    release_bundle_digest = release.get("runner_bundle", {}).get("digest")
    if release_bundle_digest != expected_bundle_digest:
        catalog_errors.append("registered TCK runner bundle digest does not match the working tree")

    responses, stderr_text = invoke_adapter(
        command,
        requests,
        timeout_seconds=timeout_seconds,
        max_stdout_bytes=max_stdout_bytes,
        max_stderr_bytes=max_stderr_bytes,
    )
    failures: list[dict[str, str]] = []
    case_results: list[dict[str, Any]] = []
    generated_artifacts: list[dict[str, Any]] = []
    degraded = False
    degraded_reasons: list[str] = []
    skipped_checks: list[str] = []
    first_metadata: dict[str, Any] | None = None
    final_metadata: dict[str, Any] | None = None

    def record(case_id: str, passed: bool, message: str) -> None:
        case_results.append({"case_id": case_id, "passed": passed, "message": message})
        if not passed:
            failures.append({"test_id": case_id, "message": message})

    record(
        "IUT-CATALOG-COVERAGE-01",
        not catalog_errors,
        "full-profile catalog covers every required suite case and positive Core producer type"
        if not catalog_errors
        else "; ".join(catalog_errors),
    )

    for response, check in zip(responses, checks):
        result = response["result"]
        kind = check["kind"]
        if kind == "describe_start":
            first_metadata = result
            required = [
                "implementation_kind",
                "implementation_id",
                "implementation_version",
                "implementation_digest",
                "supported_aicp_profiles",
                "supported_crypto_profiles",
                "adapter_protocol_version",
            ]
            missing = [field for field in required if not result.get(field) and result.get(field) != []]
            valid_kind = result.get("implementation_kind") in {
                "reference_corpus",
                "external_implementation",
            }
            passed = not missing and valid_kind
            message = "metadata complete" if passed else f"missing/invalid implementation metadata: {missing}"
            record("IUT-DESCRIBE-01", passed, message)
        elif kind == "describe_end":
            final_metadata = result
        elif kind == "canonicalize":
            expected = check["expected"]
            passed = (
                result.get("canonical_json") == expected["canonical_json"]
                and result.get("object_hash") == expected["object_hash"]
            )
            record(
                check["case_id"],
                passed,
                "canonical bytes/hash match" if passed else "canonical bytes or hash mismatch",
            )
        elif kind == "generate":
            artifact = result.get("artifact")
            generation_errors = validate_generated_artifact(
                artifact,
                check["scenario"],
                check["required_suites"],
            )
            passed = not generation_errors
            record(
                check["case_id"],
                passed,
                "generated transcript satisfies the neutral scenario and required suites"
                if passed
                else "; ".join(generation_errors),
            )
            if artifact is not None:
                generated_artifacts.append(
                    {
                        "artifact_id": check["case_id"],
                        "content_digest": canonical_content_digest(artifact),
                        "content": artifact,
                    }
                )
        elif kind == "project":
            projection_ok = result.get("projection") == check["projection"]
            hash_ok = result.get("session_state_hash") == check["session_state_hash"]
            record(
                check["case_id"],
                projection_ok,
                "projection matches the requested externally portable state"
                if projection_ok
                else "projection mismatch",
            )
            record(
                "SESSION-STATE-PROJECTION-V1-HASH",
                hash_ok,
                "projection hash matches" if hash_ok else "projection hash mismatch",
            )
            if isinstance(result.get("projection"), dict):
                generated_artifacts.append(
                    {
                        "artifact_id": check["case_id"],
                        "content_digest": canonical_content_digest(result),
                        "content": result,
                    }
                )
        elif kind == "validate":
            accepted = result.get("accepted")
            errors = result.get("errors")
            response_degraded = result.get("degraded") is True
            expected_degraded = check.get("expected_degraded") is True
            passed = accepted is check["accepted"] and isinstance(errors, list)
            passed = passed and (not errors if check["accepted"] else bool(errors))
            if expected_degraded:
                passed = passed and response_degraded and bool(result.get("degraded_reasons"))
            elif response_degraded:
                passed = False
                degraded = True
                for reason in result.get("degraded_reasons", []) or []:
                    if isinstance(reason, str) and reason not in degraded_reasons:
                        degraded_reasons.append(reason)
                for check_id in result.get("skipped_checks", []) or []:
                    if isinstance(check_id, str) and check_id not in skipped_checks:
                        skipped_checks.append(check_id)
            record(
                check["case_id"],
                passed,
                f"consumer accepted={accepted}; expected={check['accepted']}; "
                f"degraded={response_degraded}; expected_degraded={expected_degraded}",
            )

    if first_metadata is None or final_metadata is None or first_metadata != final_metadata:
        record("IUT-DESCRIBE-STABILITY-01", False, "implementation metadata changed during execution")
    else:
        record("IUT-DESCRIBE-STABILITY-01", True, "implementation metadata stable")

    metadata = first_metadata or {}
    if profile not in (metadata.get("supported_aicp_profiles") or []):
        record("IUT-PROFILE-SUPPORT-01", False, f"adapter does not declare support for {profile}")
    else:
        record("IUT-PROFILE-SUPPORT-01", True, f"adapter declares support for {profile}")
    if profile == "AICP-AUTHENTICATED-BASE@0.1":
        crypto_ok = "aicp.crypto.ed25519.v1" in (metadata.get("supported_crypto_profiles") or [])
        record(
            "IUT-CRYPTO-SUPPORT-01",
            crypto_ok,
            "adapter declares aicp.crypto.ed25519.v1"
            if crypto_ok
            else "adapter does not declare aicp.crypto.ed25519.v1",
        )
    if include_session_state_projection:
        state_ok = "aicp.session_state_projection.v1" in (metadata.get("supported_capabilities") or [])
        record(
            "IUT-STATE-SUPPORT-01",
            state_ok,
            "adapter declares strict state-projection capability"
            if state_ok
            else "adapter does not declare strict state-projection capability",
        )

    expected_ids = mandatory_case_ids(
        catalog,
        profile,
        mode,
        include_session_state_projection=include_session_state_projection,
    )
    observed_counts = Counter(item["case_id"] for item in case_results)
    expected_counts = Counter(expected_ids)
    coverage_ok = observed_counts == expected_counts
    if not coverage_ok:
        coverage_result = next(
            item for item in case_results if item["case_id"] == "IUT-CATALOG-COVERAGE-01"
        )
        coverage_result["passed"] = False
        coverage_result["message"] += "; executed mandatory case set is incomplete or duplicated"
        failures.append(
            {
                "test_id": "IUT-CATALOG-COVERAGE-01",
                "message": "executed mandatory case set is incomplete or duplicated",
            }
        )

    passed = not failures
    subject_kind = metadata.get("implementation_kind")
    if subject_kind not in {"reference_corpus", "external_implementation"}:
        subject_kind = "reference_corpus"
    profile_id, profile_version = _profile_parts(profile)
    profile_path = ROOT / config["profile_catalog"]
    input_paths = required_input_paths(catalog, profile)
    input_artifacts = [
        {
            "artifact_id": Path(path).stem,
            "path": path,
            "content_digest": normalized_file_digest(ROOT / path),
        }
        for path in input_paths
    ]
    suite_provenance = []
    for suite_ref in config["required_suites"]:
        suite_catalog = json.loads((ROOT / suite_ref).read_text(encoding="utf-8"))
        suite_provenance.append(
            {
                "suite_id": suite_catalog["suite_id"],
                "suite_version": suite_catalog["suite_version"],
                "suite_digest": normalized_file_digest(ROOT / suite_ref),
            }
        )

    marks: list[str] = []
    eligible = (
        mode == "full-profile"
        and passed
        and not degraded
        and not skipped_checks
        and coverage_ok
        and subject_kind == "external_implementation"
        and release_bundle_digest == expected_bundle_digest
    )
    if eligible:
        marks = [config["expected_mark"]]

    return {
        "report_format_version": "1.0",
        "report_type": "aicp.external_iut",
        "execution_mode": mode,
        "execution_subject": {
            "kind": subject_kind,
            "implementation_id": str(metadata.get("implementation_id", "unknown")),
            "implementation_version": str(metadata.get("implementation_version", "unknown")),
            "implementation_digest": str(metadata.get("implementation_digest", "unknown")),
        },
        "runner": {
            "name": "aicp-iut-runner",
            "version": "1.0",
            "source_revision": expected_bundle_digest,
        },
        "tck_release": {
            "release_id": catalog["tck_release_id"],
            "registry_digest": sha256_file(TCK_RELEASES_PATH),
            "runner_bundle_digest": expected_bundle_digest,
            "case_catalog_digest": sha256_file(CASES_PATH),
        },
        "suite": {
            "suite_id": catalog["suite_id"],
            "suite_version": catalog["suite_version"],
            "suite_digest": sha256_file(CASES_PATH),
        },
        "required_suites": suite_provenance,
        "profile": {
            "profile_id": profile_id,
            "profile_version": profile_version,
            "profile_digest": sha256_file(profile_path),
        },
        "input_artifacts": input_artifacts,
        "generated_artifacts": generated_artifacts,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "case_results": case_results,
        "failures": failures,
        "degraded": degraded,
        "degraded_reasons": degraded_reasons,
        "skipped_checks": skipped_checks,
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
    parser = argparse.ArgumentParser(description="Run AICP conformance against a JSONL IUT adapter")
    command_group = parser.add_mutually_exclusive_group(required=True)
    command_group.add_argument("--cmd", help="Adapter command parsed to argv; never passed to a shell")
    command_group.add_argument("--cmd-json", help="Adapter argv as a JSON string array")
    parser.add_argument(
        "--profile",
        required=True,
        choices=["AICP-BASE@0.1", "AICP-AUTHENTICATED-BASE@0.1"],
    )
    parser.add_argument("--mode", required=True, choices=["smoke", "full-profile"])
    parser.add_argument("--include-session-state-projection", action="store_true")
    parser.add_argument("--timeout", type=float, default=20)
    parser.add_argument("--max-stdout-bytes", type=int, default=8_388_608)
    parser.add_argument("--max-stderr-bytes", type=int, default=262_144)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    try:
        report = run_iut(
            _parse_command(args),
            args.profile,
            mode=args.mode,
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
    print(f"IUT {args.mode} {status}: {args.profile} -> {out_path}")
    for failure in report["failures"]:
        print(f" - [{failure['test_id']}] {failure['message']}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
