#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REF_PY = ROOT / "reference" / "python"
IUT_DIR = ROOT / "conformance" / "iut"
for path in (REF_PY, IUT_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from _iut_evaluator import evaluate_transcript  # noqa: E402
from aicp_ref.hashing import object_hash  # noqa: E402
from aicp_ref.jcs import canonicalize_json  # noqa: E402
from projection_v1_handler import derive_projection  # noqa: E402


PROTOCOL_VERSION = "1.1"
TARGET_KEY = "aicp.session_state_projection@v1"
SUITE_REF = "conformance/extensions/OR_SESSION_STATE_PROJECTION_V1.json"

if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8", errors="strict")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="strict")


def _file_digest(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _validate_transcript(input_obj: dict[str, Any]) -> dict[str, Any]:
    if input_obj.get("target") != {
        "kind": "capability",
        "target_id": "aicp.session_state_projection",
        "target_version": "v1",
    }:
        return {
            "accepted": False,
            "errors": [
                {
                    "code": "TARGET_NOT_SUPPORTED",
                    "message": "target must be exact projection v1",
                }
            ],
            "degraded": False,
            "degraded_reasons": [],
            "skipped_checks": [],
        }
    transcript = input_obj.get("transcript")
    if not isinstance(transcript, list) or not all(
        isinstance(item, dict) for item in transcript
    ):
        return {
            "accepted": False,
            "errors": [
                {
                    "code": "INVALID_TRANSCRIPT",
                    "message": "transcript must be an array of message objects",
                }
            ],
            "degraded": False,
            "degraded_reasons": [],
            "skipped_checks": [],
        }
    errors, degraded, reasons, skipped = evaluate_transcript(
        transcript,
        [SUITE_REF],
    )
    return {
        "accepted": not errors,
        "errors": errors,
        "degraded": degraded,
        "degraded_reasons": reasons,
        "skipped_checks": skipped,
    }


def handle_request(
    request: dict[str, Any],
    *,
    implementation_kind: str = "reference_corpus",
    implementation_id: str = "aicp-projection-v1-reference-adapter",
    implementation_version: str = "1.0.0",
    implementation_digest: str | None = None,
) -> dict[str, Any]:
    operation = request.get("operation")
    input_obj = request.get("input") or {}
    if not isinstance(input_obj, dict):
        raise ValueError("request input must be an object")
    if operation == "describe":
        result = {
            "adapter_protocol_version": PROTOCOL_VERSION,
            "implementation_kind": implementation_kind,
            "implementation_id": implementation_id,
            "implementation_version": implementation_version,
            "implementation_digest": implementation_digest
            or _file_digest(Path(__file__)),
            "supported_aicp_capabilities": [
                {
                    "capability_id": "aicp.session_state_projection",
                    "capability_version": "v1",
                }
            ],
        }
    elif operation == "canonicalize_hash":
        result = {
            "canonical_json": canonicalize_json(input_obj.get("object")),
            "object_hash": object_hash(
                str(input_obj.get("object_type")),
                input_obj.get("object"),
            ),
        }
    elif operation == "validate_transcript":
        result = _validate_transcript(input_obj)
    elif operation == "project_session_state":
        if input_obj.get("target") != {
            "kind": "capability",
            "target_id": "aicp.session_state_projection",
            "target_version": "v1",
        }:
            raise ValueError("project_session_state target is not supported")
        transcript = input_obj.get("transcript")
        scenario = input_obj.get("scenario")
        if not isinstance(transcript, list) or not transcript:
            raise ValueError("project_session_state requires a transcript")
        if not isinstance(scenario, dict):
            raise ValueError("project_session_state requires a neutral scenario")
        projection, projection_hash = derive_projection(scenario, transcript)
        result = {
            "projection": projection,
            "session_state_hash": projection_hash,
        }
    else:
        raise ValueError(f"unsupported operation: {operation}")
    return {
        "adapter_protocol_version": PROTOCOL_VERSION,
        "request_id": request.get("request_id"),
        "operation": operation,
        "success": True,
        "result": result,
    }


def main() -> int:
    for raw in sys.stdin:
        if not raw.strip():
            continue
        request: dict[str, Any] = {}
        try:
            request = json.loads(raw)
            response = handle_request(request)
        except Exception as exc:
            response = {
                "adapter_protocol_version": PROTOCOL_VERSION,
                "request_id": request.get("request_id"),
                "operation": request.get("operation"),
                "success": False,
                "error": {
                    "code": "adapter_error",
                    "message": str(exc),
                },
            }
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
