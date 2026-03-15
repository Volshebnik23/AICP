#!/usr/bin/env python3
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference/python"))
from aicp_ref.hashing import message_hash_from_body  # noqa: E402

OUT_DIR = ROOT / "fixtures/extensions/subscriptions"


def finalize(rows: list[dict]) -> list[dict]:
    prev = None
    out = []
    for row in rows:
        msg = deepcopy(row)
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


def sb01() -> list[dict]:
    return finalize([
        {"session_id":"ssb-01","message_id":"m1","timestamp":"2026-03-24T10:00:00Z","sender":"agent:subscriber","message_type":"SUBSCRIBE","contract_id":"c-sb-01","payload":{"subscription_id":"sub-01","channel_id":"org/acme/security","delivery_mode":"digest","filters":{"severity":["critical"],"locale":"en-US","tier":"gold"}}},
        {"session_id":"ssb-01","message_id":"m2","timestamp":"2026-03-24T10:00:01Z","sender":"agent:brand","message_type":"SUBSCRIPTION_STATE","contract_id":"c-sb-01","payload":{"subscription_id":"sub-01","cursor":"cur-001"}},
        {"session_id":"ssb-01","message_id":"m3","timestamp":"2026-03-24T10:00:02Z","sender":"agent:subscriber","message_type":"UNSUBSCRIBE","contract_id":"c-sb-01","payload":{"subscription_id":"sub-01"}}
    ])


def sb02() -> list[dict]:
    return finalize([
        {"session_id":"ssb-02","message_id":"m1","timestamp":"2026-03-24T10:10:00Z","sender":"agent:subscriber","message_type":"SUBSCRIBE","contract_id":"c-sb-02","payload":{"subscription_id":"sub-02","channel_id":"org/acme/security","delivery_mode":"realtime","filters":{"severity":["high"]}}},
        {"session_id":"ssb-02","message_id":"m2","timestamp":"2026-03-24T10:10:01Z","sender":"agent:brand","message_type":"SUBSCRIPTION_STATE","contract_id":"c-sb-02","payload":{"subscription_id":"sub-other","cursor":"cur-002"}}
    ])


def sb03() -> list[dict]:
    return finalize([
        {"session_id":"ssb-03","message_id":"m1","timestamp":"2026-03-24T10:20:00Z","sender":"agent:subscriber","message_type":"SUBSCRIBE","contract_id":"c-sb-03","payload":{"subscription_id":"sub-03","channel_id":"org/acme/security","delivery_mode":"digest","filters":{"severity":["critical"]}}},
        {"session_id":"ssb-03","message_id":"m2","timestamp":"2026-03-24T10:20:01Z","sender":"agent:brand","message_type":"SUBSCRIPTION_STATE","contract_id":"c-sb-03","payload":{"subscription_id":"sub-03","cursor":"cur-010"}},
        {"session_id":"ssb-03","message_id":"m3","timestamp":"2026-03-24T10:20:02Z","sender":"agent:brand","message_type":"SUBSCRIPTION_STATE","contract_id":"c-sb-03","payload":{"subscription_id":"sub-03","cursor":"cur-009"}}
    ])


def main() -> int:
    fixtures = {
        "SB-01_subscription_pass.jsonl": sb01(),
        "SB-02_state_for_unknown_subscription_expected_fail.jsonl": sb02(),
        "SB-03_bad_cursor_progression_expected_fail.jsonl": sb03(),
    }
    for name, rows in fixtures.items():
        path = OUT_DIR / name
        write_jsonl(path, rows)
        print(f"wrote {path.relative_to(ROOT)} ({len(rows)} records)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
