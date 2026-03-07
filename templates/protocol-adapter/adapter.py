#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


LOSSY_FIELDS_NOTE = (
    "payload is retained as-is, but relation/extension metadata is reduced to a compact projection; "
    "persist the full source envelope for authoritative replay and dispute review"
)


def _project_relation_meta(message: dict[str, Any]) -> dict[str, Any]:
    relation_keys = ["replaces", "supersedes", "relates_to", "parent_message_id", "thread_id"]
    relation = {key: message[key] for key in relation_keys if key in message}

    extension_keys = ["extensions", "profile", "capabilities", "channel", "binding"]
    extension = {key: message[key] for key in extension_keys if key in message}

    return {"relation": relation, "extension": extension}


def map_aicp_to_event(message: dict[str, Any]) -> dict[str, Any]:
    relation_meta = _project_relation_meta(message)
    return {
        "event_type": message.get("message_type"),
        "session_id": message.get("session_id"),
        "message_id": message.get("message_id"),
        "sender": message.get("sender"),
        "timestamp": message.get("timestamp"),
        "contract_id": message.get("contract_id"),
        "contract_ref": message.get("contract_ref"),
        "message_hash": message.get("message_hash"),
        "prev_msg_hash": message.get("prev_msg_hash"),
        "signatures": message.get("signatures", []),
        "payload": message.get("payload"),
        "audit_envelope": {
            "contract_ref": message.get("contract_ref"),
            "prev_msg_hash": message.get("prev_msg_hash"),
            "signatures": message.get("signatures", []),
            "relation_meta": relation_meta,
        },
        "projection_mode": "demo_with_audit_envelope",
        "projection_note": LOSSY_FIELDS_NOTE,
    }


def run(input_jsonl: Path) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for raw in input_jsonl.read_text(encoding="utf-8").splitlines():
        if not raw.strip():
            continue
        message = json.loads(raw)
        events.append(map_aicp_to_event(message))
    return events


if __name__ == "__main__":
    import sys

    src = Path(sys.argv[1])
    out = run(src)
    print(json.dumps(out, indent=2))
