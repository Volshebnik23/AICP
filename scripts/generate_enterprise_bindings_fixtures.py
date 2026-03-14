#!/usr/bin/env python3
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference/python"))
from aicp_ref.hashing import message_hash_from_body, object_hash  # noqa: E402

OUT_DIR = ROOT / "fixtures/extensions/enterprise_bindings"


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


def base(session: str, contract_id: str, eb_ext: dict) -> list[dict]:
    return [
        {
            "session_id": session,
            "message_id": "m1",
            "timestamp": "2026-03-15T10:00:00Z",
            "sender": "agent:A",
            "message_type": "CONTRACT_PROPOSE",
            "contract_id": contract_id,
            "payload": {
                "contract": {
                    "contract_id": contract_id,
                    "goal": "enterprise_bindings",
                    "roles": ["agent", "mediator", "approver", "issuer"],
                    "ext": {
                        "enterprise_bindings": eb_ext,
                        "iam_bridge": {
                            "issuer_allowlist": ["https://idp.example"],
                            "scope_to_authority": {"orders.write": ["tool.call"]},
                            "role_to_authority": {"operator": ["tool.call"]},
                            "group_to_authority": {"tier2": ["tool.call"]},
                            "actions": {
                                "tool.execute_sensitive_approval": {
                                    "required_scopes_all": ["orders.write"],
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
            }
        },
        {
            "session_id": session,
            "message_id": "m2",
            "timestamp": "2026-03-15T10:00:01Z",
            "sender": "agent:B",
            "message_type": "CONTRACT_ACCEPT",
            "contract_id": contract_id,
            "payload": {"accepted": True}
        }
    ]


def eb_ext(operation_id: str = "postOrder", odata_target: str = "Orders", policy_kind: str = "abac", requires_obs_correlation: bool = False) -> dict:
    return {
        "openapi_bindings": [
            {
                "binding_id": "obind.orders.create",
                "spec_ref": "spec://openapi/orders@v1#sha256:abc123",
                "operation_id": operation_id,
                "tool_id": "tools.orders.create",
                "projection_ref": "proj://orders.create.v1",
                "binding_version": "1"
            }
        ],
        "odata_bindings": [
            {
                "binding_id": "odb.orders.list",
                "service_ref": "service://odata/orders@v4#sha256:def456",
                "target_ref": odata_target,
                "query_profile_ref": "qprof://orders.list.basic",
                "binding_version": "1"
            }
        ],
        "requires_obs_correlation": requires_obs_correlation,
        "policy_xrefs": [
            {
                "xref_id": "px.orders.create",
                "policy_kind": policy_kind,
                "policy_ref": "policy://orders/create",
                "subject_ref": "subject://employee",
                "resource_ref": "resource://orders",
                "action_ref": "tool.execute_sensitive_approval",
                "opa_package_ref": "opa://orders.authz.v1",
                "authority_map_ref": "authority://orders.tool.call"
            }
        ]
    }


def issue_binding_ref() -> dict:
    claims = {
        "issuer": "https://idp.example",
        "subject": "user:alpha",
        "scopes": ["orders.write"],
        "roles": ["operator"],
        "groups": ["tier2"],
        "acr": "urn:mfa:phishing-resistant",
        "amr": ["pwd", "otp"],
        "issued_at": "2026-03-15T09:59:00Z",
        "expires_at": "2026-03-15T11:00:00Z"
    }
    binding = {
        "binding_id": "bind-eb-iam",
        "agent_id": "agent:A",
        "account_id": "acct:alpha",
        "issuer": "auth:IDP",
        "scopes": ["orders.write"],
        "issued_at": "2026-03-15T10:00:02Z",
        "expires_at": "2026-03-15T10:30:00Z",
        "ext": {
            "iam_bridge_claims": claims,
            "iam_bridge_claims_hash": object_hash("iam_claims_snapshot", claims)
        }
    }
    return {
        "object_type": "subject_binding",
        "object": binding,
        "object_hash": object_hash("subject_binding", binding)
    }


def add_tool_call(rows: list[dict], session: str, contract_id: str, tool_call_id: str, binding_id: str, *, with_iam: bool = True, with_approval: bool = False) -> None:
    ext = {"enterprise_bindings": {"binding_ref_id": binding_id}}
    if with_iam:
        ext["iam_bridge"] = {"action": "tool.execute_sensitive_approval"}
    if with_approval:
        ext["human_approval"] = {"required": True, "tool_call_id": tool_call_id}
    rows.append(
        {
            "session_id": session,
            "message_id": f"m{len(rows)+1}",
            "timestamp": "2026-03-15T10:00:03Z",
            "sender": "agent:A",
            "message_type": "TOOL_CALL_REQUEST",
            "contract_id": contract_id,
            "payload": {
                "tool_call_id": tool_call_id,
                "tool_id": "tools.orders.create",
                "arguments": {"order_id": "o-1"},
                "ext": ext
            }
        }
    )


def add_obs(rows: list[dict], session: str, contract_id: str, tool_call_id: str) -> None:
    rows.append(
        {
            "session_id": session,
            "message_id": f"m{len(rows)+1}",
            "timestamp": "2026-03-15T10:00:04Z",
            "sender": "agent:mediator",
            "message_type": "OBS_SIGNAL",
            "contract_id": contract_id,
            "payload": {
                "sla": {
                    "signal_type": "degraded",
                    "reason_code": "SERVICE_DEGRADED",
                    "observed_at": "2026-03-15T10:00:04Z",
                    "correlation_ref": {"tool_call_id": tool_call_id}
                }
            }
        }
    )


def eb01() -> list[dict]:
    rows = base("seb-01", "ceb-01", eb_ext(requires_obs_correlation=True))
    add_tool_call(rows, "seb-01", "ceb-01", "tc-eb-01", "obind.orders.create")
    add_obs(rows, "seb-01", "ceb-01", "tc-eb-01")
    return finalize(rows)


def eb02(invalid_target: bool = False) -> list[dict]:
    rows = base("seb-06" if invalid_target else "seb-02", "ceb-06" if invalid_target else "ceb-02", eb_ext(odata_target="UnknownEntity" if invalid_target else "Orders"))
    rows.append(
        {
            "session_id": rows[0]["session_id"],
            "message_id": "m3",
            "timestamp": "2026-03-15T10:00:03Z",
            "sender": "agent:A",
            "message_type": "TOOL_CALL_REQUEST",
            "contract_id": rows[0]["contract_id"],
            "payload": {
                "tool_call_id": "tc-eb-02",
                "tool_id": "tools.odata.query",
                "arguments": {"target_ref": "Orders"},
                "ext": {
                    "enterprise_bindings": {"binding_ref_id": "odb.orders.list"}
                }
            }
        }
    )
    return finalize(rows)


def eb03(invalid_kind: bool = False) -> list[dict]:
    rows = base("seb-07" if invalid_kind else "seb-03", "ceb-07" if invalid_kind else "ceb-03", eb_ext(policy_kind="xacml" if invalid_kind else "opa"))
    rows.append(
        {
            "session_id": rows[0]["session_id"],
            "message_id": "m3",
            "timestamp": "2026-03-15T10:00:03Z",
            "sender": "agent:A",
            "message_type": "POLICY_EVAL_REQUEST",
            "contract_id": rows[0]["contract_id"],
            "payload": {
                "policy_ref": "policy://orders/create",
                "subject_ref": "subject://employee",
                "resource_ref": "resource://orders",
                "action_ref": "tool.execute_sensitive_approval"
            }
        }
    )
    return finalize(rows)


def eb04() -> list[dict]:
    rows = base("seb-04", "ceb-04", eb_ext(requires_obs_correlation=True))
    rows.append({
        "session_id": "seb-04", "message_id": "m3", "timestamp": "2026-03-15T10:00:02Z", "sender": "agent:issuer",
        "message_type": "SUBJECT_BINDING_ISSUE", "contract_id": "ceb-04", "payload": {"binding_ref": issue_binding_ref()}
    })
    rows.append({
        "session_id": "seb-04", "message_id": "m4", "timestamp": "2026-03-15T10:00:03Z", "sender": "agent:mediator",
        "message_type": "APPROVAL_CHALLENGE", "contract_id": "ceb-04",
        "payload": {"target_binding": {"tool_call_id": "tc-eb-04"}, "approver_id": "agent:approver", "scope": {"action": "tool.execute_sensitive_approval"}, "expires_at": "2026-03-15T10:10:00Z"}
    })
    base_rows = finalize(rows)
    rows.append({
        "session_id": "seb-04", "message_id": "m5", "timestamp": "2026-03-15T10:00:04Z", "sender": "agent:approver",
        "message_type": "APPROVAL_GRANT", "contract_id": "ceb-04",
        "payload": {"challenge_message_hash": base_rows[-1]["message_hash"], "approver_id": "agent:approver", "target_binding": {"tool_call_id": "tc-eb-04"}, "scope": {"action": "tool.execute_sensitive_approval"}, "expires_at": "2026-03-15T10:10:00Z"}
    })
    add_tool_call(rows, "seb-04", "ceb-04", "tc-eb-04", "obind.orders.create", with_iam=True, with_approval=True)
    add_obs(rows, "seb-04", "ceb-04", "tc-eb-04")
    return finalize(rows)


def eb05() -> list[dict]:
    rows = base("seb-05", "ceb-05", eb_ext(operation_id=""))
    add_tool_call(rows, "seb-05", "ceb-05", "tc-eb-05", "obind.orders.create")
    return finalize(rows)


def eb08() -> list[dict]:
    rows = base("seb-08", "ceb-08", eb_ext(requires_obs_correlation=True))
    add_tool_call(rows, "seb-08", "ceb-08", "tc-eb-08", "obind.orders.create")
    return finalize(rows)


def main() -> int:
    fixtures = {
        "EB-01_openapi_tool_binding_pass.jsonl": eb01(),
        "EB-02_odata_retrieval_binding_pass.jsonl": eb02(),
        "EB-03_policy_xref_binding_pass.jsonl": eb03(),
        "EB-04_enterprise_flow_with_iam_and_approval_pass.jsonl": eb04(),
        "EB-05_missing_openapi_operation_ref_expected_fail.jsonl": eb05(),
        "EB-06_invalid_odata_target_expected_fail.jsonl": eb02(invalid_target=True),
        "EB-07_invalid_policy_kind_expected_fail.jsonl": eb03(invalid_kind=True),
        "EB-08_binding_without_required_correlation_expected_fail.jsonl": eb08()
    }
    for name, rows in fixtures.items():
        write_jsonl(OUT_DIR / name, rows)
    print(f"Generated {len(fixtures)} enterprise-bindings fixtures in {OUT_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
