#!/usr/bin/env python3
"""Regenerate the frozen AICP-PAIRWISE-TCK-1.0.0 release artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PAIRWISE = ROOT / "interop" / "pairwise"
RELEASE_ID = "AICP-PAIRWISE-TCK-1.0.0"


def digest(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix.lower() in {".json", ".jsonl", ".md", ".py", ".ts", ".mjs", ".yml", ".yaml"}:
        data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def artifact(relative: str) -> dict[str, str]:
    return {"path": relative, "content_digest": digest(ROOT / relative)}


def encoded_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    bundle_entries = [
        ("interop/pairwise/aicp_pairwise_runner.py", "runner"),
        ("interop/pairwise/pairwise_process.py", "process_supervision"),
    ]
    bundle = {
        "manifest_version": "1.0",
        "release_id": RELEASE_ID,
        "entries": [
            {"path": path, "role": role, "digest": digest(ROOT / path)}
            for path, role in bundle_entries
        ],
    }
    bundle_path = PAIRWISE / "pairwise_runner_bundle_v1_0.json"
    bundle_bytes = encoded_json(bundle)
    bundle_digest = "sha256:" + hashlib.sha256(bundle_bytes).hexdigest()

    authorities = [
        "conformance/iut/tck_releases.json",
        "conformance/iut/cases.json",
        "conformance/iut/iut_report_v1.schema.json",
        "conformance/profiles/PF_AICP_BASE_0.1.json",
        "conformance/core/CT_CORE_0.1.json",
        "conformance/evidence/evidence_tck_releases.json",
        "conformance/evidence/external_evidence_report_v2_2.schema.json",
        "conformance/evidence/targets.json",
        "conformance/evidence/target_registry.schema.json",
        "conformance/evidence/live_bindings/mcp_v01_target_v4.json",
        "conformance/evidence/live_bindings/mcp_v01_scenarios.json",
        "conformance/bindings/TB_MCP_0.1.json",
        "registry/aicp_profiles.json",
        "registry/transport_bindings.json",
    ]
    release = {
        "release_id": RELEASE_ID,
        "status": "publication-eligible",
        "registry_schema_digest": digest(PAIRWISE / "tck_releases.schema.json"),
        "runner_bundle": {"path": "interop/pairwise/pairwise_runner_bundle_v1_0.json", "digest": bundle_digest},
        "report_schema": artifact("interop/pairwise/pairwise_joint_report_v1.schema.json"),
        "evaluator": artifact("interop/pairwise/pairwise_report_evaluator.py"),
        "normalizer": artifact("interop/pairwise/pairwise_semantic_normalizer.py"),
        "target_registry": {
            **artifact("interop/pairwise/targets.json"),
            "schema_path": "interop/pairwise/target_registry.schema.json",
            "schema_digest": digest(PAIRWISE / "target_registry.schema.json"),
        },
        "scenario_catalog": {
            **artifact("interop/pairwise/scenarios.json"),
            "schema_path": "interop/pairwise/pairwise_scenario_v1.schema.json",
            "schema_digest": digest(PAIRWISE / "pairwise_scenario_v1.schema.json"),
        },
        "mandatory_execution": {
            "target_id": "AICP-BASE@0.1+BIND-MCP@0.1",
            "scenario_id": "PAIRWISE-MCP-CROSS-CONSUMPTION-01",
            "directions": ["A_TO_B", "B_TO_A"],
            "clean_run_count": 2,
            "side_evidence": ["AICP-BASE@0.1/full-profile", "BIND-MCP@0.1/full-binding"],
        },
        "underlying_authorities": [artifact(path) for path in authorities],
    }
    registry = {"registry_version": "1.0", "releases": [release]}
    try:
        from jsonschema import Draft202012Validator  # type: ignore

        schema = json.loads((PAIRWISE / "tck_releases.schema.json").read_text(encoding="utf-8"))
        issues = list(Draft202012Validator(schema).iter_errors(registry))
        if issues:
            raise ValueError("; ".join(issue.message for issue in issues))
    except ImportError as exc:
        raise RuntimeError("jsonschema is required to freeze the Pairwise TCK") from exc
    registry_path = PAIRWISE / "tck_releases.json"
    snapshot_path = PAIRWISE / "release_registry_snapshots" / f"{RELEASE_ID}.json"
    expected = {
        bundle_path: bundle_bytes,
        registry_path: encoded_json(registry),
        snapshot_path: encoded_json(registry),
    }
    if args.check:
        stale = [str(path.relative_to(ROOT)) for path, content in expected.items() if not path.is_file() or path.read_bytes().replace(b"\r\n", b"\n") != content]
        if stale:
            raise RuntimeError("stale Pairwise TCK artifacts: " + ", ".join(stale))
        print(f"{RELEASE_ID} generated artifacts are current")
        return 0
    for path, content in expected.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    print(f"generated {RELEASE_ID}; registry_digest={digest(registry_path)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
