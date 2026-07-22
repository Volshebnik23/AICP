#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
REF_PY = ROOT / "reference/python"
if str(REF_PY) not in sys.path:
    sys.path.insert(0, str(REF_PY))

from aicp_ref.chain import verify_transcript_chain  # noqa: E402
from aicp_ref.hashing import message_hash_from_body, object_hash  # noqa: E402
from aicp_ref.jcs import canonicalize_json  # noqa: E402
from aicp_ref.session_state import project_session_state, validate_session_state_projection  # noqa: E402
from aicp_ref.signatures import signature_verifier_available  # noqa: E402
from aicp_ref.validate import message_body_without_hash_and_signatures, validate_message_signatures  # noqa: E402


PROTOCOL_VERSION = "1.0"
CASES_PATH = ROOT / "conformance/iut/cases.json"

if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8", errors="strict")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="strict")


def _sha256_file(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix.lower() in {".json", ".jsonl", ".md", ".py", ".ts", ".mjs", ".yml", ".yaml"}:
        data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _case_map() -> dict[str, str]:
    catalog = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    mapping: dict[str, str] = {}
    for profile in catalog["profiles"].values():
        producer = profile["producer_case"]
        mapping[producer["case_id"]] = producer["fixture"]
    state = catalog["session_state_projection"]["producer_case"]
    mapping[state["case_id"]] = state["fixture"]
    return mapping


def _base_validation(messages: list[dict[str, Any]], key_map: dict[str, Any]) -> tuple[list[dict[str, str]], bool, list[str]]:
    errors: list[dict[str, str]] = []
    degraded = False
    degraded_reasons: list[str] = []
    for message in verify_transcript_chain(messages):
        errors.append({"code": "chain", "message": message})
    for index, message in enumerate(messages, start=1):
        try:
            computed = message_hash_from_body(message_body_without_hash_and_signatures(message))
        except Exception as exc:
            errors.append({"code": "message_hash", "message": f"line {index}: hash recompute error: {exc}"})
        else:
            if computed != message.get("message_hash"):
                errors.append({"code": "message_hash", "message": f"line {index}: message_hash mismatch"})
        for issue in validate_message_signatures(message, key_map, verify_crypto=True):
            if issue["code"] == "crypto_unavailable":
                degraded = True
                if issue["message"] not in degraded_reasons:
                    degraded_reasons.append(issue["message"])
            else:
                errors.append({"code": issue["code"], "message": f"line {index}: {issue['message']}"})
    return errors, degraded, degraded_reasons


def _validate(input_obj: dict[str, Any]) -> dict[str, Any]:
    target = input_obj.get("target")
    messages = input_obj.get("transcript")
    key_map = input_obj.get("public_keys") or {}
    if not isinstance(messages, list) or not all(isinstance(item, dict) for item in messages):
        return {"accepted": False, "errors": [{"code": "protocol", "message": "transcript must be an array of objects"}], "degraded": False, "degraded_reasons": []}

    errors, degraded, degraded_reasons = _base_validation(messages, key_map)
    if target == "AICP-AUTHENTICATED-BASE@0.1":
        for index, message in enumerate(messages, start=1):
            for issue in validate_message_signatures(
                message,
                key_map,
                verify_crypto=True,
                require_signatures=True,
                require_sender_signature=True,
            ):
                if issue["code"] == "crypto_unavailable":
                    degraded = True
                    if issue["message"] not in degraded_reasons:
                        degraded_reasons.append(issue["message"])
                else:
                    entry = {"code": issue["code"], "message": f"line {index}: {issue['message']}"}
                    if entry not in errors:
                        errors.append(entry)
    elif target == "SESSION-STATE-PROJECTION-V1":
        profiles = {
            (entry.get("profile_id"), entry.get("profile_version"))
            for entry in json.loads((ROOT / "registry/aicp_profiles.json").read_text(encoding="utf-8"))
        }
        extensions = {
            entry.get("id")
            for entry in json.loads((ROOT / "registry/extension_ids.json").read_text(encoding="utf-8"))
        }
        for index, message in enumerate(messages):
            for issue in validate_session_state_projection(
                message,
                messages,
                index,
                registered_profiles=profiles,
                registered_extensions=extensions,
            ):
                errors.append({"code": issue["code"], "message": f"line {index + 1}: {issue['message']}"})

    return {
        "accepted": not errors,
        "errors": errors,
        "degraded": degraded,
        "degraded_reasons": degraded_reasons,
    }


def handle_request(request: dict[str, Any]) -> dict[str, Any]:
    operation = request.get("operation")
    input_obj = request.get("input") or {}
    if operation == "describe":
        result = {
            "adapter_protocol_version": PROTOCOL_VERSION,
            "implementation_kind": "reference_adapter",
            "implementation_id": "aicp-python-reference-adapter",
            "implementation_version": (ROOT / "VERSION").read_text(encoding="utf-8").strip(),
            "implementation_digest": _sha256_file(Path(__file__)),
            "supported_aicp_profiles": ["AICP-BASE@0.1", "AICP-AUTHENTICATED-BASE@0.1"],
            "supported_crypto_profiles": ["aicp.crypto.ed25519.v1"],
            "supported_capabilities": ["aicp.session_state_projection.v1"],
        }
    elif operation == "canonicalize_hash":
        result = {
            "canonical_json": canonicalize_json(input_obj.get("object")),
            "object_hash": object_hash(str(input_obj.get("object_type")), input_obj.get("object")),
        }
    elif operation == "validate_transcript":
        result = _validate(input_obj)
    elif operation == "generate_case":
        case_id = input_obj.get("case_id")
        fixture = _case_map().get(case_id)
        if fixture is None:
            raise ValueError(f"unknown canonical case_id: {case_id}")
        result = {"case_id": case_id, "artifact": _load_jsonl(ROOT / fixture)}
    elif operation == "project_session_state":
        projection, projection_hash = project_session_state(input_obj.get("context") or {})
        result = {"projection": projection, "session_state_hash": projection_hash}
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
                "error": {"code": "adapter_error", "message": str(exc)},
            }
        sys.stdout.write(json.dumps(response, separators=(",", ":"), ensure_ascii=False) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
