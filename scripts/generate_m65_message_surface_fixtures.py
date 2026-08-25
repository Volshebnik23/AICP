#!/usr/bin/env python3
"""Generate M65 fixtures for extension families without a dedicated generator."""

from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference/python"))

from aicp_ref.hashing import message_hash_from_body, object_hash  # noqa: E402


def finalize(rows: list[dict]) -> list[dict]:
    previous: str | None = None
    result: list[dict] = []
    for row in rows:
        message = dict(row)
        message.pop("message_hash", None)
        if previous is not None:
            message["prev_msg_hash"] = previous
        message["message_hash"] = message_hash_from_body(message)
        previous = message["message_hash"]
        result.append(message)
    return result


def render(rows: list[dict]) -> str:
    return "\n".join(
        json.dumps(row, separators=(",", ":"), ensure_ascii=False) for row in rows
    ) + "\n"


def emit(relative: str, rows: list[dict], *, check: bool) -> None:
    path = ROOT / relative
    expected = render(rows)
    if check:
        if not path.is_file() or path.read_text(encoding="utf-8") != expected:
            raise SystemExit(f"stale generated fixture: {relative}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(expected, encoding="utf-8")
    print(f"wrote {relative} ({len(rows)} records)")


def facilitation() -> list[dict]:
    contract_ref = {"branch_id": "main", "base_version": "v1", "head_version": "v1"}
    return finalize(
        [
            {"session_id": "sFA2", "message_id": "m1", "timestamp": "2026-05-01T09:00:00Z", "sender": "agent:moderator", "message_type": "CONTRACT_PROPOSE", "contract_id": "cFA2", "contract_ref": contract_ref, "payload": {"contract": {"contract_id": "cFA2", "goal": "facilitation_registered_surface", "roles": ["moderator", "participant"]}}},
            {"session_id": "sFA2", "message_id": "m2", "timestamp": "2026-05-01T09:00:01Z", "sender": "agent:participant", "message_type": "CONTRACT_ACCEPT", "contract_id": "cFA2", "contract_ref": contract_ref, "payload": {"accepted": True}},
            {"session_id": "sFA2", "message_id": "m3", "timestamp": "2026-05-01T09:00:02Z", "sender": "agent:moderator", "message_type": "AGENDA_DECLARE", "contract_id": "cFA2", "contract_ref": contract_ref, "payload": {"agenda_id": "agenda-fa2", "title": "Registered surface review"}},
            {"session_id": "sFA2", "message_id": "m4", "timestamp": "2026-05-01T09:00:03Z", "sender": "agent:moderator", "message_type": "AGENDA_UPDATE", "contract_id": "cFA2", "contract_ref": contract_ref, "payload": {"agenda_id": "agenda-fa2", "note": "Proceed to participant review"}},
            {"session_id": "sFA2", "message_id": "m5", "timestamp": "2026-05-01T09:00:04Z", "sender": "agent:participant", "message_type": "TURN_REQUEST", "contract_id": "cFA2", "contract_ref": contract_ref, "payload": {"turn_id": "turn-fa2", "topic": "surface review"}},
            {"session_id": "sFA2", "message_id": "m6", "timestamp": "2026-05-01T09:00:05Z", "sender": "agent:moderator", "message_type": "TURN_GRANT", "contract_id": "cFA2", "contract_ref": contract_ref, "payload": {"turn_id": "turn-fa2", "grantee": "agent:participant"}},
            {"session_id": "sFA2", "message_id": "m7", "timestamp": "2026-05-01T09:00:06Z", "sender": "agent:moderator", "message_type": "TURN_REVOKE", "contract_id": "cFA2", "contract_ref": contract_ref, "payload": {"turn_id": "turn-fa2", "reason": "review complete"}},
        ]
    )


def participant_leave() -> list[dict]:
    contract_ref = {"branch_id": "main", "base_version": "v1", "head_version": "v1"}
    return finalize(
        [
            {"session_id": "sPA4", "message_id": "m1", "timestamp": "2026-01-11T00:00:00Z", "sender": "agent:A", "message_type": "CONTRACT_PROPOSE", "contract_id": "cPA4", "contract_ref": contract_ref, "payload": {"contract": {"contract_id": "cPA4", "goal": "participants_leave", "roles": ["initiator", "participant"], "ext": {"participants": {"model": "shared_contract", "acceptors": ["agent:A"], "roles_catalog": ["role:writer"]}}}}},
            {"session_id": "sPA4", "message_id": "m2", "timestamp": "2026-01-11T00:00:02Z", "sender": "agent:B", "message_type": "CONTRACT_ACCEPT", "contract_id": "cPA4", "contract_ref": contract_ref, "payload": {"accepted": True}},
            {"session_id": "sPA4", "message_id": "m3", "timestamp": "2026-01-11T00:00:04Z", "sender": "user:U", "message_type": "PARTICIPANT_JOIN", "contract_id": "cPA4", "contract_ref": contract_ref, "payload": {"participant_id": "user:U", "requested_roles": ["role:writer"]}},
            {"session_id": "sPA4", "message_id": "m4", "timestamp": "2026-01-11T00:00:06Z", "sender": "agent:A", "message_type": "PARTICIPANT_ACCEPT", "contract_id": "cPA4", "contract_ref": contract_ref, "payload": {"participant_id": "user:U", "granted_roles": ["role:writer"]}},
            {"session_id": "sPA4", "message_id": "m5", "timestamp": "2026-01-11T00:00:08Z", "sender": "user:U", "message_type": "PARTICIPANT_LEAVE", "contract_id": "cPA4", "contract_ref": contract_ref, "payload": {"participant_id": "user:U", "reason": "session_complete", "mode": "voluntary"}},
        ]
    )


def policy_attestation() -> list[dict]:
    context = {
        "context_id": "ctx-pe5",
        "contract_head_version": "v1",
        "subject": "agent:A",
        "action": "content.publish",
        "resource": "content:5",
    }
    context["context_hash"] = object_hash("evaluation_context", context)
    prefix = finalize(
        [
            {"session_id": "sPE5", "message_id": "m1", "timestamp": "2026-01-09T00:00:00Z", "sender": "agent:A", "message_type": "POLICY_EVAL_REQUEST", "contract_id": "cPE5", "payload": {"eval_id": "pe5", "policy_bundle_ref": {"policy_bundle_id": "bundle-5", "version": "1", "language_id": "rego.v1", "content_hash": "sha256:bundle5"}, "policy_binding_ref": {"binding_id": "opa.input.v1", "input_schema_version": "1"}, "evaluation_context": context, "requested_action_id": "act-pe5"}},
            {"session_id": "sPE5", "message_id": "m2", "timestamp": "2026-01-09T00:00:02Z", "sender": "policy:P", "message_type": "POLICY_EVAL_RESULT", "contract_id": "cPE5", "payload": {"eval_id": "pe5", "policy_decision": {"decision": "ALLOW", "reason_codes": [], "evaluated_at": "2026-01-09T00:00:02Z", "context_hash": context["context_hash"]}}},
            {"session_id": "sPE5", "message_id": "m3", "timestamp": "2026-01-09T00:00:04Z", "sender": "agent:A", "message_type": "ATTEST_ACTION", "contract_id": "cPE5", "payload": {"action_id": "act-pe5", "action_type": "content.publish", "consent_ref": "policy:pe5"}},
        ]
    )
    return finalize(
        [
            {key: value for key, value in message.items() if key not in {"message_hash", "prev_msg_hash"}}
            for message in prefix
        ]
        + [
            {"session_id": "sPE5", "message_id": "m4", "timestamp": "2026-01-09T00:00:06Z", "sender": "policy:P", "message_type": "POLICY_DECISION_ATTEST", "contract_id": "cPE5", "payload": {"eval_id": "pe5", "policy_decision_ref": prefix[1]["message_hash"], "related_action_id": "act-pe5"}},
        ]
    )


def main() -> int:
    check = "--check" in sys.argv
    emit(
        "fixtures/extensions/facilitation/FA-02_agenda_and_turn_revoke_pass.jsonl",
        facilitation(),
        check=check,
    )
    emit(
        "fixtures/extensions/participants/PA-04_participant_leave_pass.jsonl",
        participant_leave(),
        check=check,
    )
    emit(
        "fixtures/extensions/policy_eval/PE-05_policy_decision_attest_presence.jsonl",
        policy_attestation(),
        check=check,
    )
    if check:
        print("[OK] M65 message-surface fixtures are deterministic")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
