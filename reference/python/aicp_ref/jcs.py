from __future__ import annotations

import json
import math
from decimal import Decimal
from typing import Any


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


def canonicalize_json(obj: Any) -> str:
    return _encode(obj)


def canonicalize_to_bytes(obj: Any) -> bytes:
    return canonicalize_json(obj).encode("utf-8")
