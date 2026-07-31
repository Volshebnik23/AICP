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


EXPECTED_MARK = "AICP-Evidence-SESSION-STATE-PROJECTION-v1"
MODES = [
    "external_good",
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
    "wrong_runner_digest",
    "wrong_suite_digest",
    "wrong_input_digest",
    "forged_compatibility_mark",
    "reference_subject_with_external_mark",
]

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
            if args.mode == "wrong_projection":
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
