#!/usr/bin/env python3
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference/python"))
from aicp_ref.hashing import message_hash_from_body  # noqa: E402

OUT_DIR = ROOT / "fixtures/extensions/marketplace"


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


def mp01() -> list[dict]:
    rows = [
        {"session_id":"smp-01","message_id":"m1","timestamp":"2026-03-22T09:00:00Z","sender":"agent:host","message_type":"CONTRACT_PROPOSE","contract_id":"c-mp-01",
         "payload":{"contract":{"contract_id":"c-mp-01","goal":"bazaar orchestration","roles":["host","bidder"],"ext":{"marketplace":{"routing_attestation_required":True,"requires_obs_correlation":True}}}}},
        {"session_id":"smp-01","message_id":"m2","timestamp":"2026-03-22T09:00:01Z","sender":"agent:bidderA","message_type":"CONTRACT_ACCEPT","contract_id":"c-mp-01","payload":{"accepted":True}},
        {"session_id":"smp-01","message_id":"m3","timestamp":"2026-03-22T09:00:02Z","sender":"agent:host","message_type":"RFW_POST","contract_id":"c-mp-01",
         "payload":{"rfw_id":"rfw-01","work_spec_ref":"work:listing.publish","policy_ref":"policy:group-routing:v1","deadline":"2026-03-23T09:00:00Z","budget_hint":"fixed:50","sla_hint":"p95<2s","required_attestation_refs":["att:trust:market:v1"]}},
        {"session_id":"smp-01","message_id":"m4","timestamp":"2026-03-22T09:00:03Z","sender":"agent:bidderA","message_type":"BID_SUBMIT","contract_id":"c-mp-01",
         "payload":{"bid_id":"bid-01","rfw_id":"rfw-01","offer_terms":{"price_hint":"fixed:45","sla_hint":"p95<2s"}}},
        {"session_id":"smp-01","message_id":"m5","timestamp":"2026-03-22T09:00:04Z","sender":"agent:host","message_type":"AWARD_ISSUE","contract_id":"c-mp-01",
         "payload":{"award_id":"award-01","rfw_id":"rfw-01","bid_id":"bid-01","work_order":{"work_order_id":"wo-01","workflow_ref":"workflow:sync:001"}}},
    ]
    base = finalize(rows)
    rows.extend([
        {"session_id":"smp-01","message_id":"m6","timestamp":"2026-03-22T09:00:05Z","sender":"agent:host","message_type":"ROUTING_DECISION_ATTEST","contract_id":"c-mp-01",
         "payload":{"decision_id":"route-01","award_id":"award-01","policy_ref":"policy:group-routing:v1","evidence_ref":f"msghash:{base[4]['message_hash']}"}},
        {"session_id":"smp-01","message_id":"m7","timestamp":"2026-03-22T09:00:06Z","sender":"agent:bidderA","message_type":"AWARD_ACCEPT","contract_id":"c-mp-01",
         "payload":{"award_id":"award-01","rfw_id":"rfw-01"}},
        {"session_id":"smp-01","message_id":"m8","timestamp":"2026-03-22T09:00:07Z","sender":"agent:meter","message_type":"OBS_SIGNAL","contract_id":"c-mp-01",
         "payload":{"trace":{"trace_id":"4bf92f3577b34da6a3ce929d0e0e4736","span_id":"00f067aa0ba902b7","correlation_ref":{"message_hash":base[4]['message_hash']}}}}
    ])
    return finalize(rows)


def mp02() -> list[dict]:
    return finalize([
        {"session_id":"smp-02","message_id":"m1","timestamp":"2026-03-22T09:10:00Z","sender":"agent:host","message_type":"RFW_POST","contract_id":"c-mp-02",
         "payload":{"rfw_id":"rfw-02","work_spec_ref":"work:data.enrich","policy_ref":"policy:auction:v1","deadline":"2026-03-23T09:10:00Z"}},
        {"session_id":"smp-02","message_id":"m2","timestamp":"2026-03-22T09:10:01Z","sender":"agent:host","message_type":"AUCTION_OPEN","contract_id":"c-mp-02",
         "payload":{"auction_id":"auc-02","rfw_id":"rfw-02","auction_mode":"sealed-bid","deadline":"2026-03-22T10:10:00Z"}},
        {"session_id":"smp-02","message_id":"m3","timestamp":"2026-03-22T09:10:02Z","sender":"agent:bidderB","message_type":"BID_SUBMIT","contract_id":"c-mp-02",
         "payload":{"bid_id":"bid-02","rfw_id":"rfw-02","offer_terms":{"price_hint":"fixed:70","sla_hint":"p95<5s"}}},
        {"session_id":"smp-02","message_id":"m4","timestamp":"2026-03-22T09:10:03Z","sender":"agent:host","message_type":"AUCTION_CLOSE","contract_id":"c-mp-02",
         "payload":{"auction_id":"auc-02","rfw_id":"rfw-02","result_ref":"bid:bid-02"}}
    ])


