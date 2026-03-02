#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
from pathlib import Path
import sys

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference/python"))
from aicp_ref.hashing import message_hash_from_body, object_hash  # noqa: E402


def _b64url_no_pad(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _sign(private_key: Ed25519PrivateKey, object_hash_value: str) -> str:
    sig_input = f"AICP1\0SIG\0{object_hash_value}".encode("utf-8")
    return _b64url_no_pad(private_key.sign(sig_input))


def finalize(rows: list[dict]) -> list[dict]:
    prev = None
    out: list[dict] = []
    for row in rows:
        msg = dict(row)
        msg.pop("message_hash", None)
        if prev is not None:
            msg["prev_msg_hash"] = prev
        msg["message_hash"] = message_hash_from_body(msg)
        prev = msg["message_hash"]
        out.append(msg)
    return out


def sign_rows(rows: list[dict], keys: dict[str, tuple[str, Ed25519PrivateKey]], include_unsigned_issue: bool = False) -> list[dict]:
    out = []
    for msg in rows:
        msg = dict(msg)
        sender = msg.get("sender")
        if isinstance(sender, str) and sender in keys:
            kid, key = keys[sender]
            should_sign = msg.get("message_type") in {"SUBJECT_BINDING_ISSUE", "SUBJECT_BINDING_REVOKE", "ATTEST_ACTION", "CONTENT_MESSAGE"}
            if should_sign and not (include_unsigned_issue and msg.get("message_type") == "SUBJECT_BINDING_ISSUE"):
                msg["signatures"] = [{
                    "signer": sender,
                    "kid": kid,
                    "object_type": "message",
                    "object_hash": msg["message_hash"],
                    "sig_b64url": _sign(key, msg["message_hash"]),
                }]
        out.append(msg)
    return out


def write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, separators=(",", ":"), ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def aid_ref(agent_id: str, kid: str, pub: str, issued_at: str) -> dict:
    aid_obj = {
        "agent_id": agent_id,
        "issued_at": issued_at,
        "keys": [{"kid": kid, "alg": "ed25519", "public_key_b64url": pub, "status": "active"}],
        "issuer": agent_id,
    }
    return {"object_type": "aid", "object": aid_obj, "object_hash": object_hash("aid", aid_obj)}


def build_rows(session: str, contract: str, use_ts: str, revoke_ts: str | None = None, issue_signed: bool = True) -> list[dict]:
    cref = {"branch_id": "main", "base_version": "v1", "head_version": "v1"}

    idp_seed = bytes([11]) * 32
    agent_seed = bytes([22]) * 32
    idp_key = Ed25519PrivateKey.from_private_bytes(idp_seed)
    agent_key = Ed25519PrivateKey.from_private_bytes(agent_seed)
    idp_pub = _b64url_no_pad(idp_key.public_key().public_bytes_raw())
    agent_pub = _b64url_no_pad(agent_key.public_key().public_bytes_raw())

    binding_obj = {
        "binding_id": f"b-{session}",
        "agent_id": "agent:A",
        "account_id": "acct:alpha",
        "issuer": "auth:IDP",
        "scopes": ["chat:reception", "delegate:act"],
        "issued_at": "2026-03-01T00:00:04Z",
        "expires_at": "2026-03-01T00:30:00Z",
    }
    binding_hash = object_hash("subject_binding", binding_obj)

    rows = [
        {"session_id": session, "message_id": "m1", "timestamp": "2026-03-01T00:00:00Z", "sender": "agent:A", "message_type": "CONTRACT_PROPOSE", "contract_id": contract, "contract_ref": cref, "payload": {"contract": {"contract_id": contract, "goal": "delegated_identity", "roles": ["agent", "issuer"]}}},
        {"session_id": session, "message_id": "m2", "timestamp": "2026-03-01T00:00:01Z", "sender": "agent:B", "message_type": "CONTRACT_ACCEPT", "contract_id": contract, "contract_ref": cref, "payload": {"accepted": True}},
        {"session_id": session, "message_id": "m3", "timestamp": "2026-03-01T00:00:02Z", "sender": "auth:IDP", "message_type": "IDENTITY_ANNOUNCE", "contract_id": contract, "contract_ref": cref, "payload": {"aid_hash": aid_ref("auth:IDP", "P1", idp_pub, "2026-03-01T00:00:02Z")["object_hash"], "aid_ref": aid_ref("auth:IDP", "P1", idp_pub, "2026-03-01T00:00:02Z")}},
        {"session_id": session, "message_id": "m4", "timestamp": "2026-03-01T00:00:03Z", "sender": "agent:A", "message_type": "IDENTITY_ANNOUNCE", "contract_id": contract, "contract_ref": cref, "payload": {"aid_hash": aid_ref("agent:A", "A1", agent_pub, "2026-03-01T00:00:03Z")["object_hash"], "aid_ref": aid_ref("agent:A", "A1", agent_pub, "2026-03-01T00:00:03Z")}},
        {"session_id": session, "message_id": "m5", "timestamp": "2026-03-01T00:00:04Z", "sender": "auth:IDP", "message_type": "SUBJECT_BINDING_ISSUE", "contract_id": contract, "contract_ref": cref, "payload": {"binding_hash": binding_hash, "binding_ref": {"object_type": "subject_binding", "object": binding_obj, "object_hash": binding_hash}, "note": "delegated identity issued"}},
    ]

    mid = 6
    if revoke_ts is not None:
        rows.append({"session_id": session, "message_id": f"m{mid}", "timestamp": "2026-03-01T00:00:05Z", "sender": "auth:IDP", "message_type": "SUBJECT_BINDING_REVOKE", "contract_id": contract, "contract_ref": cref, "payload": {"binding_hash": binding_hash, "effective_at": revoke_ts, "reason_code": "security_incident"}})
        mid += 1

    rows.append({"session_id": session, "message_id": f"m{mid}", "timestamp": use_ts, "sender": "agent:A", "message_type": "ATTEST_ACTION", "contract_id": contract, "contract_ref": cref, "ext": {"subject_binding_hash": binding_hash}, "payload": {"action": "submit_reception_summary", "result_hash": f"sha256:{session}-result"}})

    rows = finalize(rows)
    rows = sign_rows(rows, {"auth:IDP": ("P1", idp_key), "agent:A": ("A1", agent_key)}, include_unsigned_issue=not issue_signed)
    return rows


def main() -> None:
    out = ROOT / "fixtures/extensions/delegated_identity"
    di01 = build_rows("sDI1", "cDI1", use_ts="2026-03-01T00:00:10Z")
    di02 = build_rows("sDI2", "cDI2", use_ts="2026-03-01T00:00:10Z", revoke_ts="2026-03-01T00:00:06Z")
    di03 = build_rows("sDI3", "cDI3", use_ts="2026-03-01T00:40:00Z")
    di04 = build_rows("sDI4", "cDI4", use_ts="2026-03-01T00:00:10Z", issue_signed=False)

    write(out / "DI-01_issue_and_use_binding_pass.jsonl", di01)
    write(out / "DI-02_revoke_then_use_expected_fail.jsonl", di02)
    write(out / "DI-03_expired_binding_expected_fail.jsonl", di03)
    write(out / "DI-04_issue_not_signed_expected_fail.jsonl", di04)
    print("Generated delegated identity fixtures")


if __name__ == "__main__":
    main()
