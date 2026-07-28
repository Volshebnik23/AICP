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

from aicp_ref.chain import verify_transcript_chain  # noqa: E402
from aicp_ref.validate import (  # noqa: E402
    message_body_without_hash_and_signatures,
    validate_message_signatures,
)
from aicp_ref.hashing import message_hash_from_body  # noqa: E402
from aicp_ref.signatures import signature_verifier_available  # noqa: E402
from contract_agreement_checks import run_contract_agreement_checks  # noqa: E402

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover - exercised by dependency-minimal users
    Draft202012Validator = None


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[tuple[int, dict[str, Any]]]:
    rows: list[tuple[int, dict[str, Any]]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ValueError(f"{path}: line {line_no} must be a JSON object")
            rows.append((line_no, value))
    return rows


def _failure(
    test_id: str,
    message: str,
    file: str,
    line: int | None = None,
) -> dict[str, Any]:
    return {"test_id": test_id, "message": message, "file": file, "line": line}


def _validator(schema: dict[str, Any]) -> Any | None:
    if Draft202012Validator is None:
        return None
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def _payload_validator(payload_schema: dict[str, Any], message_type: str) -> Any | None:
    definition = payload_schema.get("$defs", {}).get(message_type)
    if not isinstance(definition, dict):
        return None
    wrapper = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$ref": f"#/$defs/{message_type}",
        "$defs": payload_schema["$defs"],
    }
    return _validator(wrapper)


def _schema_failure_id(
    message: dict[str, Any],
    *,
    payload: bool,
    issue: Any | None = None,
) -> str:
    message_type = message.get("message_type")
    if payload and message_type == "CONTEXT_AMEND":
        return "CT2-CONTEXT-BINDING-01"
    if not payload and message_type == "CONTRACT_PROPOSE":
        issue_path = list(getattr(issue, "absolute_path", ()))
        issue_message = str(getattr(issue, "message", ""))
        if (
            issue_path
            and issue_path[0] == "contract_ref"
        ) or (
            not issue_path
            and "'contract_ref' is a required property" in issue_message
        ):
            return "CT2-CONTRACT-REF-01"
    return "CT-PAYLOAD-SCHEMA-01" if payload else "CT-SCHEMA-JSONL-01"


