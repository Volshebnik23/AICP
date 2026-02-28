from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SANDBOX = ROOT / "sandbox/run.py"
RUNNER = ROOT / "conformance/runner/aicp_conformance_runner.py"


def test_python_dropin_generator_and_sandbox_validation(tmp_path: Path) -> None:
    out = tmp_path / "py_minimal_core.jsonl"
    cmd = [
        sys.executable,
        str(ROOT / "dropins/aicp-core/python/generate_minimal_core_transcript.py"),
        "--out",
        str(out),
    ]
    gen = subprocess.run(cmd, cwd=ROOT, check=False, capture_output=True, text=True)
    assert gen.returncode == 0, gen.stdout + gen.stderr
    assert out.exists() and out.read_text(encoding="utf-8").strip()

    verify = subprocess.run(
        [sys.executable, str(SANDBOX), str(out), "--no-signature-verify"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert verify.returncode == 0, verify.stdout + verify.stderr


def test_typescript_dropin_generator_and_conformance_runner(tmp_path: Path) -> None:
    out_rel = Path("out/test_quickstart_ts/minimal_core.jsonl")
    out = ROOT / out_rel
    out.parent.mkdir(parents=True, exist_ok=True)

    gen = subprocess.run(
        [
            "node",
            str(ROOT / "dropins/aicp-core/typescript/scripts/generate_minimal_core_transcript.mjs"),
            "--out",
            str(out),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert gen.returncode == 0, gen.stdout + gen.stderr
    assert out.exists() and out.read_text(encoding="utf-8").strip()

    suite = {
        "suite_id": "TMP-QUICKSTART-TS",
        "suite_version": "0.1.0-dev",
        "aicp_version": "0.1",
        "description": "Temporary quickstart suite",
        "schema_ref": "schemas/core/aicp-core-message.schema.json",
        "transcripts": [
            {
                "id": "TMP-TS",
                "path": str(out_rel),
                "expected_message_types": ["CONTRACT_PROPOSE", "CONTRACT_ACCEPT", "CONTEXT_AMEND"],
            }
        ],
        "checks": [
            {"test_id": "CT-SCHEMA-JSONL-01"},
            {"test_id": "CT-MESSAGE-TYPE-REGISTRY-01"},
            {"test_id": "CT-HASH-CHAIN-01"},
            {"test_id": "CT-INVARIANTS-01"},
            {"test_id": "CT-SEQUENCE-01"},
            {"test_id": "CT-MESSAGE-HASH-01"},
        ],
    }

    suite_path = tmp_path / "tmp_quickstart_suite.json"
    suite_path.write_text(json.dumps(suite, indent=2) + "\n", encoding="utf-8")
    report_path = ROOT / "out/test_quickstart_ts/tmp_quickstart_report.json"

    run = subprocess.run(
        [sys.executable, str(RUNNER), "--suite", str(suite_path), "--out", str(report_path)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert run.returncode == 0, run.stdout + run.stderr
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["passed"] is True
    report_path.unlink(missing_ok=True)


def test_sandbox_accepts_external_path_without_relative_to_crash(tmp_path: Path) -> None:
    out = tmp_path / "external_minimal_core.jsonl"
    subprocess.run(
        [
            sys.executable,
            str(ROOT / "dropins/aicp-core/python/generate_minimal_core_transcript.py"),
            "--out",
            str(out),
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )

    result = subprocess.run(
        [sys.executable, str(SANDBOX), str(out), "--no-signature-verify"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASSED" in result.stdout
