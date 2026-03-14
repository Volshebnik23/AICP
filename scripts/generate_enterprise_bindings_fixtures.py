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


def enterprise_bindings_config(case: str, *, missing_openapi_operation: bool = False, invalid_policy_kind: bool = False, requires_obs_correlation: bool = False) -> dict:
    return {
        "openapi_bindings": [
            {
                "binding_id": f"eb-openapi-{case}",
                "spec_ref": "spec:openapi:crm:v3@sha256:9f3d1c7a",
                "operation_id": "" if missing_openapi_operation else "createCustomerCase",
                "tool_id": "tools.crm.case.create",
                "projection_ref": "proj:crm.case.v1",
                "binding_version": "2026-03",
                "namespace": "enterprise:crm"
            }
        ],
        "odata_bindings": [
            {
                "binding_id": f"eb-odata-{case}",
                "service_ref": "odata:service:erp:v2",
                "target_ref": "entityset:ServiceTickets",
                "select_ref": "select:ticket_minimal",
                "filter_ref": "filter:active_only",
                "orderby_ref": "orderby:updated_desc",
                "page_ref": "page:size50",
                "binding_version": "2026-03",
                "namespace": "enterprise:erp"
            }
        ],
        "policy_xrefs": [
            {
                "xref_id": f"eb-policy-{case}-rbac",
                "policy_kind": "legacy_rbac" if invalid_policy_kind else "rbac",
                "policy_ref": "policy:rbac:case-writer:v2",
                "subject_ref": "role:support.agent",
                "resource_ref": "resource:case",
                "action_ref": "ticket.create"
            },
            {
                "xref_id": f"eb-policy-{case}-opa",
                "policy_kind": "opa",
                "policy_ref": "policy:opa:service-ticket:v4",
                "subject_ref": "subject:agent",
                "resource_ref": "resource:ticket",
                "action_ref": "ticket.read",
                "opa_package_ref": "package:enterprise.ticket.authz"
            }
        ],
        "requires_obs_correlation": requires_obs_correlation
    }


def contract_payload(contract_id: str, case: str, **kwargs: bool) -> dict:
    return {
        "contract": {
            "contract_id": contract_id,
            "goal": "enterprise binding alignment",
            "roles": ["agent", "mediator", "approver"],
            "ext": {
                "enterprise_bindings": enterprise_bindings_config(case, **kwargs)
            }
        }
    }


def base_rows(case: str, **kwargs: bool) -> list[dict]:
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
            "payload": contract_payload(contract_id, case, **kwargs)
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


def tool_call(case: str, *, binding_ref_id: str, target_ref: str = "entityset:ServiceTickets", include_iam: bool = False, include_approval: bool = False) -> dict:
    ext: dict = {"enterprise_bindings": {"binding_ref_id": binding_ref_id}}
    if include_iam:
        ext["iam_bridge"] = {"action": "ticket.create", "required_scopes_any": ["tickets.write"]}
    if include_approval:
        ext["human_approval"] = {"required": True, "tool_call_id": f"tc-eb-{case}"}
    return {
        "session_id": f"seb-{case}",
        "message_id": "m3",
        "timestamp": "2026-03-14T10:01:00Z",
        "sender": "agent:A",
        "message_type": "TOOL_CALL_REQUEST",
        "contract_id": f"c-eb-{case}",
        "payload": {
            "tool_call_id": f"tc-eb-{case}",
            "tool_id": "tools.crm.case.create" if binding_ref_id.startswith("eb-openapi") else "tools.erp.ticket.query",
            "arguments": {
                "target_ref": target_ref,
                "query_ref": "query:ticket.open"
            },
            "ext": ext
        }
    }


def fixture_eb01() -> list[dict]:
    rows = base_rows("01")
    rows.append(tool_call("01", binding_ref_id="eb-openapi-01"))
    return finalize(rows)


def fixture_eb02() -> list[dict]:
    rows = base_rows("02")
    rows.append(tool_call("02", binding_ref_id="eb-odata-02", target_ref="entityset:ServiceTickets"))
    return finalize(rows)


def fixture_eb03() -> list[dict]:
    rows = base_rows("03")
    rows.append(tool_call("03", binding_ref_id="eb-openapi-03"))
    return finalize(rows)