def _check_common(
    *,
    rows: list[tuple[int, dict[str, Any]]],
    transcript: dict[str, Any],
    rel_file: str,
    enabled_checks: set[str],
    message_validator: Any | None,
    payload_schema: dict[str, Any],
    key_map: dict[str, Any],
    crypto_available: bool,
) -> tuple[list[dict[str, Any]], set[int]]:
    failures: list[dict[str, Any]] = []
    messages = [message for _, message in rows]
    invalid_indices: set[int] = set()
    line_to_index = {line_no: index for index, (line_no, _) in enumerate(rows)}

    if "CT-SCHEMA-JSONL-01" in enabled_checks and message_validator is not None:
        for index, (line_no, message) in enumerate(rows):
            issues = sorted(
                message_validator.iter_errors(message),
                key=lambda item: (list(item.absolute_path), item.message),
            )
            if issues:
                invalid_indices.add(index)
            for issue in issues:
                failures.append(
                    _failure(
                        _schema_failure_id(
                            message, payload=False, issue=issue
                        ),
                        issue.message,
                        rel_file,
                        line_no,
                    )
                )

    if "CT-PAYLOAD-SCHEMA-01" in enabled_checks:
        for index, (line_no, message) in enumerate(rows):
            message_type = message.get("message_type")
            if not isinstance(message_type, str):
                continue
            validator = _payload_validator(payload_schema, message_type)
            if validator is None:
                continue
            issues = sorted(
                validator.iter_errors(message.get("payload")),
                key=lambda item: (list(item.absolute_path), item.message),
            )
            if issues:
                invalid_indices.add(index)
            for issue in issues:
                failures.append(
                    _failure(
                        _schema_failure_id(
                            message, payload=True, issue=issue
                        ),
                        issue.message,
                        rel_file,
                        line_no,
                    )
                )

    if "CT-MESSAGE-TYPE-REGISTRY-01" in enabled_checks:
        allowed = {
            "CONTRACT_PROPOSE",
            "CONTRACT_ACCEPT",
            "CONTEXT_AMEND",
            "ATTEST_ACTION",
            "RESOLVE_CONFLICT",
            "ERROR",
        }
        for index, (line_no, message) in enumerate(rows):
            if message.get("message_type") not in allowed:
                invalid_indices.add(index)
                failures.append(
                    _failure(
                        "CT-MESSAGE-TYPE-REGISTRY-01",
                        "message_type is not a registered Core lifecycle ID",
                        rel_file,
                        line_no,
                    )
                )

    if "CT-INVARIANTS-01" in enabled_checks:
        if messages:
            session_id = messages[0].get("session_id")
            for index, (line_no, message) in enumerate(rows[1:], 1):
                if message.get("session_id") != session_id:
                    invalid_indices.add(index)
                    failures.append(
                        _failure(
                            "CT-INVARIANTS-01",
                            "session_id changed from the first transcript message",
                            rel_file,
                            line_no,
                        )
                    )
        seen_message_ids: set[Any] = set()
        for index, (line_no, message) in enumerate(rows):
            message_id = message.get("message_id")
            if message_id in seen_message_ids:
                invalid_indices.add(index)
                failures.append(
                    _failure(
                        "CT-INVARIANTS-01",
                        f"duplicate message_id occurrence: {message_id}",
                        rel_file,
                        line_no,
                    )
                )
            else:
                seen_message_ids.add(message_id)

    expected_types = transcript.get("expected_message_types")
    if "CT-SEQUENCE-01" in enabled_checks and isinstance(expected_types, list):
        actual_types = [message.get("message_type") for message in messages]
        if actual_types != expected_types:
            failures.append(
                _failure(
                    "CT-SEQUENCE-01",
                    f"message sequence mismatch (expected {expected_types}, got {actual_types})",
                    rel_file,
                )
            )

    if "CT-HASH-CHAIN-01" in enabled_checks or "CT-PREV-MSG-REQUIRED-01" in enabled_checks:
        for error in verify_transcript_chain(messages):
            line_no = int(error.split(":", 1)[0].split()[1])
            test_id = (
                "CT-PREV-MSG-REQUIRED-01"
                if "missing prev_msg_hash" in error
                else "CT-HASH-CHAIN-01"
            )
            if test_id in enabled_checks:
                index = line_to_index.get(line_no)
                if index is not None:
                    invalid_indices.add(index)
                failures.append(_failure(test_id, error, rel_file, line_no))

    if "CT-MESSAGE-HASH-01" in enabled_checks:
        for index, (line_no, message) in enumerate(rows):
            computed = message_hash_from_body(
                message_body_without_hash_and_signatures(message)
            )
            if computed != message.get("message_hash"):
                invalid_indices.add(index)
                failures.append(
                    _failure(
                        "CT-MESSAGE-HASH-01",
                        f"message_hash mismatch (computed {computed})",
                        rel_file,
                        line_no,
                    )
                )

    signature_checks = {
        "CT-SIGNATURE-HASH-01",
        "CT-SIGNATURE-STRUCTURE-01",
        "CT-SIGNATURE-VERIFY-01",
    }
    if signature_checks & enabled_checks:
        expected_failure_ids = {
            entry.get("test_id")
            for entry in transcript.get("expected_failures", [])
            if isinstance(entry, dict)
        }
        synthetic_verify_failure_added = False
        for index, (line_no, message) in enumerate(rows):
            signatures = message.get("signatures")
            has_signatures = isinstance(signatures, list) and bool(signatures)
            if (
                "CT-SIGNATURE-VERIFY-01" in enabled_checks
                and not crypto_available
                and has_signatures
            ):
                invalid_indices.add(index)
                if (
                    "CT-SIGNATURE-VERIFY-01" in expected_failure_ids
                    and not synthetic_verify_failure_added
                ):
                    failures.append(
                        _failure(
                            "CT-SIGNATURE-VERIFY-01",
                            "Ed25519 signature verification unavailable",
                            rel_file,
                            line_no,
                        )
                    )
                    synthetic_verify_failure_added = True
            for issue in validate_message_signatures(
                message,
                key_map,
                verify_crypto=(
                    "CT-SIGNATURE-VERIFY-01" in enabled_checks
                    and crypto_available
                ),
            ):
                if issue["code"] == "object_hash_mismatch":
                    test_id = "CT-SIGNATURE-HASH-01"
                elif issue["code"] in {
                    "missing_key",
                    "kid_mismatch",
                } or (
                    issue["code"] == "signature_invalid"
                    and "signature verification failed" in issue["message"]
                ):
                    test_id = "CT-SIGNATURE-VERIFY-01"
                else:
                    test_id = "CT-SIGNATURE-STRUCTURE-01"
                if test_id in enabled_checks:
                    invalid_indices.add(index)
                    failures.append(
                        _failure(test_id, issue["message"], rel_file, line_no)
                    )

    return failures, invalid_indices


def _evaluate_expected(
    transcript: dict[str, Any],
    transcript_failures: list[dict[str, Any]],
    rel_file: str,
) -> list[dict[str, Any]]:
    if transcript.get("expect_pass", True):
        return transcript_failures

    expected = {
        entry["test_id"]: int(entry.get("min_count", 1))
        for entry in transcript.get("expected_failures", [])
    }
    counts: dict[str, int] = {}
    errors: list[dict[str, Any]] = []
    for failure in transcript_failures:
        test_id = failure["test_id"]
        counts[test_id] = counts.get(test_id, 0) + 1
        if test_id not in expected:
            errors.append(failure)
    for test_id, minimum in expected.items():
        if counts.get(test_id, 0) < minimum:
            errors.append(
                _failure(
                    test_id,
                    f"expected failure missing or below min_count={minimum}",
                    rel_file,
                )
            )
    return errors


