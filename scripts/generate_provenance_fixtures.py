#!/usr/bin/env python3
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference/python"))
from aicp_ref.hashing import message_hash_from_body  # noqa: E402

OUT_DIR = ROOT / "fixtures/extensions/provenance"


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


def pr01() -> list[dict]:
    return finalize([
        {"session_id":"spr-01","message_id":"m1","timestamp":"2026-03-23T09:00:00Z","sender":"agent:planner","message_type":"PROVENANCE_DECLARE","contract_id":"c-pr-01",
         "payload":{"graph_id":"g-pr-01","nodes":[
             {"node_id":"n1","node_type":"artifact_node","artifact_ref":"objhash:sha256:a1","originator":"agent:planner"},
             {"node_id":"n2","node_type":"transform_node","parent_node_ids":["n1"],"operation_ref":"workflow:sync:plan"}
         ]}},
        {"session_id":"spr-01","message_id":"m2","timestamp":"2026-03-23T09:00:01Z","sender":"agent:worker","message_type":"PROVENANCE_APPEND","contract_id":"c-pr-01",
         "payload":{"graph_id":"g-pr-01","node":{"node_id":"n3","node_type":"artifact_node","parent_node_ids":["n2"],"artifact_ref":"objhash:sha256:a2","originator":"agent:worker"}}},
        {"session_id":"spr-01","message_id":"m3","timestamp":"2026-03-23T09:00:02Z","sender":"agent:auditor","message_type":"PROVENANCE_APPEND","contract_id":"c-pr-01",
         "payload":{"graph_id":"g-pr-01","node":{"node_id":"n4","node_type":"decision_node","parent_node_ids":["n3"],"policy_ref":"policy:quality:v1","approval_ref":"msghash:sha256:approve"}}}
    ])


def pr02() -> list[dict]:
    return finalize([
        {"session_id":"spr-02","message_id":"m1","timestamp":"2026-03-23T09:10:00Z","sender":"agent:planner","message_type":"PROVENANCE_DECLARE","contract_id":"c-pr-02",
         "payload":{"graph_id":"g-pr-02","nodes":[{"node_id":"n1","node_type":"artifact_node","artifact_ref":"objhash:sha256:b1"}]}},
        {"session_id":"spr-02","message_id":"m2","timestamp":"2026-03-23T09:10:01Z","sender":"agent:worker","message_type":"PROVENANCE_APPEND","contract_id":"c-pr-02",
         "payload":{"graph_id":"g-pr-02","node":{"node_id":"n2","node_type":"transform_node","parent_node_ids":["n-missing"],"operation_ref":"workflow:sync:x"}}}
    ])


def pr03() -> list[dict]:
    return finalize([
        {"session_id":"spr-03","message_id":"m1","timestamp":"2026-03-23T09:20:00Z","sender":"agent:planner","message_type":"PROVENANCE_DECLARE","contract_id":"c-pr-03",
         "payload":{"graph_id":"g-pr-03","nodes":[{"node_id":"n1","node_type":"artifact_node","artifact_ref":"objhash:sha256:c1"}]}},
        {"session_id":"spr-03","message_id":"m2","timestamp":"2026-03-23T09:20:01Z","sender":"agent:worker","message_type":"PROVENANCE_APPEND","contract_id":"c-pr-03",
         "payload":{"graph_id":"g-pr-03","node":{"node_id":"n1","node_type":"artifact_node","parent_node_ids":["n1"],"artifact_ref":"objhash:sha256:c2"}}}
    ])


def main() -> int:
    fixtures = {
        "PR-01_dag_multi_agent_pass.jsonl": pr01(),
        "PR-02_append_missing_parent_expected_fail.jsonl": pr02(),
        "PR-03_append_duplicate_node_expected_fail.jsonl": pr03(),
    }
    for name, rows in fixtures.items():
        path = OUT_DIR / name
        write_jsonl(path, rows)
        print(f"wrote {path.relative_to(ROOT)} ({len(rows)} records)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
