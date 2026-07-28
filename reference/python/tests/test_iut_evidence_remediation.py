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
INTEROP_TOOLS_DIR = ROOT / "interop/tools"
for path in (IUT_DIR, RUNNER_DIR, SCRIPTS_DIR, INTEROP_TOOLS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from _runner_context import build_validator, load_json  # noqa: E402
from aicp_conformance_runner import run_suite  # noqa: E402
from aicp_iut_catalog import (  # noqa: E402
    CASES_PATH,
    expected_execution_observation,
    mandatory_case_ids,
    validate_catalog_coverage,
    validate_execution_accounting,
)
from aicp_iut_runner import (  # noqa: E402
    IUTProtocolError,
    build_execution_plan,
    invoke_adapter,
    run_iut,
)
from aicp_profile_runner import run_profile  # noqa: E402
from interop_matrix import build_matrix  # noqa: E402
from interop_submission_validation import (  # noqa: E402
    STRONG_PROFILE_CLAIM_EVIDENCE_ERROR,
    _validate_strong_report_evidence,
)
from generate_iut_tck_release_registry import (  # noqa: E402
    FROZEN_RELEASE_DIGESTS,
    _release_digest,
    build_registry,
)


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
        timeout_seconds=60,
    )
    assert report["passed"] is True, report["failures"]
    return report


def test_full_profile_catalog_counts_are_derived_and_complete() -> None:
    catalog = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    assert validate_catalog_coverage(catalog, "AICP-BASE@0.1") == []
    assert validate_catalog_coverage(catalog, "AICP-AUTHENTICATED-BASE@0.1") == []
    assert len(mandatory_case_ids(catalog, "AICP-BASE@0.1", "full-profile")) == 21
    assert len(mandatory_case_ids(catalog, "AICP-AUTHENTICATED-BASE@0.1", "full-profile")) == 37
    assert catalog["tck_release_id"] == "AICP-IUT-TCK-1.1.0"
    probe = next(
        item
        for item in catalog["profiles"]["AICP-AUTHENTICATED-BASE@0.1"][
            "full_profile"
        ]["consumer_cases"]
        if item["case_id"] == "AUTH-CRYPTO-UNAVAILABLE"
    )
    assert expected_execution_observation(probe) == {
        "scope": "case_local_expected",
        "accepted": True,
        "degraded": True,
        "degraded_reasons": [
            "Ed25519 verification backend unavailable for requested test mode"
        ],
        "skipped_checks": ["AUTH-SIGNATURE-VERIFY-01"],
    }


@pytest.mark.parametrize(
    ("mutation", "expected_error"),
    [
        (
            lambda case: case["expected_execution_observation"].pop("scope"),
            "fields must be exactly",
        ),
        (
            lambda case: case["expected_execution_observation"].update(
                {"scope": "run_level"}
            ),
            "unsupported execution accounting scope",
        ),
        (
            lambda case: case.update({"expected_degraded": True}),
            "legacy execution expectation fields",
        ),
        (
            lambda case: case.pop("expected_execution_observation"),
            "requires an explicit expected_execution_observation scope",
        ),
    ],
)
def test_catalog_rejects_ambiguous_case_accounting(
    mutation, expected_error: str
) -> None:
    catalog = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    probe = next(
        item
        for item in catalog["profiles"]["AICP-AUTHENTICATED-BASE@0.1"][
            "full_profile"
        ]["consumer_cases"]
        if item["case_id"] == "AUTH-CRYPTO-UNAVAILABLE"
    )
    mutation(probe)
    errors = validate_execution_accounting(probe)
    assert any(expected_error in error for error in errors)


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
    assert external_auth_report["degraded"] is False
    assert external_auth_report["degraded_reasons"] == []
    assert external_auth_report["skipped_checks"] == []
    assert external_auth_report["compatibility_marks"] == [
        "AICP-Profile-AUTHENTICATED-BASE-0.1"
    ]
    probe = next(
        item
        for item in external_auth_report["case_results"]
        if item["case_id"] == "AUTH-CRYPTO-UNAVAILABLE"
    )
    assert probe["execution_observation"] == {
        "scope": "case_local_expected",
        "accepted": True,
        "degraded": True,
        "degraded_reasons": [
            "Ed25519 verification backend unavailable for requested test mode"
        ],
        "skipped_checks": ["AUTH-SIGNATURE-VERIFY-01"],
    }
    reference = run_iut(
        _cmd(str(IUT_DIR / "reference_adapter.py")),
        "AICP-BASE@0.1",
        mode="full-profile",
    )
    assert reference["passed"] is True
    assert reference["execution_subject"]["kind"] == "reference_corpus"
    assert reference["compatibility_marks"] == []


