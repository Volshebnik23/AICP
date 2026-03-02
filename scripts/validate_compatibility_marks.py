#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXT_REGISTRY = ROOT / "registry/extension_ids.json"
SUITE_GLOBS = [
    ROOT / "conformance/core/*.json",
    ROOT / "conformance/extensions/*.json",
]
MARK_RE = re.compile(r"^AICP-EXT-(?P<name>.+)-(?P<version>\d[0-9A-Za-z.-]*)$")


def load_extension_ids() -> set[str]:
    with EXT_REGISTRY.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    return {entry["id"] for entry in payload if isinstance(entry, dict) and entry.get("id", "").startswith("EXT-")}


def main() -> int:
    extension_ids = load_extension_ids()
    failures: list[str] = []

    suite_paths: list[Path] = []
    for pattern in SUITE_GLOBS:
        suite_paths.extend(sorted(ROOT.glob(pattern.relative_to(ROOT).as_posix())))

    for suite_path in suite_paths:
        with suite_path.open("r", encoding="utf-8") as f:
            suite = json.load(f)
        mark = suite.get("compatibility_mark")
        if not isinstance(mark, str) or not mark.startswith("AICP-EXT-"):
            continue

        m = MARK_RE.match(mark)
        if not m:
            failures.append(
                f"{suite_path.relative_to(ROOT)}: compatibility_mark '{mark}' is malformed. "
                "Expected pattern AICP-EXT-<EXT_NAME>-<version>."
            )
            continue

        ext_id = f"EXT-{m.group('name')}"
        if ext_id not in extension_ids:
            failures.append(
                f"{suite_path.relative_to(ROOT)}: compatibility_mark '{mark}' references missing extension id '{ext_id}'. "
                "Fix by registering the extension in registry/extension_ids.json or renaming the mark to a non-extension prefix (e.g., AICP-SUITE-*)."
            )

    if failures:
        print("FAIL: compatibility mark validation failed:")
        for item in failures:
            print(f"- {item}")
        return 1

    print("OK: compatibility marks with AICP-EXT-* map to registered extension IDs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
