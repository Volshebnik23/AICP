#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
VERSION_FILE = ROOT / 'VERSION'
RELEASE_NOTES = ROOT / 'RELEASE_NOTES.md'
CHANGELOG = ROOT / 'CHANGELOG.md'
PACKAGE_JSON = ROOT / 'sdk' / 'typescript' / 'package.json'
PACKAGE_LOCK = ROOT / 'sdk' / 'typescript' / 'package-lock.json'


HEADER_RE = re.compile(r'^##\s+(?:\[)?(?P<version>[0-9][^\]\s]*)', re.MULTILINE)


def _read_text(path: Path) -> str:
    return path.read_text(encoding='utf-8')


def _load_json(path: Path) -> Any:
    with path.open('r', encoding='utf-8') as handle:
        return json.load(handle)


def _extract_target_version(path: Path) -> str | None:
    match = HEADER_RE.search(_read_text(path))
    if match:
        return match.group('version')
    return None


def main() -> int:
    expected_version = _read_text(VERSION_FILE).strip()
    errors: list[str] = []

    package_json = _load_json(PACKAGE_JSON)
    package_lock = _load_json(PACKAGE_LOCK)

    package_json_version = package_json.get('version')
    package_lock_version = package_lock.get('version')
    package_lock_root_version = package_lock.get('packages', {}).get('', {}).get('version')

    if package_json_version != expected_version:
        errors.append(
            f"sdk/typescript/package.json version mismatch: expected '{expected_version}', found '{package_json_version}'"
        )
    if package_lock_version != expected_version:
        errors.append(
            f"sdk/typescript/package-lock.json version mismatch: expected '{expected_version}', found '{package_lock_version}'"
        )
    if package_lock_root_version != expected_version:
        errors.append(
            "sdk/typescript/package-lock.json packages[''] version mismatch: "
            f"expected '{expected_version}', found '{package_lock_root_version}'"
        )

    release_notes_version = _extract_target_version(RELEASE_NOTES)
    if release_notes_version != expected_version:
        errors.append(
            f"RELEASE_NOTES.md target version mismatch: expected '{expected_version}', found '{release_notes_version}'"
        )

    changelog_version = _extract_target_version(CHANGELOG)
    if changelog_version != expected_version:
        errors.append(
            f"CHANGELOG.md target version mismatch: expected '{expected_version}', found '{changelog_version}'"
        )

    if errors:
        print('[FAIL] release metadata consistency check failed')
        for error in errors:
            print(f' - {error}')
        return 1

    print(f"OK: release metadata is consistent for version {expected_version}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
