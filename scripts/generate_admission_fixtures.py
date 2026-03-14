#!/usr/bin/env python3
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference/python"))
from aicp_ref.hashing import message_hash_from_body  # noqa: E402

OUT_DIR = ROOT / "fixtures/extensions/admission"


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


def fixture_ad01() -> list[dict]:
    return finalize([
        {
            "session_id": "sad-01", "message_id": "m1", "timestamp": "2026-03-20T10:00:00Z", "sender": "agent:new",
            "message_type": "ADMISSION_REQUEST", "contract_id": "c-ad-01",
            "payload": {
                "request_id": "req-ad-01", "requested_roles": ["publisher"], "requested_scopes": ["publish.post"],
                "risk_tier": "medium", "desired_quota_class": "standard", "priority_class": "normal"
            }
        },
        {
            "session_id": "sad-01", "message_id": "m2", "timestamp": "2026-03-20T10:00:01Z", "sender": "mediator:host",
            "message_type": "ADMISSION_OFFER", "contract_id": "c-ad-01",
            "payload": {
                "request_id": "req-ad-01", "offer_id": "offer-ad-01", "granted_roles": ["publisher"],
                "granted_scopes": ["publish.post"], "quota_class": "standard", "lease_profile": "queue.standard"
            }
        },
        {
            "session_id": "sad-01", "message_id": "m3", "timestamp": "2026-03-20T10:00:02Z", "sender": "agent:new",
            "message_type": "ADMISSION_ACCEPT", "contract_id": "c-ad-01",
            "payload": {"request_id": "req-ad-01", "offer_id": "offer-ad-01", "accepted_at": "2026-03-20T10:00:02Z"}
        }
    ])


def fixture_ad02() -> list[dict]:
    return finalize([
        {
            "session_id": "sad-02", "message_id": "m1", "timestamp": "2026-03-20T10:10:00Z", "sender": "agent:risky",
            "message_type": "ADMISSION_REQUEST", "contract_id": "c-ad-02",
            "payload": {
                "request_id": "req-ad-02", "requested_roles": ["operator"], "requested_scopes": ["tool.exec.high_risk"],
                "risk_tier": "high", "attestation_refs": ["att:trust:seed:v1"]
            }
        },
        {
            "session_id": "sad-02", "message_id": "m2", "timestamp": "2026-03-20T10:10:01Z", "sender": "mediator:host",
            "message_type": "ADMISSION_REJECT", "contract_id": "c-ad-02",
            "payload": {"request_id": "req-ad-02", "reason_code": "SCOPE_VIOLATION"}
        }
    ])


