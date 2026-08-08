from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REF_PY = ROOT / "reference" / "python"
if str(REF_PY) not in sys.path:
    sys.path.insert(0, str(REF_PY))

from aicp_ref.hashing import message_hash_from_body, object_hash  # noqa: E402


FLOW_TEMPLATES: dict[str, tuple[str, ...]] = {
    "core_contract_action": ("fixtures/golden_transcripts/GT-01_happy_path_signed.jsonl",),
    "core_conflict_choose": ("fixtures/golden_transcripts/GT-02_conflict_choose_signed.jsonl",),
    "core_consent_grant": ("fixtures/golden_transcripts/GT-04_consent_required_and_grant.jsonl",),
    "core_consent_revoke": ("fixtures/golden_transcripts/GT-05_consent_revoke.jsonl",),
    "core_resync": ("fixtures/golden_transcripts/GT-06_unknown_base_and_resync.jsonl",),
    "core_error": ("fixtures/golden_transcripts/GT-08_error_minimal.jsonl",),
    "profile_accept_contract": ("fixtures/extensions/capneg/CN-07_negotiation_bound_into_contract_pass.jsonl",),
    "profile_reject": ("fixtures/extensions/capneg/CN-02_reject_incompatible_profile.jsonl",),
    "policy_allow_delivery": (
        "fixtures/extensions/policy_eval/PE-01_basic_allow.jsonl",
        "fixtures/extensions/enforcement/EF-01_allow_and_deliver.jsonl",
    ),
    "policy_deny_block": (
        "fixtures/extensions/policy_eval/PE-01_basic_allow.jsonl",
        "fixtures/extensions/enforcement/EF-02_deny_but_delivered_expected_fail.jsonl",
    ),
    "resume_in_sync": ("fixtures/extensions/resume/RS-01_ok_in_sync.jsonl",),
    "resume_needs_resync": (
        "fixtures/extensions/resume/RS-02_needs_resync.jsonl",
        "fixtures/extensions/object_resync/OR-02_state_sync.jsonl",
    ),
    "object_retrieval": ("fixtures/extensions/object_resync/OR-01_object_request_response.jsonl",),
    "identity_announce_use": ("fixtures/extensions/identity_lc/IL-01_announce_and_verify_session_local_key.jsonl",),
    "identity_rotate_use": ("fixtures/extensions/identity_lc/IL-02_rotation_cross_sign_and_use_new_key.jsonl",),
    "identity_revoke_clean": ("fixtures/extensions/identity_lc/IL-03_revoke_then_use_revoked_key_expected_fail.jsonl",),
    "binding_issue_use": ("fixtures/extensions/delegated_identity/DI-01_issue_and_use_binding_pass.jsonl",),
    "binding_revoke_clean": ("fixtures/extensions/delegated_identity/DI-02_revoke_then_use_expected_fail.jsonl",),
}


def scenario_template_paths() -> list[str]:
    return sorted({path for paths in FLOW_TEMPLATES.values() for path in paths})


def _load_jsonl(relative: str) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in (ROOT / relative).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _body(message: dict[str, Any]) -> dict[str, Any]:
    value = dict(message)
    value.pop("message_hash", None)
    value.pop("signatures", None)
    return value


def _rechain(messages: list[dict[str, Any]], *, unsigned: bool = True) -> None:
    previous: str | None = None
    for message in messages:
        if unsigned:
            message.pop("signatures", None)
        if previous is None:
            message.pop("prev_msg_hash", None)
        else:
            message["prev_msg_hash"] = previous
        message["message_hash"] = message_hash_from_body(_body(message))
        previous = str(message["message_hash"])


def _retarget_profile(
    messages: list[dict[str, Any]],
    profile_id: str,
    profile_version: str,
) -> list[dict[str, Any]]:
    result = copy.deepcopy(messages)
    exact = {"profile_id": profile_id, "profile_version": profile_version}
    proposed: dict[str, Any] | None = None
    proposed_hash: str | None = None
    for message in result:
        payload = message.get("payload") if isinstance(message.get("payload"), dict) else {}
        if message.get("message_type") == "CAPABILITIES_DECLARE":
            for field in ("supported_aicp_profiles", "required_aicp_profiles"):
                if field in payload:
                    payload[field] = [dict(exact)]
        elif message.get("message_type") == "CAPABILITIES_PROPOSE":
            proposed = payload.get("negotiation_result")
            selected = proposed.get("selected") if isinstance(proposed, dict) else None
            if isinstance(selected, dict):
                selected["aicp_profile"] = dict(exact)
                proposed_hash = object_hash("capneg.negotiation_result", proposed)
        elif message.get("message_type") == "CAPABILITIES_ACCEPT" and proposed_hash:
            payload["negotiation_result_hash"] = proposed_hash
            if isinstance(payload.get("negotiation_result"), dict):
                payload["negotiation_result"] = copy.deepcopy(proposed)
        elif message.get("message_type") == "CONTRACT_PROPOSE" and proposed_hash:
            contract = payload.get("contract") if isinstance(payload.get("contract"), dict) else {}
            capneg = (contract.get("ext") or {}).get("capneg")
            if isinstance(capneg, dict):
                capneg["negotiation_result_hash"] = proposed_hash
                if "selected" in capneg and isinstance(proposed, dict):
                    capneg["selected"] = copy.deepcopy(proposed.get("selected"))
    _rechain(result)
    return result


