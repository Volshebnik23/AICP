from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUNNER_PATH = ROOT / "conformance/runner/aicp_conformance_runner.py"
PROFILE_RUNNER_PATH = ROOT / "conformance/runner/aicp_profile_runner.py"
V02_RUNNER_PATH = ROOT / "conformance/core_v02_runner/aicp_core_v02_runner.py"
V02_PROFILE_RUNNER_PATH = (
    ROOT / "conformance/core_v02_runner/aicp_core_v02_profile_runner.py"
)
if str(RUNNER_PATH.parent) not in sys.path:
    sys.path.insert(0, str(RUNNER_PATH.parent))
if str(V02_RUNNER_PATH.parent) not in sys.path:
    sys.path.insert(0, str(V02_RUNNER_PATH.parent))


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_suite_degraded_mode_removes_compatibility_marks(monkeypatch) -> None:
    suite_runner = _load_module(RUNNER_PATH, "aicp_conformance_runner_test")
    monkeypatch.setattr(suite_runner, "signature_verifier_available", lambda: False)
    report = suite_runner.run_suite(ROOT / "conformance/core/CT_CORE_0.1.json")
    assert report["passed"] is True
    assert report["degraded"] is True
    assert "CT-SIGNATURE-VERIFY-01" in report.get("skipped_checks", [])
    assert report.get("compatibility_marks") == []


def test_profile_degraded_mode_removes_profile_badges(monkeypatch, tmp_path: Path) -> None:
    profile_runner = _load_module(PROFILE_RUNNER_PATH, "aicp_profile_runner_test")

    profile = {
        "profile_id": "TMP-PROFILE-DEGRADED",
        "profile_version": "0.1.0-dev",
        "required_suites": ["conformance/core/CT_CORE_0.1.json", "conformance/extensions/CN_CAPNEG_0.1.json"],
        "compatibility_mark": "TMP-PROFILE-MARK",
    }
    profile_path = tmp_path / "tmp_profile.json"
    profile_path.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")

    responses = [
        {
            "suite_id": "CT-CORE-0.1",
            "aicp_version": "0.1",
            "passed": True,
            "failures": [],
            "compatibility_marks": [],
            "degraded": True,
            "degraded_reasons": ["signature verification unavailable"],
        },
        {
            "suite_id": "CN-CAPNEG-0.1",
            "aicp_version": "0.1",
            "passed": True,
            "failures": [],
            "compatibility_marks": ["AICP-EXT-CAPNEG-0.1"],
            "degraded": False,
            "degraded_reasons": [],
        },
    ]

    def fake_run_suite(_suite_path: Path):
        return responses.pop(0)

    monkeypatch.setattr(profile_runner, "run_suite", fake_run_suite)
    report = profile_runner.run_profile(profile_path)
    assert report["passed"] is True
    assert report["degraded"] is True
    assert "signature verification unavailable" in report.get("degraded_reasons", [])
    assert report.get("compatibility_marks") == []


def test_profile_infers_aicp_version_from_suite_catalog_when_mock_missing(monkeypatch, tmp_path: Path) -> None:
    profile_runner = _load_module(PROFILE_RUNNER_PATH, "aicp_profile_runner_missing_version_test")

    profile = {
        "profile_id": "TMP-PROFILE-INFER-VERSION",
        "profile_version": "0.1",
        "required_suites": ["conformance/core/CT_CORE_0.1.json"],
        "compatibility_mark": "TMP-PROFILE-MARK",
    }
    profile_path = tmp_path / "tmp_profile_infer.json"
    profile_path.write_text(json.dumps(profile, indent=2) + "\n", encoding="utf-8")

    monkeypatch.setattr(
        profile_runner,
        "run_suite",
        lambda _suite_path: {
            "suite_id": "CT-CORE-0.1",
            "passed": True,
            "failures": [],
            "compatibility_marks": ["AICP-Core-0.1"],
            "degraded": False,
            "degraded_reasons": [],
        },
    )

    report = profile_runner.run_profile(profile_path)
    assert report["aicp_version"] == "0.1"


