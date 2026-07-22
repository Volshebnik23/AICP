from __future__ import annotations

import re
from typing import Any

from .hashing import object_hash


PROJECTION_VERSION = "aicp.session_state_projection.v1"
PROJECTION_OBJECT_TYPE = "session_state_projection"
HASH_RE = re.compile(r"^sha256:[A-Za-z0-9_-]{43}$")
REF_RE = re.compile(r"^[A-Za-z][A-Za-z0-9._-]*:[^\s]+$")
NAMESPACED_EXTENSION_RE = re.compile(r"^(?:x-[a-z0-9][a-z0-9._-]*|(?:vendor|org):[A-Za-z0-9][A-Za-z0-9._-]*)$")


def is_strict_session_state_projection(message: dict[str, Any]) -> bool:
    state = (message.get("payload") or {}).get("session_state")
    return isinstance(state, dict) and state.get("projection_version") == PROJECTION_VERSION


def project_session_state(context: dict[str, Any]) -> tuple[dict[str, Any], str]:
    """Build the portable claim from explicit externally visible context.

    This helper deliberately does not infer an internal reducer, database, or finality
    model. Callers supply the declared as-of/head context they intend to publish.
    """

    projection: dict[str, Any] = {
        "projection_version": PROJECTION_VERSION,
        "session_id": context["session_id"],
        "contract_id": context["contract_id"],
        "as_of_message_hash": context["as_of_message_hash"],
        "session_status": context.get("session_status", "UNKNOWN"),
    }
    for field in (
        "active_contract_ref",
        "selected_aicp_profile",
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


def _issue(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def _core_contract_ref_valid(value: Any) -> bool:
    if not isinstance(value, dict) or set(value) != {"branch_id", "base_version", "head_version"}:
        return False
    return all(isinstance(value.get(field), str) and value[field] for field in value)


def validate_session_state_projection(
    message: dict[str, Any],
    transcript: list[dict[str, Any]],
    message_index: int,
    *,
    registered_profiles: set[tuple[str, str]],
    registered_extensions: set[str],
) -> list[dict[str, str]]:
    if not is_strict_session_state_projection(message):
        return []

    payload = message.get("payload") or {}
    state = payload.get("session_state") or {}
    issues: list[dict[str, str]] = []

    if state.get("session_id") != message.get("session_id"):
        issues.append(_issue("session_mismatch", "projection session_id must equal envelope session_id"))
    if state.get("contract_id") != message.get("contract_id"):
        issues.append(_issue("contract_mismatch", "projection contract_id must equal envelope contract_id"))

    try:
        computed_hash = object_hash(PROJECTION_OBJECT_TYPE, state)
    except Exception as exc:
        issues.append(_issue("projection_hash", f"session_state_hash recompute error: {exc}"))
    else:
        if payload.get("session_state_hash") != computed_hash:
            issues.append(
                _issue(
                    "projection_hash",
                    f"session_state_hash mismatch (expected {payload.get('session_state_hash')}, got {computed_hash})",
                )
            )

    as_of = state.get("as_of_message_hash")
    if not isinstance(as_of, str) or not HASH_RE.fullmatch(as_of):
        issues.append(_issue("as_of", "as_of_message_hash must use the exact AICP SHA-256 syntax"))

    branch_heads = payload.get("branch_heads")
    declared_heads = [item for item in branch_heads if isinstance(item, dict)] if isinstance(branch_heads, list) else []
    known_hashes = {
        item.get("message_hash")
        for item in transcript[: message_index + 1]
        if isinstance(item.get("message_hash"), str)
    }
    declared_hashes = {
        item.get("message_hash") for item in declared_heads if isinstance(item.get("message_hash"), str)
    }
    if isinstance(as_of, str) and as_of not in known_hashes and as_of not in declared_hashes:
        issues.append(_issue("as_of", "as_of_message_hash must bind to a known message or declared branch head"))

    head_keys: set[tuple[Any, Any]] = set()
    for head in declared_heads:
        key = (head.get("branch_id"), head.get("head_version"))
        if key in head_keys:
            issues.append(_issue("active_head", "branch_heads must not repeat a branch_id/head_version pair"))
        head_keys.add(key)

    contract_ref = state.get("active_contract_ref")
    if contract_ref is not None and not _core_contract_ref_valid(contract_ref):
        issues.append(_issue("contract_ref", "active_contract_ref must have the canonical Core contract-ref shape"))

    active_head_version = payload.get("active_head_version")
    if active_head_version is not None:
        if _core_contract_ref_valid(contract_ref) and contract_ref.get("head_version") != active_head_version:
            issues.append(_issue("active_head", "active_head_version must equal active_contract_ref.head_version"))
        elif _core_contract_ref_valid(contract_ref) and not any(
            head.get("branch_id") == contract_ref.get("branch_id")
            and head.get("head_version") == active_head_version
            for head in declared_heads
        ):
            issues.append(_issue("active_head", "active_head_version must identify the declared active branch head"))

    profile = state.get("selected_aicp_profile")
    if profile is not None:
        profile_key = (
            profile.get("profile_id") if isinstance(profile, dict) else None,
            profile.get("profile_version") if isinstance(profile, dict) else None,
        )
        if profile_key not in registered_profiles:
            issues.append(_issue("profile", f"selected_aicp_profile {profile_key[0]}@{profile_key[1]} is not registered"))

    active_extensions = state.get("active_extensions")
    if active_extensions is not None:
        if not isinstance(active_extensions, list):
            issues.append(_issue("extension", "active_extensions must be an array"))
        else:
            seen_extensions: set[str] = set()
            for extension_id in active_extensions:
                if not isinstance(extension_id, str) or not extension_id:
                    issues.append(_issue("extension", "active_extensions entries must be non-empty strings"))
                    continue
                if extension_id in seen_extensions:
                    issues.append(_issue("extension", f"duplicate active extension '{extension_id}'"))
                seen_extensions.add(extension_id)
                if extension_id not in registered_extensions and not NAMESPACED_EXTENSION_RE.fullmatch(extension_id):
                    issues.append(_issue("extension", f"active extension '{extension_id}' is not registered or namespaced"))

    reference_fields = (
        "participant_refs",
        "policy_refs",
        "unresolved_conflict_refs",
        "authority_refs",
        "evidence_refs",
    )
    for field in reference_fields:
        refs = state.get(field)
        if refs is None:
            continue
        if not isinstance(refs, list):
            issues.append(_issue("reference", f"{field} must be an array"))
            continue
        seen_refs: set[str] = set()
        for ref in refs:
            if not isinstance(ref, str) or not REF_RE.fullmatch(ref):
                issues.append(_issue("reference", f"{field} contains an invalid reference"))
                continue
            if ref in seen_refs:
                issues.append(_issue("reference", f"{field} contains duplicate reference '{ref}'"))
            seen_refs.add(ref)

    evidence_refs = state.get("evidence_refs") or []
    prior_messages = transcript[:message_index]
    prior_ids = {item.get("message_id") for item in prior_messages}
    prior_hashes = {item.get("message_hash") for item in prior_messages}
    all_ids = {item.get("message_id") for item in transcript}
    all_hashes = {item.get("message_hash") for item in transcript}
    for ref in evidence_refs if isinstance(evidence_refs, list) else []:
        if not isinstance(ref, str):
            continue
        if ref.startswith("msgid:"):
            target = ref[len("msgid:") :]
            if target not in prior_ids:
                detail = "future" if target in all_ids else "unresolved"
                issues.append(_issue("reference", f"evidence reference '{ref}' is {detail}, not prior evidence"))
        elif ref.startswith("msghash:"):
            target = ref[len("msghash:") :]
            if target not in prior_hashes:
                detail = "future" if target in all_hashes else "unresolved"
                issues.append(_issue("reference", f"evidence reference '{ref}' is {detail}, not prior evidence"))

    status = state.get("session_status")
    conflicts = state.get("unresolved_conflict_refs") or []
    if status == "CONFLICTED" and not conflicts:
        issues.append(_issue("contradiction", "CONFLICTED requires unresolved_conflict_refs"))
    if status != "CONFLICTED" and conflicts:
        issues.append(_issue("contradiction", "unresolved_conflict_refs requires session_status CONFLICTED"))
    if status == "CLOSED":
        final_head = payload.get("final_head_version")
        if not isinstance(final_head, str) or not final_head:
            issues.append(_issue("contradiction", "CLOSED requires final_head_version"))
        elif isinstance(active_head_version, str) and active_head_version != final_head:
            issues.append(_issue("contradiction", "CLOSED active_head_version must equal final_head_version"))

    return issues
