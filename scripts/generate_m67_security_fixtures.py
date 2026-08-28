#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REF_PY = ROOT / "reference" / "python"
if str(REF_PY) not in sys.path:
    sys.path.insert(0, str(REF_PY))

from aicp_ref.hashing import message_hash_from_body, object_hash  # noqa: E402
from aicp_ref.validate import message_body_without_hash_and_signatures  # noqa: E402


SIGNED_DIR = ROOT / "fixtures" / "security" / "signed_paths"
ALERT_DIR = ROOT / "fixtures" / "extensions" / "alerts"
CAPNEG_DIR = ROOT / "fixtures" / "extensions" / "capneg"
ENFORCEMENT_DIR = ROOT / "fixtures" / "extensions" / "enforcement"
OBJECT_RESYNC_DIR = ROOT / "fixtures" / "extensions" / "object_resync"


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _render_jsonl(rows: list[dict[str, Any]]) -> str:
    return "".join(
        json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
        for row in rows
    )


def _finalize(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    finalized: list[dict[str, Any]] = []
    previous: str | None = None
    for original in rows:
        body = message_body_without_hash_and_signatures(copy.deepcopy(original))
        body.pop("prev_msg_hash", None)
        if previous is not None:
            body["prev_msg_hash"] = previous
        digest = message_hash_from_body(body)
        finalized.append({**body, "message_hash": digest})
        previous = digest
    return finalized


def _capneg_stale_declaration() -> list[dict[str, Any]]:
    profile_mediated = {
        "profile_id": "AICP-MEDIATED-BLOCKING",
        "profile_version": "0.1",
    }
    profile_base = {"profile_id": "AICP-BASE", "profile_version": "0.1"}
    crypto = ["AICP-JCS-1", "AICP-HASH-SHA256-1", "AICP-SIG-ED25519-1"]
    extensions = ["EXT-CAPNEG", "EXT-ENFORCEMENT", "EXT-ALERTS", "EXT-RESUME"]
    selected = {
        "crypto_profile": crypto,
        "privacy_mode": "standard",
        "required_extensions": extensions,
        "aicp_profile": profile_mediated,
    }
    negotiation = {
        "negotiation_id": "neg-cn13",
        "session_id": "sCN13",
        "contract_id": "cCN13",
        "participants": ["agent:A", "agent:B"],
        "selected": selected,
        "transcript_binding": "chain:cn13:m4",
    }
    rows = [
        {
            "session_id": "sCN13",
            "message_id": "m1",
            "timestamp": "2026-08-27T00:00:00Z",
            "sender": "agent:A",
            "message_type": "CAPABILITIES_DECLARE",
            "contract_id": "cCN13",
            "payload": {
                "capabilities_id": "cap-a-cn13-d1",
                "party_id": "agent:A",
                "supported_profiles": crypto,
                "supported_privacy_modes": ["standard"],
                "supported_extensions": extensions,
                "supported_aicp_profiles": [profile_mediated, profile_base],
                "required_aicp_profiles": [profile_mediated],
            },
        },
        {
            "session_id": "sCN13",
            "message_id": "m2",
            "timestamp": "2026-08-27T00:00:01Z",
            "sender": "agent:A",
            "message_type": "CAPABILITIES_DECLARE",
            "contract_id": "cCN13",
            "payload": {
                "capabilities_id": "cap-a-cn13-d2",
                "party_id": "agent:A",
                "supported_profiles": crypto,
                "supported_privacy_modes": ["standard"],
                "supported_extensions": ["EXT-CAPNEG"],
                "supported_aicp_profiles": [profile_base],
                "required_aicp_profiles": [profile_base],
            },
        },
        {
            "session_id": "sCN13",
            "message_id": "m3",
            "timestamp": "2026-08-27T00:00:02Z",
            "sender": "agent:B",
            "message_type": "CAPABILITIES_DECLARE",
            "contract_id": "cCN13",
            "payload": {
                "capabilities_id": "cap-b-cn13",
                "party_id": "agent:B",
                "supported_profiles": crypto,
                "supported_privacy_modes": ["standard"],
                "supported_extensions": extensions,
                "supported_aicp_profiles": [profile_mediated, profile_base],
                "required_aicp_profiles": [profile_mediated],
            },
        },
        {
            "session_id": "sCN13",
            "message_id": "m4",
            "timestamp": "2026-08-27T00:00:03Z",
            "sender": "agent:B",
            "message_type": "CAPABILITIES_PROPOSE",
            "contract_id": "cCN13",
            "payload": {"negotiation_result": negotiation},
        },
        {
            "session_id": "sCN13",
            "message_id": "m5",
            "timestamp": "2026-08-27T00:00:04Z",
            "sender": "agent:A",
            "message_type": "CAPABILITIES_ACCEPT",
            "contract_id": "cCN13",
            "payload": {
                "negotiation_id": "neg-cn13",
                "accepted": True,
                "negotiation_result_hash": object_hash(
                    "capneg.negotiation_result", negotiation
                ),
            },
        },
    ]
    return _finalize(rows)


def _enforcement_mutations() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    source = _load_jsonl(ENFORCEMENT_DIR / "EF-01_allow_and_deliver.jsonl")
    target_mismatch = copy.deepcopy(source)
    target_mismatch[3]["payload"]["target_message_hash"] = object_hash(
        "message", {"different_content_target": True}
    )
    wrong_reference = copy.deepcopy(source)
    wrong_reference[4]["payload"]["verdict_message_id"] = "m999"
    return _finalize(target_mismatch), _finalize(wrong_reference)


def _alert_unknown_action() -> list[dict[str, Any]]:
    rows = copy.deepcopy(
        _load_jsonl(ALERT_DIR / "AL-01_warning_resync_required.jsonl")
    )
    alert = next(item for item in rows if item["message_type"] == "ALERT")
    alert["payload"]["recommended_actions"] = ["RETRY", "NOT-REGISTERED"]
    return _finalize(rows)


def _invalid_alert_signature(
    source: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows = copy.deepcopy(source)
    alert = next(item for item in rows if item["message_type"] == "ALERT")
    alert["signatures"][0]["sig_b64url"] = "A" * 86
    return rows


def _object_resync_case(
    *,
    case: str,
    status: str,
    allow_redaction: bool = False,
    max_bytes: int | None = None,
    mismatch: bool = False,
) -> list[dict[str, Any]]:
    contract = {
        "contract_id": f"c{case}",
        "goal": "object_resync_security_mechanism",
        "roles": ["initiator", "responder"],
    }
    expected_hash = object_hash("contract", contract)
    request_item: dict[str, Any] = {
        "object_hash": expected_hash,
        "want_type": "contract",
    }
    request_payload: dict[str, Any] = {
        "request_id": f"{case.lower()}-request",
        "objects": [request_item],
        "allow_redaction": allow_redaction,
    }
    if max_bytes is not None:
        request_item["max_bytes"] = max_bytes
        request_payload["max_total_bytes"] = max_bytes
    entry: dict[str, Any] = {"object_hash": expected_hash, "status": status}
    if status == "REDACTED":
        entry["redaction_note"] = "Object withheld under the responder's selected local policy."
    if status == "FOUND":
        entry["object_type"] = "contract"
        entry["object"] = (
            {**contract, "goal": "mutated_after_declared_hash"}
            if mismatch
            else contract
        )
    rows = [
        {
            "session_id": f"s{case}",
            "message_id": "m1",
            "timestamp": "2026-08-27T00:10:00Z",
            "sender": "agent:A",
            "message_type": "OBJECT_REQUEST",
            "contract_id": f"c{case}",
            "payload": request_payload,
        },
        {
            "session_id": f"s{case}",
            "message_id": "m2",
            "timestamp": "2026-08-27T00:10:01Z",
            "sender": "agent:B",
            "message_type": "OBJECT_RESPONSE",
            "contract_id": f"c{case}",
            "payload": {
                "request_id": request_payload["request_id"],
                "entries": [entry],
            },
        },
    ]
    return _finalize(rows)


def generated() -> dict[Path, str]:
    signed_source = _load_jsonl(
        SIGNED_DIR / "SP-01_mediated_blocking_signed.jsonl"
    )
    enforcement_target, enforcement_reference = _enforcement_mutations()
    return {
        SIGNED_DIR / "SP-03_truncated_mediated_flow_expected_fail.jsonl": _render_jsonl(
            signed_source[:5]
        ),
        SIGNED_DIR / "SP-04_invalid_alert_signature_expected_fail.jsonl": _render_jsonl(
            _invalid_alert_signature(signed_source)
        ),
        ALERT_DIR / "AL-03_unknown_recommended_action_expected_fail.jsonl": _render_jsonl(
            _alert_unknown_action()
        ),
        CAPNEG_DIR / "CN-13_stale_declaration_rollback_expected_fail.jsonl": _render_jsonl(
            _capneg_stale_declaration()
        ),
        ENFORCEMENT_DIR / "EF-03_allow_target_hash_mismatch_expected_fail.jsonl": _render_jsonl(
            enforcement_target
        ),
        ENFORCEMENT_DIR / "EF-04_wrong_verdict_reference_expected_fail.jsonl": _render_jsonl(
            enforcement_reference
        ),
        OBJECT_RESYNC_DIR / "OR-03_access_denied.jsonl": _render_jsonl(
            _object_resync_case(case="OR3", status="ACCESS_DENIED")
        ),
        OBJECT_RESYNC_DIR / "OR-04_too_large.jsonl": _render_jsonl(
            _object_resync_case(case="OR4", status="TOO_LARGE", max_bytes=4096)
        ),
        OBJECT_RESYNC_DIR / "OR-05_redacted.jsonl": _render_jsonl(
            _object_resync_case(case="OR5", status="REDACTED", allow_redaction=True)
        ),
        OBJECT_RESYNC_DIR / "OR-06_found_hash_mismatch_expected_fail.jsonl": _render_jsonl(
            _object_resync_case(case="OR6", status="FOUND", mismatch=True)
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    stale: list[str] = []
    for path, content in generated().items():
        relative = path.relative_to(ROOT).as_posix()
        if args.write:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        elif not path.is_file() or path.read_text(encoding="utf-8") != content:
            stale.append(relative)
    if stale:
        print("[FAIL] stale M67 security fixtures: " + ", ".join(stale))
        return 1
    print(f"[OK] M67 security fixtures: {len(generated())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
