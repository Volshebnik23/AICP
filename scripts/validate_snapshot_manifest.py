#!/usr/bin/env python3
"""Validate deterministic snapshot manifest is current."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any

from generate_snapshot_manifest import DEFAULT_OUT, ROOT, build_manifest


def _git_head_sha() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "unknown"


def _normalize_text_bytes(path: Path, data: bytes) -> bytes:
    if path.suffix in {".json", ".jsonl", ".md"}:
        return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return data


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _collect_set_diff(name: str, expected: dict[str, Any], actual: dict[str, Any]) -> dict[str, Any]:
    exp_files = {f["path"]: f["sha256"] for f in expected.get("files", []) if isinstance(f, dict)}
    act_files = {f["path"]: f["sha256"] for f in actual.get("files", []) if isinstance(f, dict)}

    return {
        "name": name,
        "combined_expected": expected.get("combined_sha256"),
        "combined_actual": actual.get("combined_sha256"),
        "added": sorted(set(exp_files) - set(act_files)),
        "removed": sorted(set(act_files) - set(exp_files)),
        "changed": sorted(path for path in set(exp_files) & set(act_files) if exp_files[path] != act_files[path]),
        "expected_file_shas": exp_files,
        "actual_file_shas": act_files,
    }


def _print_drift_diagnostics(diff: dict[str, Any]) -> None:
    crlf = bytes((13, 10))
    cr = bytes((13,))
    set_name = diff["name"]
    exp_map: dict[str, str] = diff["expected_file_shas"]
    act_map: dict[str, str] = diff["actual_file_shas"]

    for rel_path in diff["changed"]:
        path = ROOT / rel_path
        file_bytes = path.read_bytes() if path.exists() else b""
        raw_sha = _sha256_bytes(file_bytes)
        normalized_sha = _sha256_bytes(_normalize_text_bytes(path, file_bytes))
        has_crlf = crlf in file_bytes
        has_cr = cr in file_bytes
        print(f"    [{set_name}] {rel_path}")
        print(f"      manifest sha256   : {act_map.get(rel_path)}")
        print(f"      computed sha256   : {exp_map.get(rel_path)}")
        print(f"      raw sha256        : {raw_sha}")
        print(f"      normalized sha256 : {normalized_sha}")
        print(f"      contains CRLF     : {has_crlf}")
        print(f"      contains CR       : {has_cr}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default=str(DEFAULT_OUT), help="Snapshot manifest path")
    args = parser.parse_args()

    print(f"[INFO] validate_snapshot_manifest HEAD={_git_head_sha()}")
    print(f"[INFO] python={sys.version.splitlines()[0]}")
    print(f"[INFO] platform={platform.platform()}")

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
    diffs: list[dict[str, Any]] = []
    for set_name in ["registries", "schemas", "conformance", "fixtures"]:
        diff = _collect_set_diff(set_name, expected_sets.get(set_name, {}), actual_sets.get(set_name, {}))
        diffs.append(diff)

        if diff["combined_expected"] != diff["combined_actual"]:
            print(
                f"  - {set_name}.combined_sha256 mismatch: expected={diff['combined_expected']} actual={diff['combined_actual']}"
            )
        if diff["added"]:
            print(f"  - {set_name} missing paths in manifest: {', '.join(diff['added'])}")
        if diff["removed"]:
            print(f"  - {set_name} unexpected stale paths in manifest: {', '.join(diff['removed'])}")
        if diff["changed"]:
            print(f"  - {set_name} sha drift: {', '.join(diff['changed'])}")

    if expected.get("compatibility_marks") != actual.get("compatibility_marks"):
        print("  - compatibility_marks mismatch")

    if expected.get("snapshot_id") != actual.get("snapshot_id"):
        print(f"  - snapshot_id mismatch: expected={expected.get('snapshot_id')} actual={actual.get('snapshot_id')}")
    if expected.get("manifest_version") != actual.get("manifest_version"):
        print(
            f"  - manifest_version mismatch: expected={expected.get('manifest_version')} actual={actual.get('manifest_version')}"
        )

    # Failure diagnostics for per-file byte differences.
    for diff in diffs:
        if diff["changed"]:
            _print_drift_diagnostics(diff)

    print("Fix: run `make snapshot` and commit updated manifest.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
