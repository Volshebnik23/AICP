#!/usr/bin/env python3
"""Freeze issued Pairwise releases and generate immutable Pairwise TCK 1.3."""

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
RELEASE_1_2 = "AICP-PAIRWISE-TCK-1.2.0"
RELEASE_1_3 = "AICP-PAIRWISE-TCK-1.3.0"
RELEASE_DIR = PAIRWISE / "release_artifacts" / RELEASE_1_3
FREEZE_DIR = PAIRWISE / "release_freezes"
FREEZE_1_1 = FREEZE_DIR / f"{RELEASE_1_1}.json"
FREEZE_1_2 = FREEZE_DIR / f"{RELEASE_1_2}.json"
FROZEN_1_1_MANIFEST_SHA256 = "6a8a74fe585f0513f57bae079c1d91e51a1afcd297148333e0981a1d5bcf9769"
FROZEN_1_2_MANIFEST_SHA256 = "0a8f6c6c35809ff9e5e7ca7cc215942e8e0e3e172e602f465a186260c395ccee"
TEXT_SUFFIXES = {".json", ".jsonl", ".md", ".py", ".ts", ".mjs", ".yml", ".yaml"}
TARGET_ID = "AICP-BASE@0.1+BIND-MCP@0.1"

FROZEN_1_0_REPOSITORY_SHA256 = {
    "interop/pairwise/tck_releases.schema.json": "620cd734ab23b63d2a35648baf8f063b8085d8c11a5cc7a03d2d8f18f5a42905",
    "interop/pairwise/release_registry_snapshots/AICP-PAIRWISE-TCK-1.0.0.json": "4d8ca895e8848f4171b2c48952840d0e383a6cd1e43d966a6bd9582051d2182a",
    "interop/pairwise/pairwise_joint_report_v1.schema.json": "bccfe9710747ab8703ef262c0b86f452c36a65bfee26202a4d220adea202cdf9",
    "interop/pairwise/aicp_pairwise_runner.py": "496678529639f69c8fc437e0889e40a7f1b4d9f592ade5ac65dffc21ade58eec",
    "interop/pairwise/pairwise_report_evaluator.py": "fb8ca05a000f3ee372039d208436a0bdf9e79feb2c029f0ce7ac40eaeceec43b",
    "interop/pairwise/pairwise_semantic_normalizer.py": "b6f36f883dc71722a6b9b6833d59f76e527bc9ff96bc71a2175fe4e2fe261edf",
    "interop/pairwise/pairwise_runner_bundle_v1_0.json": "86eda6ccb0e7dac0d9ee7eb5a9c668a1a722a7656d08c0c3b4f31606dc7a1781",
    "interop/pairwise/pairwise_process.py": "6a71ab9c3ac60692084fb614b5017f054de424ae7e15e6f6287295708656c242",
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
    if path.suffix.lower() in TEXT_SUFFIXES:
        data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return data


def normalized_bytes_for_expected(content: bytes, path: Path) -> bytes:
    if path.suffix.lower() in TEXT_SUFFIXES:
        return content.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return content


def digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(normalized_bytes(path)).hexdigest()


def repository_sha256(path: Path) -> str:
    """Hash Git-canonical text bytes independently of checkout EOL conversion."""

    return hashlib.sha256(normalized_bytes(path)).hexdigest()


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


def discover_process_import_closure(seeds: Iterable[Path], import_roots: Iterable[Path]) -> list[Path]:
    """Discover imports against the exact sys.path roots used by another process."""

    roots = tuple(path.resolve() for path in import_roots)

    def resolve(module: str) -> Path | None:
        relative = Path(*module.split("."))
        for root in roots:
            for candidate in (root / relative.with_suffix(".py"), root / relative / "__init__.py"):
                if candidate.is_file():
                    return candidate.resolve()
        return None

    def imports(path: Path) -> set[Path]:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        resolved: set[Path] = set()
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Import):
                names.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                names.append(node.module)
            for name in names:
                candidate = resolve(name)
                if candidate is not None:
                    resolved.add(candidate)
        return resolved

    pending = [path.resolve() for path in seeds]
    discovered: set[Path] = set()
    while pending:
        current = pending.pop()
        if current in discovered:
            continue
        if not current.is_file() or not current.is_relative_to(ROOT):
            raise RuntimeError(f"process import closure escaped repository root: {current}")
        discovered.add(current)
        pending.extend(sorted(imports(current) - discovered))
    return sorted(discovered, key=lambda item: item.relative_to(ROOT).as_posix())


