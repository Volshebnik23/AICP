from __future__ import annotations

from collections import defaultdict
from typing import Any

from aicp_ref.hashing import message_hash_from_body
from aicp_ref.validate import (
    message_body_without_hash_and_signatures,
    validate_message_signatures,
)

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover
    Draft202012Validator = None


CAPNEG_TYPES = {
    "CAPABILITIES_DECLARE",
    "CAPABILITIES_PROPOSE",
    "CAPABILITIES_ACCEPT",
    "CAPABILITIES_REJECT",
}
AUTHENTICATED_PROFILE = ("AICP-AUTHENTICATED-BASE", "0.1")
_VALIDATOR_CACHE: dict[tuple[int, str | None], Any] = {}


def validator(schema: dict[str, Any], definition: str | None = None) -> Any | None:
    if Draft202012Validator is None:
        return None
    cache_key = (id(schema), definition)
    if cache_key in _VALIDATOR_CACHE:
        return _VALIDATOR_CACHE[cache_key]
    if definition is None:
        Draft202012Validator.check_schema(schema)
        result = Draft202012Validator(schema)
        _VALIDATOR_CACHE[cache_key] = result
        return result
    wrapper = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$ref": f"#/$defs/{definition}",
        "$defs": schema["$defs"],
    }
    Draft202012Validator.check_schema(wrapper)
    result = Draft202012Validator(wrapper)
    _VALIDATOR_CACHE[cache_key] = result
    return result


def issue(
    code: str,
    detail: str,
    *,
    message_index: int | None,
    message_id: Any,
) -> dict[str, Any]:
    return {
        "code": code,
        "message_index": message_index,
        "message_id": message_id if isinstance(message_id, str) else None,
        "detail": detail,
    }


def route_capneg_schema_error(message: dict[str, Any]) -> str:
    payload = message.get("payload", {})
    selected = payload.get("negotiation_result", {}).get("selected", {})
    profiles = selected.get("profile_composition", {}).get("profiles")
    if isinstance(profiles, list) and not profiles:
        return "PROFILE_COMPOSITION_EMPTY"
    if isinstance(profiles, list):
        keys = [
            (profile.get("profile_id"), profile.get("profile_version"))
            for profile in profiles
            if isinstance(profile, dict)
        ]
        if len(keys) != len(set(keys)):
            return "PROFILE_DUPLICATE"
    bindings = payload.get("negotiation_result", {}).get("declaration_bindings")
    participants = payload.get("negotiation_result", {}).get("participants")
    if (
        isinstance(bindings, list)
        and isinstance(participants, list)
        and len(bindings) < len(participants)
    ):
        return "MISSING_DECLARATION_BINDING"
    return "CAPNEG_PAYLOAD_SCHEMA_INVALID"


def _selected_profiles_for_decision(
    messages: list[dict[str, Any]], index: int
) -> set[tuple[str, str]]:
    decision = messages[index].get("payload", {})
    for proposal in reversed(messages[:index]):
        payload = proposal.get("payload", {})
        if proposal.get("message_type") != "CAPABILITIES_PROPOSE":
            continue
        if (
            payload.get("negotiation_result", {}).get("negotiation_id")
            == decision.get("negotiation_id")
            and payload.get("proposal_revision")
            == decision.get("proposal_revision")
            and proposal.get("message_id") == decision.get("proposal_message_id")
            and proposal.get("message_hash") == decision.get("proposal_message_hash")
            and payload.get("negotiation_result_hash")
            == decision.get("negotiation_result_hash")
        ):
            profiles = (
                payload.get("negotiation_result", {})
                .get("selected", {})
                .get("profile_composition", {})
                .get("profiles", [])
            )
            return {
                (
                    str(profile.get("profile_id")),
                    str(profile.get("profile_version")),
                )
                for profile in profiles
                if isinstance(profile, dict)
            }
    return set()


def _proposal_for_decision(
    messages: list[dict[str, Any]], index: int
) -> dict[str, Any] | None:
    decision = messages[index].get("payload", {})
    for proposal in reversed(messages[:index]):
        payload = proposal.get("payload", {})
        result = payload.get("negotiation_result", {})
        if (
            proposal.get("message_type") == "CAPABILITIES_PROPOSE"
            and result.get("negotiation_id") == decision.get("negotiation_id")
            and payload.get("proposal_revision")
            == decision.get("proposal_revision")
            and proposal.get("message_id") == decision.get("proposal_message_id")
            and proposal.get("message_hash") == decision.get("proposal_message_hash")
            and payload.get("negotiation_result_hash")
            == decision.get("negotiation_result_hash")
        ):
            return proposal
    return None


