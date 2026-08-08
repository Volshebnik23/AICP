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
REPORT_SCHEMA_V21_PATH = EVIDENCE_DIR / "external_evidence_report_v2_1.schema.json"
TCK_RELEASES_PATH = EVIDENCE_DIR / "evidence_tck_releases.json"
EXPECTATIONS_PATH = EVIDENCE_DIR / "projection_v1_expectations.json"
LEGACY_BUNDLE_MANIFEST_PATH = EVIDENCE_DIR / "evidence_runner_bundle.json"
BUNDLE_MANIFEST_PATH = EVIDENCE_DIR / "evidence_runner_bundle_v1_2.json"
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
PROFILE_TCK_RELEASE_ID = "AICP-EVIDENCE-TCK-1.2.0"
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
FROZEN_TCK_1_1_RECORD_DIGEST = (
    "sha256:a1b4515821b86a23daff0df9a8b1d6bbf68eec3c5768172c06ed34afb0e7b5cb"
)
PROFILE_TARGET_KEYS = (
    "AICP-MEDIATED-BLOCKING@0.1",
    "AICP-RESUMABLE-SESSIONS@0.1",
    "AICP-DELEGATED-IDENTITY@0.1",
)
EXPECTED_TARGET_KEYS = (TARGET_KEY, *PROFILE_TARGET_KEYS)
TARGET_KINDS = {"product_profile", "capability", "binding"}
TARGET_KIND_POLICY = {
    "product_profile": ("full-profile", "implements_profile"),
    "capability": ("full-capability", "implements_capability"),
    "binding": ("full-binding", "implements_binding"),
}


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


def release_target_entry(
    release: dict[str, Any],
    target_key: str | None = None,
) -> dict[str, Any]:
    singular = release.get("target")
    if isinstance(singular, dict):
        if target_key is not None and singular.get("target_key") != target_key:
            raise ValueError("declared release does not contain the exact target")
        return singular
    targets = release.get("targets")
    if not isinstance(targets, list) or not isinstance(target_key, str):
        raise ValueError("multi-target evidence release requires an exact target key")
    matches = [
        item
        for item in targets
        if isinstance(item, dict) and item.get("target_key") == target_key
    ]
    if len(matches) != 1:
        raise ValueError("declared release must contain the exact target once")
    return matches[0]


def expected_input_artifacts(
    release: dict[str, Any],
    target_key: str | None = None,
) -> list[dict[str, str]]:
    try:
        target = release_target_entry(release, target_key)
    except ValueError:
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


