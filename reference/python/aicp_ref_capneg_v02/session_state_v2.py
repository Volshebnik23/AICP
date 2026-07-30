from __future__ import annotations

from typing import Any

from aicp_ref.hashing import object_hash

from .profile_composition import (
    COMPOSITION_VERSION,
    canonical_profile_ref_key,
    resolve_profile_composition,
)


PROJECTION_VERSION = "aicp.session_state_projection.v2"
PROJECTION_OBJECT_TYPE = "session_state_projection"


def project_session_state_v2(context: dict[str, Any]) -> tuple[dict[str, Any], str]:
    projection: dict[str, Any] = {
        "projection_version": PROJECTION_VERSION,
        "session_id": context["session_id"],
        "contract_id": context["contract_id"],
        "as_of_message_hash": context["as_of_message_hash"],
        "session_status": context.get("session_status", "UNKNOWN"),
        "selected_aicp_profiles": context["selected_aicp_profiles"],
        "profile_composition_hash": context["profile_composition_hash"],
        "accepted_negotiation_result_hash": context[
            "accepted_negotiation_result_hash"
        ],
    }
    for field in (
        "active_contract_ref",
        "active_extensions",
        "participant_refs",
        "policy_refs",
        "unresolved_conflict_refs",
        "authority_refs",
        "evidence_refs",
        "extension_data",
    ):
        if field in context:
            projection[field] = context[field]
    return projection, object_hash(PROJECTION_OBJECT_TYPE, projection)


