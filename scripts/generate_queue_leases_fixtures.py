#!/usr/bin/env python3
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference/python"))
from aicp_ref.hashing import message_hash_from_body  # noqa: E402

OUT_DIR = ROOT / "fixtures/extensions/queue_leases"


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


def base_contract(case: str, *, lease_required: bool = True, require_obs: bool = False) -> list[dict]:
    return [
        {
            "session_id": f"sql-{case}", "message_id": "m1", "timestamp": "2026-03-20T11:00:00Z", "sender": "agent:host", "message_type": "CONTRACT_PROPOSE", "contract_id": f"c-ql-{case}",
            "payload": {"contract": {"contract_id": f"c-ql-{case}", "goal": "crowd queue control", "roles": ["host", "participant"],
                                    "ext": {"queue_leases": {"lease_required": lease_required, "requires_obs_correlation": require_obs}}}}
        },
        {
            "session_id": f"sql-{case}", "message_id": "m2", "timestamp": "2026-03-20T11:00:01Z", "sender": "agent:participant", "message_type": "CONTRACT_ACCEPT", "contract_id": f"c-ql-{case}",
            "payload": {"accepted": True}
        }
    ]


def fixture_ql01() -> list[dict]:
    rows = base_contract("01", require_obs=True)
    rows.extend([
        {"session_id":"sql-01","message_id":"m3","timestamp":"2026-03-20T11:00:02Z","sender":"agent:participant","message_type":"QUEUE_ENQUEUE","contract_id":"c-ql-01",
         "payload":{"queue_id":"bazaar-main","item_id":"itm-01","priority_class":"standard","desired_lease_profile":"interactive"}},
        {"session_id":"sql-01","message_id":"m4","timestamp":"2026-03-20T11:00:03Z","sender":"mediator:queue","message_type":"QUEUE_LEASE_GRANT","contract_id":"c-ql-01",
         "payload":{"lease_id":"lease-01","queue_id":"bazaar-main","ttl_seconds":60,"max_msgs":2,"max_tool_calls":1,"allowed_message_types":["TOOL_CALL_REQUEST"]}},
        {"session_id":"sql-01","message_id":"m5","timestamp":"2026-03-20T11:00:04Z","sender":"agent:participant","message_type":"TOOL_CALL_REQUEST","contract_id":"c-ql-01",
         "payload":{"tool_call_id":"tc-ql-01","tool_id":"tools.listing.publish","arguments":{"title":"item"},"ext":{"queue_leases":{"lease_id":"lease-01"},"human_approval":{"required":True,"tool_call_id":"tc-ql-01"}}}},
        {"session_id":"sql-01","message_id":"m6","timestamp":"2026-03-20T11:00:05Z","sender":"mediator:queue","message_type":"QUEUE_ACK","contract_id":"c-ql-01",
         "payload":{"lease_id":"lease-01","item_id":"itm-01"}},
        {"session_id":"sql-01","message_id":"m7","timestamp":"2026-03-20T11:00:06Z","sender":"agent:participant","message_type":"QUEUE_RELEASE","contract_id":"c-ql-01",
         "payload":{"lease_id":"lease-01"}},
    ])
    base = finalize(rows)
    rows.append({"session_id":"sql-01","message_id":"m8","timestamp":"2026-03-20T11:00:07Z","sender":"agent:meter","message_type":"OBS_SIGNAL","contract_id":"c-ql-01",
                 "payload":{"trace":{"trace_id":"4bf92f3577b34da6a3ce929d0e0e4736","span_id":"00f067aa0ba902b7","correlation_ref":{"message_hash":base[3]["message_hash"]}}}})
    return finalize(rows)


def fixture_ql02() -> list[dict]:
    rows = base_contract("02")
    rows.extend([
        {"session_id":"sql-02","message_id":"m3","timestamp":"2026-03-20T11:10:02Z","sender":"agent:participant","message_type":"QUEUE_ENQUEUE","contract_id":"c-ql-02",
         "payload":{"queue_id":"bazaar-main","item_id":"itm-02"}},
        {"session_id":"sql-02","message_id":"m4","timestamp":"2026-03-20T11:10:03Z","sender":"mediator:queue","message_type":"QUEUE_LEASE_GRANT","contract_id":"c-ql-02",
         "payload":{"lease_id":"lease-02","queue_id":"bazaar-main","ttl_seconds":30,"max_msgs":1,"max_tool_calls":0}},
        {"session_id":"sql-02","message_id":"m5","timestamp":"2026-03-20T11:10:04Z","sender":"mediator:queue","message_type":"QUEUE_NACK","contract_id":"c-ql-02",
         "payload":{"lease_id":"lease-02","item_id":"itm-02","reason_code":"RATE_LIMITED","retry_after_seconds":15}},
        {"session_id":"sql-02","message_id":"m6","timestamp":"2026-03-20T11:10:05Z","sender":"mediator:queue","message_type":"THROTTLE_UPDATE","contract_id":"c-ql-02",
         "payload":{"max_msgs_per_minute":4,"max_tool_calls_per_minute":1,"applies_to_message_types":["QUEUE_ENQUEUE","TOOL_CALL_REQUEST"]}}
    ])
    return finalize(rows)