def _issued_1_1_paths() -> list[Path]:
    explicit = [
        PAIRWISE / "tck_releases_v2.schema.json",
        PAIRWISE / "release_registry_snapshots" / f"{RELEASE_1_1}.json",
        PAIRWISE / "pairwise_joint_report_v1_1.schema.json",
        PAIRWISE / "aicp_pairwise_runner_v1_1.py",
        PAIRWISE / "pairwise_report_evaluator_v1_1.py",
        PAIRWISE / "pairwise_semantic_normalizer_v1_1.py",
        PAIRWISE / "pairwise_side_report_evaluator_v1_1.py",
        PAIRWISE / "pairwise_authority_bridge_v1_1.py",
        PAIRWISE / "pairwise_core_validator_v1_1.py",
        PAIRWISE / "pairwise_runner_bundle_v1_1.json",
        PAIRWISE / "pairwise_evaluator_bundle_v1_1.json",
        PAIRWISE / "target_registry_v1_1.schema.json",
        PAIRWISE / "pairwise_scenario_v1_1.schema.json",
        PAIRWISE / "pairwise_process.py",
    ]
    for root in (
        PAIRWISE / "release_artifacts" / RELEASE_1_1,
        PAIRWISE / "current_vectors" / RELEASE_1_1,
    ):
        explicit.extend(path for path in root.rglob("*") if path.is_file() and "__pycache__" not in path.parts)
    return sorted(set(explicit), key=lambda item: item.relative_to(ROOT).as_posix())


def _freeze_manifest() -> dict[str, Any]:
    return {
        "freeze_format_version": "1.0",
        "release_id": RELEASE_1_1,
        "source_merge_commit": "7b752769600a4335617f2c7f439011c4b52a297a",
        "files": [
            {"path": path.relative_to(ROOT).as_posix(), "repository_sha256": repository_sha256(path)}
            for path in _issued_1_1_paths()
        ],
    }


def _issued_1_2_paths() -> list[Path]:
    explicit = [
        PAIRWISE / "tck_releases_v3.schema.json",
        PAIRWISE / "release_registry_snapshots" / f"{RELEASE_1_2}.json",
        PAIRWISE / "pairwise_joint_report_v1_2.schema.json",
        PAIRWISE / "aicp_pairwise_runner_v1_2.py",
        PAIRWISE / "pairwise_report_evaluator_v1_2.py",
        PAIRWISE / "pairwise_semantic_normalizer_v1_2.py",
        PAIRWISE / "pairwise_runner_bundle_v1_2.json",
        PAIRWISE / "pairwise_evaluator_bundle_v1_2.json",
        PAIRWISE / "target_registry_v1_2.schema.json",
        PAIRWISE / "pairwise_scenario_v1_2.schema.json",
    ]
    snapshot = load(PAIRWISE / "release_registry_snapshots" / f"{RELEASE_1_2}.json")
    release = snapshot["releases"][0]
    for field in ("runner_bundle", "evaluator_bundle"):
        bundle_path = ROOT / release[field]["path"]
        for entry in load(bundle_path).get("entries", []):
            explicit.append(ROOT / entry["path"])
    for reference in release.get("underlying_authorities", []):
        explicit.append(ROOT / reference["path"])
    for root in (
        PAIRWISE / "release_artifacts" / RELEASE_1_2,
        PAIRWISE / "current_vectors" / RELEASE_1_2,
    ):
        explicit.extend(path for path in root.rglob("*") if path.is_file() and "__pycache__" not in path.parts)
    return sorted(set(explicit), key=lambda item: item.relative_to(ROOT).as_posix())


def _freeze_1_2_manifest() -> dict[str, Any]:
    return {
        "freeze_format_version": "1.0",
        "release_id": RELEASE_1_2,
        "source_merge_commit": "0b8679dfa384585857d562ddd9b678389feff515",
        "files": [
            {"path": path.relative_to(ROOT).as_posix(), "repository_sha256": repository_sha256(path)}
            for path in _issued_1_2_paths()
        ],
    }


