#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


EVIDENCE_DIR = Path(__file__).resolve().parent
if str(EVIDENCE_DIR) not in sys.path:
    sys.path.insert(0, str(EVIDENCE_DIR))

from reference_adapter import handle_request  # noqa: E402
from aicp_ref.hashing import object_hash  # noqa: E402


EXPECTED_MARK = "AICP-Evidence-SESSION-STATE-PROJECTION-v1"
MODES = [
    "external_good",
    "echo_context",
    "copy_last_response_projection",
    "copy_last_response_hash",
    "ignore_transcript_and_return_reviewed_fixture",
    "return_projection_with_unresolved_as_of",
    "return_projection_with_wrong_evidence_message",
    "return_projection_with_wrong_canonical_order",
    "return_projection_from_another_session",
    "return_projection_from_another_contract",
    "nondeterministic_derived_reference",
    "target_not_declared",
    "wrong_projection",
    "wrong_projection_hash",
    "missing_projection_field",
    "nondeterministic_second_projection",
    "accepts_every_consumer",
    "rejects_valid_consumer",
    "consumer_missing_field",
    "skipped_without_degraded",
    "unexpected_degradation",
    "missing_case",
    "duplicate_case",
    "wrong_target_id",
    "wrong_target_version",
    "wrong_tck_release",
    "historical_release",
    "wrong_current_release",
    "wrong_registry_schema_digest",
    "wrong_target_registry_digest",
    "wrong_target_catalog_digest",
    "wrong_runner_digest",
    "wrong_suite_digest",
    "wrong_input_digest",
    "forged_compatibility_mark",
    "reference_subject_with_external_mark",
]

OLD_REVIEWED_PROJECTION = {
    "projection_version": "aicp.session_state_projection.v1",
    "session_id": "sSP1",
    "contract_id": "cSP1",
    "as_of_message_hash": "sha256:IkiKDdCVIdkgtZx17iR7_hSKAYX7xlMPIvtRqfYlG78",
    "session_status": "OPEN",
    "active_contract_ref": {
        "branch_id": "main",
        "base_version": "v1",
        "head_version": "v2",
    },
    "selected_aicp_profile": {
        "profile_id": "AICP-BASE",
        "profile_version": "0.1",
    },
    "active_extensions": ["EXT-OBJECT-RESYNC"],
    "participant_refs": ["agent:A", "agent:B"],
    "evidence_refs": [
        "msghash:sha256:vj2Aoj6yNJDvRVSO9xcfkGgFe1Rh_svRMyaC42S8310"
    ],
}
OLD_REVIEWED_HASH = "sha256:kPqZ9musmznNE6H2fNQrMr4ZSdlyzvh6HW2cnk3cAoY"

