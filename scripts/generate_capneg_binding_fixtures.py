#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference/python"))
from aicp_ref.hashing import message_hash_from_body, object_hash  # noqa: E402


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

    negotiation_result = {
        "negotiation_id": "NEG-CN7",
        "session_id": "sCN7",
        "contract_id": "cCN7",
        "participants": ["agent:A", "agent:B"],
        "selected": {
            "crypto_profile": ["AICP-JCS-1", "AICP-HASH-SHA256-1", "AICP-SIG-ED25519-1"],
            "privacy_mode": "standard",
            "required_extensions": ["EXT-CAPNEG", "EXT-POLICY-EVAL"],
            "aicp_profile": {"profile_id": "AICP-MEDIATED-BLOCKING", "profile_version": "0.1"},
        },
        "transcript_binding": "msgid:cn7-m3",
    }
    negotiation_result_hash = object_hash("capneg.negotiation_result", negotiation_result)

    cn07 = finalize([
        {"session_id": "sCN7", "message_id": "m1", "timestamp": "2026-01-10T00:00:00Z", "sender": "agent:A", "message_type": "CAPABILITIES_DECLARE", "contract_id": "cCN7", "payload": {"capabilities_id": "cap-A-7", "party_id": "agent:A", "supported_profiles": ["AICP-JCS-1", "AICP-HASH-SHA256-1", "AICP-SIG-ED25519-1"], "supported_privacy_modes": ["standard", "strict"], "supported_extensions": ["EXT-CAPNEG", "EXT-POLICY-EVAL"], "supported_aicp_profiles": [{"profile_id": "AICP-MEDIATED-BLOCKING", "profile_version": "0.1"}] }},
        {"session_id": "sCN7", "message_id": "m2", "timestamp": "2026-01-10T00:00:02Z", "sender": "agent:B", "message_type": "CAPABILITIES_DECLARE", "contract_id": "cCN7", "payload": {"capabilities_id": "cap-B-7", "party_id": "agent:B", "supported_profiles": ["AICP-JCS-1", "AICP-HASH-SHA256-1", "AICP-SIG-ED25519-1"], "supported_privacy_modes": ["standard"], "supported_extensions": ["EXT-CAPNEG", "EXT-POLICY-EVAL"], "supported_aicp_profiles": [{"profile_id": "AICP-MEDIATED-BLOCKING", "profile_version": "0.1"}] }},
        {"session_id": "sCN7", "message_id": "m3", "timestamp": "2026-01-10T00:00:04Z", "sender": "agent:A", "message_type": "CAPABILITIES_PROPOSE", "contract_id": "cCN7", "payload": {"negotiation_result": negotiation_result}},
        {"session_id": "sCN7", "message_id": "m4", "timestamp": "2026-01-10T00:00:06Z", "sender": "agent:B", "message_type": "CAPABILITIES_ACCEPT", "contract_id": "cCN7", "payload": {"negotiation_id": "NEG-CN7", "accepted": True, "negotiation_result_hash": negotiation_result_hash}},
        {"session_id": "sCN7", "message_id": "m5", "timestamp": "2026-01-10T00:00:08Z", "sender": "agent:A", "message_type": "CONTRACT_PROPOSE", "contract_id": "cCN7", "contract_ref": cref, "payload": {"contract": {"contract_id": "cCN7", "goal": "capneg_bound_contract", "roles": ["initiator", "responder"], "ext": {"capneg": {"negotiation_result_hash": negotiation_result_hash, "selected": negotiation_result["selected"], "negotiation_id": "NEG-CN7", "transcript_binding": "msgid:m4"}}}}},
        {"session_id": "sCN7", "message_id": "m6", "timestamp": "2026-01-10T00:00:10Z", "sender": "agent:B", "message_type": "CONTRACT_ACCEPT", "contract_id": "cCN7", "contract_ref": cref, "payload": {"accepted": True}},
    ])

    cn08 = finalize([
        {"session_id": "sCN8", "message_id": "m1", "timestamp": "2026-01-10T00:20:00Z", "sender": "agent:A", "message_type": "CAPABILITIES_DECLARE", "contract_id": "cCN8", "payload": {"capabilities_id": "cap-A-8", "party_id": "agent:A", "supported_profiles": ["AICP-JCS-1", "AICP-HASH-SHA256-1", "AICP-SIG-ED25519-1"], "supported_privacy_modes": ["standard", "strict"], "supported_extensions": ["EXT-CAPNEG", "EXT-POLICY-EVAL"], "supported_aicp_profiles": [{"profile_id": "AICP-MEDIATED-BLOCKING", "profile_version": "0.1"}] }},
        {"session_id": "sCN8", "message_id": "m2", "timestamp": "2026-01-10T00:20:02Z", "sender": "agent:B", "message_type": "CAPABILITIES_DECLARE", "contract_id": "cCN8", "payload": {"capabilities_id": "cap-B-8", "party_id": "agent:B", "supported_profiles": ["AICP-JCS-1", "AICP-HASH-SHA256-1", "AICP-SIG-ED25519-1"], "supported_privacy_modes": ["standard"], "supported_extensions": ["EXT-CAPNEG", "EXT-POLICY-EVAL"], "supported_aicp_profiles": [{"profile_id": "AICP-MEDIATED-BLOCKING", "profile_version": "0.1"}] }},
        {"session_id": "sCN8", "message_id": "m3", "timestamp": "2026-01-10T00:20:04Z", "sender": "agent:A", "message_type": "CAPABILITIES_PROPOSE", "contract_id": "cCN8", "payload": {"negotiation_result": {**negotiation_result, "session_id": "sCN8", "contract_id": "cCN8", "negotiation_id": "NEG-CN8"}}},
        {"session_id": "sCN8", "message_id": "m4", "timestamp": "2026-01-10T00:20:06Z", "sender": "agent:B", "message_type": "CAPABILITIES_ACCEPT", "contract_id": "cCN8", "payload": {"negotiation_id": "NEG-CN8", "accepted": True, "negotiation_result_hash": object_hash("capneg.negotiation_result", {**negotiation_result, "session_id": "sCN8", "contract_id": "cCN8", "negotiation_id": "NEG-CN8"})}},
        {"session_id": "sCN8", "message_id": "m5", "timestamp": "2026-01-10T00:20:08Z", "sender": "agent:A", "message_type": "CONTRACT_PROPOSE", "contract_id": "cCN8", "contract_ref": cref, "payload": {"contract": {"contract_id": "cCN8", "goal": "capneg_bound_contract_fail", "roles": ["initiator", "responder"], "ext": {"capneg": {"negotiation_result_hash": "sha256:WRONG"}}}}},
        {"session_id": "sCN8", "message_id": "m6", "timestamp": "2026-01-10T00:20:10Z", "sender": "agent:B", "message_type": "CONTRACT_ACCEPT", "contract_id": "cCN8", "contract_ref": cref, "payload": {"accepted": True}},
    ])

    out = ROOT / "fixtures/extensions/capneg"
    write(out / "CN-07_negotiation_bound_into_contract_pass.jsonl", cn07)
    write(out / "CN-08_missing_or_mismatched_contract_binding_expected_fail.jsonl", cn08)
    print("Generated CAPNEG binding fixtures")


if __name__ == "__main__":
    main()
