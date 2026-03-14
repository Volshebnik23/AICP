#!/usr/bin/env python3
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference/python"))
from aicp_ref.hashing import message_hash_from_body  # noqa: E402

OUT_DIR = ROOT / "fixtures/extensions/responsibility"


def finalize(rows: list[dict]) -> list[dict]:
    prev = None
    out: list[dict] = []
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


def rp01() -> list[dict]:
    rows = [
        {"session_id":"srp-01","message_id":"m1","timestamp":"2026-03-23T11:00:00Z","sender":"agent:planner","message_type":"PROVENANCE_DECLARE","contract_id":"c-rp-01",
         "payload":{"graph_id":"g-rp-01","nodes":[{"node_id":"n1","node_type":"artifact_node","artifact_ref":"objhash:sha256:r1"}]}},
        {"session_id":"srp-01","message_id":"m2","timestamp":"2026-03-23T11:00:01Z","sender":"agent:orchestrator","message_type":"RESPONSIBILITY_ASSIGN","contract_id":"c-rp-01",
         "payload":{"transfer_id":"t-01","action_ref":"toolcall:publish:01","from_party":"agent:orchestrator","to_party":"agent:worker","warranty_class":"best_effort"}},
        {"session_id":"srp-01","message_id":"m3","timestamp":"2026-03-23T11:00:02Z","sender":"agent:worker","message_type":"RESPONSIBILITY_ACCEPT","contract_id":"c-rp-01",
         "payload":{"transfer_id":"t-01","accepted_by":"agent:worker"}},
        {"session_id":"srp-01","message_id":"m4","timestamp":"2026-03-23T11:00:03Z","sender":"agent:worker","message_type":"CHAIN_FAILURE_ATTEST","contract_id":"c-rp-01",
         "payload":{"failure_id":"f-01","transfer_id":"t-01","classification":"permanent","reason_code":"SERVICE_DEGRADED","compensating_action_ref":"workflow:rollback:01","provenance_graph_id":"g-rp-01"}}
    ]
    base = finalize(rows)
    rows.append({"session_id":"srp-01","message_id":"m5","timestamp":"2026-03-23T11:00:04Z","sender":"agent:meter","message_type":"OBS_SIGNAL","contract_id":"c-rp-01",
                 "payload":{"trace":{"trace_id":"4bf92f3577b34da6a3ce929d0e0e4736","span_id":"00f067aa0ba902b7","correlation_ref":{"message_hash":base[3]["message_hash"]}}}})
    return finalize(rows)


def rp02() -> list[dict]:
    return finalize([
        {"session_id":"srp-02","message_id":"m1","timestamp":"2026-03-23T11:10:00Z","sender":"agent:worker","message_type":"RESPONSIBILITY_ACCEPT","contract_id":"c-rp-02",
         "payload":{"transfer_id":"t-missing","accepted_by":"agent:worker"}}
    ])


def rp03() -> list[dict]:
    return finalize([
        {"session_id":"srp-03","message_id":"m1","timestamp":"2026-03-23T11:20:00Z","sender":"agent:orchestrator","message_type":"RESPONSIBILITY_ASSIGN","contract_id":"c-rp-03",
         "payload":{"transfer_id":"t-03","action_ref":"toolcall:x","from_party":"agent:orchestrator","to_party":"agent:worker","warranty_class":"audited"}}
    ])


def rp04() -> list[dict]:
    return finalize([
        {"session_id":"srp-04","message_id":"m1","timestamp":"2026-03-23T11:30:00Z","sender":"agent:orchestrator","message_type":"RESPONSIBILITY_ASSIGN","contract_id":"c-rp-04",
         "payload":{"transfer_id":"t-04","action_ref":"toolcall:y","from_party":"agent:orchestrator","to_party":"agent:worker","warranty_class":"best_effort"}},
        {"session_id":"srp-04","message_id":"m2","timestamp":"2026-03-23T11:30:01Z","sender":"agent:worker","message_type":"RESPONSIBILITY_ACCEPT","contract_id":"c-rp-04",
         "payload":{"transfer_id":"t-04","accepted_by":"agent:worker"}},
        {"session_id":"srp-04","message_id":"m3","timestamp":"2026-03-23T11:30:02Z","sender":"agent:worker","message_type":"CHAIN_FAILURE_ATTEST","contract_id":"c-rp-04",
         "payload":{"failure_id":"f-04","transfer_id":"t-04","classification":"transient","reason_code":"RATE_LIMITED"}}
    ])


def rp05() -> list[dict]:
    return finalize([
        {"session_id":"srp-05","message_id":"m1","timestamp":"2026-03-23T11:40:00Z","sender":"agent:orchestrator","message_type":"RESPONSIBILITY_ASSIGN","contract_id":"c-rp-05",
         "payload":{"transfer_id":"t-05","action_ref":"toolcall:z","from_party":"agent:orchestrator","to_party":"agent:worker","warranty_class":"best_effort"}},
        {"session_id":"srp-05","message_id":"m2","timestamp":"2026-03-23T11:40:01Z","sender":"agent:worker","message_type":"RESPONSIBILITY_ACCEPT","contract_id":"c-rp-05",
         "payload":{"transfer_id":"t-05","accepted_by":"agent:worker"}},
        {"session_id":"srp-05","message_id":"m3","timestamp":"2026-03-23T11:40:02Z","sender":"agent:worker","message_type":"CHAIN_FAILURE_ATTEST","contract_id":"c-rp-05",
         "payload":{"failure_id":"f-05","transfer_id":"t-05","classification":"permanent","reason_code":"SERVICE_DEGRADED","provenance_graph_id":"g-missing"}}
    ])


def main() -> int:
    fixtures = {
        "RP-01_assign_accept_failure_attest_pass.jsonl": rp01(),
        "RP-02_accept_without_assign_expected_fail.jsonl": rp02(),
        "RP-03_missing_terminal_transfer_expected_fail.jsonl": rp03(),
        "RP-04_transient_failure_without_retry_expected_fail.jsonl": rp04(),
        "RP-05_failure_with_missing_provenance_expected_fail.jsonl": rp05(),
    }
    for name, rows in fixtures.items():
        path = OUT_DIR / name
        write_jsonl(path, rows)
        print(f"wrote {path.relative_to(ROOT)} ({len(rows)} records)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
