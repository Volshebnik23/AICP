#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REF_PY = ROOT / "reference/python"
IUT_DIR = ROOT / "conformance/iut"
for path in (REF_PY, IUT_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from _iut_evaluator import evaluate_transcript  # noqa: E402
from aicp_iut_catalog import CASES_PATH, profile_config  # noqa: E402
from aicp_ref.hashing import object_hash  # noqa: E402
from aicp_ref.jcs import canonicalize_json  # noqa: E402
from aicp_ref.session_state import project_session_state, validate_session_state_projection  # noqa: E402


PROTOCOL_VERSION = "1.1"

if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8", errors="strict")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="strict")


def _sha256_file(path: Path) -> str:
    data = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _catalog() -> dict[str, Any]:
    return json.loads(CASES_PATH.read_text(encoding="utf-8"))


def _producer_template(target: str, scenario: dict[str, Any]) -> list[dict[str, Any]]:
    config = profile_config(_catalog(), target)
    for producer in config["full_profile"]["producer_scenarios"]:
        if producer.get("scenario") == scenario:
            return _load_jsonl(ROOT / producer["template_fixture"])
    raise ValueError("unsupported neutral producer scenario")


def _validate_profile(input_obj: dict[str, Any]) -> dict[str, Any]:
    target = input_obj.get("target_profile")
    messages = input_obj.get("transcript")
    if not isinstance(target, str):
        return {
            "accepted": False,
            "errors": [{"code": "protocol", "message": "target_profile must be an exact profile string"}],
            "degraded": False,
            "degraded_reasons": [],
            "skipped_checks": [],
        }
    if not isinstance(messages, list) or not all(isinstance(item, dict) for item in messages):
        return {
            "accepted": False,
            "errors": [{"code": "protocol", "message": "transcript must be an array of objects"}],
            "degraded": False,
            "degraded_reasons": [],
            "skipped_checks": [],
        }
    config = profile_config(_catalog(), target)
    errors, degraded, degraded_reasons, skipped_checks = evaluate_transcript(messages, config["required_suites"])
    runtime_options = input_obj.get("runtime_options") or {}
    if (
        target == "AICP-AUTHENTICATED-BASE@0.1"
        and runtime_options.get("cryptographic_verification") == "unavailable"
    ):
        degraded = True
        reason = "Ed25519 verification backend unavailable for requested test mode"
        if reason not in degraded_reasons:
            degraded_reasons.append(reason)
        if "AUTH-SIGNATURE-VERIFY-01" not in skipped_checks:
            skipped_checks.append("AUTH-SIGNATURE-VERIFY-01")
    return {
        "accepted": not errors,
        "errors": errors,
        "degraded": degraded,
        "degraded_reasons": degraded_reasons,
        "skipped_checks": skipped_checks,
    }


def _validate_state_projection(input_obj: dict[str, Any]) -> dict[str, Any]:
    messages = input_obj.get("transcript")
    if not isinstance(messages, list) or not all(isinstance(item, dict) for item in messages):
        return {
            "accepted": False,
            "errors": [{"code": "protocol", "message": "transcript must be an array of objects"}],
            "degraded": False,
            "degraded_reasons": [],
            "skipped_checks": [],
        }
    profiles = {
        (entry.get("profile_id"), entry.get("profile_version"))
        for entry in json.loads((ROOT / "registry/aicp_profiles.json").read_text(encoding="utf-8"))
    }
    extensions = {
        entry.get("id")
        for entry in json.loads((ROOT / "registry/extension_ids.json").read_text(encoding="utf-8"))
    }
    errors: list[dict[str, str]] = []
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
        "degraded": False,
        "degraded_reasons": [],
        "skipped_checks": [],
    }


def handle_request(request: dict[str, Any]) -> dict[str, Any]:
    operation = request.get("operation")
    input_obj = request.get("input") or {}
    if operation == "describe":
        result = {
            "adapter_protocol_version": PROTOCOL_VERSION,
            "implementation_kind": "reference_corpus",
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
        if input_obj.get("target_profile") == "aicp.session_state_projection.v1":
            result = _validate_state_projection(input_obj)
        else:
            result = _validate_profile(input_obj)
    elif operation == "generate_scenario":
        target = input_obj.get("target_profile")
        scenario = input_obj.get("scenario")
        if not isinstance(target, str) or not isinstance(scenario, dict):
            raise ValueError("generate_scenario requires target_profile and scenario")
        result = {"artifact": _producer_template(target, scenario)}
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
