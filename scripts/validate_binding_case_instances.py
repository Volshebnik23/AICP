#!/usr/bin/env python3
"""Validate binding case JSON fixtures against each binding suite schema_ref."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BINDING_SUITES = ROOT / "conformance" / "bindings"
SCHEMAS_DIR = ROOT / "schemas"


try:
    from jsonschema import Draft202012Validator
except Exception:  # noqa: BLE001
    Draft202012Validator = None

try:
    from referencing import Registry, Resource
except Exception:  # noqa: BLE001
    Registry = None
    Resource = None


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


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
    aliases = {
        schema_path.resolve().as_uri(),
        f"aicp:{schema_path.relative_to(ROOT).as_posix()}",
    }

    schema_id = schema.get("$id")
    if isinstance(schema_id, str) and schema_id:
        aliases.add(schema_id)

    legacy_ids = schema.get("x-legacy-ids")
    if isinstance(legacy_ids, list):
        for legacy in legacy_ids:
            if isinstance(legacy, str) and legacy:
                aliases.add(legacy)

    return aliases


def _schema_resources() -> dict[str, Any]:
    if Resource is None:
        return {}

    resources: dict[str, Any] = {}
    for schema_path in sorted(SCHEMAS_DIR.rglob("*.json")):
        schema = _load_json(schema_path)
        resource = Resource.from_contents(schema)
        for alias in _schema_aliases(schema, schema_path):
            resources[alias] = resource
    return resources


def _build_validator(schema: dict[str, Any], schema_path: Path) -> Any:
    if Draft202012Validator is None:
        return None

    remote_refs = {
        ref for ref in _collect_refs(schema)
        if ref.startswith("http://") or ref.startswith("https://")
    }

    if Registry is None or Resource is None:
        if remote_refs:
            raise ValueError(
                "Remote schema retrieval is disabled; install referencing resources or replace remote refs with in-repo aliases."
            )
        return Draft202012Validator(schema)

    resources = _schema_resources()
    schema_resource = Resource.from_contents(schema)
    for alias in _schema_aliases(schema, schema_path):
        resources[alias] = schema_resource

    allowed_remote = {uri for uri in resources if uri.startswith("http://") or uri.startswith("https://")}
    unresolved = sorted(remote_refs - allowed_remote)
    if unresolved:
        raise ValueError(
            "Remote schema retrieval is disabled; unmapped refs: " + ", ".join(unresolved)
        )

    registry = Registry().with_resources(resources.items())
    return Draft202012Validator(schema, registry=registry)


def main() -> int:
    if Draft202012Validator is None:
        print("[WARN] jsonschema is not installed. Skipping binding case schema validation.")
        return 0

    errors = 0
    suite_paths = sorted(BINDING_SUITES.glob("*.json"))

    for suite_path in suite_paths:
        suite = _load_json(suite_path)
        suite_id = suite.get("suite_id", suite_path.stem)
        schema_ref = suite.get("schema_ref")
        if not isinstance(schema_ref, str) or not schema_ref:
            print(f"[FAIL] {suite_id} {suite_path.relative_to(ROOT)}: missing schema_ref")
            errors += 1
            continue

        schema_path = ROOT / schema_ref
        if not schema_path.exists():
            print(f"[FAIL] {suite_id} {schema_ref}: schema_ref path does not exist")
            errors += 1
            continue

        try:
            schema = _load_json(schema_path)
            validator = _build_validator(schema, schema_path)
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] {suite_id} {schema_ref}: validator setup failed ({exc})")
            errors += 1
            continue

        for case_rel in suite.get("cases", []):
            case_path = ROOT / case_rel
            try:
                case_obj = _load_json(case_path)
            except Exception as exc:  # noqa: BLE001
                print(f"[FAIL] {suite_id} {case_rel}: invalid JSON ({exc})")
                errors += 1
                continue

            for err in sorted(validator.iter_errors(case_obj), key=lambda issue: list(issue.path)):
                print(f"[FAIL] {suite_id} {case_rel}: {err.message}")
                errors += 1

    if errors:
        print(f"Binding case schema validation failed with {errors} error(s).")
        return 1

    print(f"OK: validated binding case instances for {len(suite_paths)} suite(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
