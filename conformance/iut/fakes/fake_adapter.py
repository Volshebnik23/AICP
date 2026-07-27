#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any


IUT_DIR = Path(__file__).resolve().parents[1]
if str(IUT_DIR) not in sys.path:
    sys.path.insert(0, str(IUT_DIR))

from reference_adapter import handle_request  # noqa: E402
from aicp_ref.hashing import message_hash_from_body  # noqa: E402


MODES = [
    "external_good",
    "crypto_probe_good",
    "crypto_probe_not_degraded",
    "crypto_probe_missing_reason",
    "crypto_probe_wrong_reason",
    "crypto_probe_missing_skip",
    "crypto_probe_extra_skip",
    "normal_auth_crypto_unavailable",
    "authenticated_producer_crypto_unavailable",
    "wrong_canonicalization",
    "accepts_invalid_chain",
    "accepts_invalid_signature",
    "incomplete_core",
    "incomplete_authenticated",
    "missing_mandatory_case_support",
    "skipped_without_degraded",
    "degraded_reason_without_degraded",
    "wrong_degraded_skip",
    "missing_skipped_checks_field",
    "wrong_producer_session",
    "wrong_producer_contract",
    "undeclared_producer_sender",
    "unsigned_authenticated_producer",
    "nondeterministic_producer",
    "mismatched_projection",
    "forged_metadata",
    "lies_metadata",
    "never_reads_stdin",
    "stdout_overflow",
    "stderr_overflow",
    "partial_hang",
    "early_exit",
    "timeout",
]

if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8", errors="strict")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="strict")


def _errors_contain(result: dict[str, Any], fragments: tuple[str, ...]) -> bool:
    for error in result.get("errors", []) or []:
        code = str(error.get("code", "")).lower()
        message = str(error.get("message", "")).lower()
        if any(fragment in code or fragment in message for fragment in fragments):
            return True
    return False


