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


def _base_rows(deliver_sender: str) -> list[dict]:
    cref = {"branch_id": "main", "base_version": "v1", "head_version": "v1"}
    negotiation_result = {
        "negotiation_id": "neg-rc1",
        "session_id": "sRC1",
        "contract_id": "cRC1",
        "participants": ["agent:A", "agent:B"],
        "selected": {
            "crypto_profile": ["AICP-JCS-1", "AICP-HASH-SHA256-1", "AICP-SIG-ED25519-1"],
            "privacy_mode": "standard",
            "required_extensions": [
                "EXT-CAPNEG",
                "EXT-PARTICIPANTS",
                "EXT-POLICY-EVAL",
                "EXT-ENFORCEMENT",
                "EXT-SECURITY-ALERT",
                "EXT-DISPUTES"
            ],
            "aicp_profile": {
                "profile_id": "AICP-RECEPTION-CHAT",
                "profile_version": "0.1"
            }
        },
        "transcript_binding": "chain:rc1:m3"
    }
    negotiation_hash = object_hash("negotiation_result", negotiation_result)

    return [
        {
            "session_id": "sRC1",
            "message_id": "m1",
            "timestamp": "2026-02-01T00:00:00Z",
            "sender": "agent:A",
            "message_type": "CAPABILITIES_DECLARE",
            "contract_id": "cRC1",
            "contract_ref": cref,
            "payload": {
                "capabilities_id": "cap-a-rc1",
                "party_id": "agent:A",
                "supported_profiles": ["AICP-JCS-1", "AICP-HASH-SHA256-1", "AICP-SIG-ED25519-1"],
                "supported_privacy_modes": ["standard"],
                "supported_extensions": ["EXT-CAPNEG", "EXT-PARTICIPANTS", "EXT-POLICY-EVAL", "EXT-ENFORCEMENT"],
                "required_aicp_profiles": [{"profile_id": "AICP-RECEPTION-CHAT", "profile_version": "0.1"}],
            },
        },
        {
            "session_id": "sRC1",
            "message_id": "m2",
            "timestamp": "2026-02-01T00:00:01Z",
            "sender": "agent:B",
            "message_type": "CAPABILITIES_DECLARE",
            "contract_id": "cRC1",
            "contract_ref": cref,
            "payload": {
                "capabilities_id": "cap-b-rc1",
                "party_id": "agent:B",
                "supported_profiles": ["AICP-JCS-1", "AICP-HASH-SHA256-1", "AICP-SIG-ED25519-1"],
                "supported_privacy_modes": ["standard"],
                "supported_extensions": [
                    "EXT-CAPNEG",
                    "EXT-PARTICIPANTS",
                    "EXT-POLICY-EVAL",
                    "EXT-ENFORCEMENT",
                    "EXT-SECURITY-ALERT",
                    "EXT-DISPUTES"
                ],
                "required_aicp_profiles": [{"profile_id": "AICP-RECEPTION-CHAT", "profile_version": "0.1"}],
            },
        },
        {
            "session_id": "sRC1",
            "message_id": "m3",
            "timestamp": "2026-02-01T00:00:02Z",
            "sender": "agent:B",
            "message_type": "CAPABILITIES_PROPOSE",
            "contract_id": "cRC1",
            "contract_ref": cref,
            "payload": {
                "negotiation_result": negotiation_result,
            },
        },
        {
            "session_id": "sRC1",
            "message_id": "m4",
            "timestamp": "2026-02-01T00:00:03Z",
            "sender": "agent:A",
            "message_type": "CAPABILITIES_ACCEPT",
            "contract_id": "cRC1",
            "contract_ref": cref,
            "payload": {
                "negotiation_id": "neg-rc1",
                "accepted": True,
                "negotiation_result": negotiation_result,
            },
        },
        {
            "session_id": "sRC1",
            "message_id": "m5",
            "timestamp": "2026-02-01T00:00:04Z",
            "sender": "agent:A",
            "message_type": "CONTRACT_PROPOSE",
            "contract_id": "cRC1",
            "contract_ref": cref,
            "payload": {
                "contract": {
                    "contract_id": "cRC1",
                    "goal": "reception_chat_semantics",
                    "roles": ["initiator", "mediator", "participant", "enforcer"],
                    "ext": {
                        "capneg": {
                            "negotiation_result_hash": negotiation_hash,
                            "selected": negotiation_result["selected"],
                        },
                        "enforcement": {
                            "mode": "blocking",
                            "enforcers": ["enforcer:E"],
                            "mediators": ["mediator:M"],
                            "gated_message_types": ["CONTENT_MESSAGE"],
                        },
                        "participants": {
                            "model": "shared_contract",
                            "acceptors": ["mediator:M"],
                            "roles_catalog": ["role:participant"],
                        },
                    },
                }
            },
        },
        {
            "session_id": "sRC1",
            "message_id": "m6",
            "timestamp": "2026-02-01T00:00:05Z",
            "sender": "agent:B",
            "message_type": "CONTRACT_ACCEPT",
            "contract_id": "cRC1",
            "contract_ref": cref,
            "payload": {"accepted": True},
        },
        {
            "session_id": "sRC1",
            "message_id": "m7",
            "timestamp": "2026-02-01T00:00:06Z",
            "sender": "user:U",
            "message_type": "PARTICIPANT_JOIN",
            "contract_id": "cRC1",
            "contract_ref": cref,
            "payload": {"participant_id": "user:U", "requested_roles": ["role:participant"]},
        },
        {
            "session_id": "sRC1",
            "message_id": "m8",
            "timestamp": "2026-02-01T00:00:07Z",
            "sender": "mediator:M",
            "message_type": "PARTICIPANT_ACCEPT",
            "contract_id": "cRC1",
            "contract_ref": cref,
            "payload": {"participant_id": "user:U", "granted_roles": ["role:participant"]},
        },
        {
            "session_id": "sRC1",
            "message_id": "m9",
            "timestamp": "2026-02-01T00:00:08Z",
            "sender": "user:U",
            "message_type": "CONTENT_MESSAGE",
            "contract_id": "cRC1",
            "contract_ref": cref,
            "payload": {"content": "Need desk assistance for reception check-in.", "content_type": "text/plain"},
        },
        {
            "session_id": "sRC1",
            "message_id": "m10",
            "timestamp": "2026-02-01T00:00:09Z",
            "sender": "enforcer:E",
            "message_type": "ENFORCEMENT_VERDICT",
            "contract_id": "cRC1",
            "contract_ref": cref,
            "payload": {
                "target_message_hash": "__TARGET_HASH__",
                "decision": "ALLOW",
                "reason": "policy_ok",
                "reason_code": "ALLOW_POLICY",
            },
        },
        {
            "session_id": "sRC1",
            "message_id": "m11",
            "timestamp": "2026-02-01T00:00:10Z",
            "sender": deliver_sender,
            "message_type": "CONTENT_DELIVER",
            "contract_id": "cRC1",
            "contract_ref": cref,
            "payload": {
                "original_message_hash": "__TARGET_HASH__",
                "original_message": {
                    "message_type": "CONTENT_MESSAGE",
                    "message_hash": "__TARGET_HASH__",
                    "sender": "user:U",
                    "payload": {"content": "Need desk assistance for reception check-in.", "content_type": "text/plain"},
                },
                "verdict_message_id": "m10",
            },
        },
    ]


def _finalize_reception(rows: list[dict]) -> list[dict]:
    interim = finalize(rows)
    target_hash = interim[8]["message_hash"]
    interim[9]["payload"]["target_message_hash"] = target_hash
    interim[10]["payload"]["original_message_hash"] = target_hash
    interim[10]["payload"]["original_message"]["message_hash"] = target_hash
    return finalize(interim)


def main() -> None:
    out = ROOT / "fixtures/extensions/reception_chat"
    rc01 = _finalize_reception(_base_rows("mediator:M"))
    rc02 = _finalize_reception(_base_rows("user:U"))

    write(out / "RC-01_reception_chat_semantics_pass.jsonl", rc01)
    write(out / "RC-02_content_deliver_not_from_mediator_expected_fail.jsonl", rc02)
    print("Generated reception chat semantics fixtures")


if __name__ == "__main__":
    main()
