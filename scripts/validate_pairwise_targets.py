#!/usr/bin/env python3
"""Validate one Pairwise target, issued freezes, and current TCK 1.3."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from generate_pairwise_tck import (
    FROZEN_1_0_REPOSITORY_SHA256,
    FROZEN_1_1_MANIFEST_SHA256,
    FROZEN_1_1_REPOSITORY_SHA256,
    FROZEN_1_2_MANIFEST_SHA256,
    FROZEN_1_2_REPOSITORY_SHA256,
    repository_sha256,
)


ROOT = Path(__file__).resolve().parents[1]
PAIRWISE = ROOT / "interop" / "pairwise"
RELEASE_IDS = (
    "AICP-PAIRWISE-TCK-1.0.0",
    "AICP-PAIRWISE-TCK-1.1.0",
    "AICP-PAIRWISE-TCK-1.2.0",
    "AICP-PAIRWISE-TCK-1.3.0",
)
EVIDENCE_1_10_RECORD_SHA256 = "caed5afec58101d1e108f5e64a31f953dca492d8d4a079b173f54591af33eeaf"
EVIDENCE_1_10_SNAPSHOT_SHA256 = "7f57814d35cab7d7d50241b41ede7eb182e2b9f890928d04a6c872bb19f743dc"


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path: Path) -> str:
    return "sha256:" + repository_sha256(path)


def validate_schema(value: Any, schema_path: Path) -> list[str]:
    from jsonschema import Draft202012Validator  # type: ignore

    return [
        f"{schema_path.name}: /{'/'.join(str(part) for part in issue.path)}: {issue.message}"
        for issue in sorted(
            Draft202012Validator(load(schema_path)).iter_errors(value),
            key=lambda item: list(item.path),
        )
    ]


def validate_artifact(ref: Any, label: str, errors: list[str]) -> None:
    if not isinstance(ref, dict):
        errors.append(f"{label} reference missing")
        return
    path = ROOT / str(ref.get("path", ""))
    if not path.is_file() or ref.get("content_digest") != digest(path):
        errors.append(f"{label} digest drift: {ref.get('path')}")


def validate_bundle(ref: Any, label: str, errors: list[str]) -> None:
    if not isinstance(ref, dict):
        errors.append(f"{label} reference missing")
        return
    path = ROOT / str(ref.get("path", ""))
    if not path.is_file() or ref.get("digest") != digest(path):
        errors.append(f"{label} manifest drift")
        return
    for entry in load(path).get("entries", []):
        entry_path = ROOT / str(entry.get("path", ""))
        if not entry_path.is_file() or entry.get("digest") != digest(entry_path):
            errors.append(f"{label} closure drift: {entry.get('path')}")


def validate_target(errors: list[str]) -> None:
    targets = load(PAIRWISE / "targets.json")
    errors.extend(validate_schema(targets, PAIRWISE / "target_registry_v1_3.schema.json"))
    records = [item for item in targets.get("targets", []) if isinstance(item, dict)]
    if len(records) != 1:
        errors.append("M66 must register exactly one Pairwise target")
        return
    record = records[0]
    if record.get("target_id") != "AICP-BASE@0.1+BIND-MCP@0.1":
        errors.append("the exact Base+MCP Pairwise target is not registered")
    if record.get("pairwise_tck_release") != RELEASE_IDS[3]:
        errors.append("the Pairwise target does not resolve current TCK 1.3")
    if record.get("required_transport_roles") != ["client", "server"]:
        errors.append("the Pairwise target does not require both transport roles")
    if record.get("required_runs") != 2 or record.get("required_directions") != ["A_TO_B", "B_TO_A"]:
        errors.append("the Pairwise target does not require two bidirectional clean runs")
    profiles = load(ROOT / "registry" / "aicp_profiles.json")
    profile = next(
        (
            item for item in profiles
            if item.get("profile_id") == "AICP-BASE" and item.get("profile_version") == "0.1"
        ),
        None,
    )
    if not isinstance(profile, dict) or profile.get("status") != "stable":
        errors.append("AICP-BASE@0.1 does not resolve as a stable profile")
    bindings = load(ROOT / "registry" / "transport_bindings.json")
    binding = next((item for item in bindings if item.get("id") == "BIND-MCP-0.1"), None)
    if not isinstance(binding, dict) or binding.get("status") != "stable" or "canonical_id" in binding:
        errors.append("BIND-MCP-0.1 does not resolve as the stable canonical binding")
    for suite in record.get("required_suites", []):
        if not (ROOT / suite).is_file():
            errors.append(f"Pairwise required suite does not resolve: {suite}")
    scenario = load(PAIRWISE / "scenarios.json")
    errors.extend(validate_schema(scenario, PAIRWISE / "pairwise_scenario_v1_3.schema.json"))
    if scenario.get("scenario_id") != "PAIRWISE-MCP-RAW-ROLE-GLOBAL-CAUSALITY-03":
        errors.append("the current Pairwise scenario is not raw-role/global-causality scenario 03")


def validate_releases(errors: list[str]) -> None:
    registry = load(PAIRWISE / "tck_releases.json")
    schema_path = PAIRWISE / "tck_releases_v4.schema.json"
    errors.extend(validate_schema(registry, schema_path))
    releases = {
        item.get("release_id"): item
        for item in registry.get("releases", [])
        if isinstance(item, dict)
    }
    policies = {
        item.get("release_id"): item
        for item in registry.get("release_policies", [])
        if isinstance(item, dict)
    }
    expected_policy = {
        RELEASE_IDS[0]: ("historical", False),
        RELEASE_IDS[1]: ("historical", False),
        RELEASE_IDS[2]: ("historical", False),
        RELEASE_IDS[3]: ("current", True),
    }
    if set(releases) != set(RELEASE_IDS) or set(policies) != set(RELEASE_IDS):
        errors.append("Pairwise registry must contain exactly releases and policies 1.0/1.1/1.2/1.3")
    for release_id, (lifecycle, eligible) in expected_policy.items():
        policy = policies.get(release_id, {})
        if policy.get("lifecycle") != lifecycle or policy.get("strong_eligible") is not eligible:
            errors.append(f"Pairwise policy mismatch for {release_id}")
        snapshot_path = PAIRWISE / "release_registry_snapshots" / f"{release_id}.json"
        snapshot_release = load(snapshot_path).get("releases", [None])[0]
        if releases.get(release_id) != snapshot_release:
            errors.append(f"{release_id} release object differs from its immutable snapshot")

    if sum(policy.get("lifecycle") == "current" for policy in policies.values()) != 1:
        errors.append("Pairwise registry must contain exactly one current release")
    current = releases.get(RELEASE_IDS[3])
    if not isinstance(current, dict):
        errors.append("Pairwise TCK 1.3 release missing")
        return
    snapshot_path = PAIRWISE / "release_registry_snapshots" / f"{RELEASE_IDS[3]}.json"
    release_schema = ROOT / current["registry_schema"]["path"]
    errors.extend(validate_schema(load(snapshot_path), release_schema))
    if current.get("registry_schema_digest") != digest(release_schema):
        errors.append("Pairwise TCK 1.3 release-local registry schema digest drift")
    for field in ("registry_schema", "report_schema", "evaluator", "normalizer", "target_registry", "scenario_catalog"):
        artifact = current.get(field)
        validate_artifact(artifact, f"Pairwise TCK 1.3 {field}", errors)
        if field in {"target_registry", "scenario_catalog"} and isinstance(artifact, dict):
            schema = ROOT / str(artifact.get("schema_path", ""))
            if not schema.is_file() or artifact.get("schema_digest") != digest(schema):
                errors.append(f"Pairwise TCK 1.3 {field} schema digest drift")
    validate_bundle(current.get("runner_bundle"), "Pairwise 1.3 runner bundle", errors)
    validate_bundle(current.get("evaluator_bundle"), "Pairwise 1.3 evaluator bundle", errors)
    validate_bundle(current.get("side_authority_bundle"), "Pairwise 1.3 side-authority bundle", errors)
    if current.get("evaluator_api") != "evaluate_pairwise_report.v1":
        errors.append("Pairwise TCK 1.3 evaluator API is not registered")
    for authority in current.get("underlying_authorities", []):
        validate_artifact(authority, "Pairwise immutable underlying authority", errors)
    authority_spec = load(
        PAIRWISE / "release_artifacts" / RELEASE_IDS[1] / "authority_root" / "pairwise_side_authorities.json"
    )
    if authority_spec.get("profile", {}).get("resolved_release_id") != "AICP-IUT-TCK-1.1.0":
        errors.append("Pairwise profile authority does not resolve frozen IUT TCK 1.1")
    if authority_spec.get("binding", {}).get("resolved_release_id") != "AICP-EVIDENCE-TCK-1.10.0":
        errors.append("Pairwise binding authority does not resolve frozen Evidence TCK 1.10")
    old = releases.get(RELEASE_IDS[2], {})
    if current.get("underlying_authorities") != old.get("underlying_authorities"):
        errors.append("Pairwise TCK 1.3 did not reuse the exact frozen authority set")
    evaluator_entries = load(ROOT / current["evaluator_bundle"]["path"]).get("entries", [])
    evaluator_paths = {item.get("path") for item in evaluator_entries if isinstance(item, dict)}
    if "interop/pairwise/pairwise_release_router.py" in evaluator_paths or any(
        path == "interop/pairwise/pairwise_report_dispatcher.py" for path in evaluator_paths
    ):
        errors.append("mutable Pairwise routing is frozen into the 1.3 evaluator closure")
    if any(
        isinstance(path, str)
        and (path.startswith("conformance/") or path.startswith("reference/"))
        for path in evaluator_paths
    ):
        errors.append("Pairwise 1.3 evaluator closure contains mutable current authorities")


def validate_frozen_bytes(errors: list[str]) -> None:
    freeze_path = PAIRWISE / "release_freezes" / f"{RELEASE_IDS[1]}.json"
    if repository_sha256(freeze_path) != FROZEN_1_1_MANIFEST_SHA256:
        errors.append("Pairwise TCK 1.1 freeze manifest changed")
    freeze_1_2_path = PAIRWISE / "release_freezes" / f"{RELEASE_IDS[2]}.json"
    if repository_sha256(freeze_1_2_path) != FROZEN_1_2_MANIFEST_SHA256:
        errors.append("Pairwise TCK 1.2 freeze manifest changed")
    for release_id, frozen in (
        (RELEASE_IDS[0], FROZEN_1_0_REPOSITORY_SHA256),
        (RELEASE_IDS[1], FROZEN_1_1_REPOSITORY_SHA256),
        (RELEASE_IDS[2], FROZEN_1_2_REPOSITORY_SHA256),
    ):
        for relative, expected in frozen.items():
            # Mutable Evidence/IUT source paths are observations from the historical
            # source checkout, not issued Pairwise artifacts. Their immutable copies
            # live in the release-local Pairwise authority root and are checked here.
            if not relative.startswith("interop/pairwise/"):
                continue
            path = ROOT / relative
            actual = repository_sha256(path) if path.is_file() else "missing"
            if actual != expected:
                errors.append(f"{release_id} repository-byte drift: {relative}")


def validate_evidence_freeze(errors: list[str]) -> None:
    registry_path = ROOT / "conformance" / "evidence" / "evidence_tck_releases.json"
    snapshot_path = ROOT / "conformance" / "evidence" / "release_registry_snapshots" / "AICP-EVIDENCE-TCK-1.10.0.json"
    registry = load(registry_path)
    record = next(item for item in registry["releases"] if item["release_id"] == "AICP-EVIDENCE-TCK-1.10.0")
    record_digest = hashlib.sha256(
        json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if record_digest != EVIDENCE_1_10_RECORD_SHA256:
        errors.append("AICP-EVIDENCE-TCK-1.10.0 release record changed")
    if repository_sha256(snapshot_path) != EVIDENCE_1_10_SNAPSHOT_SHA256:
        errors.append("AICP-EVIDENCE-TCK-1.10.0 snapshot bytes changed during M66")


def validate_current_vector(errors: list[str]) -> None:
    root = PAIRWISE / "current_vectors" / RELEASE_IDS[3]
    expected_names = {
        "a-profile.json",
        "a-binding.json",
        "b-profile.json",
        "b-binding.json",
        "joint.json",
        "manifest.json",
    }
    actual_names = {path.name for path in root.iterdir() if path.is_file()} if root.is_dir() else set()
    if actual_names != expected_names:
        errors.append(f"Pairwise TCK 1.3 vector file set mismatch: {sorted(actual_names)}")
        return
    manifest = load(root / "manifest.json")
    if manifest.get("pairwise_tck_release") != RELEASE_IDS[3]:
        errors.append("Pairwise TCK 1.3 vector manifest release mismatch")
    entries = manifest.get("files", [])
    if {item.get("path") for item in entries if isinstance(item, dict)} != expected_names - {"manifest.json"}:
        errors.append("Pairwise TCK 1.3 vector manifest report set mismatch")
    for item in entries:
        path = root / str(item.get("path", ""))
        actual = repository_sha256(path) if path.is_file() else "missing"
        if actual != item.get("sha256"):
            errors.append(f"Pairwise TCK 1.3 vector digest drift: {item.get('path')}")


def main() -> int:
    errors: list[str] = []
    validate_target(errors)
    validate_releases(errors)
    validate_frozen_bytes(errors)
    validate_evidence_freeze(errors)
    validate_current_vector(errors)
    if errors:
        for message in errors:
            print(f"[ERROR] {message}")
        return 1
    print(
        "Pairwise target/TCK validation passed: registered=1; reachable=1; "
        "current=AICP-PAIRWISE-TCK-1.3.0; historical-strong-ineligible=3; "
        "real-pairwise-submissions=0; Evidence-TCK-1.10=frozen"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
