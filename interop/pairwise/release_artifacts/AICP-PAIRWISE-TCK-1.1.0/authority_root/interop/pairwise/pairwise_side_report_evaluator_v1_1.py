"""Fail-closed access to the Pairwise 1.1 frozen side/Core authority bridge."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
BRIDGE = HERE / "pairwise_authority_bridge_v1_1.py"
_CACHE: dict[str, dict[str, Any]] = {}


def _invoke(request: dict[str, Any]) -> dict[str, Any]:
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
