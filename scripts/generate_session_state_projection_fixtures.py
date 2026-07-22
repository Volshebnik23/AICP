#!/usr/bin/env python3
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
REF_PY = ROOT / "reference/python"
if str(REF_PY) not in sys.path:
    sys.path.insert(0, str(REF_PY))

from aicp_ref.hashing import message_hash_from_body, object_hash  # noqa: E402
from aicp_ref.session_state import PROJECTION_OBJECT_TYPE, PROJECTION_VERSION  # noqa: E402


OUT = ROOT / "fixtures/extensions/object_resync/state_projection_v1"


def _hash_message(body: dict[str, Any]) -> dict[str, Any]:
    return {**body, "message_hash": message_hash_from_body(body)}


def _base_rows() -> list[dict[str, Any]]:
    request = _hash_message(
        {
            "session_id": "sSP1",
            "message_id": "m1",
            "timestamp": "2026-06-01T00:00:00Z",
            "sender": "agent:A",
            "message_type": "STATE_SYNC_REQUEST",
            "contract_id": "cSP1",
            "payload": {"request_id": "sp-request-1", "want_closed_status": True},
        }
    )
    remote_head_hash = object_hash("message", {"declared_remote_head": "sSP1/main/v2"})
    state = {
        "projection_version": PROJECTION_VERSION,
        "session_id": "sSP1",
        "contract_id": "cSP1",
        "as_of_message_hash": remote_head_hash,
        "session_status": "OPEN",
        "active_contract_ref": {"branch_id": "main", "base_version": "v1", "head_version": "v2"},
        "selected_aicp_profile": {"profile_id": "AICP-BASE", "profile_version": "0.1"},
        "active_extensions": ["EXT-OBJECT-RESYNC"],
        "participant_refs": ["agent:A", "agent:B"],
        "evidence_refs": [f"msghash:{request['message_hash']}"],
    }
    response_body = {
        "session_id": "sSP1",
        "message_id": "m2",
        "timestamp": "2026-06-01T00:00:01Z",
        "sender": "agent:B",
        "message_type": "STATE_SYNC_RESPONSE",
        "contract_id": "cSP1",
        "payload": {
            "request_id": "sp-request-1",
            "session_state": state,
            "session_state_hash": object_hash(PROJECTION_OBJECT_TYPE, state),
            "branch_heads": [
                {"branch_id": "main", "head_version": "v2", "message_hash": remote_head_hash}
            ],
            "active_head_version": "v2",
        },
        "prev_msg_hash": request["message_hash"],
    }
    return [request, _hash_message(response_body)]


def _refresh(rows: list[dict[str, Any]], *, preserve_projection_hash: bool = False) -> list[dict[str, Any]]:
    state = rows[1]["payload"]["session_state"]
    if not preserve_projection_hash:
        rows[1]["payload"]["session_state_hash"] = object_hash(PROJECTION_OBJECT_TYPE, state)
    response_body = dict(rows[1])
    response_body.pop("message_hash", None)
    rows[1] = _hash_message(response_body)
    return rows


def _write(name: str, rows: list[dict[str, Any]]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    path.write_text(
        "".join(json.dumps(row, separators=(",", ":"), ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _mutated(mutator: Callable[[list[dict[str, Any]]], None], *, preserve_projection_hash: bool = False) -> list[dict[str, Any]]:
    rows = copy.deepcopy(_base_rows())
    mutator(rows)
    return _refresh(rows, preserve_projection_hash=preserve_projection_hash)


def main() -> int:
    _write("SP-01_valid.jsonl", _base_rows())
    _write("SP-02_session_mismatch_expected_fail.jsonl", _mutated(lambda rows: rows[1]["payload"]["session_state"].update(session_id="other-session")))
    _write("SP-03_contract_mismatch_expected_fail.jsonl", _mutated(lambda rows: rows[1]["payload"]["session_state"].update(contract_id="other-contract")))
    _write(
        "SP-04_projection_hash_mismatch_expected_fail.jsonl",
        _mutated(
            lambda rows: rows[1]["payload"].update(session_state_hash=object_hash("message", {"wrong": True})),
            preserve_projection_hash=True,
        ),
    )
    _write("SP-05_malformed_contract_ref_expected_fail.jsonl", _mutated(lambda rows: rows[1]["payload"]["session_state"]["active_contract_ref"].pop("base_version")))
    _write("SP-06_unregistered_profile_expected_fail.jsonl", _mutated(lambda rows: rows[1]["payload"]["session_state"].update(selected_aicp_profile={"profile_id": "AICP-NOT-REGISTERED", "profile_version": "9.9"})))
    _write("SP-07_invalid_extension_expected_fail.jsonl", _mutated(lambda rows: rows[1]["payload"]["session_state"].update(active_extensions=["EXT-NOT-REGISTERED"])))
    _write("SP-08_active_head_mismatch_expected_fail.jsonl", _mutated(lambda rows: rows[1]["payload"].update(active_head_version="v9")))
    unresolved_hash = object_hash("message", {"unknown_evidence": True})
    _write("SP-09_invalid_evidence_ref_expected_fail.jsonl", _mutated(lambda rows: rows[1]["payload"]["session_state"].update(evidence_refs=[f"msghash:{unresolved_hash}"])))
    _write("SP-10_contradictory_state_expected_fail.jsonl", _mutated(lambda rows: rows[1]["payload"]["session_state"].update(unresolved_conflict_refs=["conflict:C1"])))
    unbound_hash = object_hash("message", {"unbound_head": True})
    _write("SP-11_unbound_as_of_expected_fail.jsonl", _mutated(lambda rows: rows[1]["payload"]["session_state"].update(as_of_message_hash=unbound_hash)))
    _write("SP-12_malformed_as_of_expected_fail.jsonl", _mutated(lambda rows: rows[1]["payload"]["session_state"].update(as_of_message_hash="sha256:short")))
    print(f"Generated 12 strict state-projection fixtures under {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
