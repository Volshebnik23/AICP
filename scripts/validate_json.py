#!/usr/bin/env python3
"""Validate that JSON files are parseable."""

from __future__ import annotations

import json
import sys
from pathlib import Path

SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__"}


def should_skip(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    errors = 0
    count = 0

    for file_path in sorted(root.rglob("*.json")):
        if should_skip(file_path):
            continue
        count += 1
        try:
            json.loads(file_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] Invalid JSON: {file_path.relative_to(root)}: {exc}")
            errors += 1

    if errors:
        print(f"JSON validation failed with {errors} error(s) across {count} file(s).")
        return 1

    print(f"OK: {count} JSON file(s) parsed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
