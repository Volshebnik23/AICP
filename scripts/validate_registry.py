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
    "privacy_modes.json",
    "policy_languages.json",
    "policy_bindings.json",
    "extension_ids.json",
    "enforcement_sanction_codes.json",
    "security_alert_categories.json",
    "dispute_claim_types.json",
    "alert_codes.json",
    "alert_recommended_actions.json",
    "aicp_profiles.json",
    "capneg_reason_codes.json",
    "channel_properties.json",
    "trust_signal_types.json",
    "attestation_types.json",
    "status_assertion_codes.json",
    "revocation_reason_codes.json",
    "responsibility_warranty_classes.json",
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
    version_marks: dict[str, str] = {}

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

            if status == "stable":
                compatibility_notes = entry.get("compatibility_notes")
                if not isinstance(compatibility_notes, str) or not compatibility_notes.strip():
                    fail(f"{ctx}.compatibility_notes must be a non-empty string for stable entries")
                    errors += 1
                if isinstance(spec_ref, str) and "#" not in spec_ref:
                    fail(f"{ctx}.spec_ref must include an anchor (#...) for stable entries")
                    errors += 1

            if status == "deprecated":
                deprecation_notes = entry.get("deprecation_notes")
                if not isinstance(deprecation_notes, str) or not deprecation_notes.strip():
                    fail(f"{ctx}.deprecation_notes must be a non-empty string for deprecated entries")
                    errors += 1
                if isinstance(spec_ref, str) and "#" not in spec_ref:
                    fail(f"{ctx}.spec_ref must include an anchor (#...) for deprecated entries")
                    errors += 1

            versions = entry.get("versions")
            if versions is not None:
                if name != "extension_ids.json":
                    fail(f"{ctx}.versions is only valid for extension registry entries")
                    errors += 1
                elif not isinstance(versions, list) or not versions:
                    fail(f"{ctx}.versions must be a non-empty list")
                    errors += 1
                else:
                    seen_versions: set[str] = set()
                    for version_index, version in enumerate(versions, start=1):
                        version_ctx = f"{ctx}.versions[{version_index}]"
                        if not isinstance(version, dict):
                            fail(f"{version_ctx} must be an object")
                            errors += 1
                            continue
                        required_version_fields = {
                            "version",
                            "status",
                            "normative_spec",
                            "payload_schema",
                            "conformance_suite",
                            "compatibility_mark",
                        }
                        missing_version_fields = sorted(
                            required_version_fields - set(version)
                        )
                        if missing_version_fields:
                            fail(
                                f"{version_ctx} missing required fields: "
                                + ", ".join(missing_version_fields)
                            )
                            errors += 1
                        exact_version = version.get("version")
                        if (
                            not isinstance(exact_version, str)
                            or not exact_version.strip()
                        ):
                            fail(f"{version_ctx}.version must be a non-empty string")
                            errors += 1
                        elif exact_version in seen_versions:
                            fail(
                                f"{version_ctx}.version duplicates prior version "
                                f"'{exact_version}'"
                            )
                            errors += 1
                        else:
                            seen_versions.add(exact_version)
                        if version.get("status") not in ALLOWED_STATUS:
                            fail(
                                f"{version_ctx}.status must be one of: "
                                + ", ".join(sorted(ALLOWED_STATUS))
                            )
                            errors += 1
                        for field in (
                            "normative_spec",
                            "payload_schema",
                            "conformance_suite",
                        ):
                            relative = version.get(field)
                            if (
                                not isinstance(relative, str)
                                or not relative
                                or not (ROOT / relative).is_file()
                            ):
                                fail(
                                    f"{version_ctx}.{field} must resolve to a file"
                                )
                                errors += 1
                        mark = version.get("compatibility_mark")
                        if not isinstance(mark, str) or not mark:
                            fail(
                                f"{version_ctx}.compatibility_mark must be non-empty"
                            )
                            errors += 1
                        elif mark in version_marks:
                            fail(
                                f"{version_ctx}.compatibility_mark duplicates "
                                f"{version_marks[mark]}"
                            )
                            errors += 1
                        else:
                            version_marks[mark] = version_ctx

                    if entry.get("id") == "EXT-CAPNEG":
                        expected_capneg_versions = [
                            {
                                "version": "0.1",
                                "status": "stable",
                                "normative_spec": "docs/extensions/RFC_EXT_CAPNEG.md",
                                "payload_schema": "schemas/extensions/ext-capneg-payloads.schema.json",
                                "conformance_suite": "conformance/extensions/CN_CAPNEG_0.1.json",
                                "compatibility_mark": "AICP-EXT-CAPNEG-0.1",
                            },
                            {
                                "version": "0.2",
                                "status": "experimental",
                                "normative_spec": "docs/extensions/RFC_EXT_CAPNEG_v0.2.md",
                                "payload_schema": "schemas/extensions/ext-capneg-v0.2-payloads.schema.json",
                                "conformance_suite": "conformance/extensions/CN_CAPNEG_0.2.json",
                                "compatibility_mark": "AICP-EXT-CAPNEG-0.2",
                            },
                        ]
                        if status != "stable":
                            fail(
                                f"{ctx}: EXT-CAPNEG top-level status must remain stable"
                            )
                            errors += 1
                        if versions != expected_capneg_versions:
                            fail(
                                f"{ctx}.versions must exactly pin stable v0.1 and "
                                "experimental v0.2 artifacts"
                            )
                            errors += 1

    if errors:
        print(f"\nRegistry validation failed with {errors} error(s).")
        return 1

    print(f"OK: validated {len(REQUIRED_FILES)} registry file(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
