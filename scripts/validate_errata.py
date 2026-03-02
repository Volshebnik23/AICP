#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ERRATA = ROOT / "ERRATA.md"
ID_RE = re.compile(r"^ER-\d{4}$")
REQ = {"Area", "Description", "Impact", "Status"}
ALLOWED = {"open", "in_progress", "fixed", "wont_fix"}


def _entries(lines: list[str]) -> list[dict[str, str]]:
    entries = []
    current: dict[str, str] = {}
    for line in lines:
        m = re.match(r"- \*\*(.+?):\*\*\s*(.*)$", line.strip())
        if not m:
            continue
        key, value = m.group(1).strip(), m.group(2).strip()
        if key == "ID" and current:
            entries.append(current)
            current = {}
        current[key] = value
    if current:
        entries.append(current)
    return entries


def main() -> int:
    if not ERRATA.exists():
        print("[FAIL] ERRATA.md missing")
        return 1
    lines = ERRATA.read_text(encoding="utf-8").splitlines()
    if "## Entries" in lines:
        lines = lines[lines.index("## Entries") + 1 :]
    entries = _entries(lines)
    ids: set[str] = set()
    errs: list[str] = []
    for idx, entry in enumerate(entries, start=1):
        eid = entry.get("ID", "")
        if not ID_RE.match(eid):
            errs.append(f"entry {idx}: invalid ID '{eid}'")
        elif eid in ids:
            errs.append(f"entry {idx}: duplicate ID '{eid}'")
        ids.add(eid)
        missing = sorted(k for k in REQ if not entry.get(k))
        if missing:
            errs.append(f"entry {eid or idx}: missing required fields: {', '.join(missing)}")
        status = entry.get("Status", "")
        if status and status not in ALLOWED:
            errs.append(f"entry {eid or idx}: invalid Status '{status}'")
    if errs:
        print("[FAIL] errata validation failed")
        for e in errs:
            print(" -", e)
        return 1
    print(f"OK: errata validation passed ({len(entries)} entries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
