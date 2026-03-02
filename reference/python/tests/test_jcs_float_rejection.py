from __future__ import annotations

import pytest

from aicp_ref.jcs import canonicalize_json, canonicalize_number


def test_canonicalize_json_accepts_floats_and_normalizes_integral_forms() -> None:
    assert canonicalize_json({"x": 1.0, "z": -0.0, "y": 0.1}) == '{"x":1,"y":0.1,"z":0}'


def test_canonicalize_number_normalizes_exponent_and_zero() -> None:
    assert canonicalize_number(-0.0) == "0"
    assert canonicalize_number(1.2e-7) == "1.2e-7"


def test_canonicalize_json_rejects_unsafe_integer() -> None:
    with pytest.raises(ValueError, match="Unsafe integer"):
        canonicalize_json({"x": 9007199254740992})


def test_canonicalize_json_rejects_non_finite_numbers() -> None:
    with pytest.raises(ValueError, match="non-finite"):
        canonicalize_json({"x": float("inf")})
