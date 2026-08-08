#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = ROOT / "conformance" / "evidence"
REF_PY = ROOT / "reference" / "python"
for path in (EVIDENCE_DIR, REF_PY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from aicp_ref.hashing import object_hash  # noqa: E402
from aicp_ref.jcs import canonicalize_json  # noqa: E402
from profile_scenario_builder import generated_transcript_result  # noqa: E402
from profile_transcript_evaluator import evaluate_profile_transcript  # noqa: E402
from target_catalog import canonical_target_key, resolve_target_record  # noqa: E402


SUPPORTED_PROFILES = [
    {"profile_id": "AICP-MEDIATED-BLOCKING", "profile_version": "0.1"},
    {"profile_id": "AICP-RESUMABLE-SESSIONS", "profile_version": "0.1"},
    {"profile_id": "AICP-DELEGATED-IDENTITY", "profile_version": "0.1"},
]


def metadata(implementation_kind: str = "reference_corpus") -> dict[str, Any]:
    return {
        "implementation_kind": implementation_kind,
        "implementation_id": (
            "aicp-product-profile-reference"
            if implementation_kind == "reference_corpus"
            else "test-only-product-profile-external"
        ),
        "implementation_version": "1.0.0",
        "implementation_digest": "sha256:" + ("a" if implementation_kind == "reference_corpus" else "b") * 64,
        "supported_aicp_profiles": [dict(item) for item in SUPPORTED_PROFILES],
        "adapter_protocol_version": "1.1",
    }


def _record_from_target(target: Any) -> Any:
    if not isinstance(target, dict):
        raise ValueError("exact target object is required")
    key = canonical_target_key(
        str(target.get("kind")),
        str(target.get("target_id")),
        str(target.get("target_version")),
    )
    record = resolve_target_record(key)
    if record.target_kind != "product_profile":
        raise ValueError("product profile adapter accepts only product_profile targets")
    return record


def handle_request(
    request: dict[str, Any],
    *,
    implementation_kind: str = "reference_corpus",
) -> dict[str, Any]:
    operation = request.get("operation")
    input_obj = request.get("input") if isinstance(request.get("input"), dict) else {}
    if operation == "describe":
        return metadata(implementation_kind)
    if operation == "canonicalize_hash":
        return {
            "canonical_json": canonicalize_json(input_obj["object"]),
            "object_hash": object_hash(input_obj["object_type"], input_obj["object"]),
        }
    if operation == "validate_transcript":
        record = _record_from_target(input_obj.get("target"))
        transcript = input_obj.get("transcript")
        if not isinstance(transcript, list):
            raise ValueError("transcript must be an array")
        material = (
            input_obj.get("public_verification_material")
            if isinstance(input_obj.get("public_verification_material"), dict)
            else {}
        )
        selected_suite = material.get("selected_suite")
        if selected_suite not in record.required_suites:
            raise ValueError("selected suite is not required by the exact target")
        runtime = input_obj.get("runtime_options") if isinstance(input_obj.get("runtime_options"), dict) else {}
        return evaluate_profile_transcript(
            transcript,
            [str(selected_suite)],
            simulate_no_crypto=bool(runtime.get("simulate_no_crypto")),
        ).as_adapter_result()
    if operation == "generate_scenario":
        _record_from_target(input_obj.get("target"))
        scenario = input_obj.get("scenario")
        if not isinstance(scenario, dict):
            raise ValueError("neutral scenario must be an object")
        return generated_transcript_result(scenario)
    raise ValueError(f"unsupported operation: {operation}")


def main() -> int:
    for raw_bytes in sys.stdin.buffer:
        raw = raw_bytes.decode("utf-8")
        if not raw.strip():
            continue
        request: dict[str, Any] = {}
        try:
            request = json.loads(raw)
            result = handle_request(request)
            response = {
                "adapter_protocol_version": "1.1",
                "request_id": request["request_id"],
                "operation": request["operation"],
                "success": True,
                "result": result,
            }
        except Exception as exc:
            response = {
                "adapter_protocol_version": "1.1",
                "request_id": request.get("request_id"),
                "operation": request.get("operation"),
                "success": False,
                "error": {
                    "code": "adapter_error",
                    "message": str(exc),
                },
            }
        sys.stdout.buffer.write(
            (json.dumps(response, ensure_ascii=False) + "\n").encode("utf-8")
        )
        sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
