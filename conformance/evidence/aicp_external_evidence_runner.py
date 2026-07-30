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
IUT_DIR = ROOT / "conformance" / "iut"
RUNNER_DIR = ROOT / "conformance" / "runner"
REF_PY = ROOT / "reference" / "python"
for path in (EVIDENCE_DIR, IUT_DIR, RUNNER_DIR, REF_PY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from _runner_context import build_validator  # noqa: E402
from aicp_iut_runner import IUTProtocolError, invoke_adapter  # noqa: E402
from aicp_ref.hashing import object_hash  # noqa: E402
from aicp_ref.signatures import signature_verifier_available  # noqa: E402
from target_catalog import (  # noqa: E402
    EXPECTED_MARK,
    REPORT_SCHEMA_PATH,
    TARGET_CATALOG_PATH,
    TARGET_ID,
    TARGET_KEY,
    TARGET_VERSION,
    TARGETS_PATH,
    TCK_RELEASES_PATH,
    TCK_RELEASE_ID,
    canonical_digest,
    consumer_cases,
    expected_input_artifacts,
    expected_suite_records,
    file_digest,
    load_json,
    load_jsonl,
    mandatory_case_ids,
    release_record,
    target_catalog,
    target_record,
    validate_release_registry,
    validate_target_catalog,
    validate_target_registry,
)


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
    catalog: dict[str, Any],
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
    for vector_entry in catalog["canonicalization_vectors"]:
        vector = load_json(ROOT / vector_entry["path"])
        append(
            "canonicalize_hash",
            {
                "object_type": vector["object_type"],
                "object": vector["object"],
            },
            {
                "kind": "canonicalize",
                "case_id": vector_entry["case_id"],
                "expected": vector,
            },
        )

    producer = catalog["producer_case"]
    transcript = load_jsonl(ROOT / producer["fixture"])
    state_response = transcript[-1]
    context = state_response["payload"]["session_state"]
    semantic_input = {
        "target_capability": TARGET_KEY,
        "transcript": transcript,
        "context": context,
        "deterministic_seed": producer["deterministic_seed"],
    }
    append(
        "project_session_state",
        semantic_input,
        {"kind": "producer", **producer},
    )
    append(
        "project_session_state",
        semantic_input,
        {"kind": "producer_repeat", **producer},
    )
    for case in consumer_cases(catalog, mode):
        append(
            "validate_transcript",
            {
                "target_capability": TARGET_KEY,
                "transcript": load_jsonl(ROOT / case["fixture"]),
                "runtime_options": {},
            },
            {"kind": "consumer", **case},
        )
    append("describe", {}, {"kind": "describe_end"})
    return requests, checks


def _projection_schema_validator(
    *,
    simulate_no_jsonschema: bool,
) -> Any | None:
    if simulate_no_jsonschema:
        return None
    schema_path = ROOT / "schemas/extensions/ext-object-resync-payloads.schema.json"
    schema = load_json(schema_path)
    wrapper = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$defs": schema["$defs"],
        "$ref": "#/$defs/SessionStateProjectionV1",
    }
    return build_validator(wrapper, schema_path)


def _producer_errors(
    result: dict[str, Any],
    check: dict[str, Any],
    validator: Any | None,
) -> list[str]:
    errors: list[str] = []
    projection = result.get("projection")
    projection_hash = result.get("session_state_hash")
    if not isinstance(projection, dict):
        return ["producer result must contain projection object"]
    if validator is None:
        errors.append("projection schema validation unavailable")
    else:
        for issue in sorted(
            validator.iter_errors(projection),
            key=lambda item: list(item.path),
        ):
            path = "/".join(str(part) for part in issue.path)
            errors.append(f"projection schema error at /{path}: {issue.message}")
    if projection != check["expected_projection"]:
        errors.append("producer projection does not equal the reviewed portable projection")
    if projection.get("session_id") != "sSP1":
        errors.append("producer projection session binding mismatch")
    if projection.get("contract_id") != "cSP1":
        errors.append("producer projection contract binding mismatch")
    computed = object_hash("session_state_projection", projection)
    if projection_hash != computed:
        errors.append("producer projection hash does not match independently recomputed hash")
    if projection_hash != check["expected_projection_hash"]:
        errors.append("producer projection hash does not equal reviewed expectation")
    return errors


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


