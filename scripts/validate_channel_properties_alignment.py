#!/usr/bin/env python3
"""Validate channel-properties schema/registry/CAPNEG alignment."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _fail(msg: str) -> None:
    print(f"[FAIL] {msg}")


def main() -> int:
    registry = _load_json(ROOT / "registry/channel_properties.json")
    binding_schema = _load_json(ROOT / "schemas/bindings/channel-properties.schema.json")
    capneg_schema = _load_json(ROOT / "schemas/extensions/ext-capneg-payloads.schema.json")

    registry_ids = sorted(
        entry.get("id")
        for entry in registry
        if isinstance(entry, dict) and isinstance(entry.get("id"), str) and entry["id"].startswith("CP-")
    )

    defs = binding_schema.get("$defs", {}) if isinstance(binding_schema, dict) else {}
    capneg_defs = capneg_schema.get("$defs", {}) if isinstance(capneg_schema, dict) else {}

    ch_props = defs.get("ChannelProperties", {}) if isinstance(defs, dict) else {}
    supp_props = defs.get("SupportedChannelProperties", {}) if isinstance(defs, dict) else {}

    ch_keys = sorted((ch_props.get("properties") or {}).keys()) if isinstance(ch_props, dict) else []
    supp_keys = sorted((supp_props.get("properties") or {}).keys()) if isinstance(supp_props, dict) else []

    errors = 0

    if ch_keys != registry_ids:
        _fail(f"ChannelProperties keys drift from registry IDs: schema={ch_keys} registry={registry_ids}")
        errors += 1

    if supp_keys != registry_ids:
        _fail(f"SupportedChannelProperties keys drift from registry IDs: schema={supp_keys} registry={registry_ids}")
        errors += 1

    pattern = ch_props.get("patternProperties", {}) if isinstance(ch_props, dict) else {}
    if not isinstance(pattern, dict) or "^vendor:/.+" not in pattern:
        _fail("ChannelProperties.patternProperties must include '^vendor:/.+'")
        errors += 1

    supp_pattern = supp_props.get("patternProperties", {}) if isinstance(supp_props, dict) else {}
    if not isinstance(supp_pattern, dict) or "^vendor:/.+" not in supp_pattern:
        _fail("SupportedChannelProperties.patternProperties must include '^vendor:/.+'")
        errors += 1

    for key in ["ReplayWindowRange", "ChannelProperties", "SupportedChannelProperties"]:
        if defs.get(key) != capneg_defs.get(key):
            _fail(f"CAPNEG $defs.{key} drift detected relative to canonical binding schema")
            errors += 1

    if errors:
        print(f"Channel properties alignment validation failed with {errors} error(s).")
        return 1

    print(
        "OK: channel properties alignment satisfied "
        f"({len(registry_ids)} registry IDs, binding schema + CAPNEG defs synchronized)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
