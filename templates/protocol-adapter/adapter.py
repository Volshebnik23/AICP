#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


def map_aicp_to_event(message: dict) -> dict:
    return {
        "event_type": message.get("message_type"),
        "session_id": message.get("session_id"),
        "contract_id": message.get("contract_id"),
        "message_hash": message.get("message_hash"),
        "payload": message.get("payload"),
    }


def run(input_jsonl: Path) -> list[dict]:
    events: list[dict] = []
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