if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8", errors="strict")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="strict")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=MODES)
    args = parser.parse_args()
    project_count = 0
    validate_count = 0
    first_validate_request_id: str | None = None
    for raw in sys.stdin:
        if not raw.strip():
            continue
        request = json.loads(raw)
        kind = (
            "reference_corpus"
            if args.mode == "reference_subject_with_external_mark"
            else "external_implementation"
        )
        response = handle_request(
            request,
            implementation_kind=kind,
            implementation_id="fictional-projection-v1-test-adapter",
            implementation_version="1.0.0-test",
            implementation_digest="sha256:" + "1" * 64,
        )
        operation = request.get("operation")
        result = response.get("result")
        if not isinstance(result, dict):
            result = {}
            response["result"] = result

        if operation == "describe":
            if args.mode == "target_not_declared":
                result["supported_aicp_capabilities"] = []
            elif args.mode == "wrong_target_id":
                result["supported_aicp_capabilities"] = [
                    {
                        "capability_id": "aicp.other_capability",
                        "capability_version": "v1",
                    }
                ]
            elif args.mode == "wrong_target_version":
                result["supported_aicp_capabilities"] = [
                    {
                        "capability_id": "aicp.session_state_projection",
                        "capability_version": "v2",
                    }
                ]
            elif args.mode == "wrong_tck_release":
                result["claimed_tck_release"] = "AICP-EVIDENCE-TCK-0.0.0"
            elif args.mode == "historical_release":
                result["claimed_tck_release"] = "AICP-EVIDENCE-TCK-1.0.0"
            elif args.mode == "wrong_current_release":
                result["claimed_tck_release"] = "AICP-EVIDENCE-TCK-1.0.1"
            elif args.mode == "wrong_registry_schema_digest":
                result["claimed_registry_schema_digest"] = "sha256:" + "5" * 64
            elif args.mode == "wrong_target_registry_digest":
                result["claimed_target_registry_digest"] = "sha256:" + "6" * 64
            elif args.mode == "wrong_target_catalog_digest":
                result["claimed_target_catalog_digest"] = "sha256:" + "7" * 64
            elif args.mode == "wrong_runner_digest":
                result["claimed_runner_digest"] = "sha256:" + "2" * 64
            elif args.mode == "wrong_suite_digest":
                result["claimed_suite_digest"] = "sha256:" + "3" * 64
            elif args.mode == "wrong_input_digest":
                result["claimed_input_digest"] = "sha256:" + "4" * 64
            elif args.mode in {
                "forged_compatibility_mark",
                "reference_subject_with_external_mark",
            }:
                result["claimed_compatibility_marks"] = [EXPECTED_MARK]
        elif operation == "project_session_state":
            project_count += 1
            projection = result.get("projection")
            if not isinstance(projection, dict):
                projection = {}
                result["projection"] = projection
            if args.mode == "echo_context":
                scenario = request.get("input", {}).get("scenario")
                result["projection"] = scenario if isinstance(scenario, dict) else {}
                result["session_state_hash"] = object_hash(
                    "session_state_projection",
                    result["projection"],
                )
            elif args.mode in {
                "copy_last_response_projection",
                "copy_last_response_hash",
            }:
                copied_projection = None
                copied_hash = None
                transcript = request.get("input", {}).get("transcript") or []
                for message in reversed(transcript):
                    payload = message.get("payload") if isinstance(message, dict) else None
                    if isinstance(payload, dict) and isinstance(
                        payload.get("session_state"), dict
                    ):
                        copied_projection = payload["session_state"]
                        copied_hash = payload.get("session_state_hash")
                        break
                if args.mode == "copy_last_response_projection":
                    result["projection"] = copied_projection or {}
                else:
                    result["session_state_hash"] = copied_hash or (
                        "sha256:" + "A" * 43
                    )
            elif args.mode == "ignore_transcript_and_return_reviewed_fixture":
                result["projection"] = dict(OLD_REVIEWED_PROJECTION)
                result["session_state_hash"] = OLD_REVIEWED_HASH
            elif args.mode == "wrong_projection":
                result["projection"]["session_id"] = "wrong-session"
            elif args.mode == "wrong_projection_hash":
                result["session_state_hash"] = (
                    "sha256:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
                )
            elif args.mode == "missing_projection_field":
                result["projection"].pop("active_contract_ref", None)
            elif (
                args.mode == "nondeterministic_second_projection"
                and project_count == 2
            ):
                result["projection"]["session_status"] = "UNKNOWN"
            elif args.mode == "return_projection_with_unresolved_as_of":
                projection["as_of_message_hash"] = "sha256:" + "A" * 43
                result["session_state_hash"] = object_hash(
                    "session_state_projection", projection
                )
            elif args.mode == "return_projection_with_wrong_evidence_message":
                projection["evidence_refs"] = ["msghash:sha256:" + "B" * 43]
                result["session_state_hash"] = object_hash(
                    "session_state_projection", projection
                )
            elif args.mode == "return_projection_with_wrong_canonical_order":
                projection["participant_refs"] = list(
                    reversed(projection.get("participant_refs", []))
                )
                result["session_state_hash"] = object_hash(
                    "session_state_projection", projection
                )
            elif args.mode == "return_projection_from_another_session":
                projection["session_id"] = "another-session"
                result["session_state_hash"] = object_hash(
                    "session_state_projection", projection
                )
            elif args.mode == "return_projection_from_another_contract":
                projection["contract_id"] = "another-contract"
                result["session_state_hash"] = object_hash(
                    "session_state_projection", projection
                )
            elif (
                args.mode == "nondeterministic_derived_reference"
                and project_count == 2
            ):
                projection["evidence_refs"] = ["msghash:sha256:" + "C" * 43]
                result["session_state_hash"] = object_hash(
                    "session_state_projection", projection
                )
        elif operation == "validate_transcript":
            validate_count += 1
            if first_validate_request_id is None:
                first_validate_request_id = str(request.get("request_id"))
            if args.mode == "missing_case" and validate_count == 2:
                continue
            if args.mode == "duplicate_case" and validate_count == 2:
                response["request_id"] = first_validate_request_id
            elif args.mode == "accepts_every_consumer":
                result.update({"accepted": True, "errors": []})
            elif (
                args.mode == "rejects_valid_consumer"
                and result.get("accepted") is True
            ):
                result.update(
                    {
                        "accepted": False,
                        "errors": [
                            {
                                "code": "FAKE_REJECTION",
                                "message": "valid consumer rejected",
                            }
                        ],
                    }
                )
            elif args.mode == "consumer_missing_field":
                result.pop("skipped_checks", None)
            elif args.mode == "skipped_without_degraded":
                result.update(
                    {
                        "degraded": False,
                        "degraded_reasons": [],
                        "skipped_checks": ["MANDATORY-CHECK"],
                    }
                )
            elif args.mode == "unexpected_degradation":
                result.update(
                    {
                        "degraded": True,
                        "degraded_reasons": ["unexpected adapter degradation"],
                        "skipped_checks": ["MANDATORY-CHECK"],
                    }
                )

        sys.stdout.write(
            json.dumps(
                response,
                separators=(",", ":"),
                ensure_ascii=False,
            )
            + "\n"
        )
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
