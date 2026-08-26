"""Evaluator-owned semantic normalization for repeated pairwise runs."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def normalized_run(run: dict[str, Any]) -> dict[str, Any]:
    directions: list[dict[str, Any]] = []
    for direction in run.get("directions", []):
        messages = direction.get("messages", [])
        by_hash = {
            item.get("message", {}).get("message_hash"): index
            for index, item in enumerate(messages)
            if isinstance(item, dict) and isinstance(item.get("message"), dict)
        }
        normalized_messages: list[dict[str, Any]] = []
        for item in messages:
            message = item.get("message", {})
            payload = message.get("payload", {})
            shape: dict[str, Any]
            if message.get("message_type") == "CONTRACT_PROPOSE":
                contract = payload.get("contract", {})
                shape = {
                    "contract_roles": contract.get("roles"),
                    "has_contract_hash": isinstance(payload.get("contract_hash"), str),
                }
            elif message.get("message_type") == "CONTRACT_ACCEPT":
                shape = {"accepted": payload.get("accepted")}
            else:
                shape = {
                    "action_type": payload.get("action_type"),
                    "has_result_hash": isinstance(payload.get("result_hash"), str),
                }
            previous = message.get("prev_msg_hash")
            normalized_messages.append(
                {
                    "sequence": item.get("sequence"),
                    "constructed_by": item.get("constructed_by"),
                    "consumed_by": item.get("consumed_by"),
                    "message_type": message.get("message_type"),
                    "sender_side": item.get("sender_side"),
                    "previous_sequence": by_hash.get(previous) if previous is not None else None,
                    "payload_semantics": shape,
                    "mcp_tools": [
                        item.get("mcp_send", {}).get("request", {}).get("params", {}).get("name"),
                        item.get("mcp_poll", {}).get("request", {}).get("params", {}).get("name"),
                    ],
                }
            )
        directions.append(
            {
                "direction": direction.get("direction"),
                "producer_side": direction.get("producer_side"),
                "consumer_side": direction.get("consumer_side"),
                "messages": normalized_messages,
            }
        )
    return {"directions": directions}


def semantic_digest(run: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(_canonical(normalized_run(run))).hexdigest()