def _describe_errors(
    metadata: dict[str, Any],
    *,
    release: dict[str, Any],
    inputs: list[dict[str, str]],
    suites: list[dict[str, str]],
) -> list[str]:
    errors: list[str] = []
    required = [
        "implementation_kind",
        "implementation_id",
        "implementation_version",
        "implementation_digest",
        "supported_aicp_capabilities",
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
    expected_capability = {
        "capability_id": TARGET_ID,
        "capability_version": TARGET_VERSION,
    }
    capabilities = metadata.get("supported_aicp_capabilities")
    if not isinstance(capabilities, list) or expected_capability not in capabilities:
        errors.append("target capability is not explicitly declared")

    claim_checks = {
        "claimed_tck_release": TCK_RELEASE_ID,
        "claimed_runner_digest": release["runner_bundle"]["digest"],
        "claimed_suite_digest": suites[0]["suite_digest"],
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
    mode: str,
    release: dict[str, Any],
    catalog_digest: str,
    inputs: list[dict[str, str]],
    suites: list[dict[str, str]],
    timestamp: str,
) -> dict[str, Any]:
    return {
        "report_format_version": "2.0",
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
            "version": "2.0",
            "source_revision": release["runner_bundle"]["digest"],
        },
        "tck_release": {
            "release_id": release["release_id"],
            "registry_digest": file_digest(TCK_RELEASES_PATH),
            "target_registry_digest": release["target_registry"][
                "content_digest"
            ],
            "target_catalog_digest": catalog_digest,
            "report_schema_digest": release["report_schema"]["content_digest"],
            "runner_bundle_digest": release["runner_bundle"]["digest"],
        },
        "target": {
            "kind": "capability",
            "target_id": TARGET_ID,
            "target_version": TARGET_VERSION,
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
    if target != TARGET_KEY:
        raise ValueError(f"unregistered or unimplemented evidence target: {target}")
    if mode not in {"full-capability", "smoke"}:
        raise ValueError("execution mode must be full-capability or smoke")
    target_record(target)
    catalog = target_catalog()
    release = release_record()
    inputs = expected_input_artifacts(release)
    suites = expected_suite_records(release)
    catalog_digest = file_digest(TARGET_CATALOG_PATH)
    report = _base_report(
        mode=mode,
        release=release,
        catalog_digest=catalog_digest,
        inputs=inputs,
        suites=suites,
        timestamp=timestamp
        or datetime.now(timezone.utc).isoformat(),
    )
    failures = report["failures"]
    case_results = report["case_results"]

    def record(
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
        *validate_target_registry(),
        *validate_target_catalog(catalog),
    ]
    record(
        "EVIDENCE-TARGET-CATALOG-01",
        not catalog_errors,
        "registered target and owning-suite catalog are complete"
        if not catalog_errors
        else "; ".join(catalog_errors),
    )
    release_errors = validate_release_registry()
    record(
        "EVIDENCE-TCK-PROVENANCE-01",
        not release_errors,
        "evidence TCK provenance matches current bytes"
        if not release_errors
        else "; ".join(release_errors),
    )

    validator = _projection_schema_validator(
        simulate_no_jsonschema=simulate_no_jsonschema
    )
    if validator is None:
        report["degraded"] = True
        report["degraded_reasons"].append(
            "jsonschema dependency unavailable; producer schema validation could not execute"
        )
        report["skipped_checks"].append(
            "EVIDENCE-PRODUCER-SCHEMA-01"
        )
    crypto_available = signature_verifier_available() and not simulate_no_crypto
    if not crypto_available:
        report["degraded"] = True
        report["degraded_reasons"].append(
            "Ed25519 verifier unavailable; mandatory evidence dependency probe did not complete"
        )
        report["skipped_checks"].append(
            "EVIDENCE-CRYPTO-DEPENDENCY-01"
        )

    requests, checks = build_execution_plan(catalog, mode)
    try:
        responses, stderr_text = invoke_adapter(
            command,
            requests,
            timeout_seconds=timeout_seconds,
            max_stdout_bytes=max_stdout_bytes,
            max_stderr_bytes=max_stderr_bytes,
        )
    except IUTProtocolError as exc:
        failures.append(
            {
                "test_id": "EVIDENCE-ADAPTER-PROTOCOL-01",
                "message": str(exc),
            }
        )
        report["passed"] = False
        return report
    report["adapter_stderr"] = stderr_text

    first_metadata: dict[str, Any] | None = None
    final_metadata: dict[str, Any] | None = None
    producer_result: dict[str, Any] | None = None
    producer_digest: str | None = None
    producer_case_result: dict[str, Any] | None = None
    for response, check in zip(responses, checks):
        result = response["result"]
        kind = check["kind"]
        if kind == "describe_start":
            first_metadata = result
            errors = _describe_errors(
                result,
                release=release,
                inputs=inputs,
                suites=suites,
            )
            record(
                "EVIDENCE-DESCRIBE-START-01",
                not errors,
                "implementation metadata is complete and provenance claims are consistent"
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
            record(
                check["case_id"],
                passed,
                "canonical bytes and hash match"
                if passed
                else "canonical bytes or hash mismatch",
            )
        elif kind in {"producer", "producer_repeat"}:
            errors = _producer_errors(result, check, validator)
            digest = canonical_digest(result)
            if kind == "producer":
                producer_result = result
                producer_digest = digest
                record(
                    check["case_id"],
                    not errors,
                    "producer projection passed independent schema, binding, field, and hash checks"
                    if not errors
                    else "; ".join(errors),
                )
                producer_case_result = case_results[-1]
            else:
                if producer_result is None or producer_digest is None:
                    errors.append("first producer result is missing")
                elif result != producer_result or digest != producer_digest:
                    errors.append(
                        "producer repeat changed canonical content digest"
                    )
                if producer_case_result is not None and errors:
                    producer_case_result["passed"] = False
                    producer_case_result["message"] += "; " + "; ".join(errors)
                    if not any(
                        item["test_id"] == check["case_id"]
                        for item in failures
                    ):
                        failures.append(
                            {
                                "test_id": check["case_id"],
                                "message": producer_case_result["message"],
                            }
                        )
                if (
                    producer_result is not None
                    and producer_digest is not None
                ):
                    report["generated_artifacts"] = [
                        {
                            "artifact_id": check["case_id"],
                            "content_digest": producer_digest,
                            "repeat_content_digest": digest,
                            "content": producer_result,
                        }
                    ]
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
                "error_codes": check["expected_error_codes"],
                "degraded": check["expected_degraded"],
                "degraded_reasons": check[
                    "expected_degraded_reasons"
                ],
                "skipped_checks": check["expected_skipped_checks"],
            }
            passed = not shape_errors
            passed = passed and observation["accepted"] is expected["accepted"]
            passed = passed and actual_codes == expected["error_codes"]
            passed = passed and observation["degraded"] is expected["degraded"]
            passed = (
                passed
                and observation["degraded_reasons"]
                == expected["degraded_reasons"]
            )
            passed = (
                passed
                and observation["skipped_checks"]
                == expected["skipped_checks"]
            )
            detail = (
                "consumer observation exactly matches reviewed expectation"
                if passed
                else (
                    f"observed accepted={observation['accepted']}, "
                    f"errors={actual_codes}, degraded={observation['degraded']}, "
                    f"reasons={observation['degraded_reasons']}, "
                    f"skips={observation['skipped_checks']}; expected={expected}"
                    + (
                        "; " + "; ".join(shape_errors)
                        if shape_errors
                        else ""
                    )
                )
            )
            record(
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
        record(
            "EVIDENCE-DESCRIBE-STABILITY-01",
            False,
            "implementation metadata changed during execution",
        )
    else:
        record(
            "EVIDENCE-DESCRIBE-STABILITY-01",
            True,
            "implementation metadata remained immutable",
        )
    expected_capability = {
        "capability_id": TARGET_ID,
        "capability_version": TARGET_VERSION,
    }
    capabilities = (
        first_metadata.get("supported_aicp_capabilities")
        if isinstance(first_metadata, dict)
        else None
    )
    support_ok = (
        isinstance(capabilities, list)
        and expected_capability in capabilities
    )
    record(
        "EVIDENCE-TARGET-SUPPORT-01",
        support_ok,
        "adapter explicitly declares exact projection v1 capability"
        if support_ok
        else "adapter does not declare exact projection v1 capability",
    )

    metadata = first_metadata or {}
    subject_kind = metadata.get("implementation_kind")
    if subject_kind not in {
        "external_implementation",
        "reference_corpus",
    }:
        subject_kind = "reference_corpus"
    report["execution_subject"] = {
        "kind": subject_kind,
        "implementation_id": str(
            metadata.get("implementation_id", "unknown")
        ),
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

    expected_ids = Counter(mandatory_case_ids(catalog, mode))
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
    report["degraded_reasons"] = sorted(
        set(report["degraded_reasons"])
    )
    report["skipped_checks"] = sorted(set(report["skipped_checks"]))
    report["passed"] = not failures
    eligible = (
        mode == "full-capability"
        and report["passed"]
        and coverage_ok
        and subject_kind == "external_implementation"
        and report["degraded"] is False
        and report["degraded_reasons"] == []
        and report["skipped_checks"] == []
        and report["generated_artifacts"]
        and report["generated_artifacts"][0]["content_digest"]
        == report["generated_artifacts"][0]["repeat_content_digest"]
    )
    report["compatibility_marks"] = [EXPECTED_MARK] if eligible else []
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cmd-json", required=True)
    parser.add_argument("--target", default=TARGET_KEY)
    parser.add_argument(
        "--mode",
        choices=["full-capability", "smoke"],
        default="full-capability",
    )
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