@pytest.mark.parametrize(
    "fixture_name", ["external_base_report", "external_auth_report"]
)
def test_every_consumer_case_has_one_structured_observation(
    fixture_name: str, request: pytest.FixtureRequest
) -> None:
    report = request.getfixturevalue(fixture_name)
    catalog = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    target = (
        f"{report['profile']['profile_id']}@{report['profile']['profile_version']}"
    )
    consumer_ids = {
        item["case_id"]
        for item in catalog["profiles"][target]["full_profile"]["consumer_cases"]
    }
    observed_ids = {
        item["case_id"]
        for item in report["case_results"]
        if "execution_observation" in item
    }
    assert observed_ids == consumer_ids
    for result in report["case_results"]:
        if result["case_id"] in consumer_ids:
            assert set(result["execution_observation"]) == {
                "scope",
                "accepted",
                "degraded",
                "degraded_reasons",
                "skipped_checks",
            }
        else:
            assert "execution_observation" not in result


@pytest.mark.parametrize(
    "mode",
    [
        "crypto_probe_not_degraded",
        "crypto_probe_missing_reason",
        "crypto_probe_wrong_reason",
        "crypto_probe_missing_skip",
        "crypto_probe_extra_skip",
        "normal_auth_crypto_unavailable",
        "authenticated_producer_crypto_unavailable",
    ],
)
def test_authenticated_accounting_fakes_fail_without_marks(mode: str) -> None:
    report = run_iut(
        _fake(mode),
        "AICP-AUTHENTICATED-BASE@0.1",
        mode="full-profile",
        timeout_seconds=60,
    )
    assert report["passed"] is False
    assert report["compatibility_marks"] == []
    if mode.startswith("crypto_probe_"):
        probe = next(
            item
            for item in report["case_results"]
            if item["case_id"] == "AUTH-CRYPTO-UNAVAILABLE"
        )
        assert probe["passed"] is False
        assert report["degraded"] is False
        assert report["degraded_reasons"] == []
        assert report["skipped_checks"] == []
    if mode == "normal_auth_crypto_unavailable":
        assert report["degraded"] is True
        assert report["skipped_checks"] == ["AUTH-SIGNATURE-VERIFY-01"]


def test_explicit_good_probe_fake_mode_is_mark_eligible() -> None:
    report = run_iut(
        _fake("crypto_probe_good"),
        "AICP-AUTHENTICATED-BASE@0.1",
        mode="full-profile",
        timeout_seconds=60,
    )
    assert report["passed"] is True
    assert report["degraded"] is False
    assert report["skipped_checks"] == []
    assert report["compatibility_marks"] == [
        "AICP-Profile-AUTHENTICATED-BASE-0.1"
    ]


