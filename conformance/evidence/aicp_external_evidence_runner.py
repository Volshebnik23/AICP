#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = ROOT / "conformance" / "evidence"
REF_PY = ROOT / "reference" / "python"
for path in (EVIDENCE_DIR, REF_PY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from adapter_process import AdapterProcessError, invoke_adapter  # noqa: E402
from aicp_ref.signatures import signature_verifier_available  # noqa: E402
from target_catalog import (  # noqa: E402
    TARGET_KEY,
    TARGET_SCHEMA_PATH,
    TARGETS_PATH,
    TCK_RELEASES_PATH,
    TargetRecord,
    canonical_digest,
    expected_input_artifacts,
    expected_suite_records,
    file_digest,
    load_json,
    mandatory_case_ids,
    release_record,
    release_target_entry,
    resolve_target_record,
    target_catalog,
    validate_release_registry,
    validate_target_catalog,
    validate_target_registry,
)
from target_handlers import resolve_handler  # noqa: E402


PROTOCOL_VERSION = "1.1"
DIGEST_RE = re.compile(r"^sha256:[a-f0-9]{64}$")


def _request(
    request_id: str,
    operation: str,
    input_obj: dict[str, Any],
) -> dict[str, Any]:
    return {
        "adapter_protocol_version": PROTOCOL_VERSION,
        "request_id": request_id,
        "operation": operation,
        "input": input_obj,
    }


def build_execution_plan(
    record: TargetRecord,
    catalog: dict[str, Any],
    handler: Any,
    mode: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    requests: list[dict[str, Any]] = []
    checks: list[dict[str, Any]] = []
    counter = 0

    def append(
        operation: str,
        input_obj: dict[str, Any],
        check: dict[str, Any],
    ) -> None:
        nonlocal counter
        counter += 1
        requests.append(
            _request(
                f"evidence-request-{counter:06d}",
                operation,
                input_obj,
            )
        )
        checks.append(check)

    append("describe", {}, {"kind": "describe_start"})
    for operation, input_obj, check in handler.build_plan_entries(catalog, mode):
        append(operation, input_obj, check)
    append("describe", {}, {"kind": "describe_end"})
    return requests, checks


def _consumer_observation(
    result: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    errors: list[str] = []
    required = (
        "accepted",
        "errors",
        "degraded",
        "degraded_reasons",
        "skipped_checks",
    )
    missing = [field for field in required if field not in result]
    if missing:
        errors.append("missing required result fields: " + ", ".join(missing))
    accepted = result.get("accepted")
    result_errors = result.get("errors")
    degraded = result.get("degraded")
    reasons = result.get("degraded_reasons")
    skipped = result.get("skipped_checks")
    if type(accepted) is not bool:
        errors.append("accepted must be boolean")
    if not isinstance(result_errors, list) or not all(
        isinstance(item, dict)
        and isinstance(item.get("code"), str)
        and isinstance(item.get("message"), str)
        for item in result_errors or []
    ):
        errors.append("errors must be an array of code/message objects")
        result_errors = []
    if type(degraded) is not bool:
        errors.append("degraded must be boolean")
    if not isinstance(reasons, list) or not all(
        isinstance(item, str) and item for item in reasons or []
    ):
        errors.append("degraded_reasons must be non-empty strings")
        reasons = []
    if not isinstance(skipped, list) or not all(
        isinstance(item, str) and item for item in skipped or []
    ):
        errors.append("skipped_checks must be non-empty strings")
        skipped = []
    return (
        {
            "accepted": accepted,
            "errors": result_errors,
            "degraded": degraded,
            "degraded_reasons": reasons,
            "skipped_checks": skipped,
        },
        errors,
    )


def _support_metadata(record: TargetRecord) -> tuple[str, dict[str, str]]:
    if record.target_kind == "capability":
        return (
            "supported_aicp_capabilities",
            {
                "capability_id": record.target_id,
                "capability_version": record.target_version,
            },
        )
    if record.target_kind == "product_profile":
        return (
            "supported_aicp_profiles",
            {
                "profile_id": record.target_id,
                "profile_version": record.target_version,
            },
        )
    return (
        "supported_aicp_bindings",
        {
            "binding_id": record.target_id,
            "binding_version": record.target_version,
        },
    )


def _describe_errors(
    metadata: dict[str, Any],
    *,
    record: TargetRecord,
    release: dict[str, Any],
    inputs: list[dict[str, str]],
    suites: list[dict[str, str]],
) -> list[str]:
    errors: list[str] = []
    release_target = release_target_entry(release, record.target_key)
    support_field, expected_support = _support_metadata(record)
    required = [
        "implementation_kind",
        "implementation_id",
        "implementation_version",
        "implementation_digest",
        support_field,
        "adapter_protocol_version",
    ]
    missing = [field for field in required if field not in metadata]
    if missing:
        errors.append("missing implementation metadata: " + ", ".join(missing))
    if metadata.get("implementation_kind") not in {
        "external_implementation",
        "reference_corpus",
    }:
        errors.append("implementation_kind is not eligible or reference")
    for field in ("implementation_id", "implementation_version"):
        if not isinstance(metadata.get(field), str) or not metadata.get(field):
            errors.append(f"{field} must be a non-empty string")
    if not isinstance(metadata.get("implementation_digest"), str) or not DIGEST_RE.fullmatch(
        str(metadata.get("implementation_digest"))
    ):
        errors.append("implementation_digest must be an exact SHA-256 digest")
    if metadata.get("adapter_protocol_version") != PROTOCOL_VERSION:
        errors.append("adapter protocol metadata must remain version 1.1")
    supported = metadata.get(support_field)
    if not isinstance(supported, list) or expected_support not in supported:
        errors.append("exact registered target is not explicitly declared")

    claim_checks = {
        "claimed_tck_release": release["release_id"],
        "claimed_runner_digest": release["runner_bundle"]["digest"],
        "claimed_registry_schema_digest": release["target_registry"][
            "schema_digest"
        ],
        "claimed_target_registry_digest": release["target_registry"][
            "content_digest"
        ],
        "claimed_target_catalog_digest": release_target["target_catalog"][
            "content_digest"
        ],
        "claimed_suite_digest": suites[0]["suite_digest"],
        "claimed_report_schema_digest": release["report_schema"][
            "content_digest"
        ],
        "claimed_input_digest": canonical_digest(inputs),
    }
    for field, expected in claim_checks.items():
        if field in metadata and metadata.get(field) != expected:
            errors.append(f"adapter {field} does not match runner provenance")
    if "claimed_compatibility_marks" in metadata:
        errors.append("adapter-supplied compatibility marks are never trusted")
    return errors


def _base_report(
    *,
    record: TargetRecord,
    mode: str,
    release: dict[str, Any],
    catalog_digest: str,
    inputs: list[dict[str, str]],
    suites: list[dict[str, str]],
    timestamp: str,
) -> dict[str, Any]:
    report_version = (
        "2.1"
        if str(release["report_schema"]["path"]).endswith("v2_1.schema.json")
        else "2.0"
    )
    return {
        "report_format_version": report_version,
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
            "version": report_version,
            "source_revision": release["runner_bundle"]["digest"],
        },
        "tck_release": {
            "release_id": release["release_id"],
            "registry_digest": file_digest(TCK_RELEASES_PATH),
            "target_registry_digest": release["target_registry"][
                "content_digest"
            ],
            "target_registry_schema_digest": release["target_registry"][
                "schema_digest"
            ],
            "target_catalog_digest": catalog_digest,
            "report_schema_digest": release["report_schema"][
                "content_digest"
            ],
            "runner_bundle_digest": release["runner_bundle"]["digest"],
        },
        "target": {
            **record.identity(),
            "target_catalog_digest": catalog_digest,
        },
        "required_suites": suites,
        "input_artifacts": inputs,
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


def run_evidence(
    command: list[str],
    *,
    target: str = TARGET_KEY,
    mode: str = "full-capability",
    timeout_seconds: float = 20,
    max_stdout_bytes: int = 8_388_608,
    max_stderr_bytes: int = 262_144,
    simulate_no_jsonschema: bool = False,
    simulate_no_crypto: bool = False,
    timestamp: str | None = None,
) -> dict[str, Any]:
    try:
        record = resolve_target_record(target)
    except ValueError as exc:
        raise ValueError(f"unregistered evidence target: {target}") from exc
    try:
        handler = resolve_handler(record.handler_id)
    except ValueError as exc:
        raise ValueError(
            f"target registered but handler unavailable: {target}"
        ) from exc
    if mode not in {record.execution_mode, "smoke"}:
        raise ValueError(
            f"execution mode must be {record.execution_mode} or smoke"
        )
    catalog = target_catalog(record)
    release = release_record(record.current_release_id)
    inputs = expected_input_artifacts(release, record.target_key)
    suites = expected_suite_records(release, record.target_key)
    catalog_path = ROOT / record.catalog_path
    catalog_digest = file_digest(catalog_path)
    report = _base_report(
        record=record,
        mode=mode,
        release=release,
        catalog_digest=catalog_digest,
        inputs=inputs,
        suites=suites,
        timestamp=timestamp or datetime.now(timezone.utc).isoformat(),
    )
    failures = report["failures"]
    case_results = report["case_results"]

    def record_case(
        case_id: str,
        passed: bool,
        message: str,
        *,
        observation: dict[str, Any] | None = None,
    ) -> None:
        item: dict[str, Any] = {
            "case_id": case_id,
            "passed": passed,
            "message": message,
        }
        if observation is not None:
            item["execution_observation"] = observation
        case_results.append(item)
        if not passed:
            failures.append({"test_id": case_id, "message": message})

    catalog_errors = [
        *validate_target_registry(
            simulate_no_jsonschema=simulate_no_jsonschema,
        ),
        *validate_target_catalog(
            catalog,
            record=record,
            handler=handler,
            simulate_no_jsonschema=simulate_no_jsonschema,
        ),
    ]
    record_case(
        "EVIDENCE-TARGET-CATALOG-01",
        not catalog_errors,
        "registry-schema-validated target and catalog are complete"
        if not catalog_errors
        else "; ".join(catalog_errors),
    )
    release_errors = validate_release_registry()
    record_case(
        "EVIDENCE-TCK-PROVENANCE-01",
        not release_errors,
        "evidence TCK provenance and import-closed bundle match current bytes"
        if not release_errors
        else "; ".join(release_errors),
    )

    producer = (
        catalog["producer_scenario_catalog"]
        if record.target_kind == "product_profile"
        else catalog["producer_case"]
    )
    scenario_validator, projection_validator = handler.producer_validators(
        ROOT
        / str(
            producer.get("schema_path")
            or producer["scenario_schema_path"]
        ),
        simulate_no_jsonschema=simulate_no_jsonschema,
    )
    if scenario_validator is None or projection_validator is None:
        report["degraded"] = True
        report["degraded_reasons"].append(
            "jsonschema dependency unavailable; target registry and producer schemas could not execute"
        )
        report["skipped_checks"].append("EVIDENCE-PRODUCER-SCHEMA-01")
    crypto_available = signature_verifier_available() and not simulate_no_crypto
    if not crypto_available:
        report["degraded"] = True
        report["degraded_reasons"].append(
            "Ed25519 verifier unavailable; mandatory evidence dependency probe did not complete"
        )
        report["skipped_checks"].append("EVIDENCE-CRYPTO-DEPENDENCY-01")

    requests, checks = build_execution_plan(record, catalog, handler, mode)
    try:
        responses, stderr_text = invoke_adapter(
            command,
            requests,
            timeout_seconds=timeout_seconds,
            max_stdout_bytes=max_stdout_bytes,
            max_stderr_bytes=max_stderr_bytes,
        )
    except AdapterProcessError as exc:
        failures.append(
            {"test_id": "EVIDENCE-ADAPTER-PROTOCOL-01", "message": str(exc)}
        )
        report["passed"] = False
        return report
    report["adapter_stderr"] = stderr_text

    first_metadata: dict[str, Any] | None = None
    final_metadata: dict[str, Any] | None = None
    producer_results: dict[str, dict[str, Any]] = {}
    producer_digests: dict[str, str] = {}
    producer_case_results: dict[str, dict[str, Any]] = {}
    for response, check in zip(responses, checks):
        result = response["result"]
        kind = check["kind"]
        if kind == "describe_start":
            first_metadata = result
            errors = _describe_errors(
                result,
                record=record,
                release=release,
                inputs=inputs,
                suites=suites,
            )
            record_case(
                "EVIDENCE-DESCRIBE-START-01",
                not errors,
                "implementation metadata and provenance claims are consistent"
                if not errors
                else "; ".join(errors),
            )
        elif kind == "describe_end":
            final_metadata = result
        elif kind == "canonicalize":
            expected = check["expected"]
            passed = (
                result.get("canonical_json") == expected["canonical_json"]
                and result.get("object_hash") == expected["object_hash"]
            )
            record_case(
                check["case_id"],
                passed,
                "canonical bytes and hash match"
                if passed
                else "canonical bytes or hash mismatch",
            )
        elif kind in {"producer", "producer_repeat"}:
            errors = handler.producer_errors(
                result,
                check,
                scenario_validator=scenario_validator,
                projection_validator=projection_validator,
            )
            digest = canonical_digest(result)
            artifact_id = str(check.get("artifact_id", check["case_id"]))
            if kind == "producer":
                producer_results[artifact_id] = result
                producer_digests[artifact_id] = digest
                record_case(
                    check["case_id"],
                    not errors,
                    "producer output passed scenario, transcript, schema, ordering, binding, and hash checks"
                    if not errors
                    else "; ".join(errors),
                )
                producer_case_results[artifact_id] = case_results[-1]
            else:
                producer_result = producer_results.get(artifact_id)
                producer_digest = producer_digests.get(artifact_id)
                producer_case_result = producer_case_results.get(artifact_id)
                if producer_result is None or producer_digest is None:
                    errors.append("first producer result is missing")
                elif result != producer_result or digest != producer_digest:
                    errors.append("producer repeat changed canonical content digest")
                if producer_case_result is not None and errors:
                    producer_case_result["passed"] = False
                    producer_case_result["message"] += "; " + "; ".join(errors)
                    if not any(
                        item["test_id"] == check["case_id"] for item in failures
                    ):
                        failures.append(
                            {
                                "test_id": check["case_id"],
                                "message": producer_case_result["message"],
                            }
                        )
                if producer_result is not None and producer_digest is not None:
                    artifact = {
                        "artifact_id": artifact_id,
                        "content_digest": producer_digest,
                        "repeat_content_digest": digest,
                        "content": producer_result,
                    }
                    if report["report_format_version"] == "2.1":
                        artifact["artifact_kind"] = str(
                            producer_result.get("artifact_kind", "transcript")
                        )
                    report["generated_artifacts"].append(artifact)
                    if producer_case_result is not None and not errors:
                        producer_case_result[
                            "message"
                        ] += "; deterministic repeat digest matched"
        elif kind == "consumer":
            observation, shape_errors = _consumer_observation(result)
            actual_codes = [
                str(item.get("code"))
                for item in observation["errors"]
                if isinstance(item, dict)
            ]
            expected = {
                "accepted": check["accepted"],
                "error_codes": handler.expected_error_codes(check),
                "degraded": check["expected_degraded"],
                "degraded_reasons": check["expected_degraded_reasons"],
                "skipped_checks": check["expected_skipped_checks"],
            }
            passed = not shape_errors
            passed = passed and observation["accepted"] is expected["accepted"]
            passed = passed and actual_codes == expected["error_codes"]
            passed = passed and observation["degraded"] is expected["degraded"]
            passed = passed and observation["degraded_reasons"] == expected[
                "degraded_reasons"
            ]
            passed = passed and observation["skipped_checks"] == expected[
                "skipped_checks"
            ]
            detail = (
                "consumer observation exactly matches reviewed counts and ordering"
                if passed
                else (
                    f"observed accepted={observation['accepted']}, "
                    f"errors={actual_codes}, degraded={observation['degraded']}, "
                    f"reasons={observation['degraded_reasons']}, "
                    f"skips={observation['skipped_checks']}; expected={expected}"
                    + ("; " + "; ".join(shape_errors) if shape_errors else "")
                )
            )
            record_case(
                check["case_id"],
                passed,
                detail,
                observation=observation,
            )

    if (
        first_metadata is None
        or final_metadata is None
        or first_metadata != final_metadata
    ):
        record_case(
            "EVIDENCE-DESCRIBE-STABILITY-01",
            False,
            "implementation metadata changed during execution",
        )
    else:
        record_case(
            "EVIDENCE-DESCRIBE-STABILITY-01",
            True,
            "implementation metadata remained immutable",
        )
    support_field, expected_support = _support_metadata(record)
    supported = (
        first_metadata.get(support_field)
        if isinstance(first_metadata, dict)
        else None
    )
    support_ok = isinstance(supported, list) and expected_support in supported
    record_case(
        "EVIDENCE-TARGET-SUPPORT-01",
        support_ok,
        "adapter explicitly declares the exact registered target"
        if support_ok
        else "adapter does not declare the exact registered target",
    )

    metadata = first_metadata or {}
    subject_kind = metadata.get("implementation_kind")
    if subject_kind not in {"external_implementation", "reference_corpus"}:
        subject_kind = "reference_corpus"
    report["execution_subject"] = {
        "kind": subject_kind,
        "implementation_id": str(metadata.get("implementation_id", "unknown")),
        "implementation_version": str(
            metadata.get("implementation_version", "unknown")
        ),
        "implementation_digest": (
            str(metadata.get("implementation_digest"))
            if isinstance(metadata.get("implementation_digest"), str)
            and DIGEST_RE.fullmatch(str(metadata["implementation_digest"]))
            else "sha256:" + "0" * 64
        ),
    }

    expected_ids = Counter(mandatory_case_ids(catalog, mode, handler))
    actual_ids = Counter(item["case_id"] for item in case_results)
    coverage_ok = actual_ids == expected_ids
    if not coverage_ok:
        failures.append(
            {
                "test_id": "EVIDENCE-CASE-COVERAGE-01",
                "message": (
                    "mandatory case coverage mismatch; "
                    f"missing={sorted((expected_ids - actual_ids).elements())}; "
                    f"duplicate_or_unknown={sorted((actual_ids - expected_ids).elements())}"
                ),
            }
        )
    report["degraded_reasons"] = sorted(set(report["degraded_reasons"]))
    report["skipped_checks"] = sorted(set(report["skipped_checks"]))
    report["passed"] = not failures
    eligible = (
        mode == record.execution_mode
        and report["passed"]
        and coverage_ok
        and subject_kind == "external_implementation"
        and report["degraded"] is False
        and report["degraded_reasons"] == []
        and report["skipped_checks"] == []
        and report["generated_artifacts"]
        and all(
            artifact["content_digest"] == artifact["repeat_content_digest"]
            for artifact in report["generated_artifacts"]
        )
    )
    report["compatibility_marks"] = [record.expected_mark] if eligible else []
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cmd-json", required=True)
    parser.add_argument("--target", default=TARGET_KEY)
    parser.add_argument("--mode", default="full-capability")
    parser.add_argument(
        "--out",
        default="out/evidence/session-state-projection-v1.json",
    )
    parser.add_argument("--timeout", type=float, default=20)
    parser.add_argument("--simulate-no-jsonschema", action="store_true")
    parser.add_argument("--simulate-no-crypto", action="store_true")
    parser.add_argument("--timestamp")
    args = parser.parse_args()
    command = json.loads(args.cmd_json)
    if not isinstance(command, list) or not all(
        isinstance(item, str) and item for item in command
    ):
        parser.error("--cmd-json must be a JSON array of non-empty strings")
    report = run_evidence(
        command,
        target=args.target,
        mode=args.mode,
        timeout_seconds=args.timeout,
        simulate_no_jsonschema=args.simulate_no_jsonschema,
        simulate_no_crypto=args.simulate_no_crypto,
        timestamp=args.timestamp,
    )
    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    label = (
        "PASSED"
        if report["passed"] and not report["degraded"]
        else "PASSED (DEGRADED)"
        if report["passed"]
        else "FAILED"
    )
    print(
        f"External evidence {label}: {args.target}; mode={args.mode}; "
        f"mark_count={len(report['compatibility_marks'])}; out={args.out}"
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
