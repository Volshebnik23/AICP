#!/usr/bin/env python3
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference/python"))
from aicp_ref.hashing import message_hash_from_body  # noqa: E402

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


def enterprise_bindings_config(*, invalid_openapi_operation: bool = False, invalid_policy_kind: bool = False, requires_obs_correlation: bool = True) -> dict:
    return {
        "openapi_bindings": [
            {
                "binding_id": "eb-openapi-1",
                "spec_ref": "sha256:openapi:billing:v1",
                "operation_id": "" if invalid_openapi_operation else "createInvoice",
                "tool_id": "tools.billing.create_invoice",
                "projection_ref": "proj:billing:createInvoice:v1",
                "binding_version": "v1"
            }
        ],
        "odata_bindings": [
            {
                "binding_id": "eb-odata-1",
                "service_ref": "sha256:odata:crm:v4",
                "target_ref": "Customers",
                "select_ref": "select:customer-summary"
            }
        ],
        "policy_xrefs": [
            {
                "xref_id": "eb-policy-1",
                "policy_kind": "legacy" if invalid_policy_kind else "rbac",
                "policy_ref": "policy://corp/rbac/invoice-create",
                "subject_ref": "subject:user",
                "resource_ref": "resource:invoice",
                "action_ref": "invoice.create"
            },
            {
                "xref_id": "eb-policy-2",
                "policy_kind": "opa",
                "policy_ref": "policy://corp/opa/billing/allow_create",
                "opa_package_ref": "package.billing.authz",
                "action_ref": "invoice.create"
            }
        ],
        "requires_obs_correlation": requires_obs_correlation
    }


def contract_payload(contract_id: str, **kwargs: bool) -> dict:
    return {
        "contract": {
            "contract_id": contract_id,
            "goal": "enterprise-bindings",
            "roles": ["agent", "mediator", "approver"],
            "ext": {
                "enterprise_bindings": enterprise_bindings_config(**kwargs)
            }
        }
    }


def base_two(case: str, **kwargs: bool) -> list[dict]:
    session = f"seb-{case}"
    contract_id = f"c-eb-{case}"
    return [
        {
            "session_id": session,
            "message_id": "m1",
            "timestamp": "2026-03-14T10:00:00Z",
            "sender": "agent:A",
            "message_type": "CONTRACT_PROPOSE",
            "contract_id": contract_id,
            "payload": contract_payload(contract_id, **kwargs)
        },
        {
            "session_id": session,
            "message_id": "m2",
            "timestamp": "2026-03-14T10:00:01Z",
            "sender": "agent:B",
            "message_type": "CONTRACT_ACCEPT",
            "contract_id": contract_id,
            "payload": {"accepted": True}
        }
    ]


def make_tool_call(case: str, *, binding_ref_id: str = "eb-openapi-1", target_ref: str = "Customers", with_iam: bool = False, requires_approval: bool = False) -> dict:
    ext = {
        "enterprise_bindings": {
            "binding_ref_id": binding_ref_id
        }
    }
    if with_iam:
        ext["iam_bridge"] = {"action": "invoice.create"}
    if requires_approval:
        ext["human_approval"] = {"required": True, "tool_call_id": f"tc-eb-{case}"}

    return {
        "session_id": f"seb-{case}",
        "message_id": "m3" if not requires_approval else "m5",
        "timestamp": "2026-03-14T10:00:02Z" if not requires_approval else "2026-03-14T10:00:06Z",
        "sender": "agent:A",
        "message_type": "TOOL_CALL_REQUEST",
        "contract_id": f"c-eb-{case}",
        "payload": {
            "tool_call_id": f"tc-eb-{case}",
            "tool_id": "tools.billing.create_invoice" if binding_ref_id == "eb-openapi-1" else "tools.crm.query_customers",
            "arguments": {
                "target_ref": target_ref,
                "amount": 42
            },
            "ext": ext
        }
    }


def make_obs(case: str, tool_call_id: str) -> dict:
    return {
        "session_id": f"seb-{case}",
        "message_id": "m4" if case not in {"04"} else "m6",
        "timestamp": "2026-03-14T10:00:03Z" if case not in {"04"} else "2026-03-14T10:00:07Z",
        "sender": "agent:mediator",
        "message_type": "OBS_SIGNAL",
        "contract_id": f"c-eb-{case}",
        "payload": {
            "trace": {
                "trace_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "span_id": "1111111111111111",
                "correlation_ref": {"tool_call_id": tool_call_id}
            }
        }
    }


