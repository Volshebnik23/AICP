#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference/python"))
from aicp_ref.hashing import message_hash_from_body, object_hash  # noqa: E402


def finalize(rows: list[dict]) -> list[dict]:
    prev=None
    out=[]
    for row in rows:
        msg=dict(row)
        msg.pop('message_hash',None)
        if prev is not None:
            msg['prev_msg_hash']=prev
        msg['message_hash']=message_hash_from_body(msg)
        prev=msg['message_hash']
        out.append(msg)
    return out


def write(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('\n'.join(json.dumps(r,separators=(',',':'),ensure_ascii=False) for r in rows)+'\n',encoding='utf-8')


def main() -> None:
    cref={"branch_id":"main","base_version":"v1","head_version":"v1"}

    wf1={"steps":[{"id":"S1","action":"summarize"}]}
    wf1_hash=object_hash('workflow',wf1)
    wf2={"steps":[{"id":"S1","action":"summarize"},{"id":"S2","action":"review"}]}
    wf2_hash=object_hash('workflow',wf2)

    wf01=finalize([
        {"session_id":"sWF1","message_id":"m1","timestamp":"2026-01-07T00:00:00Z","sender":"agent:A","message_type":"CONTRACT_PROPOSE","contract_id":"cWF1","contract_ref":cref,"payload":{"contract":{"contract_id":"cWF1","goal":"workflow_sync_happy","roles":["initiator","responder"]}}},
        {"session_id":"sWF1","message_id":"m2","timestamp":"2026-01-07T00:00:02Z","sender":"agent:B","message_type":"CONTRACT_ACCEPT","contract_id":"cWF1","contract_ref":cref,"payload":{"accepted":True}},
        {"session_id":"sWF1","message_id":"m3","timestamp":"2026-01-07T00:00:04Z","sender":"planner:P","message_type":"WORKFLOW_DECLARE","contract_id":"cWF1","contract_ref":cref,"payload":{"workflow_id":"W1","contract_head_version":"v1","version":"v1","workflow_artifact_ref":{"object_type":"workflow","object":wf1,"object_hash":wf1_hash},"workflow_hash":wf1_hash,"step_index":0}},
        {"session_id":"sWF1","message_id":"m4","timestamp":"2026-01-07T00:00:06Z","sender":"executor:E","message_type":"WORKFLOW_STEP_ATTEST","contract_id":"cWF1","contract_ref":cref,"payload":{"workflow_id":"W1","step_id":"S1","contract_head_version":"v1","status":"completed","step_index":0,"output_hash":"sha256:wf01-output"}},
    ])

    wf02=finalize([
        {"session_id":"sWF2","message_id":"m1","timestamp":"2026-01-07T00:10:00Z","sender":"agent:A","message_type":"CONTRACT_PROPOSE","contract_id":"cWF2","contract_ref":cref,"payload":{"contract":{"contract_id":"cWF2","goal":"workflow_sync_update","roles":["initiator","responder"]}}},
        {"session_id":"sWF2","message_id":"m2","timestamp":"2026-01-07T00:10:02Z","sender":"agent:B","message_type":"CONTRACT_ACCEPT","contract_id":"cWF2","contract_ref":cref,"payload":{"accepted":True}},
        {"session_id":"sWF2","message_id":"m3","timestamp":"2026-01-07T00:10:04Z","sender":"planner:P","message_type":"WORKFLOW_DECLARE","contract_id":"cWF2","contract_ref":cref,"payload":{"workflow_id":"W1","contract_head_version":"v1","version":"v1","workflow_artifact_ref":{"object_type":"workflow","object":wf1,"object_hash":wf1_hash},"workflow_hash":wf1_hash,"step_index":0}},
        {"session_id":"sWF2","message_id":"m4","timestamp":"2026-01-07T00:10:06Z","sender":"planner:P","message_type":"WORKFLOW_UPDATE","contract_id":"cWF2","contract_ref":cref,"payload":{"workflow_id":"W1","contract_head_version":"v1","version":"v2","base_workflow_hash":wf1_hash,"workflow_artifact_ref":{"object_type":"workflow","object":wf2,"object_hash":wf2_hash},"workflow_hash":wf2_hash}},
        {"session_id":"sWF2","message_id":"m5","timestamp":"2026-01-07T00:10:08Z","sender":"executor:E","message_type":"WORKFLOW_STEP_ATTEST","contract_id":"cWF2","contract_ref":cref,"payload":{"workflow_id":"W1","step_id":"S1","contract_head_version":"v1","status":"completed","step_index":0,"output_hash":"sha256:wf02-output-1"}},
        {"session_id":"sWF2","message_id":"m6","timestamp":"2026-01-07T00:10:10Z","sender":"executor:E","message_type":"WORKFLOW_STEP_ATTEST","contract_id":"cWF2","contract_ref":cref,"payload":{"workflow_id":"W1","step_id":"S2","contract_head_version":"v1","status":"completed","step_index":1,"output_hash":"sha256:wf02-output-2"}},
    ])

    wf03=finalize([
        {"session_id":"sWF3","message_id":"m1","timestamp":"2026-01-07T00:20:00Z","sender":"agent:A","message_type":"CONTRACT_PROPOSE","contract_id":"cWF3","contract_ref":cref,"payload":{"contract":{"contract_id":"cWF3","goal":"workflow_missing_ref","roles":["initiator","responder"]}}},
        {"session_id":"sWF3","message_id":"m2","timestamp":"2026-01-07T00:20:02Z","sender":"agent:B","message_type":"CONTRACT_ACCEPT","contract_id":"cWF3","contract_ref":cref,"payload":{"accepted":True}},
        {"session_id":"sWF3","message_id":"m3","timestamp":"2026-01-07T00:20:04Z","sender":"executor:E","message_type":"WORKFLOW_STEP_ATTEST","contract_id":"cWF3","contract_ref":cref,"payload":{"workflow_id":"W-missing","step_id":"S1","contract_head_version":"v1","status":"completed","step_index":0,"output_hash":"sha256:wf03-output"}},
    ])

    wf04=finalize([
        {"session_id":"sWF4","message_id":"m1","timestamp":"2026-01-07T00:30:00Z","sender":"agent:A","message_type":"CONTRACT_PROPOSE","contract_id":"cWF4","contract_ref":cref,"payload":{"contract":{"contract_id":"cWF4","goal":"workflow_non_monotonic","roles":["initiator","responder"]}}},
        {"session_id":"sWF4","message_id":"m2","timestamp":"2026-01-07T00:30:02Z","sender":"agent:B","message_type":"CONTRACT_ACCEPT","contract_id":"cWF4","contract_ref":cref,"payload":{"accepted":True}},
        {"session_id":"sWF4","message_id":"m3","timestamp":"2026-01-07T00:30:04Z","sender":"planner:P","message_type":"WORKFLOW_DECLARE","contract_id":"cWF4","contract_ref":cref,"payload":{"workflow_id":"W1","contract_head_version":"v1","version":"v1","workflow_artifact_ref":{"object_type":"workflow","object":wf1,"object_hash":wf1_hash},"workflow_hash":wf1_hash}},
        {"session_id":"sWF4","message_id":"m4","timestamp":"2026-01-07T00:30:06Z","sender":"executor:E","message_type":"WORKFLOW_STEP_ATTEST","contract_id":"cWF4","contract_ref":cref,"payload":{"workflow_id":"W1","step_id":"S2","contract_head_version":"v1","status":"completed","step_index":1,"output_hash":"sha256:wf04-output-1"}},
        {"session_id":"sWF4","message_id":"m5","timestamp":"2026-01-07T00:30:08Z","sender":"executor:E","message_type":"WORKFLOW_STEP_ATTEST","contract_id":"cWF4","contract_ref":cref,"payload":{"workflow_id":"W1","step_id":"S1","contract_head_version":"v1","status":"completed","step_index":0,"output_hash":"sha256:wf04-output-0"}},
    ])

    out=ROOT/'fixtures/extensions/workflow_sync'
    write(out/'WF-01_declare_and_step_attest_pass.jsonl',wf01)
    write(out/'WF-02_update_and_monotonic_steps_pass.jsonl',wf02)
    write(out/'WF-03_step_without_declare_expected_fail.jsonl',wf03)
    write(out/'WF-04_non_monotonic_step_index_expected_fail.jsonl',wf04)
    print('Generated workflow sync fixtures')

if __name__=='__main__':
    main()