def fixture_ad03() -> list[dict]:
    rows=[
        {
            "session_id":"sad-03","message_id":"m1","timestamp":"2026-03-20T10:20:00Z","sender":"agent:seed","message_type":"ADMISSION_REQUEST","contract_id":"c-ad-03",
            "payload":{"request_id":"req-ad-03a","requested_roles":["moderator"],"requested_scopes":["queue.moderate"],"risk_tier":"medium","attestation_refs":["msgid:m4"]}
        },
        {
            "session_id":"sad-03","message_id":"m2","timestamp":"2026-03-20T10:20:01Z","sender":"mediator:host","message_type":"ADMISSION_OFFER","contract_id":"c-ad-03",
            "payload":{"request_id":"req-ad-03a","offer_id":"offer-ad-03a","granted_roles":["moderator"],"granted_scopes":["queue.moderate"],"quota_class":"priority","lease_profile":"queue.priority"}
        },
        {
            "session_id":"sad-03","message_id":"m3","timestamp":"2026-03-20T10:20:02Z","sender":"agent:seed","message_type":"ADMISSION_ACCEPT","contract_id":"c-ad-03",
            "payload":{"request_id":"req-ad-03a","offer_id":"offer-ad-03a"}
        },
        {
            "session_id":"sad-03","message_id":"m4","timestamp":"2026-03-20T10:20:03Z","sender":"trust:notary","message_type":"ATTEST_ACTION","contract_id":"c-ad-03",
            "payload":{"attestation_ref":"att:trust:seed:v1","subject_ref":"agent:seed","action":"admission.renew"}
        },
        {
            "session_id":"sad-03","message_id":"m5","timestamp":"2026-03-20T10:20:04Z","sender":"mediator:host","message_type":"APPROVAL_CHALLENGE","contract_id":"c-ad-03",
            "payload":{"target_binding":{"message_hash":"sha256:placeholder"},"approver_id":"agent:approver","scope":{"action":"admission.renew","constraints":["queue.moderate"]},"expires_at":"2026-03-20T10:30:00Z"}
        }
    ]
    base=finalize(rows)
    rows[4]["payload"]["target_binding"]={"message_hash":base[0]["message_hash"]}
    rows.append({
        "session_id":"sad-03","message_id":"m6","timestamp":"2026-03-20T10:20:05Z","sender":"agent:approver","message_type":"APPROVAL_GRANT","contract_id":"c-ad-03",
        "payload":{"challenge_message_hash":"sha256:placeholder","approver_id":"agent:approver","target_binding":{"message_hash":"sha256:placeholder"},"scope":{"action":"admission.renew","constraints":["queue.moderate"]},"expires_at":"2026-03-20T10:30:00Z"}
    })
    base=finalize(rows)
    rows[5]["payload"]["challenge_message_hash"]=base[4]["message_hash"]
    rows[5]["payload"]["target_binding"]={"message_hash":base[0]["message_hash"]}
    rows.append({
        "session_id":"sad-03","message_id":"m7","timestamp":"2026-03-20T10:20:06Z","sender":"agent:seed","message_type":"ADMISSION_RENEW","contract_id":"c-ad-03",
        "payload":{"request_id":"req-ad-03b","prior_request_id":"req-ad-03a","reason_code":"RATE_LIMITED","attestation_refs":["msgid:m4"]}
    })
    rows.append({
        "session_id":"sad-03","message_id":"m8","timestamp":"2026-03-20T10:20:07Z","sender":"mediator:host","message_type":"ADMISSION_OFFER","contract_id":"c-ad-03",
        "payload":{"request_id":"req-ad-03b","offer_id":"offer-ad-03b","granted_roles":["moderator"],"granted_scopes":["queue.moderate"],"quota_class":"priority","lease_profile":"queue.priority","required_approval":True}
    })
    rows.append({
        "session_id":"sad-03","message_id":"m9","timestamp":"2026-03-20T10:20:08Z","sender":"agent:seed","message_type":"ADMISSION_ACCEPT","contract_id":"c-ad-03",
        "payload":{"request_id":"req-ad-03b","offer_id":"offer-ad-03b"}
    })
    return finalize(rows)


def fixture_ad04() -> list[dict]:
    return finalize([
        {"session_id":"sad-04","message_id":"m1","timestamp":"2026-03-20T10:30:00Z","sender":"agent:bad","message_type":"ADMISSION_REQUEST","contract_id":"c-ad-04",
         "payload":{"request_id":"req-ad-04","requested_roles":["publisher"],"requested_scopes":["publish.post"],"risk_tier":"low"}},
        {"session_id":"sad-04","message_id":"m2","timestamp":"2026-03-20T10:30:01Z","sender":"mediator:host","message_type":"ADMISSION_REJECT","contract_id":"c-ad-04",
         "payload":{"request_id":"req-ad-04","reason_code":""}}
    ])