def fixture_ql03() -> list[dict]:
    rows = base_contract("03", lease_required=False)
    rows.extend([
        {"session_id":"sql-03","message_id":"m3","timestamp":"2026-03-20T11:20:02Z","sender":"mediator:queue","message_type":"OVERLOAD_SIGNAL","contract_id":"c-ql-03",
         "payload":{"severity":"high","reason_code":"SERVICE_DEGRADED","retry_after_seconds":20,"degradation_mode":"limited_accept","allowed_message_types":["QUEUE_ENQUEUE"]}},
        {"session_id":"sql-03","message_id":"m4","timestamp":"2026-03-20T11:20:03Z","sender":"mediator:queue","message_type":"THROTTLE_UPDATE","contract_id":"c-ql-03",
         "payload":{"max_msgs_per_minute":2,"applies_to_message_types":["QUEUE_ENQUEUE"]}}
    ])
    return finalize(rows)


def fixture_ql04() -> list[dict]:
    rows = base_contract("04", lease_required=True)
    rows.append({"session_id":"sql-04","message_id":"m3","timestamp":"2026-03-20T11:30:02Z","sender":"agent:participant","message_type":"TOOL_CALL_REQUEST","contract_id":"c-ql-04",
                 "payload":{"tool_call_id":"tc-ql-04","tool_id":"tools.listing.publish","arguments":{"title":"bad-no-lease"}}})
    return finalize(rows)


def fixture_ql05() -> list[dict]:
    rows = base_contract("05", lease_required=True)
    rows.extend([
        {"session_id":"sql-05","message_id":"m3","timestamp":"2026-03-20T11:40:02Z","sender":"mediator:queue","message_type":"QUEUE_LEASE_GRANT","contract_id":"c-ql-05",
         "payload":{"lease_id":"lease-05","queue_id":"bazaar-main","ttl_seconds":60,"max_msgs":1,"max_tool_calls":1,"allowed_message_types":["TOOL_CALL_REQUEST"]}},
        {"session_id":"sql-05","message_id":"m4","timestamp":"2026-03-20T11:40:03Z","sender":"agent:participant","message_type":"TOOL_CALL_REQUEST","contract_id":"c-ql-05",
         "payload":{"tool_call_id":"tc-ql-05a","tool_id":"tools.a","arguments":{},"ext":{"queue_leases":{"lease_id":"lease-05"}}}},
        {"session_id":"sql-05","message_id":"m5","timestamp":"2026-03-20T11:40:04Z","sender":"agent:participant","message_type":"TOOL_CALL_REQUEST","contract_id":"c-ql-05",
         "payload":{"tool_call_id":"tc-ql-05b","tool_id":"tools.b","arguments":{},"ext":{"queue_leases":{"lease_id":"lease-05"}}}}
    ])
    return finalize(rows)


def fixture_ql06() -> list[dict]:
    rows = base_contract("06", lease_required=False)
    rows.append({"session_id":"sql-06","message_id":"m3","timestamp":"2026-03-20T11:50:02Z","sender":"mediator:queue","message_type":"OVERLOAD_SIGNAL","contract_id":"c-ql-06",
                 "payload":{"severity":"urgent","reason_code":"SERVICE_DEGRADED","retry_after_seconds":10}})
    return finalize(rows)


def main() -> int:
    fixtures = {
        "QL-01_enqueue_lease_grant_bounded_release_pass.jsonl": fixture_ql01(),
        "QL-02_nack_with_retry_guidance_pass.jsonl": fixture_ql02(),
        "QL-03_overload_signal_degraded_mode_pass.jsonl": fixture_ql03(),
        "QL-04_interaction_without_lease_expected_fail.jsonl": fixture_ql04(),
        "QL-05_lease_overrun_expected_fail.jsonl": fixture_ql05(),
        "QL-06_invalid_overload_severity_expected_fail.jsonl": fixture_ql06(),
    }
    for name, rows in fixtures.items():
        path = OUT_DIR / name
        write_jsonl(path, rows)
        print(f"wrote {path.relative_to(ROOT)} ({len(rows)} records)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
