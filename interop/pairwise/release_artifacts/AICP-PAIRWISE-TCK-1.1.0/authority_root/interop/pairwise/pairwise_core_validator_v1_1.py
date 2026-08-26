"""Pure Core v0.1 transcript validation for embedded evidence authorities."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from _runner_core_checks import run_core_transcript_checks
from aicp_ref.hashing import message_hash_from_body, object_hash
from aicp_ref.validate import message_body_without_hash_and_signatures, validate_message_signatures


EXPECTED_SEQUENCE = ("CONTRACT_PROPOSE", "CONTRACT_ACCEPT", "ATTEST_ACTION")


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _issue(test_id: str, message: str, line: int | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"test_id": test_id, "message": message}
    if line is not None:
        result["line"] = line
    return result


def _schema_issues(
    validator: Draft202012Validator,
    value: Any,
    *,
    test_id: str,
    line: int,
) -> list[dict[str, Any]]:
    return [
        _issue(
            test_id,
            ("/" + "/".join(str(part) for part in error.path) if error.path else "/")
            + f": {error.message}",
            line,
        )
        for error in sorted(validator.iter_errors(value), key=lambda item: list(item.path))
    ]


def validate_core_v01_transcript(
    messages: list[dict[str, Any]],
    *,
    authority_root: Path,
    expected_sequence: tuple[str, ...] = EXPECTED_SEQUENCE,
) -> list[dict[str, Any]]:
    """Execute the Core v0.1 suite-equivalent checks over in-memory messages."""

    message_schema = _load(authority_root / "schemas/core/aicp-core-message.schema.json")
    payload_schema = _load(authority_root / "schemas/core/aicp-core-payloads.schema.json")
    contract_schema = _load(authority_root / "schemas/core/aicp-core-contract.schema.json")
    message_validator = Draft202012Validator(message_schema)
    contract_validator = Draft202012Validator(contract_schema)
    payload_validators = {
        message_type: Draft202012Validator(payload_schema["$defs"][message_type])
        for message_type in expected_sequence
    }
    registered_types = {
        item.get("id")
        for item in _load(authority_root / "registry/message_types.json")
        if isinstance(item, dict)
    }
    policy_categories = {
        item.get("id")
        for item in _load(authority_root / "registry/policy_categories.json")
        if isinstance(item, dict)
    }
    public_keys = _load(authority_root / "fixtures/keys/GT_public_keys.json")
    errors: list[dict[str, Any]] = []
    if not isinstance(messages, list) or not messages:
        return [_issue("CT-SCHEMA-JSONL-01", "transcript must contain JSON objects")]

    rows = [(index, message) for index, message in enumerate(messages, start=1) if isinstance(message, dict)]
    core_failures: list[dict[str, Any]] = []
    run_core_transcript_checks(
        rows=rows,
        transcript={"expected_message_types": list(expected_sequence)},
        enabled_checks={
            "CT-MESSAGE-TYPE-REGISTRY-01",
            "CT-HASH-CHAIN-01",
            "CT-PREV-MSG-REQUIRED-01",
            "CT-INVARIANTS-01",
            "CT-CONTRACT-ID-01",
            "CT-SEQUENCE-01",
            "CT-SIGNATURE-HASH-01",
        },
        registered_message_types=registered_types,
        rel_file="pairwise-joint-transcript.jsonl",
        failures=core_failures,
    )
    errors.extend(
        _issue(
            str(item.get("test_id")),
            str(item.get("message")),
            item.get("line") if isinstance(item.get("line"), int) else None,
        )
        for item in core_failures
    )
    namespaced_dash = re.compile(r"^x-[a-z0-9]+[a-z0-9._-]*$")
    namespaced_colon = re.compile(r"^[a-z0-9]+:[a-z0-9][a-z0-9._-]*$")
    for index, message in enumerate(messages, start=1):
        if not isinstance(message, dict):
            errors.append(_issue("CT-SCHEMA-JSONL-01", "record must be a JSON object", index))
            continue
        errors.extend(_schema_issues(message_validator, message, test_id="CT-SCHEMA-JSONL-01", line=index))
        message_type = message.get("message_type")
        payload_validator = payload_validators.get(str(message_type))
        if payload_validator is None:
            errors.append(_issue("CT-PAYLOAD-SCHEMA-01", f"no Core v0.1 payload mapping for {message_type!r}", index))
        else:
            errors.extend(
                _schema_issues(
                    payload_validator,
                    message.get("payload"),
                    test_id="CT-PAYLOAD-SCHEMA-01",
                    line=index,
                )
            )
        try:
            computed_hash = message_hash_from_body(message_body_without_hash_and_signatures(message))
        except Exception as exc:
            errors.append(_issue("CT-MESSAGE-HASH-01", f"hash recomputation failed: {exc}", index))
        else:
            if message.get("message_hash") != computed_hash:
                errors.append(_issue("CT-MESSAGE-HASH-01", "message_hash differs from normative AICP-JCS-1 hashing", index))
        for signature_issue in validate_message_signatures(message, public_keys, verify_crypto=True):
            test_id = {
                "object_hash_mismatch": "CT-SIGNATURE-HASH-01",
                "object_type_mismatch": "CT-SIGNATURE-STRUCTURE-01",
            }.get(signature_issue["code"], "CT-SIGNATURE-VERIFY-01")
            errors.append(_issue(test_id, signature_issue["message"], index))

        payload = message.get("payload")
        if message_type == "CONTRACT_PROPOSE" and isinstance(payload, dict):
            contract = payload.get("contract")
            errors.extend(_schema_issues(contract_validator, contract, test_id="CT-CONTRACT-SCHEMA-01", line=index))
            if isinstance(contract, dict):
                if contract.get("contract_id") != message.get("contract_id"):
                    errors.append(_issue("CT-CONTRACT-SCHEMA-01", "envelope and contract contract_id values differ", index))
                contract_hash = payload.get("contract_hash")
                if contract_hash is not None and contract_hash != object_hash("contract", contract):
                    errors.append(_issue("CT-CONTRACT-SCHEMA-01", "contract_hash differs from normative AICP-JCS-1 hashing", index))
                policies = contract.get("policies")
                if policies is not None:
                    seen_policy_ids: set[str] = set()
                    for policy_index, policy in enumerate(policies if isinstance(policies, list) else []):
                        if not isinstance(policy, dict):
                            errors.append(_issue("CT-POLICY-CATEGORIES-01", f"policies[{policy_index}] must be an object", index))
                            continue
                        policy_id = policy.get("policy_id")
                        category = policy.get("category")
                        if not isinstance(policy_id, str) or not policy_id or policy_id in seen_policy_ids:
                            errors.append(_issue("CT-POLICY-CATEGORIES-01", "policy_id values must be non-empty and unique", index))
                        else:
                            seen_policy_ids.add(policy_id)
                        if not isinstance(category, str) or not category or (
                            category not in policy_categories
                            and not namespaced_dash.match(category)
                            and not namespaced_colon.match(category)
                        ):
                            errors.append(_issue("CT-POLICY-CATEGORIES-01", f"invalid policy category {category!r}", index))
    return errors
