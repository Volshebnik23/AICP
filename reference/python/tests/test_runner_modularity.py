from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CONTEXT_HELPERS = ROOT / "conformance/runner/_runner_context.py"
IO_HELPERS = ROOT / "conformance/runner/_runner_io.py"
REPORTING_HELPERS = ROOT / "conformance/runner/_runner_reporting.py"
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


def test_runner_io_helpers_cover_repo_paths_reporting_and_json_write(tmp_path: Path) -> None:
    helpers = _load_module(IO_HELPERS, "aicp_runner_io_test")

    repo_relative = helpers.resolve_repo_path("conformance/report_modularity_test.json")
    assert repo_relative == (ROOT / "conformance/report_modularity_test.json").resolve()
    assert helpers.display_path(repo_relative) == "conformance/report_modularity_test.json"

    external = tmp_path / "outside.json"
    report = {"passed": True, "suite_id": "CT-CORE-0.1"}
    helpers.write_json_report(external, report)
    assert external.read_text(encoding="utf-8").endswith("\n")
    assert '  "passed": true' in external.read_text(encoding="utf-8")

    status = helpers.format_status_line("Conformance", "CT-CORE-0.1", repo_relative, True, False)
    degraded = helpers.format_status_line("Profile conformance", "AICP-BASE", repo_relative, True, True)
    assert status == "Conformance PASSED: CT-CORE-0.1 -> conformance/report_modularity_test.json"
    assert degraded == "Profile conformance PASSED (DEGRADED): AICP-BASE -> conformance/report_modularity_test.json"


def test_runner_reporting_helper_builds_expected_report_shape() -> None:
    helpers = _load_module(REPORTING_HELPERS, "aicp_runner_reporting_test")

    report = helpers.build_conformance_report(
        aicp_version="0.1",
        suite_id="CT-CORE-0.1",
        suite_version="0.1.0-dev",
        passed=True,
        failures=[],
        compatibility_marks=["AICP-Core-0.1"],
        degraded=False,
        degraded_reasons=[],
        skipped_checks=["CT-OPTIONAL-01"],
    )

    assert report["aicp_version"] == "0.1"
    assert report["suite_id"] == "CT-CORE-0.1"
    assert report["suite_version"] == "0.1.0-dev"
    assert report["passed"] is True
    assert report["failures"] == []
    assert report["compatibility_marks"] == ["AICP-Core-0.1"]
    assert report["degraded"] is False
    assert report["degraded_reasons"] == []
    assert report["skipped_checks"] == ["CT-OPTIONAL-01"]
    assert isinstance(report["timestamp"], str) and report["timestamp"]
