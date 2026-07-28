#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REF_PY = ROOT / "reference/python"
RUNNER_DIR = ROOT / "conformance/runner"
for candidate in (REF_PY, RUNNER_DIR):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

from aicp_ref_v02.contract_agreement import reduce_transcript  # noqa: E402
from aicp_ref.hashing import message_hash_from_body  # noqa: E402
from _runner_context import (  # noqa: E402
    build_payload_validator_map,
    build_validator,
    load_json,
)


def _body(message: dict) -> dict:
    body = dict(message)
    body.pop("message_hash", None)
    body.pop("signatures", None)
    return body


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("transcript")
    args = parser.parse_args()
    path = Path(args.transcript)
    messages = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    errors: list[str] = []

    message_schema_path = ROOT / "schemas/core/aicp-core-message-v0.2.schema.json"
    message_validator = build_validator(
        load_json(message_schema_path), message_schema_path
    )
    payload_schema = load_json(
        ROOT / "schemas/core/aicp-core-payloads-v0.2.schema.json"
    )
    payload_validators = build_payload_validator_map(
        payload_schema,
        {
            "CONTRACT_PROPOSE": "#/$defs/CONTRACT_PROPOSE",
            "CONTRACT_ACCEPT": "#/$defs/CONTRACT_ACCEPT",
            "CONTEXT_AMEND": "#/$defs/CONTEXT_AMEND",
            "ATTEST_ACTION": "#/$defs/ATTEST_ACTION",
            "RESOLVE_CONFLICT": "#/$defs/RESOLVE_CONFLICT",
            "ERROR": "#/$defs/ERROR",
        },
    )
    contract_schema_path = ROOT / "schemas/core/aicp-core-contract-v0.2.schema.json"
    contract_validator = build_validator(
        load_json(contract_schema_path), contract_schema_path
    )

    previous = None
    for index, message in enumerate(messages):
        if message_validator is not None:
            errors.extend(
                f"message {index + 1}: {issue.message}"
                for issue in message_validator.iter_errors(message)
            )
        validator = payload_validators.get(message.get("message_type"))
        if validator is not None:
            errors.extend(
                f"payload {index + 1}: {issue.message}"
                for issue in validator.iter_errors(message.get("payload"))
            )
        if message.get("message_type") == "CONTRACT_PROPOSE" and contract_validator is not None:
            contract = (message.get("payload") or {}).get("contract")
            errors.extend(
                f"contract {index + 1}: {issue.message}"
                for issue in contract_validator.iter_errors(contract)
            )
        if index > 0 and message.get("prev_msg_hash") != previous:
            errors.append(f"message {index + 1}: prev_msg_hash mismatch")
        computed = message_hash_from_body(_body(message))
        if message.get("message_hash") != computed:
            errors.append(f"message {index + 1}: message_hash mismatch")
        previous = message.get("message_hash")

    if [item.get("message_type") for item in messages] != [
        "CONTRACT_PROPOSE",
        "CONTRACT_ACCEPT",
        "ATTEST_ACTION",
    ]:
        errors.append("quickstart sequence must be propose, accept, action")
    state = reduce_transcript(messages)
    errors.extend(f"{issue.code}: {issue.message}" for issue in state.issues)
    if state.state != "ACTIVE_HEAD" or state.active_head is None:
        errors.append("quickstart did not reach an exact active head")

    if errors:
        print("[FAIL] Core v0.2 quickstart transcript")
        for error in errors:
            print(f" - {error}")
        return 1
    print(
        "OK: Core v0.2 quickstart reached ACTIVE_HEAD with exact proposal, "
        "acceptance, contract hash, and message-chain bindings."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
