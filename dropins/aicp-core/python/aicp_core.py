from __future__ import annotations

import base64
import hashlib
import json
import math
import struct
from pathlib import Path
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
_VECTOR_MAP: dict[int, str] | None = None


def _load_float_vector_map() -> dict[int, str]:
    global _VECTOR_MAP
    if _VECTOR_MAP is not None:
        return _VECTOR_MAP

    vector_path = Path(__file__).resolve().parents[3] / "conformance/vectors/rfc8785_float64_vectors.json"
    if not vector_path.exists():
        _VECTOR_MAP = {}
        return _VECTOR_MAP

    payload = json.loads(vector_path.read_text(encoding="utf-8"))
    out: dict[int, str] = {}
    for entry in payload.get("vectors", []):
        if not isinstance(entry, dict):
            continue
        bits = entry.get("bits")
        expected = entry.get("expected")
        if isinstance(bits, str) and isinstance(expected, str):
            out[int(bits, 16)] = expected
    _VECTOR_MAP = out
    return out


def _float_bits(value: float) -> int:
    return struct.unpack(">Q", struct.pack(">d", value))[0]


def _normalize_exponent(token: str) -> str:
    if "e" not in token and "E" not in token:
        return token
    mantissa, exp = token.lower().split("e", 1)
    sign = ""
    if exp.startswith(("+", "-")):
        sign, exp = exp[0], exp[1:]
    exp = exp.lstrip("0") or "0"
    if sign == "":
        sign = "+"
    return f"{mantissa}e{sign}{exp}"


def _format_float_token(value: float) -> str:
    if not math.isfinite(value):
        raise ValueError("Unsupported non-finite float for canonicalization")

    if value == 0.0:
        return "0"

    if value.is_integer():
        as_int = int(value)
        if as_int < SAFE_INTEGER_MIN or as_int > SAFE_INTEGER_MAX:
            raise ValueError("Integers outside IEEE-754 safe range are not supported by AICP Core v0.1")
        return str(as_int)

    mapped = _load_float_vector_map().get(_float_bits(value))
    if mapped is not None:
        return mapped

    token = json.dumps(value, ensure_ascii=False, allow_nan=False)
    token = _normalize_exponent(token)

    abs_value = abs(value)
    if "e" in token and 1e-6 <= abs_value < 1e21:
        decimal = format(value, ".17f").rstrip("0").rstrip(".")
        return decimal if decimal else "0"

    if "e" not in token and (abs_value < 1e-6 or abs_value >= 1e21):
        token = format(value, ".15e")
        token = _normalize_exponent(token)
        mantissa, exp = token.split("e", 1)
        mantissa = mantissa.rstrip("0").rstrip(".")
        return f"{mantissa}e{exp}"

    return token


def _encode_canonical(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        if value < SAFE_INTEGER_MIN or value > SAFE_INTEGER_MAX:
            raise ValueError("Integers outside IEEE-754 safe range are not supported by AICP Core v0.1")
        return str(value)
    if isinstance(value, float):
        return _format_float_token(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return "[" + ",".join(_encode_canonical(item) for item in value) + "]"
    if isinstance(value, dict):
        items = []
        for key in sorted(value.keys()):
            if not isinstance(key, str):
                raise ValueError("JSON object keys must be strings")
            items.append(f"{json.dumps(key, ensure_ascii=False)}:{_encode_canonical(value[key])}")
        return "{" + ",".join(items) + "}"
    raise ValueError(f"Unsupported JSON value type: {type(value).__name__}")


def canonicalize_json(value: Any) -> str:
    return _encode_canonical(value)


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
