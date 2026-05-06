from __future__ import annotations

from typing import Any, Callable


def _add_failure(failures: list[dict[str, Any]], test_id: str, message: str, file: str, line: int | None = None) -> None:
    failures.append({"test_id": test_id, "message": message, "file": file, "line": line})


def run_alert_transcript_checks(
    *,
    rows: list[tuple[int, dict[str, Any]]],
    enabled_checks: set[str],
    alert_codes_registry: dict[str, Any],
    alert_recommended_actions: set[str],
    canonicalize_json_fn: Callable[[Any], str],
    rel_file: str,
    failures: list[dict[str, Any]],
) -> None:
    if "AL-ALERT-CODES-01" in enabled_checks or "AL-ALERT-ACTIONS-01" in enabled_checks:
        for line_no, msg in rows:
            if msg.get("message_type") != "ALERT":
                continue
            payload = msg.get("payload") or {}
            if "AL-ALERT-CODES-01" in enabled_checks:
                code = payload.get("code")
                if code not in alert_codes_registry:
                    _add_failure(failures, "AL-ALERT-CODES-01", f"unknown alert code '{code}'", rel_file, line_no)
            if "AL-ALERT-ACTIONS-01" in enabled_checks:
                for action in payload.get("recommended_actions", []) or []:
                    if action not in alert_recommended_actions:
                        _add_failure(failures, "AL-ALERT-ACTIONS-01", f"unknown recommended_action '{action}'", rel_file, line_no)

    if "AL-VERBOSITY-01" in enabled_checks:
        for line_no, msg in rows:
            if msg.get("message_type") != "ALERT":
                continue
            payload = msg.get("payload") or {}
            message = payload.get("message")
            if isinstance(message, str) and len(message) > 256:
                _add_failure(failures, "AL-VERBOSITY-01", f"ALERT payload.message exceeds 256 characters (got {len(message)})", rel_file, line_no)
            if "details" in payload:
                try:
                    details_size = len(canonicalize_json_fn(payload.get("details")))
                except Exception as exc:
                    _add_failure(failures, "AL-VERBOSITY-01", f"ALERT payload.details canonicalization failed: {exc}", rel_file, line_no)
                    continue
                if details_size > 4096:
                    _add_failure(
                        failures,
                        "AL-VERBOSITY-01",
                        f"ALERT payload.details canonical JSON exceeds 4096 bytes (got {details_size})",
                        rel_file,
                        line_no,
                    )
