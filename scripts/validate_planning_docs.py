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

PLANNING_FRAMING_TOKEN_GROUPS = [
    ["planning-only"],
    ["remaining deliverables", "remaining product deliverables"],
    ["roadmap.md"],
]

REMOVED_DELIVERED_MILESTONE_HEADERS = [
    "## M16",
    "## M17",
    "## M18",
    "## M19",
    "## M22",
]

CYCLE_LABEL_RE = re.compile(r"\bv(?:88|90)\b", re.IGNORECASE)
MILESTONE_SECTION_RE = re.compile(r"(?ms)^## M\d+\b.*?(?=^## M\d+\b|\Z)")
ROADMAP_CURRENT_NEXT_RE = re.compile(r"(?ms)^## Current / Next\s*\n(.*?)(?=^## |\Z)")
ROADMAP_PLANNED_RE = re.compile(r"(?ms)^## Planned milestones.*?\n(.*?)(?=^## |\Z)")
ROADMAP_M22_ENTRY_RE = re.compile(r"(?m)^###\s*[✅🚧⏳]?\s*M22\b")


def _load(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"missing required file: {path}")
    return path.read_text(encoding="utf-8")


def _headers_with_cycles(text: str) -> list[str]:
    return [
        line.strip()
        for line in text.splitlines()
        if line.startswith("#") and CYCLE_LABEL_RE.search(line)
    ]


def _roadmap_section(text: str, pattern: re.Pattern[str]) -> str:
    match = pattern.search(text)
    return match.group(1) if match else ""


def main() -> int:
    errors: list[str] = []
    backlog = _load(BACKLOG)
    roadmap = _load(ROADMAP)

    for phrase in BANNED_PHRASES:
        if phrase in backlog:
            errors.append(f"AICP_Backlog contains banned phrase: '{phrase}'")

    for header in REMOVED_DELIVERED_MILESTONE_HEADERS:
        if re.search(rf"(?m)^{re.escape(header)}\b", backlog):
            errors.append(f"AICP_Backlog must not include delivered milestone section header '{header}'")

    if "**Status:** Delivered" in backlog:
        errors.append("AICP_Backlog must not include delivered-status milestone markers")

    top = "\n".join(backlog.splitlines()[:25]).lower()
    for token_group in PLANNING_FRAMING_TOKEN_GROUPS:
        if not any(token in top for token in token_group):
            errors.append(
                "AICP_Backlog top framing must include one of: " + ", ".join(repr(token) for token in token_group)
            )

    milestone_headers = [line.strip() for line in backlog.splitlines() if line.startswith("## M")]
    if not milestone_headers:
        errors.append("AICP_Backlog must include at least one remaining milestone section")

    for section in MILESTONE_SECTION_RE.findall(backlog):
        if "**Status:** Delivered" in section:
            errors.append("Backlog milestone sections must not carry delivered-status ledger markers")
            break

    roadmap_current_next = _roadmap_section(roadmap, ROADMAP_CURRENT_NEXT_RE)
    roadmap_planned = _roadmap_section(roadmap, ROADMAP_PLANNED_RE)
    if roadmap_planned:
        if re.search(r"(?m)^.*✅.*\bM[0-9]", roadmap_planned):
            errors.append("ROADMAP.md must not include completed (✅) milestones under '## Planned milestones'")
        if re.search(r"(?m)^###\s*[✅🚧⏳]?\s*M16a\b", roadmap_planned):
            errors.append("ROADMAP.md must not list M16a under '## Planned milestones'")
        if re.search(r"(?m)^###\s*[✅🚧⏳]?\s*M17\.1\b", roadmap_planned):
            errors.append("ROADMAP.md must not list M17.1 under '## Planned milestones'")

    if roadmap_current_next and roadmap_planned:
        current_has_m22 = bool(ROADMAP_M22_ENTRY_RE.search(roadmap_current_next))
        planned_has_m22 = bool(ROADMAP_M22_ENTRY_RE.search(roadmap_planned))
        if current_has_m22 and planned_has_m22:
            errors.append("ROADMAP.md must not duplicate M22 under both '## Current / Next' and '## Planned milestones'")

    backlog_cycle_headers = _headers_with_cycles(backlog)
    roadmap_cycle_headers = _headers_with_cycles(roadmap)
    if backlog_cycle_headers:
        errors.append(
            "AICP_Backlog contains disallowed cycle labels in headers: "
            + "; ".join(backlog_cycle_headers)
        )
    if roadmap_cycle_headers:
        errors.append(
            "ROADMAP.md contains disallowed cycle labels in headers: "
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
