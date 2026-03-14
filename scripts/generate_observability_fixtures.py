#!/usr/bin/env python3
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference/python"))
from aicp_ref.hashing import message_hash_from_body, object_hash  # noqa: E402

OUT_DIR = ROOT / "fixtures/extensions/observability"


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


def contract_payload(contract_id: str) -> dict:
    return {
        "contract": {
            "contract_id": contract_id,
            "goal": "observability",
            "roles": ["agent", "mediator", "approver"],
            "ext": {
                "observability": {
                    "signal_types": ["drop", "throttle", "deny", "degraded", "timeout"],
                    "meter_units": ["token", "call", "request"]
                }
            }
        }
    }


def base_two(case: str) -> list[dict]:
    session = f"sob-{case}"
    contract_id = f"c-ob-{case}"
    return [
        {
            "session_id": session,
            "message_id": "m1",
            "timestamp": "2026-03-14T09:00:00Z",
            "sender": "agent:A",
            "message_type": "CONTRACT_PROPOSE",
            "contract_id": contract_id,
            "payload": contract_payload(contract_id)
        },
        {
            "session_id": session,
            "message_id": "m2",
            "timestamp": "2026-03-14T09:00:01Z",
            "sender": "agent:B",
            "message_type": "CONTRACT_ACCEPT",
            "contract_id": contract_id,
            "payload": {"accepted": True}
        }
    ]


def fixture_ob01() -> list[dict]:
    rows = base_two("01")
    base = finalize(rows)
    rows.append(
        {
            "session_id": "sob-01",
            "message_id": "m3",
            "timestamp": "2026-03-14T09:00:02Z",
            "sender": "agent:mediator",
            "message_type": "OBS_SIGNAL",
            "contract_id": "c-ob-01",
            "payload": {
                "trace": {
                    "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
                    "span_id": "00f067aa0ba902b7",
                    "parent_span_id": "b7ad6b7169203331",
                    "trace_flags": "01",
                    "correlation_ref": {"message_hash": base[1]["message_hash"]}
                }
            }
        }
    )
    return finalize(rows)


def fixture_ob02() -> list[dict]:
    rows = base_two("02")
    rows.append(
        {
            "session_id": "sob-02",
            "message_id": "m3",
            "timestamp": "2026-03-14T09:01:00Z",
            "sender": "agent:A",
            "message_type": "TOOL_CALL_REQUEST",
            "contract_id": "c-ob-02",
            "payload": {
                "tool_call_id": "tc-ob-02",
                "tool_id": "tools.search",
                "arguments": {"q": "observability"}
            }
        }
    )
    rows.append(
        {
            "session_id": "sob-02",
            "message_id": "m4",
            "timestamp": "2026-03-14T09:01:01Z",
            "sender": "agent:mediator",
            "message_type": "OBS_SIGNAL",
            "contract_id": "c-ob-02",
            "payload": {
                "trace": {
                    "trace_id": "1234567890abcdef1234567890abcdef",
                    "span_id": "fedcba0987654321",
                    "correlation_ref": {"tool_call_id": "tc-ob-02"}
                }
            }
        }
    )
    return finalize(rows)


def fixture_ob03(invalid_signal: bool = False, invalid_reason: bool = False) -> list[dict]:
    rows = base_two("03" if not invalid_signal and not invalid_reason else ("08" if invalid_signal else "09"))
    base = finalize(rows)
    rows.append(
        {
            "session_id": rows[0]["session_id"],
            "message_id": "m3",
            "timestamp": "2026-03-14T09:02:00Z",
            "sender": "agent:mediator",
            "message_type": "OBS_SIGNAL",
            "contract_id": rows[0]["contract_id"],
            "payload": {
                "sla": {
                    "signal_type": "slow" if invalid_signal else "throttle",
                    "reason_code": "UNKNOWN_REASON_CODE" if invalid_reason else "RATE_LIMITED",
                    "observed_at": "2026-03-14T09:02:00Z",
                    "correlation_ref": {"message_hash": base[1]["message_hash"]}
                }
            }
        }
    )
    return finalize(rows)


