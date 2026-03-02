#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    from jsonschema import Draft202012Validator
except Exception:
    Draft202012Validator = None

ROOT = Path(__file__).resolve().parents[1]


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    if Draft202012Validator is None:
        print("[WARN] jsonschema is not installed. Skipping binding case instance validation.")
        return 0

    suites = sorted((ROOT / 'conformance/bindings').glob('*.json'))
    errors = 0
    validated = 0
    for suite_path in suites:
        suite = _load(suite_path)
        suite_id = suite.get('suite_id', str(suite_path))
        schema_ref = suite.get('schema_ref')
        cases = suite.get('cases', [])
        if not isinstance(schema_ref, str):
            continue
        schema = _load(ROOT / schema_ref)
        validator = Draft202012Validator(schema)
        for case_ref in cases:
            case_path = ROOT / case_ref
            case_obj = _load(case_path)
            validated += 1
            for err in sorted(validator.iter_errors(case_obj), key=lambda e: list(e.path)):
                print(f"[FAIL] {suite_id} {case_ref}: {err.message}")
                errors += 1
    if errors:
        print(f"Binding case validation failed with {errors} error(s) across {validated} case(s).")
        return 1
    print(f"OK: binding case instances validated ({validated} case(s)).")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
