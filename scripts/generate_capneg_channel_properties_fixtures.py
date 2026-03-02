#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference/python"))

from aicp_ref.hashing import message_hash_from_body, object_hash  # noqa: E402


OUT = ROOT / "fixtures/extensions/capneg/CN-09_channel_properties_negotiation_pass.jsonl"


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


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, separators=(",", ":"), ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def main() -> int:
    selected = {
        "crypto_profile": ["AICP-JCS-1", "AICP-HASH-SHA256-1", "AICP-SIG-ED25519-1"],
        "privacy_mode": "standard",
        "binding": "BIND-MCP-0.1",
        "channel_properties": {
            "CP-RELIABILITY-0.1": "at_least_once",
            "CP-ORDERING-0.1": "ordered",
            "CP-ACK-0.1": "explicit",
            "CP-REPLAY-WINDOW-0.1": 30
        }
    }
    negotiation_result = {
        "negotiation_id": "NEG-CN9",
        "session_id": "sCN9",
        "contract_id": "cCN9",
        "participants": ["agent:A", "agent:B"],
        "selected": selected,
        "transcript_binding": "msgid:m3"
    }
    negotiation_result_hash = object_hash("capneg.negotiation_result", negotiation_result)

    rows = finalize([
        {
            "session_id": "sCN9",
            "message_id": "m1",
            "timestamp": "2026-03-03T00:00:00Z",
            "sender": "agent:A",
            "message_type": "CAPABILITIES_DECLARE",
            "contract_id": "cCN9",
            "payload": {
                "capabilities_id": "cap-A-9",
                "party_id": "agent:A",
                "supported_profiles": ["AICP-JCS-1", "AICP-HASH-SHA256-1", "AICP-SIG-ED25519-1"],
                "supported_privacy_modes": ["standard", "strict"],
                "bindings": ["BIND-MCP-0.1"],
                "supported_channel_properties": {
                    "CP-RELIABILITY-0.1": ["at_least_once", "at_most_once"],
                    "CP-ORDERING-0.1": ["ordered", "unordered"],
                    "CP-ACK-0.1": ["none", "explicit"],
                    "CP-REPLAY-WINDOW-0.1": {"min": 15, "max": 120}
                }
            }
        },
        {
            "session_id": "sCN9",
            "message_id": "m2",
            "timestamp": "2026-03-03T00:00:02Z",
            "sender": "agent:B",
            "message_type": "CAPABILITIES_DECLARE",
            "contract_id": "cCN9",
            "payload": {
                "capabilities_id": "cap-B-9",
                "party_id": "agent:B",
                "supported_profiles": ["AICP-JCS-1", "AICP-HASH-SHA256-1", "AICP-SIG-ED25519-1"],
                "supported_privacy_modes": ["standard"],
                "bindings": ["BIND-MCP-0.1"],
                "supported_channel_properties": {
                    "CP-RELIABILITY-0.1": ["at_least_once"],
                    "CP-ORDERING-0.1": ["ordered"],
                    "CP-ACK-0.1": ["explicit"],
                    "CP-REPLAY-WINDOW-0.1": {"min": 0, "max": 45}
                }
            }
        },
        {
            "session_id": "sCN9",
            "message_id": "m3",
            "timestamp": "2026-03-03T00:00:04Z",
            "sender": "agent:A",
            "message_type": "CAPABILITIES_PROPOSE",
            "contract_id": "cCN9",
            "payload": {
                "negotiation_result": negotiation_result
            }
        },
        {
            "session_id": "sCN9",
            "message_id": "m4",
            "timestamp": "2026-03-03T00:00:06Z",
            "sender": "agent:B",
            "message_type": "CAPABILITIES_ACCEPT",
            "contract_id": "cCN9",
            "payload": {
                "negotiation_id": "NEG-CN9",
                "accepted": True,
                "negotiation_result_hash": negotiation_result_hash
            }
        }
    ])

    write_jsonl(OUT, rows)
    print(f"updated {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