def test_actual_runner_crypto_unavailability_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from aicp_ref import signatures

    monkeypatch.setattr(signatures, "Ed25519PublicKey", None)
    report = run_iut(
        _fake("external_good"),
        "AICP-AUTHENTICATED-BASE@0.1",
        mode="full-profile",
        timeout_seconds=60,
    )
    assert report["passed"] is False
    assert report["compatibility_marks"] == []
    assert any(
        "validation was degraded" in failure["message"]
        or "verification unavailable" in failure["message"]
        for failure in report["failures"]
    )


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
    report = run_iut(_fake(mode), profile, mode="full-profile", timeout_seconds=60)
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
    producer_requests = [item for item in requests if item["operation"] == "generate_scenario"]
    assert len(producer_requests) == 12
    assert len({item["request_id"] for item in producer_requests}) == 12
    for first, repeat in zip(producer_requests[::2], producer_requests[1::2]):
        assert first["input"] == repeat["input"]


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
    "mode,match,timeout_seconds",
    [
        ("stdout_overflow", "stdout exceeded", 10.0),
        ("stderr_overflow", "stderr exceeded", 10.0),
        ("partial_hang", "timed out", 2.0),
        ("early_exit", "exited before consuming|returned 0 responses", 10.0),
    ],
)
def test_process_supervision_fails_closed(
    mode: str, match: str, timeout_seconds: float
) -> None:
    with pytest.raises(IUTProtocolError, match=match):
        invoke_adapter(
            _fake(mode),
            _probe_request(200_000 if mode == "early_exit" else 0),
            timeout_seconds=timeout_seconds,
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


def test_complete_authenticated_external_report_is_strong_evidence_eligible(
    tmp_path: Path, external_auth_report: dict
) -> None:
    schema_path = IUT_DIR / "iut_report_v1.schema.json"
    validator = build_validator(load_json(schema_path), schema_path)
    assert validator is not None
    validator.validate(external_auth_report)
    assert _validate_report(tmp_path, external_auth_report) == []


@pytest.mark.parametrize(
    ("name", "mutate"),
    [
        (
            "missing_probe_observation",
            lambda report, probe: probe.pop("execution_observation"),
        ),
        (
            "wrong_observation_scope",
            lambda report, probe: probe["execution_observation"].update(
                {"scope": "normal"}
            ),
        ),
        (
            "wrong_probe_degraded",
            lambda report, probe: probe["execution_observation"].update(
                {"degraded": False}
            ),
        ),
        (
            "wrong_probe_accepted",
            lambda report, probe: probe["execution_observation"].update(
                {"accepted": False}
            ),
        ),
        (
            "wrong_probe_reason",
            lambda report, probe: probe["execution_observation"].update(
                {"degraded_reasons": ["wrong reason"]}
            ),
        ),
        (
            "missing_probe_skip",
            lambda report, probe: probe["execution_observation"].update(
                {"skipped_checks": []}
            ),
        ),
        (
            "additional_probe_skip",
            lambda report, probe: probe["execution_observation"].update(
                {
                    "skipped_checks": [
                        "AUTH-SIGNATURE-VERIFY-01",
                        "AUTH-UNEXPECTED-SKIP",
                    ]
                }
            ),
        ),
        (
            "observation_on_wrong_case",
            lambda report, probe: report["case_results"][0].update(
                {
                    "execution_observation": {
                        "scope": "normal",
                        "accepted": True,
                        "degraded": False,
                        "degraded_reasons": [],
                        "skipped_checks": [],
                    }
                }
            ),
        ),
        (
            "probe_copied_to_top_level",
            lambda report, probe: report.update(
                {
                    "degraded": True,
                    "degraded_reasons": list(
                        probe["execution_observation"]["degraded_reasons"]
                    ),
                    "skipped_checks": list(
                        probe["execution_observation"]["skipped_checks"]
                    ),
                }
            ),
        ),
        (
            "malformed_probe_skip_type",
            lambda report, probe: probe["execution_observation"].update(
                {"skipped_checks": "AUTH-SIGNATURE-VERIFY-01"}
            ),
        ),
        (
            "unexpected_probe_field",
            lambda report, probe: probe["execution_observation"].update(
                {"unregistered": True}
            ),
        ),
        (
            "modified_normal_observation",
            lambda report, probe: next(
                item
                for item in report["case_results"]
                if item.get("execution_observation", {}).get("scope") == "normal"
            )["execution_observation"].update(
                {
                    "degraded": True,
                    "degraded_reasons": ["forged"],
                    "skipped_checks": ["AUTH-SIGNATURE-VERIFY-01"],
                }
            ),
        ),
    ],
)
def test_strong_evidence_rejects_forged_authenticated_observations(
    tmp_path: Path,
    external_auth_report: dict,
    name: str,
    mutate,
) -> None:
    candidate = copy.deepcopy(external_auth_report)
    probe = next(
        item
        for item in candidate["case_results"]
        if item["case_id"] == "AUTH-CRYPTO-UNAVAILABLE"
    )
    mutate(candidate, probe)
    errors = _validate_report(tmp_path, candidate)
    assert errors, name


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
    add("wrong_repeat_digest", lambda report: report["generated_artifacts"][0].update({"repeat_content_digest": "sha256:" + "0" * 64}))
    add("reference_subject", lambda report: report["execution_subject"].update({"kind": "reference_corpus"}))
    add("degraded", lambda report: report.update({"degraded": True, "degraded_reasons": ["test"]}))
    add("skipped", lambda report: report.update({"skipped_checks": ["MANDATORY"]}))

    for name, mutate in mutations:
        candidate = copy.deepcopy(external_base_report)
        mutate(candidate)
        errors = _validate_report(tmp_path, candidate)
        assert errors, name


@pytest.mark.parametrize("claim_type", ["implements_profile", "compatible_with_profile"])
def test_self_attested_strong_profile_claims_fail_closed(
    tmp_path: Path, external_base_report: dict, claim_type: str
) -> None:
    manifest = _manifest_for(external_base_report)
    manifest.update({"claim_type": claim_type, "evidence_status": "self_attested"})
    errors = _validate_report(tmp_path, external_base_report, manifest)
    assert errors == [STRONG_PROFILE_CLAIM_EVIDENCE_ERROR]


def test_reproducible_strong_claim_without_eligible_report_is_rejected(tmp_path: Path) -> None:
    package = tmp_path / "empty"
    package.mkdir()
    manifest = {
        "implementation_id": "external-a",
        "implementation_version": "1.0.0",
        "profile_refs": [{"profile_id": "AICP-BASE", "profile_version": "0.1"}],
        "report_refs": [],
        "claim_type": "implements_profile",
        "evidence_status": "reproducible",
    }
    errors = _validate_strong_report_evidence(package / "submission.json", manifest)
    assert any("no eligible external IUT report" in error for error in errors)


def test_smoke_report_cannot_prove_compatible_with_profile(
    tmp_path: Path, external_base_report: dict
) -> None:
    report = copy.deepcopy(external_base_report)
    report["execution_mode"] = "smoke"
    report["compatibility_marks"] = []
    manifest = _manifest_for(report)
    manifest["claim_type"] = "compatible_with_profile"
    errors = _validate_report(tmp_path, report, manifest)
    assert any("IUT_SMOKE_EVIDENCE_INELIGIBLE" in error for error in errors)


def test_matrix_computes_only_independently_eligible_marks(
    tmp_path: Path, external_base_report: dict
) -> None:
    submissions = tmp_path / "submissions"

    def write_package(name: str, report: dict, *, evidence_status: str = "reproducible") -> None:
        package = submissions / name
        reports = package / "reports"
        reports.mkdir(parents=True)
        (reports / "iut.json").write_text(json.dumps(report), encoding="utf-8")
        manifest = _manifest_for(external_base_report)
        manifest.update(
            {
                "submission_id": name,
                "evidence_status": evidence_status,
                "report_refs": ["reports/iut.json"],
            }
        )
        (package / "submission.json").write_text(json.dumps(manifest), encoding="utf-8")

    write_package("eligible", external_base_report)
    hand_shaped = {
        "compatibility_marks": ["AICP-Profile-BASE-0.1"],
        "passed": True,
    }
    write_package("hand-shaped", hand_shaped)
    write_package("self-attested", external_base_report, evidence_status="self_attested")

    entries = {item["folder"]: item for item in build_matrix(submissions)["real_submissions"]}
    assert entries["eligible"]["computed_marks"] == ["AICP-Profile-BASE-0.1"]
    assert entries["eligible"]["evidence_validation_status"] == "eligible"
    for name in ("hand-shaped", "self-attested"):
        assert entries[name]["computed_marks"] == []
        assert entries[name]["evidence_validation_status"] == "rejected"
        assert any(item["error_code"] == "STRONG_EVIDENCE_INELIGIBLE" for item in entries[name]["errors"])


def test_generated_tck_registry_preserves_1_0_and_recomputes_current_release() -> None:
    committed = json.loads((IUT_DIR / "tck_releases.json").read_text(encoding="utf-8"))
    assert committed == build_registry()
    assert [release["release_id"] for release in committed["releases"]] == [
        "AICP-IUT-TCK-1.0.0",
        "AICP-IUT-TCK-1.1.0",
    ]
    historical = committed["releases"][0]
    assert _release_digest(historical) == FROZEN_RELEASE_DIGESTS[
        "AICP-IUT-TCK-1.0.0"
    ]
    release = committed["releases"][1]
    for record in [release["case_catalog"]]:
        assert (ROOT / record["path"]).is_file()
    for path in release["runner_bundle"]["paths"]:
        assert (ROOT / path).is_file()
    for profile in release["profiles"].values():
        records = [
            profile["profile_catalog"],
            *profile["required_suites"],
            *profile["required_input_artifacts"],
        ]
        for record in records:
            assert (ROOT / record["path"]).is_file()


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
