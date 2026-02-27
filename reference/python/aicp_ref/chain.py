from __future__ import annotations

from typing import Any


def verify_transcript_chain(messages: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    prev_hash = None
    for idx, msg in enumerate(messages, start=1):
        current_prev = msg.get("prev_msg_hash")
        if prev_hash is not None and current_prev is not None and current_prev != prev_hash:
            errors.append(
                f"line {idx}: prev_msg_hash mismatch (expected {prev_hash}, got {current_prev})"
            )
        prev_hash = msg.get("message_hash")
    return errors
