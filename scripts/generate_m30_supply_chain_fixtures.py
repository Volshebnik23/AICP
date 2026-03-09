#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
REF_PY = ROOT / "reference/python"
if str(REF_PY) not in sys.path:
    sys.path.insert(0, str(REF_PY))

from aicp_ref.hashing import message_hash_from_body  # noqa: E402

OUT = ROOT / "fixtures/extensions/tool_supply_chain"


def add_hashes(rows: list[dict]) -> list[dict]:
    prev = None
    for row in rows:
        row.pop("message_hash", None)
        if prev is None:
            row.pop("prev_msg_hash", None)
        else:
            row["prev_msg_hash"] = prev
        row["message_hash"] = message_hash_from_body(row)
        prev = row["message_hash"]
    return rows


def write(name: str, rows: list[dict]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, separators=(",", ":")) + "\n")


def base_contract(session: str, contract: str, pin_hash: str, pinned: list[dict], manifests: list[dict], head: str = "v1") -> dict:
    return {
        "session_id": session,
        "message_id": "m1",
        "timestamp": "2026-03-09T00:00:00Z",
        "sender": "agent:buyer",
        "message_type": "CONTRACT_PROPOSE",
        "contract_id": contract,
        "contract_ref": {"branch_id": "main", "base_version": head, "head_version": head},
        "payload": {
            "contract": {
                "contract_id": contract,
                "goal": "m30_supply_chain",
                "roles": ["buyer", "mediator", "tool"],
                "ext": {
                    "tool_gating": {"mode": "blocking", "acceptors": ["mediator:M"]},
                    "artifact_pinning": {
                        "manifest_set_hash": pin_hash,
                        "pinned_artifacts": pinned,
                        "manifests": manifests,
                    },
                },
            }
        },
    }


