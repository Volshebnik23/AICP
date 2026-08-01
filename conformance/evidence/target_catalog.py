from __future__ import annotations

import ast
import hashlib
import json
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = ROOT / "conformance" / "evidence"
RUNNER_DIR = ROOT / "conformance" / "runner"
if str(RUNNER_DIR) not in sys.path:
    sys.path.insert(0, str(RUNNER_DIR))

from _runner_context import build_validator  # noqa: E402


TARGETS_PATH = EVIDENCE_DIR / "targets.json"
TARGET_SCHEMA_PATH = EVIDENCE_DIR / "target_registry.schema.json"
TARGET_CATALOG_PATH = EVIDENCE_DIR / "session_state_projection_v1_target.json"
REPORT_SCHEMA_PATH = EVIDENCE_DIR / "external_evidence_report_v2.schema.json"
TCK_RELEASES_PATH = EVIDENCE_DIR / "evidence_tck_releases.json"
EXPECTATIONS_PATH = EVIDENCE_DIR / "projection_v1_expectations.json"
BUNDLE_MANIFEST_PATH = EVIDENCE_DIR / "evidence_runner_bundle.json"
PRODUCER_SCENARIO_PATH = EVIDENCE_DIR / "projection_v1_producer_scenario.json"
PRODUCER_TRANSCRIPT_PATH = EVIDENCE_DIR / "projection_v1_producer_transcript.json"
PRODUCER_SCENARIO_SCHEMA_PATH = (
    EVIDENCE_DIR / "projection_v1_producer_scenario.schema.json"
)
TARGET_KEY = "aicp.session_state_projection@v1"
TARGET_ID = "aicp.session_state_projection"
TARGET_VERSION = "v1"
EXPECTED_MARK = "AICP-Evidence-SESSION-STATE-PROJECTION-v1"
TCK_RELEASE_ID = "AICP-EVIDENCE-TCK-1.1.0"
HISTORICAL_TCK_RELEASE_ID = "AICP-EVIDENCE-TCK-1.0.0"
HISTORICAL_RELEASE_RECORD_DIGEST = (
    "sha256:e227fdb2b2d35f83cfeeceff6e80f455ff8a95a1e56244bb6d4433942c53ba80"
)
HISTORICAL_TARGET_SCHEMA_DIGEST = (
    "sha256:a4d63416e0e387ef3e6bff0d3b9397e37a2f380961360a5e4d63096228bcfc50"
)
HISTORICAL_RELEASE_REGISTRY_DIGEST = (
    "sha256:bbc549d1d0ca6344de41a149430c25e257cf3438845f6e4ccdf0eab17f81ceaf"
)
TARGET_KINDS = {"product_profile", "capability", "binding"}


@dataclass(frozen=True)
class TargetRecord:
    target_key: str
    target_kind: str
    target_id: str
    target_version: str
    status: str
    catalog_path: str
    expected_mark: str
    execution_mode: str
    evidence_claim_type: str
    handler_id: str
    current_release_id: str
    required_suites: tuple[str, ...]
    required_operations: tuple[str, ...]

    @classmethod
    def from_mapping(cls, item: dict[str, Any]) -> "TargetRecord":
        return cls(
            target_key=str(item["target_key"]),
            target_kind=str(item["target_kind"]),
            target_id=str(item["target_id"]),
            target_version=str(item["target_version"]),
            status=str(item["status"]),
            catalog_path=str(item["catalog_path"]),
            expected_mark=str(item["expected_mark"]),
            execution_mode=str(item["execution_mode"]),
            evidence_claim_type=str(item["evidence_claim_type"]),
            handler_id=str(item["handler_id"]),
            current_release_id=str(item["current_release_id"]),
            required_suites=tuple(str(value) for value in item["required_suites"]),
            required_operations=tuple(
                str(value) for value in item["required_operations"]
            ),
        )

    def identity(self) -> dict[str, str]:
        return {
            "kind": self.target_kind,
            "target_id": self.target_id,
            "target_version": self.target_version,
        }


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


