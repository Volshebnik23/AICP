from __future__ import annotations

import importlib.util
from pathlib import Path


DROPIN_PATH = Path(__file__).resolve().parents[3] / "dropins/aicp-core/python/aicp_core.py"


def _load_dropin_module():
    spec = importlib.util.spec_from_file_location("aicp_dropin_core", DROPIN_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[assignment]
    return module


def test_dropin_accepts_float_numbers() -> None:
    mod = _load_dropin_module()
    assert mod.canonicalize_json({"score": 0.5}) == '{"score":0.5}'


def test_dropin_rejects_non_finite_float_numbers() -> None:
    mod = _load_dropin_module()
    try:
        mod.canonicalize_json({"score": float("nan")})
    except ValueError as exc:
        assert "non-finite" in str(exc)
    else:
        raise AssertionError("expected non-finite float canonicalization to be rejected")


def test_dropin_core_message_types_include_error() -> None:
    mod = _load_dropin_module()
    assert "ERROR" in mod.CORE_MESSAGE_TYPES
