from __future__ import annotations

import json
import struct
from pathlib import Path

import pytest

from aicp_ref.jcs import canonicalize_json

ROOT = Path(__file__).resolve().parents[3]
VECTORS_PATH = ROOT / "conformance/vectors/rfc8785_float64_vectors.json"


def _float_from_bits(bits_hex: str) -> float:
    bits = int(bits_hex, 16)
    return struct.unpack(">d", struct.pack(">Q", bits))[0]


def test_canonicalize_json_matches_float_vectors() -> None:
    vectors = json.loads(VECTORS_PATH.read_text(encoding="utf-8"))["vectors"]
    for entry in vectors:
        n = _float_from_bits(entry["bits"])
        expected = '{"x":' + entry["expected"] + '}'
        if n.is_integer() and (n < -9007199254740991 or n > 9007199254740991):
            with pytest.raises(ValueError, match="safe range"):
                canonicalize_json({"x": n})
        else:
            assert canonicalize_json({"x": n}) == expected


def test_canonicalize_json_rejects_unsafe_integers() -> None:
    with pytest.raises(ValueError, match="safe range"):
        canonicalize_json({"x": 9007199254740993})


def test_canonicalize_json_rejects_non_finite_numbers() -> None:
    with pytest.raises(ValueError, match="non-finite"):
        canonicalize_json({"x": float("inf")})
    with pytest.raises(ValueError, match="non-finite"):
        canonicalize_json({"x": float("nan")})
