#!/usr/bin/env python3
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference/python"))
from aicp_ref.hashing import message_hash_from_body  # noqa: E402

OUT_DIR = ROOT / "fixtures/extensions/execution_lifecycle"


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


def ex01() -> list[dict]:
    return finalize([
        {"session_id":"sex-01","message_id":"m1","timestamp":"2026-04-01T09:00:00Z","sender":"agent:orch","message_type":"CONTRACT_PROPOSE","contract_id":"c-ex-01","payload":{"contract":{"contract_id":"c-ex-01","goal":"execution_lifecycle_run"}}},
        {"session_id":"sex-01","message_id":"m2","timestamp":"2026-04-01T09:00:01Z","sender":"agent:worker","message_type":"CONTRACT_ACCEPT","contract_id":"c-ex-01","payload":{"accepted":True}},
        {"session_id":"sex-01","message_id":"m3","timestamp":"2026-04-01T09:00:02Z","sender":"agent:worker","message_type":"RUN_CREATE","contract_id":"c-ex-01","payload":{"run_id":"run-01","thread_id":"thr-01","status":"created"}},
        {"session_id":"sex-01","message_id":"m4","timestamp":"2026-04-01T09:00:03Z","sender":"agent:worker","message_type":"RUN_UPDATE","contract_id":"c-ex-01","payload":{"run_id":"run-01","thread_id":"thr-01","status":"running"}},
        {"session_id":"sex-01","message_id":"m5","timestamp":"2026-04-01T09:00:04Z","sender":"agent:worker","message_type":"RUN_COMPLETE","contract_id":"c-ex-01","payload":{"run_id":"run-01","thread_id":"thr-01","result_hash":"sha256:ex01result"}}
    ])


def ex02() -> list[dict]:
    return finalize([
        {"session_id":"sex-02","message_id":"m1","timestamp":"2026-04-01T09:10:00Z","sender":"agent:orch","message_type":"CONTRACT_PROPOSE","contract_id":"c-ex-02","payload":{"contract":{"contract_id":"c-ex-02","goal":"execution_lifecycle_thread"}}},
        {"session_id":"sex-02","message_id":"m2","timestamp":"2026-04-01T09:10:01Z","sender":"agent:worker","message_type":"CONTRACT_ACCEPT","contract_id":"c-ex-02","payload":{"accepted":True}},
        {"session_id":"sex-02","message_id":"m3","timestamp":"2026-04-01T09:10:02Z","sender":"agent:worker","message_type":"THREAD_CREATE","contract_id":"c-ex-02","payload":{"thread_id":"thr-02"}},
        {"session_id":"sex-02","message_id":"m4","timestamp":"2026-04-01T09:10:03Z","sender":"agent:worker","message_type":"THREAD_APPEND","contract_id":"c-ex-02","payload":{"thread_id":"thr-02","entry_hash":"sha256:ex02e1"}},
        {"session_id":"sex-02","message_id":"m5","timestamp":"2026-04-01T09:10:04Z","sender":"agent:worker","message_type":"THREAD_CLOSE","contract_id":"c-ex-02","payload":{"thread_id":"thr-02","reason_code":"THREAD_DONE"}}
    ])


def ex03() -> list[dict]:
    return finalize([
        {"session_id":"sex-03","message_id":"m1","timestamp":"2026-04-01T09:20:00Z","sender":"agent:worker","message_type":"RUN_CREATE","contract_id":"c-ex-03","payload":{"run_id":"run-03","status":"created","store_ref":{"ref_id":"store-r1","object_hash":"sha256:ex03store","object_type":"context_bundle","access":{"mode":"read","constraint":"scope:run-03","resolution_required":True}}}},
        {"session_id":"sex-03","message_id":"m2","timestamp":"2026-04-01T09:20:01Z","sender":"agent:worker","message_type":"OBJECT_REQUEST","contract_id":"c-ex-03","payload":{"request_id":"or-ex-03","objects":[{"object_hash":"sha256:ex03store","want_type":"context_bundle"}]}},
        {"session_id":"sex-03","message_id":"m3","timestamp":"2026-04-01T09:20:02Z","sender":"mediator:store","message_type":"OBJECT_RESPONSE","contract_id":"c-ex-03","payload":{"request_id":"or-ex-03","entries":[{"object_hash":"sha256:ex03store","status":"FOUND","object_type":"context_bundle","artifact_ref":"artifact://ctx/ex03"}]}},
        {"session_id":"sex-03","message_id":"m4","timestamp":"2026-04-01T09:20:03Z","sender":"agent:worker","message_type":"RUN_UPDATE","contract_id":"c-ex-03","payload":{"run_id":"run-03","status":"running","memory_ref":{"ref_id":"mem-r1","object_hash":"sha256:ex03mem","object_type":"ephemeral_context","access":{"mode":"read_write","constraint":"scope:run-03"}}}}
    ])


