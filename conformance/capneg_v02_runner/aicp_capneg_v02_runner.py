#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


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


def _run_case(
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
) -> tuple[list[dict[str, Any]], bool]:
    case_id = str(case.get("id"))
    messages = case.get("messages")
    if not isinstance(messages, list) or not all(
        isinstance(message, dict) for message in messages
    ):
        return [
            _failure(
                "RUNNER-CASE-SHAPE-01",
                "case messages must be an array of objects",
                case_id=case_id,
            )
        ], False
    expected_observations = case.get(
        "expected_error_observations",
        case.get("expected", {}).get("error_observations", []),
    )
    expected_state = case.get(
        "expected_final_state",
        case.get("expected", {}).get("final_state", {}),
    )
    invalid, transcript_issues = validate_messages(
        messages,
        message_schema=message_schema,
        capneg_schema=capneg_schema,
        projection_schema=projection_schema,
        core_payload_schema=core_payload_schema,
        core_contract_schema=core_contract_schema,
        registered_messages=registered_messages,
        key_map=key_map,
        jsonschema_available=jsonschema_available,
        crypto_available=crypto_available,
    )
    failures: list[dict[str, Any]] = []
    snapshot = reduce_capneg_v02(
        messages,
        rules=rules,
        registered_reason_codes=registered_reasons,
        key_map=key_map,
        crypto_available=crypto_available,
        invalid_messages=invalid,
    )
    observed_issues = list(snapshot["issues"])
    observed_issues.extend(transcript_issues)
    for index, message in enumerate(messages):
        if index in invalid:
            continue
        if message.get("message_type") == "STATE_SYNC_RESPONSE":
            observed_issues.extend(
                validate_session_state_projection_v2(
                    message,
                    messages,
                    index,
                    registered_extensions=registered_extensions,
                    rules=rules,
                    registered_reason_codes=registered_reasons,
                    key_map=key_map,
                    crypto_available=crypto_available,
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
    observed = normalize_observations(observed_issues)
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
                "exact final CAPNEG state differs from the generated expectation",
                case_id=case_id,
            )
        )
    return failures, True


def run_suite(
    suite_path: Path,
    *,
    simulate_no_jsonschema: bool = False,
    simulate_no_crypto: bool = False,
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

    failures: list[dict[str, Any]] = []
    positive_count = 0
    negative_count = 0
    for catalog_ref in suite.get("case_catalogs", []):
        catalog = _load(ROOT / catalog_ref)
        for case in catalog.get("cases", []):
            case_id = str(case.get("id"))
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
            case_failures, _ran = _run_case(
                case,
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
            )
            failures.extend(case_failures)

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