def mp03() -> list[dict]:
    return finalize([
        {"session_id":"smp-03","message_id":"m1","timestamp":"2026-03-22T09:20:00Z","sender":"agent:host","message_type":"BLACKBOARD_DECLARE","contract_id":"c-mp-03",
         "payload":{"workspace_id":"board-03","policy_ref":"policy:blackboard:v1","retention_ref":"retain:7d"}},
        {"session_id":"smp-03","message_id":"m2","timestamp":"2026-03-22T09:20:01Z","sender":"agent:coord","message_type":"BLACKBOARD_POST","contract_id":"c-mp-03",
         "payload":{"workspace_id":"board-03","entry_id":"e1","content_ref":"objhash:sha256:111"}},
        {"session_id":"smp-03","message_id":"m3","timestamp":"2026-03-22T09:20:02Z","sender":"agent:coord","message_type":"BLACKBOARD_UPDATE","contract_id":"c-mp-03",
         "payload":{"workspace_id":"board-03","entry_id":"e1","content_ref":"objhash:sha256:222"}},
        {"session_id":"smp-03","message_id":"m4","timestamp":"2026-03-22T09:20:03Z","sender":"agent:coord","message_type":"BLACKBOARD_REMOVE","contract_id":"c-mp-03",
         "payload":{"workspace_id":"board-03","entry_id":"e1"}}
    ])


def mp04() -> list[dict]:
    return finalize([
        {"session_id":"smp-04","message_id":"m1","timestamp":"2026-03-22T09:30:00Z","sender":"agent:host","message_type":"CONTRACT_PROPOSE","contract_id":"c-mp-04",
         "payload":{"contract":{"contract_id":"c-mp-04","goal":"subchat gating","roles":["host","participant"],"ext":{"marketplace":{"subchat_requires_admission":True}}}}},
        {"session_id":"smp-04","message_id":"m2","timestamp":"2026-03-22T09:30:01Z","sender":"agent:member","message_type":"ADMISSION_REQUEST","contract_id":"c-mp-04",
         "payload":{"request_id":"req-04","requested_roles":["participant"],"requested_scopes":["subchat.join"],"risk_tier":"low"}},
        {"session_id":"smp-04","message_id":"m3","timestamp":"2026-03-22T09:30:02Z","sender":"agent:host","message_type":"ADMISSION_OFFER","contract_id":"c-mp-04",
         "payload":{"request_id":"req-04","offer_id":"offer-04","granted_roles":["participant"],"granted_scopes":["subchat.join"],"quota_class":"standard","lease_profile":"queue.standard"}},
        {"session_id":"smp-04","message_id":"m4","timestamp":"2026-03-22T09:30:03Z","sender":"agent:member","message_type":"ADMISSION_ACCEPT","contract_id":"c-mp-04",
         "payload":{"request_id":"req-04","offer_id":"offer-04"}},
        {"session_id":"smp-04","message_id":"m5","timestamp":"2026-03-22T09:30:04Z","sender":"agent:host","message_type":"SUBCHAT_CREATE","contract_id":"c-mp-04",
         "payload":{"subchat_id":"sub-04","parent_chat_id":"chat-main","topic_tag":"auction.followup","admission_policy_ref":"policy:admission:v1"}},
        {"session_id":"smp-04","message_id":"m6","timestamp":"2026-03-22T09:30:05Z","sender":"agent:host","message_type":"SUBCHAT_INVITE","contract_id":"c-mp-04",
         "payload":{"subchat_id":"sub-04","invitee_id":"agent:member"}},
        {"session_id":"smp-04","message_id":"m7","timestamp":"2026-03-22T09:30:06Z","sender":"agent:member","message_type":"SUBCHAT_JOIN","contract_id":"c-mp-04",
         "payload":{"subchat_id":"sub-04","participant_id":"agent:member"}}
    ])


def mp05() -> list[dict]:
    return finalize([
        {"session_id":"smp-05","message_id":"m1","timestamp":"2026-03-22T09:40:00Z","sender":"agent:bad","message_type":"BID_SUBMIT","contract_id":"c-mp-05",
         "payload":{"bid_id":"bid-05","rfw_id":"rfw-missing","offer_terms":{"price_hint":"fixed:10","sla_hint":"p95<2s"}}}
    ])


