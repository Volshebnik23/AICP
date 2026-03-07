from __future__ import annotations

from aicp_ref.hashing import message_hash_from_body
from aicp_ref.validate import verify_signatures
from aicp_ref.chain import verify_transcript_chain


def _message(*, message_id: str, prev_msg_hash: str | None = None) -> dict:
    body = {
        "session_id": "s-1",
        "message_id": message_id,
        "timestamp": "2026-03-01T00:00:00Z",
        "sender": "agent:A",
        "message_type": "CONTRACT_PROPOSE",
        "contract_id": "c-1",
        "payload": {"contract": {"contract_id": "c-1", "goal": "demo", "roles": ["initiator"]}},
    }
    if prev_msg_hash is not None:
        body["prev_msg_hash"] = prev_msg_hash
    return {**body, "message_hash": message_hash_from_body(body)}


def test_non_first_message_requires_prev_msg_hash() -> None:
    first = _message(message_id="m1")
    second = _message(message_id="m2")
    errors = verify_transcript_chain([first, second])
    assert "line 2: missing prev_msg_hash for non-first message" in errors


def test_signature_object_hash_must_match_message_hash() -> None:
    msg = _message(message_id="m1")
    msg["signatures"] = [
        {
            "signer": "agent:A",
            "kid": "A1",
            "object_type": "message",
            "object_hash": "sha256:not-the-message-hash",
            "sig_b64url": "invalid-signature-for-negative-test",
        }
    ]
    key_map = {"agent:A": {"kid": "A1", "public_key_b64url": "unused-in-this-negative-case"}}
    errors = verify_signatures([msg], key_map)
    assert any("signature.object_hash mismatch" in err for err in errors)


def test_signature_kid_must_match_signer_key() -> None:
    msg = _message(message_id="m1")
    msg["signatures"] = [
        {
            "signer": "agent:A",
            "kid": "A2",
            "object_type": "message",
            "object_hash": msg["message_hash"],
            "sig_b64url": "invalid-signature-for-negative-test",
        }
    ]
    key_map = {"agent:A": {"kid": "A1", "public_key_b64url": "unused-in-this-negative-case"}}
    errors = verify_signatures([msg], key_map)
    assert any("signature kid mismatch" in err for err in errors)
