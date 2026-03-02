from __future__ import annotations

import base64
import hashlib
import json
import math
from decimal import Decimal
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


def _ecmascript_number(value: float) -> str:
    if not math.isfinite(value):
        raise ValueError("Unsupported non-finite float for canonicalization")
    if value == 0:
        return "0"

    abs_value = abs(value)
    raw = repr(value)
    use_exponent = abs_value < 1e-6 or abs_value >= 1e21

    if "e" in raw or "E" in raw:
        mantissa, exponent = raw.lower().split("e", 1)
        exp_num = int(exponent)
        if use_exponent:
            return f"{mantissa}e{exp_num:+d}"
        fixed = format(Decimal(raw), "f")
        if "." in fixed:
            fixed = fixed.rstrip("0").rstrip(".")
        return fixed

    if value.is_integer() and not use_exponent:
        return str(int(value))

    if use_exponent:
        sci = format(value, ".15e")
        mantissa, exponent = sci.split("e", 1)
        mantissa = mantissa.rstrip("0").rstrip(".")
        return f"{mantissa}e{int(exponent):+d}"

    return raw


def _encode(value: Any) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, int):
        if value < SAFE_INTEGER_MIN or value > SAFE_INTEGER_MAX:
            raise ValueError("Integers outside IEEE-754 safe range are not supported by AICP Core v0.1")
        return str(value)
    if isinstance(value, float):
        return _ecmascript_number(value)
    if isinstance(value, str):
        return json.encoder.encode_basestring(value)
    if isinstance(value, list):
        return "[" + ",".join(_encode(item) for item in value) + "]"
    if isinstance(value, dict):
        items: list[str] = []
        for key in sorted(value):
            if not isinstance(key, str):
                raise TypeError("JSON object keys must be strings")
            items.append(f"{json.encoder.encode_basestring(key)}:{_encode(value[key])}")
        return "{" + ",".join(items) + "}"
    raise TypeError(f"Unsupported type for canonicalization: {type(value)!r}")


def canonicalize_json(value: Any) -> str:
    return _encode(value)


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
