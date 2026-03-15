#!/usr/bin/env python3
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference/python"))
from aicp_ref.hashing import message_hash_from_body  # noqa: E402

OUT_DIR = ROOT / "fixtures/extensions/transcript_witness"


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


def tw01() -> list[dict]:
    rows = [
        {"session_id":"stw-01","message_id":"m1","timestamp":"2026-03-25T09:00:00Z","sender":"agent:orchestrator","message_type":"ACTION_PREPARE","contract_id":"c-tw-01","payload":{"escrow_id":"esc-01","tool_call_request_hash":"sha256:tcr1","policy_context_hash":"sha256:pc1"}},
        {"session_id":"stw-01","message_id":"m2","timestamp":"2026-03-25T09:00:01Z","sender":"agent:approver","message_type":"ACTION_APPROVE","contract_id":"c-tw-01","payload":{"escrow_id":"esc-01","approval_hash":"sha256:ap1"}},
        {"session_id":"stw-01","message_id":"m3","timestamp":"2026-03-25T09:00:02Z","sender":"agent:executor","message_type":"ACTION_COMMIT","contract_id":"c-tw-01","payload":{"escrow_id":"esc-01","tool_call_request_hash":"sha256:tcr1","approval_hash":"sha256:ap1","policy_context_hash":"sha256:pc1"}},
    ]
    base = finalize(rows)
    head = base[-1]["message_hash"]
    rows.extend([
        {"session_id":"stw-01","message_id":"m4","timestamp":"2026-03-25T09:00:03Z","sender":"agent:executor","message_type":"WITNESS_SUBMIT","contract_id":"c-tw-01","payload":{"checkpoint":{"checkpoint_id":"cp-01","session_id":"stw-01","head_hash":head,"issued_at":"2026-03-25T09:00:03Z","sequence_no":1,"original_sender_sig_ref":"sig:agent:executor:1"}}},
        {"session_id":"stw-01","message_id":"m5","timestamp":"2026-03-25T09:00:04Z","sender":"mediator:witness-a","message_type":"WITNESS_RECEIPT","contract_id":"c-tw-01","payload":{"receipt":{"receipt_id":"rcp-01","checkpoint_id":"cp-01","submit_message_hash":"TO_BE_FILLED","witness_id":"witness-a","issued_at":"2026-03-25T09:00:04Z"}}}
    ])
    final = finalize(rows)
    final[4]["payload"]["receipt"]["submit_message_hash"] = final[3]["message_hash"]
    return finalize(final)


def tw02() -> list[dict]:
    rows = [
        {"session_id":"stw-02","message_id":"m1","timestamp":"2026-03-25T10:00:00Z","sender":"agent:brand","message_type":"PUBLICATION_PUBLISH","contract_id":"c-tw-02","payload":{"publication_id":"pub-tw-1","version_id":"v1","content_hash":"sha256:pubtw1","ttl_seconds":300}},
    ]
    base = finalize(rows)
    head = base[-1]["message_hash"]
    rows.extend([
        {"session_id":"stw-02","message_id":"m2","timestamp":"2026-03-25T10:00:01Z","sender":"agent:brand","message_type":"WITNESS_SUBMIT","contract_id":"c-tw-02","payload":{"checkpoint":{"checkpoint_id":"cp-02","session_id":"stw-02","head_hash":head,"issued_at":"2026-03-25T10:00:01Z","sequence_no":5}}},
        {"session_id":"stw-02","message_id":"m3","timestamp":"2026-03-25T10:00:02Z","sender":"agent:peer","message_type":"HEAD_EXCHANGE","contract_id":"c-tw-02","payload":{"head":{"session_id":"stw-02","head_hash":head,"as_of":"2026-03-25T10:00:02Z","source_ref":"peer:edge-a"}}},
        {"session_id":"stw-02","message_id":"m4","timestamp":"2026-03-25T10:00:03Z","sender":"agent:peer","message_type":"INCLUSION_PROOF_DECLARE","contract_id":"c-tw-02","payload":{"proof":{"proof_id":"proof-02","checkpoint_id":"cp-02","target_message_hash":head,"root_hash":"sha256:root2","path_hashes":["sha256:p1","sha256:p2"]}}}
    ])
    return finalize(rows)


def tw03() -> list[dict]:
    return finalize([
        {"session_id":"stw-03","message_id":"m1","timestamp":"2026-03-25T11:00:00Z","sender":"mediator:witness-a","message_type":"WITNESS_RECEIPT","contract_id":"c-tw-03","payload":{"receipt":{"receipt_id":"rcp-03","checkpoint_id":"cp-missing","submit_message_hash":"sha256:nope","witness_id":"witness-a","issued_at":"2026-03-25T11:00:00Z"}}}
    ])