def _load_frozen_1_1() -> dict[str, str]:
    if not FREEZE_1_1.is_file():
        return {}
    if repository_sha256(FREEZE_1_1) != FROZEN_1_1_MANIFEST_SHA256:
        return {}
    value = load(FREEZE_1_1)
    return {item["path"]: item["repository_sha256"] for item in value.get("files", [])}


FROZEN_1_1_REPOSITORY_SHA256 = _load_frozen_1_1()


def _load_frozen_1_2() -> dict[str, str]:
    if not FREEZE_1_2.is_file():
        return {}
    if repository_sha256(FREEZE_1_2) != FROZEN_1_2_MANIFEST_SHA256:
        return {}
    value = load(FREEZE_1_2)
    return {item["path"]: item["repository_sha256"] for item in value.get("files", [])}


FROZEN_1_2_REPOSITORY_SHA256 = _load_frozen_1_2()


def _freeze_errors() -> list[str]:
    errors: list[str] = []
    for ref, expected_hash in {
        **FROZEN_1_0_REPOSITORY_SHA256,
        **FROZEN_1_1_REPOSITORY_SHA256,
        **FROZEN_1_2_REPOSITORY_SHA256,
    }.items():
        # Historical freeze manifests record the source checkout that produced the
        # release, but later Evidence/IUT releases are allowed to advance those mutable
        # source paths. Issued Pairwise bytes and copied authority roots remain under
        # interop/pairwise and are the load-bearing historical freeze surface.
        if not ref.startswith("interop/pairwise/"):
            continue
        path = ROOT / ref
        actual = repository_sha256(path) if path.is_file() else "missing"
        if actual != expected_hash:
            errors.append(f"{ref}: expected repository sha256 {expected_hash}, got {actual}")
    if not FROZEN_1_1_REPOSITORY_SHA256:
        errors.append("Pairwise TCK 1.1 freeze manifest is missing")
    if not FROZEN_1_2_REPOSITORY_SHA256:
        errors.append("Pairwise TCK 1.2 freeze manifest is missing")
    return errors


def _targets() -> dict[str, Any]:
    return {
        "registry_version": "1.3",
        "targets": [
            {
                "target_id": TARGET_ID,
                "base_profile": {
                    "profile_id": "AICP-BASE", "profile_version": "0.1", "status": "stable",
                    "profile_catalog": "conformance/profiles/PF_AICP_BASE_0.1.json",
                    "compatibility_mark": "AICP-Profile-BASE-0.1", "execution_mode": "full-profile",
                },
                "binding": {
                    "binding_id": "BIND-MCP", "binding_version": "0.1", "registry_id": "BIND-MCP-0.1",
                    "status": "stable", "deprecated": False, "compatibility_mark": "AICP-BIND-MCP-0.1",
                    "execution_mode": "full-binding", "transport": "mcp_stdio",
                },
                "required_suites": ["conformance/core/CT_CORE_0.1.json", "conformance/bindings/TB_MCP_0.1.json"],
                "scenario_catalog": f"interop/pairwise/release_artifacts/{RELEASE_1_3}/scenarios.json",
                "required_side_evidence": ["AICP-BASE@0.1/full-profile", "BIND-MCP@0.1/full-binding"],
                "required_runs": 2,
                "required_directions": ["A_TO_B", "B_TO_A"],
                "required_transport_roles": ["client", "server"],
                "pairwise_tck_release": RELEASE_1_3,
                "relation_kind": "pairwise_interop",
            }
        ],
    }


