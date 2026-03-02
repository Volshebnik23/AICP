#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference/python"))

from aicp_ref.hashing import message_hash_from_body

OUT_DIR = ROOT / "fixtures/core/numeric"


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")


def _build_pass_rows() -> list[dict[str, Any]]:
    session_id = "sNUM1"
    contract_id = "cNUM1"
    contract_ref = {"branch_id": "main", "base_version": "v1", "head_version": "v1"}

    rows: list[dict[str, Any]] = []
    bodies = [
        {
            "session_id": session_id,
            "message_id": "m1",
            "timestamp": "2026-03-03T00:00:00Z",
            "sender": "agent:A",
            "message_type": "CONTRACT_PROPOSE",
            "contract_id": contract_id,
            "contract_ref": contract_ref,
            "payload": {"contract": {"contract_id": contract_id, "goal": "numeric_guardrail", "roles": ["agent"]}},
        },
        {
            "session_id": session_id,
            "message_id": "m2",
            "timestamp": "2026-03-03T00:00:01Z",
            "sender": "agent:B",
            "message_type": "CONTRACT_ACCEPT",
            "contract_id": contract_id,
            "contract_ref": contract_ref,
            "payload": {"accepted": True},
        },
        {
            "session_id": session_id,
            "message_id": "m3",
            "timestamp": "2026-03-03T00:00:02Z",
            "sender": "agent:A",
            "message_type": "ATTEST_ACTION",
            "contract_id": contract_id,
            "contract_ref": contract_ref,
            "payload": {
                "action": "numeric_test",
                "score": 0.5,
                "prob": 0.1,
                "integral_float": 1.0,
                "neg_zero": -0.0,
            },
        },
    ]

    prev_hash: str | None = None
    for body in bodies:
        if prev_hash:
            body["prev_msg_hash"] = prev_hash
        msg_hash = message_hash_from_body(body)
        rows.append({**body, "message_hash": msg_hash})
        prev_hash = msg_hash
    return rows


def _build_unsafe_rows() -> list[dict[str, Any]]:
    return [
        {
            "session_id": "sNUM2",
            "message_id": "m1",
            "timestamp": "2026-03-03T00:10:00Z",
            "sender": "agent:A",
            "message_type": "CONTRACT_PROPOSE",
            "contract_id": "cNUM2",
            "contract_ref": {"branch_id": "main", "base_version": "v1", "head_version": "v1"},
            "payload": {"contract": {"contract_id": "cNUM2", "goal": "numeric_guardrail", "roles": ["agent"]}},
            "message_hash": "sha256:NUM2_M1_PLACEHOLDER",
        },
        {
            "session_id": "sNUM2",
            "message_id": "m2",
            "timestamp": "2026-03-03T00:10:01Z",
            "sender": "agent:B",
            "message_type": "CONTRACT_ACCEPT",
            "contract_id": "cNUM2",
            "contract_ref": {"branch_id": "main", "base_version": "v1", "head_version": "v1"},
            "payload": {"accepted": True},
            "prev_msg_hash": "sha256:NUM2_M1_PLACEHOLDER",
            "message_hash": "sha256:NUM2_M2_PLACEHOLDER",
        },
        {
            "session_id": "sNUM2",
            "message_id": "m3",
            "timestamp": "2026-03-03T00:10:02Z",
            "sender": "agent:A",
            "message_type": "ATTEST_ACTION",
            "contract_id": "cNUM2",
            "contract_ref": {"branch_id": "main", "base_version": "v1", "head_version": "v1"},
            "payload": {"action": "numeric_test", "big": 9007199254740992},
            "prev_msg_hash": "sha256:NUM2_M2_PLACEHOLDER",
            "message_hash": "sha256:NUM2_M3_PLACEHOLDER",
        },
    ]


def main() -> int:
    _write_jsonl(OUT_DIR / "NUM-01_float_payload_pass.jsonl", _build_pass_rows())
    _write_jsonl(OUT_DIR / "NUM-02_unsafe_integer_expected_fail.jsonl", _build_unsafe_rows())
    print("Generated numeric fixtures:")
    print("- fixtures/core/numeric/NUM-01_float_payload_pass.jsonl")
    print("- fixtures/core/numeric/NUM-02_unsafe_integer_expected_fail.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