def ex04() -> list[dict]:
    return finalize([
        {"session_id":"sex-04","message_id":"m1","timestamp":"2026-04-01T09:30:00Z","sender":"agent:worker","message_type":"RUN_UPDATE","contract_id":"c-ex-04","payload":{"run_id":"run-missing","status":"running"}}
    ])


def ex05() -> list[dict]:
    return finalize([
        {"session_id":"sex-05","message_id":"m1","timestamp":"2026-04-01T09:40:00Z","sender":"agent:worker","message_type":"RUN_CREATE","contract_id":"c-ex-05","payload":{"run_id":"run-05","status":"created"}},
        {"session_id":"sex-05","message_id":"m2","timestamp":"2026-04-01T09:40:01Z","sender":"agent:worker","message_type":"RUN_CANCEL","contract_id":"c-ex-05","payload":{"run_id":"run-05","reason_code":"USER_CANCELLED"}},
        {"session_id":"sex-05","message_id":"m3","timestamp":"2026-04-01T09:40:02Z","sender":"agent:worker","message_type":"RUN_UPDATE","contract_id":"c-ex-05","payload":{"run_id":"run-05","status":"running"}}
    ])


def ex06() -> list[dict]:
    return finalize([
        {"session_id":"sex-06","message_id":"m1","timestamp":"2026-04-01T09:50:00Z","sender":"agent:worker","message_type":"THREAD_CREATE","contract_id":"c-ex-06","payload":{"thread_id":"thr-06"}},
        {"session_id":"sex-06","message_id":"m2","timestamp":"2026-04-01T09:50:01Z","sender":"agent:worker","message_type":"THREAD_CLOSE","contract_id":"c-ex-06","payload":{"thread_id":"thr-06","reason_code":"done"}},
        {"session_id":"sex-06","message_id":"m3","timestamp":"2026-04-01T09:50:02Z","sender":"agent:worker","message_type":"THREAD_APPEND","contract_id":"c-ex-06","payload":{"thread_id":"thr-06","entry_hash":"sha256:ex06late"}}
    ])


def ex07() -> list[dict]:
    return finalize([
        {"session_id":"sex-07","message_id":"m1","timestamp":"2026-04-01T10:00:00Z","sender":"agent:worker","message_type":"RUN_CREATE","contract_id":"c-ex-07","payload":{"run_id":"run-07","status":"created","store_ref":{"ref_id":"store-r7","object_hash":"sha256:ex07missing","object_type":"context_bundle","access":{"mode":"read","constraint":"scope:run-07","resolution_required":True}}}}
    ])


def main() -> int:
    fixtures = {
        "EX-01_basic_run_lifecycle_pass.jsonl": ex01(),
        "EX-02_thread_lifecycle_pass.jsonl": ex02(),
        "EX-03_store_ref_resolved_pass.jsonl": ex03(),
        "EX-04_run_update_before_create_expected_fail.jsonl": ex04(),
        "EX-05_post_terminal_mutation_expected_fail.jsonl": ex05(),
        "EX-06_thread_append_after_close_expected_fail.jsonl": ex06(),
        "EX-07_dangling_store_ref_expected_fail.jsonl": ex07(),
    }
    for name, rows in fixtures.items():
        path = OUT_DIR / name
        write_jsonl(path, rows)
        print(f"wrote {path.relative_to(ROOT)} ({len(rows)} records)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
