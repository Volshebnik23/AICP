#!/usr/bin/env python3
"""Fail when current git diff contains binary-file extensions.

Intended to protect Codex PR creation flow from binary diffs.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

BANNED_EXTENSIONS = {".docx", ".pdf", ".png", ".jpg", ".jpeg", ".zip"}


def main() -> int:
    if shutil.which("git") is None:
        print("[WARN] git is not available; skipping binary diff check.")
        return 0

    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        print(f"[WARN] unable to run git diff; skipping binary diff check: {exc}")
        return 0

    changed = [Path(line.strip()) for line in result.stdout.splitlines() if line.strip()]
    offenders = [p for p in changed if p.suffix.lower() in BANNED_EXTENSIONS]

    if offenders:
        print("[FAIL] Binary-file changes detected in working diff:")
        for path in offenders:
            print(f" - {path}")
        print("Remove binary diffs before creating a PR.")
        return 1

    print("OK: no binary-file changes detected in current git diff.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
