#!/usr/bin/env python3
"""Fail on banned legacy message-type terms in markdown docs."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
BANNED = ("AMENDMENT_PROPOSE", "AMENDMENT_ACCEPT")


def main() -> int:
    offenders: list[tuple[Path, int, str]] = []
    for path in sorted(DOCS.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        for idx, line in enumerate(text.splitlines(), start=1):
            if any(term in line for term in BANNED):
                offenders.append((path.relative_to(ROOT), idx, line.strip()))

    if offenders:
        print("[FAIL] banned legacy terms found:")
        for rel, idx, line in offenders:
            print(f" - {rel}:{idx}: {line}")
        return 1

    print("OK: no banned legacy message-type terms found in docs markdown.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
