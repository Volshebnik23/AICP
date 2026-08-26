#!/usr/bin/env python3
"""Validate the M66 target and immutable Pairwise TCK 1.0/1.1 releases."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from generate_pairwise_tck import FROZEN_1_0_REPOSITORY_SHA256, repository_sha256

ROOT = Path(__file__).resolve().parents[1]
PAIRWISE = ROOT / "interop" / "pairwise"
EVIDENCE_1_10_REGISTRY_SHA256 = "7f57814d35cab7d7d50241b41ede7eb182e2b9f890928d04a6c872bb19f743dc"
EVIDENCE_1_10_RECORD_SHA256 = "caed5afec58101d1e108f5e64a31f953dca492d8d4a079b173f54591af33eeaf"
EVIDENCE_1_10_SNAPSHOT_SHA256 = "7f57814d35cab7d7d50241b41ede7eb182e2b9f890928d04a6c872bb19f743dc"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix.lower() in {".json", ".jsonl", ".md", ".py", ".ts", ".mjs", ".yml", ".yaml"}:
        data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return "sha256:" + hashlib.sha256(data).hexdigest()


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


def validate_artifact(ref: dict[str, Any], label: str, errors: list[str]) -> None:
    path = ROOT / str(ref.get("path", ""))
    if not path.is_file() or ref.get("content_digest") != digest(path):
        errors.append(f"{label} digest drift: {ref.get('path')}")


def validate_bundle(ref: dict[str, Any], label: str, errors: list[str]) -> None:
    path = ROOT / str(ref.get("path", ""))
    if not path.is_file() or ref.get("digest") != digest(path):
        errors.append(f"{label} manifest drift")
        return
    for entry in load(path).get("entries", []):
        entry_path = ROOT / str(entry.get("path", ""))
        if not entry_path.is_file() or entry.get("digest") != digest(entry_path):
            errors.append(f"{label} closure drift: {entry.get('path')}")


def main() -> int:
    errors: list[str] = []
    targets = load(PAIRWISE / "targets.json")
    errors.extend(validate_schema(targets, PAIRWISE / "target_registry_v1_1.schema.json"))
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
    errors.extend(validate_schema(scenario, PAIRWISE / "pairwise_scenario_v1_1.schema.json"))
    releases = load(PAIRWISE / "tck_releases.json")
    errors.extend(validate_schema(releases, PAIRWISE / "tck_releases_v2.schema.json"))
    by_release = {
        item.get("release_id"): item
        for item in releases.get("releases", [])
        if isinstance(item, dict)
    }
    old_release = by_release.get("AICP-PAIRWISE-TCK-1.0.0")
    current_release = by_release.get("AICP-PAIRWISE-TCK-1.1.0")
    old_snapshot = load(
        PAIRWISE / "release_registry_snapshots" / "AICP-PAIRWISE-TCK-1.0.0.json"
    ).get("releases", [None])[0]
    current_snapshot = load(
        PAIRWISE / "release_registry_snapshots" / "AICP-PAIRWISE-TCK-1.1.0.json"
    ).get("releases", [None])[0]
    if old_release != old_snapshot:
        errors.append("Pairwise TCK 1.0 release object differs from its immutable snapshot")
    if current_release != current_snapshot:
        errors.append("Pairwise TCK 1.1 release object differs from its immutable snapshot")

    policies = {
        item.get("release_id"): item
        for item in releases.get("release_policies", [])
        if isinstance(item, dict)
    }
    old_policy = policies.get("AICP-PAIRWISE-TCK-1.0.0", {})
    current_policy = policies.get("AICP-PAIRWISE-TCK-1.1.0", {})
    if old_policy.get("lifecycle") != "historical" or old_policy.get("strong_eligible") is not False:
        errors.append("Pairwise TCK 1.0 must be explicitly historical and strong-ineligible")
    if current_policy.get("lifecycle") != "current" or current_policy.get("strong_eligible") is not True:
        errors.append("Pairwise TCK 1.1 must be explicitly current and strong-eligible")
    for relative, expected in FROZEN_1_0_REPOSITORY_SHA256.items():
        path = ROOT / relative
        actual = repository_sha256(path) if path.is_file() else "missing"
        if actual != expected:
            errors.append(f"Pairwise TCK 1.0 repository-byte drift: {relative}")

    if isinstance(current_release, dict):
        if current_release.get("registry_schema_digest") != digest(PAIRWISE / "tck_releases_v2.schema.json"):
            errors.append("Pairwise TCK 1.1 registry schema digest drift")
        for field in ("report_schema", "evaluator", "normalizer", "target_registry", "scenario_catalog"):
            artifact = current_release.get(field, {})
            validate_artifact(artifact, f"Pairwise TCK 1.1 {field}", errors)
            if field in {"target_registry", "scenario_catalog"}:
                schema_path = ROOT / str(artifact.get("schema_path", ""))
                if not schema_path.is_file() or artifact.get("schema_digest") != digest(schema_path):
                    errors.append(f"Pairwise TCK 1.1 {field} schema digest drift")
        validate_bundle(current_release.get("runner_bundle", {}), "Pairwise runner bundle", errors)
        validate_bundle(current_release.get("evaluator_bundle", {}), "Pairwise evaluator bundle", errors)
        for authority in current_release.get("underlying_authorities", []):
            validate_artifact(authority, "Pairwise immutable underlying authority", errors)
        forbidden = (
            "conformance/evidence/evidence_tck_releases.json",
            "conformance/evidence/targets.json",
            "conformance/iut/tck_releases.json",
        )
        authority_paths = {item.get("path") for item in current_release.get("underlying_authorities", [])}
        for path in forbidden:
            if path in authority_paths:
                errors.append(f"Pairwise TCK 1.1 depends on mutable current authority: {path}")
        authority_spec = load(
            PAIRWISE
            / "release_artifacts"
            / "AICP-PAIRWISE-TCK-1.1.0"
            / "authority_root"
            / "pairwise_side_authorities.json"
        )
        if authority_spec.get("profile", {}).get("resolved_release_id") != "AICP-IUT-TCK-1.1.0":
            errors.append("Pairwise profile authority does not resolve exact IUT TCK 1.1")
        if authority_spec.get("binding", {}).get("resolved_release_id") != "AICP-EVIDENCE-TCK-1.10.0":
            errors.append("Pairwise binding authority does not resolve exact Evidence TCK 1.10")

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
    print(
        "Pairwise target/TCK validation passed: registered=1; reachable=1; "
        "current=AICP-PAIRWISE-TCK-1.1.0; historical-strong-ineligible=1; "
        "Evidence TCK 1.10 frozen"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
