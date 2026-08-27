"""Fail-closed client for the Pairwise 1.3 frozen side/Core authority process."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
BRIDGE = HERE / "pairwise_authority_bridge_v1_3.py"
BUNDLE = HERE / "pairwise_side_authority_bundle_v1_3.json"
TEXT_SUFFIXES = {".json", ".jsonl", ".md", ".py", ".ts", ".mjs", ".yml", ".yaml"}
_CACHE: dict[str, dict[str, Any]] = {}


def _digest(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix.lower() in TEXT_SUFFIXES:
        data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def verify_frozen_authority_bundle(*, bundle_path: Path | None = None) -> None:
    path = Path(bundle_path or BUNDLE)
    bundle = json.loads(path.read_text(encoding="utf-8"))
    entries = bundle.get("entries")
    if bundle.get("release_id") != "AICP-PAIRWISE-TCK-1.3.0" or not isinstance(entries, list):
        raise RuntimeError("Pairwise 1.3 frozen side-authority bundle is malformed")
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise RuntimeError("Pairwise 1.3 frozen side-authority entry is malformed")
        target = (ROOT / entry["path"]).resolve()
        if not target.is_relative_to(ROOT.resolve()):
            raise RuntimeError("Pairwise 1.3 frozen side-authority path escaped the repository")
        if not target.is_file() or _digest(target) != entry.get("digest"):
            raise RuntimeError(f"Pairwise 1.3 frozen side-authority drift: {entry['path']}")


def _invoke(request: dict[str, Any]) -> dict[str, Any]:
    verify_frozen_authority_bundle()
    cache_key = hashlib.sha256(
        json.dumps(request, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    cached = _CACHE.get(cache_key)
    if cached is not None:
        return cached
    result = subprocess.run(
        [sys.executable, "-X", "utf8", str(BRIDGE)],
        input=json.dumps(request, ensure_ascii=False),
        text=True,
        encoding="utf-8",
        capture_output=True,
        shell=False,
        timeout=30,
        cwd=HERE.parents[1],
    )
    if result.returncode != 0:
        raise RuntimeError(f"frozen authority bridge failed: {result.stderr or result.stdout}")
    response = json.loads(result.stdout)
    if response.get("ok") is not True or not isinstance(response.get("result"), dict):
        raise RuntimeError(f"frozen authority bridge rejected its request: {response.get('error')}")
    _CACHE[cache_key] = response["result"]
    return response["result"]


def evaluate_side_report(
    report: dict[str, Any],
    *,
    kind: str,
    identity: dict[str, Any],
) -> list[str]:
    result = _invoke({"operation": "side", "kind": kind, "report": report, "identity": identity})
    errors = result.get("errors")
    if not isinstance(errors, list) or not all(isinstance(item, str) for item in errors):
        raise RuntimeError("frozen side authority returned malformed errors")
    return errors


def validate_core_transcript(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = _invoke({"operation": "core", "messages": messages})
    errors = result.get("errors")
    if not isinstance(errors, list) or not all(isinstance(item, dict) for item in errors):
        raise RuntimeError("frozen Core authority returned malformed errors")
    return errors


def frozen_hash(object_type: str, value: Any) -> dict[str, Any]:
    return _invoke({"operation": "hash", "object_type": object_type, "value": value})