def canonical_target_key(kind: str, target_id: str, version: str) -> str:
    if kind not in TARGET_KINDS:
        raise ValueError(f"unknown evidence target kind: {kind}")
    for label, value in (("target_id", target_id), ("target_version", version)):
        if (
            not isinstance(value, str)
            or not value
            or "@" in value
            or any(character.isspace() for character in value)
        ):
            raise ValueError(f"{label} must be a non-empty unambiguous exact value")
    return f"{target_id}@{version}"


def target_registry() -> dict[str, Any]:
    value = load_json(TARGETS_PATH)
    if not isinstance(value, dict):
        raise ValueError("evidence target registry must be an object")
    return value


def release_registry() -> dict[str, Any]:
    value = load_json(TCK_RELEASES_PATH)
    if not isinstance(value, dict):
        raise ValueError("evidence TCK release registry must be an object")
    return value


def resolve_target_record(
    target_key: str,
    registry: dict[str, Any] | None = None,
) -> TargetRecord:
    value = registry if registry is not None else target_registry()
    matches = [
        item
        for item in value.get("targets", [])
        if isinstance(item, dict) and item.get("target_key") == target_key
    ]
    if len(matches) != 1:
        raise ValueError(f"target must resolve exactly once: {target_key}")
    record = TargetRecord.from_mapping(matches[0])
    if record.target_key != canonical_target_key(
        record.target_kind,
        record.target_id,
        record.target_version,
    ):
        raise ValueError("target key is ambiguous or does not match exact identity")
    return record


def target_record(target_key: str = TARGET_KEY) -> TargetRecord:
    return resolve_target_record(target_key)


def target_catalog(record: TargetRecord | None = None) -> dict[str, Any]:
    selected = record or target_record()
    value = load_json(ROOT / selected.catalog_path)
    if not isinstance(value, dict):
        raise ValueError("evidence target catalog must be an object")
    return value


def release_record(
    release_id: str = TCK_RELEASE_ID,
    registry: dict[str, Any] | None = None,
) -> dict[str, Any]:
    value = registry if registry is not None else release_registry()
    matches = [
        item
        for item in value.get("releases", [])
        if isinstance(item, dict) and item.get("release_id") == release_id
    ]
    if len(matches) != 1:
        raise ValueError(
            f"evidence TCK release must resolve exactly once: {release_id}"
        )
    return matches[0]