def fixture_ob04(negative_meter: bool = False) -> list[dict]:
    case = "10" if negative_meter else "04"
    rows = base_two(case)
    rows.append(
        {
            "session_id": rows[0]["session_id"],
            "message_id": "m3",
            "timestamp": "2026-03-14T09:03:00Z",
            "sender": "agent:A",
            "message_type": "TOOL_CALL_REQUEST",
            "contract_id": rows[0]["contract_id"],
            "payload": {
                "tool_call_id": f"tc-ob-{case}",
                "tool_id": "tools.classify",
                "arguments": {"text": "ok"}
            }
        }
    )
    rows.append(
        {
            "session_id": rows[0]["session_id"],
            "message_id": "m4",
            "timestamp": "2026-03-14T09:03:02Z",
            "sender": "agent:meter",
            "message_type": "OBS_SIGNAL",
            "contract_id": rows[0]["contract_id"],
            "payload": {
                "metering": {
                    "meter_type": "tokens_input",
                    "quantity": -1 if negative_meter else 128,
                    "unit": "token",
                    "subject_ref": "acct:alpha",
                    "observed_at": "2026-03-14T09:03:02Z",
                    "window_start": "2026-03-14T09:03:00Z",
                    "window_end": "2026-03-14T09:03:02Z",
                    "correlation_ref": {"tool_call_id": f"tc-ob-{case}"}
                }
            }
        }
    )
    return finalize(rows)


def fixture_ob05() -> list[dict]:
    rows = base_two("05")
    claims = {
        "issuer": "https://idp.example",
        "subject": "user:alpha",
        "scopes": ["tool.execute"],
        "roles": ["operator"],
        "groups": ["tier2"],
        "acr": "urn:mfa:phishing-resistant",
        "amr": ["pwd", "otp"],
        "issued_at": "2026-03-14T08:59:00Z",
        "expires_at": "2026-03-14T10:00:00Z"
    }
    binding = {
        "binding_id": "bind-ob-05",
        "agent_id": "agent:A",
        "account_id": "acct:alpha",
        "issuer": "auth:IDP",
        "scopes": ["tool.execute"],
        "issued_at": "2026-03-14T09:00:05Z",
        "expires_at": "2026-03-14T09:30:00Z",
        "ext": {
            "iam_bridge_claims": claims,
            "iam_bridge_claims_hash": object_hash("iam_claims_snapshot", claims)
        }
    }
    rows.append(
        {
            "session_id": "sob-05",
            "message_id": "m3",
            "timestamp": "2026-03-14T09:00:05Z",
            "sender": "agent:issuer",
            "message_type": "SUBJECT_BINDING_ISSUE",
            "contract_id": "c-ob-05",
            "payload": {
                "binding_ref": {
                    "object_type": "subject_binding",
                    "object": binding,
                    "object_hash": object_hash("subject_binding", binding)
                }
            }
        }
    )
    rows.append(
        {
            "session_id": "sob-05",
            "message_id": "m4",
            "timestamp": "2026-03-14T09:00:06Z",
            "sender": "agent:mediator",
            "message_type": "APPROVAL_CHALLENGE",
            "contract_id": "c-ob-05",
            "payload": {
                "target_binding": {"tool_call_id": "tc-ob-05"},
                "approver_id": "agent:approver",
                "scope": {"action": "tool.execute_sensitive_approval", "constraints": ["amount<=100"]},
                "expires_at": "2026-03-14T09:10:00Z"
            }
        }
    )
    base = finalize(rows)
    rows.append(
        {
            "session_id": "sob-05",
            "message_id": "m5",
            "timestamp": "2026-03-14T09:00:07Z",
            "sender": "agent:approver",
            "message_type": "APPROVAL_GRANT",
            "contract_id": "c-ob-05",
            "payload": {
                "challenge_message_hash": base[-1]["message_hash"],
                "approver_id": "agent:approver",
                "target_binding": {"tool_call_id": "tc-ob-05"},
                "scope": {"action": "tool.execute_sensitive_approval", "constraints": ["amount<=100"]},
                "expires_at": "2026-03-14T09:10:00Z",
                "grant_ref": "grant:ob:05"
            }
        }
    )
    rows.append(
        {
            "session_id": "sob-05",
            "message_id": "m6",
            "timestamp": "2026-03-14T09:00:08Z",
            "sender": "agent:A",
            "message_type": "TOOL_CALL_REQUEST",
            "contract_id": "c-ob-05",
            "payload": {
                "tool_call_id": "tc-ob-05",
                "tool_id": "tools.payment.capture",
                "arguments": {"amount": 42},
                "ext": {
                    "iam_bridge": {"action": "tool.execute_sensitive_approval"},
                    "human_approval": {"required": True, "tool_call_id": "tc-ob-05"}
                }
            }
        }
    )
    base = finalize(rows)
    rows.append(
        {
            "session_id": "sob-05",
            "message_id": "m7",
            "timestamp": "2026-03-14T09:00:09Z",
            "sender": "agent:mediator",
            "message_type": "OBS_SIGNAL",
            "contract_id": "c-ob-05",
            "payload": {
                "sla": {
                    "signal_type": "degraded",
                    "reason_code": "SERVICE_DEGRADED",
                    "observed_at": "2026-03-14T09:00:09Z",
                    "correlation_ref": {"tool_call_id": "tc-ob-05"}
                }
            }
        }
    )
    rows.append(
        {
            "session_id": "sob-05",
            "message_id": "m8",
            "timestamp": "2026-03-14T09:00:10Z",
            "sender": "agent:mediator",
            "message_type": "OBS_SIGNAL",
            "contract_id": "c-ob-05",
            "payload": {
                "trace": {
                    "trace_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                    "span_id": "1111111111111111",
                    "parent_span_id": "2222222222222222",
                    "correlation_ref": {"message_hash": base[5]["message_hash"]}
                }
            }
        }
    )
    return finalize(rows)