def validate_session_state_projection_v2(
    message: dict[str, Any],
    transcript: list[dict[str, Any]],
    message_index: int,
    *,
    registered_extensions: set[str],
    rules: dict[str, Any] | None = None,
    registered_reason_codes: set[str] | None = None,
    key_map: dict[str, Any] | None = None,
    crypto_available: bool = True,
    invalid_messages: dict[int, list[dict[str, Any]]] | None = None,
) -> list[dict[str, Any]]:
    payload = message.get("payload", {})
    projection = payload.get("session_state")
    if (
        not isinstance(projection, dict)
        or projection.get("projection_version") != PROJECTION_VERSION
    ):
        return []

    issues: list[dict[str, Any]] = []

    def issue(code: str, detail: str) -> None:
        issues.append(
            {
                "code": code,
                "message_index": message_index,
                "message_id": (
                    message.get("message_id")
                    if isinstance(message.get("message_id"), str)
                    else None
                ),
                "detail": detail,
            }
        )

    if projection.get("session_id") != message.get("session_id"):
        issue("PROJECTION_SESSION_MISMATCH", "projection session_id must equal envelope session_id")
    if projection.get("contract_id") != message.get("contract_id"):
        issue("PROJECTION_CONTRACT_MISMATCH", "projection contract_id must equal envelope contract_id")
    try:
        expected_projection_hash = object_hash(PROJECTION_OBJECT_TYPE, projection)
    except Exception as exc:
        issue("PROJECTION_HASH_MISMATCH", f"projection hash recompute failed: {exc}")
    else:
        if payload.get("session_state_hash") != expected_projection_hash:
            issue("PROJECTION_HASH_MISMATCH", "session_state_hash does not match projection")

    profiles = projection.get("selected_aicp_profiles")
    if (
        not isinstance(profiles, list)
        or profiles != sorted(profiles, key=canonical_profile_ref_key)
        or len({canonical_profile_ref_key(profile) for profile in profiles})
        != len(profiles)
    ):
        issue(
            "PROJECTION_PROFILE_SET_MISMATCH",
            "selected_aicp_profiles must be unique and canonically sorted",
        )
        profiles = profiles if isinstance(profiles, list) else []
    composition = {
        "composition_version": COMPOSITION_VERSION,
        "profiles": profiles,
    }
    resolved = resolve_profile_composition(composition)
    if resolved["errors"]:
        issue(
            "PROJECTION_PROFILE_SET_MISMATCH",
            "projection profile set is not a valid CAPNEG v0.2 composition",
        )
    elif projection.get("profile_composition_hash") != resolved["composition_hash"]:
        issue(
            "PROJECTION_COMPOSITION_HASH_MISMATCH",
            "projection composition hash does not match selected_aicp_profiles",
        )

    as_of = projection.get("as_of_message_hash")
    matching_indices = [
        index
        for index, prior in enumerate(transcript[:message_index])
        if prior.get("message_hash") == as_of
    ]
    prefix_state: dict[str, Any] | None = None
    if len(matching_indices) != 1:
        issue(
            "PROJECTION_AS_OF_STALE",
            "as_of_message_hash must identify exactly one prior transcript message",
        )
    else:
        from .state_machine import reduce_capneg_v02

        as_of_index = matching_indices[0]
        prefix_invalid = {
            index: observations
            for index, observations in (invalid_messages or {}).items()
            if index <= as_of_index
        }
        prefix_state = reduce_capneg_v02(
            transcript[: as_of_index + 1],
            rules=rules,
            registered_reason_codes=registered_reason_codes,
            key_map=key_map,
            crypto_available=crypto_available,
            invalid_messages=prefix_invalid,
            include_internal=True,
        )

    projection_participants = projection.get("participant_refs")
    target_participants = (
        sorted(projection_participants)
        if isinstance(projection_participants, list)
        and all(isinstance(party, str) for party in projection_participants)
        else None
    )
    negotiation_contexts = (
        prefix_state.get("_negotiation_contexts", {})
        if prefix_state is not None
        else {}
    )
    accepted_candidates = (
        [
            negotiation
            for negotiation in prefix_state.get("negotiations", [])
            if negotiation.get("state") == "ACCEPTED"
            and negotiation_contexts.get(
                str(negotiation.get("negotiation_id")), {}
            ).get("session_id")
            == projection.get("session_id")
            and negotiation_contexts.get(
                str(negotiation.get("negotiation_id")), {}
            ).get("contract_id")
            == projection.get("contract_id")
            and (
                target_participants is None
                or sorted(
                    negotiation_contexts.get(
                        str(negotiation.get("negotiation_id")), {}
                    ).get("participants", [])
                )
                == target_participants
            )
        ]
        if prefix_state is not None
        else []
    )
    if len(accepted_candidates) > 1:
        issue(
            "NEGOTIATION_ACCEPTED_ROOT_AMBIGUOUS",
            "projection cannot resolve more than one current accepted root for its negotiation context",
        )
    accepted_negotiation = (
        accepted_candidates[0] if len(accepted_candidates) == 1 else None
    )
    accepted_composition = (
        accepted_negotiation.get("accepted_profile_composition")
        if accepted_negotiation is not None
        else None
    )
    if prefix_state is not None and accepted_negotiation is None:
        issue(
            "PROJECTION_ACCEPTANCE_NOT_ESTABLISHED",
            "the projected CAPNEG result is not current and fully accepted at as_of_message_hash",
        )
    if (
        not isinstance(accepted_composition, dict)
        or accepted_composition.get("profiles") != profiles
    ):
        issue(
            "PROJECTION_PROFILE_SET_MISMATCH",
            "projection profile set must equal the fully accepted composition",
        )
    if projection.get("accepted_negotiation_result_hash") != (
        accepted_negotiation.get("accepted_result_hash")
        if accepted_negotiation is not None
        else None
    ):
        issue(
            "PROJECTION_ACCEPTED_RESULT_HASH_MISMATCH",
            "projection accepted result hash must equal CAPNEG accepted state",
        )

    active_extensions = projection.get("active_extensions", [])
    if (
        not isinstance(active_extensions, list)
        or active_extensions != sorted(set(active_extensions))
        or any(extension not in registered_extensions for extension in active_extensions)
    ):
        issue(
            "PROJECTION_ACTIVE_EXTENSION_INCONSISTENT",
            "active_extensions must be unique, canonical, and registered",
        )
    elif not set(resolved.get("required_extensions", [])) <= set(active_extensions):
        issue(
            "PROJECTION_ACTIVE_EXTENSION_INCONSISTENT",
            "active_extensions omits a composition-required extension",
        )

    return issues
