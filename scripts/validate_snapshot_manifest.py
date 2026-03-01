#!/usr/bin/env python3
"""Validate deterministic snapshot manifest is current."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from generate_snapshot_manifest import DEFAULT_OUT, ROOT, build_manifest


def _summarize_set_diff(name: str, expected: dict, actual: dict) -> list[str]:
    lines: list[str] = []
    if expected.get("combined_sha256") != actual.get("combined_sha256"):
        lines.append(
            f"  - {name}.combined_sha256 mismatch: expected={expected.get('combined_sha256')} actual={actual.get('combined_sha256')}"
        )

    exp_files = {f["path"]: f["sha256"] for f in expected.get("files", []) if isinstance(f, dict)}
    act_files = {f["path"]: f["sha256"] for f in actual.get("files", []) if isinstance(f, dict)}

    added = sorted(set(exp_files) - set(act_files))
    removed = sorted(set(act_files) - set(exp_files))
    changed = sorted(path for path in set(exp_files) & set(act_files) if exp_files[path] != act_files[path])

    if added:
        lines.append(f"  - {name} missing paths in manifest: {', '.join(added)}")
    if removed:
        lines.append(f"  - {name} unexpected stale paths in manifest: {', '.join(removed)}")
    if changed:
        lines.append(f"  - {name} sha drift: {', '.join(changed)}")

    return lines


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=str(DEFAULT_OUT), help="Snapshot manifest path")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    if not manifest_path.is_absolute():
        manifest_path = ROOT / manifest_path

    if not manifest_path.exists():
        print(f"[FAIL] snapshot manifest missing: {manifest_path.relative_to(ROOT)}")
        print("       Run `make snapshot` to generate it.")
        return 1

    expected = build_manifest()
    actual = json.loads(manifest_path.read_text(encoding="utf-8"))

    if actual == expected:
        print(f"OK: snapshot manifest is current: {manifest_path.relative_to(ROOT)}")
        return 0

    print("[FAIL] snapshot manifest is out of date.")
    expected_sets = expected.get("artifact_sets", {})
    actual_sets = actual.get("artifact_sets", {})
    for set_name in ["registries", "schemas", "conformance", "fixtures"]:
        lines = _summarize_set_diff(set_name, expected_sets.get(set_name, {}), actual_sets.get(set_name, {}))
        for line in lines:
            print(line)

    if expected.get("compatibility_marks") != actual.get("compatibility_marks"):
        print("  - compatibility_marks mismatch")

    if expected.get("snapshot_id") != actual.get("snapshot_id"):
        print(f"  - snapshot_id mismatch: expected={expected.get('snapshot_id')} actual={actual.get('snapshot_id')}")
    if expected.get("manifest_version") != actual.get("manifest_version"):
        print(
            f"  - manifest_version mismatch: expected={expected.get('manifest_version')} actual={actual.get('manifest_version')}"
        )

    print("Fix: run `make snapshot` and commit updated manifest.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
