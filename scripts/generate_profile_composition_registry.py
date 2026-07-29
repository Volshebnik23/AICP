#!/usr/bin/env python3
"""Generate the exact profile-composition rules used by EXT-CAPNEG v0.2."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "registry/aicp_profile_composition_rules.json"
PROFILE_REGISTRY = ROOT / "registry/aicp_profiles.json"
PROFILE_CATALOGS = ROOT / "conformance/profiles"
SUPPORTED_CORE_SUITE = "conformance/core/CT_CORE_0.1.json"
MAX_PROFILES = 16

EXCLUSIVE_GROUPS = [
    {
        "group_id": "policy-semantic-dialect",
        "max_selected": 1,
        "members": [
            {
                "profile_id": "AICP-POLICY-ABAC-RBAC",
                "profile_version": "0.1",
            },
            {
                "profile_id": "AICP-POLICY-LLM-SAFETY",
                "profile_version": "0.1",
            },
            {
                "profile_id": "AICP-POLICY-OPA-REGO",
                "profile_version": "0.1",
            },
        ],
        "evidence": "docs/profiles/AICP_Policy_Semantic_Profiles.md",
    }
]


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _profile_ref(profile_id: str, profile_version: str) -> dict[str, str]:
    return {
        "profile_id": profile_id,
        "profile_version": profile_version,
    }


def _profile_key(value: dict[str, Any]) -> tuple[str, str]:
    return str(value["profile_id"]), str(value["profile_version"])


def _suite_metadata(path: str) -> dict[str, str]:
    suite = _load_json(ROOT / path)
    suite_id = suite.get("suite_id")
    suite_version = suite.get("suite_version")
    if not isinstance(suite_id, str) or not isinstance(suite_version, str):
        raise ValueError(f"{path}: suite_id and suite_version are required")
    return {
        "suite_id": suite_id,
        "suite_version": suite_version,
        "path": path,
    }


def build_registry(root: Path = ROOT) -> dict[str, Any]:
    registry_entries = _load_json(root / PROFILE_REGISTRY.relative_to(ROOT))
    if not isinstance(registry_entries, list):
        raise ValueError("registry/aicp_profiles.json must be a list")

    catalogs: dict[tuple[str, str], tuple[str, dict[str, Any]]] = {}
    for path in sorted((root / PROFILE_CATALOGS.relative_to(ROOT)).glob("PF_AICP_*.json")):
        catalog = _load_json(path)
        if not isinstance(catalog, dict):
            raise ValueError(f"{path.relative_to(root).as_posix()}: catalog must be an object")
        key = _profile_key(catalog)
        if key in catalogs:
            raise ValueError(f"duplicate profile catalog: {key[0]}@{key[1]}")
        catalogs[key] = (path.relative_to(root).as_posix(), catalog)

    registry_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in registry_entries:
        if not isinstance(entry, dict):
            raise ValueError("profile registry entries must be objects")
        key = _profile_key(entry)
        if key in registry_by_key:
            raise ValueError(f"duplicate registered profile: {key[0]}@{key[1]}")
        if entry.get("id") != f"{key[0]}@{key[1]}":
            raise ValueError(f"registry id mismatch for {key[0]}@{key[1]}")
        registry_by_key[key] = entry

    if set(catalogs) != set(registry_by_key):
        missing_catalogs = sorted(set(registry_by_key) - set(catalogs))
        missing_registry = sorted(set(catalogs) - set(registry_by_key))
        raise ValueError(
            "profile registry/catalog mismatch: "
            f"missing_catalogs={missing_catalogs}, missing_registry={missing_registry}"
        )

    profiles: list[dict[str, Any]] = []
    marks: set[str] = set()
    for key in sorted(registry_by_key):
        registry_entry = registry_by_key[key]
        catalog_path, catalog = catalogs[key]
        required_suites = catalog.get("required_suites")
        if not isinstance(required_suites, list) or not required_suites:
            raise ValueError(f"{key[0]}@{key[1]}: required_suites must be non-empty")
        if len(required_suites) != len(set(required_suites)):
            raise ValueError(f"{key[0]}@{key[1]}: duplicate required suite")
        for suite_path in required_suites:
            if not isinstance(suite_path, str) or not (root / suite_path).is_file():
                raise ValueError(f"{key[0]}@{key[1]}: unresolved suite {suite_path!r}")

        core_paths = sorted(
            path
            for path in required_suites
            if isinstance(path, str) and path.startswith("conformance/core/CT_CORE_")
        )
        if len(core_paths) != 1:
            raise ValueError(
                f"{key[0]}@{key[1]}: expected exactly one Core suite, found {core_paths}"
            )

        mark = catalog.get("compatibility_mark")
        if not isinstance(mark, str) or not mark:
            raise ValueError(f"{key[0]}@{key[1]}: compatibility_mark is required")
        if mark in marks:
            raise ValueError(f"duplicate compatibility mark: {mark}")
        marks.add(mark)

        negotiable = core_paths[0] == SUPPORTED_CORE_SUITE
        record: dict[str, Any] = {
            "profile": _profile_ref(*key),
            "profile_catalog": catalog_path,
            "core_suite": _suite_metadata(core_paths[0]),
            "required_suites": sorted(required_suites),
            "required_extensions": sorted(registry_entry.get("required_extensions", [])),
            "required_crypto_profiles": sorted(
                registry_entry.get("required_crypto_profiles", [])
            ),
            "required_policy_categories": sorted(
                registry_entry.get("required_policy_categories", [])
            ),
            "compatibility_mark": mark,
            "negotiable_by_capneg_v0_2": negotiable,
        }
        if not negotiable:
            record["capneg_v0_2_unsupported_reason"] = {
                "reason_code": "CAPNEG_CORE_FAMILY_UNSUPPORTED",
                "detail": (
                    "EXT-CAPNEG v0.2 uses the Core v0.1 bootstrap envelope and "
                    f"does not negotiate profiles requiring {core_paths[0]}."
                ),
            }
        profiles.append(record)

    profile_keys = {
        _profile_key(record["profile"])
        for record in profiles
    }
    for group in EXCLUSIVE_GROUPS:
        for member in group["members"]:
            if _profile_key(member) not in profile_keys:
                raise ValueError(
                    f"exclusive group {group['group_id']} references an unknown profile"
                )

    subset_relations: list[dict[str, Any]] = []
    for candidate in profiles:
        candidate_suites = set(candidate["required_suites"])
        for covering in profiles:
            if candidate is covering:
                continue
            covering_suites = set(covering["required_suites"])
            if candidate_suites < covering_suites:
                subset_relations.append(
                    {
                        "redundant_profile": candidate["profile"],
                        "covering_profile": covering["profile"],
                    }
                )
    subset_relations.sort(
        key=lambda item: (
            *_profile_key(item["redundant_profile"]),
            *_profile_key(item["covering_profile"]),
        )
    )

    return {
        "registry_version": "aicp.profile_composition_rules.v1",
        "generator": "scripts/generate_profile_composition_registry.py",
        "composition_version": "aicp.profile_composition.v1",
        "composition_hash_domain": "capneg.profile_composition",
        "capneg_version": "0.2",
        "maximum_profiles": MAX_PROFILES,
        "supported_core_suites": [_suite_metadata(SUPPORTED_CORE_SUITE)],
        "rules": {
            "exact_profile_match": True,
            "canonical_order": ["profile_id", "profile_version"],
            "same_profile_id_max_versions": 1,
            "reject_strict_suite_redundancy": True,
            "exclusive_groups": EXCLUSIVE_GROUPS,
            "strict_suite_subset_relations": subset_relations,
        },
        "profiles": profiles,
    }


def _render(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()

    rendered = _render(build_registry())
    if args.check:
        if not OUTPUT.is_file():
            print(f"[FAIL] missing generated registry: {OUTPUT.relative_to(ROOT)}")
            return 1
        if OUTPUT.read_text(encoding="utf-8") != rendered:
            print(
                "[FAIL] registry/aicp_profile_composition_rules.json is stale; "
                "run scripts/generate_profile_composition_registry.py --write"
            )
            return 1
        print("OK: profile-composition registry matches deterministic generator output.")
        return 0

    OUTPUT.write_text(rendered, encoding="utf-8")
    print(f"Generated {OUTPUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
