#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference/python"))

from aicp_ref.hashing import message_hash_from_body  # noqa: E402

OUT_DIR = ROOT / "fixtures/extensions/human_approval"
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


def _base_contract(case_id: str) -> list[dict]:
    session_id = f"sha-{case_id}"
    contract_id = f"cha-{case_id}"
    return [
        {
            "session_id": session_id,
            "message_id": "m1",
            "timestamp": "2026-03-13T00:00:00Z",
            "sender": "agent:caller",
            "message_type": "CONTRACT_PROPOSE",
            "contract_id": contract_id,
            "contract_ref": CREF,
            "payload": {
                "contract": {
                    "contract_id": contract_id,
                    "goal": "human_approval_controlled_action",
                    "roles": ["caller", "approver"],
                    "ext": {
                        "human_approval": {
                            "default_required": True,
                            "approval_policy_ref": "policy:approval:default:v1"
                        }
                    }
                }
            }
        },
        {
            "session_id": session_id,
            "message_id": "m2",
            "timestamp": "2026-03-13T00:00:01Z",
            "sender": "agent:approver",
            "message_type": "CONTRACT_ACCEPT",
            "contract_id": contract_id,
            "contract_ref": CREF,
            "payload": {"accepted": True}
        }
    ]


def _challenge_message(case_id: str, target_binding: dict, expires_at: str = "2026-03-13T00:10:00Z") -> dict:
    return {
        "session_id": f"sha-{case_id}",
        "message_id": "m3",
        "timestamp": "2026-03-13T00:01:00Z",
        "sender": "agent:caller",
        "message_type": "APPROVAL_CHALLENGE",
        "contract_id": f"cha-{case_id}",
        "payload": {
            "target_binding": target_binding,
            "approver_id": "agent:approver",
            "scope": {
                "action": "tool.execute.payment.capture",
                "constraints": ["amount<=100", "currency=USD"]
            },
            "expires_at": expires_at,
            "revocation_handle": "approval:rev:001"
        }
    }


def _grant_message(case_id: str, challenge_hash: str, target_binding: dict, *, expires_at: str = "2026-03-13T00:10:00Z", sender: str = "agent:approver", approver_id: str = "agent:approver", ts: str = "2026-03-13T00:02:00Z") -> dict:
    return {
        "session_id": f"sha-{case_id}",
        "message_id": "m4",
        "timestamp": ts,
        "sender": sender,
        "message_type": "APPROVAL_GRANT",
        "contract_id": f"cha-{case_id}",
        "payload": {
            "challenge_message_hash": challenge_hash,
            "approver_id": approver_id,
            "target_binding": target_binding,
            "scope": {
                "action": "tool.execute.payment.capture",
                "constraints": ["amount<=100", "currency=USD"]
            },
            "expires_at": expires_at,
            "grant_ref": "approval:grant:001"
        }
    }


def _deny_message(case_id: str, challenge_hash: str, target_binding: dict) -> dict:
    return {
        "session_id": f"sha-{case_id}",
        "message_id": "m4",
        "timestamp": "2026-03-13T00:02:00Z",
        "sender": "agent:approver",
        "message_type": "APPROVAL_DENY",
        "contract_id": f"cha-{case_id}",
        "payload": {
            "challenge_message_hash": challenge_hash,
            "approver_id": "agent:approver",
            "target_binding": target_binding,
            "scope": {
                "action": "tool.execute.payment.capture",
                "constraints": ["amount<=100", "currency=USD"]
            },
            "expires_at": "2026-03-13T00:10:00Z",
            "deny_reason": "manual policy rejection"
        }
    }


