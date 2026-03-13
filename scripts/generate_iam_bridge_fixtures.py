#!/usr/bin/env python3
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference/python"))
from aicp_ref.hashing import message_hash_from_body, object_hash  # noqa: E402

OUT_DIR = ROOT / "fixtures/extensions/iam_bridge"


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


def make_claims(*, issuer: str = "https://idp.example", scopes=None, roles=None, groups=None, acr: str = "urn:mfa:phishing-resistant", amr=None) -> dict:
    return {
        "issuer": issuer,
        "subject": "user:alpha",
        "scopes": scopes if scopes is not None else ["crm.read", "tool.execute"],
        "roles": roles if roles is not None else ["operator"],
        "groups": groups if groups is not None else ["tier2"],
        "acr": acr,
        "amr": amr if amr is not None else ["pwd", "otp"],
        "issued_at": "2026-03-10T09:59:00Z",
        "expires_at": "2026-03-10T11:00:00Z"
    }


def contract_obj(contract_id: str) -> dict:
    return {
        "contract_id": contract_id,
        "goal": "iam_bridge",
        "roles": ["agent", "issuer", "approver"],
        "ext": {
            "iam_bridge": {
                "issuer_allowlist": ["https://idp.example"],
                "scope_to_authority": {"crm.read": ["delegation.result_attest"], "tool.execute": ["tool.call"]},
                "role_to_authority": {"operator": ["tool.call"], "approver-role": ["approval.grant"]},
                "group_to_authority": {"tier2": ["tool.call"], "delegation-team": ["delegation.result_attest"]},
                "actions": {
                    "delegation.result_attest": {
                        "required_scopes_all": ["crm.read"],
                        "required_authority_any": ["delegation.result_attest"]
                    },
                    "tool.execute_sensitive": {
                        "required_scopes_all": ["tool.execute"],
                        "required_roles_all": ["operator"],
                        "required_groups_all": ["tier2"],
                        "required_authority_any": ["tool.call"],
                        "required_acr": "urn:mfa:phishing-resistant",
                        "required_amr_all": ["pwd", "otp"]
                    },
                    "tool.execute_sensitive_approval": {
                        "required_scopes_all": ["tool.execute"],
                        "required_roles_all": ["operator"],
                        "required_groups_all": ["tier2"],
                        "required_authority_any": ["tool.call"],
                        "required_acr": "urn:mfa:phishing-resistant",
                        "required_amr_all": ["pwd", "otp"],
                        "requires_human_approval": True,
                        "approval_scope_action": "tool.execute_sensitive_approval"
                    }
                }
            }
        }
    }


def base_rows(fid: str, *, claims: dict) -> list[dict]:
    session = f"s{fid}"
    contract_id = f"c{fid}"
    cref = {"branch_id": "main", "base_version": "v1", "head_version": "v1"}
    binding_obj = {
        "binding_id": f"b-{fid}",
        "agent_id": "agent:A",
        "account_id": "acct:alpha",
        "issuer": "auth:IDP",
        "scopes": ["chat:ops", "delegate:act"],
        "issued_at": "2026-03-10T10:00:03Z",
        "expires_at": "2026-03-10T11:30:00Z",
        "ext": {
            "iam_bridge_claims": claims,
            "iam_bridge_claims_hash": object_hash("iam_claims_snapshot", claims)
        }
    }
    binding_hash = object_hash("subject_binding", binding_obj)

    rows = [
        {"session_id": session, "message_id": "m1", "timestamp": "2026-03-10T10:00:00Z", "sender": "agent:A", "message_type": "CONTRACT_PROPOSE", "contract_id": contract_id, "contract_ref": cref, "payload": {"contract": contract_obj(contract_id)}},
        {"session_id": session, "message_id": "m2", "timestamp": "2026-03-10T10:00:01Z", "sender": "agent:B", "message_type": "CONTRACT_ACCEPT", "contract_id": contract_id, "contract_ref": cref, "payload": {"accepted": True}},
        {"session_id": session, "message_id": "m3", "timestamp": "2026-03-10T10:00:02Z", "sender": "auth:IDP", "message_type": "SUBJECT_BINDING_ISSUE", "contract_id": contract_id, "contract_ref": cref, "payload": {"binding_hash": binding_hash, "binding_ref": {"object_type": "subject_binding", "object": binding_obj, "object_hash": binding_hash}}}
    ]
    return rows


def add_attest_action(rows: list[dict], *, action: str = "delegation.result_attest", required_scopes=None, required_roles=None, required_groups=None, ts="2026-03-10T10:00:10Z"):
    ext = {"subject_binding_hash": rows[2]["payload"]["binding_hash"], "iam_bridge": {"action": action}}
    if required_scopes is not None:
        ext["iam_bridge"]["required_scopes"] = required_scopes
    if required_roles is not None:
        ext["iam_bridge"]["required_roles"] = required_roles
    if required_groups is not None:
        ext["iam_bridge"]["required_groups"] = required_groups
    rows.append({"session_id": rows[0]["session_id"], "message_id": f"m{len(rows)+1}", "timestamp": ts, "sender": "agent:A", "message_type": "ATTEST_ACTION", "contract_id": rows[0]["contract_id"], "contract_ref": rows[0]["contract_ref"], "ext": ext, "payload": {"action": action, "result_hash": f"sha256:{rows[0]['session_id']}-result"}})


