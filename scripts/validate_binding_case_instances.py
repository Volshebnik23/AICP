#!/usr/bin/env python3
"""Validate binding case JSON fixtures against each binding suite schema_ref."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BINDING_SUITES = ROOT / "conformance" / "bindings"


def main() -> int:
    try:
        from jsonschema import Draft202012Validator
    except Exception:  # noqa: BLE001
        print("[WARN] jsonschema is not installed. Skipping binding case schema validation.")
        return 0

    errors = 0
    suite_paths = sorted(BINDING_SUITES.glob("*.json"))

    for suite_path in suite_paths:
        suite = json.loads(suite_path.read_text(encoding="utf-8"))
        suite_id = suite.get("suite_id", suite_path.stem)
        schema_ref = suite.get("schema_ref")
        if not isinstance(schema_ref, str) or not schema_ref:
            print(f"[FAIL] {suite_id} {suite_path.relative_to(ROOT)}: missing schema_ref")
            errors += 1
            continue

        schema_path = ROOT / schema_ref
        if not schema_path.exists():
            print(f"[FAIL] {suite_id} {schema_ref}: schema_ref path does not exist")
            errors += 1
            continue

        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)

        for case_rel in suite.get("cases", []):
            case_path = ROOT / case_rel
            try:
                case_obj = json.loads(case_path.read_text(encoding="utf-8"))
            except Exception as exc:  # noqa: BLE001
                print(f"[FAIL] {suite_id} {case_rel}: invalid JSON ({exc})")
                errors += 1
                continue

            for err in sorted(validator.iter_errors(case_obj), key=lambda issue: list(issue.path)):
                print(f"[FAIL] {suite_id} {case_rel}: {err.message}")
                errors += 1

    if errors:
        print(f"Binding case schema validation failed with {errors} error(s).")
        return 1

    print(f"OK: validated binding case instances for {len(suite_paths)} suite(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