def build_approval_case(case_id: str, *, missing_target: bool = False, expired: bool = False, wrong_signer: bool = False, target_mismatch: bool = False) -> list[dict]:
    target = {"tool_call_id": "tc-001"}
    rows = _base_contract(case_id)
    challenge = _challenge_message(case_id, target, expires_at="2026-03-13T00:01:30Z" if expired else "2026-03-13T00:10:00Z")
    if missing_target:
        challenge["payload"].pop("target_binding", None)
    rows.append(challenge)

    baseline = finalize(rows)
    challenge_hash = baseline[-1]["message_hash"]

    grant_target = {"tool_call_hash": "sha256:other-target"} if target_mismatch else target
    grant = _grant_message(
        case_id,
        challenge_hash,
        grant_target,
        expires_at=challenge["payload"].get("expires_at", "2026-03-13T00:10:00Z"),
        sender="agent:not-approver" if wrong_signer else "agent:approver",
        approver_id="agent:not-approver" if wrong_signer else "agent:approver",
        ts="2026-03-13T00:02:00Z"
    )
    rows.append(grant)

    if not missing_target:
        rows.append(
            {
                "session_id": f"sha-{case_id}",
                "message_id": "m5",
                "timestamp": "2026-03-13T00:03:00Z" if not expired else "2026-03-13T00:02:30Z",
                "sender": "agent:caller",
                "message_type": "TOOL_CALL_REQUEST",
                "contract_id": f"cha-{case_id}",
                "payload": {
                    "tool_call_id": "tc-001",
                    "tool_id": "tools.payment.capture",
                    "arguments": {"amount": 99, "currency": "USD"},
                    "ext": {
                        "human_approval": {
                            "required": True,
                            "tool_call_id": "tc-001"
                        }
                    }
                }
            }
        )

    return finalize(rows)


def build_deny_case(case_id: str) -> list[dict]:
    target = {"tool_call_id": "tc-002"}
    rows = _base_contract(case_id)
    rows.append(_challenge_message(case_id, target))
    baseline = finalize(rows)
    rows.append(_deny_message(case_id, baseline[-1]["message_hash"], target))
    return finalize(rows)


def build_intervention_case(case_id: str, *, missing_handle: bool = False) -> list[dict]:
    rows = _base_contract(case_id)
    required_payload = {
        "reason_code": "step_up_auth",
        "provider_hint": "oidc-step-up",
        "expires_at": "2026-03-13T00:20:00Z",
        "intervention_handle": "intervention:3ds:txn-001"
    }
    if missing_handle:
        required_payload.pop("intervention_handle", None)

    rows.append(
        {
            "session_id": f"sha-{case_id}",
            "message_id": "m3",
            "timestamp": "2026-03-13T00:05:00Z",
            "sender": "agent:mediator",
            "message_type": "INTERVENTION_REQUIRED",
            "contract_id": f"cha-{case_id}",
            "payload": required_payload
        }
    )

    baseline = finalize(rows)
    rows.append(
        {
            "session_id": f"sha-{case_id}",
            "message_id": "m4",
            "timestamp": "2026-03-13T00:06:00Z",
            "sender": "agent:caller",
            "message_type": "INTERVENTION_COMPLETE",
            "contract_id": f"cha-{case_id}",
            "payload": {
                "required_message_hash": baseline[-1]["message_hash"],
                "intervention_handle": "intervention:3ds:txn-001" if not missing_handle else "",
                "completion_ref": "objhash:sha256:stepup-proof-001"
            }
        }
    )
    return finalize(rows)


def main() -> int:
    fixtures = {
        "HA-01_basic_approval_grant_pass.jsonl": build_approval_case("HA01"),
        "HA-02_approval_deny_pass.jsonl": build_deny_case("HA02"),
        "HA-03_intervention_required_complete_pass.jsonl": build_intervention_case("HA03"),
        "HA-04_missing_target_binding_expected_fail.jsonl": build_approval_case("HA04", missing_target=True),
        "HA-05_expired_approval_expected_fail.jsonl": build_approval_case("HA05", expired=True),
        "HA-06_wrong_signer_expected_fail.jsonl": build_approval_case("HA06", wrong_signer=True),
        "HA-07_approval_reuse_across_targets_expected_fail.jsonl": build_approval_case("HA07", target_mismatch=True),
        "HA-08_missing_intervention_handle_expected_fail.jsonl": build_intervention_case("HA08", missing_handle=True)
    }

    for name, rows in fixtures.items():
        write_jsonl(OUT_DIR / name, rows)

    print(f"Generated {len(fixtures)} human approval fixtures in {OUT_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
