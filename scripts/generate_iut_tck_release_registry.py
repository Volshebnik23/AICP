#!/usr/bin/env python3
from __future__ import annotations

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


def _artifact(path_ref: str) -> dict[str, str]:
    return {
        "path": path_ref,
        "content_digest": normalized_file_digest(ROOT / path_ref),
    }


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
    return {
        "registry_version": "1.0",
        "releases": [
            {
                "release_id": catalog["tck_release_id"],
                "status": "experimental-post-uat",
                "case_catalog": _artifact("conformance/iut/cases.json"),
                "runner_bundle": {
                    "paths": bundle_paths,
                    "digest": bundle_digest(bundle_paths),
                },
                "profiles": profiles,
            }
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
