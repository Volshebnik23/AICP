#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import secrets
import sys
import tempfile
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = ROOT / "conformance" / "evidence"
RUNNER_DIR = ROOT / "conformance" / "runner"
for path in (EVIDENCE_DIR, RUNNER_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from _runner_context import build_validator  # noqa: E402
from target_catalog import (  # noqa: E402
    TARGET_SCHEMA_PATH,
    TARGETS_PATH,
    bundle_digest,
    expected_input_artifacts,
    expected_suite_records,
    file_digest,
    load_json,
    mandatory_case_ids,
    release_record,
    release_snapshot_digest,
    release_target_entry,
    resolve_target_record,
    runtime_import_closure,
    target_catalog,
    validate_release_registry,
    validate_target_catalog,
    validate_target_registry,
)
from target_handlers import resolve_handler  # noqa: E402
from live_bindings.live_binding_process import (  # noqa: E402
    LiveProcessError,
    explicit_environment,
    reject_secret_reflection,
    spawn_process,
    terminate_and_reap,
    validate_loopback_url,
    wait_ready_descriptor,
)
from live_bindings.live_binding_trace import (  # noqa: E402
    build_trace_artifact,
    evaluate_live_binding_trace,
    load_scenario_catalog,
)
from live_bindings.live_http_transport import (  # noqa: E402
    TlsChallengeObservation,
    TlsChallengeSequence,
    execute_http_client,
    interactions_from_capture,
    load_messages,
    start_http_server,
    stop_http_server,
)
from live_bindings.live_http_capture import attach_tls_challenge_evidence  # noqa: E402
from live_bindings.live_mcp_transport import (  # noqa: E402
    execute_mcp_server,
    serve_mcp_client,
)
from live_bindings.live_public_scenarios import public_scenario_projection  # noqa: E402
from live_bindings.live_tls import (  # noqa: E402
    challenge_server_ssl_context,
    generate_ephemeral_tls_material,
    server_ssl_context,
)


READY_SCHEMA_PATH = EVIDENCE_DIR / "live_bindings/live_endpoint_descriptor_v2.schema.json"
TRACE_SCHEMA_PATH = EVIDENCE_DIR / "live_bindings/live_binding_trace_v4.schema.json"
PUBLIC_SCENARIO_SCHEMA_PATH = (
    EVIDENCE_DIR / "live_bindings/live_public_scenario_v1.schema.json"
)
ROLE_NAMES = ("server_under_test", "client_under_test")


def _binding_slug(binding_id: str) -> str:
    return "http" if binding_id == "BIND-HTTP" else "mcp"


def _descriptor_subject(descriptor: dict[str, Any]) -> dict[str, Any]:
    return {
        "role": descriptor["role"],
        "implementation_kind": descriptor["implementation_kind"],
        "implementation_id": descriptor["implementation_id"],
        "implementation_version": descriptor["implementation_version"],
        "implementation_digest": descriptor["implementation_digest"],
        "declared_features": descriptor["declared_features"],
    }


def _validate_descriptor(
    descriptor: dict[str, Any],
    *,
    binding_id: str,
    role: str,
) -> None:
    schema = load_json(READY_SCHEMA_PATH)
    validator = build_validator(schema, READY_SCHEMA_PATH)
    if validator is None:
        raise LiveProcessError("jsonschema is required for live endpoint descriptors")
    issues = sorted(validator.iter_errors(descriptor), key=lambda item: list(item.path))
    if issues:
        issue = issues[0]
        pointer = "/" + "/".join(str(part) for part in issue.path)
        raise LiveProcessError(f"live endpoint descriptor schema error at {pointer}: {issue.message}")
    if descriptor.get("binding_id") != binding_id or descriptor.get("binding_version") != "0.1":
        raise LiveProcessError("live endpoint descriptor binding identity mismatch")
    if descriptor.get("role") != role:
        raise LiveProcessError("live endpoint descriptor role mismatch")
    features = descriptor.get("declared_features")
    if not isinstance(features, dict) or features.get("request_response") is not True:
        raise LiveProcessError("live endpoint must declare request/response support")
    if binding_id == "BIND-MCP" and descriptor.get("transport") != "stdio":
        raise LiveProcessError("MCP live endpoint must declare stdio transport")
    if binding_id == "BIND-HTTP" and role == "server_under_test":
        validate_loopback_url(str(descriptor.get("base_url", "")))
        features = descriptor.get("declared_features", {})
        websocket_url = descriptor.get("websocket_url")
        if features.get("websocket") is True:
            validate_loopback_url(str(websocket_url or ""))
        if features.get("wss") is True and not str(websocket_url).startswith("wss://"):
            raise LiveProcessError("WSS was declared without an executable WSS endpoint")


def _scenario_payload(binding_id: str, role: str, run_index: int) -> dict[str, Any]:
    catalog = load_scenario_catalog(binding_id)
    payload = public_scenario_projection(
        catalog,
        tested_role=role,
        run_index=run_index,
        input_messages=load_messages(),
    )
    validator = build_validator(
        load_json(PUBLIC_SCENARIO_SCHEMA_PATH), PUBLIC_SCENARIO_SCHEMA_PATH
    )
    if validator is None:
        raise LiveProcessError("jsonschema is required for public live scenarios")
    issues = sorted(validator.iter_errors(payload), key=lambda item: list(item.path))
    if issues:
        raise LiveProcessError(f"public live scenario schema error: {issues[0].message}")
    return payload


def _control_environment(
    *,
    binding_id: str,
    role: str,
    run_index: int,
    ready_path: Path,
    scenario_path: Path,
    bearer: str,
    endpoint_url: str | None = None,
    websocket_url: str | None = None,
    wss_challenge_url: str | None = None,
    tls_ca_file: Path | None = None,
    tls_cert_file: Path | None = None,
    tls_key_file: Path | None = None,
    tls_wrong_ca_file: Path | None = None,
) -> dict[str, str]:
    values = {
        "AICP_LIVE_RUN_ID": f"m64-{_binding_slug(binding_id)}-{role}-{run_index}",
        "AICP_LIVE_BINDING_ID": binding_id,
        "AICP_LIVE_BINDING_VERSION": "0.1",
        "AICP_LIVE_ROLE": role,
        "AICP_LIVE_READY_FILE": str(ready_path),
        "AICP_LIVE_SCENARIO_FILE": str(scenario_path),
        "AICP_LIVE_TEST_BEARER": bearer,
    }
    if endpoint_url is not None:
        values["AICP_LIVE_ENDPOINT_URL"] = endpoint_url
    if websocket_url is not None:
        values["AICP_LIVE_WEBSOCKET_URL"] = websocket_url
    if wss_challenge_url is not None:
        values["AICP_LIVE_WSS_CHALLENGE_URL"] = wss_challenge_url
    for name, path in (
        ("AICP_LIVE_TLS_CA_FILE", tls_ca_file),
        ("AICP_LIVE_TLS_CERT_FILE", tls_cert_file),
        ("AICP_LIVE_TLS_KEY_FILE", tls_key_file),
        ("AICP_LIVE_TLS_WRONG_CA_FILE", tls_wrong_ca_file),
    ):
        if path is not None:
            values[name] = str(path)
    return explicit_environment(values)


def _run_http_server_role(
    command: list[str],
    *,
    run_index: int,
    timeout_seconds: float,
) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    bearer = secrets.token_urlsafe(32)
    with tempfile.TemporaryDirectory(prefix="aicp-live-http-server-") as temporary:
        directory = Path(temporary)
        ready_path = directory / "ready.json"
        scenario_path = directory / "scenario.json"
        material = generate_ephemeral_tls_material(directory, stem="server")
        wrong_material = generate_ephemeral_tls_material(directory, stem="wrong")
        scenario_path.write_text(
            json.dumps(_scenario_payload("BIND-HTTP", "server_under_test", run_index), separators=(",", ":"), ensure_ascii=False),
            encoding="utf-8",
        )
        environment = _control_environment(
            binding_id="BIND-HTTP",
            role="server_under_test",
            run_index=run_index,
            ready_path=ready_path,
            scenario_path=scenario_path,
            bearer=bearer,
            tls_ca_file=material.ca_file,
            tls_cert_file=material.cert_file,
            tls_key_file=material.key_file,
            tls_wrong_ca_file=wrong_material.ca_file,
        )
        process, stdout_collector, stderr_collector = spawn_process(
            command,
            environment=environment,
            root=ROOT,
        )
        deadline = time.monotonic() + timeout_seconds
        try:
            descriptor = wait_ready_descriptor(process, ready_path, deadline=deadline)
            _validate_descriptor(descriptor, binding_id="BIND-HTTP", role="server_under_test")
            interactions = execute_http_client(
                str(descriptor["base_url"]),
                bearer,
                role="server_under_test",
                declared_features=descriptor["declared_features"],
                websocket_url=str(descriptor.get("websocket_url", "")) or None,
                tls_ca_file=str(material.ca_file),
            )
            reject_secret_reflection(
                {"descriptor": descriptor, "interactions": interactions},
                [bearer, material.private_key_pem, wrong_material.private_key_pem],
            )
        finally:
            terminate_and_reap(process)
        stdout_text = stdout_collector.finish() if stdout_collector is not None else ""
        stderr_text = stderr_collector.finish()
        if stdout_text.strip():
            raise LiveProcessError("HTTP server wrote unexpected stdout outside its transport")
        return _descriptor_subject(descriptor), interactions, stderr_text


def _run_http_client_role(
    command: list[str],
    *,
    run_index: int,
    timeout_seconds: float,
) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    bearer = secrets.token_urlsafe(32)
    temporary_context = tempfile.TemporaryDirectory(prefix="aicp-live-http-client-tls-")
    tls_directory = Path(temporary_context.name)
    material = generate_ephemeral_tls_material(tls_directory, stem="server")
    wrong_material = generate_ephemeral_tls_material(tls_directory, stem="wrong")
    challenge_sequence = TlsChallengeSequence()
    trusted_observation = TlsChallengeObservation(
        endpoint_class="trusted", sequence=challenge_sequence
    )
    untrusted_observation = TlsChallengeObservation(
        endpoint_class="untrusted", sequence=challenge_sequence
    )
    server, state, thread = start_http_server(bearer)
    tls_server, _tls_state, tls_thread = start_http_server(
        bearer,
        ssl_context=server_ssl_context(material),
        state=state,
        tls_observation=trusted_observation,
    )
    untrusted_server, _untrusted_state, untrusted_thread = start_http_server(
        bearer,
        ssl_context=challenge_server_ssl_context(wrong_material),
        state=state,
        tls_observation=untrusted_observation,
    )
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    websocket_url = f"wss://127.0.0.1:{tls_server.server_address[1]}"
    wss_challenge_url = (
        f"wss://127.0.0.1:{untrusted_server.server_address[1]}"
    )
    try:
        with tempfile.TemporaryDirectory(prefix="aicp-live-http-client-") as temporary:
            directory = Path(temporary)
            ready_path = directory / "ready.json"
            scenario_path = directory / "scenario.json"
            scenario_path.write_text(
                json.dumps(_scenario_payload("BIND-HTTP", "client_under_test", run_index), separators=(",", ":"), ensure_ascii=False),
                encoding="utf-8",
            )
            environment = _control_environment(
                binding_id="BIND-HTTP",
                role="client_under_test",
                run_index=run_index,
                ready_path=ready_path,
                scenario_path=scenario_path,
                bearer=bearer,
                endpoint_url=base_url,
                websocket_url=websocket_url,
                wss_challenge_url=wss_challenge_url,
                tls_ca_file=material.ca_file,
            )
            process, stdout_collector, stderr_collector = spawn_process(
                command,
                environment=environment,
                root=ROOT,
            )
            deadline = time.monotonic() + timeout_seconds
            try:
                descriptor = wait_ready_descriptor(process, ready_path, deadline=deadline)
                _validate_descriptor(descriptor, binding_id="BIND-HTTP", role="client_under_test")
                remaining = max(0.01, deadline - time.monotonic())
                try:
                    process.wait(timeout=remaining)
                except Exception as exc:
                    raise LiveProcessError("HTTP client did not complete before its deadline") from exc
                if process.returncode != 0:
                    raise LiveProcessError(f"HTTP client exited with code {process.returncode}")
                interactions = interactions_from_capture(
                    state,
                    role="client_under_test",
                    declared_features=descriptor["declared_features"],
                )
                interactions = attach_tls_challenge_evidence(
                    interactions,
                    [
                        untrusted_observation.evidence(),
                        trusted_observation.evidence(),
                    ],
                )
                reject_secret_reflection(
                    {"descriptor": descriptor, "interactions": interactions},
                    [bearer, material.private_key_pem, wrong_material.private_key_pem],
                )
            finally:
                terminate_and_reap(process)
            stdout_text = stdout_collector.finish() if stdout_collector is not None else ""
            stderr_text = stderr_collector.finish()
            if stdout_text.strip():
                raise LiveProcessError("HTTP client wrote unexpected stdout outside its transport")
            return _descriptor_subject(descriptor), interactions, stderr_text
    finally:
        stop_http_server(server, thread)
        stop_http_server(tls_server, tls_thread)
        stop_http_server(untrusted_server, untrusted_thread)
        temporary_context.cleanup()


def _run_mcp_server_role(
    command: list[str],
    *,
    run_index: int,
    timeout_seconds: float,
) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    with tempfile.TemporaryDirectory(prefix="aicp-live-mcp-server-") as temporary:
        directory = Path(temporary)
        ready_path = directory / "ready.json"
        scenario_path = directory / "scenario.json"
        scenario_path.write_text(
            json.dumps(_scenario_payload("BIND-MCP", "server_under_test", run_index), separators=(",", ":"), ensure_ascii=False),
            encoding="utf-8",
        )
        environment = _control_environment(
            binding_id="BIND-MCP",
            role="server_under_test",
            run_index=run_index,
            ready_path=ready_path,
            scenario_path=scenario_path,
            bearer="",
        )
        process, _stdout_collector, stderr_collector = spawn_process(
            command,
            environment=environment,
            root=ROOT,
            stdout_transport=True,
        )
        deadline = time.monotonic() + timeout_seconds
        try:
            descriptor = wait_ready_descriptor(process, ready_path, deadline=deadline)
            _validate_descriptor(descriptor, binding_id="BIND-MCP", role="server_under_test")
            interactions = execute_mcp_server(
                process,
                role="server_under_test",
                deadline=deadline,
            )
            if process.stdin is not None:
                process.stdin.close()
            remaining = max(0.01, deadline - time.monotonic())
            try:
                process.wait(timeout=remaining)
            except Exception as exc:
                raise LiveProcessError("MCP server did not exit after stdin closed") from exc
            if process.returncode != 0:
                raise LiveProcessError(f"MCP server exited with code {process.returncode}")
        finally:
            terminate_and_reap(process)
        return _descriptor_subject(descriptor), interactions, stderr_collector.finish()


def _run_mcp_client_role(
    command: list[str],
    *,
    run_index: int,
    timeout_seconds: float,
) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    with tempfile.TemporaryDirectory(prefix="aicp-live-mcp-client-") as temporary:
        directory = Path(temporary)
        ready_path = directory / "ready.json"
        scenario_path = directory / "scenario.json"
        scenario_path.write_text(
            json.dumps(_scenario_payload("BIND-MCP", "client_under_test", run_index), separators=(",", ":"), ensure_ascii=False),
            encoding="utf-8",
        )
        environment = _control_environment(
            binding_id="BIND-MCP",
            role="client_under_test",
            run_index=run_index,
            ready_path=ready_path,
            scenario_path=scenario_path,
            bearer="",
        )
        process, _stdout_collector, stderr_collector = spawn_process(
            command,
            environment=environment,
            root=ROOT,
            stdout_transport=True,
        )
        deadline = time.monotonic() + timeout_seconds
        try:
            descriptor = wait_ready_descriptor(process, ready_path, deadline=deadline)
            _validate_descriptor(descriptor, binding_id="BIND-MCP", role="client_under_test")
            interactions = serve_mcp_client(
                process,
                role="client_under_test",
                deadline=deadline,
            )
        finally:
            terminate_and_reap(process)
        return _descriptor_subject(descriptor), interactions, stderr_collector.finish()


def _run_role(
    binding_id: str,
    role: str,
    command: list[str],
    *,
    run_index: int,
    timeout_seconds: float,
) -> tuple[dict[str, Any], list[dict[str, Any]], str]:
    if binding_id == "BIND-HTTP" and role == "server_under_test":
        return _run_http_server_role(command, run_index=run_index, timeout_seconds=timeout_seconds)
    if binding_id == "BIND-HTTP":
        return _run_http_client_role(command, run_index=run_index, timeout_seconds=timeout_seconds)
    if role == "server_under_test":
        return _run_mcp_server_role(command, run_index=run_index, timeout_seconds=timeout_seconds)
    return _run_mcp_client_role(command, run_index=run_index, timeout_seconds=timeout_seconds)


def _base_report(record: Any, mode: str, timestamp: str) -> dict[str, Any]:
    release = release_record(record.current_release_id)
    release_target = release_target_entry(release, record.target_key)
    catalog_digest = release_target["target_catalog"]["content_digest"]
    return {
        "report_format_version": "2.2",
        "report_type": "aicp.external_evidence",
        "execution_mode": mode,
        "execution_subject": {
            "kind": "reference_corpus",
            "implementation_id": "unknown",
            "implementation_version": "unknown",
            "implementation_digest": "sha256:" + "0" * 64,
        },
        "runner": {
            "name": "aicp-external-evidence-runner",
            "version": "2.2",
            "source_revision": release["runner_bundle"]["digest"],
        },
        "tck_release": {
            "release_id": release["release_id"],
            "registry_digest": release_snapshot_digest(release["release_id"]),
            "target_registry_digest": release["target_registry"]["content_digest"],
            "target_registry_schema_digest": release["target_registry"]["schema_digest"],
            "target_catalog_digest": catalog_digest,
            "report_schema_digest": release["report_schema"]["content_digest"],
            "runner_bundle_digest": release["runner_bundle"]["digest"],
        },
        "target": {**record.identity(), "target_catalog_digest": catalog_digest},
        "required_suites": expected_suite_records(release, record.target_key),
        "input_artifacts": expected_input_artifacts(release, record.target_key),
        "generated_artifacts": [],
        "timestamp": timestamp,
        "passed": False,
        "case_results": [],
        "failures": [],
        "degraded": False,
        "degraded_reasons": [],
        "skipped_checks": [],
        "compatibility_marks": [],
        "adapter_stderr": "",
    }


def run_live_binding_evidence(
    server_command: list[str],
    client_command: list[str] | None,
    *,
    target: str,
    mode: str,
    timeout_seconds: float = 15,
    timestamp: str | None = None,
) -> dict[str, Any]:
    record = resolve_target_record(target)
    if record.target_kind != "binding":
        raise ValueError("live binding runner requires a binding target")
    if mode not in {"smoke", "full-binding"}:
        raise ValueError("live binding execution mode must be smoke or full-binding")
    if mode == "full-binding" and not client_command:
        raise ValueError("full-binding execution requires both role commands")
    handler = resolve_handler(record.handler_id)
    catalog = target_catalog(record)
    report = _base_report(record, mode, timestamp or datetime.now(timezone.utc).isoformat())

    def record_case(case_id: str, passed: bool, message: str) -> None:
        report["case_results"].append({"case_id": case_id, "passed": passed, "message": message})
        if not passed:
            report["failures"].append({"test_id": case_id, "message": message})

    catalog_errors = [
        *validate_target_registry(),
        *validate_target_catalog(catalog, record=record, handler=handler),
    ]
    record_case(
        "EVIDENCE-TARGET-CATALOG-01",
        not catalog_errors,
        "binding target registry and neutral scenario catalog are complete" if not catalog_errors else "; ".join(catalog_errors),
    )
    release_errors = validate_release_registry()
    record_case(
        "EVIDENCE-TCK-PROVENANCE-01",
        not release_errors,
        "evidence TCK provenance and import-closed bundle match current bytes" if not release_errors else "; ".join(release_errors),
    )
    actual_bundle = bundle_digest(runtime_import_closure())
    registered_bundle = report["tck_release"]["runner_bundle_digest"]
    bundle_matches = actual_bundle == registered_bundle
    if not bundle_matches:
        report["runner"]["source_revision"] = actual_bundle
    record_case(
        "EVIDENCE-RUNNER-WORKTREE-01",
        bundle_matches,
        "actual runtime import closure matches TCK 1.7" if bundle_matches else "actual live runner bytes differ from the registered release",
    )

    roles_to_run = ["server_under_test"] + (["client_under_test"] if mode == "full-binding" else [])
    commands = {
        "server_under_test": server_command,
        "client_under_test": client_command or [],
    }
    role_metadata: dict[str, dict[str, Any]] = {}
    runs: list[dict[str, Any]] = []
    stderr_parts: list[str] = []
    execution_error: str | None = None
    for run_index in (1, 2):
        interactions: list[dict[str, Any]] = []
        for role in roles_to_run:
            try:
                descriptor, observed, stderr_text = _run_role(
                    record.target_id,
                    role,
                    commands[role],
                    run_index=run_index,
                    timeout_seconds=timeout_seconds,
                )
            except (LiveProcessError, OSError, ValueError) as exc:
                execution_error = str(exc)
                break
            if run_index == 1:
                role_metadata[role] = descriptor
            elif role_metadata.get(role) != descriptor:
                execution_error = f"{role} implementation metadata changed between clean runs"
                break
            interactions.extend(observed)
            if stderr_text:
                # External stderr may contain implementation diagnostics or
                # credentials. Its presence is useful; its bytes are not
                # evidence and are deliberately excluded from the report.
                stderr_parts.append(
                    f"{role} emitted bounded stderr; content omitted from live evidence"
                )
        if execution_error is not None:
            break
        runs.append({"run_index": run_index, "interactions": interactions})

    for role in roles_to_run:
        passed = execution_error is None and role in role_metadata and len(runs) == 2
        record_case(
            "EVIDENCE-LIVE-SERVER-ROLE-01" if role == "server_under_test" else "EVIDENCE-LIVE-CLIENT-ROLE-01",
            passed,
            f"{role} completed two clean real-transport runs" if passed else (execution_error or f"{role} did not complete"),
        )

    if execution_error == "EVIDENCE_LIVE_SECRET_REFLECTION":
        report["failures"].append(
            {
                "test_id": "EVIDENCE_LIVE_SECRET_REFLECTION",
                "message": "a runner-created live secret was reflected into candidate evidence",
            }
        )

    identity_values = {
        (
            item.get("implementation_kind"),
            item.get("implementation_id"),
            item.get("implementation_version"),
            item.get("implementation_digest"),
        )
        for item in role_metadata.values()
    }
    subject_ok = execution_error is None and len(identity_values) == 1 and set(role_metadata) == set(roles_to_run)
    record_case(
        "EVIDENCE-LIVE-SUBJECT-01",
        subject_ok,
        "all executed roles identify one exact implementation build" if subject_ok else "live role implementation subjects differ or are incomplete",
    )

    artifact: dict[str, Any] | None = None
    trace_schema_ok = False
    trace_errors: list[str] = []
    if execution_error is None and len(runs) == 2 and subject_ok:
        artifact = build_trace_artifact(binding_id=record.target_id, roles=role_metadata, runs=runs)
        trace_schema = load_json(TRACE_SCHEMA_PATH)
        validator = build_validator(trace_schema, TRACE_SCHEMA_PATH)
        if validator is not None:
            issues = sorted(validator.iter_errors(artifact), key=lambda item: list(item.path))
            trace_errors = [
                "/" + "/".join(str(part) for part in issue.path) + f": {issue.message}"
                for issue in issues
            ]
            trace_schema_ok = not trace_errors
        else:
            trace_errors = ["jsonschema is unavailable"]
        report["generated_artifacts"] = [artifact]
    record_case(
        "EVIDENCE-LIVE-TRACE-SCHEMA-01",
        trace_schema_ok,
        "sanitized live trace matches its strict schema" if trace_schema_ok else "; ".join(trace_errors or [execution_error or "trace unavailable"]),
    )
    if artifact is not None:
        trace_eval_errors = evaluate_live_binding_trace(
            artifact,
            load_scenario_catalog(record.target_id),
            full_binding=mode == "full-binding",
        )
    else:
        trace_eval_errors = [execution_error or "trace unavailable"]
    record_case(
        "EVIDENCE-LIVE-TRACE-EVALUATION-01",
        not trace_eval_errors,
        "independent live evaluator recomputed every mandatory semantic family" if not trace_eval_errors else "; ".join(trace_eval_errors),
    )
    determinism_ok = (
        artifact is not None
        and artifact["content"]["semantic_digest"] == artifact["content"]["repeat_semantic_digest"]
    )
    record_case(
        "EVIDENCE-LIVE-DETERMINISM-01",
        determinism_ok,
        "two normalized semantic digests recompute and match" if determinism_ok else "normalized semantic repeat differs or is unavailable",
    )
    support_ok = record.target_id in {"BIND-HTTP", "BIND-MCP"}
    record_case(
        "EVIDENCE-TARGET-SUPPORT-01",
        support_ok,
        "implementation descriptors declare the exact registered binding" if support_ok else "binding target is unsupported",
    )

    if role_metadata:
        first = next(iter(role_metadata.values()))
        report["execution_subject"] = {
            "kind": first["implementation_kind"],
            "implementation_id": first["implementation_id"],
            "implementation_version": first["implementation_version"],
            "implementation_digest": first["implementation_digest"],
        }
    report["adapter_stderr"] = "\n".join(stderr_parts)[:262_144]
    expected_ids = Counter(mandatory_case_ids(catalog, mode, handler))
    actual_ids = Counter(item["case_id"] for item in report["case_results"])
    coverage_ok = expected_ids == actual_ids
    if not coverage_ok:
        report["failures"].append(
            {
                "test_id": "EVIDENCE-CASE-COVERAGE-01",
                "message": "mandatory live evidence case coverage is missing, duplicated, or unknown",
            }
        )
    report["passed"] = not report["failures"]
    eligible = (
        report["passed"]
        and coverage_ok
        and mode == "full-binding"
        and report["execution_subject"]["kind"] == "external_implementation"
    )
    report["compatibility_marks"] = [record.expected_mark] if eligible else []
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server-cmd-json", required=True)
    parser.add_argument("--client-cmd-json")
    parser.add_argument("--target", required=True)
    parser.add_argument("--mode", choices=("smoke", "full-binding"), required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--timeout", type=float, default=15)
    parser.add_argument("--timestamp")
    args = parser.parse_args()
    try:
        server_command = json.loads(args.server_cmd_json)
        client_command = json.loads(args.client_cmd_json) if args.client_cmd_json else None
    except json.JSONDecodeError as exc:
        parser.error(f"role command is not a JSON argument vector: {exc}")
    for name, command in (("server", server_command), ("client", client_command)):
        if command is not None and (
            not isinstance(command, list)
            or not all(isinstance(part, str) and part for part in command)
        ):
            parser.error(f"--{name}-cmd-json must be a JSON array of non-empty strings")
    report = run_live_binding_evidence(
        server_command,
        client_command,
        target=args.target,
        mode=args.mode,
        timeout_seconds=args.timeout,
        timestamp=args.timestamp,
    )
    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(
        f"Live binding evidence {'PASSED' if report['passed'] else 'FAILED'}: "
        f"{args.target}; mode={args.mode}; mark_count={len(report['compatibility_marks'])}; out={args.out}"
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