def fixture_eb04() -> list[dict]:
    rows = base_rows("04", requires_obs_correlation=True)
    rows.append(
        {
            "session_id": "seb-04",
            "message_id": "m3",
            "timestamp": "2026-03-14T10:00:10Z",
            "sender": "agent:mediator",
            "message_type": "APPROVAL_CHALLENGE",
            "contract_id": "c-eb-04",
            "payload": {
                "target_binding": {"tool_call_id": "tc-eb-04"},
                "approver_id": "agent:approver",
                "scope": {"action": "ticket.create", "constraints": ["severity!=critical"]},
                "expires_at": "2026-03-14T10:10:00Z"
            }
        }
    )
    base = finalize(rows)
    rows.append(
        {
            "session_id": "seb-04",
            "message_id": "m4",
            "timestamp": "2026-03-14T10:00:11Z",
            "sender": "agent:approver",
            "message_type": "APPROVAL_GRANT",
            "contract_id": "c-eb-04",
            "payload": {
                "challenge_message_hash": base[-1]["message_hash"],
                "approver_id": "agent:approver",
                "target_binding": {"tool_call_id": "tc-eb-04"},
                "scope": {"action": "ticket.create", "constraints": ["severity!=critical"]},
                "expires_at": "2026-03-14T10:10:00Z",
                "grant_ref": "grant:eb:04"
            }
        }
    )
    rows.append(tool_call("04", binding_ref_id="eb-openapi-04", include_iam=True, include_approval=True) | {"message_id": "m5", "timestamp": "2026-03-14T10:01:00Z"})
    rows.append(
        {
            "session_id": "seb-04",
            "message_id": "m6",
            "timestamp": "2026-03-14T10:01:02Z",
            "sender": "agent:meter",
            "message_type": "OBS_SIGNAL",
            "contract_id": "c-eb-04",
            "payload": {
                "sla": {
                    "signal_type": "degraded",
                    "reason_code": "SERVICE_DEGRADED",
                    "observed_at": "2026-03-14T10:01:02Z",
                    "correlation_ref": {"tool_call_id": "tc-eb-04"}
                }
            }
        }
    )
    return finalize(rows)


def fixture_eb05() -> list[dict]:
    rows = base_rows("05", missing_openapi_operation=True)
    rows.append(tool_call("05", binding_ref_id="eb-openapi-05"))
    return finalize(rows)


def fixture_eb06() -> list[dict]:
    rows = base_rows("06")
    rows.append(tool_call("06", binding_ref_id="eb-odata-06", target_ref="entityset:ArchivedTickets"))
    return finalize(rows)


def fixture_eb07() -> list[dict]:
    rows = base_rows("07", invalid_policy_kind=True)
    rows.append(tool_call("07", binding_ref_id="eb-openapi-07"))
    return finalize(rows)


def fixture_eb08() -> list[dict]:
    rows = base_rows("08", requires_obs_correlation=True)
    rows.append(tool_call("08", binding_ref_id="eb-openapi-08") | {"message_id": "m3"})
    rows.append(
        {
            "session_id": "seb-08",
            "message_id": "m4",
            "timestamp": "2026-03-14T10:01:02Z",
            "sender": "agent:meter",
            "message_type": "OBS_SIGNAL",
            "contract_id": "c-eb-08",
            "payload": {
                "trace": {
                    "trace_id": "0af7651916cd43dd8448eb211c80319c",
                    "span_id": "b9c7c989f97918e1",
                    "correlation_ref": {"tool_call_id": "tc-eb-08-other"}
                }
            }
        }
    )
    return finalize(rows)


def main() -> int:
    fixtures = {
        "EB-01_openapi_tool_binding_pass.jsonl": fixture_eb01(),
        "EB-02_odata_retrieval_binding_pass.jsonl": fixture_eb02(),
        "EB-03_policy_xref_binding_pass.jsonl": fixture_eb03(),
        "EB-04_enterprise_flow_with_iam_and_approval_pass.jsonl": fixture_eb04(),
        "EB-05_missing_openapi_operation_ref_expected_fail.jsonl": fixture_eb05(),
        "EB-06_invalid_odata_target_expected_fail.jsonl": fixture_eb06(),
        "EB-07_invalid_policy_kind_expected_fail.jsonl": fixture_eb07(),
        "EB-08_binding_without_required_correlation_expected_fail.jsonl": fixture_eb08(),
    }
    for name, rows in fixtures.items():
        path = OUT_DIR / name
        write_jsonl(path, rows)
        print(f"wrote {path.relative_to(ROOT)} ({len(rows)} records)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
