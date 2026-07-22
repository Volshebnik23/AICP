from __future__ import annotations

from typing import Any

from aicp_ref.session_state import validate_session_state_projection


ISSUE_TO_TEST_ID = {
    "session_mismatch": "OR-SP-SESSION-01",
    "contract_mismatch": "OR-SP-CONTRACT-01",
    "projection_hash": "OR-SP-HASH-01",
    "as_of": "OR-SP-AS-OF-01",
    "contract_ref": "OR-SP-CONTRACT-REF-01",
    "profile": "OR-SP-PROFILE-01",
    "extension": "OR-SP-EXTENSION-01",
    "active_head": "OR-SP-ACTIVE-HEAD-01",
    "reference": "OR-SP-REFERENCE-01",
    "contradiction": "OR-SP-STATE-01",
}


def run_state_projection_checks(
    *,
    rows: list[tuple[int, dict[str, Any]]],
    enabled_checks: set[str],
    registered_profiles: set[tuple[str, str]],
    registered_extensions: set[str],
    rel_file: str,
    failures: list[dict[str, Any]],
) -> None:
    transcript = [message for _, message in rows]
    for index, (line_no, message) in enumerate(rows):
        for issue in validate_session_state_projection(
            message,
            transcript,
            index,
            registered_profiles=registered_profiles,
            registered_extensions=registered_extensions,
        ):
            test_id = ISSUE_TO_TEST_ID[issue["code"]]
            if test_id in enabled_checks:
                failures.append(
                    {
                        "test_id": test_id,
                        "message": issue["message"],
                        "file": rel_file,
                        "line": line_no,
                    }
                )
