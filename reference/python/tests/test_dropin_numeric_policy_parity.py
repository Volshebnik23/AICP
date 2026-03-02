from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from aicp_ref.jcs import canonicalize_json as ref_canonicalize_json

DROPIN_PATH = Path(__file__).resolve().parents[3] / "dropins/aicp-core/python/aicp_core.py"


def _load_dropin_module():
    spec = importlib.util.spec_from_file_location("aicp_dropin_core_parity", DROPIN_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[assignment]
    return module


def test_dropin_numeric_policy_matches_reference() -> None:
    mod = _load_dropin_module()
    payload = {"z": [1, {"a": -9007199254740991}], "b": 2}
    assert mod.canonicalize_json(payload) == ref_canonicalize_json(payload)


@pytest.mark.parametrize("value", [9007199254740993, -9007199254740993, 0.1, 1.0])
def test_dropin_rejections_match_reference(value: float | int) -> None:
    mod = _load_dropin_module()
    with pytest.raises(ValueError):
        mod.canonicalize_json({"x": value})
    with pytest.raises(ValueError):
        ref_canonicalize_json({"x": value})
