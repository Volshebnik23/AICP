from __future__ import annotations

import json
import math
from typing import Any


SAFE_INTEGER_MAX = (2 ** 53) - 1
SAFE_INTEGER_MIN = -SAFE_INTEGER_MAX


def _reject_unsupported_numbers(value: Any) -> None:
    if isinstance(value, bool):
        return
    if isinstance(value, int):
        if value < SAFE_INTEGER_MIN or value > SAFE_INTEGER_MAX:
            raise ValueError("Integers outside IEEE-754 safe range are not supported by AICP Core v0.1")
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("Unsupported non-finite float for canonicalization")
        # Current fixtures avoid float edge cases; disallow until full RFC8785 handling is added.
        raise ValueError("Floats are not supported by AICP Core v0.1; see OQ-0001 / RFC8785 numeric handling")
    if isinstance(value, dict):
        for v in value.values():
            _reject_unsupported_numbers(v)
    elif isinstance(value, list):
        for v in value:
            _reject_unsupported_numbers(v)


def canonicalize_json(obj: Any) -> str:
    """Deterministic canonical JSON aligned with current Core fixtures.

    Uses key sorting and compact separators. Full RFC8785 numeric edge-case handling
    is intentionally not implemented; unsupported floats raise an explicit exception.
    """
    _reject_unsupported_numbers(obj)
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def canonicalize_to_bytes(obj: Any) -> bytes:
    return canonicalize_json(obj).encode("utf-8")