def tw04() -> list[dict]:
    rows = [
        {"session_id":"stw-04","message_id":"m1","timestamp":"2026-03-25T12:00:00Z","sender":"agent:a","message_type":"CONTRACT_PROPOSE","contract_id":"c-tw-04","payload":{"contract":{"contract_id":"c-tw-04","goal":"inclusion proof"}}}
    ]
    base = finalize(rows)
    h1 = base[0]["message_hash"]
    rows.extend([
        {"session_id":"stw-04","message_id":"m2","timestamp":"2026-03-25T12:00:01Z","sender":"agent:a","message_type":"WITNESS_SUBMIT","contract_id":"c-tw-04","payload":{"checkpoint":{"checkpoint_id":"cp-04","session_id":"stw-04","head_hash":h1,"issued_at":"2026-03-25T12:00:01Z","sequence_no":1}}},
        {"session_id":"stw-04","message_id":"m3","timestamp":"2026-03-25T12:00:02Z","sender":"agent:a","message_type":"INCLUSION_PROOF_DECLARE","contract_id":"c-tw-04","payload":{"proof":{"proof_id":"proof-04","checkpoint_id":"cp-04","target_message_hash":"sha256:unknown-target","root_hash":"sha256:root4"}}}
    ])
    return finalize(rows)


def tw05() -> list[dict]:
    rows = [
        {"session_id":"stw-05","message_id":"m1","timestamp":"2026-03-25T13:00:00Z","sender":"agent:a","message_type":"CONTRACT_PROPOSE","contract_id":"c-tw-05","payload":{"contract":{"contract_id":"c-tw-05","goal":"strict witness","ext":{"transcript_witness":{"require_strict_head_consensus":True}}}}},
        {"session_id":"stw-05","message_id":"m2","timestamp":"2026-03-25T13:00:00Z","sender":"agent:a","message_type":"HEAD_EXCHANGE","contract_id":"c-tw-05","payload":{"head":{"session_id":"stw-05","head_hash":"TO_FILL_CONTRACT","as_of":"2026-03-25T13:00:00Z"}}},
        {"session_id":"stw-05","message_id":"m3","timestamp":"2026-03-25T13:00:01Z","sender":"agent:a","message_type":"WITNESS_SUBMIT","contract_id":"c-tw-05","payload":{"checkpoint":{"checkpoint_id":"cp-05a","session_id":"stw-05","head_hash":"TO_FILL_CONTRACT","issued_at":"2026-03-25T13:00:01Z","sequence_no":9}}},
        {"session_id":"stw-05","message_id":"m4","timestamp":"2026-03-25T13:00:02Z","sender":"agent:b","message_type":"WITNESS_SUBMIT","contract_id":"c-tw-05","payload":{"checkpoint":{"checkpoint_id":"cp-05b","session_id":"stw-05","head_hash":"TO_FILL_HEAD_EXCHANGE","issued_at":"2026-03-25T13:00:02Z","sequence_no":9}}}
    ]
    draft = finalize(rows)
    contract_hash = draft[0]["message_hash"]
    rows[1]["payload"]["head"]["head_hash"] = contract_hash
    rows[2]["payload"]["checkpoint"]["head_hash"] = contract_hash

    midway = finalize(rows)
    head_exchange_hash = midway[1]["message_hash"]
    rows[3]["payload"]["checkpoint"]["head_hash"] = head_exchange_hash
    return finalize(rows)


def tw06() -> list[dict]:
    rows = [
        {"session_id":"stw-06","message_id":"m1","timestamp":"2026-03-25T14:00:00Z","sender":"agent:a","message_type":"CONTRACT_PROPOSE","contract_id":"c-tw-06","payload":{"contract":{"contract_id":"c-tw-06","goal":"nonrep required","ext":{"transcript_witness":{"require_nonrep_signature_ref":True}}}}},
    ]
    base = finalize(rows)
    h1 = base[0]["message_hash"]
    rows.append({"session_id":"stw-06","message_id":"m2","timestamp":"2026-03-25T14:00:01Z","sender":"agent:a","message_type":"WITNESS_SUBMIT","contract_id":"c-tw-06","payload":{"checkpoint":{"checkpoint_id":"cp-06","session_id":"stw-06","head_hash":h1,"issued_at":"2026-03-25T14:00:01Z","sequence_no":1}}})
    return finalize(rows)


def main() -> int:
    fixtures = {
        "TW-01_submit_receipt_pass.jsonl": tw01(),
        "TW-02_head_exchange_inclusion_pass.jsonl": tw02(),
        "TW-03_receipt_without_submit_expected_fail.jsonl": tw03(),
        "TW-04_unknown_inclusion_target_expected_fail.jsonl": tw04(),
        "TW-05_split_history_expected_fail.jsonl": tw05(),
        "TW-06_nonrep_required_missing_sigref_expected_fail.jsonl": tw06(),
    }
    for name, rows in fixtures.items():
        path = OUT_DIR / name
        write_jsonl(path, rows)
        print(f"wrote {path.relative_to(ROOT)} ({len(rows)} records)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
