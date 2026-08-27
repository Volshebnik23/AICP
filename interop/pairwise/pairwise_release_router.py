#!/usr/bin/env python3
"""Route Pairwise reports through registry-declared immutable evaluators."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any, Callable


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
TEXT_SUFFIXES = {".json", ".jsonl", ".md", ".py", ".ts", ".mjs", ".yml", ".yaml"}
EVALUATOR_API = "evaluate_pairwise_report.v1"
REGISTRY_PATH = HERE / "tck_releases.json"


def _empty(status: str, code: str, message: str) -> dict[str, Any]:
    return {
        "status": status,
        "errors": [{"code": code, "message": message}],
        "eligible_pairwise_relations": [],
        "eligible_marks": [],
    }


def _digest(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix.lower() in TEXT_SUFFIXES:
        data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _load_registry(path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    registry = json.loads(path.read_text(encoding="utf-8"))
    releases = registry.get("releases")
    policies = registry.get("release_policies")
    if not isinstance(releases, list) or not isinstance(policies, list):
        raise ValueError("Pairwise registry requires release and policy arrays")
    release_map: dict[str, dict[str, Any]] = {}
    policy_map: dict[str, dict[str, Any]] = {}
    for item in releases:
        release_id = item.get("release_id") if isinstance(item, dict) else None
        if not isinstance(release_id, str) or not release_id or release_id in release_map:
            raise ValueError("Pairwise registry release IDs must be non-empty and unique")
        release_map[release_id] = item
    for item in policies:
        release_id = item.get("release_id") if isinstance(item, dict) else None
        if not isinstance(release_id, str) or not release_id or release_id in policy_map:
            raise ValueError("Pairwise registry policy release IDs must be non-empty and unique")
        if item.get("lifecycle") not in {"current", "historical"} or not isinstance(
            item.get("strong_eligible"), bool
        ):
            raise ValueError(f"Pairwise registry policy is malformed: {release_id}")
        policy_map[release_id] = item
    if set(release_map) != set(policy_map):
        raise ValueError("Pairwise registry releases and policies differ")
    if sum(item.get("lifecycle") == "current" for item in policies) != 1:
        raise ValueError("Pairwise registry must contain exactly one current release")
    return release_map, policy_map


def _resolve_evaluator(release: dict[str, Any]) -> Callable[..., dict[str, Any]]:
    if release.get("evaluator_api") != EVALUATOR_API:
        raise ValueError("release evaluator API is unknown")
    reference = release.get("evaluator")
    relative = reference.get("path") if isinstance(reference, dict) else None
    expected = reference.get("content_digest") if isinstance(reference, dict) else None
    if not isinstance(relative, str) or not isinstance(expected, str):
        raise ValueError("release evaluator reference is incomplete")
    target = (ROOT / relative).resolve()
    if not target.is_relative_to(HERE.resolve()) or target.parent != HERE.resolve() or not target.is_file():
        raise ValueError("release evaluator path is outside the bounded Pairwise evaluator directory")
    if _digest(target) != expected:
        raise ValueError("release evaluator bytes differ from the registry digest")
    module_name = "_aicp_pairwise_release_" + expected.removeprefix("sha256:")
    spec = importlib.util.spec_from_file_location(module_name, target)
    if spec is None or spec.loader is None:
        raise ValueError("release evaluator module cannot be loaded")
    if str(HERE) not in sys.path:
        sys.path.insert(0, str(HERE))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    evaluator = getattr(module, "evaluate_pairwise_report", None)
    if not callable(evaluator):
        raise ValueError("release evaluator API entrypoint is missing")
    return evaluator


def evaluate_pairwise_report(
    report: dict[str, Any],
    *,
    base_dir: Path,
    registry_path: Path | None = None,
) -> dict[str, Any]:
    tck = report.get("pairwise_tck_release")
    release_id = tck.get("release_id") if isinstance(tck, dict) else None
    try:
        releases, policies = _load_registry(Path(registry_path or REGISTRY_PATH))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        return _empty("rejected", "PAIRWISE_RELEASE_REGISTRY_INVALID", str(exc))
    if release_id not in releases:
        return _empty("rejected", "PAIRWISE_TCK_RELEASE_UNKNOWN", str(release_id))
    policy = policies[release_id]
    if policy["strong_eligible"] is False:
        return _empty(
            "ineligible",
            "PAIRWISE_RELEASE_HISTORICAL_INELIGIBLE",
            f"{release_id}: {policy.get('reason')}",
        )
    if policy["lifecycle"] not in {"current", "historical"}:
        return _empty("rejected", "PAIRWISE_RELEASE_POLICY_INVALID", str(release_id))
    try:
        evaluator = _resolve_evaluator(releases[release_id])
        return evaluator(report, base_dir=base_dir)
    except Exception as exc:
        return _empty("rejected", "PAIRWISE_RELEASE_EVALUATOR_INVALID", str(exc))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report")
    args = parser.parse_args()
    path = Path(args.report).resolve()
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
        result = evaluate_pairwise_report(report, base_dir=path.parent)
    except Exception as exc:
        result = _empty("rejected", "PAIRWISE_DISPATCH_FAILURE", str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "eligible" else 1


if __name__ == "__main__":
    raise SystemExit(main())
