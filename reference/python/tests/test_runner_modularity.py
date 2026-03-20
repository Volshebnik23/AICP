from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CONTEXT_HELPERS = ROOT / "conformance/runner/_runner_context.py"
CONFORMANCE_RUNNER = ROOT / "conformance/runner/aicp_conformance_runner.py"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_runner_context_helper_module_exports_pointer_and_validator_helpers() -> None:
    helpers = _load_module(CONTEXT_HELPERS, "aicp_runner_context_test")

    assert helpers.normalize_pointer("#/$defs/PiiRef") == "/$defs/PiiRef"
    assert helpers.normalize_pointer("") == ""
    assert helpers.resolve_json_pointer({"a/b": {"~key": 7}}, "/a~1b/~0key") == 7


def test_runner_public_shims_preserve_pointer_helper_behavior() -> None:
    runner = _load_module(CONFORMANCE_RUNNER, "aicp_conformance_runner_modularity_test")
    helpers = _load_module(CONTEXT_HELPERS, "aicp_runner_context_shim_test")

    assert runner._normalize_pointer("#/$defs/PiiRef") == helpers.normalize_pointer("#/$defs/PiiRef")
    assert runner._resolve_json_pointer({"items": [{"value": 3}]}, "/items/0/value") == 3

    if runner.Draft202012Validator is None:
        return

    schema_path = ROOT / "schemas/extensions/ext-redaction-payloads.schema.json"
    pointer = "/$defs/PiiRef"
    via_runner = runner._validator_for_schema_path_pointer(str(schema_path.resolve()), pointer)
    via_helpers = helpers.validator_for_schema_path_pointer(str(schema_path.resolve()), pointer)
    assert type(via_runner) is type(via_helpers)


def test_run_suite_still_works_via_public_entrypoint() -> None:
    runner = _load_module(CONFORMANCE_RUNNER, "aicp_conformance_runner_run_suite_modularity_test")
    report = runner.run_suite(ROOT / "conformance/core/CT_CORE_0.1.json")

    assert report["passed"] is True
    assert report["suite_id"] == "CT-CORE-0.1"
