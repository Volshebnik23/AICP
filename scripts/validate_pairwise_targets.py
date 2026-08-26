#!/usr/bin/env python3
"""Validate the M66 target registry and immutable Pairwise TCK release."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PAIRWISE = ROOT / "interop" / "pairwise"
EVIDENCE_1_10_REGISTRY_SHA256 = "7f57814d35cab7d7d50241b41ede7eb182e2b9f890928d04a6c872bb19f743dc"
EVIDENCE_1_10_RECORD_SHA256 = "caed5afec58101d1e108f5e64a31f953dca492d8d4a079b173f54591af33eeaf"
EVIDENCE_1_10_SNAPSHOT_SHA256 = "7f57814d35cab7d7d50241b41ede7eb182e2b9f890928d04a6c872bb19f743dc"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def normalized_source_sha256(path: Path) -> str:
    raw = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return hashlib.sha256(raw).hexdigest()


def validate_schema(value: Any, schema_path: Path) -> list[str]:
    from jsonschema import Draft202012Validator  # type: ignore

    return [
        f"{schema_path.name}: /{'/'.join(str(part) for part in issue.path)}: {issue.message}"
        for issue in sorted(
            Draft202012Validator(load(schema_path)).iter_errors(value),
            key=lambda item: list(item.path),
        )
    ]


def main() -> int:
    errors: list[str] = []
    targets = load(PAIRWISE / "targets.json")
    errors.extend(validate_schema(targets, PAIRWISE / "target_registry.schema.json"))
    records = [item for item in targets.get("targets", []) if isinstance(item, dict)]
    target_ids = [str(item.get("target_id")) for item in records]
    semantic_ids = [
        (
            item.get("base_profile", {}).get("profile_id"),
            item.get("base_profile", {}).get("profile_version"),
            item.get("binding", {}).get("binding_id"),
            item.get("binding", {}).get("binding_version"),
        )
        for item in records
    ]
    if len(target_ids) != len(set(target_ids)):
        errors.append("duplicate pairwise target_id")
    if len(semantic_ids) != len(set(semantic_ids)):
        errors.append("duplicate semantic pairwise target under another key")
    if len(records) != 1:
        errors.append("M66 must register exactly one pairwise target")
    else:
        record = records[0]
        profiles = load(ROOT / "registry" / "aicp_profiles.json")
        profile = next(
            (
                item
                for item in profiles
                if item.get("profile_id") == "AICP-BASE"
                and item.get("profile_version") == "0.1"
            ),
            None,
        )
        if not isinstance(profile, dict) or profile.get("status") != "stable":
            errors.append("AICP-BASE@0.1 must resolve as a stable registered profile")
        profile_catalog = load(ROOT / record["base_profile"]["profile_catalog"])
        if (
            profile_catalog.get("profile_id") != "AICP-BASE"
            or profile_catalog.get("profile_version") != "0.1"
            or profile_catalog.get("compatibility_mark") != record["base_profile"]["compatibility_mark"]
            or profile_catalog.get("required_suites") != ["conformance/core/CT_CORE_0.1.json"]
        ):
            errors.append("pairwise profile catalog binding is not exact")
        bindings = load(ROOT / "registry" / "transport_bindings.json")
        binding = next((item for item in bindings if item.get("id") == record["binding"]["registry_id"]), None)
        if not isinstance(binding, dict) or binding.get("status") != "stable" or "canonical_id" in binding:
            errors.append("BIND-MCP-0.1 must resolve as the stable non-deprecated canonical binding")
        evidence_targets = load(ROOT / "conformance" / "evidence" / "targets.json")
        binding_target = next(
            (
                item
                for item in evidence_targets.get("targets", [])
                if item.get("target_kind") == "binding"
                and item.get("target_id") == "BIND-MCP"
                and item.get("target_version") == "0.1"
            ),
            None,
        )
        if (
            not isinstance(binding_target, dict)
            or binding_target.get("expected_mark") != record["binding"]["compatibility_mark"]
            or binding_target.get("required_suites")
            != ["conformance/bindings/TB_MCP_0.1.json"]
        ):
            errors.append("pairwise MCP target does not resolve to the canonical evidence target and suite")
        for suite in record.get("required_suites", []):
            if not (ROOT / suite).is_file():
                errors.append(f"pairwise required suite does not resolve: {suite}")

    scenario = load(PAIRWISE / "scenarios.json")
    errors.extend(validate_schema(scenario, PAIRWISE / "pairwise_scenario_v1.schema.json"))
    releases = load(PAIRWISE / "tck_releases.json")
    errors.extend(validate_schema(releases, PAIRWISE / "tck_releases.schema.json"))
    release = releases.get("releases", [None])[0]
    snapshot_path = PAIRWISE / "release_registry_snapshots" / "AICP-PAIRWISE-TCK-1.0.0.json"
    snapshot = load(snapshot_path)
    if snapshot.get("releases", [None])[0] != release:
        errors.append("Pairwise TCK current record differs from its immutable 1.0.0 snapshot")
    if isinstance(release, dict):
        if release.get("registry_schema_digest") != digest(PAIRWISE / "tck_releases.schema.json"):
            errors.append("Pairwise TCK registry schema digest drift")
        for field in ("report_schema", "evaluator", "normalizer", "target_registry", "scenario_catalog"):
            artifact = release.get(field, {})
            path = ROOT / str(artifact.get("path", ""))
            if not path.is_file() or artifact.get("content_digest") != digest(path):
                errors.append(f"Pairwise TCK {field} digest drift")
        bundle_ref = release.get("runner_bundle", {})
        bundle_path = ROOT / str(bundle_ref.get("path", ""))
        if not bundle_path.is_file() or bundle_ref.get("digest") != digest(bundle_path):
            errors.append("Pairwise runner bundle manifest drift")
        else:
            for entry in load(bundle_path).get("entries", []):
                path = ROOT / str(entry.get("path", ""))
                if not path.is_file() or entry.get("digest") != digest(path):
                    errors.append(f"Pairwise runner import-closure drift: {entry.get('path')}")
        for authority in release.get("underlying_authorities", []):
            path = ROOT / str(authority.get("path", ""))
            if not path.is_file() or authority.get("content_digest") != digest(path):
                errors.append(f"Pairwise underlying authority drift: {authority.get('path')}")

    evidence_registry_path = ROOT / "conformance" / "evidence" / "evidence_tck_releases.json"
    evidence_snapshot_path = ROOT / "conformance" / "evidence" / "release_registry_snapshots" / "AICP-EVIDENCE-TCK-1.10.0.json"
    evidence_registry = load(evidence_registry_path)
    evidence_record = next(item for item in evidence_registry["releases"] if item["release_id"] == "AICP-EVIDENCE-TCK-1.10.0")
    evidence_record_digest = hashlib.sha256(
        json.dumps(evidence_record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if normalized_source_sha256(evidence_registry_path) != EVIDENCE_1_10_REGISTRY_SHA256:
        errors.append("AICP-EVIDENCE-TCK-1.10.0 registry bytes changed during M66")
    if evidence_record_digest != EVIDENCE_1_10_RECORD_SHA256:
        errors.append("AICP-EVIDENCE-TCK-1.10.0 release record changed during M66")
    if normalized_source_sha256(evidence_snapshot_path) != EVIDENCE_1_10_SNAPSHOT_SHA256:
        errors.append("AICP-EVIDENCE-TCK-1.10.0 snapshot bytes changed during M66")

    if errors:
        for message in errors:
            print(f"[ERROR] {message}")
        return 1
    print("Pairwise target/TCK validation passed: registered=1; reachable=1; Evidence TCK 1.10 frozen")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
