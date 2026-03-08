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
]

CYCLE_LABEL_RE = re.compile(r"\bv(?:88|90)\b", re.IGNORECASE)
M22_HEADER_RE = re.compile(
    r"^## M22 — Transport bindings and channel properties \(HTTP/WS \+ anti-replay \+ quotas \+ streaming\)\s*$",
    re.MULTILINE,
)
MILESTONE_SECTION_RE = re.compile(
    r"(?ms)^## M\d+\b.*?(?=^## M\d+\b|\Z)",
)
M22_STALE_WORDING_PATTERNS = [
    re.compile(r"\btransport binding(?:s)?\b.{0,40}\bmissing\b", re.IGNORECASE),
    re.compile(r"\bbinding(?:s)?\b.{0,40}\bmissing\b", re.IGNORECASE),
    re.compile(r"\bhttp/ws\b.{0,40}\bmissing\b", re.IGNORECASE),
    re.compile(r"\bmajor\b.{0,40}\btransport\b.{0,40}\bmissing\b", re.IGNORECASE),
    re.compile(r"\bmajor\b.{0,40}\bbinding\b.{0,40}\bmissing\b", re.IGNORECASE),
]


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


def _m22_section(text: str) -> str | None:
    m22_start = M22_HEADER_RE.search(text)
    if not m22_start:
        return None
    start = m22_start.start()
    rest = text[m22_start.end() :]
    next_m = re.search(r"(?m)^## M\d+\b", rest)
    end = m22_start.end() + next_m.start() if next_m else len(text)
    return text[start:end]


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

    m22 = _m22_section(backlog)
    if not m22:
        errors.append("AICP_Backlog must include an M22 section")
    else:
        m22_lower = m22.lower()
        if "remaining gap" not in m22_lower:
            errors.append("M22 must explicitly describe a remaining gap")
        if "already-shipped" not in m22_lower and "shipped" not in m22_lower:
            errors.append("M22 must acknowledge shipped transport/binding foundations and focus on remaining work")
        for pattern in M22_STALE_WORDING_PATTERNS:
            if pattern.search(m22):
                errors.append(
                    "M22 contains stale wording that describes already-shipped transport/binding work as broadly missing"
                )
                break

    # enforce planning-only structure: milestone bodies should not include delivered-status style markers
    for section in MILESTONE_SECTION_RE.findall(backlog):
        if "**Status:** Delivered" in section:
            errors.append("Backlog milestone sections must not carry delivered-status ledger markers")
            break

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
