#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference/python"))

from aicp_ref.hashing import message_hash_from_body, object_hash  # noqa: E402

OUT_DIR = ROOT / "fixtures/extensions/iam_bridge"
CREF = {"branch_id": "main", "base_version": "v1", "head_version": "v1"}


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


def contract_iam_policy(approval_required: bool = False) -> dict:
    return {
        "issuers_allowlist": ["https://issuer.example"],
        "scope_authority_map": {
            "payments.write": ["auth:payments:write"],
            "highrisk.execute": ["auth:highrisk:execute"]
        },
        "role_authority_map": {
            "payments.operator": ["auth:payments:write"]
        },
        "group_authority_map": {
            "finance": ["auth:payments:write"]
        },
        "protected_actions": {
            "tool.execute.payment.capture": {
                "required_authority": ["auth:payments:write"],
                "required_scopes": ["payments.write"],
                "required_roles": ["payments.operator"],
                "required_groups": ["finance"],
                "required_acr": "urn:loa:2",
                "required_amr_all": ["pwd", "otp"],
                "approval_required": approval_required
            }
        }
    }


def claims(*, issuer="https://issuer.example", scopes=None, roles=None, groups=None, acr="urn:loa:2", amr=None) -> dict:
    return {
        "issuer": issuer,
        "subject": "user:alice",
        "scopes": scopes if scopes is not None else ["payments.write"],
        "roles": roles if roles is not None else ["payments.operator"],
        "groups": groups if groups is not None else ["finance"],
        "acr": acr,
        "amr": amr if amr is not None else ["pwd", "otp"],
        "issued_at": "2026-03-14T00:00:00Z",
        "expires_at": "2026-03-14T01:00:00Z"
    }


def build_case(case_id: str, *, claim_overrides=None, require_approval=False, include_approval=False) -> list[dict]:
    session_id = f"sib-{case_id}"
    contract_id = f"ibc-{case_id}"
    policy = contract_iam_policy(approval_required=require_approval)

    c = claims()
    if claim_overrides:
        c.update(claim_overrides)

    binding_object = {
        "binding_id": f"bind-{case_id}",
        "agent_id": "agent:worker",
        "account_id": "acct:alice",
        "issuer": "agent:idp",
        "scopes": ["act:on-behalf"],
        "issued_at": "2026-03-14T00:00:00Z",
        "expires_at": "2026-03-14T02:00:00Z",
        "iam_claims_snapshot": c
    }
    binding_hash = object_hash("subject_binding", binding_object)

    rows = [
        {
            "session_id": session_id,
            "message_id": "m1",
            "timestamp": "2026-03-14T00:00:00Z",
            "sender": "agent:caller",
            "message_type": "CONTRACT_PROPOSE",
            "contract_id": contract_id,
            "contract_ref": CREF,
            "payload": {
                "contract": {
                    "contract_id": contract_id,
                    "goal": "iam_bridge_controlled_action",
                    "roles": ["caller", "worker", "approver"],
                    "ext": {
                        "iam_bridge": policy,
                        "human_approval": {"default_required": bool(require_approval), "approval_policy_ref": "policy:approval:iam:v1"}
                    }
                }
            }
        },
        {
            "session_id": session_id,
            "message_id": "m2",
            "timestamp": "2026-03-14T00:00:01Z",
            "sender": "agent:worker",
            "message_type": "CONTRACT_ACCEPT",
            "contract_id": contract_id,
            "contract_ref": CREF,
            "payload": {"accepted": True}
        },
        {
            "session_id": session_id,
            "message_id": "m3",
            "timestamp": "2026-03-14T00:00:02Z",
            "sender": "agent:idp",
            "message_type": "SUBJECT_BINDING_ISSUE",
            "contract_id": contract_id,
            "payload": {
                "binding_hash": binding_hash,
                "binding_ref": {
                    "object_type": "subject_binding",
                    "object": binding_object,
                    "object_hash": binding_hash
                }
            }
        }
    ]

    if include_approval:
        rows.append({
            "session_id": session_id,
            "message_id": "m4",
            "timestamp": "2026-03-14T00:00:03Z",
            "sender": "agent:caller",
            "message_type": "APPROVAL_CHALLENGE",
            "contract_id": contract_id,
            "payload": {
                "target_binding": {"tool_call_id": "tc-ib-1"},
                "approver_id": "agent:approver",
                "scope": {"action": "tool.execute.payment.capture", "constraints": ["amount<=100"]},
                "expires_at": "2026-03-14T00:30:00Z"
            }
        })
        pre = finalize(rows)
        chash = pre[-1]["message_hash"]
        rows.append({
            "session_id": session_id,
            "message_id": "m5",
            "timestamp": "2026-03-14T00:00:04Z",
            "sender": "agent:approver",
            "message_type": "APPROVAL_GRANT",
            "contract_id": contract_id,
            "payload": {
                "challenge_message_hash": chash,
                "approver_id": "agent:approver",
                "target_binding": {"tool_call_id": "tc-ib-1"},
                "scope": {"action": "tool.execute.payment.capture", "constraints": ["amount<=100"]},
                "expires_at": "2026-03-14T00:30:00Z"
            }
        })
        action_id = "m6"
        action_ts = "2026-03-14T00:00:05Z"
    else:
        action_id = "m4"
        action_ts = "2026-03-14T00:00:03Z"

    rows.append({
        "session_id": session_id,
        "message_id": action_id,
        "timestamp": action_ts,
        "sender": "agent:worker",
        "message_type": "TOOL_CALL_REQUEST",
        "contract_id": contract_id,
        "ext": {"subject_binding_hash": binding_hash},
        "payload": {
            "tool_call_id": "tc-ib-1",
            "tool_id": "tools.payment.capture",
            "arguments": {"amount": 42, "currency": "USD"},
            "ext": {
                "iam_bridge": {"action_id": "tool.execute.payment.capture"},
                "human_approval": {"required": bool(require_approval), "tool_call_id": "tc-ib-1"}
            }
        }
    })

    return finalize(rows)


def main() -> int:
    fixtures = {
        "IB-01_scope_maps_to_delegation_authority_pass.jsonl": build_case("01"),
        "IB-02_role_group_maps_to_protected_action_pass.jsonl": build_case("02"),
        "IB-03_acr_amr_stepup_satisfied_pass.jsonl": build_case("03", require_approval=True, include_approval=True),
        "IB-04_missing_required_scope_expected_fail.jsonl": build_case("04", claim_overrides={"scopes": ["profile.read"]}),
        "IB-05_wrong_issuer_expected_fail.jsonl": build_case("05", claim_overrides={"issuer": "https://bad-issuer.example"}),
        "IB-06_missing_required_role_or_group_expected_fail.jsonl": build_case("06", claim_overrides={"roles": ["viewer"], "groups": ["finance"]}),
        "IB-07_required_acr_not_met_expected_fail.jsonl": build_case("07", claim_overrides={"acr": "urn:loa:1"}),
        "IB-08_required_amr_not_met_expected_fail.jsonl": build_case("08", claim_overrides={"amr": ["pwd"]}),
        "IB-09_missing_required_approval_evidence_expected_fail.jsonl": build_case("09", require_approval=True, include_approval=False)
    }

    for name, rows in fixtures.items():
        write_jsonl(OUT_DIR / name, rows)

    print(f"Generated {len(fixtures)} IAM bridge fixtures in {OUT_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
