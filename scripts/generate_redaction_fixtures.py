#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference/python"))

from aicp_ref.hashing import message_hash_from_body  # noqa: E402

OUT_DIR = ROOT / "fixtures/extensions/redaction"
CREF = {"branch_id": "main", "base_version": "v1", "head_version": "v1"}


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


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(r, separators=(",", ":"), ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")


def build_case(case_id: str, *, with_pii: bool = False, include_retention: bool = True, original_ref_mode: str = "valid", include_proof: bool = True, bad_pii: bool = False, retention_missing_audit: bool = False) -> list[dict]:
    session_id = f"s{case_id}"
    contract_id = f"c{case_id}"

    contract_ext = {}
    if include_retention:
        rp = {
            "ttl_seconds": 86400,
            "delete_semantics": "tombstone",
            "audit_retention_seconds": 2592000,
        }
        if retention_missing_audit:
            rp.pop("audit_retention_seconds", None)
        contract_ext["redaction"] = {"retention_policy": rp}

    msg1 = {
        "session_id": session_id,
        "message_id": "m1",
        "timestamp": "2026-03-12T00:00:00Z",
        "sender": "agent:A",
        "message_type": "CONTRACT_PROPOSE",
        "contract_id": contract_id,
        "contract_ref": CREF,
        "payload": {
            "contract": {
                "contract_id": contract_id,
                "goal": "redaction_contract",
                "roles": ["initiator", "responder"],
                "ext": contract_ext,
            }
        },
    }

    msg2 = {
        "session_id": session_id,
        "message_id": "m2",
        "timestamp": "2026-03-12T00:00:02Z",
        "sender": "agent:B",
        "message_type": "CONTRACT_ACCEPT",
        "contract_id": contract_id,
        "contract_ref": CREF,
        "payload": {"accepted": True},
    }

    msg3 = {
        "session_id": session_id,
        "message_id": "m3",
        "timestamp": "2026-03-12T00:00:04Z",
        "sender": "agent:A",
        "message_type": "CONTENT_MESSAGE",
        "contract_id": contract_id,
        "payload": {
            "content": "Customer record includes sensitive values.",
            "content_type": "text/plain",
        },
    }

    baseline = finalize([msg1, msg2, msg3])
    original_hash = baseline[-1]["message_hash"]
    if original_ref_mode == "unknown":
        original_hash = "sha256:UNKNOWN_ORIGINAL_HASH"

    redaction_payload = {
        "original_message_hash": original_hash,
        "redaction_policy_ref": "policy:redaction:customer_profile:v1",
        "redaction_proof": {
            "proof_type": "policy-exec-attest-v1",
            "proof_ref": "objhash:sha256:redaction-proof-rd",
            "generated_at": "2026-03-12T00:00:05Z",
        },
        "artifact_refs": ["msgid:m3"],
        "replacement_summary": {
            "replaced_classes": ["email", "phone"],
            "method": "tokenize",
        },
    }

    if not include_proof:
        redaction_payload.pop("redaction_proof", None)

    if with_pii:
        pii = {
            "ref_id": "pii:customer:001",
            "class": "contact.email",
            "controller": "org:crm",
            "access_policy_ref": "policy:pii-access:v1",
            "handle_digest": "sha256:pii-handle-001",
        }
        if bad_pii:
            pii["email"] = "user@example.com"
        redaction_payload["pii_refs"] = [pii]

    msg4 = {
        "session_id": session_id,
        "message_id": "m4",
        "timestamp": "2026-03-12T00:00:06Z",
        "sender": "agent:A",
        "message_type": "CONTENT_REDACTED",
        "contract_id": contract_id,
        "payload": redaction_payload,
    }

    return finalize([msg1, msg2, msg3, msg4])


def main() -> int:
    fixtures = {
        "RD-01_basic_redaction_pass.jsonl": build_case("RD01"),
        "RD-02_redaction_with_pii_refs_pass.jsonl": build_case("RD02", with_pii=True),
        "RD-03_contract_retention_policy_pass.jsonl": build_case("RD03", include_retention=True),
        "RD-04_missing_original_hash_expected_fail.jsonl": build_case("RD04", original_ref_mode="unknown"),
        "RD-05_missing_redaction_proof_expected_fail.jsonl": build_case("RD05", include_proof=False),
        "RD-06_invalid_pii_ref_expected_fail.jsonl": build_case("RD06", with_pii=True, bad_pii=True),
        "RD-07_missing_retention_field_expected_fail.jsonl": build_case("RD07", include_retention=True, retention_missing_audit=True),
    }

    for filename, rows in fixtures.items():
        write_jsonl(OUT_DIR / filename, rows)

    print(f"Generated {len(fixtures)} redaction fixtures in {OUT_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