def fixture_ob06() -> list[dict]:
    rows = base_two("06")
    rows.append(
        {
            "session_id": "sob-06",
            "message_id": "m3",
            "timestamp": "2026-03-14T09:06:00Z",
            "sender": "agent:mediator",
            "message_type": "OBS_SIGNAL",
            "contract_id": "c-ob-06",
            "payload": {
                "trace": {
                    "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
                    "span_id": "00f067aa0ba902b7"
                }
            }
        }
    )
    return finalize(rows)


def fixture_ob07() -> list[dict]:
    rows = base_two("07")
    base = finalize(rows)
    rows.append(
        {
            "session_id": "sob-07",
            "message_id": "m3",
            "timestamp": "2026-03-14T09:07:00Z",
            "sender": "agent:mediator",
            "message_type": "OBS_SIGNAL",
            "contract_id": "c-ob-07",
            "payload": {
                "trace": {
                    "trace_id": "bad-trace-id",
                    "span_id": "bad",
                    "parent_span_id": "bad",
                    "correlation_ref": {"message_hash": base[1]["message_hash"]}
                }
            }
        }
    )
    return finalize(rows)


def main() -> int:
    fixtures = {
        "OB-01_trace_correlates_message_pass.jsonl": fixture_ob01(),
        "OB-02_trace_correlates_tool_call_pass.jsonl": fixture_ob02(),
        "OB-03_sla_throttle_signal_pass.jsonl": fixture_ob03(),
        "OB-04_metering_usage_pass.jsonl": fixture_ob04(),
        "OB-05_stepup_flow_observability_pass.jsonl": fixture_ob05(),
        "OB-06_missing_correlation_ref_expected_fail.jsonl": fixture_ob06(),
        "OB-07_invalid_trace_shape_expected_fail.jsonl": fixture_ob07(),
        "OB-08_invalid_signal_type_expected_fail.jsonl": fixture_ob03(invalid_signal=True),
        "OB-09_unregistered_reason_code_expected_fail.jsonl": fixture_ob03(invalid_reason=True),
        "OB-10_negative_meter_quantity_expected_fail.jsonl": fixture_ob04(negative_meter=True)
    }

    for name, rows in fixtures.items():
        write_jsonl(OUT_DIR / name, rows)

    print(f"Generated {len(fixtures)} observability fixtures in {OUT_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
