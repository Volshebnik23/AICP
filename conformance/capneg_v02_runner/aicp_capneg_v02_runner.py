#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[2]
REFERENCE_PYTHON = ROOT / "reference/python"
if str(REFERENCE_PYTHON) not in sys.path:
    sys.path.insert(0, str(REFERENCE_PYTHON))

from aicp_ref.signatures import signature_verifier_available  # noqa: E402
from aicp_ref_capneg_v02.profile_composition import load_composition_rules  # noqa: E402
from aicp_ref_capneg_v02.session_state_v2 import (  # noqa: E402
    validate_session_state_projection_v2,
)
from aicp_ref_capneg_v02.state_machine import reduce_capneg_v02  # noqa: E402
from validation import (  # noqa: E402
    case_requires_crypto,
    normalize_observations,
    validate_messages,
)

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover
    Draft202012Validator = None


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_without_duplicate_keys(path: Path) -> Any:
    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"{path}: duplicate JSON object key {key!r}")
            result[key] = value
        return result

    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=unique_object,
    )


def _failure(
    test_id: str,
    detail: str,
    *,
    case_id: str | None = None,
    message_id: str | None = None,
) -> dict[str, Any]:
    return {
        "test_id": test_id,
        "detail": detail,
        "case_id": case_id,
        "message_id": message_id,
    }


def execute_case(
    case: dict[str, Any],
    *,
    message_schema: dict[str, Any],
    capneg_schema: dict[str, Any],
    projection_schema: dict[str, Any],
    core_payload_schema: dict[str, Any],
    core_contract_schema: dict[str, Any],
    rules: dict[str, Any],
    registered_messages: set[str],
    registered_extensions: set[str],
    registered_reasons: set[str],
    key_map: dict[str, Any],
    jsonschema_available: bool,
    crypto_available: bool,
    reducer_function: Callable[..., dict[str, Any]] = reduce_capneg_v02,
    projection_validator_function: Callable[
        ..., list[dict[str, Any]]
    ] = validate_session_state_projection_v2,
    message_validity_validator: Callable[
        ..., tuple[dict[int, list[dict[str, Any]]], list[dict[str, Any]]]
    ] = validate_messages,
    observation_normalizer: Callable[
        [list[dict[str, Any]]], list[dict[str, Any]]
    ] = normalize_observations,
) -> dict[str, Any]:
    case_id = str(case.get("id"))
    messages = case.get("messages")
    if not isinstance(messages, list) or not all(
        isinstance(message, dict) for message in messages
    ):
        return {
            "ran": False,
            "failures": [
                _failure(
                    "RUNNER-CASE-SHAPE-01",
                    "case messages must be an array of objects",
                    case_id=case_id,
                )
            ],
            "observations": [],
            "snapshot": {},
        }
    case_execution = case.get("execution_metadata", {})
    effective_crypto_available = (
        False
        if isinstance(case_execution, dict)
        and case_execution.get("crypto_available") is False
        else crypto_available
    )
    invalid, transcript_issues = message_validity_validator(
        messages,
        message_schema=message_schema,
        capneg_schema=capneg_schema,
        projection_schema=projection_schema,
        core_payload_schema=core_payload_schema,
        core_contract_schema=core_contract_schema,
        registered_messages=registered_messages,
        key_map=key_map,
        jsonschema_available=jsonschema_available,
        crypto_available=effective_crypto_available,
    )
    snapshot = reducer_function(
        messages,
        rules=rules,
        registered_reason_codes=registered_reasons,
        key_map=key_map,
        crypto_available=effective_crypto_available,
        invalid_messages=invalid,
    )
    observed_issues = list(snapshot["issues"])
    observed_issues.extend(transcript_issues)
    for index, message in enumerate(messages):
        if index in invalid:
            continue
        if message.get("message_type") == "STATE_SYNC_RESPONSE":
            observed_issues.extend(
                projection_validator_function(
                    message,
                    messages,
                    index,
                    registered_extensions=registered_extensions,
                    rules=rules,
                    registered_reason_codes=registered_reasons,
                    key_map=key_map,
                    crypto_available=effective_crypto_available,
                    invalid_messages=invalid,
                )
            )
    if case.get("require_accepted") and snapshot["state"] != "ACCEPTED":
        observed_issues.append(
            {
                "code": "PARTICIPANT_ACCEPTANCE_INCOMPLETE",
                "message_index": None,
                "message_id": None,
                "detail": "the transcript did not reach fully accepted CAPNEG state",
            }
        )
    observed = observation_normalizer(observed_issues)
    return {
        "ran": True,
        "failures": [],
        "observations": observed,
        "snapshot": snapshot,
    }


