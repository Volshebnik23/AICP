from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator
except Exception:  # pragma: no cover - environment dependent
    Draft202012Validator = None

try:
    from referencing import Registry, Resource
except Exception:  # pragma: no cover - environment dependent
    Registry = None
    Resource = None

ROOT = Path(__file__).resolve().parents[2]


@lru_cache(maxsize=512)
def _load_json_cached(path_str: str) -> Any:
    return json.loads(Path(path_str).read_text(encoding="utf-8"))


def load_json(path: Path) -> Any:
    return _load_json_cached(str(path.resolve()))


def _collect_refs(node: Any) -> list[str]:
    refs: list[str] = []
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str):
            refs.append(ref)
        for value in node.values():
            refs.extend(_collect_refs(value))
    elif isinstance(node, list):
        for value in node:
            refs.extend(_collect_refs(value))
    return refs


def _schema_aliases(schema: dict[str, Any], schema_path: Path) -> set[str]:
    aliases = {schema_path.resolve().as_uri()}
    schema_id = schema.get("$id")
    if isinstance(schema_id, str) and schema_id:
        aliases.add(schema_id)
    for legacy in schema.get("x-legacy-ids", []):
        if isinstance(legacy, str) and legacy:
            aliases.add(legacy)
    return aliases


@lru_cache(maxsize=1)
def _core_schema_resources() -> dict[str, Any]:
    if Resource is None:
        return {}
    core_path = ROOT / "schemas/core/aicp-core-message.schema.json"
    core_schema = load_json(core_path)
    resource = Resource.from_contents(core_schema)
    resources = {alias: resource for alias in _schema_aliases(core_schema, core_path)}
    for report_ref in (
        "conformance/conformance_report_schema.json",
        "conformance/conformance_report_v1.schema.json",
    ):
        report_path = ROOT / report_ref
        if report_path.exists():
            report_schema = load_json(report_path)
            report_resource = Resource.from_contents(report_schema)
            for alias in _schema_aliases(report_schema, report_path):
                resources[alias] = report_resource
    return resources


def build_validator(schema: dict[str, Any], schema_path: Path) -> Any:
    if Draft202012Validator is None:
        return None

    remote_refs = {
        ref for ref in _collect_refs(schema)
        if ref.startswith("http://") or ref.startswith("https://")
    }

    if Registry is None or Resource is None:
        if remote_refs:
            raise ValueError("Remote schema retrieval is disabled; add local mapping or replace $ref with aicp:.")
        return Draft202012Validator(schema)

    resources = _core_schema_resources()
    schema_resource = Resource.from_contents(schema)
    for alias in _schema_aliases(schema, schema_path):
        resources[alias] = schema_resource

    allowed_remote = {uri for uri in resources if uri.startswith("http://") or uri.startswith("https://")}
    unresolved = sorted(
        ref for ref in remote_refs if ref.split("#", 1)[0] not in allowed_remote
    )
    if unresolved:
        raise ValueError(
            "Remote schema retrieval is disabled; add local mapping or replace $ref with aicp:. "
            f"Unmapped refs: {', '.join(unresolved)}"
        )

    registry = Registry().with_resources(resources.items())
    return Draft202012Validator(schema, registry=registry)


def normalize_pointer(pointer: str) -> str:
    if pointer.startswith("#"):
        pointer = pointer[1:]
    if pointer == "":
        return ""
    if not pointer.startswith("/"):
        raise ValueError(f"Invalid JSON pointer format: {pointer}")
    return pointer


def resolve_json_pointer(doc: dict[str, Any], pointer: str) -> Any:
    pointer = normalize_pointer(pointer)
    if pointer == "":
        return doc
    current: Any = doc
    for raw in pointer.lstrip("/").split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, dict):
            current = current[token]
        elif isinstance(current, list):
            current = current[int(token)]
        else:
            raise KeyError(token)
    return current


def validator_for_schema_pointer(schema: dict[str, Any], pointer: str) -> Any:
    if Draft202012Validator is None:
        return None
    normalized = normalize_pointer(pointer)
    resolve_json_pointer(schema, normalized)
    wrapper = {
        "$schema": schema.get("$schema"),
        "$id": schema.get("$id"),
        "$ref": f"#{normalized}" if normalized else "#",
        "$defs": schema.get("$defs", {}),
    }
    return Draft202012Validator(wrapper)


@lru_cache(maxsize=256)
def validator_for_schema_path_pointer(schema_path_str: str, pointer: str) -> Any:
    if Draft202012Validator is None:
        return None
    schema_path = Path(schema_path_str)
    schema = load_json(schema_path)
    return validator_for_schema_pointer(schema, pointer)


def build_payload_validator_map(
    payload_schema: dict[str, Any] | None,
    payload_schema_map: dict[str, str] | None,
) -> dict[str, Any]:
    if payload_schema is None or payload_schema_map is None or Draft202012Validator is None:
        return {}
    validators: dict[str, Any] = {}
    for message_type, schema_pointer in payload_schema_map.items():
        if not isinstance(message_type, str) or not isinstance(schema_pointer, str):
            continue
        pointer = normalize_pointer(schema_pointer)
        resolve_json_pointer(payload_schema, pointer)
        wrapper = {
            "$schema": payload_schema.get("$schema"),
            "$id": payload_schema.get("$id"),
            "$ref": f"#{pointer}" if pointer else "#",
            "$defs": payload_schema.get("$defs", {}),
        }
        validators[message_type] = Draft202012Validator(wrapper)
    return validators
