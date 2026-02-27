from __future__ import annotations

import base64
import hashlib
from typing import Any

from .jcs import canonicalize_to_bytes


def b64url_no_pad(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def object_hash(object_type: str, obj: Any) -> str:
    canonical = canonicalize_to_bytes(obj)
    preimage = b"AICP1\0" + object_type.encode("utf-8") + b"\0" + canonical
    digest = hashlib.sha256(preimage).digest()
    return "sha256:" + b64url_no_pad(digest)


def message_hash_from_body(message_body_dict: dict[str, Any]) -> str:
    return object_hash("message", message_body_dict)
