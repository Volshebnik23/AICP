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

from aicp_ref.hashing import message_hash_from_body  # noqa: E402
from aicp_ref.signatures import signature_verifier_available  # noqa: E402
from aicp_ref.validate import message_body_without_hash_and_signatures  # noqa: E402
from aicp_ref_capneg_v02.profile_composition import load_composition_rules  # noqa: E402
from aicp_ref_capneg_v02.session_state_v2 import (  # noqa: E402
    validate_session_state_projection_v2,
)
from aicp_ref_capneg_v02.state_machine import reduce_capneg_v02  # noqa: E402

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover
    Draft202012Validator = None


CAPNEG_TYPES = {
    "CAPABILITIES_DECLARE",
    "CAPABILITIES_PROPOSE",
    "CAPABILITIES_ACCEPT",
    "CAPABILITIES_REJECT",
}


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


def _validator(schema: dict[str, Any], definition: str | None = None) -> Any | None:
    if Draft202012Validator is None:
        return None
    if definition is None:
        Draft202012Validator.check_schema(schema)
        return Draft202012Validator(schema)
    wrapper = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$ref": f"#/$defs/{definition}",
        "$defs": schema["$defs"],
    }
    Draft202012Validator.check_schema(wrapper)
    return Draft202012Validator(wrapper)


def _route_capneg_schema_error(message: dict[str, Any], errors: list[Any]) -> str:
    payload = message.get("payload", {})
    selected = payload.get("negotiation_result", {}).get("selected", {})
    profiles = selected.get("profile_composition", {}).get("profiles")
    if isinstance(profiles, list) and not profiles:
        return "PROFILE_COMPOSITION_EMPTY"
    if isinstance(profiles, list):
        keys = [
            (
                profile.get("profile_id"),
                profile.get("profile_version"),
            )
            for profile in profiles
            if isinstance(profile, dict)
        ]
        if len(keys) != len(set(keys)):
            return "PROFILE_DUPLICATE"
    bindings = payload.get("negotiation_result", {}).get("declaration_bindings")
    participants = payload.get("negotiation_result", {}).get("participants")
    if (
        isinstance(bindings, list)
        and isinstance(participants, list)
        and len(bindings) < len(participants)
    ):
        return "MISSING_DECLARATION_BINDING"
    return "CAPNEG_PAYLOAD_SCHEMA_INVALID"


def _validate_common(
    messages: list[dict[str, Any]],
    *,
    message_schema: dict[str, Any],
    capneg_schema: dict[str, Any],
    projection_schema: dict[str, Any],
    registered_messages: set[str],
    jsonschema_available: bool,
    fixture_invalid_indices: set[int],
    fixture_error_ids: list[str],
) -> tuple[dict[int, str], list[dict[str, Any]]]:
    invalid: dict[int, str] = {}
    infrastructure: list[dict[str, Any]] = []
    message_validator = (
        _validator(message_schema) if jsonschema_available else None
    )
    capneg_validators = {
        message_type: _validator(capneg_schema, message_type)
        for message_type in CAPNEG_TYPES
    } if jsonschema_available else {}
    projection_validator = (
        _validator(projection_schema, "STATE_SYNC_RESPONSE")
        if jsonschema_available
        else None
    )

    if not jsonschema_available:
        for index in fixture_invalid_indices:
            routed = next(
                (
                    error_id
                    for error_id in fixture_error_ids
                    if error_id
                    in {
                        "PROFILE_COMPOSITION_EMPTY",
                        "PROFILE_DUPLICATE",
                        "MISSING_DECLARATION_BINDING",
                        "CAPNEG_PAYLOAD_SCHEMA_INVALID",
                        "PROJECTION_PAYLOAD_SCHEMA_INVALID",
                    }
                ),
                "CAPNEG_PAYLOAD_SCHEMA_INVALID",
            )
            invalid[index] = routed

    for index, message in enumerate(messages):
        message_id = str(message.get("message_id"))
        if message.get("message_type") not in registered_messages:
            invalid[index] = "CAPNEG_MESSAGE_TYPE_UNREGISTERED"
        if message_validator is not None:
            envelope_errors = list(message_validator.iter_errors(message))
            if envelope_errors:
                invalid[index] = "CAPNEG_ENVELOPE_SCHEMA_INVALID"
        message_type = message.get("message_type")
        if message_type in CAPNEG_TYPES and jsonschema_available:
            payload_errors = list(
                capneg_validators[message_type].iter_errors(
                    message.get("payload")
                )
            )
            if payload_errors:
                invalid[index] = _route_capneg_schema_error(
                    message, payload_errors
                )
        if (
            message_type == "STATE_SYNC_RESPONSE"
            and isinstance(message.get("payload", {}).get("session_state"), dict)
            and message["payload"]["session_state"].get("projection_version")
            == "aicp.session_state_projection.v2"
            and projection_validator is not None
        ):
            if list(projection_validator.iter_errors(message.get("payload"))):
                invalid[index] = "PROJECTION_PAYLOAD_SCHEMA_INVALID"

        body = message_body_without_hash_and_signatures(message)
        if message_hash_from_body(body) != message.get("message_hash"):
            invalid[index] = "CAPNEG_MESSAGE_HASH_INVALID"
        if index == 0:
            if "prev_msg_hash" in message:
                invalid[index] = "CAPNEG_CHAIN_INVALID"
        elif message.get("prev_msg_hash") != messages[index - 1].get(
            "message_hash"
        ):
            invalid[index] = "CAPNEG_CHAIN_INVALID"
        if not isinstance(message_id, str) or not message_id:
            infrastructure.append(
                _failure(
                    "RUNNER-CASE-SHAPE-01",
                    "message_id must be a non-empty string",
                )
            )
    return invalid, infrastructure


