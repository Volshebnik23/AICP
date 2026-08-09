from __future__ import annotations

import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RUNNER_DIR = ROOT / "conformance" / "runner"
if str(RUNNER_DIR) not in sys.path:
    sys.path.insert(0, str(RUNNER_DIR))

from _runner_context import normalize_pointer, resolve_json_pointer  # noqa: E402


SCENARIO_CATALOG_PATHS = (
    "conformance/evidence/mediated_blocking_producer_scenarios.json",
    "conformance/evidence/resumable_sessions_producer_scenarios.json",
    "conformance/evidence/delegated_identity_producer_scenarios.json",
)


@dataclass(frozen=True)
class PayloadSchemaRoute:
    message_type: str
    surface_kind: str
    surface_id: str
    surface_version: str
    schema_path: str
    schema_pointer: str
    owning_suite: str
    check_id: str

    def identity(self) -> tuple[str, str, str, str, str]:
        return (
            self.schema_path,
            self.schema_pointer,
            self.surface_kind,
            self.surface_id,
            self.surface_version,
        )


def _load_json(relative: str) -> Any:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def tier1_scenarios() -> list[dict[str, Any]]:
    scenarios: list[dict[str, Any]] = []
    for relative in SCENARIO_CATALOG_PATHS:
        value = _load_json(relative)
        scenarios.extend(
            item for item in value.get("scenarios", []) if isinstance(item, dict)
        )
    return scenarios


def _surface(suite: dict[str, Any]) -> tuple[str, str, str]:
    declared = suite.get("payload_surface")
    if isinstance(declared, dict):
        kind = declared.get("surface_kind")
        surface_id = declared.get("surface_id")
        version = declared.get("surface_version")
        if all(isinstance(value, str) and value for value in (kind, surface_id, version)):
            return str(kind), str(surface_id), str(version)
    suite_id = str(suite.get("suite_id"))
    aicp_version = str(suite.get("aicp_version"))
    kind = "core" if suite_id.startswith("CT-CORE-") else "extension"
    surface_id = suite_id.rsplit("-", 1)[0]
    return kind, surface_id, aicp_version


def derive_payload_routes(
    scenarios: list[dict[str, Any]],
) -> tuple[dict[str, PayloadSchemaRoute], list[str]]:
    errors: list[str] = []
    candidates: dict[str, list[PayloadSchemaRoute]] = defaultdict(list)
    suite_paths = sorted(
        {
            relative
            for scenario in scenarios
            for relative in scenario.get("required_suites", [])
            if isinstance(relative, str)
        }
    )
    for relative in suite_paths:
        suite = _load_json(relative)
        if suite.get("aicp_version") != "0.1":
            errors.append(
                f"payload route suite is not selected for AICP v0.1: {relative}"
            )
            continue
        if suite.get("canonical_payload_schema") is False:
            errors.append(
                f"non-canonical payload surface cannot route Tier-1 v0.1 messages: {relative}"
            )
            continue
        schema_path = suite.get("payload_schema_ref")
        schema_map = suite.get("payload_schema_map")
        if not isinstance(schema_path, str) or not isinstance(schema_map, dict):
            errors.append(f"payload route metadata is incomplete: {relative}")
            continue
        schema = _load_json(schema_path)
        surface_kind, surface_id, surface_version = _surface(suite)
        check_id = str(
            suite.get("payload_schema_check_id", "CN-PAYLOAD-SCHEMA-01")
        )
        for message_type, raw_pointer in schema_map.items():
            if not isinstance(message_type, str) or not isinstance(raw_pointer, str):
                errors.append(f"payload route entry is malformed: {relative}")
                continue
            try:
                pointer = normalize_pointer(raw_pointer)
                resolve_json_pointer(schema, pointer)
            except (KeyError, TypeError, ValueError) as exc:
                errors.append(
                    f"payload route pointer does not resolve: {relative}/{message_type}: {exc}"
                )
                continue
            candidates[message_type].append(
                PayloadSchemaRoute(
                    message_type=message_type,
                    surface_kind=surface_kind,
                    surface_id=surface_id,
                    surface_version=surface_version,
                    schema_path=schema_path,
                    schema_pointer=pointer,
                    owning_suite=str(suite.get("suite_id")),
                    check_id=check_id,
                )
            )

    routes: dict[str, PayloadSchemaRoute] = {}
    for message_type, values in sorted(candidates.items()):
        identities = {item.identity() for item in values}
        if len(identities) != 1:
            rendered = sorted(
                f"{item.owning_suite}:{item.schema_path}#{item.schema_pointer}"
                for item in values
            )
            errors.append(
                "ambiguous payload schema route for "
                f"{message_type}: {', '.join(rendered)}"
            )
            continue
        routes[message_type] = sorted(
            values,
            key=lambda item: item.owning_suite,
        )[0]
    return routes, sorted(set(errors))


def payload_route_errors(
    scenarios: list[dict[str, Any]],
    flow_sequences: dict[str, tuple[str, ...]],
) -> list[str]:
    routes, errors = derive_payload_routes(scenarios)
    used_flows = {
        str(item.get("flow_id"))
        for item in scenarios
        if isinstance(item.get("flow_id"), str)
    }
    for flow_id in sorted(used_flows):
        sequence = flow_sequences.get(flow_id)
        if sequence is None:
            errors.append(f"producer flow has no payload-route sequence: {flow_id}")
            continue
        for message_type in sequence:
            if message_type not in routes:
                errors.append(
                    "generated message type has no exact AICP v0.1 payload route: "
                    f"{flow_id}/{message_type}"
                )
    return sorted(set(errors))


@lru_cache(maxsize=1)
def tier1_payload_routes() -> dict[str, PayloadSchemaRoute]:
    routes, errors = derive_payload_routes(tier1_scenarios())
    if errors:
        raise ValueError("; ".join(errors))
    return routes


def payload_route_inventory(
    scenarios: list[dict[str, Any]],
    flow_sequences: dict[str, tuple[str, ...]],
) -> list[dict[str, Any]]:
    routes, errors = derive_payload_routes(scenarios)
    if errors:
        raise ValueError("; ".join(errors))
    exercising: dict[str, set[str]] = defaultdict(set)
    for scenario in scenarios:
        flow_id = scenario.get("flow_id")
        if not isinstance(flow_id, str):
            continue
        for message_type in flow_sequences.get(flow_id, ()):
            exercising[message_type].add(flow_id)
    return [
        {
            "message_type": route.message_type,
            "surface_kind": route.surface_kind,
            "surface_id": route.surface_id,
            "surface_version": route.surface_version,
            "schema_path": route.schema_path,
            "schema_pointer": route.schema_pointer,
            "owning_suite": route.owning_suite,
            "check_id": route.check_id,
            "producer_flows": sorted(exercising[route.message_type]),
        }
        for route in sorted(routes.values(), key=lambda item: item.message_type)
        if exercising[route.message_type]
    ]


def tier1_payload_route_input_paths() -> list[str]:
    scenarios = tier1_scenarios()
    routes, errors = derive_payload_routes(scenarios)
    if errors:
        raise ValueError("; ".join(errors))
    suite_paths = {
        relative
        for scenario in scenarios
        for relative in scenario.get("required_suites", [])
        if isinstance(relative, str)
    }
    return sorted(
        {
            *SCENARIO_CATALOG_PATHS,
            *suite_paths,
            *(route.schema_path for route in routes.values()),
        }
    )
