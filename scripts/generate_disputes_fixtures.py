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
    out: list[dict] = []
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

    ds01 = finalize([
        {"session_id": "sDS1", "message_id": "m1", "timestamp": "2026-01-08T00:00:00Z", "sender": "agent:A", "message_type": "CONTRACT_PROPOSE", "contract_id": "cDS1", "contract_ref": cref, "payload": {"contract": {"contract_id": "cDS1", "goal": "dispute_pass", "roles": ["agent", "auditor"]}}},
        {"session_id": "sDS1", "message_id": "m2", "timestamp": "2026-01-08T00:00:02Z", "sender": "agent:B", "message_type": "CONTRACT_ACCEPT", "contract_id": "cDS1", "contract_ref": cref, "payload": {"accepted": True}},
        {"session_id": "sDS1", "message_id": "m3", "timestamp": "2026-01-08T00:00:04Z", "sender": "agent:A", "message_type": "ATTEST_ACTION", "contract_id": "cDS1", "contract_ref": cref, "payload": {"action": "deliver_summary", "result_hash": "sha256:ds01-result"}},
        {"session_id": "sDS1", "message_id": "m4", "timestamp": "2026-01-08T00:00:06Z", "sender": "auditor:Q", "message_type": "CHALLENGE_ASSERTION", "contract_id": "cDS1", "contract_ref": cref, "payload": {"challenge_id": "CH-1", "target_ref": {"message_id": "m3"}, "challenge_type": "RESULT_DISTORTION", "claim": "Output diverges from expected evidence", "evidence_refs": ["msgid:m3", "urn:evidence:ds01:1"]}},
    ])

    ds02 = finalize([
        {"session_id": "sDS2", "message_id": "m1", "timestamp": "2026-01-08T00:10:00Z", "sender": "agent:A", "message_type": "CONTRACT_PROPOSE", "contract_id": "cDS2", "contract_ref": cref, "payload": {"contract": {"contract_id": "cDS2", "goal": "dispute_fail_claim_type", "roles": ["agent", "auditor"]}}},
        {"session_id": "sDS2", "message_id": "m2", "timestamp": "2026-01-08T00:10:02Z", "sender": "agent:B", "message_type": "CONTRACT_ACCEPT", "contract_id": "cDS2", "contract_ref": cref, "payload": {"accepted": True}},
        {"session_id": "sDS2", "message_id": "m3", "timestamp": "2026-01-08T00:10:04Z", "sender": "agent:A", "message_type": "ATTEST_ACTION", "contract_id": "cDS2", "contract_ref": cref, "payload": {"action": "deliver_summary", "result_hash": "sha256:ds02-result"}},
        {"session_id": "sDS2", "message_id": "m4", "timestamp": "2026-01-08T00:10:06Z", "sender": "auditor:Q", "message_type": "CHALLENGE_ASSERTION", "contract_id": "cDS2", "contract_ref": cref, "payload": {"challenge_id": "CH-2", "target_ref": {"message_id": "m3"}, "challenge_type": "UNKNOWN_TYPE", "claim": "Output diverges from expected evidence", "evidence_refs": ["msgid:m3", "urn:evidence:ds02:1"]}},
    ])

    ds03 = finalize([
        {"session_id": "sDS3", "message_id": "m1", "timestamp": "2026-01-08T00:20:00Z", "sender": "agent:A", "message_type": "CONTRACT_PROPOSE", "contract_id": "cDS3", "contract_ref": cref, "payload": {"contract": {"contract_id": "cDS3", "goal": "dispute_unresolvable_evidence", "roles": ["agent", "auditor"]}}},
        {"session_id": "sDS3", "message_id": "m2", "timestamp": "2026-01-08T00:20:02Z", "sender": "agent:B", "message_type": "CONTRACT_ACCEPT", "contract_id": "cDS3", "contract_ref": cref, "payload": {"accepted": True}},
        {"session_id": "sDS3", "message_id": "m3", "timestamp": "2026-01-08T00:20:04Z", "sender": "agent:A", "message_type": "ATTEST_ACTION", "contract_id": "cDS3", "contract_ref": cref, "payload": {"action": "deliver_summary", "result_hash": "sha256:ds03-result"}},
        {"session_id": "sDS3", "message_id": "m4", "timestamp": "2026-01-08T00:20:06Z", "sender": "auditor:Q", "message_type": "CHALLENGE_ASSERTION", "contract_id": "cDS3", "contract_ref": cref, "payload": {"challenge_id": "CH-3", "target_ref": {"message_id": "m3"}, "challenge_type": "RESULT_DISTORTION", "claim": "Evidence reference is not transcript-resolvable", "evidence_refs": ["urn:evidence:ds03:1"]}},
    ])

    out = ROOT / "fixtures/extensions/disputes"
    write(out / "DS-01_challenge_assertion_pass.jsonl", ds01)
    write(out / "DS-02_unknown_challenge_type_expected_fail.jsonl", ds02)
    write(out / "DS-03_evidence_unresolvable_expected_fail.jsonl", ds03)
    print("Generated disputes fixtures")


if __name__ == "__main__":
    main()
