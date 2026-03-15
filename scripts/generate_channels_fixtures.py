#!/usr/bin/env python3
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference/python"))
from aicp_ref.hashing import message_hash_from_body  # noqa: E402

OUT_DIR = ROOT / "fixtures/extensions/channels"


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


def ch01() -> list[dict]:
    return finalize([
        {"session_id":"sch-01","message_id":"m1","timestamp":"2026-03-24T09:00:00Z","sender":"agent:brand","message_type":"CHANNEL_DECLARE","contract_id":"c-ch-01","payload":{"channel_id":"org/acme","version_id":"v1","visibility_class":"private"}},
        {"session_id":"sch-01","message_id":"m2","timestamp":"2026-03-24T09:00:01Z","sender":"agent:brand","message_type":"CHANNEL_DECLARE","contract_id":"c-ch-01","payload":{"channel_id":"org/acme/security","version_id":"v1","parent_channel_id":"org/acme","subject_tags":["security"],"topic_keys":["advisory"],"visibility_class":"private"}},
        {"session_id":"sch-01","message_id":"m3","timestamp":"2026-03-24T09:00:02Z","sender":"agent:brand","message_type":"CHANNEL_UPDATE","contract_id":"c-ch-01","payload":{"channel_id":"org/acme/security","version_id":"v2","parent_channel_id":"org/acme","subject_tags":["security","incident"],"topic_keys":["advisory","urgent"],"visibility_class":"private"}},
        {"session_id":"sch-01","message_id":"m4","timestamp":"2026-03-24T09:00:03Z","sender":"agent:brand","message_type":"CHANNEL_DEPRECATE","contract_id":"c-ch-01","payload":{"channel_id":"org/acme/security","version_id":"v3"}}
    ])


def ch02() -> list[dict]:
    return finalize([
        {"session_id":"sch-02","message_id":"m1","timestamp":"2026-03-24T09:10:00Z","sender":"agent:brand","message_type":"CHANNEL_DECLARE","contract_id":"c-ch-02","payload":{"channel_id":"org/acme/missing-parent-child","version_id":"v1","parent_channel_id":"org/acme/does-not-exist","visibility_class":"private"}}
    ])


def ch03() -> list[dict]:
    return finalize([
        {"session_id":"sch-03","message_id":"m1","timestamp":"2026-03-24T09:20:00Z","sender":"agent:brand","message_type":"CHANNEL_DECLARE","contract_id":"c-ch-03","payload":{"channel_id":"org/acme/private-root","version_id":"v1","visibility_class":"private"}},
        {"session_id":"sch-03","message_id":"m2","timestamp":"2026-03-24T09:20:01Z","sender":"agent:brand","message_type":"CHANNEL_DECLARE","contract_id":"c-ch-03","payload":{"channel_id":"org/acme/private-root/public-child","version_id":"v1","parent_channel_id":"org/acme/private-root","visibility_class":"public"}}
    ])


def main() -> int:
    fixtures = {
        "CH-01_channel_lifecycle_pass.jsonl": ch01(),
        "CH-02_missing_parent_expected_fail.jsonl": ch02(),
        "CH-03_visibility_escalation_expected_fail.jsonl": ch03(),
    }
    for name, rows in fixtures.items():
        path = OUT_DIR / name
        write_jsonl(path, rows)
        print(f"wrote {path.relative_to(ROOT)} ({len(rows)} records)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
