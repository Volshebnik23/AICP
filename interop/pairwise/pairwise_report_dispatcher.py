#!/usr/bin/env python3
"""Dispatch Pairwise reports to their exact release evaluator and policy."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
HISTORICAL_1_0_REASON = (
    "Pairwise TCK 1.0 is historical and strong-ineligible because its evidence provenance "
    "bound mutable authorities, actual joint traffic lacked complete Core validation, and "
    "the runtime challenge was not load-bearing."
)
HISTORICAL_1_1_POLICY_REASON = (
    "Joint MCP requests were repository-harness generated and Pairwise server processes "
    "were not bound to the exact participant builds."
)
HISTORICAL_1_1_REASON = (
    "Pairwise TCK 1.1 is historical and strong-ineligible because joint MCP requests "
    "were repository-harness generated and Pairwise server processes were not bound "
    "to the exact participant builds."
)
CURRENT_1_2_POLICY_REASON = (
    "Participant-authored MCP requests, bound client/server role descriptors, "
    "transport-first causality, and final consumer polling are complete."
)


def _empty(status: str, code: str, message: str) -> dict[str, Any]:
    return {
        "status": status,
        "errors": [{"code": code, "message": message}],
        "eligible_pairwise_relations": [],
        "eligible_marks": [],
    }


def _policy(release_id: str) -> dict[str, Any] | None:
    registry = json.loads((HERE / "tck_releases.json").read_text(encoding="utf-8"))
    return next(
        (
            item
            for item in registry.get("release_policies", [])
            if isinstance(item, dict) and item.get("release_id") == release_id
        ),
        None,
    )


def evaluate_pairwise_report(report: dict[str, Any], *, base_dir: Path) -> dict[str, Any]:
    tck = report.get("pairwise_tck_release")
    release_id = tck.get("release_id") if isinstance(tck, dict) else None
    if release_id == "AICP-PAIRWISE-TCK-1.0.0":
        policy = _policy(release_id)
        if policy != {
            "release_id": release_id,
            "lifecycle": "historical",
            "strong_eligible": False,
            "reason": "Mutable-authority provenance, incomplete actual-Core validation, and a non-load-bearing runtime challenge make this evidence release strong-ineligible.",
        }:
            return _empty("rejected", "PAIRWISE_RELEASE_POLICY_INVALID", release_id)
        return _empty("ineligible", "PAIRWISE_RELEASE_HISTORICAL_INELIGIBLE", HISTORICAL_1_0_REASON)
    if release_id == "AICP-PAIRWISE-TCK-1.1.0":
        policy = _policy(release_id)
        if policy != {
            "release_id": release_id,
            "lifecycle": "historical",
            "strong_eligible": False,
            "reason": HISTORICAL_1_1_POLICY_REASON,
        }:
            return _empty("rejected", "PAIRWISE_RELEASE_POLICY_INVALID", release_id)
        return _empty("ineligible", "PAIRWISE_RELEASE_HISTORICAL_INELIGIBLE", HISTORICAL_1_1_REASON)
    if release_id == "AICP-PAIRWISE-TCK-1.2.0":
        policy = _policy(release_id)
        if policy != {
            "release_id": release_id,
            "lifecycle": "current",
            "strong_eligible": True,
            "reason": CURRENT_1_2_POLICY_REASON,
        }:
            return _empty("rejected", "PAIRWISE_RELEASE_POLICY_INVALID", release_id)
        from pairwise_report_evaluator_v1_2 import evaluate_pairwise_report as evaluate_v1_2

        return evaluate_v1_2(report, base_dir=base_dir)
    return _empty("rejected", "PAIRWISE_TCK_RELEASE_UNKNOWN", str(release_id))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report")
    args = parser.parse_args()
    path = Path(args.report).resolve()
    try:
        result = evaluate_pairwise_report(
            json.loads(path.read_text(encoding="utf-8")),
            base_dir=path.parent,
        )
    except Exception as exc:
        result = _empty("rejected", "PAIRWISE_DISPATCH_FAILURE", str(exc))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "eligible" else 1


if __name__ == "__main__":
    raise SystemExit(main())