def compare_case_to_oracle(
    case: dict[str, Any],
    execution: dict[str, Any],
    expectation: dict[str, Any],
) -> list[dict[str, Any]]:
    case_id = str(case.get("id"))
    expected_observations = expectation["expected_error_observations"]
    expected_state = expectation["expected_final_state"]
    observed = execution["observations"]
    snapshot = execution["snapshot"]
    failures: list[dict[str, Any]] = list(execution.get("failures", []))
    if not execution.get("ran", False):
        return failures
    if observed != expected_observations:
        failures.append(
            _failure(
                "RUNNER-EXPECTED-ERRORS-01",
                "exact structured observations differ: "
                f"expected {expected_observations}, observed {observed}",
                case_id=case_id,
            )
        )
    observed_state = {
        field: snapshot[field]
        for field in expected_state
    }
    if observed_state != expected_state:
        failures.append(
            _failure(
                "RUNNER-EXPECTED-STATE-01",
                "exact final CAPNEG state differs: "
                f"expected {expected_state}, observed {observed_state}",
                case_id=case_id,
            )
        )
    return failures


def evaluate_case(
    case: dict[str, Any],
    *,
    oracle_cases: dict[str, Any],
    **execution_dependencies: Any,
) -> dict[str, Any]:
    case_id = str(case.get("id"))
    oracle_case_id = case.get("oracle_case_id")
    if not isinstance(oracle_case_id, str) or not oracle_case_id:
        return {
            "passed": False,
            "ran": False,
            "failures": [
                _failure(
                    "RUNNER-ORACLE-REFERENCE-01",
                    "case must identify one non-empty oracle_case_id",
                    case_id=case_id,
                )
            ],
            "observations": [],
            "snapshot": {},
        }
    expectation = oracle_cases.get(oracle_case_id)
    if not isinstance(expectation, dict):
        return {
            "passed": False,
            "ran": False,
            "failures": [
                _failure(
                    "RUNNER-ORACLE-MISSING-01",
                    f"oracle entry {oracle_case_id!r} does not resolve",
                    case_id=case_id,
                )
            ],
            "observations": [],
            "snapshot": {},
        }
    execution = execute_case(case, **execution_dependencies)
    failures = compare_case_to_oracle(case, execution, expectation)
    return {
        **execution,
        "passed": not failures,
        "failures": failures,
        "oracle_case_id": oracle_case_id,
    }


