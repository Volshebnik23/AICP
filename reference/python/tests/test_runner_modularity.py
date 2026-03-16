from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "conformance/runner/aicp_conformance_runner.py"
RUNNER_IO = ROOT / "conformance/runner/_runner_io.py"
RUNNER_CONTEXT = ROOT / "conformance/runner/_runner_context.py"


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_runner_internal_modules_load_and_basic_helpers_work() -> None:
    io_mod = _load(RUNNER_IO, "runner_io_modularity_test")
    ctx_mod = _load(RUNNER_CONTEXT, "runner_context_modularity_test")
    runner_mod = _load(RUNNER, "runner_modularity_test")

    schema_path = ROOT / "schemas/core/aicp-core-message.schema.json"
    first = io_mod.load_json(schema_path)
    second = io_mod.load_json(schema_path)
    assert first is second

    ptr = ctx_mod.normalize_pointer("#/properties")
    assert ptr == "/properties"
    assert isinstance(ctx_mod.resolve_json_pointer(first, "/properties"), dict)

    assert callable(runner_mod.run_suite)
