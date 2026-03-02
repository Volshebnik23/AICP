from __future__ import annotations

import pytest

from aicp_ref.jcs import canonicalize_json


def test_canonicalize_json_rejects_float_values() -> None:
    with pytest.raises(ValueError, match="Floats are not supported"):
        canonicalize_json({"x": 1.0})


def test_canonicalize_json_rejects_unsafe_integers() -> None:
    with pytest.raises(ValueError, match="safe range"):
        canonicalize_json({"x": 9007199254740993})


def test_canonicalize_json_accepts_safe_integers() -> None:
    assert canonicalize_json({"x": 9007199254740991}) == '{"x":9007199254740991}'
