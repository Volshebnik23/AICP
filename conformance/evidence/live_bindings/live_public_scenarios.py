from __future__ import annotations

import copy
from typing import Any


PUBLIC_SCENARIO_PROTOCOL = "aicp.live_public_scenario.v1"
PUBLIC_INPUT_FIELDS = {"channel_properties", "limit", "object_hash"}


def public_scenario_projection(
    catalog: dict[str, Any],
    *,
    tested_role: str,
    run_index: int,
    input_messages: list[dict[str, Any]],
) -> dict[str, Any]:
    """Project runner-private scenarios into neutral implementation controls."""
    scenarios: list[dict[str, Any]] = []
    for private in catalog.get("scenarios", []):
        if private.get("tested_role") != tested_role:
            continue
        inputs = private.get("deterministic_inputs")
        public_inputs = {
            key: copy.deepcopy(value)
            for key, value in (inputs.items() if isinstance(inputs, dict) else [])
            if key in PUBLIC_INPUT_FIELDS
        }
        item: dict[str, Any] = {
            "scenario_id": str(private["scenario_id"]),
            "semantic_operation": str(private["semantic_family"]),
            "optional_features": [
                str(value)
                for value in private.get("optional_feature_requirements", [])
            ],
        }
        if public_inputs:
            item["input_facts"] = public_inputs
        scenarios.append(item)
    return {
        "protocol": PUBLIC_SCENARIO_PROTOCOL,
        "target": copy.deepcopy(catalog["target"]),
        "tested_role": tested_role,
        "run_index": run_index,
        "scenarios": scenarios,
        "input_messages": copy.deepcopy(input_messages),
    }