def test_core_v02_missing_jsonschema_is_passed_degraded_without_mark(
    monkeypatch,
) -> None:
    suite_runner = _load_module(
        V02_RUNNER_PATH, "aicp_core_v02_runner_missing_jsonschema_test"
    )
    monkeypatch.setattr(suite_runner, "Draft202012Validator", None)
    report = suite_runner.run_suite(ROOT / "conformance/core/CT_CORE_0.2.json")
    assert report["passed"] is True
    assert report["degraded"] is True
    assert report["degraded_reasons"] == [
        "jsonschema dependency unavailable; schema checks skipped"
    ]
    assert report["skipped_checks"] == [
        "CT-SCHEMA-JSONL-01",
        "CT-PAYLOAD-SCHEMA-01",
        "CT2-CONTRACT-SCHEMA-01",
    ]
    assert report["compatibility_marks"] == []
    assert suite_runner._status_label(report) == "PASSED (DEGRADED)"


def test_core_v02_missing_ed25519_is_passed_degraded_without_mark(
    monkeypatch,
) -> None:
    suite_runner = _load_module(
        V02_RUNNER_PATH, "aicp_core_v02_runner_missing_ed25519_test"
    )
    monkeypatch.setattr(
        suite_runner, "signature_verifier_available", lambda: False
    )
    report = suite_runner.run_suite(ROOT / "conformance/core/CT_CORE_0.2.json")
    assert report["passed"] is True
    assert report["degraded"] is True
    assert report["degraded_reasons"] == [
        "Core v0.2 Ed25519 signature verification unavailable"
    ]
    assert report["skipped_checks"] == ["CT-SIGNATURE-VERIFY-01"]
    assert report["compatibility_marks"] == []
    assert suite_runner._status_label(report) == "PASSED (DEGRADED)"


def test_base_v02_profile_suppresses_all_marks_for_skipped_child(
    monkeypatch, tmp_path: Path
) -> None:
    profile_runner = _load_module(
        V02_PROFILE_RUNNER_PATH, "aicp_core_v02_profile_skipped_test"
    )
    profile_path = tmp_path / "base-v02-skipped.json"
    profile_path.write_text(
        json.dumps(
            {
                "profile_id": "AICP-BASE@0.2",
                "profile_version": "0.2.0-experimental",
                "aicp_version": "0.2",
                "required_suites": ["conformance/core/CT_CORE_0.2.json"],
                "compatibility_mark": "AICP-Profile-BASE-0.2",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        profile_runner,
        "run_suite",
        lambda _path: {
            "suite_id": "CT-CORE-0.2",
            "passed": True,
            "failures": [],
            "compatibility_marks": ["AICP-Core-0.2"],
            "degraded": False,
            "degraded_reasons": [],
            "skipped_checks": ["CT-SIGNATURE-VERIFY-01"],
        },
    )
    report = profile_runner.run_profile(profile_path)
    assert report["passed"] is True
    assert report["degraded"] is True
    assert report["degraded_reasons"] == []
    assert report["skipped_checks"] == ["CT-SIGNATURE-VERIFY-01"]
    assert report["compatibility_marks"] == []
    assert profile_runner._status_label(report) == "PASSED (DEGRADED)"


def test_base_v02_profile_deduplicates_degraded_reasons_and_suppresses_marks(
    monkeypatch, tmp_path: Path
) -> None:
    profile_runner = _load_module(
        V02_PROFILE_RUNNER_PATH, "aicp_core_v02_profile_degraded_test"
    )
    profile_path = tmp_path / "base-v02-degraded.json"
    profile_path.write_text(
        json.dumps(
            {
                "profile_id": "AICP-BASE@0.2",
                "profile_version": "0.2.0-experimental",
                "aicp_version": "0.2",
                "required_suites": [
                    "conformance/core/CT_CORE_0.2.json",
                    "conformance/core/CT_CORE_0.2.json",
                ],
                "compatibility_mark": "AICP-Profile-BASE-0.2",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        profile_runner,
        "run_suite",
        lambda _path: {
            "suite_id": "CT-CORE-0.2",
            "passed": True,
            "failures": [],
            "compatibility_marks": ["AICP-Core-0.2"],
            "degraded": False,
            "degraded_reasons": ["required verification unavailable"],
            "skipped_checks": [],
        },
    )
    report = profile_runner.run_profile(profile_path)
    assert report["passed"] is True
    assert report["degraded"] is True
    assert report["degraded_reasons"] == [
        "required verification unavailable"
    ]
    assert report["skipped_checks"] == []
    assert report["compatibility_marks"] == []
    assert profile_runner._status_label(report) == "PASSED (DEGRADED)"
