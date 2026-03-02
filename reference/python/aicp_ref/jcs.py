from __future__ import annotations

import json
import math
import re
from typing import Any

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


def canonicalize_json(obj: Any) -> str:
    """Deterministic canonical JSON aligned with Core v0.1 numeric policy."""
    return _serialize(obj)


def canonicalize_to_bytes(obj: Any) -> bytes:
    return canonicalize_json(obj).encode("utf-8")
