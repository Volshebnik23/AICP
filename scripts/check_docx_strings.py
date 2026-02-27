#!/usr/bin/env python3
"""Check banned legacy strings in canonical DOCX artifacts."""

from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile
import sys

ROOT = Path(__file__).resolve().parents[1]
DOCX_PATH = ROOT / "docs/core/AICP_Core_v0.1_Normative_0.1.0.docx"
BANNED = "Agent Interconnector Protocol"


def main() -> int:
    if not DOCX_PATH.exists():
        print(f"[FAIL] missing DOCX: {DOCX_PATH.relative_to(ROOT)}")
        return 1

    hits: list[str] = []
    with ZipFile(DOCX_PATH) as zf:
        for name in zf.namelist():
            if not name.endswith('.xml'):
                continue
            text = zf.read(name).decode('utf-8', errors='ignore')
            if BANNED in text:
                hits.append(name)

    if hits:
        print(f"[FAIL] banned legacy term '{BANNED}' found in {DOCX_PATH.relative_to(ROOT)}:")
        for name in hits:
            print(f" - {name}")
        return 1

    print("OK: DOCX terminology check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
