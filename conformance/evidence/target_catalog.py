from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = ROOT / "conformance" / "evidence"
TARGETS_PATH = EVIDENCE_DIR / "targets.json"
TARGET_CATALOG_PATH = EVIDENCE_DIR / "session_state_projection_v1_target.json"
REPORT_SCHEMA_PATH = EVIDENCE_DIR / "external_evidence_report_v2.schema.json"
TARGET_SCHEMA_PATH = EVIDENCE_DIR / "target_registry.schema.json"
TCK_RELEASES_PATH = EVIDENCE_DIR / "evidence_tck_releases.json"
EXPECTATIONS_PATH = EVIDENCE_DIR / "projection_v1_expectations.json"
TARGET_KEY = "aicp.session_state_projection@v1"
TARGET_ID = "aicp.session_state_projection"
TARGET_VERSION = "v1"
EXPECTED_MARK = "AICP-Evidence-SESSION-STATE-PROJECTION-v1"
TCK_RELEASE_ID = "AICP-EVIDENCE-TCK-1.0.0"
SUPPORTED_TARGET_KINDS = {"capability"}


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def normalized_bytes(path: Path) -> bytes:
    return path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def digest_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(
        data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    ).hexdigest()


def file_digest(path: Path) -> str:
    return digest_bytes(path.read_bytes())


def canonical_digest(value: Any) -> str:
    data = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return digest_bytes(data)


def runner_bundle_paths() -> list[str]:
    return [
        "conformance/evidence/aicp_external_evidence_runner.py",
        "conformance/evidence/report_evaluator.py",
        "conformance/evidence/target_catalog.py",
        "conformance/iut/_iut_evaluator.py",
        "conformance/iut/aicp_iut_runner.py",
        "conformance/runner/_runner_context.py",
        "conformance/runner/_runner_provenance.py",
        "conformance/runner/_runner_state_projection_checks.py",
        "conformance/runner/aicp_conformance_runner.py",
        "reference/python/aicp_ref/hashing.py",
        "reference/python/aicp_ref/jcs.py",
        "reference/python/aicp_ref/session_state.py",
        "reference/python/aicp_ref/signatures.py",
    ]


def bundle_digest(
    paths: list[str],
    *,
    root: Path = ROOT,
    overrides: dict[str, bytes] | None = None,
) -> str:
    digest = hashlib.sha256()
    replacements = overrides or {}
    for relative in sorted(paths):
        digest.update(relative.encode("utf-8"))
        digest.update(b"\0")
        data = replacements.get(relative)
        if data is None:
            data = normalized_bytes(root / relative)
        else:
            data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        digest.update(data)
    return "sha256:" + digest.hexdigest()


def target_registry() -> dict[str, Any]:
    value = load_json(TARGETS_PATH)
    if not isinstance(value, dict):
        raise ValueError("evidence target registry must be an object")
    return value


def target_catalog() -> dict[str, Any]:
    value = load_json(TARGET_CATALOG_PATH)
    if not isinstance(value, dict):
        raise ValueError("evidence target catalog must be an object")
    return value


def release_registry() -> dict[str, Any]:
    value = load_json(TCK_RELEASES_PATH)
    if not isinstance(value, dict):
        raise ValueError("evidence TCK release registry must be an object")
    return value


def target_record(target_key: str = TARGET_KEY) -> dict[str, Any]:
    matches = [
        item
        for item in target_registry().get("targets", [])
        if isinstance(item, dict) and item.get("target_key") == target_key
    ]
    if len(matches) != 1:
        raise ValueError(f"target must resolve exactly once: {target_key}")
    record = matches[0]
    if record.get("target_kind") not in SUPPORTED_TARGET_KINDS:
        raise ValueError(
            f"target kind is registered but not executable in M62: {record.get('target_kind')}"
        )
    return record


def release_record(release_id: str = TCK_RELEASE_ID) -> dict[str, Any]:
    matches = [
        item
        for item in release_registry().get("releases", [])
        if isinstance(item, dict) and item.get("release_id") == release_id
    ]
    if len(matches) != 1:
        raise ValueError(f"evidence TCK release must resolve exactly once: {release_id}")
    return matches[0]


