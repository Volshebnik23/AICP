#!/usr/bin/env python3
"""Validate AICP registry artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY_DIR = ROOT / "registry"

REQUIRED_FILES = [
    "message_types.json",
    "policy_categories.json",
    "crypto_profiles.json",
    "canonicalization_profiles.json",
    "hash_domains.json",
    "transport_bindings.json",
    "policy_reason_codes.json",
    "extension_ids.json",
    "security_alert_categories.json",
    "dispute_claim_types.json",
]

REQUIRED_FIELDS = {
    "id",
    "type",
    "status",
    "spec_ref",
    "introduced_in",
    "maintainer",
    "security_considerations",
}

ALLOWED_STATUS = {"experimental", "stable", "deprecated", "withdrawn"}


def fail(msg: str) -> None:
    print(f"[FAIL] {msg}")


def main() -> int:
    errors = 0

    for name in REQUIRED_FILES:
        path = REGISTRY_DIR / name
        if not path.exists():
            fail(f"Missing required registry file: {path.relative_to(ROOT)}")
            errors += 1
            continue

        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            fail(f"Invalid JSON in {path.relative_to(ROOT)}: {exc}")
            errors += 1
            continue

        if not isinstance(data, list):
            fail(f"Registry file must be a JSON list: {path.relative_to(ROOT)}")
            errors += 1
            continue

        seen_ids: set[str] = set()
        for idx, entry in enumerate(data, start=1):
            ctx = f"{path.relative_to(ROOT)}[{idx}]"
            if not isinstance(entry, dict):
                fail(f"{ctx} must be an object")
                errors += 1
                continue

            missing = sorted(REQUIRED_FIELDS - set(entry.keys()))
            if missing:
                fail(f"{ctx} missing required fields: {', '.join(missing)}")
                errors += 1

            entry_id = entry.get("id")
            if not isinstance(entry_id, str) or not entry_id.strip():
                fail(f"{ctx}.id must be a non-empty string")
                errors += 1
            elif entry_id in seen_ids:
                fail(f"{ctx}.id duplicates prior id '{entry_id}' in same registry")
                errors += 1
            else:
                seen_ids.add(entry_id)

            status = entry.get("status")
            if status not in ALLOWED_STATUS:
                fail(f"{ctx}.status must be one of: {', '.join(sorted(ALLOWED_STATUS))}")
                errors += 1

            introduced_in = entry.get("introduced_in")
            if not isinstance(introduced_in, str) or not introduced_in.strip():
                fail(f"{ctx}.introduced_in must be a non-empty string")
                errors += 1

            spec_ref = entry.get("spec_ref")
            if not isinstance(spec_ref, str) or not spec_ref.strip():
                fail(f"{ctx}.spec_ref must be a non-empty string")
                errors += 1
            else:
                spec_path = spec_ref.split("#", 1)[0]
                target = ROOT / spec_path
                if not target.exists():
                    fail(f"{ctx}.spec_ref path does not exist: {spec_path}")
                    errors += 1

    if errors:
        print(f"\nRegistry validation failed with {errors} error(s).")
        return 1

    print(f"OK: validated {len(REQUIRED_FILES)} registry file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
