from __future__ import annotations

import base64
import hashlib
import json
import math
import re
from typing import Any

CORE_MESSAGE_TYPES = {
    "CONTRACT_PROPOSE",
    "CONTRACT_ACCEPT",
    "CONTEXT_AMEND",
    "ATTEST_ACTION",
    "RESOLVE_CONFLICT",
    "ERROR",
}

SAFE_INTEGER_MAX = 9007199254740991
_EXP_RE = re.compile(r"^(?P<mantissa>.*)[eE](?P<exp>[+-]?\d+)$")


def canonicalize_number(value: int | float) -> str:
    if isinstance(value, bool):
        raise TypeError("boolean is not a canonical numeric value")

    if isinstance(value, int):
        if abs(value) > SAFE_INTEGER_MAX:
            raise ValueError("Unsafe integer for AICP canonicalization (must be within IEEE-754 safe integer range)")
        return str(value)

    if not math.isfinite(value):
        raise ValueError("Unsupported non-finite number for canonicalization")

    if value == 0.0 or value.is_integer():
        int_value = int(value)
        if abs(int_value) > SAFE_INTEGER_MAX:
            raise ValueError("Unsafe integer for AICP canonicalization (must be within IEEE-754 safe integer range)")
        return str(int_value)

    raw = repr(value)
    match = _EXP_RE.match(raw)
    if not match:
        if raw.endswith(".0"):
            raw = raw[:-2]
        return raw

    mantissa = match.group("mantissa")
    exponent = int(match.group("exp"))
    return f"{mantissa}e{exponent}"


def _serialize(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    if isinstance(value, int) and not isinstance(value, bool):
        return canonicalize_number(value)
    if isinstance(value, float):
        return canonicalize_number(value)
    if isinstance(value, list):
        return "[" + ",".join(_serialize(item) for item in value) + "]"
    if isinstance(value, dict):
        parts = []
        for key in sorted(value.keys()):
            if not isinstance(key, str):
                raise TypeError("Object keys must be strings for canonical JSON")
            parts.append(f"{json.dumps(key, ensure_ascii=False, separators=(',', ':'))}:{_serialize(value[key])}")
        return "{" + ",".join(parts) + "}"
    raise TypeError(f"Unsupported value type for canonicalization: {type(value)!r}")


def canonicalize_json(value: Any) -> str:
    return _serialize(value)


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
