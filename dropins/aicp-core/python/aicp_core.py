from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

CORE_MESSAGE_TYPES = {
    "CONTRACT_PROPOSE",
    "CONTRACT_ACCEPT",
    "CONTEXT_AMEND",
    "ATTEST_ACTION",
    "RESOLVE_CONFLICT",
    "ERROR",
}

SAFE_INTEGER_MAX = (2 ** 53) - 1
SAFE_INTEGER_MIN = -SAFE_INTEGER_MAX


def _reject_unsupported_numbers(value: Any) -> None:
    if isinstance(value, bool) or value is None:
        return
    if isinstance(value, int):
        if value < SAFE_INTEGER_MIN or value > SAFE_INTEGER_MAX:
            raise ValueError("Integers outside IEEE-754 safe range are not supported by AICP Core v0.1")
        return
    if isinstance(value, float):
        raise ValueError("Floats are not supported by AICP Core v0.1; see OQ-0001 / RFC8785 numeric handling")
    if isinstance(value, list):
        for item in value:
            _reject_unsupported_numbers(item)
    elif isinstance(value, dict):
        for item in value.values():
            _reject_unsupported_numbers(item)


def _sort_deep(value: Any) -> Any:
    if isinstance(value, list):
        return [_sort_deep(v) for v in value]
    if isinstance(value, dict):
        return {k: _sort_deep(value[k]) for k in sorted(value.keys())}
    return value


def canonicalize_json(value: Any) -> str:
    _reject_unsupported_numbers(value)
    return json.dumps(_sort_deep(value), separators=(",", ":"), ensure_ascii=False)


def object_hash(object_type: str, obj: Any) -> str:
    canonical = canonicalize_json(obj).encode("utf-8")
    preimage = b"AICP1\0" + object_type.encode("utf-8") + b"\0" + canonical
    digest = hashlib.sha256(preimage).digest()
    return "sha256:" + base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def message_hash_from_body(message_body: dict[str, Any]) -> str:
    return object_hash("message", message_body)


def build_core_message(*, session_id: str, message_id: str, timestamp: str, sender: str, message_type: str, payload: dict[str, Any], contract_id: str, contract_ref: dict[str, str], prev_msg_hash: str | None = None) -> dict[str, Any]:
    if message_type not in CORE_MESSAGE_TYPES:
        raise ValueError(f"Unsupported core message_type: {message_type}")

    body: dict[str, Any] = {
        "session_id": session_id,
        "message_id": message_id,
        "timestamp": timestamp,
        "sender": sender,
        "message_type": message_type,
        "contract_id": contract_id,
        "contract_ref": contract_ref,
        "payload": payload,
    }
    if prev_msg_hash:
        body["prev_msg_hash"] = prev_msg_hash

    message = dict(body)
    message["message_hash"] = message_hash_from_body(body)
    return message
