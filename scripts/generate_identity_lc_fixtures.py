#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]

import sys

REF_PY = ROOT / "reference/python"
if str(REF_PY) not in sys.path:
    sys.path.insert(0, str(REF_PY))

from aicp_ref.hashing import message_hash_from_body, object_hash  # noqa: E402


def _b64url_no_pad(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(private_key: Ed25519PrivateKey, object_hash_value: str) -> str:
    sig_input = f"AICP1\0SIG\0{object_hash_value}".encode("utf-8")
    return _b64url_no_pad(private_key.sign(sig_input))


def _sign_message(msg: dict, signer: str, kid: str, private_key: Ed25519PrivateKey) -> None:
    msg["signatures"] = [
        {
            "signer": signer,
            "kid": kid,
            "object_type": "message",
            "object_hash": msg["message_hash"],
            "sig_b64url": _sign(private_key, msg["message_hash"]),
        }
    ]


def _finalize_rows(rows: list[dict]) -> list[dict]:
    prev_hash: str | None = None
    out: list[dict] = []
    for row in rows:
        msg = dict(row)
        msg.pop("message_hash", None)
        if prev_hash is not None:
            msg["prev_msg_hash"] = prev_hash
        msg["message_hash"] = message_hash_from_body(msg)
        prev_hash = msg["message_hash"]
        out.append(msg)
    return out


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, separators=(",", ":"), ensure_ascii=False) + "\n")


def _q_keys() -> tuple[Ed25519PrivateKey, Ed25519PrivateKey, dict, dict]:
    q1_seed = bytes(range(1, 33))
    q2_seed = bytes(range(33, 65))
    q1 = Ed25519PrivateKey.from_private_bytes(q1_seed)
    q2 = Ed25519PrivateKey.from_private_bytes(q2_seed)
    q1_pub = _b64url_no_pad(q1.public_key().public_bytes_raw())
    q2_pub = _b64url_no_pad(q2.public_key().public_bytes_raw())
    return q1, q2, {"kid": "Q1", "alg": "ed25519", "public_key_b64url": q1_pub}, {"kid": "Q2", "alg": "ed25519", "public_key_b64url": q2_pub}


def _z_key() -> Ed25519PrivateKey:
    test_keys = json.loads((ROOT / "fixtures/keys/TEST_private_keys.json").read_text(encoding="utf-8"))
    z = test_keys["moderator:Z"]
    return Ed25519PrivateKey.from_private_bytes(_b64url_decode(z["private_key_b64url"]))


def _aid_object(q1_public: dict) -> dict:
    return {
        "agent_id": "agent:Q",
        "issuer": "AICP-test-fixture",
        "issued_at": "2026-01-05T00:00:00Z",
        "keys": [
            {
                "kid": q1_public["kid"],
                "alg": q1_public["alg"],
                "public_key_b64url": q1_public["public_key_b64url"],
                "status": "active",
            }
        ],
    }


def _rotation_payload(q1_private: Ed25519PrivateKey, q2_private: Ed25519PrivateKey, q2_public: dict) -> dict:
    new_key_material = {
        "kid": q2_public["kid"],
        "alg": q2_public["alg"],
        "public_key_b64url": q2_public["public_key_b64url"],
    }
    new_key_hash = object_hash("key", new_key_material)
    old_kid_binding = {"old_kid": "Q1"}
    old_kid_hash = object_hash("kid", old_kid_binding)
    return {
        "rotation_id": "rot-q-1",
        "old_kid": "Q1",
        "new_key": new_key_material,
        "cross_signatures": {
            "old_signs_new": {
                "kid": "Q1",
                "object_hash": new_key_hash,
                "sig_b64url": _sign(q1_private, new_key_hash),
            },
            "new_signs_old": {
                "kid": "Q2",
                "object_hash": old_kid_hash,
                "sig_b64url": _sign(q2_private, old_kid_hash),
            },
        },
    }


