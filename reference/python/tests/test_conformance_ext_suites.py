from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "conformance/runner/aicp_conformance_runner.py"


def _run_suite(suite: str, report: str) -> int:
    cmd = [
        sys.executable,
        str(RUNNER),
        "--suite",
        suite,
        "--out",
        report,
    ]
    result = subprocess.run(cmd, cwd=ROOT, check=False)
    return result.returncode


def test_extension_conformance_suites_pass() -> None:
    suites = [
        ("conformance/extensions/CN_CAPNEG_0.1.json", "conformance/report_ext_capneg_test.json"),
        ("conformance/extensions/OR_OBJECT_RESYNC_0.1.json", "conformance/report_ext_or_test.json"),
        ("conformance/extensions/PE_POLICY_EVAL_0.1.json", "conformance/report_ext_pe_test.json"),
        ("conformance/extensions/ENF_ENFORCEMENT_0.1.json", "conformance/report_ext_enf_test.json"),
        ("conformance/extensions/AL_ALERTS_0.1.json", "conformance/report_ext_alerts_test.json"),
        ("conformance/extensions/RS_RESUME_0.1.json", "conformance/report_ext_resume_test.json"),
        ("conformance/extensions/TA_TRUST_ATTESTATIONS_0.1.json", "conformance/report_ext_trust_attestations_test.json"),
    ]
    for suite, report in suites:
        assert _run_suite(suite, report) == 0, f"suite failed: {suite}"
        (ROOT / report).unlink(missing_ok=True)