def add_approval(rows: list[dict], *, tool_call_id: str = "tc-1"):
    rows.append({"session_id": rows[0]["session_id"], "message_id": f"m{len(rows)+1}", "timestamp": "2026-03-10T10:00:04Z", "sender": "agent:A", "message_type": "APPROVAL_CHALLENGE", "contract_id": rows[0]["contract_id"], "contract_ref": rows[0]["contract_ref"], "payload": {"target_binding": {"tool_call_id": tool_call_id}, "approver_id": "human:ops", "scope": {"action": "tool.execute_sensitive_approval"}, "expires_at": "2026-03-10T10:20:00Z"}})
    ch_hash = "PENDING"
    rows_f = finalize(rows)
    ch_hash = rows_f[-1]["message_hash"]
    rows[:] = [r for r in rows]
    rows.append({"session_id": rows[0]["session_id"], "message_id": f"m{len(rows)+1}", "timestamp": "2026-03-10T10:00:05Z", "sender": "human:ops", "message_type": "APPROVAL_GRANT", "contract_id": rows[0]["contract_id"], "contract_ref": rows[0]["contract_ref"], "payload": {"challenge_message_hash": ch_hash, "approver_id": "human:ops", "target_binding": {"tool_call_id": tool_call_id}, "scope": {"action": "tool.execute_sensitive_approval"}, "expires_at": "2026-03-10T10:20:00Z", "grant_ref": "ticket-123"}})


def add_tool_call(rows: list[dict], *, tool_call_id: str = "tc-1", ts="2026-03-10T10:00:08Z"):
    rows.append({"session_id": rows[0]["session_id"], "message_id": f"m{len(rows)+1}", "timestamp": ts, "sender": "agent:A", "message_type": "TOOL_CALL_REQUEST", "contract_id": rows[0]["contract_id"], "contract_ref": rows[0]["contract_ref"], "ext": {"subject_binding_hash": rows[2]["payload"]["binding_hash"], "iam_bridge": {"action": "tool.execute_sensitive_approval"}}, "payload": {"tool_call_id": tool_call_id, "tool": "payments.capture", "args": {"amount": 100}}})


def build_all() -> dict[str, list[dict]]:
    out = {}
    r = base_rows("IB01", claims=make_claims())
    add_attest_action(r, required_scopes=["crm.read"])
    out["IB-01_scope_maps_to_delegation_authority_pass.jsonl"] = finalize(r)

    r = base_rows("IB02", claims=make_claims())
    add_attest_action(r, action="tool.execute_sensitive", required_roles=["operator"], required_groups=["tier2"])
    out["IB-02_role_group_maps_to_protected_action_pass.jsonl"] = finalize(r)

    r = base_rows("IB03", claims=make_claims(acr="urn:mfa:phishing-resistant", amr=["pwd", "otp", "webauthn"]))
    add_approval(r)
    add_tool_call(r)
    out["IB-03_acr_amr_stepup_satisfied_pass.jsonl"] = finalize(r)

    r = base_rows("IB04", claims=make_claims(scopes=["crm.read"]))
    add_attest_action(r, action="tool.execute_sensitive")
    out["IB-04_missing_required_scope_expected_fail.jsonl"] = finalize(r)

    r = base_rows("IB05", claims=make_claims(issuer="https://evil-idp.example"))
    add_attest_action(r)
    out["IB-05_wrong_issuer_expected_fail.jsonl"] = finalize(r)

    r = base_rows("IB06", claims=make_claims(roles=["viewer"], groups=["tier1"]))
    add_attest_action(r, action="tool.execute_sensitive")
    out["IB-06_missing_required_role_or_group_expected_fail.jsonl"] = finalize(r)

    r = base_rows("IB07", claims=make_claims(acr="urn:mfa:password-only"))
    add_attest_action(r, action="tool.execute_sensitive")
    out["IB-07_required_acr_not_met_expected_fail.jsonl"] = finalize(r)

    r = base_rows("IB08", claims=make_claims(amr=["pwd"]))
    add_attest_action(r, action="tool.execute_sensitive")
    out["IB-08_required_amr_not_met_expected_fail.jsonl"] = finalize(r)

    r = base_rows("IB09", claims=make_claims())
    add_tool_call(r)
    out["IB-09_missing_required_approval_evidence_expected_fail.jsonl"] = finalize(r)

    return out


def main() -> int:
    for name, rows in build_all().items():
        write_jsonl(OUT_DIR / name, rows)
    print(f"wrote IAM bridge fixtures to {OUT_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
