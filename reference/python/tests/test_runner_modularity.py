from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
CONTEXT_HELPERS = ROOT / "conformance/runner/_runner_context.py"
IO_HELPERS = ROOT / "conformance/runner/_runner_io.py"
REPORTING_HELPERS = ROOT / "conformance/runner/_runner_reporting.py"
ALERT_CHECK_HELPERS = ROOT / "conformance/runner/_runner_alert_checks.py"
CORE_CHECK_HELPERS = ROOT / "conformance/runner/_runner_core_checks.py"
ENFORCEMENT_CHECK_HELPERS = ROOT / "conformance/runner/_runner_enforcement_checks.py"
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


def test_runner_core_check_helper_preserves_basic_failure_shape() -> None:
    helpers = _load_module(CORE_CHECK_HELPERS, "aicp_runner_core_checks_test")
    failures: list[dict[str, object]] = []

    helpers.run_core_transcript_checks(
        rows=[
            (
                1,
                {
                    "session_id": "s1",
                    "message_id": "m1",
                    "message_type": "KNOWN",
                    "message_hash": "h1",
                    "contract_id": "c1",
                    "signatures": [{"object_hash": "wrong"}],
                },
            ),
            (
                2,
                {
                    "session_id": "s2",
                    "message_id": "m1",
                    "message_type": "UNKNOWN",
                    "message_hash": "h2",
                    "prev_msg_hash": "",
                    "contract_id": "",
                },
            ),
        ],
        transcript={"expected_message_types": ["KNOWN", "KNOWN"]},
        enabled_checks={"CT-MESSAGE-TYPE-REGISTRY-01", "CT-CONTRACT-ID-01", "CT-PREV-MSG-REQUIRED-01"},
        registered_message_types={"KNOWN"},
        rel_file="fixtures/test.jsonl",
        failures=failures,
    )

    assert failures == [
        {"test_id": "CT-MESSAGE-TYPE-REGISTRY-01", "message": "unregistered message_type 'UNKNOWN'", "file": "fixtures/test.jsonl", "line": 2},
        {"test_id": "CT-INVARIANTS-01", "message": "session_id changed within transcript", "file": "fixtures/test.jsonl", "line": 2},
        {"test_id": "CT-INVARIANTS-01", "message": "duplicate message_id 'm1'", "file": "fixtures/test.jsonl", "line": 2},
        {"test_id": "CT-CONTRACT-ID-01", "message": "contract_id must be a non-empty string", "file": "fixtures/test.jsonl", "line": 2},
        {"test_id": "CT-PREV-MSG-REQUIRED-01", "message": "prev_msg_hash is required and must be a non-empty string for non-first messages", "file": "fixtures/test.jsonl", "line": 2},
        {"test_id": "CT-HASH-CHAIN-01", "message": "prev_msg_hash mismatch (expected h1, got )", "file": "fixtures/test.jsonl", "line": 2},
        {"test_id": "CT-SEQUENCE-01", "message": "message_type sequence mismatch (expected ['KNOWN', 'KNOWN'], got ['KNOWN', 'UNKNOWN'])", "file": "fixtures/test.jsonl", "line": None},
        {"test_id": "CT-SIGNATURE-HASH-01", "message": "signatures.object_hash mismatch (expected h1, got wrong)", "file": "fixtures/test.jsonl", "line": 1},
    ]


def test_runner_enforcement_check_helper_preserves_failure_shape() -> None:
    helpers = _load_module(ENFORCEMENT_CHECK_HELPERS, "aicp_runner_enforcement_checks_test")
    failures: list[dict[str, object]] = []

    helpers.run_enforcement_transcript_checks(
        rows=[
            (
                1,
                {
                    "message_type": "ENFORCEMENT_VERDICT",
                    "payload": {
                        "target_message_hash": "target-1",
                        "sanctions": [{"code": "allowed"}, {"code": "unknown"}, {"code": 7}],
                    },
                },
            ),
            (
                2,
                {
                    "message_type": "ENFORCEMENT_VERDICT",
                    "payload": {
                        "target_message_hash": "target-1",
                        "sanctions": [{"code": "x-vendor.ok"}, {"code": "vendor:ok"}],
                    },
                },
            ),
        ],
        enabled_checks={"ENF-SANCTION-CODES-01", "ENF-VERDICT-STORM-01"},
        enforcement_sanction_codes={"allowed"},
        rel_file="fixtures/enforcement.jsonl",
        failures=failures,
    )

    assert failures == [
        {"test_id": "ENF-SANCTION-CODES-01", "message": "unknown sanction code 'unknown'", "file": "fixtures/enforcement.jsonl", "line": 1},
        {"test_id": "ENF-SANCTION-CODES-01", "message": "sanctions[].code must be a string", "file": "fixtures/enforcement.jsonl", "line": 1},
        {"test_id": "ENF-VERDICT-STORM-01", "message": "multiple ENFORCEMENT_VERDICT messages reference target_message_hash 'target-1'", "file": "fixtures/enforcement.jsonl", "line": 2},
    ]


def test_runner_alert_check_helper_preserves_failure_shape() -> None:
    helpers = _load_module(ALERT_CHECK_HELPERS, "aicp_runner_alert_checks_test")
    failures: list[dict[str, object]] = []

    helpers.run_alert_transcript_checks(
        rows=[
            (
                3,
                {
                    "message_type": "ALERT",
                    "payload": {
                        "code": "UNKNOWN",
                        "recommended_actions": ["BAD_ACTION"],
                        "message": "x" * 257,
                        "details": {"note": "ok"},
                    },
                },
            ),
            (
                4,
                {
                    "message_type": "ALERT",
                    "payload": {
                        "code": "KNOWN",
                        "recommended_actions": ["GOOD_ACTION"],
                        "details": {"large": "x" * 4100},
                    },
                },
            ),
        ],
        enabled_checks={"AL-ALERT-CODES-01", "AL-ALERT-ACTIONS-01", "AL-VERBOSITY-01"},
        alert_codes_registry={"KNOWN": {}},
        alert_recommended_actions={"GOOD_ACTION"},
        canonicalize_json_fn=lambda value: __import__("json").dumps(value, separators=(",", ":"), sort_keys=True),
        rel_file="fixtures/alerts.jsonl",
        failures=failures,
    )

    assert failures == [
        {"test_id": "AL-ALERT-CODES-01", "message": "unknown alert code 'UNKNOWN'", "file": "fixtures/alerts.jsonl", "line": 3},
        {"test_id": "AL-ALERT-ACTIONS-01", "message": "unknown recommended_action 'BAD_ACTION'", "file": "fixtures/alerts.jsonl", "line": 3},
        {"test_id": "AL-VERBOSITY-01", "message": "ALERT payload.message exceeds 256 characters (got 257)", "file": "fixtures/alerts.jsonl", "line": 3},
        {"test_id": "AL-VERBOSITY-01", "message": "ALERT payload.details canonical JSON exceeds 4096 bytes (got 4112)", "file": "fixtures/alerts.jsonl", "line": 4},
    ]
