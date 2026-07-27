#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
IUT_DIR = ROOT / "conformance/iut"
if str(IUT_DIR) not in sys.path:
    sys.path.insert(0, str(IUT_DIR))

from aicp_iut_catalog import (  # noqa: E402
    CASES_PATH,
    TCK_RELEASES_PATH,
    bundle_digest,
    normalized_file_digest,
    required_input_paths,
    runner_bundle_paths,
)

FROZEN_RELEASE_DIGESTS = {
    "AICP-IUT-TCK-1.0.0": (
        "sha256:75fe5664bfc12d6fcee5ac80638fd9e04d0a188df25bc33ff12163eb246f4e9b"
    ),
}


def _artifact(path_ref: str) -> dict[str, str]:
    return {
        "path": path_ref,
        "content_digest": normalized_file_digest(ROOT / path_ref),
    }


def _release_digest(release: dict[str, Any]) -> str:
    canonical = json.dumps(
        release,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(canonical).hexdigest()


def _historical_releases(current_release_id: str) -> list[dict[str, Any]]:
    if not TCK_RELEASES_PATH.is_file():
        raise FileNotFoundError(
            "the checked-in TCK registry is required to preserve historical releases"
        )
    registry = json.loads(TCK_RELEASES_PATH.read_text(encoding="utf-8"))
    historical = [
        release
        for release in registry.get("releases", [])
        if isinstance(release, dict)
        and release.get("release_id") != current_release_id
    ]
    for release in historical:
        release_id = release.get("release_id")
        expected_digest = FROZEN_RELEASE_DIGESTS.get(str(release_id))
        if expected_digest is None:
            raise ValueError(
                f"historical TCK release {release_id!r} has no frozen digest"
            )
        if _release_digest(release) != expected_digest:
            raise ValueError(
                f"historical TCK release {release_id!r} does not match its frozen digest"
            )
    return sorted(historical, key=lambda item: str(item["release_id"]))


def build_registry() -> dict[str, Any]:
    catalog = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    bundle_paths = runner_bundle_paths()
    profiles: dict[str, Any] = {}
    for profile, config in catalog["profiles"].items():
        profiles[profile] = {
            "profile_catalog": _artifact(config["profile_catalog"]),
            "required_suites": [_artifact(path) for path in config["required_suites"]],
            "required_input_artifacts": [
                _artifact(path) for path in required_input_paths(catalog, profile)
            ],
        }
    current_release = {
        "release_id": catalog["tck_release_id"],
        "status": "experimental-post-uat",
        "case_catalog": _artifact("conformance/iut/cases.json"),
        "runner_bundle": {
            "paths": bundle_paths,
            "digest": bundle_digest(bundle_paths),
        },
        "profiles": profiles,
    }
    return {
        "registry_version": "1.0",
        "releases": [
            *_historical_releases(str(catalog["tck_release_id"])),
            current_release,
        ],
    }


def main() -> int:
    registry = build_registry()
    TCK_RELEASES_PATH.write_text(
        json.dumps(registry, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Generated {TCK_RELEASES_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
