#!/usr/bin/env python3
"""Validate coverage for stable and profile-required message types across schemas, fixtures, and conformance suites."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _stable_message_types() -> list[str]:
    registry = _load_json(ROOT / "registry" / "message_types.json")
    if not isinstance(registry, list):
        raise ValueError("registry/message_types.json must be a JSON list")
    stable_ids: list[str] = []
    for entry in registry:
        if isinstance(entry, dict) and entry.get("status") == "stable":
            msg_id = entry.get("id")
            if isinstance(msg_id, str) and msg_id:
                stable_ids.append(msg_id)
    return sorted(set(stable_ids))






def _stable_extension_entries() -> list[dict[str, str]]:
    registry = _load_json(ROOT / "registry" / "extension_ids.json")
    if not isinstance(registry, list):
        raise ValueError("registry/extension_ids.json must be a JSON list")
    out: list[dict[str, str]] = []
    for entry in registry:
        if not isinstance(entry, dict) or entry.get("status") != "stable":
            continue
        ext_id = entry.get("id")
        spec_ref = entry.get("spec_ref")
        if isinstance(ext_id, str) and isinstance(spec_ref, str):
            out.append({"id": ext_id, "spec_ref": spec_ref})
    return out


def _stable_extension_coverage_failures(entries: list[dict[str, str]]) -> list[str]:
    failures: list[str] = []
    ext_suites = sorted((ROOT / "conformance" / "extensions").glob("*.json"))
    suite_texts = {p: p.read_text(encoding="utf-8") for p in ext_suites}
    for entry in entries:
        ext_id = entry["id"]
        slug = ext_id.replace("EXT-", "").lower().replace("-", "_")
        spec_path = entry["spec_ref"].split("#", 1)[0]
        if not (ROOT / spec_path).exists():
            failures.append(f"stable extension {ext_id}: spec_ref target missing ({spec_path})")

        fixtures_dir = ROOT / "fixtures" / "extensions" / slug
        fixtures_match = sorted(fixtures_dir.glob("*.jsonl")) + sorted(fixtures_dir.glob("*.json"))
        if not fixtures_match:
            # fallback fuzzy check for capneg naming or other historical aliases
            all_ext_fixtures = list((ROOT / "fixtures" / "extensions").glob("**/*"))
            fixtures_match = [p for p in all_ext_fixtures if p.is_file() and slug.replace("_", "") in p.as_posix().replace("_", "")]
        if not fixtures_match:
            failures.append(f"stable extension {ext_id}: no fixtures found under fixtures/extensions/{slug}/")

        suite_hits = []
        for suite_path in ext_suites:
            suite_json = _load_json(suite_path)
            if isinstance(suite_json, dict) and suite_json.get("extension_id") == ext_id:
                suite_hits.append(suite_path)
                continue
            if ext_id in suite_texts[suite_path]:
                suite_hits.append(suite_path)
        if not suite_hits:
            failures.append(f"stable extension {ext_id}: no conformance/extensions suite references this id")
    return failures

def _profile_required_message_types() -> set[str]:
    profile_files = sorted((ROOT / "conformance" / "profiles").glob("*.json"))
    required: set[str] = set()
    for profile_path in profile_files:
        profile = _load_json(profile_path)
        if not isinstance(profile, dict):
            continue
        for rel_suite in profile.get("required_suites", []):
            if not isinstance(rel_suite, str) or not rel_suite:
                continue
            suite_path = ROOT / rel_suite
            if not suite_path.exists():
                continue
            suite = _load_json(suite_path)
            if not isinstance(suite, dict):
                continue
            payload_schema_map = suite.get("payload_schema_map")
            if isinstance(payload_schema_map, dict):
                required.update(k for k in payload_schema_map.keys() if isinstance(k, str) and k)
            for transcript in suite.get("transcripts", []):
                if not isinstance(transcript, dict):
                    continue
                for mtype in transcript.get("expected_message_types", []):
                    if isinstance(mtype, str) and mtype:
                        required.add(mtype)
    return required

def _walk_message_types(value: Any, out: set[str]) -> None:
    if isinstance(value, dict):
        msg_type = value.get("message_type")
        if isinstance(msg_type, str) and msg_type:
            out.add(msg_type)
        for child in value.values():
            _walk_message_types(child, out)
    elif isinstance(value, list):
        for child in value:
            _walk_message_types(child, out)


def _scan_fixture_message_types() -> tuple[set[str], list[Path]]:
    fixture_files = sorted((ROOT / "fixtures").glob("**/*.jsonl")) + sorted((ROOT / "fixtures").glob("**/*.json"))
    seen: set[str] = set()
    for path in fixture_files:
        rel = path.relative_to(ROOT)
        if path.suffix == ".jsonl":
            with path.open("r", encoding="utf-8") as f:
                for line_no, line in enumerate(f, start=1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError as exc:
                        raise ValueError(f"Invalid JSONL in {rel}:{line_no}: {exc}") from exc
                    _walk_message_types(obj, seen)
        else:
            try:
                _walk_message_types(_load_json(path), seen)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON in {rel}: {exc}") from exc
    return seen, [p.relative_to(ROOT) for p in fixture_files]


def _scan_conformance_coverage() -> tuple[set[str], set[str], list[Path]]:
    suite_files = sorted((ROOT / "conformance").glob("**/*.json"))
    payload_map_types: set[str] = set()
    expected_types: set[str] = set()
    for path in suite_files:
        rel = path.relative_to(ROOT)
        suite = _load_json(path)
        if not isinstance(suite, dict):
            continue
        payload_map = suite.get("payload_schema_map")
        if isinstance(payload_map, dict):
            for k in payload_map.keys():
                if isinstance(k, str) and k:
                    payload_map_types.add(k)
        transcripts = suite.get("transcripts")
        if isinstance(transcripts, list):
            for transcript in transcripts:
                if not isinstance(transcript, dict):
                    continue
                emt = transcript.get("expected_message_types")
                if isinstance(emt, list):
                    for msg_type in emt:
                        if isinstance(msg_type, str) and msg_type:
                            expected_types.add(msg_type)
    return payload_map_types, expected_types, [p.relative_to(ROOT) for p in suite_files]


def main() -> int:
    try:
        stable_ids = _stable_message_types()
        stable_extensions = _stable_extension_entries()
        profile_required_types = _profile_required_message_types()
        fixture_types, fixture_files = _scan_fixture_message_types()
        payload_map_types, expected_types, suite_files = _scan_conformance_coverage()
        stable_extension_failures = _stable_extension_coverage_failures(stable_extensions)
    except Exception as exc:
        print(f"[FAIL] productization coverage check aborted: {exc}")
        return 1

    coverage_ids = sorted(set(stable_ids) | set(profile_required_types))
    missing_payload = [msg for msg in coverage_ids if msg not in payload_map_types]
    missing_fixtures = [msg for msg in coverage_ids if msg not in fixture_types]
    missing_conformance = [
        msg for msg in coverage_ids if msg not in payload_map_types and msg not in expected_types
    ]

    if missing_payload or missing_fixtures or missing_conformance or stable_extension_failures:
        print("[FAIL] Productization coverage requirements not satisfied.")
        print(f"  stable message types: {', '.join(stable_ids) if stable_ids else '(none)'}")
        print(f"  profile-required message types: {', '.join(sorted(profile_required_types)) if profile_required_types else '(none)'}")
        print(
            f"  scanned fixtures: {len(fixture_files)} file(s) under fixtures/**/*.jsonl|json; "
            f"conformance suites: {len(suite_files)} file(s) under conformance/**/*.json"
        )
        if missing_payload:
            print("  - Missing payload_schema_map coverage: " + ", ".join(missing_payload))
        if missing_fixtures:
            print("  - Missing fixture occurrences: " + ", ".join(missing_fixtures))
        if missing_conformance:
            print(
                "  - Missing conformance coverage (expected_message_types or payload_schema_map): "
                + ", ".join(missing_conformance)
            )
        for failure in stable_extension_failures:
            print("  - " + failure)
        return 1

    print(
        "OK: productization coverage satisfied "
        f"({len(stable_ids)} stable ids, {len(stable_extensions)} stable extensions, {len(profile_required_types)} profile-required ids, "
        f"{len(fixture_files)} fixtures scanned, {len(suite_files)} suites scanned)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
