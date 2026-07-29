"""Independent fixture-construction model for CAPNEG v0.2.

This module intentionally has no dependency on the production CAPNEG resolver,
reducer, conformance runner, contract validator, or projection validator.
"""

from __future__ import annotations

from typing import Any

from aicp_ref.hashing import object_hash


COMPOSITION_VERSION = "aicp.profile_composition.v1"
COMPOSITION_HASH_DOMAIN = "capneg.profile_composition"


def canonical_profile_ref_key(value: Any) -> tuple[str, str]:
    if not isinstance(value, dict):
        return "", ""
    return str(value.get("profile_id", "")), str(value.get("profile_version", ""))


def _error(code: str, detail: str) -> dict[str, str]:
    return {"code": code, "detail": detail}


def resolve_fixture_composition(
    composition_value: Any, rules: dict[str, Any]
) -> dict[str, Any]:
    composition = composition_value
    errors: list[dict[str, str]] = []
    if not isinstance(composition, dict):
        composition = {}
        errors.append(
            _error(
                "PROFILE_COMPOSITION_SHAPE_INVALID",
                "profile composition must be an object",
            )
        )
    if composition.get("composition_version") != COMPOSITION_VERSION:
        errors.append(
            _error(
                "PROFILE_COMPOSITION_VERSION_UNSUPPORTED",
                f"composition_version must equal {COMPOSITION_VERSION}",
            )
        )
    profiles = composition.get("profiles")
    if not isinstance(profiles, list):
        profiles = []
        errors.append(
            _error("PROFILE_COMPOSITION_SHAPE_INVALID", "profiles must be an array")
        )
    if not profiles:
        errors.append(
            _error(
                "PROFILE_COMPOSITION_EMPTY",
                "profile composition must contain at least one profile",
            )
        )
    maximum = int(rules.get("maximum_profiles", 16))
    if len(profiles) > maximum:
        errors.append(
            _error(
                "PROFILE_COMPOSITION_LIMIT_EXCEEDED",
                f"profile composition exceeds maximum_profiles={maximum}",
            )
        )
    if not all(
        isinstance(profile, dict)
        and set(profile) == {"profile_id", "profile_version"}
        and isinstance(profile.get("profile_id"), str)
        and bool(profile["profile_id"])
        and isinstance(profile.get("profile_version"), str)
        and bool(profile["profile_version"])
        for profile in profiles
    ):
        errors.append(
            _error(
                "PROFILE_REF_INVALID",
                "every profile must contain only non-empty profile_id and profile_version",
            )
        )

    canonical_profiles = sorted(profiles, key=canonical_profile_ref_key)
    canonical = {
        "composition_version": COMPOSITION_VERSION,
        "profiles": canonical_profiles,
    }
    if profiles != canonical_profiles:
        errors.append(
            _error(
                "PROFILE_ORDER_NON_CANONICAL",
                "profiles must be sorted by exact profile_id then profile_version",
            )
        )
    keys = [canonical_profile_ref_key(profile) for profile in profiles]
    for key in sorted({key for key in keys if keys.count(key) > 1}):
        errors.append(
            _error(
                "PROFILE_DUPLICATE",
                f"duplicate profile reference {key[0]}@{key[1]}",
            )
        )
    versions_by_id: dict[str, set[str]] = {}
    for profile_id, version in keys:
        versions_by_id.setdefault(profile_id, set()).add(version)
    for profile_id in sorted(versions_by_id):
        versions = sorted(versions_by_id[profile_id])
        if len(versions) > 1:
            errors.append(
                _error(
                    "PROFILE_FAMILY_VERSION_CONFLICT",
                    f"{profile_id} selects multiple exact versions: {versions}",
                )
            )

    records = {
        canonical_profile_ref_key(record["profile"]): record
        for record in rules.get("profiles", [])
        if isinstance(record, dict) and isinstance(record.get("profile"), dict)
    }
    selected_records: list[dict[str, Any]] = []
    for key in sorted(set(keys)):
        record = records.get(key)
        if record is None:
            errors.append(
                _error(
                    "PROFILE_UNKNOWN",
                    f"unknown exact profile {key[0]}@{key[1]}",
                )
            )
        else:
            selected_records.append(record)
    core_paths = sorted(
        {
            str(record.get("core_suite", {}).get("path", ""))
            for record in selected_records
            if isinstance(record.get("core_suite"), dict)
        }
    )
    if len(core_paths) > 1:
        errors.append(
            _error(
                "PROFILE_CORE_VERSION_CONFLICT",
                f"selected profiles resolve to multiple Core suites: {core_paths}",
            )
        )
    for record in selected_records:
        if record.get("negotiable_by_capneg_v0_2") is not True:
            reason = record.get("capneg_v0_2_unsupported_reason", {})
            errors.append(
                _error(
                    str(reason.get("reason_code", "CAPNEG_CORE_FAMILY_UNSUPPORTED")),
                    str(reason.get("detail", "profile is not negotiable by CAPNEG v0.2")),
                )
            )
    selected_keys = set(keys)
    for relation in rules.get("rules", {}).get(
        "strict_suite_subset_relations", []
    ):
        redundant = canonical_profile_ref_key(relation.get("redundant_profile"))
        covering = canonical_profile_ref_key(relation.get("covering_profile"))
        if redundant in selected_keys and covering in selected_keys:
            errors.append(
                _error(
                    "PROFILE_COMPOSITION_REDUNDANT",
                    f"{redundant[0]}@{redundant[1]} is a strict required-suite "
                    f"subset of {covering[0]}@{covering[1]}",
                )
            )
    for group in rules.get("rules", {}).get("exclusive_groups", []):
        members = {
            canonical_profile_ref_key(member) for member in group.get("members", [])
        }
        selected_members = sorted(selected_keys & members)
        maximum_selected = int(group.get("max_selected", 1))
        if len(selected_members) > maximum_selected:
            errors.append(
                _error(
                    "PROFILE_COMPOSITION_EXCLUSIVE_CONFLICT",
                    f"exclusive group {group.get('group_id')} allows at most "
                    f"{maximum_selected}: {selected_members}",
                )
            )

    def union(field: str) -> list[str]:
        return sorted(
            {
                value
                for record in selected_records
                for value in record.get(field, [])
                if isinstance(value, str)
            }
        )

    marks = sorted(
        {
            record["compatibility_mark"]
            for record in selected_records
            if isinstance(record.get("compatibility_mark"), str)
        }
    )
    return {
        "composition": canonical,
        "composition_hash": (
            object_hash(COMPOSITION_HASH_DOMAIN, canonical) if not errors else None
        ),
        "core_suite": (
            selected_records[0].get("core_suite")
            if len(core_paths) == 1 and selected_records
            else None
        ),
        "required_suites": union("required_suites"),
        "required_extensions": union("required_extensions"),
        "required_crypto_profiles": union("required_crypto_profiles"),
        "required_policy_categories": union("required_policy_categories"),
        "component_compatibility_marks": marks,
        "errors": errors,
    }
