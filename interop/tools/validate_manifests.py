#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

REQUIRED_STRING_FIELDS = [
    "implementation_id",
    "name",
    "language",
    "version",
    "maintainer",
    "contact",
]


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _fallback_validate(path: Path, obj: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(obj, dict):
        return ["manifest must be a JSON object"]
    for key in REQUIRED_STRING_FIELDS:
        if key not in obj:
            errors.append(f"missing required field '{key}'")
        elif not isinstance(obj.get(key), str):
            errors.append(f"field '{key}' must be a string")
    return errors


def validate_manifest(path: Path, schema: dict[str, Any]) -> list[str]:
    try:
        obj = _load_json(path)
    except Exception as exc:
        return [f"invalid JSON: {exc}"]

    try:
        from jsonschema import Draft202012Validator  # type: ignore
    except Exception:
        return _fallback_validate(path, obj)

    validator = Draft202012Validator(schema)
    errs = sorted(validator.iter_errors(obj), key=lambda e: list(e.path))
    return [e.message for e in errs]


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate interop implementation manifests against schema")
    parser.add_argument("--schema", required=True, help="Path to implementation manifest JSON schema")
    parser.add_argument("files", nargs="*", help="Manifest files to validate")
    args = parser.parse_args()

    schema_path = Path(args.schema)
    try:
        schema = _load_json(schema_path)
    except Exception as exc:
        print(f"[FAIL] could not load schema '{schema_path}': {exc}")
        return 1

    if not args.files:
        print("No manifest files provided; skipping.")
        return 0

    failed = False
    for f in args.files:
        path = Path(f)
        errors = validate_manifest(path, schema)
        if errors:
            failed = True
            print(f"[FAIL] {path}")
            for err in errors:
                print(f"  - {err}")
        else:
            print(f"[OK] {path}")

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