def _make_valid_unsigned_variant(transcript: list[dict[str, Any]]) -> None:
    """Change canonical content while preserving a valid optional-crypto hash chain."""
    previous_hash: str | None = None
    for index, message in enumerate(transcript):
        message.pop("signatures", None)
        if index == 0:
            message["timestamp"] = "2026-01-01T00:00:01Z"
            message.pop("prev_msg_hash", None)
        else:
            message["prev_msg_hash"] = previous_hash
        body = dict(message)
        body.pop("message_hash", None)
        body.pop("signatures", None)
        message["message_hash"] = message_hash_from_body(body)
        previous_hash = message["message_hash"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=MODES)
    args = parser.parse_args()

    if args.mode in {"never_reads_stdin", "timeout"}:
        time.sleep(10)
        return 0
    if args.mode == "stdout_overflow":
        sys.stdout.write("X" * 2_000_000)
        sys.stdout.flush()
        time.sleep(10)
        return 0
    if args.mode == "stderr_overflow":
        sys.stderr.write("E" * 2_000_000)
        sys.stderr.flush()
        time.sleep(10)
        return 0
    if args.mode == "early_exit":
        return 0

    describes = 0
    generation_counts: dict[str, int] = {}
    for raw in sys.stdin:
        request: dict[str, Any] = json.loads(raw)
        response = handle_request(request)
        operation = request.get("operation")
        input_obj = request.get("input") or {}
        result = response.get("result") or {}

        if operation == "describe":
            describes += 1
            result["implementation_kind"] = "external_implementation"
            result["implementation_id"] = "fictional-iut-test-double"
            result["implementation_version"] = "1.0.0-test"
            result["implementation_digest"] = "sha256:" + "1" * 64
            if args.mode in {"forged_metadata", "lies_metadata"}:
                result["implementation_digest"] = "unknown" if describes == 1 else "sha256:" + "2" * 64
        elif args.mode == "wrong_canonicalization" and operation == "canonicalize_hash":
            result["canonical_json"] = "{}"
        elif operation == "validate_transcript":
            transcript = input_obj.get("transcript") or []
            message_types = [message.get("message_type") for message in transcript if isinstance(message, dict)]
            target = input_obj.get("target_profile")
            unavailable_probe = (
                target == "AICP-AUTHENTICATED-BASE@0.1"
                and input_obj.get("runtime_options", {}).get(
                    "cryptographic_verification"
                )
                == "unavailable"
            )
            if unavailable_probe and args.mode == "crypto_probe_not_degraded":
                result.update(
                    {
                        "degraded": False,
                        "degraded_reasons": [],
                        "skipped_checks": [],
                    }
                )
            elif unavailable_probe and args.mode == "crypto_probe_missing_reason":
                result["degraded_reasons"] = []
            elif unavailable_probe and args.mode == "crypto_probe_wrong_reason":
                result["degraded_reasons"] = ["wrong unavailable-crypto reason"]
            elif unavailable_probe and args.mode == "crypto_probe_missing_skip":
                result["skipped_checks"] = []
            elif unavailable_probe and args.mode == "crypto_probe_extra_skip":
                result["skipped_checks"] = [
                    "AUTH-SIGNATURE-VERIFY-01",
                    "AUTH-UNEXPECTED-SKIP",
                ]
            elif (
                target == "AICP-AUTHENTICATED-BASE@0.1"
                and not unavailable_probe
                and args.mode == "normal_auth_crypto_unavailable"
            ):
                result.update(
                    {
                        "degraded": True,
                        "degraded_reasons": [
                            "Ed25519 verification backend unexpectedly unavailable"
                        ],
                        "skipped_checks": ["AUTH-SIGNATURE-VERIFY-01"],
                    }
                )
            elif args.mode == "accepts_invalid_chain" and _errors_contain(
                result, ("chain", "prev-msg", "prev_msg")
            ):
                result.update({"accepted": True, "errors": []})
            elif args.mode == "accepts_invalid_signature" and _errors_contain(
                result, ("signature", "kid", "sender-signature", "key-resolution")
            ):
                result.update({"accepted": True, "errors": []})
            elif args.mode == "incomplete_core" and "STATE_SYNC_RESPONSE" in message_types:
                result.update(
                    {
                        "accepted": False,
                        "errors": [{"code": "unsupported", "message": "STATE_SYNC_RESPONSE unsupported"}],
                    }
                )
            elif (
                args.mode == "incomplete_authenticated"
                and target == "AICP-AUTHENTICATED-BASE@0.1"
                and any(len(message.get("signatures") or []) > 1 for message in transcript if isinstance(message, dict))
            ):
                result.update(
                    {
                        "accepted": False,
                        "errors": [{"code": "unsupported", "message": "co-signatures unsupported"}],
                    }
                )
            elif args.mode == "missing_mandatory_case_support" and message_types == ["ERROR"]:
                result.update(
                    {
                        "accepted": False,
                        "errors": [{"code": "unsupported", "message": "ERROR messages unsupported"}],
                    }
                )
            elif args.mode == "skipped_without_degraded" and result.get("accepted") is True:
                result.update(
                    {
                        "degraded": False,
                        "degraded_reasons": [],
                        "skipped_checks": ["MANDATORY"],
                    }
                )
            elif args.mode == "degraded_reason_without_degraded" and result.get("accepted") is True:
                result.update(
                    {
                        "degraded": False,
                        "degraded_reasons": ["contradictory degraded reason"],
                        "skipped_checks": [],
                    }
                )
            elif (
                args.mode == "wrong_degraded_skip"
                and input_obj.get("runtime_options", {}).get("cryptographic_verification") == "unavailable"
            ):
                result["skipped_checks"] = ["WRONG-MANDATORY-CHECK"]
            elif args.mode == "missing_skipped_checks_field":
                result.pop("skipped_checks", None)
        elif operation == "generate_scenario":
            scenario = input_obj.get("scenario") or {}
            artifact = result.get("artifact")
            if args.mode == "missing_mandatory_case_support" and scenario.get("desired_message_types") == ["ERROR"]:
                result["artifact"] = []
            elif isinstance(artifact, list):
                if args.mode == "wrong_producer_session":
                    for message in artifact:
                        message["session_id"] = "wrong-session"
                elif args.mode == "wrong_producer_contract":
                    for message in artifact:
                        message["contract_id"] = "wrong-contract"
                elif args.mode == "undeclared_producer_sender" and artifact:
                    artifact[0]["sender"] = "agent:undeclared"
                elif args.mode in {
                    "unsigned_authenticated_producer",
                    "authenticated_producer_crypto_unavailable",
                }:
                    for message in artifact:
                        message.pop("signatures", None)
                elif args.mode == "nondeterministic_producer":
                    seed = str(scenario.get("deterministic_seed"))
                    generation_counts[seed] = generation_counts.get(seed, 0) + 1
                    if generation_counts[seed] % 2 == 0:
                        _make_valid_unsigned_variant(artifact)
        elif args.mode == "mismatched_projection" and operation == "project_session_state":
            result["projection"]["session_id"] = "fake-mismatch"

        sys.stdout.write(json.dumps(response, separators=(",", ":"), ensure_ascii=False) + "\n")
        sys.stdout.flush()
        if args.mode == "partial_hang":
            time.sleep(10)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
