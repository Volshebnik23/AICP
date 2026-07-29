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
    capneg_state: dict[str, Any],
    registered_extensions: set[str],
) -> list[dict[str, str]]:
    payload = message.get("payload", {})
    projection = payload.get("session_state")
    if (
        not isinstance(projection, dict)
        or projection.get("projection_version") != PROJECTION_VERSION
    ):
        return []

    issues: list[dict[str, str]] = []

    def issue(code: str, detail: str) -> None:
        issues.append({"code": code, "detail": detail})

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

    accepted_composition = capneg_state.get("accepted_profile_composition")
    if (
        not isinstance(accepted_composition, dict)
        or accepted_composition.get("profiles") != profiles
    ):
        issue(
            "PROJECTION_PROFILE_SET_MISMATCH",
            "projection profile set must equal the fully accepted composition",
        )
    if projection.get("accepted_negotiation_result_hash") != capneg_state.get(
        "accepted_result_hash"
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

    as_of = projection.get("as_of_message_hash")
    known_hashes = {
        prior.get("message_hash")
        for prior in transcript[: message_index + 1]
        if isinstance(prior.get("message_hash"), str)
    }
    declared_hashes = {
        head.get("message_hash")
        for head in payload.get("branch_heads", [])
        if isinstance(head, dict) and isinstance(head.get("message_hash"), str)
    }
    if as_of not in known_hashes | declared_hashes:
        issue(
            "PROJECTION_AS_OF_STALE",
            "as_of_message_hash must bind a known transcript message or declared head",
        )

    return issues
