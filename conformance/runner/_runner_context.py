from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import sys
from typing import Any

RUNNER_DIR = Path(__file__).resolve().parent
if str(RUNNER_DIR) not in sys.path:
    sys.path.insert(0, str(RUNNER_DIR))

from _runner_io import load_json


def collect_refs(node: Any) -> list[str]:
    refs: list[str] = []
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str):
            refs.append(ref)
        for v in node.values():
            refs.extend(collect_refs(v))
    elif isinstance(node, list):
        for v in node:
            refs.extend(collect_refs(v))
    return refs


def schema_aliases(schema: dict[str, Any], schema_path: Path) -> set[str]:
    aliases = {schema_path.resolve().as_uri()}
    schema_id = schema.get("$id")
    if isinstance(schema_id, str) and schema_id:
        aliases.add(schema_id)
    for legacy in schema.get("x-legacy-ids", []):
        if isinstance(legacy, str) and legacy:
            aliases.add(legacy)
    return aliases


@lru_cache(maxsize=1)
def core_schema_resources(root_str: str, Resource: Any) -> dict[str, Any]:
    if Resource is None:
        return {}
    root = Path(root_str)
    core_path = root / "schemas/core/aicp-core-message.schema.json"
    core_schema = load_json(core_path)
    resource = Resource.from_contents(core_schema)
    return {alias: resource for alias in schema_aliases(core_schema, core_path)}


def build_validator(
    schema: dict[str, Any],
    schema_path: Path,
    root: Path,
    Draft202012Validator: Any,
    Registry: Any,
    Resource: Any,
) -> Any:
    if Draft202012Validator is None:
        return None

    remote_refs = {
        ref for ref in collect_refs(schema) if ref.startswith("http://") or ref.startswith("https://")
    }

    if Registry is None or Resource is None:
        if remote_refs:
            raise ValueError("Remote schema retrieval is disabled; add local mapping or replace $ref with aicp:.")
        return Draft202012Validator(schema)

    resources = core_schema_resources(str(root.resolve()), Resource)
    schema_resource = Resource.from_contents(schema)
    for alias in schema_aliases(schema, schema_path):
        resources[alias] = schema_resource

    allowed_remote = {u for u in resources if u.startswith("http://") or u.startswith("https://")}
    unresolved = sorted(remote_refs - allowed_remote)
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
    cur: Any = doc
    for raw in pointer.lstrip("/").split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(cur, dict):
            cur = cur[token]
        elif isinstance(cur, list):
            cur = cur[int(token)]
        else:
            raise KeyError(token)
    return cur


def validator_for_schema_pointer(schema: dict[str, Any], pointer: str, Draft202012Validator: Any) -> Any:
    if Draft202012Validator is None:
        return None
    norm_pointer = normalize_pointer(pointer)
    resolve_json_pointer(schema, norm_pointer)
    wrapper = {
        "$schema": schema.get("$schema"),
        "$id": schema.get("$id"),
        "$ref": f"#{norm_pointer}" if norm_pointer else "#",
        "$defs": schema.get("$defs", {}),
    }
    return Draft202012Validator(wrapper)


@lru_cache(maxsize=256)
def validator_for_schema_path_pointer(
    schema_path_str: str,
    pointer: str,
    Draft202012Validator: Any,
) -> Any:
    if Draft202012Validator is None:
        return None
    schema_path = Path(schema_path_str)
    schema = load_json(schema_path)
    return validator_for_schema_pointer(schema, pointer, Draft202012Validator)


def build_payload_validator_map(
    payload_schema: dict[str, Any] | None,
    payload_schema_map: dict[str, str] | None,
    Draft202012Validator: Any,
) -> dict[str, Any]:
    if payload_schema is None or payload_schema_map is None or Draft202012Validator is None:
        return {}
    validators: dict[str, Any] = {}
    for mtype, schema_pointer in payload_schema_map.items():
        if not isinstance(mtype, str) or not isinstance(schema_pointer, str):
            continue
        pointer = normalize_pointer(schema_pointer)
        resolve_json_pointer(payload_schema, pointer)
        wrapper = {
            "$schema": payload_schema.get("$schema"),
            "$id": payload_schema.get("$id"),
            "$ref": f"#{pointer}" if pointer else "#",
            "$defs": payload_schema.get("$defs", {}),
        }
        validators[mtype] = Draft202012Validator(wrapper)
    return validators
