from __future__ import annotations

import copy
import json
import sys
import time
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
IUT_DIR = ROOT / "conformance/iut"
RUNNER_DIR = ROOT / "conformance/runner"
SCRIPTS_DIR = ROOT / "scripts"
for path in (IUT_DIR, RUNNER_DIR, SCRIPTS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from _runner_context import build_validator, load_json  # noqa: E402
from aicp_conformance_runner import run_suite  # noqa: E402
from aicp_iut_catalog import CASES_PATH, mandatory_case_ids, validate_catalog_coverage  # noqa: E402
from aicp_iut_runner import (  # noqa: E402
    IUTProtocolError,
    build_execution_plan,
    invoke_adapter,
    run_iut,
)
from aicp_profile_runner import run_profile  # noqa: E402
from interop_submission_validation import _validate_strong_report_evidence  # noqa: E402


def _cmd(*parts: str) -> list[str]:
    return [sys.executable, *parts]


def _fake(mode: str) -> list[str]:
    return _cmd(str(IUT_DIR / "fakes/fake_adapter.py"), "--mode", mode)


@pytest.fixture(scope="module")
def external_base_report() -> dict:
    report = run_iut(_fake("external_good"), "AICP-BASE@0.1", mode="full-profile")
    assert report["passed"] is True, report["failures"]
    return report


@pytest.fixture(scope="module")
def external_auth_report() -> dict:
    report = run_iut(
        _fake("external_good"),
        "AICP-AUTHENTICATED-BASE@0.1",
        mode="full-profile",
    )
    assert report["passed"] is True, report["failures"]
    return report


def test_full_profile_catalog_counts_are_derived_and_complete() -> None:
    catalog = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    assert validate_catalog_coverage(catalog, "AICP-BASE@0.1") == []
    assert validate_catalog_coverage(catalog, "AICP-AUTHENTICATED-BASE@0.1") == []
    assert len(mandatory_case_ids(catalog, "AICP-BASE@0.1", "full-profile")) == 21
    assert len(mandatory_case_ids(catalog, "AICP-AUTHENTICATED-BASE@0.1", "full-profile")) == 37


@pytest.mark.parametrize("profile", ["AICP-BASE@0.1", "AICP-AUTHENTICATED-BASE@0.1"])
def test_external_smoke_never_emits_product_profile_mark(profile: str) -> None:
    report = run_iut(_fake("external_good"), profile, mode="smoke")
    assert report["passed"] is True
    assert report["execution_mode"] == "smoke"
    assert report["execution_subject"]["kind"] == "external_implementation"
    assert report["compatibility_marks"] == []


def test_full_profile_marks_require_external_complete_coverage(
    external_base_report: dict,
    external_auth_report: dict,
) -> None:
    assert len(external_base_report["case_results"]) == 21
    assert external_base_report["compatibility_marks"] == ["AICP-Profile-BASE-0.1"]
    assert len(external_auth_report["case_results"]) == 37
    assert external_auth_report["compatibility_marks"] == [
        "AICP-Profile-AUTHENTICATED-BASE-0.1"
    ]
    reference = run_iut(
        _cmd(str(IUT_DIR / "reference_adapter.py")),
        "AICP-BASE@0.1",
        mode="full-profile",
    )
    assert reference["passed"] is True
    assert reference["execution_subject"]["kind"] == "reference_corpus"
    assert reference["compatibility_marks"] == []


@pytest.mark.parametrize(
    "mode,profile",
    [
        ("incomplete_core", "AICP-BASE@0.1"),
        ("incomplete_authenticated", "AICP-AUTHENTICATED-BASE@0.1"),
        ("missing_mandatory_case_support", "AICP-BASE@0.1"),
        ("wrong_canonicalization", "AICP-BASE@0.1"),
        ("accepts_invalid_signature", "AICP-AUTHENTICATED-BASE@0.1"),
        ("forged_metadata", "AICP-BASE@0.1"),
    ],
)
def test_full_profile_rejects_deliberately_incomplete_or_forged_adapters(
    mode: str, profile: str
) -> None:
    report = run_iut(_fake(mode), profile, mode="full-profile")
    assert report["passed"] is False
    assert report["compatibility_marks"] == []


def test_adapter_requests_do_not_leak_runner_answers() -> None:
    _, requests, _ = build_execution_plan(
        "AICP-AUTHENTICATED-BASE@0.1", "full-profile"
    )
    forbidden_keys = {"case_id", "fixture", "expected_accept", "accepted"}
    for request in requests:
        input_obj = request["input"]
        if request["operation"] == "validate_transcript":
            assert set(input_obj) == {
                "target_profile",
                "transcript",
                "public_verification_material",
                "runtime_options",
            }
            assert not forbidden_keys.intersection(input_obj)
        if request["operation"] == "generate_scenario":
            assert set(input_obj) == {"target_profile", "scenario"}
            assert not forbidden_keys.intersection(input_obj["scenario"])
        serialized = json.dumps(input_obj, ensure_ascii=False)
        assert "fixtures/" not in serialized
        assert "_expected_fail" not in serialized
        assert "AUTH-AB-" not in serialized
        assert "AUTH-CORE-GT-" not in serialized


def _probe_request(payload_size: int = 0) -> list[dict]:
    return [
        {
            "adapter_protocol_version": "1.1",
            "request_id": "opaque-1",
            "operation": "describe",
            "input": {"padding": "x" * payload_size},
        }
    ]


def test_never_read_stdin_is_bounded_across_large_pipe_write() -> None:
    started = time.monotonic()
    with pytest.raises(IUTProtocolError, match="timed out"):
        invoke_adapter(
            _fake("never_reads_stdin"),
            _probe_request(2_000_000),
            timeout_seconds=0.3,
            max_stdout_bytes=4096,
            max_stderr_bytes=4096,
        )
    assert time.monotonic() - started < 3.0


@pytest.mark.parametrize(
    "mode,match",
    [
        ("stdout_overflow", "stdout exceeded"),
        ("stderr_overflow", "stderr exceeded"),
        ("partial_hang", "timed out"),
        ("early_exit", "exited before consuming|returned 0 responses"),
    ],
)
def test_process_supervision_fails_closed(mode: str, match: str) -> None:
    with pytest.raises(IUTProtocolError, match=match):
        invoke_adapter(
            _fake(mode),
            _probe_request(200_000 if mode == "early_exit" else 0),
            timeout_seconds=2.0,
            max_stdout_bytes=4096,
            max_stderr_bytes=4096,
        )


def _manifest_for(report: dict) -> dict:
    subject = report["execution_subject"]
    profile = report["profile"]
    return {
        "implementation_id": subject["implementation_id"],
        "implementation_version": subject["implementation_version"],
        "profile_refs": [
            {
                "profile_id": profile["profile_id"],
                "profile_version": profile["profile_version"],
            }
        ],
        "report_refs": ["reports/iut.json"],
        "claim_type": "implements_profile",
        "evidence_status": "reproducible",
    }


def _validate_report(tmp_path: Path, report: dict, manifest: dict | None = None) -> list[str]:
    package = tmp_path / f"package-{time.time_ns()}"
    reports = package / "reports"
    reports.mkdir(parents=True)
    (reports / "iut.json").write_text(json.dumps(report), encoding="utf-8")
    selected_manifest = manifest or _manifest_for(report)
    return _validate_strong_report_evidence(package / "submission.json", selected_manifest)


def test_complete_external_report_is_schema_and_eligibility_valid(
    tmp_path: Path, external_base_report: dict
) -> None:
    schema_path = IUT_DIR / "iut_report_v1.schema.json"
    validator = build_validator(load_json(schema_path), schema_path)
    assert validator is not None
    validator.validate(external_base_report)
    assert _validate_report(tmp_path, external_base_report) == []


def test_strong_evidence_rejects_incomplete_coverage_and_forged_provenance(
    tmp_path: Path, external_base_report: dict
) -> None:
    mutations = []

    def add(name, mutate):
        mutations.append((name, mutate))

    add("missing_case_results", lambda report: report.pop("case_results"))
    add("missing_timestamp", lambda report: report.pop("timestamp"))
    add("missing_generated", lambda report: report.pop("generated_artifacts"))
    add("duplicate_case", lambda report: report["case_results"].append(copy.deepcopy(report["case_results"][0])))
    add("omitted_case", lambda report: report["case_results"].pop())
    add("failed_case", lambda report: report["case_results"][0].update({"passed": False}))
    add("unknown_case", lambda report: report["case_results"][0].update({"case_id": "UNKNOWN-SUBSTITUTE"}))
    add("forged_mark", lambda report: report["compatibility_marks"].append("AICP-Profile-FAKE-0.1"))
    add("wrong_profile_digest", lambda report: report["profile"].update({"profile_digest": "sha256:" + "0" * 64}))
    add("wrong_case_catalog", lambda report: report["suite"].update({"suite_digest": "sha256:" + "0" * 64}))
    add("wrong_input_digest", lambda report: report["input_artifacts"][0].update({"content_digest": "sha256:" + "0" * 64}))
    add("wrong_runner_digest", lambda report: report["runner"].update({"source_revision": "sha256:" + "0" * 64}))
    add("wrong_tck_registry_digest", lambda report: report["tck_release"].update({"registry_digest": "sha256:" + "0" * 64}))
    add("wrong_tck_runner_digest", lambda report: report["tck_release"].update({"runner_bundle_digest": "sha256:" + "0" * 64}))
    add("wrong_tck_case_digest", lambda report: report["tck_release"].update({"case_catalog_digest": "sha256:" + "0" * 64}))
    add("wrong_generated_digest", lambda report: report["generated_artifacts"][0].update({"content_digest": "sha256:" + "0" * 64}))
    add("reference_subject", lambda report: report["execution_subject"].update({"kind": "reference_corpus"}))
    add("degraded", lambda report: report.update({"degraded": True, "degraded_reasons": ["test"]}))
    add("skipped", lambda report: report.update({"skipped_checks": ["MANDATORY"]}))

    for name, mutate in mutations:
        candidate = copy.deepcopy(external_base_report)
        mutate(candidate)
        errors = _validate_report(tmp_path, candidate)
        assert errors, name


def test_subject_version_mismatch_is_rejected(
    tmp_path: Path, external_base_report: dict
) -> None:
    manifest = _manifest_for(external_base_report)
    manifest["implementation_version"] = "different-version"
    errors = _validate_report(tmp_path, external_base_report, manifest)
    assert any("implementation_version" in error for error in errors)


def test_legacy_uat_reports_remain_default_and_v1_is_opt_in() -> None:
    suite_path = ROOT / "conformance/core/CT_CORE_0.1.json"
    legacy = run_suite(suite_path)
    assert "report_format_version" not in legacy
    assert set(legacy).issuperset({"aicp_version", "suite_id", "suite_version", "passed"})
    provenance = run_suite(suite_path, report_format="v1")
    assert provenance["report_format_version"] == "1.0"
    profile_path = ROOT / "conformance/profiles/PF_AICP_BASE_0.1.json"
    legacy_profile = run_profile(profile_path)
    assert "report_format_version" not in legacy_profile
    provenance_profile = run_profile(profile_path, report_format="v1")
    assert provenance_profile["report_format_version"] == "1.0"
