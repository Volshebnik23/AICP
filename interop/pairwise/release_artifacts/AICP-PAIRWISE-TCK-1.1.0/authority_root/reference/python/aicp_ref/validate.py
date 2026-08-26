from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .chain import verify_transcript_chain
from .hashing import message_hash_from_body
from .signatures import signature_verifier_available, verify_ed25519


def message_body_without_hash_and_signatures(message: dict[str, Any]) -> dict[str, Any]:
    body = dict(message)
    body.pop("message_hash", None)
    body.pop("signatures", None)
    return body


def recompute_message_hashes(messages: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    for i, msg in enumerate(messages, start=1):
        expected = msg.get("message_hash")
        computed = message_hash_from_body(message_body_without_hash_and_signatures(msg))
        if computed != expected:
            errors.append(f"line {i}: message_hash mismatch (expected {expected}, got {computed})")
    return errors


def _resolve_public_key(
    key_map: dict[str, Any], signer: Any, kid: Any
) -> tuple[str | None, str | None]:
    if not isinstance(signer, str) or not signer:
        return None, "missing_key"
    signer_keys = key_map.get(signer)
    if not isinstance(signer_keys, dict):
        return None, "missing_key"

    direct_key = signer_keys.get("public_key_b64url")
    if isinstance(direct_key, str) and direct_key:
        configured_kid = signer_keys.get("kid")
        if isinstance(configured_kid, str) and configured_kid != kid:
            return None, "kid_mismatch"
        return direct_key, None

    if not isinstance(kid, str) or not kid:
        return None, "kid_mismatch"
    selected = signer_keys.get(kid)
    if isinstance(selected, str) and selected:
        return selected, None
    if signer_keys:
        return None, "kid_mismatch"
    return None, "missing_key"


def validate_message_signatures(
    message: dict[str, Any],
    key_map: dict[str, Any],
    *,
    verify_crypto: bool,
    require_signatures: bool = False,
    require_sender_signature: bool = False,
) -> list[dict[str, str]]:
    """Validate structural and optional cryptographic message-signature semantics.

    Structural binding is always checked. ``verify_crypto=False`` disables only key
    resolution and Ed25519 verification. Each returned issue has a stable ``code``
    so the sandbox, conformance runner, and IUT adapter share one interpretation.
    """

    issues: list[dict[str, str]] = []
    message_hash = message.get("message_hash")
    signatures = message.get("signatures")

    if require_signatures and (not isinstance(signatures, list) or not signatures):
        issues.append({"code": "signatures_required", "message": "signatures must be present and non-empty"})
        return issues
    if signatures is None:
        return issues
    if not isinstance(signatures, list):
        issues.append({"code": "signatures_invalid", "message": "signatures must be an array"})
        return issues

    crypto_available = signature_verifier_available()
    if verify_crypto and not crypto_available:
        issues.append({"code": "crypto_unavailable", "message": "Ed25519 verification backend unavailable"})

    sender = message.get("sender")
    valid_sender_signature = False
    for index, signature in enumerate(signatures):
        if not isinstance(signature, dict):
            issues.append({"code": "signature_invalid", "message": f"signatures[{index}] must be an object"})
            continue

        entry_valid = True
        object_type = signature.get("object_type")
        if object_type != "message":
            issues.append(
                {
                    "code": "object_type_mismatch",
                    "message": f"signatures[{index}].object_type must equal 'message'",
                }
            )
            entry_valid = False

        signature_hash = signature.get("object_hash")
        if signature_hash != message_hash:
            issues.append(
                {
                    "code": "object_hash_mismatch",
                    "message": (
                        f"signature.object_hash mismatch at signatures[{index}] "
                        f"(expected {message_hash}, got {signature_hash})"
                    ),
                }
            )
            entry_valid = False

        if verify_crypto and crypto_available:
            signer = signature.get("signer")
            kid = signature.get("kid")
            public_key, key_error = _resolve_public_key(key_map, signer, kid)
            if key_error == "missing_key":
                issues.append(
                    {
                        "code": "missing_key",
                        "message": f"missing public key for signer {signer}",
                    }
                )
                entry_valid = False
            elif key_error == "kid_mismatch":
                issues.append(
                    {
                        "code": "kid_mismatch",
                        "message": f"signature kid mismatch for signer {signer}: {kid}",
                    }
                )
                entry_valid = False
            elif entry_valid and not verify_ed25519(
                str(public_key), str(signature.get("sig_b64url", "")), str(message_hash)
            ):
                issues.append(
                    {
                        "code": "signature_invalid",
                        "message": f"signature verification failed for signer {signer}",
                    }
                )
                entry_valid = False

        if entry_valid and (not verify_crypto or crypto_available) and signature.get("signer") == sender:
            valid_sender_signature = True

    if require_sender_signature and not valid_sender_signature and not (verify_crypto and not crypto_available):
        issues.append(
            {
                "code": "sender_signature_required",
                "message": "no valid signature signer equals the envelope sender",
            }
        )

    return issues


def verify_signatures(messages: list[dict[str, Any]], key_map: dict[str, dict[str, str]]) -> list[str]:
    errors: list[str] = []
    for i, msg in enumerate(messages, start=1):
        for issue in validate_message_signatures(msg, key_map, verify_crypto=True):
            errors.append(f"line {i}: {issue['message']}")
    return errors


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def validate_transcript(path: Path, key_map: dict[str, dict[str, str]]) -> list[str]:
    messages = load_jsonl(path)
    errors = []
    errors.extend(verify_transcript_chain(messages))
    errors.extend(recompute_message_hashes(messages))
    errors.extend(verify_signatures(messages, key_map))
    return errors
