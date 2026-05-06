from __future__ import annotations

import re
from typing import Any


def _add_failure(failures: list[dict[str, Any]], test_id: str, message: str, file: str, line: int | None = None) -> None:
    failures.append({"test_id": test_id, "message": message, "file": file, "line": line})


def run_enforcement_transcript_checks(
    *,
    rows: list[tuple[int, dict[str, Any]]],
    enabled_checks: set[str],
    enforcement_sanction_codes: set[str],
    rel_file: str,
    failures: list[dict[str, Any]],
) -> None:
    if "ENF-SANCTION-CODES-01" in enabled_checks:
        namespaced_dash = re.compile(r"^x-[a-z0-9]+[a-z0-9._-]*$")
        namespaced_colon = re.compile(r"^[a-z0-9]+:[a-z0-9][a-z0-9._-]*$")
        for line_no, msg in rows:
            if msg.get("message_type") != "ENFORCEMENT_VERDICT":
                continue
            sanctions = (msg.get("payload") or {}).get("sanctions", []) or []
            for sanction in sanctions:
                code = sanction.get("code") if isinstance(sanction, dict) else None
                if not isinstance(code, str):
                    _add_failure(failures, "ENF-SANCTION-CODES-01", "sanctions[].code must be a string", rel_file, line_no)
                    continue
                if code in enforcement_sanction_codes:
                    continue
                if namespaced_dash.match(code) or namespaced_colon.match(code):
                    continue
                _add_failure(failures, "ENF-SANCTION-CODES-01", f"unknown sanction code '{code}'", rel_file, line_no)

    if "ENF-VERDICT-STORM-01" in enabled_checks:
        verdict_counts: dict[str, int] = {}
        for line_no, msg in rows:
            if msg.get("message_type") != "ENFORCEMENT_VERDICT":
                continue
            payload = msg.get("payload") or {}
            target_hash = payload.get("target_message_hash")
            if not isinstance(target_hash, str):
                continue
            verdict_counts[target_hash] = verdict_counts.get(target_hash, 0) + 1
            if verdict_counts[target_hash] > 1:
                _add_failure(
                    failures,
                    "ENF-VERDICT-STORM-01",
                    f"multiple ENFORCEMENT_VERDICT messages reference target_message_hash '{target_hash}'",
                    rel_file,
                    line_no,
                )
