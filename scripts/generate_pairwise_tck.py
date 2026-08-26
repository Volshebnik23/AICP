#!/usr/bin/env python3
"""Generate immutable Pairwise 1.1 artifacts while guarding issued 1.0 bytes."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
PAIRWISE = ROOT / "interop" / "pairwise"
RELEASE_1_0 = "AICP-PAIRWISE-TCK-1.0.0"
RELEASE_1_1 = "AICP-PAIRWISE-TCK-1.1.0"
RELEASE_DIR = PAIRWISE / "release_artifacts" / RELEASE_1_1
AUTHORITY_ROOT = RELEASE_DIR / "authority_root"
HISTORICAL_VECTOR = PAIRWISE / "historical_vectors" / RELEASE_1_0

FROZEN_1_0_RAW_SHA256 = {
    "interop/pairwise/tck_releases.schema.json": "95387107f76c512dd32140f1fe325d52ec8738aac1da4d94d97887ff74e101f7",
    "interop/pairwise/release_registry_snapshots/AICP-PAIRWISE-TCK-1.0.0.json": "2e2ac076dd45b2ad9d429bd4fe35d027380bc883c81e068ce22c57f7c84ce2c3",
    "interop/pairwise/pairwise_joint_report_v1.schema.json": "1e2e2770b0ae28830f733407b4ad915eab155d8143598e30d686705a80583665",
    "interop/pairwise/aicp_pairwise_runner.py": "734e6239b02fd8149382340579ce714341178f962636f6f2f1a1101023253a93",
    "interop/pairwise/pairwise_report_evaluator.py": "4768911768c16f28bece5737f51e50e019451dd69f691f2a7b30ebe6aad75530",
    "interop/pairwise/pairwise_semantic_normalizer.py": "aab5cefc5533516a07ad71018adc8772075bc8928fb310e986877fbdde457197",
    "interop/pairwise/pairwise_runner_bundle_v1_0.json": "da36073dda1331807cbb057a65397b874a4f19c118c4ceeb495a8f6b0b68c16b",
    "interop/pairwise/pairwise_process.py": "56ce4e6dec39cfecafd58c823e897945a2d34ab984327466b959e73b709b8eb3",
}

IMPORT_ROOTS = (
    ROOT / "reference" / "python",
    ROOT / "conformance" / "evidence",
    ROOT / "conformance" / "runner",
    ROOT / "conformance" / "iut",
    ROOT / "scripts",
    PAIRWISE,
    ROOT,
)


def normalized_bytes(path: Path) -> bytes:
    data = path.read_bytes()
    if path.suffix.lower() in {".json", ".jsonl", ".md", ".py", ".ts", ".mjs", ".yml", ".yaml"}:
        data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return data


def normalized_bytes_for_expected(content: bytes, path: Path) -> bytes:
    if path.suffix.lower() in {".json", ".jsonl", ".md", ".py", ".ts", ".mjs", ".yml", ".yaml"}:
        return content.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return content


def digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(normalized_bytes(path)).hexdigest()


def raw_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encoded_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def artifact(relative: str) -> dict[str, str]:
    return {"path": relative, "content_digest": digest(ROOT / relative)}


def _module_name(path: Path, import_root: Path) -> str:
    parts = list(path.relative_to(import_root).with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _resolve_module(module: str) -> Path | None:
    relative = Path(*module.split("."))
    for root in IMPORT_ROOTS:
        file_candidate = root / relative.with_suffix(".py")
        package_candidate = root / relative / "__init__.py"
        if file_candidate.is_file():
            return file_candidate.resolve()
        if package_candidate.is_file():
            return package_candidate.resolve()
    return None


def _imports(path: Path) -> set[Path]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    owner_root = next((root for root in IMPORT_ROOTS if path.is_relative_to(root)), None)
    owner_module = _module_name(path, owner_root) if owner_root is not None else ""
    package_parts = owner_module.split(".")
    if path.name != "__init__.py":
        package_parts = package_parts[:-1]
    resolved: set[Path] = set()
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                keep = max(0, len(package_parts) - (node.level - 1))
                base = package_parts[:keep]
                if node.module:
                    base.extend(node.module.split("."))
                names.append(".".join(base))
            elif node.module:
                names.append(node.module)
        for name in names:
            candidate = _resolve_module(name)
            if candidate is not None:
                resolved.add(candidate)
    return resolved


def discover_import_closure(seeds: Iterable[Path]) -> list[Path]:
    pending = [path.resolve() for path in seeds]
    discovered: set[Path] = set()
    while pending:
        current = pending.pop()
        if current in discovered:
            continue
        if not current.is_file() or not current.is_relative_to(ROOT):
            raise RuntimeError(f"local authority source does not resolve inside the repository: {current}")
        discovered.add(current)
        pending.extend(sorted(_imports(current) - discovered))
    return sorted(discovered, key=lambda item: item.relative_to(ROOT).as_posix())


def _copy_expected(expected: dict[Path, bytes], source: Path, destination: Path) -> None:
    expected[destination] = source.read_bytes()


def _side_authorities() -> dict[str, Any]:
    profile_report = load(HISTORICAL_VECTOR / "a-profile.json")
    binding_report = load(HISTORICAL_VECTOR / "a-binding.json")
    iut_release_id = profile_report["tck_release"]["release_id"]
    evidence_release_id = binding_report["tck_release"]["release_id"]
    iut_registry = load(ROOT / "conformance/iut/tck_releases.json")
    iut_release = next(item for item in iut_registry["releases"] if item["release_id"] == iut_release_id)
    evidence_snapshot_path = ROOT / "conformance/evidence/release_registry_snapshots" / f"{evidence_release_id}.json"
    evidence_snapshot = load(evidence_snapshot_path)
    evidence_release = next(item for item in evidence_snapshot["releases"] if item["release_id"] == evidence_release_id)
    evidence_target = next(item for item in evidence_release["targets"] if item["target_key"] == "BIND-MCP@0.1")

    def fixed(report: dict[str, Any], schema_path: str) -> dict[str, Any]:
        return {
            "report_schema_path": schema_path,
            "report_format_version": report["report_format_version"],
            "report_type": report["report_type"],
            "execution_mode": report["execution_mode"],
            "runner": report["runner"],
            "tck_release": report["tck_release"],
            "required_suites": report["required_suites"],
            "input_artifacts": report["input_artifacts"],
            "compatibility_marks": report["compatibility_marks"],
            "case_ids": [item["case_id"] for item in report["case_results"]],
            "generated_artifact_ids": [item["artifact_id"] for item in report["generated_artifacts"]],
        }

    profile = fixed(profile_report, "conformance/iut/iut_report_v1.schema.json")
    profile.update(
        {
            "resolved_release_id": iut_release_id,
            "release_record": iut_release,
            "suite": profile_report["suite"],
            "profile": profile_report["profile"],
            "consumer_observations": {
                item["case_id"]: item["execution_observation"]
                for item in profile_report["case_results"]
                if "execution_observation" in item
            },
        }
    )
    binding = fixed(binding_report, "conformance/evidence/external_evidence_report_v2_2.schema.json")
    binding.update(
        {
            "resolved_release_id": evidence_release_id,
            "release_snapshot_digest": digest(evidence_snapshot_path),
            "release_record": evidence_release,
            "target_release_record": evidence_target,
            "target": binding_report["target"],
            "target_catalog_path": evidence_target["target_catalog"]["path"],
        }
    )
    return {"authority_format_version": "1.0", "profile": profile, "binding": binding}


def build_expected() -> tuple[dict[Path, bytes], dict[str, Any]]:
    expected: dict[Path, bytes] = {}
    expected[AUTHORITY_ROOT / "pairwise_side_authorities.json"] = encoded_json(_side_authorities())
    closure = discover_import_closure(
        [
            PAIRWISE / "pairwise_report_dispatcher.py",
            PAIRWISE / "pairwise_report_evaluator_v1_1.py",
            PAIRWISE / "pairwise_semantic_normalizer_v1_1.py",
            PAIRWISE / "pairwise_side_report_evaluator_v1_1.py",
            PAIRWISE / "pairwise_authority_bridge_v1_1.py",
        ]
    )
    for source in closure:
        _copy_expected(expected, source, AUTHORITY_ROOT / source.relative_to(ROOT))

    data_refs = {
        "conformance/conformance_report_v1.schema.json",
        "conformance/iut/iut_report_v1.schema.json",
        "conformance/evidence/external_evidence_report_v2_2.schema.json",
        "conformance/evidence/live_bindings/live_binding_scenario.schema.json",
        "conformance/evidence/live_bindings/live_binding_trace_v4.schema.json",
        "conformance/evidence/live_bindings/live_endpoint_descriptor_v2.schema.json",
        "conformance/evidence/live_bindings/live_public_scenario_v1.schema.json",
        "conformance/evidence/live_bindings/mcp_v01_scenarios.json",
        "conformance/evidence/live_bindings/mcp_v01_target_v4.json",
        "fixtures/golden_transcripts/GT-01_happy_path_signed.jsonl",
        "fixtures/keys/GT_public_keys.json",
        "registry/message_types.json",
        "registry/policy_categories.json",
        "schemas/core/aicp-core-message.schema.json",
        "schemas/core/aicp-core-payloads.schema.json",
        "schemas/core/aicp-core-contract.schema.json",
    }
    for ref in sorted(data_refs):
        _copy_expected(expected, ROOT / ref, AUTHORITY_ROOT / ref)

    source_snapshot_refs = sorted(
        destination.relative_to(ROOT).as_posix()
        for destination in expected
        if destination.suffix == ".py"
    )
    runner_entries = [
        {"path": "interop/pairwise/aicp_pairwise_runner_v1_1.py", "role": "runner"},
        {"path": "interop/pairwise/pairwise_process.py", "role": "process_supervision"},
    ]
    evaluator_entries = [
        {"path": "interop/pairwise/pairwise_report_dispatcher.py", "role": "release_dispatcher"},
        {"path": "interop/pairwise/pairwise_report_evaluator_v1_1.py", "role": "pairwise_evaluator"},
        {"path": "interop/pairwise/pairwise_semantic_normalizer_v1_1.py", "role": "semantic_normalizer"},
        {"path": "interop/pairwise/pairwise_side_report_evaluator_v1_1.py", "role": "frozen_authority_client"},
        {"path": "interop/pairwise/pairwise_authority_bridge_v1_1.py", "role": "frozen_authority_bridge"},
        *({"path": ref, "role": "generated_import_closure"} for ref in source_snapshot_refs),
    ]

    def path_digest(path: Path) -> str:
        content = expected.get(path)
        if content is None:
            return digest(path)
        return "sha256:" + hashlib.sha256(normalized_bytes_for_expected(content, path)).hexdigest()

    def bundle(name: str, entries: list[dict[str, str]]) -> tuple[str, str]:
        records = [
            {**entry, "digest": path_digest(ROOT / entry["path"])}
            for entry in entries
        ]
        value = {
            "manifest_version": "1.1",
            "release_id": RELEASE_1_1,
            "closure_discovery": "transitive-python-ast-imports-fail-closed",
            "entries": records,
        }
        path = PAIRWISE / name
        content = encoded_json(value)
        expected[path] = content
        return path.relative_to(ROOT).as_posix(), "sha256:" + hashlib.sha256(content).hexdigest()

    runner_path, runner_digest = bundle("pairwise_runner_bundle_v1_1.json", runner_entries)
    evaluator_path, evaluator_digest = bundle("pairwise_evaluator_bundle_v1_1.json", evaluator_entries)
    underlying = [
        {"path": path.relative_to(ROOT).as_posix(), "content_digest": path_digest(path)}
        for path in sorted(
            (item for item in expected if item.is_relative_to(AUTHORITY_ROOT) and item.suffix != ".py"),
            key=lambda item: item.relative_to(ROOT).as_posix(),
        )
    ]
    release = {
        "release_id": RELEASE_1_1,
        "status": "publication-eligible",
        "registry_schema_digest": digest(PAIRWISE / "tck_releases_v2.schema.json"),
        "runner_bundle": {"path": runner_path, "digest": runner_digest},
        "evaluator_bundle": {"path": evaluator_path, "digest": evaluator_digest},
        "report_schema": artifact("interop/pairwise/pairwise_joint_report_v1_1.schema.json"),
        "evaluator": artifact("interop/pairwise/pairwise_report_evaluator_v1_1.py"),
        "normalizer": artifact("interop/pairwise/pairwise_semantic_normalizer_v1_1.py"),
        "target_registry": {
            **artifact(f"interop/pairwise/release_artifacts/{RELEASE_1_1}/targets.json"),
            "schema_path": f"interop/pairwise/release_artifacts/{RELEASE_1_1}/target_registry.schema.json",
            "schema_digest": digest(RELEASE_DIR / "target_registry.schema.json"),
        },
        "scenario_catalog": {
            **artifact(f"interop/pairwise/release_artifacts/{RELEASE_1_1}/scenarios.json"),
            "schema_path": f"interop/pairwise/release_artifacts/{RELEASE_1_1}/pairwise_scenario_v1_1.schema.json",
            "schema_digest": digest(RELEASE_DIR / "pairwise_scenario_v1_1.schema.json"),
        },
        "mandatory_execution": {
            "target_id": "AICP-BASE@0.1+BIND-MCP@0.1",
            "scenario_id": "PAIRWISE-MCP-CROSS-CONSUMPTION-01",
            "directions": ["A_TO_B", "B_TO_A"],
            "clean_run_count": 2,
            "side_evidence": ["AICP-BASE@0.1/full-profile", "BIND-MCP@0.1/full-binding"],
        },
        "underlying_authorities": underlying,
    }
    snapshot = {"registry_version": "2.0", "releases": [release]}
    expected[PAIRWISE / "release_registry_snapshots" / f"{RELEASE_1_1}.json"] = encoded_json(snapshot)

    old_release = load(PAIRWISE / "release_registry_snapshots" / f"{RELEASE_1_0}.json")["releases"][0]
    registry = {
        "registry_version": "2.0",
        "release_policies": [
            {
                "release_id": RELEASE_1_0,
                "lifecycle": "historical",
                "strong_eligible": False,
                "reason": "Mutable-authority provenance, incomplete actual-Core validation, and a non-load-bearing runtime challenge make this evidence release strong-ineligible.",
            },
            {
                "release_id": RELEASE_1_1,
                "lifecycle": "current",
                "strong_eligible": True,
                "reason": "Release-specific immutable authorities, exact Core v0.1 transcript validation, and load-bearing runtime challenge binding are complete.",
            },
        ],
        "releases": [old_release, release],
    }
    expected[PAIRWISE / "tck_releases.json"] = encoded_json(registry)
    return expected, registry


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    frozen_errors = []
    for ref, expected_hash in FROZEN_1_0_RAW_SHA256.items():
        path = ROOT / ref
        actual = raw_sha256(path) if path.is_file() else "missing"
        if actual != expected_hash:
            frozen_errors.append(f"{ref}: expected raw sha256 {expected_hash}, got {actual}")
    if frozen_errors:
        raise RuntimeError("Pairwise TCK 1.0 byte freeze failed: " + "; ".join(frozen_errors))

    expected, registry = build_expected()
    from jsonschema import Draft202012Validator

    schema = load(PAIRWISE / "tck_releases_v2.schema.json")
    issues = list(Draft202012Validator(schema).iter_errors(registry))
    if issues:
        raise RuntimeError("Pairwise registry v2 invalid: " + "; ".join(issue.message for issue in issues))
    old_snapshot_release = load(PAIRWISE / "release_registry_snapshots" / f"{RELEASE_1_0}.json")["releases"][0]
    if registry["releases"][0] != old_snapshot_release:
        raise RuntimeError("Pairwise TCK 1.0 release object changed")

    if args.check:
        stale = []
        for path, content in expected.items():
            if not path.is_file() or normalized_bytes(path) != normalized_bytes_for_expected(content, path):
                stale.append(path.relative_to(ROOT).as_posix())
        authority_files = {
            path for path in AUTHORITY_ROOT.rglob("*") if path.is_file() and "__pycache__" not in path.parts
        } if AUTHORITY_ROOT.is_dir() else set()
        extra = sorted(path.relative_to(ROOT).as_posix() for path in authority_files - set(expected))
        if stale or extra:
            raise RuntimeError(
                "stale Pairwise TCK 1.1 artifacts: " + ", ".join(sorted(stale))
                + ("; unexpected authority files: " + ", ".join(extra) if extra else "")
            )
        print(f"{RELEASE_1_0} byte freeze and {RELEASE_1_1} immutable closure are current")
        return 0

    for path, content in expected.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    print(
        f"generated {RELEASE_1_1}; files={len(expected)}; "
        f"import_closure={sum(1 for path in expected if path.suffix == '.py')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
