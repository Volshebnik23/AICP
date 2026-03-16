from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CONFORMANCE_RUNNER = ROOT / "conformance/runner/aicp_conformance_runner.py"
PROFILE_RUNNER = ROOT / "conformance/runner/aicp_profile_runner.py"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_conformance_load_json_is_cached_identity() -> None:
    runner = _load_module(CONFORMANCE_RUNNER, "aicp_conformance_runner_cache_test")
    schema_path = ROOT / "schemas/core/aicp-core-message.schema.json"

    first = runner.load_json(schema_path)
    second = runner.load_json(schema_path)

    assert first is second


def test_profile_load_json_is_cached_identity() -> None:
    runner = _load_module(PROFILE_RUNNER, "aicp_profile_runner_cache_test")
    profile_path = ROOT / "conformance/profiles/PF_AICP_BASE_0.1.json"

    first = runner.load_json(profile_path)
    second = runner.load_json(profile_path)

    assert first is second


def test_pointer_validator_cached_when_available() -> None:
    runner = _load_module(CONFORMANCE_RUNNER, "aicp_conformance_runner_pointer_cache_test")
    if runner.Draft202012Validator is None:
        return

    schema_path = ROOT / "schemas/extensions/ext-redaction-payloads.schema.json"
    pointer = "/$defs/PiiRef"

    first = runner._validator_for_schema_path_pointer(str(schema_path.resolve()), pointer)
    second = runner._validator_for_schema_path_pointer(str(schema_path.resolve()), pointer)

    assert first is second