def _scenario() -> dict[str, Any]:
    return {
        "scenario_version": "1.3",
        "scenario_id": "PAIRWISE-MCP-RAW-ROLE-GLOBAL-CAUSALITY-03",
        "target_id": TARGET_ID,
        "message_flow": ["CONTRACT_PROPOSE", "CONTRACT_ACCEPT", "ATTEST_ACTION"],
        "transport_roles": ["client", "server"],
        "mcp_flow": [
            "producer_client_send_to_consumer_server",
            "consumer_client_poll_consumer_server",
            "consumer_client_send_to_producer_server",
            "producer_client_poll_producer_server",
            "producer_client_send_to_consumer_server",
            "consumer_client_final_poll_consumer_server",
        ],
        "freshness": {
            "run_count": 2,
            "fresh_fields": ["run_id", "challenge", "session_id", "contract_id", "message_id", "jsonrpc_id", "process_instance_id", "cursor"],
            "semantic_equivalence_required": True,
        },
        "challenge_binding": {
            "proposal_contract_goal": "direction.challenge",
            "consumer_discovery": "participant_client_poll_response_only",
            "acceptance_peer_message": "client_consumed_proposal",
            "attestation_peer_message": "client_consumed_acceptance",
        },
        "role_evidence": {
            "client": "raw_describe_exchange_per_run",
            "server": "raw_ready_descriptor_per_run",
            "summary": "exactly_derived_from_raw_runs",
        },
        "run_global_chronology": {
            "client_events": "exact_contiguous_global_event_sequence",
            "relay_exchanges": "exact_contiguous_global_exchange_sequence",
            "first_seen_scope": "complete_client_process_lifetime_per_run",
        },
        "cursor_progression": {
            "initial_cursor": "c0",
            "poll_limit": 1,
            "final_consumer_poll": "prior_exact_continuation_cursor",
        },
        "final_consumption_required": True,
    }


