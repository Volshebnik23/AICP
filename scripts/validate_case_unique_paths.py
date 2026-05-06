#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys


def main() -> int:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    paths = [raw.decode("utf-8") for raw in result.stdout.split(b"\0") if raw]

    seen: dict[str, str] = {}
    collisions: list[tuple[str, str]] = []
    for path in paths:
        folded = path.casefold()
        previous = seen.get(folded)
        if previous is not None and previous != path:
            collisions.append((previous, path))
        else:
            seen[folded] = path

    if collisions:
        print("[FAIL] case-only path collisions detected")
        for left, right in collisions:
            print(f" - {left} <-> {right}")
        return 1

    print(f"OK: {len(paths)} tracked path(s) are case-unique.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