def fixture_ad05() -> list[dict]:
    return finalize([
        {"session_id":"sad-05","message_id":"m1","timestamp":"2026-03-20T10:40:00Z","sender":"agent:scope","message_type":"ADMISSION_REQUEST","contract_id":"c-ad-05",
         "payload":{"request_id":"req-ad-05","requested_roles":["publisher"],"requested_scopes":["publish.post"],"risk_tier":"medium"}},
        {"session_id":"sad-05","message_id":"m2","timestamp":"2026-03-20T10:40:01Z","sender":"mediator:host","message_type":"ADMISSION_OFFER","contract_id":"c-ad-05",
         "payload":{"request_id":"req-ad-05","offer_id":"offer-ad-05","granted_roles":["publisher"],"granted_scopes":["publish.post","tool.exec.high_risk"],"quota_class":"standard","lease_profile":"queue.standard"}},
        {"session_id":"sad-05","message_id":"m3","timestamp":"2026-03-20T10:40:02Z","sender":"mediator:host","message_type":"ADMISSION_REJECT","contract_id":"c-ad-05",
         "payload":{"request_id":"req-ad-05","reason_code":"SCOPE_VIOLATION"}}
    ])


def fixture_ad06() -> list[dict]:
    return finalize([
        {"session_id":"sad-06","message_id":"m1","timestamp":"2026-03-20T10:50:00Z","sender":"agent:weird","message_type":"ADMISSION_REQUEST","contract_id":"c-ad-06",
         "payload":{"request_id":"req-ad-06","requested_roles":["publisher"],"requested_scopes":["publish.post"],"risk_tier":"low","attestation_refs":["badref-no-prefix"]}},
        {"session_id":"sad-06","message_id":"m2","timestamp":"2026-03-20T10:50:01Z","sender":"mediator:host","message_type":"ADMISSION_REJECT","contract_id":"c-ad-06",
         "payload":{"request_id":"req-ad-06","reason_code":"RATE_LIMITED"}}
    ])


def fixture_ad07() -> list[dict]:
    return finalize([
        {"session_id":"sad-07","message_id":"m1","timestamp":"2026-03-20T11:00:00Z","sender":"agent:member","message_type":"ADMISSION_REQUEST","contract_id":"c-ad-07",
         "payload":{"request_id":"req-ad-07","requested_roles":["participant"],"requested_scopes":["queue.post"],"risk_tier":"low"}},
        {"session_id":"sad-07","message_id":"m2","timestamp":"2026-03-20T11:00:01Z","sender":"mediator:host","message_type":"ADMISSION_OFFER","contract_id":"c-ad-07",
         "payload":{"request_id":"req-ad-07","offer_id":"offer-ad-07","granted_roles":["participant"],"granted_scopes":["queue.post"],"quota_class":"standard","lease_profile":"queue.standard"}},
        {"session_id":"sad-07","message_id":"m3","timestamp":"2026-03-20T11:00:02Z","sender":"agent:member","message_type":"ADMISSION_ACCEPT","contract_id":"c-ad-07",
         "payload":{"request_id":"req-ad-07","offer_id":"offer-ad-07"}},
        {"session_id":"sad-07","message_id":"m4","timestamp":"2026-03-20T11:05:00Z","sender":"mediator:host","message_type":"ADMISSION_REVOKE","contract_id":"c-ad-07",
         "payload":{"request_id":"req-ad-07","reason_code":"RATE_LIMITED","revoked_at":"2026-03-20T11:05:00Z"}}
    ])


def main() -> int:
    fixtures = {
        "AD-01_request_offer_accept_pass.jsonl": fixture_ad01(),
        "AD-02_request_reject_with_reason_pass.jsonl": fixture_ad02(),
        "AD-03_renew_with_prior_context_pass.jsonl": fixture_ad03(),
        "AD-04_reject_without_reason_expected_fail.jsonl": fixture_ad04(),
        "AD-05_offer_scope_violation_expected_fail.jsonl": fixture_ad05(),
        "AD-06_invalid_attestation_ref_expected_fail.jsonl": fixture_ad06(),
        "AD-07_revoke_with_reason_pass.jsonl": fixture_ad07(),
    }
    for name, rows in fixtures.items():
        path = OUT_DIR / name
        write_jsonl(path, rows)
        print(f"wrote {path.relative_to(ROOT)} ({len(rows)} records)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
