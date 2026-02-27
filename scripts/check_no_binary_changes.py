#!/usr/bin/env python3
"""Fail when git diff contains binary-file extensions.

Prefers PR-relevant comparison (origin/main...HEAD) when available.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

BANNED_EXTENSIONS = {".docx", ".pdf", ".png", ".jpg", ".jpeg", ".zip"}


def _run_git_diff_name_only(args: list[str]) -> list[Path] | None:
    try:
        result = subprocess.run(["git", *args], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError:
        return None
    return [Path(line.strip()) for line in result.stdout.splitlines() if line.strip()]


def main() -> int:
    if shutil.which("git") is None:
        print("[WARN] git is not available; skipping binary diff check.")
        return 0

    changed = None
    # Prefer PR-style diff if origin/main exists locally.
    if _run_git_diff_name_only(["rev-parse", "--verify", "origin/main"]) is not None:
        changed = _run_git_diff_name_only(["diff", "--name-only", "origin/main...HEAD"])
        if changed is not None:
            print("[INFO] binary check against origin/main...HEAD")

    if changed is None:
        changed = _run_git_diff_name_only(["diff", "--name-only", "HEAD"])
        if changed is None:
            print("[WARN] unable to run git diff; skipping binary diff check.")
            return 0
        print("[INFO] binary check fallback against HEAD")

    offenders = [p for p in changed if p.suffix.lower() in BANNED_EXTENSIONS]

    if offenders:
        print("[FAIL] Binary-file changes detected in git diff:")
        for path in offenders:
            print(f" - {path}")
        print("Remove binary diffs before creating a PR.")
        return 1

    print("OK: no binary-file changes detected in relevant git diff.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
