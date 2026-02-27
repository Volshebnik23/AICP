from __future__ import annotations

import base64
try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
except Exception:  # pragma: no cover
    Ed25519PublicKey = None


def _b64url_decode(value: str) -> bytes:
    pad = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + pad)


def verify_ed25519(public_key_b64url: str, signature_b64url: str, object_hash: str) -> bool:
    if Ed25519PublicKey is None:
        return False
    try:
        public_key = Ed25519PublicKey.from_public_bytes(_b64url_decode(public_key_b64url))
        signature = _b64url_decode(signature_b64url)
        signing_input = f"AICP1\0SIG\0{object_hash}".encode("utf-8")
        public_key.verify(signature, signing_input)
        return True
    except Exception:
        return False
