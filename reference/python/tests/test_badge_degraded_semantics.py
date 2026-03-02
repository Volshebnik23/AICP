from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUNNER_PATH = ROOT / "conformance/runner/aicp_conformance_runner.py"
PROFILE_RUNNER_PATH = ROOT / "conformance/runner/aicp_profile_runner.py"
if str(RUNNER_PATH.parent) not in sys.path:
    sys.path.insert(0, str(RUNNER_PATH.parent))


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
