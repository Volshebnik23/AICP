from __future__ import annotations

from typing import Any

from aicp_ref_v02.contract_agreement import (
    AGREEMENT_STATE,
    CHECK_IDS,
    CONTRACT_SCHEMA,
    AgreementState,
    reduce_transcript,
)


def _add_failure(
    failures: list[dict[str, Any]],
    test_id: str,
    message: str,
    file: str,
    line: int | None = None,
) -> None:
    failures.append(
        {"test_id": test_id, "message": message, "file": file, "line": line}
    )


def run_contract_agreement_checks(
    *,
    rows: list[tuple[int, dict[str, Any]]],
    transcript: dict[str, Any],
    enabled_checks: set[str],
    rel_file: str,
    failures: list[dict[str, Any]],
    contract_validator: Any | None,
) -> AgreementState:
    if CONTRACT_SCHEMA in enabled_checks:
        for line_no, message in rows:
            if message.get("message_type") != "CONTRACT_PROPOSE":
                continue
            contract = (message.get("payload") or {}).get("contract")
            if not isinstance(contract, dict):
                _add_failure(
                    failures,
                    CONTRACT_SCHEMA,
                    "payload.contract must be an object",
                    rel_file,
                    line_no,
                )
                continue
            if contract_validator is not None:
                for error in sorted(
                    contract_validator.iter_errors(contract),
                    key=lambda issue: list(issue.path),
                ):
                    _add_failure(
                        failures,
                        CONTRACT_SCHEMA,
                        error.message,
                        rel_file,
                        line_no,
                    )

    messages = [message for _, message in rows]
    state = reduce_transcript(messages)
    for issue in state.issues:
        if issue.code not in enabled_checks:
            continue
        line_no = rows[issue.index][0] if issue.index < len(rows) else None
        _add_failure(
            failures,
            issue.code,
            issue.message,
            rel_file,
            line_no,
        )

    if AGREEMENT_STATE in enabled_checks:
        expected_state = transcript.get("expected_agreement_state")
        if isinstance(expected_state, str) and state.state != expected_state:
            _add_failure(
                failures,
                AGREEMENT_STATE,
                f"final agreement state mismatch (expected {expected_state}, got {state.state})",
                rel_file,
                None,
            )
        if "expected_active_head" in transcript:
            expected_head = transcript.get("expected_active_head")
            if state.active_head != expected_head:
                _add_failure(
                    failures,
                    AGREEMENT_STATE,
                    "final active head does not match the exact expected head",
                    rel_file,
                    None,
                )

    return state


__all__ = ["CHECK_IDS", "run_contract_agreement_checks"]
