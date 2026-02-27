#!/usr/bin/env python3
"""Enforce canonical AICP naming in markdown docs."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BANNED = "AI Interconnector Protocol"
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__"}


def should_skip(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def main() -> int:
    failures: list[tuple[Path, int, str]] = []
    for path in sorted(ROOT.rglob("*.md")):
        if should_skip(path):
            continue
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), start=1):
            if BANNED in line:
                failures.append((path, line_no, line.strip()))

    if failures:
        for path, line_no, line in failures:
            print(f"[FAIL] banned naming in {path.relative_to(ROOT)}:{line_no}: {line}")
        print(f"\nNaming check failed: found banned term '{BANNED}'.")
        return 1

    print("OK: naming check passed (no banned legacy name in markdown docs).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
