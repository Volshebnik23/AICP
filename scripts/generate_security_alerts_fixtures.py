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

    sa01 = finalize([
        {"session_id": "sSA1", "message_id": "m1", "timestamp": "2026-01-08T01:00:00Z", "sender": "agent:A", "message_type": "CONTRACT_PROPOSE", "contract_id": "cSA1", "contract_ref": cref, "payload": {"contract": {"contract_id": "cSA1", "goal": "security_alert_pass", "roles": ["mediator", "agent"]}}},
        {"session_id": "sSA1", "message_id": "m2", "timestamp": "2026-01-08T01:00:02Z", "sender": "agent:B", "message_type": "CONTRACT_ACCEPT", "contract_id": "cSA1", "contract_ref": cref, "payload": {"accepted": True}},
        {"session_id": "sSA1", "message_id": "m3", "timestamp": "2026-01-08T01:00:04Z", "sender": "mediator:M", "message_type": "SECURITY_ALERT", "contract_id": "cSA1", "contract_ref": cref, "payload": {"alert_id": "AL-1", "category": "REPLAY_OR_FORGERY", "severity": "high", "evidence_refs": ["msgid:m2", "urn:evidence:sa01:1"], "recommended_action": "disconnect"}},
    ])

    sa02 = finalize([
        {"session_id": "sSA2", "message_id": "m1", "timestamp": "2026-01-08T01:10:00Z", "sender": "agent:A", "message_type": "CONTRACT_PROPOSE", "contract_id": "cSA2", "contract_ref": cref, "payload": {"contract": {"contract_id": "cSA2", "goal": "security_alert_fail_category", "roles": ["mediator", "agent"]}}},
        {"session_id": "sSA2", "message_id": "m2", "timestamp": "2026-01-08T01:10:02Z", "sender": "agent:B", "message_type": "CONTRACT_ACCEPT", "contract_id": "cSA2", "contract_ref": cref, "payload": {"accepted": True}},
        {"session_id": "sSA2", "message_id": "m3", "timestamp": "2026-01-08T01:10:04Z", "sender": "mediator:M", "message_type": "SECURITY_ALERT", "contract_id": "cSA2", "contract_ref": cref, "payload": {"alert_id": "AL-2", "category": "UNKNOWN_CAT", "severity": "high", "evidence_refs": ["msgid:m2", "urn:evidence:sa02:1"], "recommended_action": "disconnect"}},
    ])

    sa03 = finalize([
        {"session_id": "sSA3", "message_id": "m1", "timestamp": "2026-01-08T01:20:00Z", "sender": "agent:A", "message_type": "CONTRACT_PROPOSE", "contract_id": "cSA3", "contract_ref": cref, "payload": {"contract": {"contract_id": "cSA3", "goal": "security_alert_unresolvable_evidence", "roles": ["mediator", "agent"]}}},
        {"session_id": "sSA3", "message_id": "m2", "timestamp": "2026-01-08T01:20:02Z", "sender": "agent:B", "message_type": "CONTRACT_ACCEPT", "contract_id": "cSA3", "contract_ref": cref, "payload": {"accepted": True}},
        {"session_id": "sSA3", "message_id": "m3", "timestamp": "2026-01-08T01:20:04Z", "sender": "mediator:M", "message_type": "SECURITY_ALERT", "contract_id": "cSA3", "contract_ref": cref, "payload": {"alert_id": "AL-3", "category": "REPLAY_OR_FORGERY", "severity": "high", "evidence_refs": ["urn:evidence:sa03:1"], "recommended_action": "disconnect"}},
    ])

    out = ROOT / "fixtures/extensions/security_alerts"
    write(out / "SA-01_security_alert_pass.jsonl", sa01)
    write(out / "SA-02_unknown_category_expected_fail.jsonl", sa02)
    write(out / "SA-03_evidence_unresolvable_expected_fail.jsonl", sa03)
    print("Generated security alerts fixtures")


if __name__ == "__main__":
    main()
