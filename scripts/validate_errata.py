#!/usr/bin/env python3
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ERRATA_PATH = ROOT / "ERRATA.md"
ID_RE = re.compile(r"^ER-\d{4}$")
STATUS_RE = re.compile(r"^(open|in_progress|fixed|wont_fix)$")


def main() -> int:
    if not ERRATA_PATH.exists():
        print(f"[FAIL] Missing {ERRATA_PATH.relative_to(ROOT)}")
        return 1

    lines = ERRATA_PATH.read_text(encoding="utf-8").splitlines()
    entries: list[dict[str, str]] = []
    cur: dict[str, str] | None = None
    in_entries = False
    for line in lines:
        if line.strip() == "## Entries":
            in_entries = True
            continue
        if not in_entries:
            continue
        stripped = line.strip()
        if stripped.startswith("- **ID:**"):
            if cur:
                entries.append(cur)
            cur = {"ID": stripped.split("**ID:**", 1)[1].strip()}
        elif cur is not None:
            for field in ("Area", "Description", "Impact", "Status"):
                key = f"- **{field}:**"
                if stripped.startswith(key):
                    cur[field] = stripped.split(key, 1)[1].strip()
    if cur:
        entries.append(cur)

    if not entries:
        print("[FAIL] No errata entries found.")
        return 1

    failures: list[str] = []
    seen_ids: set[str] = set()
    for idx, entry in enumerate(entries, start=1):
        err_id = entry.get("ID", "")
        if not ID_RE.match(err_id):
            failures.append(f"entry #{idx}: invalid ID '{err_id}' (expected ER-\\d{{4}})")
        if err_id in seen_ids:
            failures.append(f"entry #{idx}: duplicate ID '{err_id}'")
        seen_ids.add(err_id)
        for field in ("Area", "Description", "Impact", "Status"):
            if not entry.get(field):
                failures.append(f"entry {err_id or '#'+str(idx)}: missing required field {field}")
        status = entry.get("Status", "")
        if status and not STATUS_RE.match(status):
            failures.append(f"entry {err_id}: invalid Status '{status}'")

    if failures:
        print("[FAIL] ERRATA validation failed:")
        for f in failures:
            print(f"- {f}")
        return 1

    print(f"OK: ERRATA entries valid ({len(entries)} entries).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
