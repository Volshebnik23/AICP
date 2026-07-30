"""Low-level fixture construction helpers for CAPNEG v0.2.

Expected composition semantics live in the reviewed composition oracle. This
module deliberately limits itself to canonical construction and hash domains.
"""

from __future__ import annotations

from typing import Any


COMPOSITION_VERSION = "aicp.profile_composition.v1"
COMPOSITION_HASH_DOMAIN = "capneg.profile_composition"


def canonical_profile_ref_key(value: Any) -> tuple[str, str]:
    if not isinstance(value, dict):
        return "", ""
    return str(value.get("profile_id", "")), str(value.get("profile_version", ""))