def _policy_enforcement_flow(*, allow: bool) -> list[dict[str, Any]]:
    policy = copy.deepcopy(_load_jsonl(FLOW_TEMPLATES["policy_allow_delivery"][0]))
    enforcement_path = (
        FLOW_TEMPLATES["policy_allow_delivery"][1]
        if allow
        else FLOW_TEMPLATES["policy_deny_block"][1]
    )
    enforcement = copy.deepcopy(_load_jsonl(enforcement_path))
    if not allow:
        enforcement = [
            message
            for message in enforcement
            if message.get("message_type") != "CONTENT_DELIVER"
        ]
    session_id = str(enforcement[0]["session_id"])
    contract_id = str(enforcement[0]["contract_id"])
    for index, message in enumerate(policy, start=1):
        message["session_id"] = session_id
        message["contract_id"] = contract_id
        message["message_id"] = f"policy-{index}"
    decision = (policy[-1].get("payload") or {}).get("policy_decision") or {}
    decision["decision"] = "ALLOW" if allow else "DENY"
    if not allow:
        decision["reason_codes"] = ["PII_BLOCKED"]
    messages = [*enforcement[:2], *policy, *enforcement[2:]]
    _rechain(messages)
    content = next(
        message for message in messages if message.get("message_type") == "CONTENT_MESSAGE"
    )
    verdict = next(
        message
        for message in messages
        if message.get("message_type") == "ENFORCEMENT_VERDICT"
    )
    verdict_payload = verdict.get("payload") or {}
    verdict_payload["decision"] = "ALLOW" if allow else "DENY"
    verdict_payload["target_message_hash"] = content["message_hash"]
    _rechain(messages)
    if allow:
        delivery = next(
            message
            for message in messages
            if message.get("message_type") == "CONTENT_DELIVER"
        )
        delivery_payload = delivery.get("payload") or {}
        delivery_payload["original_message_hash"] = content["message_hash"]
        embedded = delivery_payload.get("original_message")
        if isinstance(embedded, dict):
            embedded["message_hash"] = content["message_hash"]
            embedded["message_type"] = content["message_type"]
            embedded["payload"] = copy.deepcopy(content.get("payload"))
        delivery_payload["verdict_message_id"] = verdict["message_id"]
        _rechain(messages)
    return messages


def _resume_with_state_sync() -> list[dict[str, Any]]:
    resume = copy.deepcopy(_load_jsonl(FLOW_TEMPLATES["resume_needs_resync"][0]))
    sync = copy.deepcopy(_load_jsonl(FLOW_TEMPLATES["resume_needs_resync"][1]))
    session_id = str(resume[0]["session_id"])
    contract_id = str(resume[0]["contract_id"])
    for index, message in enumerate(sync, start=1):
        message["session_id"] = session_id
        message["contract_id"] = contract_id
        message["message_id"] = f"sync-{index}"
    messages = [*resume, *sync]
    _rechain(messages)
    return messages


def build_scenario_transcript(scenario: dict[str, Any]) -> list[dict[str, Any]]:
    flow_id = scenario.get("flow_id")
    if not isinstance(flow_id, str) or flow_id not in FLOW_TEMPLATES:
        raise ValueError("unknown neutral producer flow")
    target = scenario.get("target") if isinstance(scenario.get("target"), dict) else {}
    profile_id = target.get("target_id")
    profile_version = target.get("target_version")
    if not isinstance(profile_id, str) or not isinstance(profile_version, str):
        raise ValueError("producer scenario exact target identity is missing")

    if flow_id == "policy_allow_delivery":
        messages = _policy_enforcement_flow(allow=True)
    elif flow_id == "policy_deny_block":
        messages = _policy_enforcement_flow(allow=False)
    elif flow_id == "resume_needs_resync":
        messages = _resume_with_state_sync()
    else:
        messages = copy.deepcopy(_load_jsonl(FLOW_TEMPLATES[flow_id][0]))
        if flow_id == "profile_accept_contract":
            messages = _retarget_profile(messages, profile_id, profile_version)
        elif flow_id in {"identity_revoke_clean", "binding_revoke_clean"}:
            messages = messages[:-1]

    expected_session = scenario.get("session_id")
    expected_contract = scenario.get("contract_id")
    if any(message.get("session_id") != expected_session for message in messages):
        raise ValueError("scenario session facts do not match generated transcript")
    if any(message.get("contract_id") != expected_contract for message in messages):
        raise ValueError("scenario contract facts do not match generated transcript")
    participants = {
        str(message.get("sender"))
        for message in messages
        if isinstance(message.get("sender"), str)
    }
    if not participants.issubset(set(scenario.get("participant_ids", []))):
        raise ValueError("scenario participants do not cover generated senders")
    return messages


def generated_transcript_result(scenario: dict[str, Any]) -> dict[str, Any]:
    return {
        "artifact_kind": "transcript",
        "scenario_id": str(scenario["scenario_id"]),
        "target": copy.deepcopy(scenario["target"]),
        "messages": build_scenario_transcript(scenario),
    }
