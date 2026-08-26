from __future__ import annotations

from typing import Any


def _add_failure(failures: list[dict[str, Any]], test_id: str, message: str, file: str, line: int | None = None) -> None:
    failures.append({"test_id": test_id, "message": message, "file": file, "line": line})


def run_core_transcript_checks(
    *,
    rows: list[tuple[int, dict[str, Any]]],
    transcript: dict[str, Any],
    enabled_checks: set[str],
    registered_message_types: set[str],
    rel_file: str,
    failures: list[dict[str, Any]],
) -> None:
    if "CT-MESSAGE-TYPE-REGISTRY-01" in enabled_checks:
        for line_no, msg in rows:
            mtype = msg.get("message_type")
            if mtype not in registered_message_types:
                _add_failure(failures, "CT-MESSAGE-TYPE-REGISTRY-01", f"unregistered message_type '{mtype}'", rel_file, line_no)

    session_id = rows[0][1].get("session_id")
    seen_ids: set[str] = set()
    for line_no, msg in rows:
        if msg.get("session_id") != session_id:
            _add_failure(failures, "CT-INVARIANTS-01", "session_id changed within transcript", rel_file, line_no)

        mid = msg.get("message_id")
        if mid in seen_ids:
            _add_failure(failures, "CT-INVARIANTS-01", f"duplicate message_id '{mid}'", rel_file, line_no)
        else:
            seen_ids.add(mid)

        if "CT-CONTRACT-ID-01" in enabled_checks:
            contract_id = msg.get("contract_id")
            if not isinstance(contract_id, str) or not contract_id:
                _add_failure(
                    failures,
                    "CT-CONTRACT-ID-01",
                    "contract_id must be a non-empty string",
                    rel_file,
                    line_no,
                )

    if "CT-PREV-MSG-REQUIRED-01" in enabled_checks:
        for idx, (line_no, msg) in enumerate(rows):
            if idx == 0:
                continue
            prev_msg_hash = msg.get("prev_msg_hash")
            if not isinstance(prev_msg_hash, str) or not prev_msg_hash:
                _add_failure(
                    failures,
                    "CT-PREV-MSG-REQUIRED-01",
                    "prev_msg_hash is required and must be a non-empty string for non-first messages",
                    rel_file,
                    line_no,
                )

    prev_hash = None
    for line_no, msg in rows:
        if prev_hash is not None and "prev_msg_hash" in msg and msg.get("prev_msg_hash") != prev_hash:
            _add_failure(
                failures,
                "CT-HASH-CHAIN-01",
                f"prev_msg_hash mismatch (expected {prev_hash}, got {msg.get('prev_msg_hash')})",
                rel_file,
                line_no,
            )
        prev_hash = msg.get("message_hash")

    actual_types = [m.get("message_type") for _, m in rows]
    expected_types = transcript.get("expected_message_types", [])
    if actual_types != expected_types:
        _add_failure(
            failures,
            "CT-SEQUENCE-01",
            f"message_type sequence mismatch (expected {expected_types}, got {actual_types})",
            rel_file,
            None,
        )

    for line_no, msg in rows:
        mhash = msg.get("message_hash")
        for sig in msg.get("signatures", []) or []:
            obj_hash = sig.get("object_hash")
            if obj_hash is not None and obj_hash != mhash:
                _add_failure(
                    failures,
                    "CT-SIGNATURE-HASH-01",
                    f"signatures.object_hash mismatch (expected {mhash}, got {obj_hash})",
                    rel_file,
                    line_no,
                )
