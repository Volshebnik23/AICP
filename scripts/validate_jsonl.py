#!/usr/bin/env python3
"""Validate that JSONL files are parseable line-by-line."""

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
    files = 0
    lines = 0

    for file_path in sorted(root.rglob("*.jsonl")):
        if should_skip(file_path):
            continue
        files += 1
        for line_no, line in enumerate(file_path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            lines += 1
            try:
                json.loads(line)
            except Exception as exc:  # noqa: BLE001
                rel = file_path.relative_to(root)
                print(f"[FAIL] Invalid JSONL: {rel}:{line_no}: {exc}")
                errors += 1

    if errors:
        print(f"JSONL validation failed with {errors} error(s) across {files} file(s).")
        return 1

    print(f"OK: {files} JSONL file(s) and {lines} JSONL record(s) parsed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
