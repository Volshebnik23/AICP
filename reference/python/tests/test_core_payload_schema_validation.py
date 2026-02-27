from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "conformance/runner/aicp_conformance_runner.py"


def test_core_suite_conformance_passes_with_payload_schema() -> None:
    report = "conformance/report_core_payload_test.json"
    cmd = [
        sys.executable,
        str(RUNNER),
        "--suite",
        "conformance/core/CT_CORE_0.1.json",
        "--out",
        report,
    ]
    result = subprocess.run(cmd, cwd=ROOT, check=False)
    try:
        assert result.returncode == 0
    finally:
        (ROOT / report).unlink(missing_ok=True)


def test_core_payload_negative_missing_required_field() -> None:
    jsonschema = pytest.importorskip("jsonschema")
    Draft202012Validator = jsonschema.Draft202012Validator

    suite = json.loads((ROOT / "conformance/core/CT_CORE_0.1.json").read_text(encoding="utf-8"))
    payload_schema = json.loads((ROOT / suite["payload_schema_ref"]).read_text(encoding="utf-8"))
    ptr = suite["payload_schema_map"]["ATTEST_ACTION"]

    transcript = (ROOT / "fixtures/golden_transcripts/GT-01_happy_path_signed.jsonl").read_text(encoding="utf-8").splitlines()
    attest_msg = json.loads(transcript[2])
    bad_payload = dict(attest_msg["payload"])
    bad_payload.pop("action_id", None)

    pointer = ptr[1:] if ptr.startswith("#") else ptr
    wrapper = {
        "$schema": payload_schema.get("$schema"),
        "$id": payload_schema.get("$id"),
        "$ref": f"#{pointer}" if pointer else "#",
        "$defs": payload_schema.get("$defs", {}),
    }
    errs = list(Draft202012Validator(wrapper).iter_errors(bad_payload))
    assert errs, "Expected payload schema validation error when required field is missing"
