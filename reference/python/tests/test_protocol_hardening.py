from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
RUNNER_DIR = ROOT / "conformance/runner"
IUT_DIR = ROOT / "conformance/iut"
SCRIPTS_DIR = ROOT / "scripts"
for path in (RUNNER_DIR, IUT_DIR, SCRIPTS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from _runner_context import build_validator, load_json  # noqa: E402
from aicp_conformance_runner import run_suite  # noqa: E402
from aicp_iut_runner import IUTProtocolError, invoke_adapter, run_iut  # noqa: E402
from interop_submission_validation import _validate_strong_report_evidence, compute_file_digest  # noqa: E402


def _cmd(*parts: str) -> list[str]:
    return [sys.executable, *parts]


@pytest.mark.parametrize(
    "suite_ref",
    [
        "conformance/extensions/OR_SESSION_STATE_PROJECTION_V1.json",
        "conformance/extensions/OR_OBJECT_RESYNC_0.1.json",
        "conformance/security/AUTH_AUTHENTICATED_MESSAGES_0.1.json",
        "conformance/extensions/CN_CAPNEG_0.1.json",
    ],
)
def test_hardening_suites_pass(suite_ref: str) -> None:
    report = run_suite(ROOT / suite_ref)
    assert report["passed"] is True, report["failures"]
    assert "report_format_version" not in report
    provenance = run_suite(ROOT / suite_ref, report_format="v1")
    assert provenance["report_format_version"] == "1.0"
    assert provenance["execution_subject"]["kind"] == "reference_corpus"
    assert provenance["suite"]["suite_digest"].startswith("sha256:")
    assert all(item["content_digest"].startswith("sha256:") for item in provenance["input_artifacts"])


def test_authenticated_suite_degrades_without_crypto_and_suppresses_marks(monkeypatch) -> None:
    runner_path = RUNNER_DIR / "aicp_conformance_runner.py"
    spec = importlib.util.spec_from_file_location("aicp_auth_degraded_runner", runner_path)
    assert spec and spec.loader
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    monkeypatch.setattr(runner, "signature_verifier_available", lambda: False)
    report = runner.run_suite(ROOT / "conformance/security/AUTH_AUTHENTICATED_MESSAGES_0.1.json")
    assert report["passed"] is True
    assert report["degraded"] is True
    assert report["compatibility_marks"] == []
    assert "AUTH-SIGNATURE-VERIFY-01" in report["skipped_checks"]


def test_sandbox_no_crypto_still_rejects_structural_signature_mismatch() -> None:
    result = subprocess.run(
        _cmd(
            str(ROOT / "sandbox/run.py"),
            str(ROOT / "fixtures/security/authenticated_base/AB-07_signature_object_hash_mismatch_expected_fail.jsonl"),
            "--no-signature-verify",
        ),
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    assert result.returncode == 1
    assert "signature.object_hash mismatch at signatures[0]" in result.stdout


@pytest.mark.parametrize(
    ("fixture", "expected"),
    [
        ("AB-10_kid_mismatch_expected_fail.jsonl", "kid"),
        ("AB-12_invalid_signature_expected_fail.jsonl", "signature verification failed"),
        ("AB-13_copied_signature_expected_fail.jsonl", "object_hash mismatch"),
    ],
)
def test_sandbox_crypto_rejects_key_and_signature_failures(fixture: str, expected: str) -> None:
    result = subprocess.run(
        _cmd(str(ROOT / "sandbox/run.py"), str(ROOT / "fixtures/security/authenticated_base" / fixture)),
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    assert result.returncode == 1
    assert expected in result.stdout


def test_sandbox_crypto_rejects_missing_public_key(tmp_path: Path) -> None:
    key_map = tmp_path / "keys.json"
    key_map.write_text("{}\n", encoding="utf-8")
    result = subprocess.run(
        _cmd(
            str(ROOT / "sandbox/run.py"),
            str(ROOT / "fixtures/security/authenticated_base/AB-01_valid_sender_signed.jsonl"),
            "--keys",
            str(key_map),
        ),
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        capture_output=True,
        check=False,
    )
    assert result.returncode == 1
    assert "missing public key" in result.stdout


def test_iut_reference_adapter_passes_without_external_marks() -> None:
    report = run_iut(
        _cmd(str(IUT_DIR / "reference_adapter.py")),
        "AICP-AUTHENTICATED-BASE@0.1",
        mode="full-profile",
        timeout_seconds=20,
    )
    assert report["passed"] is True
    assert report["execution_subject"]["kind"] == "reference_corpus"
    assert report["compatibility_marks"] == []
    assert len(report["case_results"]) == 37
    schema_path = IUT_DIR / "iut_report_v1.schema.json"
    validator = build_validator(load_json(schema_path), schema_path)
    assert validator is not None
    validator.validate(report)


@pytest.mark.parametrize(
    ("mode", "profile", "include_state", "expected_case"),
    [
        ("wrong_canonicalization", "AICP-BASE@0.1", False, "AICP-JCS-UNICODE-KEY-ORDER-01"),
        ("accepts_invalid_chain", "AICP-BASE@0.1", False, "BASE-CORE-GT-09"),
        ("accepts_invalid_signature", "AICP-AUTHENTICATED-BASE@0.1", False, "AUTH-"),
        ("mismatched_projection", "AICP-BASE@0.1", True, "SESSION-STATE-PROJECTION-V1-PRODUCER"),
        ("lies_metadata", "AICP-BASE@0.1", False, "IUT-DESCRIBE-STABILITY-01"),
    ],
)
def test_iut_fake_adapters_are_rejected(
    mode: str, profile: str, include_state: bool, expected_case: str
) -> None:
    report = run_iut(
        _cmd(str(IUT_DIR / "fakes/fake_adapter.py"), "--mode", mode),
        profile,
        mode="smoke" if include_state else "full-profile",
        include_session_state_projection=include_state,
        timeout_seconds=60,
    )
    assert report["passed"] is False
    assert report["compatibility_marks"] == []
    assert any(expected_case in failure["test_id"] for failure in report["failures"])


@pytest.mark.parametrize(
    ("mode", "profile"),
    [
        ("skipped_without_degraded", "AICP-BASE@0.1"),
        ("degraded_reason_without_degraded", "AICP-BASE@0.1"),
        ("wrong_degraded_skip", "AICP-AUTHENTICATED-BASE@0.1"),
        ("missing_skipped_checks_field", "AICP-BASE@0.1"),
        ("wrong_producer_session", "AICP-BASE@0.1"),
        ("wrong_producer_contract", "AICP-BASE@0.1"),
        ("undeclared_producer_sender", "AICP-BASE@0.1"),
        ("unsigned_authenticated_producer", "AICP-AUTHENTICATED-BASE@0.1"),
        ("nondeterministic_producer", "AICP-BASE@0.1"),
    ],
)
def test_iut_truthfulness_fakes_fail_without_marks(mode: str, profile: str) -> None:
    report = run_iut(
        _cmd(str(IUT_DIR / "fakes/fake_adapter.py"), "--mode", mode),
        profile,
        mode="full-profile",
        timeout_seconds=60,
    )
    assert report["passed"] is False
    assert report["compatibility_marks"] == []
    if mode == "skipped_without_degraded":
        assert "MANDATORY" in report["skipped_checks"]


def test_full_profile_overlay_rejected_before_adapter_launch(monkeypatch) -> None:
    def unexpected_launch(*args, **kwargs):
        raise AssertionError("adapter must not launch")

    monkeypatch.setattr("aicp_iut_runner.invoke_adapter", unexpected_launch)
    with pytest.raises(IUTProtocolError, match="FULL_PROFILE_OVERLAYS_NOT_SUPPORTED"):
        run_iut(
            _cmd(str(IUT_DIR / "reference_adapter.py")),
            "AICP-BASE@0.1",
            mode="full-profile",
            include_session_state_projection=True,
        )


def test_adapter_protocol_schema_identifier_matches_version() -> None:
    schema = json.loads((IUT_DIR / "adapter_protocol.schema.json").read_text(encoding="utf-8"))
    assert schema["$id"] == "https://aicp.dev/schemas/iut-adapter-protocol-1.1.json"
    assert schema["$defs"]["Request"]["properties"]["adapter_protocol_version"]["const"] == "1.1"


def test_iut_timeout_is_bounded() -> None:
    with pytest.raises(IUTProtocolError, match="timed out"):
        run_iut(
            _cmd(str(IUT_DIR / "fakes/fake_adapter.py"), "--mode", "timeout"),
            "AICP-BASE@0.1",
            mode="smoke",
            timeout_seconds=0.1,
        )


def test_iut_protocol_rejects_unframed_non_json_stdout() -> None:
    with pytest.raises(IUTProtocolError, match="not deterministic JSON"):
        invoke_adapter(
            _cmd("-c", "print('not-json')"),
            [{"adapter_protocol_version": "1.0", "request_id": "x", "operation": "describe", "input": {}}],
            timeout_seconds=2,
            max_stdout_bytes=1024,
            max_stderr_bytes=1024,
        )


def test_incomplete_strong_interop_evidence_is_rejected(tmp_path: Path) -> None:
    profile_path = ROOT / "conformance/profiles/PF_AICP_BASE_0.1.json"
    profile_digest = "sha256:" + compute_file_digest(profile_path)
    iut_cases_path = ROOT / "conformance/iut/cases.json"
    iut_cases = json.loads(iut_cases_path.read_text(encoding="utf-8"))
    vector_ref = iut_cases["canonicalization_vectors"][0]
    report = {
        "report_format_version": "1.0",
        "execution_subject": {
            "kind": "external_implementation",
            "implementation_id": "external-a",
            "implementation_version": "1.2.3",
            "implementation_digest": "sha256:external-build",
        },
        "runner": {"name": "aicp-iut-runner", "version": "1.0", "source_revision": "sha256:runner"},
        "suite": {
            "suite_id": iut_cases["suite_id"],
            "suite_version": iut_cases["suite_version"],
            "suite_digest": "sha256:" + compute_file_digest(iut_cases_path),
        },
        "profile": {"profile_id": "AICP-BASE", "profile_version": "0.1", "profile_digest": profile_digest},
        "input_artifacts": [{"path": vector_ref, "content_digest": "sha256:" + compute_file_digest(ROOT / vector_ref)}],
        "passed": True,
        "degraded": False,
        "skipped_checks": [],
        "compatibility_marks": ["AICP-Profile-BASE-0.1"],
    }
    package = tmp_path / "external-a"
    reports = package / "reports"
    reports.mkdir(parents=True)
    (reports / "iut.json").write_text(json.dumps(report), encoding="utf-8")
    manifest = {
        "implementation_id": "external-a",
        "implementation_version": "1.2.3",
        "profile_refs": [{"profile_id": "AICP-BASE", "profile_version": "0.1"}],
        "report_refs": ["reports/iut.json"],
        "claim_type": "implements_profile",
        "evidence_status": "reproducible",
    }
    errors = _validate_strong_report_evidence(package / "submission.json", manifest)
    assert any("IUT_REPORT_SCHEMA_INVALID" in error for error in errors)
    manifest["implementation_version"] = "1.2.4"
    errors = _validate_strong_report_evidence(package / "submission.json", manifest)
    assert any("no eligible external IUT report" in error for error in errors)


def test_pairwise_interop_fails_closed_without_joint_execution(tmp_path: Path) -> None:
    profile_path = ROOT / "conformance/profiles/PF_AICP_BASE_0.1.json"
    digest = "sha256:" + compute_file_digest(profile_path)
    iut_cases_path = ROOT / "conformance/iut/cases.json"
    iut_cases = json.loads(iut_cases_path.read_text(encoding="utf-8"))
    vector_ref = iut_cases["canonicalization_vectors"][0]

    def report(subject: str, version: str) -> dict[str, object]:
        return {
            "report_format_version": "1.0",
            "execution_subject": {
                "kind": "external_implementation",
                "implementation_id": subject,
                "implementation_version": version,
                "implementation_digest": f"build:{subject}:{version}",
            },
            "runner": {"name": "aicp-iut-runner", "version": "1.0", "source_revision": "sha256:runner"},
            "suite": {
                "suite_id": iut_cases["suite_id"],
                "suite_version": iut_cases["suite_version"],
                "suite_digest": "sha256:" + compute_file_digest(iut_cases_path),
            },
            "profile": {"profile_id": "AICP-BASE", "profile_version": "0.1", "profile_digest": digest},
            "input_artifacts": [{"path": vector_ref, "content_digest": "sha256:" + compute_file_digest(ROOT / vector_ref)}],
            "passed": True,
            "degraded": False,
            "skipped_checks": [],
            "compatibility_marks": ["AICP-Profile-BASE-0.1"],
        }

    package = tmp_path / "pairwise"
    reports_dir = package / "reports"
    reports_dir.mkdir(parents=True)
    artifacts = {
        "a.json": report("external-a", "1.0.0"),
        "b.json": report("external-b", "1.9.9"),
        "summary.json": {
            "summary_type": "pairwise_interop",
            "participants": ["external-a", "external-b"],
            "profile_id": "AICP-BASE",
            "profile_version": "0.1",
            "result": "interoperable",
        },
    }
    for name, artifact in artifacts.items():
        (reports_dir / name).write_text(json.dumps(artifact), encoding="utf-8")
    manifest = {
        "implementation_id": "external-a",
        "implementation_version": "1.0.0",
        "peer_implementation_id": "external-b",
        "peer_implementation_version": "2.0.0",
        "profile_refs": [{"profile_id": "AICP-BASE", "profile_version": "0.1"}],
        "report_refs": ["reports/a.json", "reports/b.json", "reports/summary.json"],
        "claim_type": "pairwise_interop",
    }
    errors = _validate_strong_report_evidence(package / "submission.json", manifest)
    assert errors == [
        "PAIRWISE_JOINT_EVIDENCE_REQUIRED: real pairwise_interop publication is disabled until "
        "a dedicated joint-execution format binds one shared run, both named builds, and "
        "artifacts consumed in every required direction"
    ]
