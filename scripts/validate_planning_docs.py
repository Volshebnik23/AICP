#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKLOG = ROOT / "AICP_Backlog"
ROADMAP = ROOT / "ROADMAP.md"

BANNED_PHRASES = [
    "Historical problem statement",
    "Current shipped baseline",
    "Shipped in v81 baseline",
    "v90",
    "v88",
]

PLANNING_FRAMING_TOKENS = [
    "planning-only",
    "remaining deliverables",
]

CYCLE_LABEL_RE = re.compile(r"\bv(?:88|90)\b", re.IGNORECASE)


def _load(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"missing required file: {path}")
    return path.read_text(encoding="utf-8")


def _headers_with_cycles(text: str) -> list[str]:
    matches: list[str] = []
    for line in text.splitlines():
        if line.startswith("#") and CYCLE_LABEL_RE.search(line):
            matches.append(line.strip())
    return matches


def main() -> int:
    errors: list[str] = []
    backlog = _load(BACKLOG)
    roadmap = _load(ROADMAP)

    for phrase in BANNED_PHRASES:
        if phrase in backlog:
            errors.append(f"AICP_Backlog contains banned phrase: '{phrase}'")

    top = "\n".join(backlog.splitlines()[:40]).lower()
    for token in PLANNING_FRAMING_TOKENS:
        if token not in top:
            errors.append(f"AICP_Backlog top framing must include '{token}'")

    backlog_cycle_headers = _headers_with_cycles(backlog)
    roadmap_cycle_headers = _headers_with_cycles(roadmap)
    if backlog_cycle_headers:
        errors.append(
            "AICP_Backlog contains disallowed cycle labels in planning headers: "
            + "; ".join(backlog_cycle_headers)
        )
    if roadmap_cycle_headers:
        errors.append(
            "ROADMAP.md contains disallowed cycle labels in planning headers: "
            + "; ".join(roadmap_cycle_headers)
        )

    if errors:
        print("[FAIL] planning-doc validation failed")
        for error in errors:
            print(f" - {error}")
        return 1

    print("OK: planning-doc validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