def case_requires_crypto(messages: list[dict[str, Any]]) -> bool:
    if any(message.get("signatures") is not None for message in messages):
        return True
    for index, message in enumerate(messages):
        if message.get("message_type") != "CAPABILITIES_ACCEPT":
            continue
        if AUTHENTICATED_PROFILE in _selected_profiles_for_decision(messages, index):
            return True
    return False


def validate_messages(
    messages: list[dict[str, Any]],
    *,
    message_schema: dict[str, Any],
    capneg_schema: dict[str, Any],
    projection_schema: dict[str, Any],
    core_payload_schema: dict[str, Any],
    core_contract_schema: dict[str, Any],
    registered_messages: set[str],
    key_map: dict[str, Any],
    jsonschema_available: bool,
    crypto_available: bool,
) -> tuple[dict[int, list[dict[str, Any]]], list[dict[str, Any]]]:
    """Run the mandatory message-local barrier before semantic reduction."""

    invalid: dict[int, list[dict[str, Any]]] = defaultdict(list)
    transcript_issues: list[dict[str, Any]] = []
    message_validator = validator(message_schema) if jsonschema_available else None
    capneg_validators = (
        {
            message_type: validator(capneg_schema, message_type)
            for message_type in CAPNEG_TYPES
        }
        if jsonschema_available
        else {}
    )
    projection_validator = (
        validator(projection_schema, "STATE_SYNC_RESPONSE")
        if jsonschema_available
        else None
    )
    core_payload_validator = (
        validator(core_payload_schema, "CONTRACT_PROPOSE")
        if jsonschema_available
        else None
    )
    core_contract_validator = (
        validator(core_contract_schema) if jsonschema_available else None
    )

    first_session = messages[0].get("session_id") if messages else None
    first_contract = messages[0].get("contract_id") if messages else None
    seen_message_ids: set[str] = set()

    def add(index: int, code: str, detail: str) -> None:
        invalid[index].append(
            issue(
                code,
                detail,
                message_index=index,
                message_id=messages[index].get("message_id"),
            )
        )

    for index, message in enumerate(messages):
        raw_message_id = message.get("message_id")
        message_type = message.get("message_type")

        if not isinstance(raw_message_id, str) or not raw_message_id:
            add(index, "CAPNEG_MESSAGE_ID_INVALID", "message_id must be a non-empty string")
        elif raw_message_id in seen_message_ids:
            add(index, "CAPNEG_MESSAGE_ID_DUPLICATE", "message_id must be unique in the transcript")
        else:
            seen_message_ids.add(raw_message_id)

        if message.get("session_id") != first_session:
            add(
                index,
                "CAPNEG_TRANSCRIPT_SESSION_MISMATCH",
                "every message must use the transcript session_id",
            )
        if message.get("contract_id") != first_contract:
            add(
                index,
                "CAPNEG_TRANSCRIPT_CONTRACT_MISMATCH",
                "every message must use the transcript contract_id",
            )
        if message_type in {"CAPABILITIES_ACCEPT", "CAPABILITIES_REJECT"}:
            proposal = _proposal_for_decision(messages, index)
            if proposal is not None:
                result = proposal.get("payload", {}).get("negotiation_result", {})
                if message.get("session_id") != result.get("session_id"):
                    add(
                        index,
                        "DECISION_SESSION_MISMATCH",
                        "decision envelope session_id must equal the negotiated session_id",
                    )
                if message.get("contract_id") != result.get("contract_id"):
                    add(
                        index,
                        "DECISION_CONTRACT_MISMATCH",
                        "decision envelope contract_id must equal the negotiated contract_id",
                    )
        if message_type not in registered_messages:
            add(
                index,
                "CAPNEG_MESSAGE_TYPE_UNREGISTERED",
                "message_type is not registered",
            )

        if message_validator is not None and list(
            message_validator.iter_errors(message)
        ):
            add(
                index,
                "CAPNEG_ENVELOPE_SCHEMA_INVALID",
                "message does not satisfy the Core v0.1 envelope schema",
            )
        if (
            message_type in CAPNEG_TYPES
            and jsonschema_available
            and list(
                capneg_validators[message_type].iter_errors(message.get("payload"))
            )
        ):
            add(
                index,
                route_capneg_schema_error(message),
                "payload does not satisfy the selected CAPNEG v0.2 payload schema",
            )
        if (
            message_type == "STATE_SYNC_RESPONSE"
            and isinstance(message.get("payload", {}).get("session_state"), dict)
            and message["payload"]["session_state"].get("projection_version")
            == "aicp.session_state_projection.v2"
            and projection_validator is not None
            and list(projection_validator.iter_errors(message.get("payload")))
        ):
            add(
                index,
                "PROJECTION_PAYLOAD_SCHEMA_INVALID",
                "payload does not satisfy the projection v2 payload schema",
            )
        if message_type == "CONTRACT_PROPOSE":
            payload = message.get("payload")
            contract = payload.get("contract") if isinstance(payload, dict) else None
            if core_payload_validator is not None:
                if list(core_payload_validator.iter_errors(payload)):
                    add(
                        index,
                        "CORE_CONTRACT_PAYLOAD_SCHEMA_INVALID",
                        "payload does not satisfy the frozen Core v0.1 CONTRACT_PROPOSE schema",
                    )
                if list(core_contract_validator.iter_errors(contract)):
                    add(
                        index,
                        "CORE_CONTRACT_SCHEMA_INVALID",
                        "contract does not satisfy the frozen Core v0.1 contract schema",
                    )
            if (
                isinstance(contract, dict)
                and contract.get("contract_id") != message.get("contract_id")
            ):
                add(
                    index,
                    "CONTRACT_ID_MISMATCH",
                    "payload.contract.contract_id must equal envelope contract_id",
                )

        try:
            body = message_body_without_hash_and_signatures(message)
            computed_hash = message_hash_from_body(body)
        except Exception as exc:
            add(index, "CAPNEG_MESSAGE_HASH_INVALID", f"message hash recomputation failed: {exc}")
        else:
            if computed_hash != message.get("message_hash"):
                add(
                    index,
                    "CAPNEG_MESSAGE_HASH_INVALID",
                    "message_hash does not match the canonical message body",
                )
        if index == 0:
            if "prev_msg_hash" in message:
                add(
                    index,
                    "CAPNEG_CHAIN_INVALID",
                    "the first message must not contain prev_msg_hash",
                )
        elif message.get("prev_msg_hash") != messages[index - 1].get("message_hash"):
            add(
                index,
                "CAPNEG_CHAIN_INVALID",
                "prev_msg_hash must equal the immediately prior message_hash",
            )

        require_sender = (
            message_type == "CAPABILITIES_ACCEPT"
            and AUTHENTICATED_PROFILE
            in _selected_profiles_for_decision(messages, index)
        )
        signature_issues = validate_message_signatures(
            message,
            key_map,
            verify_crypto=crypto_available,
            require_signatures=require_sender,
            require_sender_signature=require_sender,
        )
        for signature_issue in signature_issues:
            shared_code = signature_issue["code"]
            if shared_code in {"signatures_required", "sender_signature_required"}:
                code = "AUTHENTICATED_ACCEPTANCE_SIGNATURE_REQUIRED"
            elif shared_code == "crypto_unavailable":
                code = "CRYPTO_VERIFICATION_UNAVAILABLE"
            elif message_type == "CAPABILITIES_ACCEPT":
                code = "ACCEPTANCE_SIGNATURE_INVALID"
            else:
                code = "CAPNEG_SIGNATURE_INVALID"
            add(index, code, signature_issue["message"])

    return dict(invalid), transcript_issues


def normalize_observations(
    issues: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, int | None, str | None], int] = defaultdict(int)
    for item in issues:
        key = (
            str(item.get("code")),
            item.get("message_index"),
            item.get("message_id"),
        )
        grouped[key] += 1
    return sorted(
        (
            {
                "code": code,
                "message_index": message_index,
                "message_id": message_id,
                "exact_count": count,
            }
            for (code, message_index, message_id), count in grouped.items()
        ),
        key=lambda item: (
            item["message_index"] is None,
            -1 if item["message_index"] is None else item["message_index"],
            item["code"],
            item["message_id"] or "",
        ),
    )