def fixture_eb01() -> list[dict]:
    rows = base_two("01")
    rows.append(make_tool_call("01", binding_ref_id="eb-openapi-1", target_ref="Customers"))
    rows.append(make_obs("01", "tc-eb-01"))
    return finalize(rows)


def fixture_eb02(invalid_target: bool = False) -> list[dict]:
    case = "06" if invalid_target else "02"
    rows = base_two(case)
    rows.append(make_tool_call(case, binding_ref_id="eb-odata-1", target_ref="Orders" if invalid_target else "Customers"))
    rows.append(make_obs(case, f"tc-eb-{case}"))
    return finalize(rows)


def fixture_eb03(invalid_policy_kind: bool = False) -> list[dict]:
    case = "07" if invalid_policy_kind else "03"
    rows = base_two(case, invalid_policy_kind=invalid_policy_kind)
    rows.append(make_tool_call(case, binding_ref_id="eb-openapi-1", target_ref="Customers"))
    rows.append(make_obs(case, f"tc-eb-{case}"))
    return finalize(rows)


def fixture_eb04() -> list[dict]:
    rows = base_two("04")
    rows.append(
        {
            "session_id": "seb-04",
            "message_id": "m3",
            "timestamp": "2026-03-14T10:00:03Z",
            "sender": "agent:mediator",
            "message_type": "APPROVAL_CHALLENGE",
            "contract_id": "c-eb-04",
            "payload": {
                "target_binding": {"tool_call_id": "tc-eb-04"},
                "approver_id": "agent:approver",
                "scope": {"action": "invoice.create", "constraints": ["amount<=100"]},
                "expires_at": "2026-03-14T10:10:00Z"
            }
        }
    )
    base = finalize(rows)
    rows.append(
        {
            "session_id": "seb-04",
            "message_id": "m4",
            "timestamp": "2026-03-14T10:00:04Z",
            "sender": "agent:approver",
            "message_type": "APPROVAL_GRANT",
            "contract_id": "c-eb-04",
            "payload": {
                "challenge_message_hash": base[-1]["message_hash"],
                "approver_id": "agent:approver",
                "target_binding": {"tool_call_id": "tc-eb-04"},
                "scope": {"action": "invoice.create", "constraints": ["amount<=100"]},
                "expires_at": "2026-03-14T10:10:00Z",
                "grant_ref": "grant:eb:04"
            }
        }
    )
    rows.append(make_tool_call("04", binding_ref_id="eb-openapi-1", target_ref="Customers", with_iam=True, requires_approval=True))
    rows.append(make_obs("04", "tc-eb-04"))
    return finalize(rows)


def fixture_eb05() -> list[dict]:
    rows = base_two("05", invalid_openapi_operation=True)
    rows.append(make_tool_call("05", binding_ref_id="eb-openapi-1", target_ref="Customers"))
    rows.append(make_obs("05", "tc-eb-05"))
    return finalize(rows)


def fixture_eb08() -> list[dict]:
    rows = base_two("08", requires_obs_correlation=True)
    rows.append(make_tool_call("08", binding_ref_id="eb-openapi-1", target_ref="Customers"))
    rows.append(make_obs("08", "tc-eb-different"))
    return finalize(rows)


def main() -> int:
    fixtures = {
        "EB-01_openapi_tool_binding_pass.jsonl": fixture_eb01(),
        "EB-02_odata_retrieval_binding_pass.jsonl": fixture_eb02(),
        "EB-03_policy_xref_binding_pass.jsonl": fixture_eb03(),
        "EB-04_enterprise_flow_with_iam_and_approval_pass.jsonl": fixture_eb04(),
        "EB-05_missing_openapi_operation_ref_expected_fail.jsonl": fixture_eb05(),
        "EB-06_invalid_odata_target_expected_fail.jsonl": fixture_eb02(invalid_target=True),
        "EB-07_invalid_policy_kind_expected_fail.jsonl": fixture_eb03(invalid_policy_kind=True),
        "EB-08_binding_without_required_correlation_expected_fail.jsonl": fixture_eb08()
    }

    for name, rows in fixtures.items():
        write_jsonl(OUT_DIR / name, rows)

    print(f"Generated {len(fixtures)} enterprise bindings fixtures in {OUT_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
