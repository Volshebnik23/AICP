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

from aicp_ref.hashing import message_hash_from_body  # noqa: E402
from aicp_ref.validate import message_body_without_hash_and_signatures  # noqa: E402
from aicp_ref_capneg_v02.session_state_v2 import (  # noqa: E402
    validate_session_state_projection_v2,
)
from aicp_ref_capneg_v02.state_machine import reduce_capneg_v02  # noqa: E402


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
    errors: list[str] = []
    for index, message in enumerate(messages):
        computed = message_hash_from_body(
            message_body_without_hash_and_signatures(message)
        )
        if computed != message.get("message_hash"):
            errors.append(f"{message.get('message_id')}: message hash mismatch")
        if index == 0:
            if "prev_msg_hash" in message:
                errors.append(f"{message.get('message_id')}: unexpected first prev_msg_hash")
        elif message.get("prev_msg_hash") != messages[index - 1].get("message_hash"):
            errors.append(f"{message.get('message_id')}: broken hash chain")

    state = reduce_capneg_v02(
        messages,
        registered_reason_codes={
            entry["id"]
            for entry in _load_json(ROOT / "registry/capneg_reason_codes.json")
        },
        key_map=_load_json(ROOT / "fixtures/keys/GT_public_keys.json"),
    )
    errors.extend(state["errors"])
    extensions = {
        entry["id"] for entry in _load_json(ROOT / "registry/extension_ids.json")
    }
    for index, message in enumerate(messages):
        errors.extend(
            issue["code"]
            for issue in validate_session_state_projection_v2(
                message,
                messages,
                index,
                capneg_state=state,
                registered_extensions=extensions,
            )
        )
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
