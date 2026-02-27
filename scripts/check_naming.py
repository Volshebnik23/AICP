#!/usr/bin/env python3
"""Enforce canonical AICP naming and taxonomy terms in markdown docs."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BANNED_TERMS = [
    "AI Interconnector Protocol",
    "AMENDMENT_PROPOSE",
    "AMENDMENT_ACCEPT",
]
SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__"}


def should_skip(path: Path) -> bool:
    return any(part in SKIP_DIRS for part in path.parts)


def main() -> int:
    failures: list[tuple[Path, int, str, str]] = []
    for path in sorted(ROOT.rglob("*.md")):
        if should_skip(path):
            continue
        text = path.read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), start=1):
            for term in BANNED_TERMS:
                if term in line:
                    failures.append((path, line_no, term, line.strip()))

    if failures:
        for path, line_no, term, line in failures:
            print(f"[FAIL] banned term '{term}' in {path.relative_to(ROOT)}:{line_no}: {line}")
        print("\nNaming/taxonomy check failed.")
        return 1

    print("OK: naming/taxonomy check passed (no banned legacy terms in markdown docs).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