def main() -> None:
    manifest_v1 = {
        "manifest_id": "tool.weather",
        "artifact_kind": "tool",
        "issuer_id": "issuer:trusted-tools",
        "issuer_scoped_id": "issuer:trusted-tools#tool.weather",
        "version": "1.0.0",
        "interface_version": "2026-03",
        "description": "Weather lookup tool",
        "risk_class": "low",
        "content_hash": "sha256:weather_v1_content",
        "signature": {"signer": "issuer:trusted-tools", "alg": "ed25519", "sig_b64url": "sig_v1"},
    }
    manifest_v2 = {**manifest_v1, "version": "2.0.0", "content_hash": "sha256:weather_v2_content", "signature": {"signer": "issuer:trusted-tools", "alg": "ed25519", "sig_b64url": "sig_v2"}}

    pin_v1 = {
        "artifact_kind": "tool",
        "manifest_id": "tool.weather",
        "issuer_id": "issuer:trusted-tools",
        "issuer_scoped_id": "issuer:trusted-tools#tool.weather",
        "version": "1.0.0",
        "content_hash": "sha256:weather_v1_content",
    }

    common_tail = [
        {"session_id": "S", "message_id": "m2", "timestamp": "2026-03-09T00:00:03Z", "sender": "agent:seller", "message_type": "CONTRACT_ACCEPT", "contract_id": "C", "contract_ref": {"branch_id": "main", "base_version": "v1", "head_version": "v1"}, "payload": {"accepted": True}},
        {"session_id": "S", "message_id": "m3", "timestamp": "2026-03-09T00:00:06Z", "sender": "agent:buyer", "message_type": "TOOL_CALL_REQUEST", "contract_id": "C", "contract_ref": {"branch_id": "main", "base_version": "v1", "head_version": "v1"}, "payload": {"tool_id": "tool.weather", "operation": "get_forecast", "args_hash": "sha256:req", "manifest_ref": {}}},
        {"session_id": "S", "message_id": "m4", "timestamp": "2026-03-09T00:00:09Z", "sender": "mediator:M", "message_type": "TOOL_CALL_VERDICT", "contract_id": "C", "contract_ref": {"branch_id": "main", "base_version": "v1", "head_version": "v1"}, "payload": {"decision": "ALLOW", "target_request_hash": "<fill>"}},
        {"session_id": "S", "message_id": "m5", "timestamp": "2026-03-09T00:00:12Z", "sender": "tool:weather", "message_type": "TOOL_CALL_RESULT", "contract_id": "C", "contract_ref": {"branch_id": "main", "base_version": "v1", "head_version": "v1"}, "payload": {"target_request_hash": "<fill>", "outcome": "SUCCESS", "result_hash": "sha256:ok", "verdict_ref": "m4"}},
    ]

    # A: valid baseline
    a = [base_contract("sM30A", "cM30A", "sha256:set_v1", [pin_v1], [manifest_v1])]
    tail = json.loads(json.dumps(common_tail))
    for m in tail:
        m["session_id"] = "sM30A"; m["contract_id"] = "cM30A"
    tail[1]["payload"]["manifest_ref"] = {k: pin_v1[k] for k in ["manifest_id", "issuer_id", "issuer_scoped_id", "version", "content_hash"]}
    a.extend(tail)
    add_hashes(a)
    req_hash = a[2]["message_hash"]
    a[3]["payload"]["target_request_hash"] = req_hash
    a[4]["payload"]["target_request_hash"] = req_hash
    add_hashes(a)
    write("M30-01_valid_pinned_baseline_pass.jsonl", a)

    # B: rug pull fail (hash changed without amend)
    b = [base_contract("sM30B", "cM30B", "sha256:set_v1", [pin_v1], [manifest_v1])]
    tail = json.loads(json.dumps(common_tail))
    for m in tail:
        m["session_id"] = "sM30B"; m["contract_id"] = "cM30B"
    mr = {k: pin_v1[k] for k in ["manifest_id", "issuer_id", "issuer_scoped_id", "version", "content_hash"]}
    mr["content_hash"] = "sha256:weather_v1_tampered"
    tail[1]["payload"]["manifest_ref"] = mr
    b.extend(tail)
    add_hashes(b); req_hash = b[2]["message_hash"]
    b[3]["payload"]["target_request_hash"] = req_hash; b[4]["payload"]["target_request_hash"] = req_hash
    add_hashes(b)
    write("M30-02_rug_pull_expected_fail.jsonl", b)

    # C: shadowing fail (same tool id, wrong issuer)
    c = [base_contract("sM30C", "cM30C", "sha256:set_v1", [pin_v1], [manifest_v1])]
    tail = json.loads(json.dumps(common_tail))
    for m in tail:
        m["session_id"] = "sM30C"; m["contract_id"] = "cM30C"
    tail[1]["payload"]["manifest_ref"] = {
        "manifest_id": "tool.weather",
        "issuer_id": "issuer:evil-shadow",
        "issuer_scoped_id": "issuer:evil-shadow#tool.weather",
        "version": "1.0.0",
        "content_hash": "sha256:weather_v1_content",
    }
    c.extend(tail)
    add_hashes(c); req_hash = c[2]["message_hash"]
    c[3]["payload"]["target_request_hash"] = req_hash; c[4]["payload"]["target_request_hash"] = req_hash
    add_hashes(c)
    write("M30-03_shadowing_expected_fail.jsonl", c)

    # D: upgrade via CONTEXT_AMEND pass
    d = [base_contract("sM30D", "cM30D", "sha256:set_v1", [pin_v1], [manifest_v1])]
    d.append({
        "session_id": "sM30D", "message_id": "m2", "timestamp": "2026-03-09T00:00:03Z", "sender": "agent:seller", "message_type": "CONTRACT_ACCEPT", "contract_id": "cM30D", "contract_ref": {"branch_id": "main", "base_version": "v1", "head_version": "v1"}, "payload": {"accepted": True}
    })
    d.append({
        "session_id": "sM30D", "message_id": "m3", "timestamp": "2026-03-09T00:00:06Z", "sender": "agent:buyer", "message_type": "CONTEXT_AMEND", "contract_id": "cM30D", "contract_ref": {"branch_id": "main", "base_version": "v1", "head_version": "v2"},
        "payload": {"amend_type": "artifact_pinning_update", "ext": {"artifact_pinning": {"manifest_set_hash": "sha256:set_v2", "pinned_artifacts": [{"artifact_kind": "tool", "manifest_id": "tool.weather", "issuer_id": "issuer:trusted-tools", "issuer_scoped_id": "issuer:trusted-tools#tool.weather", "version": "2.0.0", "content_hash": "sha256:weather_v2_content"}], "manifests": [manifest_v2]}}}
    })
    d.append({
        "session_id": "sM30D", "message_id": "m4", "timestamp": "2026-03-09T00:00:09Z", "sender": "agent:seller", "message_type": "TOOL_CALL_REQUEST", "contract_id": "cM30D", "contract_ref": {"branch_id": "main", "base_version": "v1", "head_version": "v2"},
        "payload": {"tool_id": "tool.weather", "operation": "get_forecast", "args_hash": "sha256:req", "manifest_ref": {"manifest_id": "tool.weather", "issuer_id": "issuer:trusted-tools", "issuer_scoped_id": "issuer:trusted-tools#tool.weather", "version": "2.0.0", "content_hash": "sha256:weather_v2_content"}}
    })
    add_hashes(d)
    req_hash = d[3]["message_hash"]
    d.append({"session_id": "sM30D", "message_id": "m5", "timestamp": "2026-03-09T00:00:12Z", "sender": "mediator:M", "message_type": "TOOL_CALL_VERDICT", "contract_id": "cM30D", "contract_ref": {"branch_id": "main", "base_version": "v1", "head_version": "v2"}, "payload": {"decision": "ALLOW", "target_request_hash": req_hash}})
    add_hashes(d)
    d.append({"session_id": "sM30D", "message_id": "m6", "timestamp": "2026-03-09T00:00:15Z", "sender": "tool:weather", "message_type": "TOOL_CALL_RESULT", "contract_id": "cM30D", "contract_ref": {"branch_id": "main", "base_version": "v1", "head_version": "v2"}, "payload": {"target_request_hash": req_hash, "outcome": "SUCCESS", "result_hash": "sha256:ok_v2", "verdict_ref": "m5"}})
    add_hashes(d)
    add_hashes(d)
    write("M30-04_valid_upgrade_via_context_amend_pass.jsonl", d)

    print("Generated M30 fixtures")


if __name__ == "__main__":
    main()
