from __future__ import annotations

import pytest

from aicp_ref.jcs import canonicalize_json


def test_canonicalize_json_accepts_float_values() -> None:
    assert canonicalize_json({"x": 1.0}) == '{"x":1}'
    assert canonicalize_json({"x": 0.1}) == '{"x":0.1}'


def test_canonicalize_json_rejects_non_finite_floats() -> None:
    with pytest.raises(ValueError, match="non-finite"):
        canonicalize_json({"x": float("inf")})


def test_canonicalize_json_rejects_unsafe_integers() -> None:
    with pytest.raises(ValueError, match="safe range"):
        canonicalize_json({"x": 9007199254740993})
