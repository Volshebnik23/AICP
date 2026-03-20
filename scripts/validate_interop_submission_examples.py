#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_PATH = ROOT / "interop/submissions/submission.schema.json"
EXAMPLES_DIR = ROOT / "interop/submissions/examples"
REGISTRY_PATH = ROOT / "registry/aicp_profiles.json"
ALLOWED_CLAIM_TYPES = {
    "reproducibly_evidenced_profile_implementation",
    "pairwise_profile_interop",
}


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _fallback_validate(instance: Any) -> list[str]:
    errors: list[str] = []
    if not isinstance(instance, dict):
        return ["manifest must be a JSON object"]

    required = [
        "submission_id",
        "implementation_id",
        "implementation_version",
        "profile_ids",
        "claim_type",
        "claim_scope",
        "evidence_types",
        "suite_refs",
        "report_refs",
        "generated_at",
        "disclosures",
    ]
    for key in required:
        if key not in instance:
            errors.append(f"missing required field '{key}'")

    claim_type = instance.get("claim_type")
    if claim_type not in ALLOWED_CLAIM_TYPES:
        errors.append(f"claim_type must be one of {sorted(ALLOWED_CLAIM_TYPES)}")

    if claim_type == "pairwise_profile_interop" and not isinstance(instance.get("peer_implementation_id"), str):
        errors.append("peer_implementation_id is required for pairwise_profile_interop")

    if claim_type == "pairwise_profile_interop" and instance.get("claim_scope") != "pairwise":
        errors.append("claim_scope must be 'pairwise' for pairwise_profile_interop")

    if claim_type == "reproducibly_evidenced_profile_implementation" and instance.get("claim_scope") != "single_implementation":
        errors.append("claim_scope must be 'single_implementation' for reproducibly_evidenced_profile_implementation")

    return errors


def _schema_validate(schema: dict[str, Any], instance: Any) -> list[str]:
    try:
        from jsonschema import Draft202012Validator  # type: ignore
    except Exception:
        return _fallback_validate(instance)

    validator = Draft202012Validator(schema)
    errs = sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
    return [e.message for e in errs]


def main() -> int:
    schema = _load_json(SCHEMA_PATH)
    profile_registry = _load_json(REGISTRY_PATH)
    known_profiles = {entry["id"] for entry in profile_registry if isinstance(entry, dict) and isinstance(entry.get("id"), str)}

    manifests = sorted(EXAMPLES_DIR.glob("*/submission.json"))
    if not manifests:
        print("FAIL: no example interop submission manifests found")
        return 1

    failed = False
    for manifest_path in manifests:
        payload = _load_json(manifest_path)
        errors = _schema_validate(schema, payload)

        for profile_id in payload.get("profile_ids", []):
            if profile_id not in known_profiles:
                errors.append(f"unknown profile_id '{profile_id}' (not found in registry/aicp_profiles.json)")

        claim_type = payload.get("claim_type")
        if claim_type not in ALLOWED_CLAIM_TYPES:
            errors.append(f"unsupported claim_type '{claim_type}'")

        for ref_key in ("suite_refs", "report_refs"):
            for ref in payload.get(ref_key, []):
                ref_path = ROOT / ref
                if not isinstance(ref, str) or not ref.strip():
                    errors.append(f"{ref_key} entries must be non-empty strings")
                elif not ref_path.exists():
                    errors.append(f"{ref_key} reference does not exist: {ref}")

        if errors:
            failed = True
            print(f"FAIL: {manifest_path.relative_to(ROOT)}")
            for err in errors:
                print(f"  - {err}")
        else:
            print(f"OK: {manifest_path.relative_to(ROOT)}")

    if failed:
        return 1

    print(f"OK: validated {len(manifests)} interop submission example manifest(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
