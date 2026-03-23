from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "conformance/runner/aicp_conformance_runner.py"
CORE_SUITE = ROOT / "conformance/core/CT_CORE_0.1.json"


def _message(*, message_id: str, prev_msg_hash: str | None = None) -> dict[str, object]:
    body: dict[str, object] = {
        "session_id": "s-neg-core",
        "message_id": message_id,
        "timestamp": "2026-03-01T00:00:00Z",
        "sender": "agent:A",
        "message_type": "CONTRACT_ACCEPT",
        "contract_id": "c-neg-core",
        "payload": {"accepted": True},
    }
    if prev_msg_hash is not None:
        body["prev_msg_hash"] = prev_msg_hash
    return body


def _with_hashes(messages: list[dict[str, object]]) -> list[dict[str, object]]:
    sys.path.insert(0, str((ROOT / "reference/python").resolve()))
    from aicp_ref.hashing import message_hash_from_body

    out: list[dict[str, object]] = []
    for message in messages:
        msg = dict(message)
        msg["message_hash"] = message_hash_from_body(msg)
        out.append(msg)
    return out


def test_core_suite_declares_empty_contract_id_expected_fail_fixture() -> None:
    suite = json.loads(CORE_SUITE.read_text(encoding="utf-8"))
    check_ids = {c["test_id"] for c in suite.get("checks", [])}
    assert "CT-CONTRACT-ID-01" in check_ids

    gt11 = next((tr for tr in suite.get("transcripts", []) if tr.get("id") == "GT-11"), None)
    assert gt11 is not None
    assert gt11.get("expect_pass") is False
    expected = {e.get("test_id"): e.get("min_count") for e in gt11.get("expected_failures", [])}
    assert expected.get("CT-CONTRACT-ID-01") == 1


def test_core_suite_negative_empty_contract_id_reports_contract_id_check(tmp_path: Path) -> None:
    suite = {
        "suite_id": "CT-CORE-CONTRACT-ID-NEG",
        "suite_version": "0.1.0-dev",
        "aicp_version": "0.1",
        "description": "negative empty contract_id envelope check",
        "schema_ref": str((ROOT / "schemas/core/aicp-core-message.schema.json").resolve()),
        "transcripts": [
            {
                "id": "NEG-EMPTY-CONTRACT-ID",
                "path": str((ROOT / "fixtures/golden_transcripts/GT-11_empty_contract_id_expected_fail.jsonl").resolve()),
                "expected_message_types": ["CONTRACT_ACCEPT"],
            }
        ],
        "checks": [
            {"test_id": "CT-SCHEMA-JSONL-01", "description": "core schema"},
            {"test_id": "CT-CONTRACT-ID-01", "description": "contract id"},
            {"test_id": "CT-INVARIANTS-01", "description": "invariants"},
            {"test_id": "CT-SEQUENCE-01", "description": "sequence"},
            {"test_id": "CT-MESSAGE-HASH-01", "description": "message hash"},
        ],
    }
    suite_path = tmp_path / "contract_id_negative_suite.json"
    suite_path.write_text(json.dumps(suite), encoding="utf-8")
    report = tmp_path / "core-report.json"
    result = subprocess.run(
        [sys.executable, str(RUNNER), "--suite", str(suite_path), "--out", str(report)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    data = json.loads(report.read_text(encoding="utf-8"))
    failures = [failure for failure in data.get("failures", []) if failure.get("test_id") == "CT-CONTRACT-ID-01"]
    assert len(failures) == 1
    assert failures[0]["file"].endswith("GT-11_empty_contract_id_expected_fail.jsonl")


def test_runner_reports_multi_step_hash_chain_corruption(tmp_path: Path) -> None:
    messages = _with_hashes(
        [
            _message(message_id="m1"),
            _message(message_id="m2", prev_msg_hash="__TO_FILL__"),
            _message(message_id="m3", prev_msg_hash="__TO_FILL__"),
            _message(message_id="m4", prev_msg_hash="__TO_FILL__"),
        ]
    )
    messages[1]["prev_msg_hash"] = messages[0]["message_hash"]
    messages[2]["prev_msg_hash"] = "sha256:not-the-second-hash"
    messages[3]["prev_msg_hash"] = "sha256:not-the-third-hash"

    transcript_path = tmp_path / "multi_step_chain_negative.jsonl"
    transcript_path.write_text(
        "".join(json.dumps(message, separators=(",", ":")) + "\n" for message in messages),
        encoding="utf-8",
    )

    suite = {
        "suite_id": "CT-CORE-MULTI-STEP-HASH-NEG",
        "suite_version": "0.1.0-dev",
        "aicp_version": "0.1",
        "description": "negative multi-step hash-chain corruption",
        "schema_ref": str((ROOT / "schemas/core/aicp-core-message.schema.json").resolve()),
        "transcripts": [
            {
                "id": "NEG-MULTI-STEP-HASH",
                "path": str(transcript_path.resolve()),
                "expected_message_types": ["CONTRACT_ACCEPT"] * 4,
            }
        ],
        "checks": [
            {"test_id": "CT-SCHEMA-JSONL-01", "description": "core schema"},
            {"test_id": "CT-PREV-MSG-REQUIRED-01", "description": "prev msg required"},
            {"test_id": "CT-HASH-CHAIN-01", "description": "hash chain"},
            {"test_id": "CT-MESSAGE-HASH-01", "description": "message hash"},
            {"test_id": "CT-INVARIANTS-01", "description": "invariants"},
            {"test_id": "CT-SEQUENCE-01", "description": "sequence"},
            {"test_id": "CT-CONTRACT-ID-01", "description": "contract id"},
        ],
    }
    suite_path = tmp_path / "multi_step_chain_negative_suite.json"
    suite_path.write_text(json.dumps(suite), encoding="utf-8")
    report_path = tmp_path / "multi_step_chain_negative_report.json"

    result = subprocess.run(
        [
            sys.executable,
            str(RUNNER),
            "--suite",
            str(suite_path),
            "--out",
            str(report_path),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    report = json.loads(report_path.read_text(encoding="utf-8"))
    failures = [failure for failure in report.get("failures", []) if failure.get("test_id") == "CT-HASH-CHAIN-01"]
    assert len(failures) == 2
    assert {failure.get("line") for failure in failures} == {3, 4}
