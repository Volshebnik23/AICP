#!/usr/bin/env python3
from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "reference/python"))
from aicp_ref.hashing import message_hash_from_body  # noqa: E402

OUT_DIR = ROOT / "fixtures/extensions/publications"


def finalize(rows: list[dict]) -> list[dict]:
    prev = None
    out = []
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


def pb01() -> list[dict]:
    rows = [
        {"session_id":"spb-01","message_id":"m1","timestamp":"2026-03-24T11:00:00Z","sender":"agent:brand","message_type":"CONTRACT_PROPOSE","contract_id":"c-pb-01","payload":{"contract":{"contract_id":"c-pb-01","goal":"must-reach publication","ext":{"publications":{"must_reach":True}}}}},
        {"session_id":"spb-01","message_id":"m2","timestamp":"2026-03-24T11:00:01Z","sender":"agent:subscriber","message_type":"SUBSCRIBE","contract_id":"c-pb-01","payload":{"subscription_id":"sub-pb-01","channel_id":"org/acme/security","delivery_mode":"critical-only","filters":{"severity":["critical"]}}},
        {"session_id":"spb-01","message_id":"m3","timestamp":"2026-03-24T11:00:02Z","sender":"agent:brand","message_type":"PUBLICATION_PUBLISH","contract_id":"c-pb-01","payload":{"publication_id":"pub-01","version_id":"v1","content_hash":"sha256:pub01v1","ttl_seconds":900,"policy_class":"security-critical","delivery_proof_ref":"proof:deliv:v1","provenance_graph_id":"g-pub-01"}},
        {"session_id":"spb-01","message_id":"m4","timestamp":"2026-03-24T11:00:03Z","sender":"agent:brand","message_type":"PUBLICATION_UPDATE","contract_id":"c-pb-01","payload":{"publication_id":"pub-01","version_id":"v2","prior_version_id":"v1","content_hash":"sha256:pub01v2","ttl_seconds":900,"delivery_proof_ref":"proof:deliv:v2"}},
        {"session_id":"spb-01","message_id":"m5","timestamp":"2026-03-24T11:00:04Z","sender":"agent:brand","message_type":"PUBLICATION_RETRACT","contract_id":"c-pb-01","payload":{"publication_id":"pub-01","version_id":"v3","prior_version_id":"v2","content_hash":"sha256:pub01v2","ttl_seconds":0,"reason_code":"SERVICE_DEGRADED","delivery_proof_ref":"proof:deliv:v3"}},
    ]
    base = finalize(rows)
    rows.append({"session_id":"spb-01","message_id":"m6","timestamp":"2026-03-24T11:00:05Z","sender":"agent:meter","message_type":"OBS_SIGNAL","contract_id":"c-pb-01","payload":{"trace":{"trace_id":"trace-pb-01","span_id":"span-pb-01","correlation_ref":{"message_hash":base[2]["message_hash"]}}}})
    return finalize(rows)


def pb02() -> list[dict]:
    return finalize([
        {"session_id":"spb-02","message_id":"m1","timestamp":"2026-03-24T11:10:00Z","sender":"agent:brand","message_type":"PUBLICATION_UPDATE","contract_id":"c-pb-02","payload":{"publication_id":"pub-missing","version_id":"v2","prior_version_id":"v1","content_hash":"sha256:missing","ttl_seconds":60}}
    ])


def pb03() -> list[dict]:
    return finalize([
        {"session_id":"spb-03","message_id":"m1","timestamp":"2026-03-24T11:20:00Z","sender":"agent:brand","message_type":"PUBLICATION_PUBLISH","contract_id":"c-pb-03","payload":{"publication_id":"pub-03","version_id":"v1","content_hash":"sha256:pub03v1","ttl_seconds":60}},
        {"session_id":"spb-03","message_id":"m2","timestamp":"2026-03-24T11:20:01Z","sender":"agent:brand","message_type":"PUBLICATION_UPDATE","contract_id":"c-pb-03","payload":{"publication_id":"pub-03","version_id":"v1","prior_version_id":"v1","content_hash":"sha256:pub03v1b","ttl_seconds":60}}
    ])


def pb04() -> list[dict]:
    return finalize([
        {"session_id":"spb-04","message_id":"m1","timestamp":"2026-03-24T11:30:00Z","sender":"agent:brand","message_type":"PUBLICATION_PUBLISH","contract_id":"c-pb-04","payload":{"publication_id":"pub-04","version_id":"v1","content_hash":"sha256:pub04v1","ttl_seconds":60}},
        {"session_id":"spb-04","message_id":"m2","timestamp":"2026-03-24T11:30:01Z","sender":"agent:brand","message_type":"PUBLICATION_RETRACT","contract_id":"c-pb-04","payload":{"publication_id":"pub-04","version_id":"v2","prior_version_id":"v1","content_hash":"sha256:pub04v1","ttl_seconds":0,"reason_code":"NOT_A_REAL_REASON"}}
    ])


def pb05() -> list[dict]:
    return finalize([
        {"session_id":"spb-05","message_id":"m1","timestamp":"2026-03-24T11:40:00Z","sender":"agent:brand","message_type":"CONTRACT_PROPOSE","contract_id":"c-pb-05","payload":{"contract":{"contract_id":"c-pb-05","goal":"must reach","ext":{"publications":{"must_reach":True}}}}},
        {"session_id":"spb-05","message_id":"m2","timestamp":"2026-03-24T11:40:01Z","sender":"agent:brand","message_type":"PUBLICATION_PUBLISH","contract_id":"c-pb-05","payload":{"publication_id":"pub-05","version_id":"v1","content_hash":"sha256:pub05v1","ttl_seconds":120,"policy_class":"security-critical"}}
    ])


def main() -> int:
    fixtures = {
        "PB-01_publish_update_retract_with_policy_pass.jsonl": pb01(),
        "PB-02_update_without_publish_expected_fail.jsonl": pb02(),
        "PB-03_update_without_version_progression_expected_fail.jsonl": pb03(),
        "PB-04_retract_with_unknown_reason_expected_fail.jsonl": pb04(),
        "PB-05_must_reach_without_delivery_proof_expected_fail.jsonl": pb05(),
    }
    for name, rows in fixtures.items():
        path = OUT_DIR / name
        write_jsonl(path, rows)
        print(f"wrote {path.relative_to(ROOT)} ({len(rows)} records)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
