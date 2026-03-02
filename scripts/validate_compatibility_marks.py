#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFORMANCE_ROOT = ROOT / "conformance"
EXT_REGISTRY = ROOT / "registry/extension_ids.json"
PROFILE_REGISTRY = ROOT / "registry/aicp_profiles.json"
BINDING_REGISTRY = ROOT / "registry/transport_bindings.json"

EXT_MARK_RE = re.compile(r"^AICP-EXT-(?P<name>[A-Z0-9-]+)-(?P<version>\d[0-9A-Za-z.-]*)$")
PROFILE_MARK_RE = re.compile(r"^AICP-Profile-(?P<name>[A-Z0-9-]+)-(?P<version>\d[0-9A-Za-z.-]*)$")
BINDING_MARK_RE = re.compile(r"^AICP-BIND-(?P<name>[A-Z0-9-]+)-(?P<version>\d[0-9A-Za-z.-]*)$")


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _collect_compatibility_marks(node: Any, path: Path, pointer: str = "") -> list[tuple[str, Path, str]]:
    marks: list[tuple[str, Path, str]] = []
    if isinstance(node, dict):
        for key, value in node.items():
            child_pointer = f"{pointer}/{key}" if pointer else f"/{key}"
            if key == "compatibility_mark" and isinstance(value, str):
                marks.append((value, path, child_pointer))
            marks.extend(_collect_compatibility_marks(value, path, child_pointer))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            child_pointer = f"{pointer}/{index}" if pointer else f"/{index}"
            marks.extend(_collect_compatibility_marks(value, path, child_pointer))
    return marks


def _normalize_profile_name(profile_id: str) -> str:
    return profile_id[5:] if profile_id.startswith("AICP-") else profile_id


def load_extension_ids() -> set[str]:
    payload = _load_json(EXT_REGISTRY)
    return {
        entry["id"]
        for entry in payload
        if isinstance(entry, dict) and isinstance(entry.get("id"), str) and entry["id"].startswith("EXT-")
    }


def load_profiles_registry() -> dict[tuple[str, str], dict[str, Any]]:
    payload = _load_json(PROFILE_REGISTRY)
    entries: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        profile_id = entry.get("profile_id")
        profile_version = entry.get("profile_version")
        if isinstance(profile_id, str) and isinstance(profile_version, str):
            entries[(profile_id, profile_version)] = entry
    return entries


def load_binding_ids() -> set[str]:
    payload = _load_json(BINDING_REGISTRY)
    return {
        entry["id"]
        for entry in payload
        if isinstance(entry, dict) and isinstance(entry.get("id"), str)
    }


def main() -> int:
    extension_ids = load_extension_ids()
    profile_registry = load_profiles_registry()
    binding_ids = load_binding_ids()
    failures: list[str] = []

    all_json_paths = sorted(CONFORMANCE_ROOT.glob("**/*.json"))

    seen_marks: dict[str, tuple[Path, str]] = {}
    for json_path in all_json_paths:
        payload = _load_json(json_path)
        for mark, source_path, pointer in _collect_compatibility_marks(payload, json_path):
            if mark in seen_marks:
                first_path, first_pointer = seen_marks[mark]
                failures.append(
                    f"{_rel(source_path)}{pointer}: compatibility_mark '{mark}' is duplicated; "
                    f"already defined at {_rel(first_path)}{first_pointer}."
                )
            else:
                seen_marks[mark] = (source_path, pointer)

    extension_suite_paths = sorted((CONFORMANCE_ROOT / "extensions").glob("*.json"))
    for suite_path in extension_suite_paths:
        suite = _load_json(suite_path)
        mark = suite.get("compatibility_mark")
        if not isinstance(mark, str) or not mark.startswith("AICP-EXT-"):
            continue

        match = EXT_MARK_RE.fullmatch(mark)
        if not match:
            failures.append(
                f"{_rel(suite_path)}: compatibility_mark '{mark}' is malformed. "
                "Expected pattern AICP-EXT-<EXT_NAME>-<version>."
            )
            continue

        ext_id = f"EXT-{match.group('name')}"
        if ext_id not in extension_ids:
            failures.append(
                f"{_rel(suite_path)}: compatibility_mark '{mark}' references missing extension id '{ext_id}' "
                "in registry/extension_ids.json."
            )

    profile_paths = sorted((CONFORMANCE_ROOT / "profiles").glob("*.json"))
    profiles_from_conformance: set[tuple[str, str]] = set()
    for profile_path in profile_paths:
        profile = _load_json(profile_path)
        profile_id = profile.get("profile_id")
        profile_version = profile.get("profile_version")
        mark = profile.get("compatibility_mark")

        if not isinstance(profile_id, str) or not isinstance(profile_version, str):
            failures.append(
                f"{_rel(profile_path)}: profile_id/profile_version must be strings for compatibility mark validation."
            )
            continue
        profiles_from_conformance.add((profile_id, profile_version))

        if not isinstance(mark, str):
            continue

        match = PROFILE_MARK_RE.fullmatch(mark)
        if not match:
            failures.append(
                f"{_rel(profile_path)}: compatibility_mark '{mark}' is malformed. "
                "Expected pattern AICP-Profile-<PROFILE_NAME>-<version>."
            )
            continue

        mark_name = match.group("name")
        mark_version = match.group("version")
        expected_name = _normalize_profile_name(profile_id)
        if mark_name != expected_name or mark_version != profile_version:
            failures.append(
                f"{_rel(profile_path)}: compatibility_mark '{mark}' does not align with "
                f"profile_id/profile_version ({profile_id}@{profile_version}). "
                f"Expected AICP-Profile-{expected_name}-{profile_version}."
            )

        if (profile_id, profile_version) not in profile_registry:
            failures.append(
                f"{_rel(profile_path)}: profile {profile_id}@{profile_version} is missing from "
                "registry/aicp_profiles.json."
            )

    for profile_id, profile_version in sorted(profiles_from_conformance):
        if (profile_id, profile_version) not in profile_registry:
            continue

    for profile_id, profile_version in sorted(profile_registry):
        if (profile_id, profile_version) not in profiles_from_conformance:
            failures.append(
                f"registry/aicp_profiles.json: profile {profile_id}@{profile_version} has no matching "
                "conformance/profiles/*.json catalog."
            )

    binding_paths = sorted((CONFORMANCE_ROOT / "bindings").glob("*.json"))
    for binding_path in binding_paths:
        suite = _load_json(binding_path)
        mark = suite.get("compatibility_mark")
        if not isinstance(mark, str):
            continue

        match = BINDING_MARK_RE.fullmatch(mark)
        if not match:
            failures.append(
                f"{_rel(binding_path)}: compatibility_mark '{mark}' is malformed. "
                "Expected pattern AICP-BIND-<BINDING_NAME>-<version>."
            )
            continue

        name = match.group("name")
        version = match.group("version")
        candidate_ids = {f"EXT-BIND-{name}", f"BIND-{name}-{version}"}
        if not (candidate_ids & binding_ids):
            failures.append(
                f"{_rel(binding_path)}: compatibility_mark '{mark}' is not represented in "
                "registry/transport_bindings.json. Expected one of "
                f"{', '.join(sorted(candidate_ids))}."
            )

    if failures:
        print("FAIL: compatibility mark validation failed:")
        for item in failures:
            print(f"- {item}")
        return 1

    print(
        "OK: compatibility marks are unique across conformance/** and align with extension/profile/binding registries."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
