#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import hashlib
import json
from pathlib import Path
from typing import Any


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def object_hash(object_type: str, value: Any) -> str:
    preimage = b"AICP1\0" + object_type.encode() + b"\0" + canonical_bytes(value)
    digest = hashlib.sha256(preimage).digest()
    return "sha256:" + base64.urlsafe_b64encode(digest).decode().rstrip("=")


def add_hashes(messages: list[dict[str, Any]]) -> None:
    previous: str | None = None
    for message in messages:
        message.pop("prev_msg_hash", None)
        message.pop("message_hash", None)
        if previous is not None:
            message["prev_msg_hash"] = previous
        message["message_hash"] = object_hash("message", message)
        previous = message["message_hash"]


def build_transcript() -> list[dict[str, Any]]:
    contract = {
        "contract_id": "quickstart-core-v02",
        "contract_version": "v1",
        "goal": "Demonstrate exact contract agreement",
        "roles": ["initiator", "responder"],
    }
    contract_hash = object_hash("contract", contract)
    transition_ref = {
        "branch_id": "main",
        "head": {"version": "v1", "contract_hash": contract_hash},
    }
    current_ref = {
        "branch_id": "main",
        "head": {"version": "v1", "contract_hash": contract_hash},
    }
    common = {
        "session_id": "quickstart-core-v02-session",
        "contract_id": contract["contract_id"],
    }
    proposal = {
        **common,
        "message_id": "core-v02-proposal",
        "timestamp": "2026-01-01T00:00:00Z",
        "sender": "agent://initiator",
        "message_type": "CONTRACT_PROPOSE",
        "contract_ref": transition_ref,
        "payload": {"contract": contract, "contract_hash": contract_hash},
    }
    proposal["message_hash"] = object_hash("message", proposal)
    acceptance = {
        **common,
        "message_id": "core-v02-acceptance",
        "timestamp": "2026-01-01T00:00:01Z",
        "sender": "agent://responder",
        "message_type": "CONTRACT_ACCEPT",
        "contract_ref": transition_ref,
        "payload": {
            "accepted": True,
            "proposal_message_id": proposal["message_id"],
            "proposal_message_hash": proposal["message_hash"],
            "contract_hash": contract_hash,
        },
    }
    action = {
        **common,
        "message_id": "core-v02-action",
        "timestamp": "2026-01-01T00:00:02Z",
        "sender": "agent://initiator",
        "message_type": "ATTEST_ACTION",
        "contract_ref": current_ref,
        "payload": {
            "action_id": "quickstart-action",
            "action_type": "DEMO",
            "result_hash": contract_hash,
        },
    }
    messages = [proposal, acceptance, action]
    for message in messages:
        message.pop("message_hash", None)
    add_hashes(messages)
    acceptance["payload"]["proposal_message_hash"] = proposal["message_hash"]
    add_hashes(messages)
    return messages


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    output = Path(args.out)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "\n".join(
            json.dumps(message, ensure_ascii=False, sort_keys=True)
            for message in build_transcript()
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote Core v0.2 exact-agreement transcript: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
