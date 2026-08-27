"""Normalize Pairwise 1.2 role routing, causality, and opaque runtime values."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _contains(value: Any, needle: str) -> bool:
    if isinstance(value, dict):
        return any(_contains(item, needle) for item in value.values())
    if isinstance(value, list):
        return any(_contains(item, needle) for item in value)
    return value == needle


def normalized_run(run: dict[str, Any]) -> dict[str, Any]:
    directions: list[dict[str, Any]] = []
    for direction in run.get("directions", []):
        message_items = direction.get("messages", [])
        hash_positions = {
            item.get("message", {}).get("message_hash"): index + 1
            for index, item in enumerate(message_items)
        }
        messages: list[dict[str, Any]] = []
        for item in message_items:
            message = item.get("message", {})
            payload = message.get("payload", {})
            if message.get("message_type") == "CONTRACT_PROPOSE":
                payload_shape = {
                    "roles": payload.get("contract", {}).get("roles"),
                    "goal_is_challenge": payload.get("contract", {}).get("goal") == direction.get("challenge"),
                    "has_contract_hash": isinstance(payload.get("contract_hash"), str),
                }
            elif message.get("message_type") == "CONTRACT_ACCEPT":
                payload_shape = {"accepted": payload.get("accepted")}
            else:
                payload_shape = {
                    "action_type": payload.get("action_type"),
                    "has_result_hash": isinstance(payload.get("result_hash"), str),
                }
            messages.append(
                {
                    "sequence": item.get("sequence"),
                    "sender_side": item.get("sender_side"),
                    "constructed_by": item.get("constructed_by"),
                    "consumed_by": item.get("consumed_by"),
                    "message_type": message.get("message_type"),
                    "previous_sequence": hash_positions.get(message.get("prev_msg_hash")),
                    "payload": payload_shape,
                    "send_exchange_sequence": item.get("send_exchange_sequence"),
                    "consume_exchange_sequence": item.get("consume_exchange_sequence"),
                    "first_seen_before_count": len(item.get("client_visible_hashes_before", [])),
                    "first_seen_after_count": len(item.get("client_visible_hashes_after", [])),
                }
            )
        exchanges: list[dict[str, Any]] = []
        for exchange in direction.get("exchanges", []):
            request = exchange.get("request", {})
            response = exchange.get("response", {})
            exchanges.append(
                {
                    "sequence": exchange.get("sequence"),
                    "phase": exchange.get("phase"),
                    "operation": exchange.get("operation"),
                    "originating_client_side": exchange.get("originating_client_side"),
                    "destination_server_side": exchange.get("destination_server_side"),
                    "request_origin": exchange.get("request_origin"),
                    "response_origin": exchange.get("response_origin"),
                    "request_tool": request.get("params", {}).get("name"),
                    "correlated": request.get("id") == response.get("id"),
                    "client_process_role": f"{exchange.get('originating_client_side')}:client",
                    "server_process_role": f"{exchange.get('destination_server_side')}:server",
                }
            )
        events: list[dict[str, Any]] = []
        challenge = direction.get("challenge")
        message_hashes = [item.get("message", {}).get("message_hash") for item in message_items]
        for event in direction.get("client_events", []):
            request = event.get("request", {})
            input_value = request.get("input", {}) if isinstance(request, dict) else {}
            response_result = event.get("response", {}).get("result", {})
            events.append(
                {
                    "sequence": event.get("sequence"),
                    "client_side": event.get("client_side"),
                    "operation": request.get("operation"),
                    "phase": input_value.get("phase") or response_result.get("phase"),
                    "event": response_result.get("event"),
                    "input_contains_challenge": isinstance(challenge, str) and _contains(input_value, challenge),
                    "input_contains_message_hash_positions": [
                        index + 1
                        for index, digest in enumerate(message_hashes)
                        if isinstance(digest, str) and _contains(input_value, digest)
                    ],
                }
            )
        directions.append(
            {
                "direction": direction.get("direction"),
                "producer_side": direction.get("producer_side"),
                "consumer_side": direction.get("consumer_side"),
                "messages": messages,
                "exchanges": exchanges,
                "client_events": events,
                "final_consumer_poll": any(item.get("phase") == "poll_attestation" for item in exchanges),
            }
        )
    return {"directions": directions}


def semantic_digest(run: dict[str, Any]) -> str:
    return "sha256:" + hashlib.sha256(_canonical(normalized_run(run))).hexdigest()
