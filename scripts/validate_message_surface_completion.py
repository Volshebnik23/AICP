#!/usr/bin/env python3
"""Fail closed unless every registered message has real positive coverage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from repo_truth import ROOT, _fixture_message_sequence, derive_message_surface


def completion_errors(root: Path = ROOT) -> list[str]:
    errors: list[str] = []
    try:
        surface = derive_message_surface(root)
    except (ValueError, json.JSONDecodeError) as exc:
        return [str(exc)]

    entries = surface["entries"]
    summary = surface["summary"]
    registered_count = summary["registered_count"]
    invariants = {
        "payload-schema mapped": summary["payload_schema_mapped_count"],
        "suite-owned": summary["suite_referenced_count"],
        "actual positive fixture covered": summary[
            "positive_fixture_referenced_count"
        ],
    }
    for label, count in invariants.items():
        if count != registered_count:
            errors.append(f"{label}: expected {registered_count}, found {count}")

    missing = summary["missing_positive_fixture_types"]
    if missing:
        errors.append(
            "missing actual positive fixture coverage: " + ", ".join(missing)
        )

    for entry in entries:
        message_id = entry["id"]
        if not isinstance(entry.get("owner"), str) or not entry["owner"]:
            errors.append(f"{message_id}: exactly one owner is required")
        schema = entry.get("payload_schema")
        if not isinstance(schema, dict) or not schema.get("file") or not schema.get(
            "pointer"
        ):
            errors.append(f"{message_id}: exactly one canonical payload mapping is required")
        if not entry.get("suites"):
            errors.append(f"{message_id}: at least one owning conformance suite is required")

    for suite_path in sorted((root / "conformance").glob("**/*.json")):
        try:
            suite: Any = json.loads(suite_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            continue
        if not isinstance(suite, dict):
            continue
        enabled_checks = {
            check.get("test_id")
            for check in suite.get("checks", [])
            if isinstance(check, dict)
        }
        if "CT-SEQUENCE-01" not in enabled_checks:
            continue
        for case in suite.get("transcripts", []):
            if not isinstance(case, dict):
                continue
            fixture_ref = case.get("path") or case.get("fixture") or case.get(
                "transcript"
            )
            expected = case.get("expected_message_types")
            if (
                not isinstance(fixture_ref, str)
                or not fixture_ref.endswith(".jsonl")
                or not isinstance(expected, list)
            ):
                continue
            actual = _fixture_message_sequence(root / fixture_ref)
            expected_sequence_failure = (
                case.get("expect_pass") is False
                and any(
                    isinstance(failure, dict)
                    and failure.get("test_id") == "CT-SEQUENCE-01"
                    for failure in case.get("expected_failures", [])
                )
            )
            if actual != expected and not expected_sequence_failure:
                suite_ref = suite_path.relative_to(root).as_posix()
                errors.append(
                    f"{suite_ref}::{case.get('id', '<unknown>')}: "
                    f"expected_message_types does not match actual JSONL sequence"
                )
    return errors


def main() -> int:
    errors = completion_errors()
    if errors:
        for error in errors:
            print(f"[ERROR] {error}")
        return 1
    surface = derive_message_surface(ROOT)
    summary = surface["summary"]
    version_selected = sum(
        "payload_schema_variants" in entry for entry in surface["entries"]
    )
    print(
        "[OK] registered message surface complete: "
        f"{summary['positive_fixture_referenced_count']}/"
        f"{summary['registered_count']} actual positive coverage; "
        f"{version_selected} version-selected IDs"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
