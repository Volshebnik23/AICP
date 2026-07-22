from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[2]
CASES_PATH = ROOT / "conformance/iut/cases.json"
TCK_RELEASES_PATH = ROOT / "conformance/iut/tck_releases.json"
PUBLIC_KEYS_REF = "fixtures/keys/GT_public_keys.json"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def normalized_file_digest(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix.lower() in {".json", ".jsonl", ".md", ".py", ".ts", ".mjs", ".yml", ".yaml"}:
        data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def runner_bundle_paths() -> list[str]:
    paths = [
        "conformance/iut/aicp_iut_runner.py",
        "conformance/iut/aicp_iut_catalog.py",
        "conformance/iut/_iut_evaluator.py",
    ]
    paths.extend(
        path.relative_to(ROOT).as_posix()
        for path in sorted((ROOT / "conformance/runner").glob("*.py"))
    )
    paths.extend(
        path.relative_to(ROOT).as_posix()
        for path in sorted((ROOT / "reference/python/aicp_ref").glob("*.py"))
    )
    return sorted(set(paths))


def bundle_digest(paths: Iterable[str]) -> str:
    digest = hashlib.sha256()
    for ref in sorted(set(paths)):
        path = ROOT / ref
        digest.update(ref.encode("utf-8"))
        digest.update(b"\0")
        data = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        digest.update(data)
        digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def profile_config(catalog: dict[str, Any], profile: str) -> dict[str, Any]:
    config = catalog.get("profiles", {}).get(profile)
    if not isinstance(config, dict):
        raise ValueError(f"unsupported IUT target profile: {profile}")
    return config


def _by_id(items: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item["case_id"]): item for item in items}


def selected_cases(
    catalog: dict[str, Any], profile: str, mode: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    config = profile_config(catalog, profile)
    full = config["full_profile"]
    producers = list(full["producer_scenarios"])
    consumers = list(full["consumer_cases"])
    if mode == "full-profile":
        return producers, consumers
    if mode != "smoke":
        raise ValueError("IUT mode must be 'smoke' or 'full-profile'")
    smoke = config["smoke"]
    producer_map = _by_id(producers)
    consumer_map = _by_id(consumers)
    try:
        return (
            [producer_map[case_id] for case_id in smoke["producer_case_refs"]],
            [consumer_map[case_id] for case_id in smoke["consumer_case_refs"]],
        )
    except KeyError as exc:
        raise ValueError(f"smoke case reference does not resolve: {exc.args[0]}") from exc


def mandatory_case_ids(
    catalog: dict[str, Any],
    profile: str,
    mode: str,
    *,
    include_session_state_projection: bool = False,
) -> list[str]:
    producers, consumers = selected_cases(catalog, profile, mode)
    ids = ["IUT-CATALOG-COVERAGE-01", "IUT-DESCRIBE-01"]
    for vector_ref in catalog["canonicalization_vectors"]:
        vector = load_json(ROOT / vector_ref)
        ids.append(str(vector["vector_id"]))
    ids.extend(str(item["case_id"]) for item in producers)
    ids.extend(str(item["case_id"]) for item in consumers)
    if include_session_state_projection:
        state = catalog["session_state_projection"]
        ids.append(str(state["producer_case"]["case_id"]))
        ids.append("SESSION-STATE-PROJECTION-V1-HASH")
        ids.extend(str(item["case_id"]) for item in state["consumer_cases"])
    ids.extend(["IUT-DESCRIBE-STABILITY-01", "IUT-PROFILE-SUPPORT-01"])
    if profile == "AICP-AUTHENTICATED-BASE@0.1":
        ids.append("IUT-CRYPTO-SUPPORT-01")
    if include_session_state_projection:
        ids.append("IUT-STATE-SUPPORT-01")
    if len(ids) != len(set(ids)):
        raise ValueError("mandatory IUT case IDs are not unique")
    return ids


def validate_catalog_coverage(catalog: dict[str, Any], profile: str) -> list[str]:
    errors: list[str] = []
    config = profile_config(catalog, profile)
    profile_catalog = load_json(ROOT / config["profile_catalog"])
    required_suites = list(config["required_suites"])
    if required_suites != profile_catalog.get("required_suites"):
        errors.append("IUT required_suites do not exactly match the profile catalog")

    full = config["full_profile"]
    consumers = list(full["consumer_cases"])
    producers = list(full["producer_scenarios"])
    all_case_ids = [str(item.get("case_id")) for item in producers + consumers]
    if len(all_case_ids) != len(set(all_case_ids)):
        errors.append("full-profile producer/consumer case IDs must be unique")

    positive_core_types: set[str] = set()
    for suite_ref in required_suites:
        suite = load_json(ROOT / suite_ref)
        suite_cases = {
            str(item["id"]): item
            for item in suite.get("transcripts", [])
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        represented = [
            str(item["suite_case_id"])
            for item in consumers
            if item.get("suite_ref") == suite_ref and not item.get("additional")
        ]
        if len(represented) != len(set(represented)):
            errors.append(f"{suite_ref} has duplicate mandatory suite_case_id mappings")
        missing = sorted(set(suite_cases) - set(represented))
        unknown = sorted(set(represented) - set(suite_cases))
        if missing:
            errors.append(f"{suite_ref} is missing IUT consumer coverage for {missing}")
        if unknown:
            errors.append(f"{suite_ref} has unknown IUT suite_case_id values {unknown}")
        if suite.get("suite_id") == "CT-CORE-0.1":
            for item in suite_cases.values():
                if item.get("expect_pass", True):
                    positive_core_types.update(
                        value for value in item.get("expected_message_types", []) if isinstance(value, str)
                    )

    produced_types = {
        value
        for producer in producers
        for value in producer.get("scenario", {}).get("desired_message_types", [])
        if isinstance(value, str)
    }
    missing_producer_types = sorted(positive_core_types - produced_types)
    if missing_producer_types:
        errors.append(f"producer scenarios omit positive Core message types {missing_producer_types}")

    for item in producers:
        if not (ROOT / str(item.get("template_fixture", ""))).is_file():
            errors.append(f"producer template fixture is missing for {item.get('case_id')}")
    for item in consumers:
        if not (ROOT / str(item.get("fixture", ""))).is_file():
            errors.append(f"consumer fixture is missing for {item.get('case_id')}")

    # Resolving smoke refs is itself part of catalog validation.
    try:
        selected_cases(catalog, profile, "smoke")
    except ValueError as exc:
        errors.append(str(exc))
    return errors


def required_input_paths(catalog: dict[str, Any], profile: str) -> list[str]:
    config = profile_config(catalog, profile)
    paths = {
        "conformance/iut/cases.json",
        "conformance/iut/adapter_protocol.schema.json",
        "conformance/iut/iut_report_v1.schema.json",
        PUBLIC_KEYS_REF,
        str(config["profile_catalog"]),
        *[str(ref) for ref in catalog["canonicalization_vectors"]],
        *[str(ref) for ref in config["required_suites"]],
    }
    full = config["full_profile"]
    paths.update(str(item["template_fixture"]) for item in full["producer_scenarios"])
    paths.update(str(item["fixture"]) for item in full["consumer_cases"])
    return sorted(paths)


def load_tck_release(catalog: dict[str, Any]) -> dict[str, Any]:
    registry = load_json(TCK_RELEASES_PATH)
    release_id = catalog.get("tck_release_id")
    for release in registry.get("releases", []):
        if isinstance(release, dict) and release.get("release_id") == release_id:
            return release
    raise ValueError(f"IUT case catalog references unregistered TCK release {release_id!r}")