def run_suite(suite_path: Path) -> dict[str, Any]:
    suite_path = suite_path.resolve()
    suite = _load_json(suite_path)
    if suite.get("aicp_version") != "0.2":
        raise ValueError("isolated Core v0.2 runner accepts only aicp_version 0.2")

    message_schema = _load_json(ROOT / suite["schema_ref"])
    payload_schema = _load_json(ROOT / suite["payload_schema_ref"])
    contract_schema = _load_json(ROOT / suite["contract_schema_ref"])
    key_map = _load_json(ROOT / "fixtures/keys/GT_public_keys.json")
    message_validator = _validator(message_schema)
    contract_validator = _validator(contract_schema)
    enabled_checks = {
        check["test_id"]
        for check in suite.get("checks", [])
        if isinstance(check, dict) and isinstance(check.get("test_id"), str)
    }
    crypto_check_enabled = "CT-SIGNATURE-VERIFY-01" in enabled_checks
    crypto_available = signature_verifier_available()
    degraded_reasons: list[str] = []
    skipped_checks: list[str] = []
    if Draft202012Validator is None:
        degraded_reasons.append(
            "jsonschema dependency unavailable; schema checks skipped"
        )
        skipped_checks.extend(
            [
                "CT-SCHEMA-JSONL-01",
                "CT-PAYLOAD-SCHEMA-01",
                "CT2-CONTRACT-SCHEMA-01",
            ]
        )
    if crypto_check_enabled and not crypto_available:
        degraded_reasons.append(
            "Core v0.2 Ed25519 signature verification unavailable"
        )
        skipped_checks.append("CT-SIGNATURE-VERIFY-01")
    schema_failure_ids = {
        "CT-SCHEMA-JSONL-01",
        "CT-PAYLOAD-SCHEMA-01",
        "CT2-CONTRACT-SCHEMA-01",
        *suite.get("schema_failure_routes", {})
        .get("CT-SCHEMA-JSONL-01", {})
        .values(),
        *suite.get("schema_failure_routes", {})
        .get("CT-PAYLOAD-SCHEMA-01", {})
        .values(),
    }

    failures: list[dict[str, Any]] = []
    for transcript in suite.get("transcripts", []):
        rel_file = transcript["path"]
        rows = _load_jsonl(ROOT / rel_file)
        transcript_failures, invalid_indices = _check_common(
            rows=rows,
            transcript=transcript,
            rel_file=rel_file,
            enabled_checks=enabled_checks,
            message_validator=message_validator,
            payload_schema=payload_schema,
            key_map=key_map,
            crypto_available=crypto_available,
        )
        expected_failure_ids = {
            entry.get("test_id")
            for entry in transcript.get("expected_failures", [])
            if isinstance(entry, dict)
        }
        if (
            Draft202012Validator is None
            and expected_failure_ids & schema_failure_ids
        ):
            invalid_indices.update(
                index
                for index in transcript.get("invalid_message_indices", [])
                if isinstance(index, int)
            )
        run_contract_agreement_checks(
            rows=rows,
            transcript=transcript,
            enabled_checks=enabled_checks,
            rel_file=rel_file,
            failures=transcript_failures,
            contract_validator=contract_validator,
            invalid_indices=invalid_indices,
        )
        if Draft202012Validator is None and not transcript.get(
            "expect_pass", True
        ):
            observed = {
                failure["test_id"] for failure in transcript_failures
            }
            for expected in transcript.get("expected_failures", []):
                test_id = expected.get("test_id")
                if test_id in schema_failure_ids and test_id not in observed:
                    transcript_failures.append(
                        _failure(
                            test_id,
                            "schema validation unavailable in environment",
                            rel_file,
                        )
                    )
        failures.extend(
            _evaluate_expected(transcript, transcript_failures, rel_file)
        )

    passed = not failures
    degraded_reasons = list(dict.fromkeys(degraded_reasons))
    skipped_checks = list(dict.fromkeys(skipped_checks))
    degraded = bool(degraded_reasons or skipped_checks)
    badge_eligible = (
        passed
        and not degraded
        and degraded_reasons == []
        and skipped_checks == []
    )
    mark = suite.get("compatibility_mark")
    return {
        "aicp_version": suite["aicp_version"],
        "suite_id": suite["suite_id"],
        "suite_version": suite["suite_version"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "failures": failures,
        "compatibility_marks": (
            [mark] if badge_eligible and isinstance(mark, str) else []
        ),
        "degraded": degraded,
        "degraded_reasons": degraded_reasons,
        "skipped_checks": skipped_checks,
    }


def _status_label(report: dict[str, Any]) -> str:
    if not report.get("passed"):
        return "FAILED"
    return "PASSED (DEGRADED)" if report.get("degraded") else "PASSED"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run isolated experimental Core v0.2 conformance"
    )
    parser.add_argument(
        "--suite", default="conformance/core/CT_CORE_0.2.json"
    )
    parser.add_argument("--out", default="conformance/report_core_v02.json")
    args = parser.parse_args()

    report = run_suite(ROOT / args.suite)
    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    status = _status_label(report)
    print(f"Conformance {status}: {report['suite_id']} -> {args.out}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
