#!/usr/bin/env python3
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference/python"))
from aicp_ref.hashing import message_hash_from_body  # noqa: E402

OUT_DIR = ROOT / "fixtures/extensions/inbox"


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


def ib01() -> list[dict]:
    rows = [
        {"session_id":"sib-01","message_id":"m1","timestamp":"2026-03-24T12:00:00Z","sender":"agent:brand","message_type":"RESPONSIBILITY_ASSIGN","contract_id":"c-ib-01","payload":{"transfer_id":"t-ib-01","action_ref":"delivery:item-01","from_party":"agent:brand","to_party":"agent:delivery","warranty_class":"best_effort"}},
        {"session_id":"sib-01","message_id":"m2","timestamp":"2026-03-24T12:00:01Z","sender":"agent:brand","message_type":"INBOX_ENQUEUE","contract_id":"c-ib-01","payload":{"inbox_id":"in-01","item_id":"item-01","channel_id":"org/acme/security"}},
        {"session_id":"sib-01","message_id":"m3","timestamp":"2026-03-24T12:00:02Z","sender":"agent:router","message_type":"INBOX_ROUTE","contract_id":"c-ib-01","payload":{"item_id":"item-01","route_key":"tier:gold","delivery_mode":"digest"}},
        {"session_id":"sib-01","message_id":"m4","timestamp":"2026-03-24T12:00:03Z","sender":"agent:router","message_type":"INBOX_LEASE_GRANT","contract_id":"c-ib-01","payload":{"inbox_id":"in-01","lease_id":"lease-01","ttl_seconds":30,"queue_lease_ref":"ql:lease-01","admission_ref":"adm:token-01","responsibility_transfer_id":"t-ib-01"}},
        {"session_id":"sib-01","message_id":"m5","timestamp":"2026-03-24T12:00:04Z","sender":"agent:delivery","message_type":"INBOX_ACK","contract_id":"c-ib-01","payload":{"inbox_id":"in-01","item_id":"item-01","lease_id":"lease-01"}},
    ]
    base = finalize(rows)
    rows.append({"session_id":"sib-01","message_id":"m6","timestamp":"2026-03-24T12:00:05Z","sender":"agent:meter","message_type":"OBS_SIGNAL","contract_id":"c-ib-01","payload":{"trace":{"trace_id":"trace-ib-01","span_id":"span-ib-01","correlation_ref":{"message_hash":base[3]["message_hash"]}}}})
    return finalize(rows)


def ib02() -> list[dict]:
    return finalize([
        {"session_id":"sib-02","message_id":"m1","timestamp":"2026-03-24T12:10:00Z","sender":"agent:delivery","message_type":"INBOX_ACK","contract_id":"c-ib-02","payload":{"inbox_id":"in-02","item_id":"item-missing","lease_id":"lease-missing"}}
    ])


def ib03() -> list[dict]:
    return finalize([
        {"session_id":"sib-03","message_id":"m1","timestamp":"2026-03-24T12:20:00Z","sender":"agent:brand","message_type":"CONTRACT_PROPOSE","contract_id":"c-ib-03","payload":{"contract":{"contract_id":"c-ib-03","goal":"inbox delivery","ext":{"inbox":{"require_queue_lease_ref":True,"require_admission_ref":True}}}}},
        {"session_id":"sib-03","message_id":"m2","timestamp":"2026-03-24T12:20:01Z","sender":"agent:brand","message_type":"INBOX_ENQUEUE","contract_id":"c-ib-03","payload":{"inbox_id":"in-03","item_id":"item-03"}},
        {"session_id":"sib-03","message_id":"m3","timestamp":"2026-03-24T12:20:02Z","sender":"agent:router","message_type":"INBOX_ROUTE","contract_id":"c-ib-03","payload":{"item_id":"item-03","route_key":"tier:silver"}},
        {"session_id":"sib-03","message_id":"m4","timestamp":"2026-03-24T12:20:03Z","sender":"agent:router","message_type":"INBOX_LEASE_GRANT","contract_id":"c-ib-03","payload":{"inbox_id":"in-03","lease_id":"lease-03","ttl_seconds":20}}
    ])


def main() -> int:
    fixtures = {
        "IB-01_inbox_with_queue_lease_pass.jsonl": ib01(),
        "IB-02_ack_without_enqueue_expected_fail.jsonl": ib02(),
        "IB-03_missing_queue_lease_context_expected_fail.jsonl": ib03(),
    }
    for name, rows in fixtures.items():
        path = OUT_DIR / name
        write_jsonl(path, rows)
        print(f"wrote {path.relative_to(ROOT)} ({len(rows)} records)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
