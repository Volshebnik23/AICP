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


def _schema_failure_id(message: dict[str, Any], *, payload: bool) -> str:
    message_type = message.get("message_type")
    if payload and message_type == "CONTEXT_AMEND":
        return "CT2-CONTEXT-BINDING-01"
    if not payload and message_type == "CONTRACT_PROPOSE":
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
) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    messages = [message for _, message in rows]

    if "CT-SCHEMA-JSONL-01" in enabled_checks and message_validator is not None:
        for line_no, message in rows:
            for issue in sorted(
                message_validator.iter_errors(message),
                key=lambda item: (list(item.absolute_path), item.message),
            ):
                failures.append(
                    _failure(
                        _schema_failure_id(message, payload=False),
                        issue.message,
                        rel_file,
                        line_no,
                    )
                )

    if "CT-PAYLOAD-SCHEMA-01" in enabled_checks:
        for line_no, message in rows:
            message_type = message.get("message_type")
            if not isinstance(message_type, str):
                continue
            validator = _payload_validator(payload_schema, message_type)
            if validator is None:
                continue
            for issue in sorted(
                validator.iter_errors(message.get("payload")),
                key=lambda item: (list(item.absolute_path), item.message),
            ):
                failures.append(
                    _failure(
                        _schema_failure_id(message, payload=True),
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
        for line_no, message in rows:
            if message.get("message_type") not in allowed:
                failures.append(
                    _failure(
                        "CT-MESSAGE-TYPE-REGISTRY-01",
                        "message_type is not a registered Core lifecycle ID",
                        rel_file,
                        line_no,
                    )
                )

    if "CT-INVARIANTS-01" in enabled_checks:
        sessions = {message.get("session_id") for message in messages}
        if len(sessions) != 1:
            failures.append(
                _failure(
                    "CT-INVARIANTS-01",
                    "all transcript messages must share one session_id",
                    rel_file,
                )
            )
        message_ids = [message.get("message_id") for message in messages]
        if len(set(message_ids)) != len(message_ids):
            failures.append(
                _failure(
                    "CT-INVARIANTS-01",
                    "message_id values must be unique",
                    rel_file,
                )
            )

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
                failures.append(_failure(test_id, error, rel_file, line_no))

    if "CT-MESSAGE-HASH-01" in enabled_checks:
        for line_no, message in rows:
            computed = message_hash_from_body(
                message_body_without_hash_and_signatures(message)
            )
            if computed != message.get("message_hash"):
                failures.append(
                    _failure(
                        "CT-MESSAGE-HASH-01",
                        f"message_hash mismatch (computed {computed})",
                        rel_file,
                        line_no,
                    )
                )

    if {
        "CT-SIGNATURE-HASH-01",
        "CT-SIGNATURE-STRUCTURE-01",
    } & enabled_checks:
        for line_no, message in rows:
            for issue in validate_message_signatures(
                message, {}, verify_crypto=False
            ):
                test_id = (
                    "CT-SIGNATURE-HASH-01"
                    if issue["code"] == "object_hash_mismatch"
                    else "CT-SIGNATURE-STRUCTURE-01"
                )
                if test_id in enabled_checks:
                    failures.append(
                        _failure(test_id, issue["message"], rel_file, line_no)
                    )

    return failures


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
    message_validator = _validator(message_schema)
    contract_validator = _validator(contract_schema)
    enabled_checks = {
        check["test_id"]
        for check in suite.get("checks", [])
        if isinstance(check, dict) and isinstance(check.get("test_id"), str)
    }

    failures: list[dict[str, Any]] = []
    for transcript in suite.get("transcripts", []):
        rel_file = transcript["path"]
        rows = _load_jsonl(ROOT / rel_file)
        transcript_failures = _check_common(
            rows=rows,
            transcript=transcript,
            rel_file=rel_file,
            enabled_checks=enabled_checks,
            message_validator=message_validator,
            payload_schema=payload_schema,
        )
        run_contract_agreement_checks(
            rows=rows,
            transcript=transcript,
            enabled_checks=enabled_checks,
            rel_file=rel_file,
            failures=transcript_failures,
            contract_validator=contract_validator,
        )
        failures.extend(
            _evaluate_expected(transcript, transcript_failures, rel_file)
        )

    passed = not failures
    mark = suite.get("compatibility_mark")
    return {
        "aicp_version": suite["aicp_version"],
        "suite_id": suite["suite_id"],
        "suite_version": suite["suite_version"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "failures": failures,
        "compatibility_marks": [mark] if passed and isinstance(mark, str) else [],
        "degraded": Draft202012Validator is None,
        "degraded_reasons": (
            []
            if Draft202012Validator is not None
            else ["jsonschema dependency unavailable; schema checks skipped"]
        ),
        "skipped_checks": (
            []
            if Draft202012Validator is not None
            else [
                "CT-SCHEMA-JSONL-01",
                "CT-PAYLOAD-SCHEMA-01",
                "CT2-CONTRACT-SCHEMA-01",
            ]
        ),
    }


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
    status = "PASSED" if report["passed"] else "FAILED"
    print(f"Conformance {status}: {report['suite_id']} -> {args.out}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
