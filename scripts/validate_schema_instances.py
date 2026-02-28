#!/usr/bin/env python3
"""Validate fixture JSONL records against the canonical Core message schema when available."""

from __future__ import annotations

import json
import sys
from pathlib import Path

SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__"}
CANONICAL_SCHEMA = Path("schemas/core/aicp-core-message.schema.json")


def should_skip(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def load_records(root: Path) -> list[tuple[Path, int, object]]:
    records: list[tuple[Path, int, object]] = []
    for path in sorted(root.rglob("*.jsonl")):
        if should_skip(path):
            continue
        if "fixtures" not in path.parts:
            continue
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            records.append((path, line_no, json.loads(line)))
    return records


def resolve_schema_path(root: Path) -> Path | None:
    canonical_path = root / CANONICAL_SCHEMA
    if canonical_path.exists():
        return canonical_path

    candidates = [
        p for p in sorted(root.rglob("aicp-core-message.schema.json")) if not should_skip(p)
    ]
    if not candidates:
        return None

    print(
        f"[WARN] Canonical schema {CANONICAL_SCHEMA.as_posix()} was not found. "
        f"Falling back to discovered schema {candidates[0].relative_to(root)}."
    )
    return candidates[0]


def main() -> int:
    root = Path(__file__).resolve().parents[1]

    try:
        from jsonschema import Draft202012Validator
    except Exception:  # noqa: BLE001
        print("[WARN] jsonschema is not installed. Skipping schema instance validation.")
        return 0

    schema_path = resolve_schema_path(root)
    if schema_path is None:
        print("[WARN] No aicp-core-message.schema.json found. Skipping schema instance validation.")
        return 0

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)

    errors = 0
    records = load_records(root)

    for file_path, line_no, record in records:
        for err in sorted(validator.iter_errors(record), key=lambda issue: list(issue.path)):
            rel = file_path.relative_to(root)
            print(f"[FAIL] Schema violation: {rel}:{line_no}: {err.message}")
            errors += 1

    schema_rel = schema_path.relative_to(root)
    if errors:
        print(f"Schema validation failed with {errors} error(s) using {schema_rel}.")
        return 1

    print(f"OK: {len(records)} fixture JSONL record(s) validated against {schema_rel}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