def expected_suite_records(
    release: dict[str, Any],
    target_key: str | None = None,
) -> list[dict[str, str]]:
    try:
        target = release_target_entry(release, target_key)
    except ValueError:
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
    producer_records = (
        handler.producer_cases(catalog, mode)
        if hasattr(handler, "producer_cases")
        else [catalog["producer_case"]]
    )
    ids.extend(str(item["case_id"]) for item in producer_records)
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
    profile_registry = load_json(root / "registry/aicp_profiles.json")
    profile_entries = {
        (str(item.get("profile_id")), str(item.get("profile_version"))): item
        for item in profile_registry
        if isinstance(item, dict)
    }
    releases_value = (
        release_registry()
        if require_repository_references and root == ROOT
        else load_json(root / "conformance/evidence/evidence_tck_releases.json")
        if require_repository_references
        and (root / "conformance/evidence/evidence_tck_releases.json").is_file()
        else None
    )
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
        expected_mode, expected_claim = TARGET_KIND_POLICY[record.target_kind]
        if record.execution_mode != expected_mode:
            errors.append(
                f"target kind/execution mode mismatch: {record.target_key}"
            )
        if record.evidence_claim_type != expected_claim:
            errors.append(
                f"target kind/claim type mismatch: {record.target_key}"
            )
        catalog_path = root / record.catalog_path
        if require_repository_references:
            for relative in (record.catalog_path, *record.required_suites):
                if not (root / relative).is_file():
                    errors.append(f"target registry path does not resolve: {relative}")
            if catalog_path.is_file():
                catalog_value = load_json(catalog_path)
                if catalog_value.get("target") != record.identity():
                    errors.append(
                        f"target catalog identity mismatch: {record.target_key}"
                    )
                if catalog_value.get("handler_id") != record.handler_id:
                    errors.append(
                        f"target registry handler mismatch: {record.target_key}"
                    )
                if catalog_value.get("expected_mark") != record.expected_mark:
                    errors.append(
                        f"target registry mark mismatch: {record.target_key}"
                    )
                if tuple(catalog_value.get("required_suite_paths", record.required_suites)) != record.required_suites:
                    errors.append(
                        f"target registry required suites mismatch: {record.target_key}"
                    )
                if tuple(catalog_value.get("required_operations", ())) != record.required_operations:
                    errors.append(
                        f"target registry required operations mismatch: {record.target_key}"
                    )
            if record.target_kind == "product_profile":
                profile = profile_entries.get((record.target_id, record.target_version))
                if not isinstance(profile, dict) or profile.get("status") != record.status:
                    errors.append(
                        f"target maturity differs from profile registry: {record.target_key}"
                    )
                if catalog_path.is_file():
                    catalog_value = load_json(catalog_path)
                    profile_path_value = catalog_value.get("profile_catalog", {}).get("path")
                    if not isinstance(profile_path_value, str) or not (root / profile_path_value).is_file():
                        errors.append(
                            f"profile target catalog does not bind a profile catalog: {record.target_key}"
                        )
                    else:
                        profile_catalog = load_json(root / profile_path_value)
                        if profile_catalog.get("compatibility_mark") != record.expected_mark:
                            errors.append(
                                f"profile mark differs from owning catalog: {record.target_key}"
                            )
                        if tuple(profile_catalog.get("required_suites", ())) != record.required_suites:
                            errors.append(
                                f"profile suites differ from owning catalog: {record.target_key}"
                            )
        if releases_value is not None:
            try:
                selected_release = release_record(record.current_release_id, releases_value)
                release_target = release_target_entry(selected_release, record.target_key)
            except ValueError as exc:
                errors.append(f"target current release is invalid: {record.target_key}: {exc}")
            else:
                if release_target.get("handler_id") != record.handler_id:
                    errors.append(f"release handler mismatch: {record.target_key}")
                if release_target.get("expected_mark") != record.expected_mark:
                    errors.append(f"release mark mismatch: {record.target_key}")
    if len(keys) != len(set(keys)):
        errors.append("target keys must be unique")
    if len(marks) != len(set(marks)):
        errors.append("target expected marks must be unique")
    if len(identities) != len(set(identities)):
        errors.append("exact target identities must be unique")
    if any(len(values) != 1 for values in identities_by_key.values()):
        errors.append("the same target key maps to different identities")
    if enforce_current_scope and keys != list(EXPECTED_TARGET_KEYS):
        errors.append(
            "M63 must register exactly projection v1 and the three Tier-1 profiles"
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
    if selected.target_kind == "product_profile":
        return _validate_product_profile_catalog(
            value,
            selected=selected,
            handler=handler,
            root=root,
            simulate_no_jsonschema=simulate_no_jsonschema,
        )
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


def _validate_product_profile_catalog(
    value: dict[str, Any],
    *,
    selected: TargetRecord,
    handler: Any | None,
    root: Path,
    simulate_no_jsonschema: bool,
) -> list[str]:
    errors: list[str] = []
    profile_record = value.get("profile_catalog")
    if not isinstance(profile_record, dict):
        return ["profile evidence target catalog lacks profile_catalog provenance"]
    profile_path = profile_record.get("path")
    if not isinstance(profile_path, str) or not (root / profile_path).is_file():
        return ["profile evidence target owning profile catalog does not resolve"]
    profile = load_json(root / profile_path)
    if (
        profile.get("profile_id") != selected.target_id
        or profile.get("profile_version") != selected.target_version
    ):
        errors.append("profile target catalog identity differs from owning profile")
    if profile.get("compatibility_mark") != selected.expected_mark:
        errors.append("profile target catalog mark differs from owning profile")
    required_suite_paths = list(profile.get("required_suites", []))
    if value.get("required_suite_paths") != required_suite_paths:
        errors.append("profile target required suites differ from owning profile")
    if profile_record.get("content_digest") != file_digest(root / profile_path):
        errors.append("profile catalog digest is stale")

    suite_records = value.get("required_suites")
    if not isinstance(suite_records, list):
        return sorted(set([*errors, "profile target required_suites must be an array"]))
    if [item.get("path") for item in suite_records if isinstance(item, dict)] != required_suite_paths:
        errors.append("profile target suite records are missing, duplicated, or reordered")
    expected_sources: dict[tuple[str, str], dict[str, Any]] = {}
    for suite_record in suite_records:
        if not isinstance(suite_record, dict):
            errors.append("profile target suite record must be an object")
            continue
        relative = suite_record.get("path")
        if not isinstance(relative, str) or not (root / relative).is_file():
            errors.append(f"profile target suite does not resolve: {relative}")
            continue
        suite = load_json(root / relative)
        if suite_record.get("suite_id") != suite.get("suite_id") or suite_record.get(
            "suite_version"
        ) != suite.get("suite_version"):
            errors.append(f"profile target suite identity is stale: {relative}")
        if suite_record.get("suite_digest") != file_digest(root / relative):
            errors.append(f"profile target suite digest is stale: {relative}")
        for transcript in suite.get("transcripts", []):
            if isinstance(transcript, dict) and isinstance(transcript.get("id"), str):
                expected_sources[(str(suite.get("suite_id")), str(transcript["id"]))] = {
                    "suite_path": relative,
                    "transcript": transcript,
                }

    consumers = value.get("consumer_cases")
    if not isinstance(consumers, list):
        return sorted(set([*errors, "profile target consumer_cases must be an array"]))
    observed_sources = Counter(
        (str(item.get("source_suite_id")), str(item.get("source_case_id")))
        for item in consumers
        if isinstance(item, dict)
    )
    if observed_sources != Counter({key: 1 for key in expected_sources}):
        errors.append("profile target must cover every required-suite transcript exactly once")
    case_ids = [item.get("case_id") for item in consumers if isinstance(item, dict)]
    if len(case_ids) != len(set(case_ids)):
        errors.append("profile target public consumer case IDs must be globally unique")
    for item in consumers:
        if not isinstance(item, dict):
            errors.append("profile target consumer case must be an object")
            continue
        source_key = (str(item.get("source_suite_id")), str(item.get("source_case_id")))
        source = expected_sources.get(source_key)
        if source is None:
            errors.append(f"profile target consumer source is unknown: {source_key}")
            continue
        transcript = source["transcript"]
        fixture = transcript.get("path")
        if item.get("fixture") != fixture:
            errors.append(f"profile target consumer fixture drift: {source_key}")
        if isinstance(fixture, str) and item.get("input_digest") != file_digest(root / fixture):
            errors.append(f"profile target consumer fixture digest is stale: {source_key}")
        expected_accepted = transcript.get("expect_pass", True) is True
        if item.get("accepted") is not expected_accepted:
            errors.append(f"profile target consumer acceptance drift: {source_key}")
        suite_codes = [
            str(failure.get("test_id"))
            for failure in transcript.get("expected_failures", [])
            if isinstance(failure, dict) and isinstance(failure.get("test_id"), str)
        ]
        observations = item.get("expected_error_observations")
        if not isinstance(observations, list):
            errors.append(f"profile target reviewed observation missing: {source_key}")
            continue
        reviewed_codes: list[str] = []
        for observation in observations:
            if not isinstance(observation, dict):
                errors.append(f"profile target observation is not an object: {source_key}")
                continue
            code = observation.get("code")
            count = observation.get("exact_count")
            scope = observation.get("check_scope")
            if not isinstance(code, str) or not isinstance(count, int) or count < 1:
                errors.append(f"profile target observation is invalid: {source_key}")
                continue
            if not isinstance(scope, str) or not scope:
                errors.append(f"profile target observation scope missing: {source_key}")
            reviewed_codes.extend([code] * count)
            if code not in suite_codes and not observation.get("supplemental_reason"):
                errors.append(f"profile target supplemental observation lacks rationale: {source_key}/{code}")
        if reviewed_codes != suite_codes:
            errors.append(f"profile target observations differ from reviewed suite order: {source_key}")

    if value.get("target") != selected.identity() or value.get("target_key") != selected.target_key:
        errors.append("profile target catalog identity differs from target registry")
    if value.get("handler_id") != selected.handler_id:
        errors.append("profile target catalog handler differs from target registry")
    if value.get("expected_mark") != selected.expected_mark:
        errors.append("profile target catalog mark differs from target registry")
    if tuple(value.get("required_operations", ())) != selected.required_operations:
        errors.append("profile target operation set differs from target registry")
    for artifact in value.get("required_input_artifacts", []):
        if not isinstance(artifact, dict):
            errors.append("profile target required input record must be an object")
            continue
        relative = artifact.get("path")
        if not isinstance(relative, str) or not (root / relative).is_file():
            errors.append(f"profile target required input does not resolve: {relative}")
        elif artifact.get("content_digest") != file_digest(root / relative):
            errors.append(f"profile target required input digest is stale: {relative}")
    if handler is not None:
        try:
            ids = mandatory_case_ids(value, "full-profile", handler)
        except (KeyError, TypeError, ValueError) as exc:
            errors.append(f"profile target mandatory case derivation failed: {exc}")
        else:
            if len(ids) != len(set(ids)):
                errors.append("profile target mandatory evidence case IDs are not unique")
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
    "conformance/evidence/product_profile_handler.py": "target_handler",
    "conformance/evidence/profile_transcript_evaluator.py": "transcript_validation",
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
    required_ids = {
        HISTORICAL_TCK_RELEASE_ID,
        TCK_RELEASE_ID,
        PROFILE_TCK_RELEASE_ID,
    }
    if not required_ids.issubset(set(ids)):
        errors.append("evidence TCK registry must retain 1.0.0/1.1.0 and register 1.2.0")
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
        projection_release = release_record(TCK_RELEASE_ID, value)
    except ValueError as exc:
        errors.append(str(exc))
        return sorted(set(errors))
    if canonical_digest(projection_release) != FROZEN_TCK_1_1_RECORD_DIGEST:
        errors.append("evidence TCK 1.1.0 frozen record changed")
    projection_target = target_record()
    if projection_target.current_release_id != TCK_RELEASE_ID:
        errors.append("projection v1 current release is not evidence TCK 1.1.0")
    if projection_release.get("target", {}).get("target_key") != projection_target.target_key:
        errors.append("evidence TCK 1.1.0 target identity changed")
    if projection_release.get("report_schema", {}).get("content_digest") != file_digest(
        root / REPORT_SCHEMA_PATH.relative_to(ROOT)
    ):
        errors.append("evidence report 2.0 bytes differ from frozen TCK 1.1.0")
    legacy_manifest = load_json(root / LEGACY_BUNDLE_MANIFEST_PATH.relative_to(ROOT))
    legacy_bundle = projection_release.get("runner_bundle", {})
    if legacy_bundle.get("manifest_digest") != file_digest(
        root / LEGACY_BUNDLE_MANIFEST_PATH.relative_to(ROOT)
    ):
        errors.append("evidence TCK 1.1.0 frozen bundle manifest changed")
    if legacy_bundle.get("digest") != legacy_manifest.get("bundle_digest"):
        errors.append("evidence TCK 1.1.0 frozen bundle digest changed")

    try:
        profile_release = release_record(PROFILE_TCK_RELEASE_ID, value)
    except ValueError as exc:
        errors.append(str(exc))
        return sorted(set(errors))
    release_targets = profile_release.get("targets")
    if not isinstance(release_targets, list):
        return sorted(set([*errors, "evidence TCK 1.2.0 targets are missing"]))
    release_keys = [
        item.get("target_key") for item in release_targets if isinstance(item, dict)
    ]
    if len(release_keys) != len(set(release_keys)):
        errors.append("evidence TCK 1.2.0 target keys must be unique")
    if release_keys != list(PROFILE_TARGET_KEYS):
        errors.append("evidence TCK 1.2.0 must contain exactly the three Tier-1 targets")
    expected_checks = {
        profile_release.get("report_schema", {}).get("content_digest"): file_digest(
            root / REPORT_SCHEMA_V21_PATH.relative_to(ROOT)
        ),
        profile_release.get("target_registry", {}).get("content_digest"): file_digest(
            root / TARGETS_PATH.relative_to(ROOT)
        ),
        profile_release.get("target_registry", {}).get("schema_digest"): file_digest(
            root / TARGET_SCHEMA_PATH.relative_to(ROOT)
        ),
    }
    if any(actual != expected for actual, expected in expected_checks.items()):
        errors.append("evidence TCK 1.2.0 common provenance does not match current bytes")
    manifest = bundle_manifest or load_json(root / BUNDLE_MANIFEST_PATH.relative_to(ROOT))
    errors.extend(validate_bundle_manifest(manifest, root=root))
    runner_bundle = profile_release.get("runner_bundle", {})
    if runner_bundle.get("manifest_path") != BUNDLE_MANIFEST_PATH.relative_to(ROOT).as_posix():
        errors.append("evidence TCK 1.2.0 runner bundle manifest path is incorrect")
    if runner_bundle.get("manifest_digest") != file_digest(root / BUNDLE_MANIFEST_PATH.relative_to(ROOT)):
        errors.append("evidence TCK 1.2.0 runner bundle manifest digest is stale")
    if runner_bundle.get("digest") != manifest.get("bundle_digest"):
        errors.append("evidence TCK 1.2.0 runner bundle digest is stale")
    if runner_bundle.get("paths") != [item["path"] for item in manifest.get("entries", [])]:
        errors.append("evidence TCK 1.2.0 runner bundle paths do not match manifest")

    for record in [resolve_target_record(key) for key in EXPECTED_TARGET_KEYS]:
        try:
            selected_release = release_record(record.current_release_id, value)
            selected_target = release_target_entry(selected_release, record.target_key)
        except ValueError as exc:
            errors.append(f"target/release resolution failed: {record.target_key}: {exc}")
            continue
        catalog_value = target_catalog(record)
        if selected_target.get("handler_id") != record.handler_id:
            errors.append(f"release handler mismatch: {record.target_key}")
        if selected_target.get("expected_mark") != record.expected_mark:
            errors.append(f"release mark mismatch: {record.target_key}")
        if selected_target.get("target_catalog", {}).get("path") != record.catalog_path:
            errors.append(f"release target catalog path mismatch: {record.target_key}")
        if selected_target.get("target_catalog", {}).get("content_digest") != file_digest(
            root / record.catalog_path
        ):
            errors.append(f"release target catalog digest is stale: {record.target_key}")
        expected_suite_paths = list(record.required_suites)
        suites = expected_suite_records(selected_release, record.target_key)
        if [item["path"] for item in suites] != expected_suite_paths:
            errors.append(f"release required suites mismatch: {record.target_key}")
        for item in suites:
            if file_digest(root / item["path"]) != item["suite_digest"]:
                errors.append(f"evidence TCK suite digest is stale: {item['path']}")
        for item in expected_input_artifacts(selected_release, record.target_key):
            if file_digest(root / item["path"]) != item["content_digest"]:
                errors.append(f"evidence TCK input digest is stale: {item['path']}")
        try:
            from target_handlers import resolve_handler

            handler = resolve_handler(record.handler_id)
            expected_ids = mandatory_case_ids(
                catalog_value,
                record.execution_mode,
                handler,
            )
        except (ImportError, KeyError, TypeError, ValueError) as exc:
            errors.append(f"release mandatory-case resolution failed: {record.target_key}: {exc}")
        else:
            if "mandatory_case_ids" in selected_target:
                if selected_target.get("mandatory_case_ids") != expected_ids:
                    errors.append(f"release mandatory case IDs are stale: {record.target_key}")
            else:
                producer_ids = [
                    str(item["case_id"])
                    for item in handler.producer_cases(
                        catalog_value,
                        record.execution_mode,
                    )
                ]
                consumer_ids = [
                    str(item["case_id"])
                    for item in handler.consumer_cases(
                        catalog_value,
                        record.execution_mode,
                    )
                ]
                if selected_target.get("mandatory_producer_ids") != producer_ids:
                    errors.append(f"release mandatory producer IDs are stale: {record.target_key}")
                if selected_target.get("mandatory_consumer_ids") != consumer_ids:
                    errors.append(f"release mandatory consumer IDs are stale: {record.target_key}")
    return sorted(set(errors))