def _resolved_catalog_cases(
    catalog_ref: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    catalog = _load(ROOT / catalog_ref)
    cases: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    for entry in catalog.get("cases", []):
        if not isinstance(entry, dict):
            failures.append(
                _failure(
                    "RUNNER-CASE-SHAPE-01",
                    f"{catalog_ref}: every case entry must be an object",
                )
            )
            continue
        source_catalog = entry.get("source_catalog")
        if not isinstance(source_catalog, str):
            cases.append(entry)
            continue
        source_case_id = entry.get("case_id")
        source = _load(ROOT / source_catalog)
        matches = [
            candidate
            for candidate in source.get("cases", [])
            if isinstance(candidate, dict)
            and candidate.get("id") == source_case_id
        ]
        if len(matches) != 1:
            failures.append(
                _failure(
                    "RUNNER-CASE-REFERENCE-01",
                    f"{catalog_ref}: {source_catalog}#{source_case_id} resolved {len(matches)} times",
                    case_id=str(entry.get("id")),
                )
            )
            continue
        resolved = dict(matches[0])
        if entry.get("oracle_case_id") != resolved.get("oracle_case_id"):
            failures.append(
                _failure(
                    "RUNNER-ORACLE-REFERENCE-01",
                    f"{catalog_ref}: manifest oracle_case_id must equal the source case reference",
                    case_id=str(entry.get("id")),
                )
            )
            continue
        cases.append(resolved)
    return cases, failures


def run_suite(
    suite_path: Path,
    *,
    simulate_no_jsonschema: bool = False,
    simulate_no_crypto: bool = False,
    reducer_function: Callable[..., dict[str, Any]] = reduce_capneg_v02,
    projection_validator_function: Callable[
        ..., list[dict[str, Any]]
    ] = validate_session_state_projection_v2,
    message_validity_validator: Callable[
        ..., tuple[dict[int, list[dict[str, Any]]], list[dict[str, Any]]]
    ] = validate_messages,
    observation_normalizer: Callable[
        [list[dict[str, Any]]], list[dict[str, Any]]
    ] = normalize_observations,
    case_ids: set[str] | None = None,
) -> dict[str, Any]:
    suite = _load(suite_path)
    message_schema = _load(ROOT / suite["schema_ref"])
    capneg_schema_ref = suite.get(
        "capneg_payload_schema_ref", suite.get("payload_schema_ref")
    )
    capneg_schema = _load(ROOT / capneg_schema_ref)
    projection_schema = _load(
        ROOT / "schemas/extensions/session-state-projection-v2.schema.json"
    )
    core_payload_schema = _load(
        ROOT / "schemas/core/aicp-core-payloads.schema.json"
    )
    core_contract_schema = _load(
        ROOT / "schemas/core/aicp-core-contract.schema.json"
    )
    rules = _load(ROOT / suite["composition_rules_ref"])
    registered_messages = {
        entry["id"] for entry in _load(ROOT / "registry/message_types.json")
    }
    registered_extensions = {
        entry["id"] for entry in _load(ROOT / "registry/extension_ids.json")
    }
    registered_reasons = {
        entry["id"] for entry in _load(ROOT / "registry/capneg_reason_codes.json")
    }
    key_map = _load(ROOT / "fixtures/keys/GT_public_keys.json")
    oracle_ref = suite.get("oracle_expectations_ref")
    failures: list[dict[str, Any]] = []
    if not isinstance(oracle_ref, str):
        oracle_cases: dict[str, Any] = {}
        failures.append(
            _failure(
                "RUNNER-ORACLE-REFERENCE-01",
                "suite must identify oracle_expectations_ref",
            )
        )
    else:
        try:
            oracle_document = _load_without_duplicate_keys(ROOT / oracle_ref)
            oracle_cases = oracle_document.get("cases", {})
            if not isinstance(oracle_cases, dict):
                raise ValueError("oracle cases must be an object")
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            oracle_cases = {}
            failures.append(
                _failure(
                    "RUNNER-ORACLE-LOAD-01",
                    f"failed to load unique oracle entries: {exc}",
                )
            )

    jsonschema_available = (
        Draft202012Validator is not None and not simulate_no_jsonschema
    )
    crypto_available = (
        signature_verifier_available() and not simulate_no_crypto
    )
    degraded_reasons: list[str] = []
    skipped_checks: list[str] = []
    skipped_case_ids: list[str] = []
    if not jsonschema_available:
        degraded_reasons.append(
            "jsonschema dependency unavailable; schema-dependent cases were skipped rather than inferred from fixture metadata"
        )
        skipped_checks.extend(
            ["CT-SCHEMA-JSONL-01", "CN2-PAYLOAD-SCHEMA-01"]
        )
    if not crypto_available:
        degraded_reasons.append(
            "Ed25519 verifier unavailable; content-derived signature-dependent CAPNEG v0.2 cases were skipped"
        )
        skipped_checks.append("CT-SIGNATURE-VERIFY-01")

    positive_count = 0
    negative_count = 0
    for catalog_ref in suite.get("case_catalogs", []):
        catalog_cases, catalog_failures = _resolved_catalog_cases(catalog_ref)
        failures.extend(catalog_failures)
        for case in catalog_cases:
            case_id = str(case.get("id"))
            if case_ids is not None and case_id not in case_ids:
                continue
            if not crypto_available and case_requires_crypto(case.get("messages", [])):
                skipped_case_ids.append(case_id)
                continue
            if not jsonschema_available and case.get("requires_jsonschema", False):
                skipped_case_ids.append(case_id)
                continue
            if case.get("expect_pass", True):
                positive_count += 1
            else:
                negative_count += 1
            evaluation = evaluate_case(
                case,
                oracle_cases=oracle_cases,
                message_schema=message_schema,
                capneg_schema=capneg_schema,
                projection_schema=projection_schema,
                core_payload_schema=core_payload_schema,
                core_contract_schema=core_contract_schema,
                rules=rules,
                registered_messages=registered_messages,
                registered_extensions=registered_extensions,
                registered_reasons=registered_reasons,
                key_map=key_map,
                jsonschema_available=jsonschema_available,
                crypto_available=crypto_available,
                reducer_function=reducer_function,
                projection_validator_function=projection_validator_function,
                message_validity_validator=message_validity_validator,
                observation_normalizer=observation_normalizer,
            )
            failures.extend(evaluation["failures"])

    passed = not failures
    degraded = bool(degraded_reasons or skipped_checks or skipped_case_ids)
    mark = suite.get("compatibility_mark")
    mark_eligible = passed and not degraded
    return {
        "suite_id": suite["suite_id"],
        "suite_version": suite["suite_version"],
        "capneg_version": suite.get("capneg_version"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "failures": failures,
        "positive_cases": positive_count,
        "negative_cases": negative_count,
        "compatibility_marks": (
            [mark] if mark_eligible and isinstance(mark, str) else []
        ),
        "degraded": degraded,
        "degraded_reasons": degraded_reasons,
        "skipped_checks": sorted(set(skipped_checks)),
        "skipped_case_ids": sorted(set(skipped_case_ids)),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--suite", default="conformance/extensions/CN_CAPNEG_0.2.json"
    )
    parser.add_argument(
        "--out", default="conformance/report_ext_capneg_v02.json"
    )
    parser.add_argument("--simulate-no-jsonschema", action="store_true")
    parser.add_argument("--simulate-no-crypto", action="store_true")
    args = parser.parse_args()

    report = run_suite(
        ROOT / args.suite,
        simulate_no_jsonschema=args.simulate_no_jsonschema,
        simulate_no_crypto=args.simulate_no_crypto,
    )
    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    label = (
        "FAILED"
        if not report["passed"]
        else "PASSED (DEGRADED)"
        if report["degraded"]
        else "PASSED"
    )
    print(
        f"Conformance {label}: {report['suite_id']} -> {args.out}; "
        f"positive={report['positive_cases']} negative={report['negative_cases']}"
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
