#!/usr/bin/env python3
from __future__ import annotations

import base64
import copy
import json
import sys
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
REF_PY = ROOT / "reference/python"
if str(REF_PY) not in sys.path:
    sys.path.insert(0, str(REF_PY))

from aicp_ref.hashing import message_hash_from_body, object_hash  # noqa: E402
from aicp_ref.validate import message_body_without_hash_and_signatures  # noqa: E402


OUT = ROOT / "fixtures/security/authenticated_base"
CORE_OUT = OUT / "core"
CAPNEG_OUT = ROOT / "fixtures/extensions/capneg"


def _b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _load_keys() -> dict[str, dict[str, Any]]:
    return json.loads((ROOT / "fixtures/keys/TEST_private_keys.json").read_text(encoding="utf-8"))


def _sign(hash_value: str, signer: str, keys: dict[str, dict[str, Any]], *, kid: str | None = None) -> dict[str, str]:
    meta = keys[signer]
    private_key = Ed25519PrivateKey.from_private_bytes(_b64url_decode(meta["private_key_b64url"]))
    signature = private_key.sign(f"AICP1\0SIG\0{hash_value}".encode("utf-8"))
    return {
        "signer": signer,
        "kid": kid or meta["kid"],
        "object_type": "message",
        "object_hash": hash_value,
        "sig_b64url": _b64url_encode(signature),
    }


