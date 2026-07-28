#!/usr/bin/env python3
from __future__ import annotations

import sys
import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER_DIR = ROOT / "conformance" / "runner"
if str(RUNNER_DIR) not in sys.path:
    sys.path.insert(0, str(RUNNER_DIR))

from _suite_catalog import catalog_names, catalog_pairs  # noqa: E402


def main() -> int:
    errors: list[str] = []
    report_paths: set[str] = set()
    input_paths: set[str] = set()

    for catalog in catalog_names():
        for kind, pairs in catalog_pairs(catalog):
            for input_ref, out_ref in pairs:
                input_path = ROOT / input_ref
                if not input_path.exists():
                    errors.append(f"{catalog}:{kind} input does not exist: {input_ref}")

                if input_ref in input_paths:
                    errors.append(f"duplicate conformance catalog input: {input_ref}")
                input_paths.add(input_ref)

                if out_ref in report_paths:
                    errors.append(f"duplicate conformance report output: {out_ref}")
                report_paths.add(out_ref)

                if not out_ref.startswith("conformance/report_") and out_ref != "conformance/report.json":
                    errors.append(f"{catalog}:{kind} output must be a conformance report path: {out_ref}")

    versioned = runpy.run_path(
        str(ROOT / "conformance/core_v02_runner/catalog.py")
    )
    for kind, key in (("suite", "SUITE_CATALOGS"), ("profile", "PROFILE_CATALOGS")):
        for input_ref, out_ref in versioned[key]:
            input_path = ROOT / input_ref
            if not input_path.exists():
                errors.append(f"core-v02:{kind} input does not exist: {input_ref}")
            if input_ref in input_paths:
                errors.append(f"duplicate conformance catalog input: {input_ref}")
            input_paths.add(input_ref)
            if out_ref in report_paths:
                errors.append(f"duplicate conformance report output: {out_ref}")
            report_paths.add(out_ref)
            if not out_ref.startswith("conformance/report_"):
                errors.append(
                    f"core-v02:{kind} output must be a conformance report path: {out_ref}"
                )

    if errors:
        print("[FAIL] conformance catalog validation failed")
        for error in errors:
            print(f" - {error}")
        return 1

    print(f"OK: conformance catalogs reference {len(input_paths)} input(s) and {len(report_paths)} report output(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
