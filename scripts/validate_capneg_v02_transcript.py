#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REF_PY = ROOT / "reference/python"
if str(REF_PY) not in sys.path:
    sys.path.insert(0, str(REF_PY))

RUNNER_DIR = ROOT / "conformance/capneg_v02_runner"
if str(RUNNER_DIR) not in sys.path:
    sys.path.insert(0, str(RUNNER_DIR))

from aicp_ref.signatures import signature_verifier_available  # noqa: E402
from aicp_ref_capneg_v02.session_state_v2 import (  # noqa: E402
    validate_session_state_projection_v2,
)
from aicp_ref_capneg_v02.state_machine import reduce_capneg_v02  # noqa: E402
from validation import validate_messages  # noqa: E402


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("transcript")
    args = parser.parse_args()
    path = ROOT / args.transcript
    messages = _load_jsonl(path)
    rules = _load_json(ROOT / "registry/aicp_profile_composition_rules.json")
    registered_reasons = {
        entry["id"]
        for entry in _load_json(ROOT / "registry/capneg_reason_codes.json")
    }
    key_map = _load_json(ROOT / "fixtures/keys/GT_public_keys.json")
    crypto_available = signature_verifier_available()
    invalid, transcript_issues = validate_messages(
        messages,
        message_schema=_load_json(
            ROOT / "schemas/core/aicp-core-message.schema.json"
        ),
        capneg_schema=_load_json(
            ROOT / "schemas/extensions/ext-capneg-v0.2-payloads.schema.json"
        ),
        projection_schema=_load_json(
            ROOT / "schemas/extensions/session-state-projection-v2.schema.json"
        ),
        core_payload_schema=_load_json(
            ROOT / "schemas/core/aicp-core-payloads.schema.json"
        ),
        core_contract_schema=_load_json(
            ROOT / "schemas/core/aicp-core-contract.schema.json"
        ),
        registered_messages={
            entry["id"]
            for entry in _load_json(ROOT / "registry/message_types.json")
        },
        key_map=key_map,
        jsonschema_available=True,
        crypto_available=crypto_available,
    )
    state = reduce_capneg_v02(
        messages,
        rules=rules,
        registered_reason_codes=registered_reasons,
        key_map=key_map,
        crypto_available=crypto_available,
        invalid_messages=invalid,
    )
    issues = list(state["issues"]) + transcript_issues
    extensions = {
        entry["id"] for entry in _load_json(ROOT / "registry/extension_ids.json")
    }
    for index, message in enumerate(messages):
        if index not in invalid:
            issues.extend(
                validate_session_state_projection_v2(
                    message,
                    messages,
                    index,
                    registered_extensions=extensions,
                    rules=rules,
                    registered_reason_codes=registered_reasons,
                    key_map=key_map,
                    crypto_available=crypto_available,
                    invalid_messages=invalid,
                )
            )
    errors = [
        f"{item.get('message_id') or '<transcript>'}: "
        f"{item['code']}: {item['detail']}"
        for item in issues
    ]
    if state["state"] != "ACCEPTED":
        errors.append("quickstart negotiation did not reach ACCEPTED")
    if not state["bound_contracts"]:
        errors.append("quickstart contract was not bound")
    if errors:
        for error in errors:
            print(f"[FAIL] {error}")
        return 1
    print(
        "OK: CAPNEG v0.2 quickstart has canonical composition, exact hashes, "
        "full acceptance, contract binding, and projection v2."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