def expected_input_artifacts(release: dict[str, Any]) -> list[dict[str, str]]:
    target = release.get("target")
    if not isinstance(target, dict):
        return []
    values = target.get("required_input_artifacts")
    return [
        {"path": str(item["path"]), "content_digest": str(item["content_digest"])}
        for item in values or []
        if isinstance(item, dict)
        and isinstance(item.get("path"), str)
        and isinstance(item.get("content_digest"), str)
    ]


def expected_suite_records(release: dict[str, Any]) -> list[dict[str, str]]:
    target = release.get("target")
    if not isinstance(target, dict):
        return []
    return [
        {
            "suite_id": str(item["suite_id"]),
            "suite_version": str(item["suite_version"]),
            "path": str(item["path"]),
            "suite_digest": str(item["suite_digest"]),
        }
        for item in target.get("required_suites", []) or []
        if isinstance(item, dict)
    ]


def consumer_cases(catalog: dict[str, Any], mode: str) -> list[dict[str, Any]]:
    cases = list(catalog.get("consumer_cases", []))
    if mode == "smoke":
        return [case for case in cases if case.get("source_case_id") == "SP-01"]
    if mode != "full-capability":
        raise ValueError("execution mode must be full-capability or smoke")
    return cases


def mandatory_case_ids(catalog: dict[str, Any], mode: str) -> list[str]:
    ids = [
        "EVIDENCE-TARGET-CATALOG-01",
        "EVIDENCE-TCK-PROVENANCE-01",
        "EVIDENCE-DESCRIBE-START-01",
    ]
    ids.extend(
        str(item["case_id"])
        for item in catalog.get("canonicalization_vectors", [])
    )
    ids.append(str(catalog["producer_case"]["case_id"]))
    ids.extend(str(item["case_id"]) for item in consumer_cases(catalog, mode))
    ids.extend(
        [
            "EVIDENCE-DESCRIBE-STABILITY-01",
            "EVIDENCE-TARGET-SUPPORT-01",
        ]
    )
    return ids


def validate_target_registry(
    registry: dict[str, Any] | None = None,
    *,
    root: Path = ROOT,
) -> list[str]:
    value = registry if registry is not None else target_registry()
    errors: list[str] = []
    targets = value.get("targets") if isinstance(value, dict) else None
    if not isinstance(targets, list) or not targets:
        return ["target registry must contain a non-empty targets array"]
    keys = [item.get("target_key") for item in targets if isinstance(item, dict)]
    marks = [item.get("expected_mark") for item in targets if isinstance(item, dict)]
    if len(keys) != len(set(keys)):
        errors.append("target keys must be unique")
    if len(marks) != len(set(marks)):
        errors.append("target expected marks must be unique")
    for item in targets:
        if not isinstance(item, dict):
            errors.append("target records must be objects")
            continue
        expected_key = f"{item.get('target_id')}@{item.get('target_version')}"
        if item.get("target_key") != expected_key:
            errors.append(f"target key does not exactly match ID/version: {item.get('target_key')}")
        if item.get("target_kind") not in SUPPORTED_TARGET_KINDS:
            errors.append(f"unsupported executable target kind: {item.get('target_kind')}")
        for path in [item.get("target_catalog"), *item.get("required_suites", [])]:
            if not isinstance(path, str) or not (root / path).is_file():
                errors.append(f"target registry path does not resolve: {path}")
    if keys != [TARGET_KEY]:
        errors.append("M62 must register exactly projection v1 and no projection v2 target")
    return sorted(set(errors))