def generate() -> None:
    q1, q2, q1_public, q2_public = _q_keys()
    z = _z_key()
    contract_ref = {"branch_id": "main", "base_version": "v1", "head_version": "v1"}

    aid = _aid_object(q1_public)
    aid_hash = object_hash("aid", aid)
    aid_ref = {"object_type": "aid", "object": aid, "object_hash": aid_hash}
    rotation = _rotation_payload(q1, q2, q2_public)

    # IL-01
    il01 = _finalize_rows(
        [
            {"session_id": "sIL1", "message_id": "m1", "timestamp": "2026-01-05T00:00:00Z", "sender": "agent:A", "message_type": "CONTRACT_PROPOSE", "contract_id": "cIL1", "contract_ref": contract_ref, "payload": {"contract": {"contract_id": "cIL1", "goal": "identity_lc_announce", "roles": ["initiator", "responder"]}}},
            {"session_id": "sIL1", "message_id": "m2", "timestamp": "2026-01-05T00:00:02Z", "sender": "agent:B", "message_type": "CONTRACT_ACCEPT", "contract_id": "cIL1", "contract_ref": contract_ref, "payload": {"accepted": True}},
            {"session_id": "sIL1", "message_id": "m3", "timestamp": "2026-01-05T00:00:04Z", "sender": "agent:Q", "message_type": "IDENTITY_ANNOUNCE", "contract_id": "cIL1", "contract_ref": contract_ref, "payload": {"aid_hash": aid_hash, "aid_ref": aid_ref}},
            {"session_id": "sIL1", "message_id": "m4", "timestamp": "2026-01-05T00:00:06Z", "sender": "agent:Q", "message_type": "ATTEST_ACTION", "contract_id": "cIL1", "contract_ref": contract_ref, "payload": {"action_id": "act-il1", "action_type": "notify", "consent_ref": "consent:il1"}},
        ]
    )
    _sign_message(il01[2], "agent:Q", "Q1", q1)
    _sign_message(il01[3], "agent:Q", "Q1", q1)
    _write_jsonl(ROOT / "fixtures/extensions/identity_lc/IL-01_announce_and_verify_session_local_key.jsonl", il01)

    # IL-02
    il02 = _finalize_rows(
        [
            {"session_id": "sIL2", "message_id": "m1", "timestamp": "2026-01-05T00:10:00Z", "sender": "agent:A", "message_type": "CONTRACT_PROPOSE", "contract_id": "cIL2", "contract_ref": contract_ref, "payload": {"contract": {"contract_id": "cIL2", "goal": "identity_lc_rotate", "roles": ["initiator", "responder"]}}},
            {"session_id": "sIL2", "message_id": "m2", "timestamp": "2026-01-05T00:10:02Z", "sender": "agent:B", "message_type": "CONTRACT_ACCEPT", "contract_id": "cIL2", "contract_ref": contract_ref, "payload": {"accepted": True}},
            {"session_id": "sIL2", "message_id": "m3", "timestamp": "2026-01-05T00:10:04Z", "sender": "agent:Q", "message_type": "IDENTITY_ANNOUNCE", "contract_id": "cIL2", "contract_ref": contract_ref, "payload": {"aid_hash": aid_hash, "aid_ref": aid_ref}},
            {"session_id": "sIL2", "message_id": "m4", "timestamp": "2026-01-05T00:10:06Z", "sender": "agent:Q", "message_type": "KEY_ROTATION", "contract_id": "cIL2", "contract_ref": contract_ref, "payload": rotation},
            {"session_id": "sIL2", "message_id": "m5", "timestamp": "2026-01-05T00:10:08Z", "sender": "agent:Q", "message_type": "ATTEST_ACTION", "contract_id": "cIL2", "contract_ref": contract_ref, "payload": {"action_id": "act-il2", "action_type": "notify", "consent_ref": "consent:il2"}},
        ]
    )
    _sign_message(il02[2], "agent:Q", "Q1", q1)
    _sign_message(il02[3], "agent:Q", "Q1", q1)
    _sign_message(il02[4], "agent:Q", "Q2", q2)
    _write_jsonl(ROOT / "fixtures/extensions/identity_lc/IL-02_rotation_cross_sign_and_use_new_key.jsonl", il02)

    # IL-03 expected fail
    il03 = _finalize_rows(
        [
            {"session_id": "sIL3", "message_id": "m1", "timestamp": "2026-01-05T00:20:00Z", "sender": "agent:A", "message_type": "CONTRACT_PROPOSE", "contract_id": "cIL3", "contract_ref": contract_ref, "payload": {"contract": {"contract_id": "cIL3", "goal": "identity_lc_revoke", "roles": ["initiator", "responder", "moderator"]}}},
            {"session_id": "sIL3", "message_id": "m2", "timestamp": "2026-01-05T00:20:02Z", "sender": "agent:B", "message_type": "CONTRACT_ACCEPT", "contract_id": "cIL3", "contract_ref": contract_ref, "payload": {"accepted": True}},
            {"session_id": "sIL3", "message_id": "m3", "timestamp": "2026-01-05T00:20:04Z", "sender": "agent:Q", "message_type": "IDENTITY_ANNOUNCE", "contract_id": "cIL3", "contract_ref": contract_ref, "payload": {"aid_hash": aid_hash, "aid_ref": aid_ref}},
            {"session_id": "sIL3", "message_id": "m4", "timestamp": "2026-01-05T00:20:06Z", "sender": "agent:Q", "message_type": "KEY_ROTATION", "contract_id": "cIL3", "contract_ref": contract_ref, "payload": rotation},
            {"session_id": "sIL3", "message_id": "m5", "timestamp": "2026-01-05T00:20:08Z", "sender": "moderator:Z", "message_type": "KEY_REVOKE", "contract_id": "cIL3", "contract_ref": contract_ref, "payload": {"revocation_id": "rev-il3-1", "effective_at": "2026-01-05T00:20:08Z", "target_kid": "Q2", "reason_code": "policy:key_revoke"}},
            {"session_id": "sIL3", "message_id": "m6", "timestamp": "2026-01-05T00:20:10Z", "sender": "agent:Q", "message_type": "CONTEXT_AMEND", "contract_id": "cIL3", "contract_ref": contract_ref, "payload": {"amendment": {"note": "should fail due to revoked key"}}},
        ]
    )
    _sign_message(il03[2], "agent:Q", "Q1", q1)
    _sign_message(il03[3], "agent:Q", "Q1", q1)
    _sign_message(il03[4], "moderator:Z", "Z1", z)
    _sign_message(il03[5], "agent:Q", "Q2", q2)
    _write_jsonl(ROOT / "fixtures/extensions/identity_lc/IL-03_revoke_then_use_revoked_key_expected_fail.jsonl", il03)


if __name__ == "__main__":
    generate()
    print("Generated identity lifecycle fixtures under fixtures/extensions/identity_lc/")
