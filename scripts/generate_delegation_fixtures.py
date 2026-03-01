#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference/python"))
from aicp_ref.hashing import message_hash_from_body  # noqa: E402


def finalize(rows: list[dict]) -> list[dict]:
    prev = None
    out = []
    for row in rows:
        msg = dict(row)
        msg.pop("message_hash", None)
        if prev is not None:
            msg["prev_msg_hash"] = prev
        msg["message_hash"] = message_hash_from_body(msg)
        prev = msg["message_hash"]
        out.append(msg)
    return out


def write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, separators=(",", ":"), ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def main() -> None:
    cref = {"branch_id": "main", "base_version": "v1", "head_version": "v1"}

    dl01 = finalize([
        {"session_id": "sDL1", "message_id": "m1", "timestamp": "2026-01-06T00:00:00Z", "sender": "agent:A", "message_type": "CONTRACT_PROPOSE", "contract_id": "cDL1", "contract_ref": cref, "payload": {"contract": {"contract_id": "cDL1", "goal": "delegation_happy", "roles": ["manager", "agent"]}}},
        {"session_id": "sDL1", "message_id": "m2", "timestamp": "2026-01-06T00:00:02Z", "sender": "agent:B", "message_type": "CONTRACT_ACCEPT", "contract_id": "cDL1", "contract_ref": cref, "payload": {"accepted": True}},
        {"session_id": "sDL1", "message_id": "m3", "timestamp": "2026-01-06T00:00:04Z", "sender": "manager:M", "message_type": "DELEGATION_GRANT", "contract_id": "cDL1", "contract_ref": cref, "payload": {"delegation_id": "D0", "delegator": "manager:M", "delegatee": "agent:A", "authority_subset": {"tools": ["summarize"]}, "scope": ["task:summary"], "purpose": "generate summary", "expiry": "2027-01-06T00:00:00Z", "max_depth": 1}},
        {"session_id": "sDL1", "message_id": "m4", "timestamp": "2026-01-06T00:00:06Z", "sender": "agent:A", "message_type": "DELEGATION_ACCEPT", "contract_id": "cDL1", "contract_ref": cref, "payload": {"delegation_id": "D0", "accepted_at": "2026-01-06T00:00:06Z"}},
        {"session_id": "sDL1", "message_id": "m5", "timestamp": "2026-01-06T00:00:08Z", "sender": "agent:A", "message_type": "DELEGATION_RESULT_ATTEST", "contract_id": "cDL1", "contract_ref": cref, "payload": {"delegation_id": "D0", "result_hash": "sha256:dl01result", "contract_head_version": "v1"}},
    ])

    dl02 = finalize([
        {"session_id": "sDL2", "message_id": "m1", "timestamp": "2026-01-06T00:10:00Z", "sender": "agent:A", "message_type": "CONTRACT_PROPOSE", "contract_id": "cDL2", "contract_ref": cref, "payload": {"contract": {"contract_id": "cDL2", "goal": "delegation_expiry_negative", "roles": ["manager", "agent"]}}},
        {"session_id": "sDL2", "message_id": "m2", "timestamp": "2026-01-06T00:10:02Z", "sender": "agent:B", "message_type": "CONTRACT_ACCEPT", "contract_id": "cDL2", "contract_ref": cref, "payload": {"accepted": True}},
        {"session_id": "sDL2", "message_id": "m3", "timestamp": "2026-01-06T00:10:04Z", "sender": "manager:M", "message_type": "DELEGATION_GRANT", "contract_id": "cDL2", "contract_ref": cref, "payload": {"delegation_id": "D0", "delegator": "manager:M", "delegatee": "agent:A", "authority_subset": {"tools": ["summarize"]}, "scope": ["task:summary"], "purpose": "generate summary", "expiry": "2026-01-06T00:10:05Z", "max_depth": 1}},
        {"session_id": "sDL2", "message_id": "m4", "timestamp": "2026-01-06T00:10:06Z", "sender": "agent:A", "message_type": "DELEGATION_RESULT_ATTEST", "contract_id": "cDL2", "contract_ref": cref, "payload": {"delegation_id": "D0", "result_hash": "sha256:dl02result", "contract_head_version": "v1"}},
    ])

    dl03 = finalize([
        {"session_id": "sDL3", "message_id": "m1", "timestamp": "2026-01-06T00:20:00Z", "sender": "agent:A", "message_type": "CONTRACT_PROPOSE", "contract_id": "cDL3", "contract_ref": cref, "payload": {"contract": {"contract_id": "cDL3", "goal": "delegation_depth_negative", "roles": ["manager", "agent"]}}},
        {"session_id": "sDL3", "message_id": "m2", "timestamp": "2026-01-06T00:20:02Z", "sender": "agent:B", "message_type": "CONTRACT_ACCEPT", "contract_id": "cDL3", "contract_ref": cref, "payload": {"accepted": True}},
        {"session_id": "sDL3", "message_id": "m3", "timestamp": "2026-01-06T00:20:04Z", "sender": "manager:M", "message_type": "DELEGATION_GRANT", "contract_id": "cDL3", "contract_ref": cref, "payload": {"delegation_id": "D0", "delegator": "manager:M", "delegatee": "agent:A", "authority_subset": {"tools": ["approve"]}, "scope": ["task:approve"], "purpose": "approve request", "expiry": "2027-01-06T00:00:00Z", "max_depth": 0}},
        {"session_id": "sDL3", "message_id": "m4", "timestamp": "2026-01-06T00:20:06Z", "sender": "agent:A", "message_type": "DELEGATION_GRANT", "contract_id": "cDL3", "contract_ref": cref, "payload": {"delegation_id": "D1", "delegator": "agent:A", "delegatee": "agent:B", "parent_delegation_id": "D0", "authority_subset": {"tools": ["approve"]}, "scope": ["task:approve"], "purpose": "subdelegated approval", "expiry": "2027-01-06T00:00:00Z", "max_depth": 0}},
    ])

    out = ROOT / "fixtures/extensions/delegation"
    write(out / "DL-01_grant_accept_result_happy.jsonl", dl01)
    write(out / "DL-02_expired_grant_expected_fail.jsonl", dl02)
    write(out / "DL-03_depth_exceeded_expected_fail.jsonl", dl03)
    print("Generated delegation fixtures")


if __name__ == "__main__":
    main()