def validate_target_catalog(
    catalog: dict[str, Any] | None = None,
    *,
    root: Path = ROOT,
) -> list[str]:
    value = catalog if catalog is not None else target_catalog()
    errors: list[str] = []
    suite_ref = value.get("owning_suite", {}).get("path")
    if not isinstance(suite_ref, str) or not (root / suite_ref).is_file():
        return ["target catalog owning suite does not resolve"]
    suite = load_json(root / suite_ref)
    source_cases = {
        str(item["id"]): item
        for item in suite.get("transcripts", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    consumers = value.get("consumer_cases")
    if not isinstance(consumers, list):
        return ["target catalog consumer_cases must be an array"]
    observed = [str(item.get("source_case_id")) for item in consumers if isinstance(item, dict)]
    if Counter(observed) != Counter(source_cases.keys()):
        errors.append("target catalog must cover every owning-suite transcript exactly once")
    for item in consumers:
        if not isinstance(item, dict):
            continue
        source_id = str(item.get("source_case_id"))
        source = source_cases.get(source_id)
        if source is None:
            errors.append(f"unknown source transcript: {source_id}")
            continue
        expected_accepted = source.get("expect_pass", True) is True
        if item.get("accepted") is not expected_accepted:
            errors.append(f"consumer acceptance drifts from owning suite: {source_id}")
        suite_codes = [
            str(failure.get("test_id"))
            for failure in source.get("expected_failures", [])
            if isinstance(failure, dict)
        ]
        actual_codes = [
            str(code) for code in item.get("expected_error_codes", [])
        ]
        if any(code not in actual_codes for code in suite_codes):
            errors.append(f"consumer errors omit owning-suite expectation: {source_id}")
        fixture = item.get("fixture")
        if fixture != source.get("path"):
            errors.append(f"consumer fixture drifts from owning suite: {source_id}")
    producer = value.get("producer_case")
    if not isinstance(producer, dict):
        errors.append("target catalog producer case is missing")
    elif producer.get("source_case_id") != "SP-01":
        errors.append("projection v1 producer must use neutral SP-01")
    ids = mandatory_case_ids(value, "full-capability")
    if len(ids) != len(set(ids)):
        errors.append("mandatory evidence case IDs must be unique")
    for item in value.get("required_input_artifacts", []):
        if not isinstance(item, dict):
            errors.append("required input artifact records must be objects")
            continue
        relative = item.get("path")
        if not isinstance(relative, str) or not (root / relative).is_file():
            errors.append(f"required input artifact does not resolve: {relative}")
            continue
        if item.get("content_digest") != file_digest(root / relative):
            errors.append(f"required input digest is stale: {relative}")
    owning = value.get("owning_suite", {})
    if owning.get("suite_digest") != file_digest(root / suite_ref):
        errors.append("owning suite digest is stale")
    if value.get("target") != {
        "kind": "capability",
        "target_id": TARGET_ID,
        "target_version": TARGET_VERSION,
    }:
        errors.append("target catalog identity is not exact projection v1")
    return sorted(set(errors))


def validate_release_registry(
    registry: dict[str, Any] | None = None,
    *,
    root: Path = ROOT,
) -> list[str]:
    value = registry if registry is not None else release_registry()
    errors: list[str] = []
    releases = value.get("releases") if isinstance(value, dict) else None
    if not isinstance(releases, list) or len(releases) != 1:
        return ["M62 evidence TCK registry must contain exactly one release"]
    release = releases[0]
    if release.get("release_id") != TCK_RELEASE_ID:
        errors.append("unexpected evidence TCK release ID")
    checks = {
        release.get("report_schema", {}).get("content_digest"): file_digest(
            root / "conformance/evidence/external_evidence_report_v2.schema.json"
        ),
        release.get("target_registry", {}).get("content_digest"): file_digest(
            root / "conformance/evidence/targets.json"
        ),
        release.get("target", {}).get("target_catalog", {}).get("content_digest"): file_digest(
            root / "conformance/evidence/session_state_projection_v1_target.json"
        ),
        release.get("runner_bundle", {}).get("digest"): bundle_digest(
            release.get("runner_bundle", {}).get("paths", []), root=root
        ),
    }
    if any(actual != expected for actual, expected in checks.items()):
        errors.append("evidence TCK release provenance does not match current bytes")
    for item in expected_input_artifacts(release):
        if file_digest(root / item["path"]) != item["content_digest"]:
            errors.append(f"evidence TCK input digest is stale: {item['path']}")
    return sorted(set(errors))
