#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
from m65_extension_semantics import (  # noqa: E402
    M65_SUITE_PATHS,
    extension_semantic_failures,
)


def main() -> int:
    failures = [
        failure
        for suite_path in M65_SUITE_PATHS
        for failure in extension_semantic_failures(ROOT / suite_path)
    ]
    if failures:
        for failure in failures:
            line = f":{failure['line']}" if failure.get("line") is not None else ""
            print(f"[FAIL] {failure['test_id']} {failure['file']}{line}: {failure['message']}")
        return 1
    print(f"[OK] M65 lifecycle semantics passed for {len(M65_SUITE_PATHS)} owning extension suites")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
