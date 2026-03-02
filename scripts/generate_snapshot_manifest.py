#!/usr/bin/env python3
"""Generate deterministic snapshot manifest for shipped protocol artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "dist/releases/snapshots/AICP_SNAPSHOT_0.1.0-dev.json"


def _sha256_file(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix in {".json", ".jsonl", ".md"}:
        data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(data).hexdigest()


def _collect_files(patterns: list[str], exclude_predicate: Any | None = None) -> list[dict[str, str]]:
    rel_paths: set[Path] = set()
    for pattern in patterns:
        rel_paths.update(path.relative_to(ROOT) for path in ROOT.glob(pattern) if path.is_file())

    files: list[dict[str, str]] = []
    for rel_path in sorted(rel_paths, key=lambda p: str(p)):
        if exclude_predicate is not None and exclude_predicate(rel_path):
            continue
        files.append({"path": str(rel_path), "sha256": _sha256_file(ROOT / rel_path)})
    return files


def _combined_sha256(files: list[dict[str, str]]) -> str:
    payload = "".join(f"{item['sha256']} {item['path']}\n" for item in files)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_compatibility_marks() -> dict[str, list[dict[str, str]]]:
    suite_marks: list[dict[str, str]] = []
    for path in sorted((ROOT / "conformance").glob("**/*.json"), key=lambda p: str(p.relative_to(ROOT))):
        rel = path.relative_to(ROOT)
        if rel.parts[:2] == ("conformance", "profiles"):
            continue
        payload = _load_json(path)
        if isinstance(payload, dict) and isinstance(payload.get("compatibility_mark"), str):
            suite_marks.append({"path": str(rel), "mark": payload["compatibility_mark"]})

    profile_marks: list[dict[str, str]] = []
    for path in sorted((ROOT / "conformance/profiles").glob("*.json"), key=lambda p: str(p.relative_to(ROOT))):
        rel = path.relative_to(ROOT)
        payload = _load_json(path)
        if isinstance(payload, dict) and isinstance(payload.get("compatibility_mark"), str):
            profile_marks.append({"path": str(rel), "mark": payload["compatibility_mark"]})

    return {"suites": suite_marks, "profiles": profile_marks}


def build_manifest() -> dict[str, Any]:
    registries = _collect_files(["registry/*.json"])
    schemas = _collect_files(["schemas/**/*.json"])
    conformance = _collect_files(
        ["conformance/**/*.json"],
        exclude_predicate=lambda rel: rel.name.startswith("report") and rel.parent == Path("conformance"),
    )
    fixtures = _collect_files(["fixtures/**/*.json", "fixtures/**/*.jsonl"])

    return {
        "snapshot_id": "AICP-SNAPSHOT-0.1.0-dev",
        "manifest_version": 1,
        "artifact_sets": {
            "registries": {"files": registries, "combined_sha256": _combined_sha256(registries)},
            "schemas": {"files": schemas, "combined_sha256": _combined_sha256(schemas)},
            "conformance": {"files": conformance, "combined_sha256": _combined_sha256(conformance)},
            "fixtures": {"files": fixtures, "combined_sha256": _combined_sha256(fixtures)},
        },
        "compatibility_marks": _extract_compatibility_marks(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(DEFAULT_OUT), help="Output manifest path")
    args = parser.parse_args()

    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = ROOT / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)

    manifest = build_manifest()
    out_path.write_text(json.dumps(manifest, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Generated snapshot manifest: {out_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
