#!/usr/bin/env python3
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference/python"))
from aicp_ref.hashing import message_hash_from_body  # noqa: E402

OUT_DIR = ROOT / "fixtures/extensions/action_escrow"


def finalize(rows: list[dict]) -> list[dict]:
    prev = None
    out: list[dict] = []
    for row in rows:
        msg = deepcopy(row)
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


def es01() -> list[dict]:
    return finalize([
        {"session_id":"ses-01","message_id":"m1","timestamp":"2026-03-23T10:00:00Z","sender":"agent:caller","message_type":"ACTION_PREPARE","contract_id":"c-es-01",
         "payload":{"escrow_id":"esc-01","tool_call_request_hash":"sha256:req-01","policy_context_hash":"sha256:pol-01"}},
        {"session_id":"ses-01","message_id":"m2","timestamp":"2026-03-23T10:00:01Z","sender":"agent:approver","message_type":"ACTION_APPROVE","contract_id":"c-es-01",
         "payload":{"escrow_id":"esc-01","approval_hash":"sha256:ap-01"}},
        {"session_id":"ses-01","message_id":"m3","timestamp":"2026-03-23T10:00:02Z","sender":"agent:caller","message_type":"ACTION_COMMIT","contract_id":"c-es-01",
         "payload":{"escrow_id":"esc-01","tool_call_request_hash":"sha256:req-01","approval_hash":"sha256:ap-01","policy_context_hash":"sha256:pol-01"}}
    ])


def es02() -> list[dict]:
    return finalize([
        {"session_id":"ses-02","message_id":"m1","timestamp":"2026-03-23T10:10:00Z","sender":"agent:caller","message_type":"ACTION_COMMIT","contract_id":"c-es-02",
         "payload":{"escrow_id":"esc-02","tool_call_request_hash":"sha256:req-02","approval_hash":"sha256:ap-02","policy_context_hash":"sha256:pol-02"}}
    ])


def es03() -> list[dict]:
    return finalize([
        {"session_id":"ses-03","message_id":"m1","timestamp":"2026-03-23T10:20:00Z","sender":"agent:caller","message_type":"ACTION_PREPARE","contract_id":"c-es-03",
         "payload":{"escrow_id":"esc-03","tool_call_request_hash":"sha256:req-03","policy_context_hash":"sha256:pol-03"}},
        {"session_id":"ses-03","message_id":"m2","timestamp":"2026-03-23T10:20:01Z","sender":"agent:caller","message_type":"ACTION_COMMIT","contract_id":"c-es-03",
         "payload":{"escrow_id":"esc-03","tool_call_request_hash":"sha256:req-03","approval_hash":"sha256:ap-03","policy_context_hash":"sha256:pol-03"}}
    ])


def es04() -> list[dict]:
    return finalize([
        {"session_id":"ses-04","message_id":"m1","timestamp":"2026-03-23T10:30:00Z","sender":"agent:caller","message_type":"ACTION_PREPARE","contract_id":"c-es-04",
         "payload":{"escrow_id":"esc-04","tool_call_request_hash":"sha256:req-04","policy_context_hash":"sha256:pol-04"}},
        {"session_id":"ses-04","message_id":"m2","timestamp":"2026-03-23T10:30:01Z","sender":"agent:approver","message_type":"ACTION_APPROVE","contract_id":"c-es-04",
         "payload":{"escrow_id":"esc-04","approval_hash":"sha256:ap-04"}},
        {"session_id":"ses-04","message_id":"m3","timestamp":"2026-03-23T10:30:02Z","sender":"agent:caller","message_type":"ACTION_COMMIT","contract_id":"c-es-04",
         "payload":{"escrow_id":"esc-04","tool_call_request_hash":"sha256:req-other","approval_hash":"sha256:ap-04","policy_context_hash":"sha256:pol-04"}}
    ])


def main() -> int:
    fixtures = {
        "ES-01_prepare_approve_commit_pass.jsonl": es01(),
        "ES-02_commit_without_prepare_expected_fail.jsonl": es02(),
        "ES-03_commit_without_approve_expected_fail.jsonl": es03(),
        "ES-04_commit_binding_mismatch_expected_fail.jsonl": es04(),
    }
    for name, rows in fixtures.items():
        path = OUT_DIR / name
        write_jsonl(path, rows)
        print(f"wrote {path.relative_to(ROOT)} ({len(rows)} records)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