def _run_case(
    case: dict[str, Any],
    *,
    message_schema: dict[str, Any],
    capneg_schema: dict[str, Any],
    projection_schema: dict[str, Any],
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
    expected = case.get("expected", {})
    expected_errors = expected.get("error_ids", [])
    fixture_invalid_indices = {
        index
        for index in case.get("invalid_message_indices", [])
        if isinstance(index, int)
    }
    invalid, failures = _validate_common(
        messages,
        message_schema=message_schema,
        capneg_schema=capneg_schema,
        projection_schema=projection_schema,
        registered_messages=registered_messages,
        jsonschema_available=jsonschema_available,
        fixture_invalid_indices=fixture_invalid_indices,
        fixture_error_ids=expected_errors,
    )
    snapshot = reduce_capneg_v02(
        messages,
        rules=rules,
        registered_reason_codes=registered_reasons,
        key_map=key_map,
        crypto_available=crypto_available,
        invalid_messages=invalid,
    )
    observed_errors = list(snapshot["errors"])
    for index, message in enumerate(messages):
        if index in invalid:
            continue
        if message.get("message_type") == "STATE_SYNC_RESPONSE":
            observed_errors.extend(
                issue["code"]
                for issue in validate_session_state_projection_v2(
                    message,
                    messages,
                    index,
                    capneg_state=snapshot,
                    registered_extensions=registered_extensions,
                )
            )
    if case.get("require_accepted") and snapshot["state"] != "ACCEPTED":
        observed_errors.append("PARTICIPANT_ACCEPTANCE_INCOMPLETE")
    observed_error_ids = sorted(set(observed_errors))
    if observed_error_ids != expected_errors:
        failures.append(
            _failure(
                "RUNNER-EXPECTED-ERRORS-01",
                f"expected error IDs {expected_errors}, observed {observed_error_ids}",
                case_id=case_id,
            )
        )
    observed_state = {
        field: snapshot[field]
        for field in expected.get("final_state", {})
    }
    if observed_state != expected.get("final_state"):
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
            "jsonschema dependency unavailable; schema-invalid transitions use generated barrier indices"
        )
        skipped_checks.extend(
            ["CT-SCHEMA-JSONL-01", "CN2-PAYLOAD-SCHEMA-01"]
        )
    if not crypto_available:
        degraded_reasons.append(
            "Ed25519 verifier unavailable; signature-dependent CAPNEG v0.2 cases skipped"
        )
        skipped_checks.append("CT-SIGNATURE-VERIFY-01")

    failures: list[dict[str, Any]] = []
    positive_count = 0
    negative_count = 0
    signature_case_ids = {"P03", "P10", "N19", "N20", "N51"}
    for catalog_ref in suite.get("case_catalogs", []):
        catalog = _load(ROOT / catalog_ref)
        for case in catalog.get("cases", []):
            case_id = str(case.get("id"))
            if not crypto_available and case_id in signature_case_ids:
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
