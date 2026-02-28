#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

CHECKS = [
    (
        ROOT / "schemas/core/aicp-core-message.schema.json",
        ROOT / "dropins/aicp-core/python/assets/schemas/core/aicp-core-message.schema.json",
    ),
    (
        ROOT / "schemas/core/aicp-core-message.schema.json",
        ROOT / "dropins/aicp-core/typescript/assets/schemas/core/aicp-core-message.schema.json",
    ),
    (
        ROOT / "registry/message_types.json",
        ROOT / "dropins/aicp-core/python/assets/registry/message_types.json",
    ),
    (
        ROOT / "registry/message_types.json",
        ROOT / "dropins/aicp-core/typescript/assets/registry/message_types.json",
    ),
]


def canonical_json(path: Path) -> str:
    data = json.loads(path.read_text(encoding="utf-8"))
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def main() -> int:
    mismatches: list[str] = []

    for source, copied in CHECKS:
        if not source.exists():
            mismatches.append(f"missing canonical file: {rel(source)}")
            continue
        if not copied.exists():
            mismatches.append(f"missing drop-in file: {rel(copied)}")
            continue

        if canonical_json(source) != canonical_json(copied):
            mismatches.append(
                f"mismatch: {rel(copied)} differs from canonical source {rel(source)}"
            )

    if mismatches:
        for item in mismatches:
            print(f"[FAIL] {item}")
        print(f"Drop-in asset validation failed with {len(mismatches)} mismatch(es).")
        return 1

    print("OK: drop-in assets match canonical schemas/registries.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