def build_expected_v1_3() -> tuple[dict[Path, bytes], dict[str, Any]]:
    expected: dict[Path, bytes] = {
        PAIRWISE / "targets.json": encoded_json(_targets()),
        PAIRWISE / "scenarios.json": encoded_json(_scenario()),
        RELEASE_DIR / "targets.json": encoded_json(_targets()),
        RELEASE_DIR / "scenarios.json": encoded_json(_scenario()),
    }
    for source, destination in (
        (PAIRWISE / "target_registry_v1_3.schema.json", RELEASE_DIR / "target_registry.schema.json"),
        (PAIRWISE / "pairwise_scenario_v1_3.schema.json", RELEASE_DIR / "pairwise_scenario_v1_3.schema.json"),
        (PAIRWISE / "tck_releases_v4.schema.json", RELEASE_DIR / "tck_releases_v4.schema.json"),
    ):
        expected[destination] = source.read_bytes()

    def path_digest(path: Path) -> str:
        content = expected.get(path)
        if content is None:
            return digest(path)
        return "sha256:" + hashlib.sha256(normalized_bytes_for_expected(content, path)).hexdigest()

    def expected_artifact(path: Path) -> dict[str, str]:
        return {"path": path.relative_to(ROOT).as_posix(), "content_digest": path_digest(path)}

    def write_bundle(
        name: str,
        entries: list[dict[str, str]],
        *,
        discovery: str,
    ) -> tuple[str, str]:
        value = {
            "manifest_version": "1.3",
            "release_id": RELEASE_1_3,
            "closure_discovery": discovery,
            "entries": entries,
        }
        path = PAIRWISE / name
        content = encoded_json(value)
        expected[path] = content
        return path.relative_to(ROOT).as_posix(), "sha256:" + hashlib.sha256(content).hexdigest()

    runner_closure = discover_import_closure([PAIRWISE / "aicp_pairwise_runner_v1_3.py"])
    evaluator_closure = discover_import_closure([PAIRWISE / "pairwise_report_evaluator_v1_3.py"])
    runner_entries = [
        {
            "path": path.relative_to(ROOT).as_posix(),
            "role": "in_process_runner_import_closure",
            "digest": path_digest(path),
        }
        for path in runner_closure
    ]
    evaluator_entries = [
        {
            "path": path.relative_to(ROOT).as_posix(),
            "role": "in_process_evaluator_import_closure",
            "digest": path_digest(path),
        }
        for path in evaluator_closure
    ]
    runner_path, runner_digest = write_bundle(
        "pairwise_runner_bundle_v1_3.json",
        runner_entries,
        discovery="transitive-python-ast-imports-from-runner-process-root",
    )
    evaluator_path, evaluator_digest = write_bundle(
        "pairwise_evaluator_bundle_v1_3.json",
        evaluator_entries,
        discovery="transitive-python-ast-imports-from-evaluator-process-root",
    )

    release_1_2 = load(PAIRWISE / "release_registry_snapshots" / f"{RELEASE_1_2}.json")["releases"][0]
    authority_root = PAIRWISE / "release_artifacts" / RELEASE_1_1 / "authority_root"
    authority_closure = discover_process_import_closure(
        [PAIRWISE / "pairwise_authority_bridge_v1_3.py"],
        (
            authority_root / "conformance" / "runner",
            authority_root / "conformance" / "evidence",
            authority_root / "reference" / "python",
            authority_root / "interop" / "pairwise",
            authority_root,
        ),
    )
    authority_entries = [
        {
            "path": path.relative_to(ROOT).as_posix(),
            "role": (
                "side_authority_process_entrypoint"
                if path == (PAIRWISE / "pairwise_authority_bridge_v1_3.py").resolve()
                else "side_authority_process_import_closure"
            ),
            "digest": path_digest(path),
        }
        for path in authority_closure
    ]
    existing_authority_paths = {item["path"] for item in authority_entries}
    authority_entries.extend(
        {
            "path": item["path"],
            "role": "shared_content_addressed_1_1_authority_data",
            "digest": item["content_digest"],
        }
        for item in release_1_2["underlying_authorities"]
        if item["path"] not in existing_authority_paths
    )
    authority_path, authority_digest = write_bundle(
        "pairwise_side_authority_bundle_v1_3.json",
        authority_entries,
        discovery="transitive-python-ast-imports-from-frozen-subprocess-roots-plus-declared-runtime-data",
    )

    release = {
        "release_id": RELEASE_1_3,
        "status": "publication-eligible",
        "registry_schema_digest": path_digest(RELEASE_DIR / "tck_releases_v4.schema.json"),
        "registry_schema": expected_artifact(RELEASE_DIR / "tck_releases_v4.schema.json"),
        "runner_bundle": {"path": runner_path, "digest": runner_digest},
        "evaluator_bundle": {"path": evaluator_path, "digest": evaluator_digest},
        "side_authority_bundle": {"path": authority_path, "digest": authority_digest},
        "report_schema": artifact("interop/pairwise/pairwise_joint_report_v1_3.schema.json"),
        "evaluator": artifact("interop/pairwise/pairwise_report_evaluator_v1_3.py"),
        "evaluator_api": "evaluate_pairwise_report.v1",
        "normalizer": artifact("interop/pairwise/pairwise_semantic_normalizer_v1_3.py"),
        "target_registry": {
            **expected_artifact(RELEASE_DIR / "targets.json"),
            "schema_path": (RELEASE_DIR / "target_registry.schema.json").relative_to(ROOT).as_posix(),
            "schema_digest": path_digest(RELEASE_DIR / "target_registry.schema.json"),
        },
        "scenario_catalog": {
            **expected_artifact(RELEASE_DIR / "scenarios.json"),
            "schema_path": (RELEASE_DIR / "pairwise_scenario_v1_3.schema.json").relative_to(ROOT).as_posix(),
            "schema_digest": path_digest(RELEASE_DIR / "pairwise_scenario_v1_3.schema.json"),
        },
        "mandatory_execution": {
            "target_id": TARGET_ID,
            "scenario_id": "PAIRWISE-MCP-RAW-ROLE-GLOBAL-CAUSALITY-03",
            "directions": ["A_TO_B", "B_TO_A"],
            "clean_run_count": 2,
            "transport_roles": ["client", "server"],
            "side_evidence": ["AICP-BASE@0.1/full-profile", "BIND-MCP@0.1/full-binding"],
        },
        "underlying_authorities": release_1_2["underlying_authorities"],
    }
    snapshot = {"registry_version": "4.0", "releases": [release]}
    expected[PAIRWISE / "release_registry_snapshots" / f"{RELEASE_1_3}.json"] = encoded_json(snapshot)

    old_releases = [
        load(PAIRWISE / "release_registry_snapshots" / f"{release_id}.json")["releases"][0]
        for release_id in (RELEASE_1_0, RELEASE_1_1, RELEASE_1_2)
    ]
    registry = {
        "registry_version": "4.0",
        "release_policies": [
            {
                "release_id": RELEASE_1_0,
                "lifecycle": "historical",
                "strong_eligible": False,
                "reason": "Mutable-authority provenance, incomplete actual-Core validation, and a non-load-bearing runtime challenge make this evidence release strong-ineligible.",
            },
            {
                "release_id": RELEASE_1_1,
                "lifecycle": "historical",
                "strong_eligible": False,
                "reason": "Joint MCP requests were repository-harness generated and Pairwise server processes were not bound to the exact participant builds.",
            },
            {
                "release_id": RELEASE_1_2,
                "lifecycle": "historical",
                "strong_eligible": False,
                "reason": "Per-run role identity was not independently derived from raw role evidence, first-seen causality was direction-local, and historical eligibility depended on mutable dispatcher/current-source provenance.",
            },
            {
                "release_id": RELEASE_1_3,
                "lifecycle": "current",
                "strong_eligible": True,
                "reason": "Raw per-run roles, run-global first-seen causality, exact cursor progression, and release-stable execution provenance are independently enforced.",
            },
        ],
        "releases": [*old_releases, release],
    }
    expected[PAIRWISE / "tck_releases.json"] = encoded_json(registry)
    return expected, registry


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--write-freeze-1-1", action="store_true")
    parser.add_argument("--write-freeze-1-2", action="store_true")
    args = parser.parse_args()
    if args.write_freeze_1_1:
        FREEZE_DIR.mkdir(parents=True, exist_ok=True)
        FREEZE_1_1.write_bytes(encoded_json(_freeze_manifest()))
        print(f"froze {len(_issued_1_1_paths())} issued {RELEASE_1_1} files")
        return 0
    if args.write_freeze_1_2:
        FREEZE_DIR.mkdir(parents=True, exist_ok=True)
        FREEZE_1_2.write_bytes(encoded_json(_freeze_1_2_manifest()))
        print(f"froze {len(_issued_1_2_paths())} issued {RELEASE_1_2} files")
        return 0
    frozen_errors = _freeze_errors()
    if frozen_errors:
        raise RuntimeError("Pairwise issued-release byte freeze failed: " + "; ".join(frozen_errors))

    expected, registry = build_expected_v1_3()
    from jsonschema import Draft202012Validator

    schema = load(PAIRWISE / "tck_releases_v4.schema.json")
    issues = list(Draft202012Validator(schema).iter_errors(registry))
    if issues:
        raise RuntimeError("Pairwise registry v4 invalid: " + "; ".join(issue.message for issue in issues))
    if registry["releases"][0] != load(PAIRWISE / "release_registry_snapshots" / f"{RELEASE_1_0}.json")["releases"][0]:
        raise RuntimeError("Pairwise TCK 1.0 release object changed")
    if registry["releases"][1] != load(PAIRWISE / "release_registry_snapshots" / f"{RELEASE_1_1}.json")["releases"][0]:
        raise RuntimeError("Pairwise TCK 1.1 release object changed")
    if registry["releases"][2] != load(PAIRWISE / "release_registry_snapshots" / f"{RELEASE_1_2}.json")["releases"][0]:
        raise RuntimeError("Pairwise TCK 1.2 release object changed")

    if args.check:
        stale = [
            path.relative_to(ROOT).as_posix()
            for path, content in expected.items()
            if not path.is_file() or normalized_bytes(path) != normalized_bytes_for_expected(content, path)
        ]
        release_files = {
            path for path in RELEASE_DIR.rglob("*") if path.is_file() and "__pycache__" not in path.parts
        } if RELEASE_DIR.is_dir() else set()
        extra = sorted(path.relative_to(ROOT).as_posix() for path in release_files - set(expected))
        if stale or extra:
            raise RuntimeError(
                "stale Pairwise TCK 1.3 artifacts: " + ", ".join(sorted(stale))
                + ("; unexpected release files: " + ", ".join(extra) if extra else "")
            )
        print(
            f"{RELEASE_1_0}/{RELEASE_1_1}/{RELEASE_1_2} freezes and "
            f"{RELEASE_1_3} immutable closures are current"
        )
        return 0

    for path, content in expected.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    print(
        f"generated {RELEASE_1_3}; files={len(expected)}; "
        f"runner_closure={len(discover_import_closure([PAIRWISE / 'aicp_pairwise_runner_v1_3.py']))}; "
        f"authority_tree_reused={RELEASE_1_1}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
