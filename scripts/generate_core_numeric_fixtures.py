#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference/python"))
from aicp_ref.hashing import message_hash_from_body  # noqa: E402


def _finalize(rows: list[dict]) -> list[dict]:
    out: list[dict] = []
    prev: str | None = None
    for row in rows:
        msg = dict(row)
        msg.pop("message_hash", None)
        if prev is None:
            msg.pop("prev_msg_hash", None)
        else:
            msg["prev_msg_hash"] = prev
        msg["message_hash"] = message_hash_from_body(msg)
        prev = msg["message_hash"]
        out.append(msg)
    return out


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, separators=(",", ":"), ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def main() -> None:
    rows = [
        {
            "session_id": "sNUM1",
            "message_id": "m1",
            "timestamp": "2026-03-03T00:00:00Z",
            "sender": "agent:A",
            "message_type": "CONTRACT_PROPOSE",
            "contract_id": "cNUM1",
            "contract_ref": {"branch_id": "main", "base_version": "v1", "head_version": "v1"},
            "payload": {"contract": {"contract_id": "cNUM1", "goal": "numeric_guardrail", "roles": ["agent"]}},
        },
        {
            "session_id": "sNUM1",
            "message_id": "m2",
            "timestamp": "2026-03-03T00:00:01Z",
            "sender": "agent:B",
            "message_type": "CONTRACT_ACCEPT",
            "contract_id": "cNUM1",
            "contract_ref": {"branch_id": "main", "base_version": "v1", "head_version": "v1"},
            "payload": {"accepted": True},
        },
        {
            "session_id": "sNUM1",
            "message_id": "m3",
            "timestamp": "2026-03-03T00:00:02Z",
            "sender": "agent:A",
            "message_type": "ATTEST_ACTION",
            "contract_id": "cNUM1",
            "contract_ref": {"branch_id": "main", "base_version": "v1", "head_version": "v1"},
            "payload": {"action": "numeric_test", "score": 0.5},
        },
    ]

    out = _finalize(rows)
    _write_jsonl(ROOT / "fixtures/core/numeric/NUM-01_float_in_payload.jsonl", out)
    print("Generated fixtures/core/numeric/NUM-01_float_in_payload.jsonl")


if __name__ == "__main__":
    main()
