#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from aicp_core import build_core_message


def generate_messages() -> list[dict]:
    contract_id = "c-quickstart"
    contract_ref = {"branch_id": "main", "base_version": "v1", "head_version": "v1"}

    m1 = build_core_message(
        session_id="s-quickstart",
        message_id="m0001",
        timestamp="t0001",
        sender="agent:A",
        message_type="CONTRACT_PROPOSE",
        contract_id=contract_id,
        contract_ref=contract_ref,
        payload={
            "contract": {
                "contract_id": contract_id,
                "goal": "minimal_quickstart",
                "roles": ["initiator", "responder"],
                "policies": [
                    {
                        "policy_id": "pol-001",
                        "category": "user_consent",
                        "parameters": {},
                        "status": "active",
                    }
                ],
            }
        },
    )

    m2 = build_core_message(
        session_id="s-quickstart",
        message_id="m0002",
        timestamp="t0002",
        sender="agent:B",
        message_type="CONTRACT_ACCEPT",
        contract_id=contract_id,
        contract_ref=contract_ref,
        payload={"accepted": True},
        prev_msg_hash=m1["message_hash"],
    )

    m3 = build_core_message(
        session_id="s-quickstart",
        message_id="m0003",
        timestamp="t0003",
        sender="agent:A",
        message_type="CONTEXT_AMEND",
        contract_id=contract_id,
        contract_ref=contract_ref,
        payload={"amendment": {"note": "minimal_update"}},
        prev_msg_hash=m2["message_hash"],
    )

    return [m1, m2, m3]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="out/minimal_core.jsonl")
    args = parser.parse_args()

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(msg, separators=(",", ":"), ensure_ascii=False) for msg in generate_messages()]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {len(lines)} records to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