def _rehash_and_sign(rows: list[dict[str, Any]], keys: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    previous: str | None = None
    for original in rows:
        body = message_body_without_hash_and_signatures(original)
        body.pop("prev_msg_hash", None)
        if previous is not None:
            body["prev_msg_hash"] = previous
        digest = message_hash_from_body(body)
        message = {**body, "message_hash": digest}
        message["signatures"] = [_sign(digest, body["sender"], keys)]
        out.append(message)
        previous = digest
    return out


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, separators=(",", ":"), ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _signed_core_variants(keys: dict[str, dict[str, Any]]) -> None:
    sources = {
        "01": "GT-01_happy_path_signed.jsonl",
        "02": "GT-02_conflict_choose_signed.jsonl",
        "04": "GT-04_consent_required_and_grant.jsonl",
        "05": "GT-05_consent_revoke.jsonl",
        "06": "GT-06_unknown_base_and_resync.jsonl",
        "07": "GT-07_invalid_signature_reject.jsonl",
        "08": "GT-08_replay_duplicate_message_id.jsonl",
        "09": "GT-09_missing_prev_msg_hash_expected_fail.jsonl",
        "10": "GT-08_error_minimal.jsonl",
        "11": "GT-11_empty_contract_id_expected_fail.jsonl",
    }
    golden = ROOT / "fixtures/golden_transcripts"
    for case_id, filename in sources.items():
        source_rows = _load_jsonl(golden / filename)
        if case_id == "07":
            # Preserve the suite's deliberately invalid signature evidence.
            rows = source_rows
        else:
            for row in source_rows:
                if row.get("sender") == "agent:A":
                    row["sender"] = "agent:S"
                elif row.get("sender") == "agent:B":
                    row["sender"] = "agent:T"
            rows = _rehash_and_sign(source_rows, keys)
        if case_id == "09":
            # Preserve the missing non-first prev_msg_hash while keeping every
            # message sender-authenticated for the authenticated profile.
            rows[1].pop("prev_msg_hash", None)
            for index in range(1, len(rows)):
                body = message_body_without_hash_and_signatures(rows[index])
                if index > 1:
                    body["prev_msg_hash"] = rows[index - 1]["message_hash"]
                digest = message_hash_from_body(body)
                rows[index] = {
                    **body,
                    "message_hash": digest,
                    "signatures": [_sign(digest, body["sender"], keys)],
                }
        _write_jsonl(CORE_OUT / f"AB-CORE-GT-{case_id}.jsonl", rows)


def _single_message(keys: dict[str, dict[str, Any]]) -> dict[str, Any]:
    source = json.loads(
        (ROOT / "fixtures/golden_transcripts/GT-01_happy_path_signed.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    source["sender"] = "agent:S"
    return _rehash_and_sign([source], keys)[0]


def _capneg_rows(include_required_crypto: bool) -> list[dict[str, Any]]:
    session_id = "sCNAuthGood" if include_required_crypto else "sCNAuthBad"
    contract_id = "cCNAuthGood" if include_required_crypto else "cCNAuthBad"
    profile_ref = {"profile_id": "AICP-AUTHENTICATED-BASE", "profile_version": "0.1"}
    crypto = ["aicp.crypto.ed25519.v1"] if include_required_crypto else []
    messages = [
        {
            "session_id": session_id,
            "message_id": "m1",
            "timestamp": "2026-06-02T00:00:00Z",
            "sender": "agent:A",
            "message_type": "CAPABILITIES_DECLARE",
            "contract_id": contract_id,
            "payload": {
                "capabilities_id": "cap-auth-a",
                "party_id": "agent:A",
                "supported_profiles": ["aicp.crypto.ed25519.v1"],
                "supported_privacy_modes": ["standard"],
                "supported_aicp_profiles": [profile_ref],
                "required_aicp_profiles": [profile_ref],
            },
        },
        {
            "session_id": session_id,
            "message_id": "m2",
            "timestamp": "2026-06-02T00:00:01Z",
            "sender": "agent:B",
            "message_type": "CAPABILITIES_DECLARE",
            "contract_id": contract_id,
            "payload": {
                "capabilities_id": "cap-auth-b",
                "party_id": "agent:B",
                "supported_profiles": ["aicp.crypto.ed25519.v1"],
                "supported_privacy_modes": ["standard"],
                "supported_aicp_profiles": [profile_ref],
                "required_aicp_profiles": [profile_ref],
            },
        },
    ]
    negotiation_result = {
        "negotiation_id": "neg-auth",
        "session_id": session_id,
        "contract_id": contract_id,
        "participants": ["agent:A", "agent:B"],
        "selected": {
            "crypto_profile": crypto,
            "privacy_mode": "standard",
            "required_extensions": [],
            "aicp_profile": profile_ref,
        },
        "transcript_binding": "chain:auth:m3",
    }
    messages.extend(
        [
            {
                "session_id": session_id,
                "message_id": "m3",
                "timestamp": "2026-06-02T00:00:02Z",
                "sender": "agent:B",
                "message_type": "CAPABILITIES_PROPOSE",
                "contract_id": contract_id,
                "payload": {"negotiation_result": negotiation_result},
            },
            {
                "session_id": session_id,
                "message_id": "m4",
                "timestamp": "2026-06-02T00:00:03Z",
                "sender": "agent:A",
                "message_type": "CAPABILITIES_ACCEPT",
                "contract_id": contract_id,
                "payload": {
                    "negotiation_id": "neg-auth",
                    "accepted": True,
                    "negotiation_result_hash": object_hash("capneg.negotiation_result", negotiation_result),
                },
            },
        ]
    )
    out: list[dict[str, Any]] = []
    previous = None
    for message in messages:
        if previous is not None:
            message["prev_msg_hash"] = previous
        message["message_hash"] = message_hash_from_body(message)
        previous = message["message_hash"]
        out.append(message)
    return out


def main() -> int:
    keys = _load_keys()
    _signed_core_variants(keys)
    golden_rows = [json.loads(line) for line in (ROOT / "fixtures/golden_transcripts/GT-01_happy_path_signed.jsonl").read_text(encoding="utf-8").splitlines() if line]
    for row in golden_rows:
        row["sender"] = "agent:S" if row["sender"] == "agent:A" else "agent:T"
    valid = _rehash_and_sign(golden_rows, keys)
    _write_jsonl(OUT / "AB-01_valid_sender_signed.jsonl", valid)

    multi = copy.deepcopy(valid)
    for message in multi:
        cosigner = "agent:T" if message["sender"] == "agent:S" else "agent:S"
        message["signatures"].append(_sign(message["message_hash"], cosigner, keys))
    _write_jsonl(OUT / "AB-02_valid_multiple_signatures.jsonl", multi)

    base = _single_message(keys)
    cases: dict[str, dict[str, Any]] = {}
    unsigned = copy.deepcopy(base)
    unsigned.pop("signatures")
    cases["AB-03_unsigned_expected_fail.jsonl"] = unsigned
    empty = copy.deepcopy(base)
    empty["signatures"] = []
    cases["AB-04_empty_signatures_expected_fail.jsonl"] = empty
    missing_hash = copy.deepcopy(base)
    missing_hash.pop("message_hash")
    cases["AB-05_missing_message_hash_expected_fail.jsonl"] = missing_hash
    stale = copy.deepcopy(base)
    stale_hash = object_hash("message", {"stale": True})
    stale["message_hash"] = stale_hash
    stale["signatures"] = [_sign(stale_hash, stale["sender"], keys)]
    cases["AB-06_stale_message_hash_expected_fail.jsonl"] = stale
    wrong_object_hash = copy.deepcopy(base)
    other_hash = object_hash("message", {"other": True})
    wrong_object_hash["signatures"] = [_sign(other_hash, base["sender"], keys)]
    cases["AB-07_signature_object_hash_mismatch_expected_fail.jsonl"] = wrong_object_hash
    wrong_type = copy.deepcopy(base)
    wrong_type["signatures"][0]["object_type"] = "contract"
    cases["AB-08_signature_object_type_expected_fail.jsonl"] = wrong_type
    no_sender = copy.deepcopy(base)
    no_sender["signatures"] = [_sign(base["message_hash"], "agent:T", keys)]
    cases["AB-09_no_sender_signature_expected_fail.jsonl"] = no_sender
    kid_mismatch = copy.deepcopy(base)
    kid_mismatch["signatures"] = [_sign(base["message_hash"], base["sender"], keys, kid="WRONG-KID")]
    cases["AB-10_kid_mismatch_expected_fail.jsonl"] = kid_mismatch
    unknown = copy.deepcopy(base)
    unknown_sig = _sign(base["message_hash"], "agent:S", keys)
    unknown_sig.update({"signer": "agent:UNKNOWN", "kid": "UNKNOWN-1"})
    unknown["signatures"] = [unknown_sig]
    cases["AB-11_unknown_signer_key_expected_fail.jsonl"] = unknown
    invalid = copy.deepcopy(base)
    invalid["signatures"][0]["sig_b64url"] = "A" * 86
    cases["AB-12_invalid_signature_expected_fail.jsonl"] = invalid
    copied = copy.deepcopy(base)
    copied["signatures"] = [copy.deepcopy(valid[1]["signatures"][0])]
    cases["AB-13_copied_signature_expected_fail.jsonl"] = copied
    hidden_invalid = copy.deepcopy(base)
    bad_cosignature = _sign(base["message_hash"], "agent:T", keys)
    bad_cosignature["sig_b64url"] = "B" * 86
    hidden_invalid["signatures"].append(bad_cosignature)
    cases["AB-14_invalid_signature_among_valid_expected_fail.jsonl"] = hidden_invalid
    for name, message in cases.items():
        _write_jsonl(OUT / name, [message])

    _write_jsonl(CAPNEG_OUT / "CN-11_authenticated_base_crypto_pass.jsonl", _capneg_rows(True))
    _write_jsonl(CAPNEG_OUT / "CN-12_authenticated_base_crypto_missing_expected_fail.jsonl", _capneg_rows(False))
    print(f"Generated authenticated-base fixtures under {OUT.relative_to(ROOT)} and CAPNEG cases CN-11/CN-12")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
