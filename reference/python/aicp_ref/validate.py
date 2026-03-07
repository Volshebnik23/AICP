from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .chain import verify_transcript_chain
from .hashing import message_hash_from_body
from .signatures import verify_ed25519


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


def verify_signatures(messages: list[dict[str, Any]], key_map: dict[str, dict[str, str]]) -> list[str]:
    errors: list[str] = []
    for i, msg in enumerate(messages, start=1):
        message_hash = msg.get("message_hash")
        for sig in msg.get("signatures", []) or []:
            signer = sig.get("signer")
            signer_key = key_map.get(signer)
            if signer_key is None:
                errors.append(f"line {i}: missing key for signer {signer}")
                continue

            signature_hash = sig.get("object_hash")
            if signature_hash != message_hash:
                errors.append(
                    f"line {i}: signature.object_hash mismatch (expected {message_hash}, got {signature_hash})"
                )
                continue

            key_id = sig.get("kid")
            if key_id is not None and signer_key.get("kid") not in (None, key_id):
                errors.append(
                    f"line {i}: signature kid mismatch for signer {signer} "
                    f"(expected {signer_key.get('kid')}, got {key_id})"
                )
                continue

            public_key = signer_key.get("public_key_b64url")
            ok = verify_ed25519(public_key, sig.get("sig_b64url"), signature_hash)
            if not ok:
                errors.append(f"line {i}: signature verification failed for signer {signer}")
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
