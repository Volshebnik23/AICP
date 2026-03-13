#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference/python"))

from aicp_ref.hashing import message_hash_from_body, object_hash  # noqa: E402


OUT_DIR = ROOT / "fixtures/extensions/confidentiality"
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


def build_transcript(case_id: str, mode: str, confidentiality_overrides: dict | None = None) -> list[dict]:
    negotiation_result = {
        "negotiation_id": f"NEG-{case_id}",
        "session_id": f"s{case_id}",
        "contract_id": f"c{case_id}",
        "participants": ["agent:A", "agent:B"],
        "selected": {
            "crypto_profile": ["AICP-JCS-1", "AICP-HASH-SHA256-1", "AICP-SIG-ED25519-1"],
            "privacy_mode": mode,
            "required_extensions": ["EXT-CAPNEG", "EXT-CONFIDENTIALITY"]
        },
        "transcript_binding": "msgid:m3"
    }
    negotiation_hash = object_hash("capneg.negotiation_result", negotiation_result)

    confidentiality = {
        "mode_id": mode,
        "negotiation_result_hash": negotiation_hash
    }
    if mode == "redacted":
        confidentiality["redaction_artifact_refs"] = ["objhash:sha256:redaction-proof-1"]
    elif mode == "metadata-only":
        confidentiality["metadata_projection"] = {
            "subject": "ticket.summary",
            "priority": "ticket.priority"
        }
    elif mode == "classification-only":
        confidentiality["classification_labels"] = ["pii:limited", "risk:moderate"]
        confidentiality["classification_evidence_refs"] = ["msgid:m2"]

    if confidentiality_overrides:
        for key, value in confidentiality_overrides.items():
            if value is None:
                confidentiality.pop(key, None)
            else:
                confidentiality[key] = value

    rows = [
        {
            "session_id": f"s{case_id}",
            "message_id": "m1",
            "timestamp": "2026-03-10T00:00:00Z",
            "sender": "agent:A",
            "message_type": "CAPABILITIES_DECLARE",
            "contract_id": f"c{case_id}",
            "payload": {
                "capabilities_id": f"cap-A-{case_id}",
                "party_id": "agent:A",
                "supported_profiles": ["AICP-JCS-1", "AICP-HASH-SHA256-1", "AICP-SIG-ED25519-1"],
                "supported_privacy_modes": ["full", "redacted", "metadata-only", "classification-only"],
                "supported_extensions": ["EXT-CAPNEG", "EXT-CONFIDENTIALITY"]
            }
        },
        {
            "session_id": f"s{case_id}",
            "message_id": "m2",
            "timestamp": "2026-03-10T00:00:02Z",
            "sender": "agent:B",
            "message_type": "CAPABILITIES_DECLARE",
            "contract_id": f"c{case_id}",
            "payload": {
                "capabilities_id": f"cap-B-{case_id}",
                "party_id": "agent:B",
                "supported_profiles": ["AICP-JCS-1", "AICP-HASH-SHA256-1", "AICP-SIG-ED25519-1"],
                "supported_privacy_modes": ["full", "redacted", "metadata-only", "classification-only"],
                "supported_extensions": ["EXT-CAPNEG", "EXT-CONFIDENTIALITY"]
            }
        },
        {
            "session_id": f"s{case_id}",
            "message_id": "m3",
            "timestamp": "2026-03-10T00:00:04Z",
            "sender": "agent:A",
            "message_type": "CAPABILITIES_PROPOSE",
            "contract_id": f"c{case_id}",
            "payload": {"negotiation_result": negotiation_result}
        },
        {
            "session_id": f"s{case_id}",
            "message_id": "m4",
            "timestamp": "2026-03-10T00:00:06Z",
            "sender": "agent:B",
            "message_type": "CAPABILITIES_ACCEPT",
            "contract_id": f"c{case_id}",
            "payload": {
                "negotiation_id": f"NEG-{case_id}",
                "accepted": True,
                "negotiation_result_hash": negotiation_hash
            }
        },
        {
            "session_id": f"s{case_id}",
            "message_id": "m5",
            "timestamp": "2026-03-10T00:00:08Z",
            "sender": "agent:A",
            "message_type": "CONTRACT_PROPOSE",
            "contract_id": f"c{case_id}",
            "contract_ref": CREF,
            "payload": {
                "contract": {
                    "contract_id": f"c{case_id}",
                    "goal": "confidentiality_bound_contract",
                    "roles": ["initiator", "responder"],
                    "ext": {
                        "capneg": {
                            "negotiation_id": f"NEG-{case_id}",
                            "negotiation_result_hash": negotiation_hash,
                            "selected": negotiation_result["selected"]
                        },
                        "confidentiality": confidentiality
                    }
                }
            }
        },
        {
            "session_id": f"s{case_id}",
            "message_id": "m6",
            "timestamp": "2026-03-10T00:00:10Z",
            "sender": "agent:B",
            "message_type": "CONTRACT_ACCEPT",
            "contract_id": f"c{case_id}",
            "contract_ref": CREF,
            "payload": {"accepted": True}
        }
    ]

    return finalize(rows)


def main() -> int:
    cases = {
        "CF-01_full_mode_pass.jsonl": build_transcript("CF01", "full"),
        "CF-02_redacted_mode_with_artifacts_pass.jsonl": build_transcript("CF02", "redacted"),
        "CF-03_metadata_only_with_projection_pass.jsonl": build_transcript("CF03", "metadata-only"),
        "CF-04_classification_only_with_labels_pass.jsonl": build_transcript("CF04", "classification-only"),
        "CF-05_redacted_missing_artifacts_expected_fail.jsonl": build_transcript("CF05", "redacted", {"redaction_artifact_refs": None}),
        "CF-06_metadata_only_missing_projection_expected_fail.jsonl": build_transcript("CF06", "metadata-only", {"metadata_projection": None}),
        "CF-07_classification_only_missing_labels_expected_fail.jsonl": build_transcript(
            "CF07",
            "classification-only",
            {"classification_labels": None}
        ),
        "CF-08_capneg_contract_mode_mismatch_expected_fail.jsonl": build_transcript("CF08", "full", {"mode_id": "redacted", "redaction_artifact_refs": ["msgid:m1"]})
    }

    for filename, rows in cases.items():
        write_jsonl(OUT_DIR / filename, rows)

    print(f"Generated {len(cases)} confidentiality fixtures in {OUT_DIR.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
