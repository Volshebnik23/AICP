from __future__ import annotations

import pytest

from aicp_ref.jcs import canonicalize_json


def test_canonicalize_json_rejects_float_values() -> None:
    with pytest.raises(ValueError):
        canonicalize_json({"x": 1.0})
