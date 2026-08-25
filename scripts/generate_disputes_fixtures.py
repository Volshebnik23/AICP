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
    rendered = "\n".join(json.dumps(r, separators=(",", ":"), ensure_ascii=False) for r in rows) + "\n"
    if "--check" in sys.argv:
        if not path.is_file() or path.read_text(encoding="utf-8") != rendered:
            raise SystemExit(f"stale generated fixture: {path.relative_to(ROOT)}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8")


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

    ds04 = finalize([
        {"session_id": "sDS4", "message_id": "m1", "timestamp": "2026-01-10T00:00:00Z", "sender": "agent:A", "message_type": "CONTRACT_PROPOSE", "contract_id": "cDS4", "contract_ref": cref, "payload": {"contract": {"contract_id": "cDS4", "goal": "dispute_claim_arbitration", "roles": ["agent", "auditor", "arbiter"]}}},
        {"session_id": "sDS4", "message_id": "m2", "timestamp": "2026-01-10T00:00:02Z", "sender": "agent:B", "message_type": "CONTRACT_ACCEPT", "contract_id": "cDS4", "contract_ref": cref, "payload": {"accepted": True}},
        {"session_id": "sDS4", "message_id": "m3", "timestamp": "2026-01-10T00:00:04Z", "sender": "agent:A", "message_type": "ATTEST_ACTION", "contract_id": "cDS4", "contract_ref": cref, "payload": {"action": "deliver_summary", "result_hash": "sha256:ds04-result"}},
        {"session_id": "sDS4", "message_id": "m4", "timestamp": "2026-01-10T00:00:06Z", "sender": "auditor:Q", "message_type": "CHALLENGE_ASSERTION", "contract_id": "cDS4", "contract_ref": cref, "payload": {"challenge_id": "CH-4", "target_ref": {"message_id": "m3"}, "challenge_type": "RESULT_DISTORTION", "claim": "Required delivery evidence is incomplete", "evidence_refs": ["msgid:m3"]}},
        {"session_id": "sDS4", "message_id": "m5", "timestamp": "2026-01-10T00:00:08Z", "sender": "auditor:Q", "message_type": "CLAIM_BREACH", "contract_id": "cDS4", "contract_ref": cref, "payload": {"claim_id": "CL-4", "delegation_id": "DL-4", "breach_type": "DELEGATION_BREACH", "narrative": "Expected delivery was not observed.", "evidence_refs": ["msgid:m4"]}},
        {"session_id": "sDS4", "message_id": "m6", "timestamp": "2026-01-10T00:00:10Z", "sender": "auditor:Q", "message_type": "ARBITRATION_REQUEST", "contract_id": "cDS4", "contract_ref": cref, "payload": {"arbitration_id": "ARB-4", "related_challenge_id": "CH-4", "arbitrator": "arbiter:R", "note": "Escalating claim for determination.", "evidence_refs": ["msgid:m5"]}},
        {"session_id": "sDS4", "message_id": "m7", "timestamp": "2026-01-10T00:00:12Z", "sender": "arbiter:R", "message_type": "ARBITRATION_RESULT", "contract_id": "cDS4", "contract_ref": cref, "payload": {"arbitration_id": "ARB-4", "outcome": "upheld", "remedy": "retry_with_mediator", "evidence_refs": ["msgid:m6"], "note": "Claim upheld with remediation path."}},
    ])

    out = ROOT / "fixtures/extensions/disputes"
    write(out / "DS-01_challenge_assertion_pass.jsonl", ds01)
    write(out / "DS-02_unknown_challenge_type_expected_fail.jsonl", ds02)
    write(out / "DS-03_evidence_unresolvable_expected_fail.jsonl", ds03)
    write(out / "DS-04_claim_and_arbitration_pass.jsonl", ds04)
    print("Generated disputes fixtures")


if __name__ == "__main__":
    main()
