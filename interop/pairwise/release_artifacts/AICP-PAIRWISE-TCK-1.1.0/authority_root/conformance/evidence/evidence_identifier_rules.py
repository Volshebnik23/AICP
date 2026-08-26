from __future__ import annotations

import re
from typing import Any


_BROAD_DASH = re.compile(r"^x-[a-z0-9]+[a-z0-9._-]*$")
_BROAD_COLON = re.compile(r"^[a-z0-9]+:[a-z0-9][a-z0-9._-]*$")


def is_vendor_or_org_namespaced_identifier(value: Any) -> bool:
    """Mirror the ordinary PE/CAPNEG vendor:/org: namespace rule."""

    return isinstance(value, str) and (
        value.startswith("vendor:") or value.startswith("org:")
    )


def is_broad_namespaced_identifier(value: Any) -> bool:
    """Mirror rules that permit x-* or any valid colon namespace."""

    return isinstance(value, str) and bool(
        _BROAD_DASH.fullmatch(value) or _BROAD_COLON.fullmatch(value)
    )