def mp06() -> list[dict]:
    return finalize([
        {"session_id":"smp-06","message_id":"m1","timestamp":"2026-03-22T09:50:00Z","sender":"agent:host","message_type":"CONTRACT_PROPOSE","contract_id":"c-mp-06",
         "payload":{"contract":{"contract_id":"c-mp-06","goal":"attest required","ext":{"marketplace":{"routing_attestation_required":True}}}}},
        {"session_id":"smp-06","message_id":"m2","timestamp":"2026-03-22T09:50:01Z","sender":"agent:host","message_type":"RFW_POST","contract_id":"c-mp-06",
         "payload":{"rfw_id":"rfw-06","work_spec_ref":"work:x","policy_ref":"policy:routing:v1","deadline":"2026-03-23T09:50:00Z"}},
        {"session_id":"smp-06","message_id":"m3","timestamp":"2026-03-22T09:50:02Z","sender":"agent:bidder","message_type":"BID_SUBMIT","contract_id":"c-mp-06",
         "payload":{"bid_id":"bid-06","rfw_id":"rfw-06","offer_terms":{"price_hint":"fixed:20","sla_hint":"p95<4s"}}},
        {"session_id":"smp-06","message_id":"m4","timestamp":"2026-03-22T09:50:03Z","sender":"agent:host","message_type":"AWARD_ISSUE","contract_id":"c-mp-06",
         "payload":{"award_id":"award-06","rfw_id":"rfw-06","bid_id":"bid-06","work_order":{"work_order_id":"wo-06","workflow_ref":"workflow:sync:06"}}}
    ])


def mp07() -> list[dict]:
    return finalize([
        {"session_id":"smp-07","message_id":"m1","timestamp":"2026-03-22T10:00:00Z","sender":"agent:host","message_type":"CONTRACT_PROPOSE","contract_id":"c-mp-07",
         "payload":{"contract":{"contract_id":"c-mp-07","goal":"subchat admission required","ext":{"marketplace":{"subchat_requires_admission":True}}}}},
        {"session_id":"smp-07","message_id":"m2","timestamp":"2026-03-22T10:00:01Z","sender":"agent:host","message_type":"SUBCHAT_CREATE","contract_id":"c-mp-07",
         "payload":{"subchat_id":"sub-07","parent_chat_id":"chat-main","topic_tag":"ops"}},
        {"session_id":"smp-07","message_id":"m3","timestamp":"2026-03-22T10:00:02Z","sender":"agent:visitor","message_type":"SUBCHAT_JOIN","contract_id":"c-mp-07",
         "payload":{"subchat_id":"sub-07","participant_id":"agent:visitor"}}
    ])


def mp08() -> list[dict]:
    return finalize([
        {"session_id":"smp-08","message_id":"m1","timestamp":"2026-03-22T10:10:00Z","sender":"agent:host","message_type":"RFW_POST","contract_id":"c-mp-08",
         "payload":{"rfw_id":"rfw-08","work_spec_ref":"work:y","policy_ref":"policy:auction:v1","deadline":"2026-03-23T10:10:00Z"}},
        {"session_id":"smp-08","message_id":"m2","timestamp":"2026-03-22T10:10:01Z","sender":"agent:host","message_type":"AUCTION_OPEN","contract_id":"c-mp-08",
         "payload":{"auction_id":"auc-08","rfw_id":"rfw-08","auction_mode":"chaotic-mode","deadline":"2026-03-22T11:10:00Z"}}
    ])


def main() -> int:
    fixtures = {
        "MP-01_rfw_bid_award_workflow_pass.jsonl": mp01(),
        "MP-02_auction_open_close_pass.jsonl": mp02(),
        "MP-03_blackboard_coordination_pass.jsonl": mp03(),
        "MP-04_subchat_with_valid_admission_pass.jsonl": mp04(),
        "MP-05_bid_without_valid_rfw_expected_fail.jsonl": mp05(),
        "MP-06_award_without_required_evidence_expected_fail.jsonl": mp06(),
        "MP-07_subchat_without_required_admission_expected_fail.jsonl": mp07(),
        "MP-08_invalid_auction_mode_expected_fail.jsonl": mp08(),
    }
    for name, rows in fixtures.items():
        path = OUT_DIR / name
        write_jsonl(path, rows)
        print(f"wrote {path.relative_to(ROOT)} ({len(rows)} records)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