def release_supersession(
    release_id: str,
    registry: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    value = registry if registry is not None else release_registry()
    for item in value.get("supersessions", []):
        if isinstance(item, dict) and item.get("release_id") == release_id:
            return item
    return None


def expected_input_artifacts(release: dict[str, Any]) -> list[dict[str, str]]:
    target = release.get("target")
    if not isinstance(target, dict):
        return []
    return [
        {
            "path": str(item["path"]),
            "content_digest": str(item["content_digest"]),
        }
        for item in target.get("required_input_artifacts", []) or []
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


def mandatory_case_ids(
    catalog: dict[str, Any],
    mode: str,
    handler: Any,
) -> list[str]:
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
    ids.extend(
        str(item["case_id"])
        for item in handler.consumer_cases(catalog, mode)
    )
    ids.extend(
        ["EVIDENCE-DESCRIBE-STABILITY-01", "EVIDENCE-TARGET-SUPPORT-01"]
    )
    return ids


def _registered_reference_valid(
    record: TargetRecord,
    *,
    root: Path,
) -> bool:
    if record.target_kind == "capability":
        return (
            record.target_id == TARGET_ID
            and record.target_version == TARGET_VERSION
        )
    if record.target_kind == "product_profile":
        profiles = load_json(root / "registry/aicp_profiles.json")
        return any(
            isinstance(item, dict)
            and item.get("profile_id") == record.target_id
            and item.get("profile_version") == record.target_version
            for item in profiles
        )
    bindings = load_json(root / "registry/transport_bindings.json")
    canonical_id = f"{record.target_id}-{record.target_version}"
    return any(
        isinstance(item, dict)
        and item.get("id") == canonical_id
        and item.get("status") != "deprecated"
        for item in bindings
    )


def validate_target_registry(
    registry: dict[str, Any] | None = None,
    *,
    root: Path = ROOT,
    simulate_no_jsonschema: bool = False,
    require_repository_references: bool = True,
    enforce_current_scope: bool | None = None,
) -> list[str]:
    value = registry if registry is not None else target_registry()
    errors: list[str] = []
    if enforce_current_scope is None:
        enforce_current_scope = registry is None
    schema_path = root / "conformance/evidence/target_registry.schema.json"
    schema = load_json(schema_path)
    validator = None if simulate_no_jsonschema else build_validator(schema, schema_path)
    if validator is None:
        errors.append(
            "jsonschema is required to validate the evidence target registry"
        )
    else:
        for issue in sorted(
            validator.iter_errors(value),
            key=lambda item: list(item.path),
        ):
            pointer = "/" + "/".join(str(part) for part in issue.path)
            errors.append(f"target registry schema error at {pointer}: {issue.message}")

    targets = value.get("targets") if isinstance(value, dict) else None
    if not isinstance(targets, list) or not targets:
        return sorted(set([*errors, "target registry must contain targets"]))
    keys: list[str] = []
    marks: list[str] = []
    identities: list[tuple[str, str, str]] = []
    identities_by_key: dict[str, set[tuple[str, str, str]]] = {}
    for item in targets:
        if not isinstance(item, dict):
            errors.append("target records must be objects")
            continue
        try:
            record = TargetRecord.from_mapping(item)
            expected_key = canonical_target_key(
                record.target_kind,
                record.target_id,
                record.target_version,
            )
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"invalid target record: {exc}")
            continue
        keys.append(record.target_key)
        marks.append(record.expected_mark)
        identity = (
            record.target_kind,
            record.target_id,
            record.target_version,
        )
        identities.append(identity)
        identities_by_key.setdefault(record.target_key, set()).add(identity)
        if record.target_key != expected_key:
            errors.append(
                f"target key does not exactly match identity: {record.target_key}"
            )
        if require_repository_references and not _registered_reference_valid(
            record,
            root=root,
        ):
            errors.append(
                f"target identity is not registered: {record.target_key}"
            )
        for relative in (record.catalog_path, *record.required_suites):
            if not (root / relative).is_file():
                errors.append(f"target registry path does not resolve: {relative}")
    if len(keys) != len(set(keys)):
        errors.append("target keys must be unique")
    if len(marks) != len(set(marks)):
        errors.append("target expected marks must be unique")
    if len(identities) != len(set(identities)):
        errors.append("exact target identities must be unique")
    if any(len(values) != 1 for values in identities_by_key.values()):
        errors.append("the same target key maps to different identities")
    if enforce_current_scope and keys != [TARGET_KEY]:
        errors.append(
            "M62 correction must register only projection v1 as a real target"
        )
    return sorted(set(errors))


def validate_target_catalog(
    catalog: dict[str, Any] | None = None,
    *,
    record: TargetRecord | None = None,
    handler: Any | None = None,
    root: Path = ROOT,
    simulate_no_jsonschema: bool = False,
) -> list[str]:
    selected = record or target_record()
    value = catalog if catalog is not None else target_catalog(selected)
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
    observed = [
        str(item.get("source_case_id"))
        for item in consumers
        if isinstance(item, dict)
    ]
    if Counter(observed) != Counter(source_cases.keys()):
        errors.append(
            "target catalog must cover every owning-suite transcript exactly once"
        )
    if value.get("consumer_error_ordering") != (
        "observation-list order, repeated code exact_count times"
    ):
        errors.append("consumer error ordering semantics are not explicit")
    for item in consumers:
        if not isinstance(item, dict):
            errors.append("consumer case records must be objects")
            continue
        source_id = str(item.get("source_case_id"))
        source = source_cases.get(source_id)
        if source is None:
            errors.append(f"unknown source transcript: {source_id}")
            continue
        expected_accepted = source.get("expect_pass", True) is True
        if item.get("accepted") is not expected_accepted:
            errors.append(f"consumer acceptance drifts from owning suite: {source_id}")
        suite_codes = Counter(
            str(failure.get("test_id"))
            for failure in source.get("expected_failures", [])
            if isinstance(failure, dict)
        )
        observations = item.get("expected_error_observations")
        if not isinstance(observations, list):
            errors.append(f"consumer observations are missing: {source_id}")
            continue
        reviewed_counts: Counter[str] = Counter()
        for observation in observations:
            if not isinstance(observation, dict):
                errors.append(f"consumer observation must be an object: {source_id}")
                continue
            code = observation.get("code")
            count = observation.get("exact_count")
            scope = observation.get("check_scope")
            if not isinstance(code, str) or not code:
                errors.append(f"consumer observation code is invalid: {source_id}")
                continue
            if not isinstance(count, int) or isinstance(count, bool) or count < 1:
                errors.append(f"consumer observation count is invalid: {source_id}")
                continue
            if not isinstance(scope, str) or not scope:
                errors.append(f"consumer observation scope is missing: {source_id}")
            reviewed_counts[code] += count
            if count > suite_codes[code] and not observation.get(
                "supplemental_reason"
            ):
                errors.append(
                    f"supplemental consumer observation lacks rationale: {source_id}/{code}"
                )
        if any(reviewed_counts[code] < count for code, count in suite_codes.items()):
            errors.append(
                f"consumer observations omit owning-suite expectation: {source_id}"
            )
        fixture = item.get("fixture")
        if fixture != source.get("path"):
            errors.append(f"consumer fixture drifts from owning suite: {source_id}")
    producer = value.get("producer_case")
    if not isinstance(producer, dict):
        errors.append("target catalog producer case is missing")
    ids = (
        mandatory_case_ids(value, "full-capability", handler)
        if handler is not None
        else []
    )
    if ids and len(ids) != len(set(ids)):
        errors.append("mandatory evidence case IDs must be unique")
    for artifact in value.get("required_input_artifacts", []):
        if not isinstance(artifact, dict):
            errors.append("required input artifact records must be objects")
            continue
        relative = artifact.get("path")
        if not isinstance(relative, str) or not (root / relative).is_file():
            errors.append(f"required input artifact does not resolve: {relative}")
            continue
        if artifact.get("content_digest") != file_digest(root / relative):
            errors.append(f"required input digest is stale: {relative}")
    owning = value.get("owning_suite", {})
    if owning.get("suite_digest") != file_digest(root / suite_ref):
        errors.append("owning suite digest is stale")
    if value.get("target") != selected.identity():
        errors.append("target catalog identity does not match the registry record")
    if value.get("target_key") != selected.target_key:
        errors.append("target catalog key does not match the registry record")
    if value.get("expected_mark") != selected.expected_mark:
        errors.append("target catalog mark does not match the registry record")
    if handler is not None:
        errors.extend(
            handler.validate_catalog(
                value,
                simulate_no_jsonschema=simulate_no_jsonschema,
            )
        )
    return sorted(set(errors))


_BUNDLE_SEEDS = (
    "conformance/evidence/aicp_external_evidence_runner.py",
    "conformance/evidence/report_evaluator.py",
    "conformance/evidence/target_catalog.py",
    "conformance/evidence/target_handlers.py",
)
_BUNDLE_ROLES = {
    "conformance/evidence/aicp_external_evidence_runner.py": "runner",
    "conformance/evidence/report_evaluator.py": "evaluator",
    "conformance/evidence/target_catalog.py": "target_dispatch",
    "conformance/evidence/target_handlers.py": "target_dispatch",
    "conformance/evidence/projection_v1_handler.py": "target_handler",
    "conformance/evidence/adapter_process.py": "process_supervision",
    "conformance/runner/_runner_context.py": "report_schema_support",
    "reference/python/aicp_ref/hashing.py": "canonicalization",
    "reference/python/aicp_ref/jcs.py": "canonicalization",
    "reference/python/aicp_ref/signatures.py": "dependency_probe",
    "reference/python/aicp_ref/__init__.py": "package_initialization",
}


def _local_module_map(root: Path) -> dict[str, str]:
    modules: dict[str, str] = {}
    roots = (
        root / "conformance/evidence",
        root / "conformance/runner",
        root / "conformance/iut",
        root / "reference/python",
    )
    for base in roots:
        if not base.is_dir():
            continue
        for path in base.rglob("*.py"):
            relative = path.relative_to(root).as_posix()
            if base == root / "reference/python":
                parts = list(path.relative_to(base).with_suffix("").parts)
                if parts[-1] == "__init__":
                    parts = parts[:-1]
                module = ".".join(parts)
            else:
                module = path.stem
            if module:
                modules.setdefault(module, relative)
    return modules


def _module_for_path(path: str) -> str:
    relative = Path(path)
    if path.startswith("reference/python/"):
        parts = list(relative.relative_to("reference/python").with_suffix("").parts)
        if parts[-1] == "__init__":
            parts = parts[:-1]
        return ".".join(parts)
    return relative.stem


def _resolve_imports(
    path: str,
    data: bytes,
    modules: dict[str, str],
) -> set[str]:
    tree = ast.parse(data.decode("utf-8"), filename=path)
    importer = _module_for_path(path)
    found: set[str] = set()
    for node in ast.walk(tree):
        names: list[str] = []
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level:
                base = importer.split(".")[:-1]
                if node.level > 1:
                    base = base[: -(node.level - 1)]
                module = ".".join([*base, module] if module else base)
            names.append(module)
        for name in names:
            candidate = modules.get(name)
            if candidate is not None:
                found.add(candidate)
                parts = name.split(".")
                for index in range(1, len(parts)):
                    parent = modules.get(".".join(parts[:index]))
                    if parent is not None:
                        found.add(parent)
    return found


def runtime_import_closure(
    *,
    root: Path = ROOT,
    overrides: dict[str, bytes] | None = None,
) -> list[str]:
    modules = _local_module_map(root)
    replacements = overrides or {}
    closure = set(_BUNDLE_SEEDS)
    pending = list(_BUNDLE_SEEDS)
    while pending:
        relative = pending.pop()
        data = replacements.get(relative)
        if data is None:
            data = (root / relative).read_bytes()
        for imported in _resolve_imports(relative, data, modules):
            if imported not in closure:
                closure.add(imported)
                pending.append(imported)
    return sorted(closure)


def runner_bundle_paths() -> list[str]:
    return runtime_import_closure()


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


def bundle_manifest_payload(
    *,
    root: Path = ROOT,
    overrides: dict[str, bytes] | None = None,
) -> dict[str, Any]:
    paths = runtime_import_closure(root=root, overrides=overrides)
    replacements = overrides or {}
    entries = []
    for relative in paths:
        data = replacements.get(relative)
        digest = (
            digest_bytes(data)
            if data is not None
            else file_digest(root / relative)
        )
        entries.append(
            {
                "path": relative,
                "role": _BUNDLE_ROLES.get(relative, "runtime_dependency"),
                "digest": digest,
            }
        )
    return {
        "manifest_version": "1.0",
        "entries": entries,
        "bundle_digest": bundle_digest(
            paths,
            root=root,
            overrides=overrides,
        ),
    }


def validate_bundle_manifest(
    manifest: dict[str, Any] | None = None,
    *,
    root: Path = ROOT,
    overrides: dict[str, bytes] | None = None,
) -> list[str]:
    value = manifest if manifest is not None else load_json(BUNDLE_MANIFEST_PATH)
    expected = bundle_manifest_payload(root=root, overrides=overrides)
    errors: list[str] = []
    actual_entries = value.get("entries") if isinstance(value, dict) else None
    if not isinstance(actual_entries, list):
        return ["runner bundle manifest entries are missing"]
    actual_paths = [
        item.get("path") for item in actual_entries if isinstance(item, dict)
    ]
    expected_paths = [item["path"] for item in expected["entries"]]
    missing = sorted(set(expected_paths) - set(actual_paths))
    extra = sorted(set(actual_paths) - set(expected_paths))
    if missing:
        errors.append("runner bundle has unlisted runtime imports: " + ", ".join(missing))
    if extra:
        errors.append("runner bundle has stale extra paths: " + ", ".join(extra))
    if value != expected:
        errors.append("runner bundle manifest does not match runtime import closure")
    return sorted(set(errors))


def validate_release_registry(
    registry: dict[str, Any] | None = None,
    *,
    root: Path = ROOT,
    bundle_manifest: dict[str, Any] | None = None,
) -> list[str]:
    value = registry if registry is not None else release_registry()
    errors: list[str] = []
    releases = value.get("releases") if isinstance(value, dict) else None
    if not isinstance(releases, list):
        return ["evidence TCK registry releases are missing"]
    ids = [item.get("release_id") for item in releases if isinstance(item, dict)]
    if len(ids) != len(set(ids)):
        errors.append("evidence TCK release IDs must be unique")
    if set(ids) != {HISTORICAL_TCK_RELEASE_ID, TCK_RELEASE_ID}:
        errors.append("evidence TCK registry must retain 1.0.0 and register 1.1.0")
    try:
        historical = release_record(HISTORICAL_TCK_RELEASE_ID, value)
    except ValueError as exc:
        errors.append(str(exc))
    else:
        if canonical_digest(historical) != HISTORICAL_RELEASE_RECORD_DIGEST:
            errors.append("evidence TCK 1.0.0 historical record changed")
    supersession = release_supersession(HISTORICAL_TCK_RELEASE_ID, value)
    if not isinstance(supersession, dict):
        errors.append("evidence TCK 1.0.0 supersession metadata is missing")
    else:
        if supersession.get("status") != "superseded-experimental":
            errors.append("evidence TCK 1.0.0 supersession status is inaccurate")
        if supersession.get("frozen_record_digest") != HISTORICAL_RELEASE_RECORD_DIGEST:
            errors.append("evidence TCK 1.0.0 frozen digest metadata is stale")
        if supersession.get("target_registry_schema_digest") != HISTORICAL_TARGET_SCHEMA_DIGEST:
            errors.append("evidence TCK 1.0.0 schema digest metadata is stale")
        if supersession.get("release_registry_digest") != HISTORICAL_RELEASE_REGISTRY_DIGEST:
            errors.append("evidence TCK 1.0.0 release-registry digest metadata is stale")
        if supersession.get("superseded_by") != TCK_RELEASE_ID:
            errors.append("evidence TCK supersession does not point to 1.1.0")

    try:
        current = release_record(TCK_RELEASE_ID, value)
    except ValueError as exc:
        errors.append(str(exc))
        return sorted(set(errors))
    target = target_record()
    if target.current_release_id != TCK_RELEASE_ID:
        errors.append("projection v1 current release is not evidence TCK 1.1.0")
    if current.get("target", {}).get("target_key") != target.target_key:
        errors.append("current release target identity does not match registry")
    expected_checks = {
        current.get("report_schema", {}).get("content_digest"): file_digest(
            root / "conformance/evidence/external_evidence_report_v2.schema.json"
        ),
        current.get("target_registry", {}).get("content_digest"): file_digest(
            root / "conformance/evidence/targets.json"
        ),
        current.get("target_registry", {}).get("schema_digest"): file_digest(
            root / "conformance/evidence/target_registry.schema.json"
        ),
        current.get("target", {}).get("target_catalog", {}).get("content_digest"): file_digest(
            root / target.catalog_path
        ),
    }
    if any(actual != expected for actual, expected in expected_checks.items()):
        errors.append("evidence TCK 1.1.0 provenance does not match current bytes")
    manifest = bundle_manifest or load_json(root / BUNDLE_MANIFEST_PATH.relative_to(ROOT))
    errors.extend(validate_bundle_manifest(manifest, root=root))
    runner_bundle = current.get("runner_bundle", {})
    if runner_bundle.get("manifest_path") != BUNDLE_MANIFEST_PATH.relative_to(ROOT).as_posix():
        errors.append("evidence TCK runner bundle manifest path is incorrect")
    if runner_bundle.get("manifest_digest") != file_digest(root / BUNDLE_MANIFEST_PATH.relative_to(ROOT)):
        errors.append("evidence TCK runner bundle manifest digest is stale")
    if runner_bundle.get("digest") != manifest.get("bundle_digest"):
        errors.append("evidence TCK runner bundle digest is stale")
    if runner_bundle.get("paths") != [item["path"] for item in manifest.get("entries", [])]:
        errors.append("evidence TCK runner bundle paths do not match manifest")
    for item in expected_input_artifacts(current):
        if file_digest(root / item["path"]) != item["content_digest"]:
            errors.append(f"evidence TCK input digest is stale: {item['path']}")
    for item in expected_suite_records(current):
        if file_digest(root / item["path"]) != item["suite_digest"]:
            errors.append(f"evidence TCK suite digest is stale: {item['path']}")
    return sorted(set(errors))
