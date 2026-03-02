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


def test_dropin_supports_float_numbers_with_normalization() -> None:
    mod = _load_dropin_module()
    canonical = mod.canonicalize_json({"score": 1.0, "prob": 0.1, "neg_zero": -0.0})
    assert canonical == '{"neg_zero":0,"prob":0.1,"score":1}'


def test_dropin_rejects_unsafe_integers() -> None:
    mod = _load_dropin_module()
    try:
        mod.canonicalize_json({"big": 9007199254740992})
    except ValueError as exc:
        assert "Unsafe integer" in str(exc)
    else:
        raise AssertionError("expected unsafe integer canonicalization to be rejected")


def test_dropin_core_message_types_include_error() -> None:
    mod = _load_dropin_module()
    assert "ERROR" in mod.CORE_MESSAGE_TYPES


def test_dropin_accepts_safe_integers() -> None:
    mod = _load_dropin_module()
    canonical = mod.canonicalize_json({"score": 1})
    assert canonical == '{"score":1}'
