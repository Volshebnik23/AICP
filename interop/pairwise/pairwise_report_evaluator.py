#!/usr/bin/env python3
"""Independently evaluate M66 joint reports and compute typed pairwise relations."""

from __future__ import annotations

import argparse
import base64
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Callable

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
for import_path in (HERE, ROOT / "conformance" / "evidence"):
    if str(import_path) not in sys.path:
        sys.path.insert(0, str(import_path))

from pairwise_semantic_normalizer import semantic_digest  # noqa: E402
from report_evaluator import evaluate_report as evaluate_binding_report  # noqa: E402

RELEASE_ID = "AICP-PAIRWISE-TCK-1.0.0"
TARGET_ID = "AICP-BASE@0.1+BIND-MCP@0.1"
SCENARIO_ID = "PAIRWISE-MCP-CROSS-CONSUMPTION-01"
CONTROL_VERSION = "aicp.pairwise_control.v1"
MESSAGE_TYPES = ("CONTRACT_PROPOSE", "CONTRACT_ACCEPT", "ATTEST_ACTION")


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_file(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix.lower() in {".json", ".jsonl", ".md", ".py", ".ts", ".mjs", ".yml", ".yaml"}:
        data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return "sha256:" + hashlib.sha256(data).hexdigest()


def typed_hash(object_type: str, value: Any) -> str:
    preimage = b"AICP1\0" + object_type.encode("utf-8") + b"\0" + canonical_bytes(value)
    return "sha256:" + base64.urlsafe_b64encode(hashlib.sha256(preimage).digest()).decode("ascii").rstrip("=")


def message_hash(message: dict[str, Any]) -> str:
    body = copy.deepcopy(message)
    body.pop("message_hash", None)
    body.pop("signatures", None)
    return typed_hash("message", body)


def error(code: str, detail: str) -> dict[str, str]:
    return {"code": code, "message": detail}


def schema_errors(report: dict[str, Any]) -> list[dict[str, str]]:
    try:
        from jsonschema import Draft202012Validator, FormatChecker  # type: ignore
    except Exception:
        return [error("PAIRWISE_SCHEMA_VALIDATION_UNAVAILABLE", "jsonschema is required")]
    schema = json.loads((HERE / "pairwise_joint_report_v1.schema.json").read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    return [
        error(
            "PAIRWISE_REPORT_SCHEMA_INVALID",
            ("/" + "/".join(str(part) for part in issue.path) if issue.path else "/") + f": {issue.message}",
        )
        for issue in sorted(validator.iter_errors(report), key=lambda item: list(item.path))
    ]


def safe_report_path(base_dir: Path, ref: str) -> Path:
    target = (base_dir / ref).resolve()
    root = base_dir.resolve()
    if target != root and root not in target.parents:
        raise ValueError("report reference escapes the joint-report directory")
    if not target.is_file():
        raise ValueError(f"report reference does not exist: {ref}")
    return target


def load_release_errors(report: dict[str, Any]) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    errors: list[dict[str, str]] = []
    registry_path = HERE / "tck_releases.json"
    try:
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, [error("PAIRWISE_TCK_REGISTRY_INVALID", str(exc))]
    current_release = next((item for item in registry.get("releases", []) if item.get("release_id") == RELEASE_ID), None)
    snapshot_path = HERE / "release_registry_snapshots" / f"{RELEASE_ID}.json"
    try:
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, [error("PAIRWISE_TCK_SNAPSHOT_INVALID", str(exc))]
    release = next((item for item in snapshot.get("releases", []) if item.get("release_id") == RELEASE_ID), None)
    if not isinstance(release, dict) or current_release != release:
        return None, [error("PAIRWISE_TCK_RELEASE_UNKNOWN", RELEASE_ID)]
    declared = report.get("pairwise_tck_release", {})
    expected = {
        "release_id": RELEASE_ID,
        "registry_digest": sha256_file(snapshot_path),
        "runner_bundle_digest": release["runner_bundle"]["digest"],
        "report_schema_digest": release["report_schema"]["content_digest"],
        "evaluator_digest": release["evaluator"]["content_digest"],
        "normalizer_digest": release["normalizer"]["content_digest"],
    }
    if declared != expected:
        errors.append(error("PAIRWISE_TCK_PROVENANCE_MISMATCH", "declared release provenance does not exactly match the frozen registry"))
    file_bindings = (
        ("report_schema", "pairwise_joint_report_v1.schema.json"),
        ("evaluator", "pairwise_report_evaluator.py"),
        ("normalizer", "pairwise_semantic_normalizer.py"),
        ("target_registry", "targets.json"),
        ("scenario_catalog", "scenarios.json"),
    )
    for field, filename in file_bindings:
        if release.get(field, {}).get("content_digest") != sha256_file(HERE / filename):
            errors.append(error("PAIRWISE_TCK_ARTIFACT_DRIFT", f"{filename} no longer matches the frozen release"))
    if release.get("target_registry", {}).get("schema_digest") != sha256_file(HERE / "target_registry.schema.json"):
        errors.append(error("PAIRWISE_TCK_ARTIFACT_DRIFT", "target registry schema no longer matches the frozen release"))
    if release.get("scenario_catalog", {}).get("schema_digest") != sha256_file(HERE / "pairwise_scenario_v1.schema.json"):
        errors.append(error("PAIRWISE_TCK_ARTIFACT_DRIFT", "scenario schema no longer matches the frozen release"))
    if release.get("registry_schema_digest") != sha256_file(HERE / "tck_releases.schema.json"):
        errors.append(error("PAIRWISE_TCK_ARTIFACT_DRIFT", "Pairwise TCK registry schema no longer matches the frozen release"))
    bundle_ref = release.get("runner_bundle", {})
    bundle_path = ROOT / str(bundle_ref.get("path", ""))
    if not bundle_path.is_file() or bundle_ref.get("digest") != sha256_file(bundle_path):
        errors.append(error("PAIRWISE_TCK_ARTIFACT_DRIFT", "runner bundle manifest no longer matches the frozen release"))
    else:
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        for entry in bundle.get("entries", []):
            path = ROOT / str(entry.get("path", ""))
            if not path.is_file() or entry.get("digest") != sha256_file(path):
                errors.append(error("PAIRWISE_TCK_ARTIFACT_DRIFT", f"runner import closure drifted: {entry.get('path')}"))
    for authority in release.get("underlying_authorities", []):
        path = ROOT / str(authority.get("path", ""))
        if not path.is_file() or authority.get("content_digest") != sha256_file(path):
            errors.append(error("PAIRWISE_TCK_UNDERLYING_AUTHORITY_DRIFT", str(authority.get("path"))))
    if release.get("mandatory_execution") != {
        "target_id": TARGET_ID,
        "scenario_id": SCENARIO_ID,
        "directions": ["A_TO_B", "B_TO_A"],
        "clean_run_count": 2,
        "side_evidence": ["AICP-BASE@0.1/full-profile", "BIND-MCP@0.1/full-binding"],
    }:
        errors.append(error("PAIRWISE_TCK_MANDATORY_EXECUTION_INVALID", "release mandatory execution policy is not exact"))
    target = report.get("target", {})
    expected_target = {
        "profile_id": "AICP-BASE",
        "profile_version": "0.1",
        "binding_id": "BIND-MCP",
        "binding_version": "0.1",
        "target_catalog_digest": release["target_registry"]["content_digest"],
    }
    if target != expected_target:
        errors.append(error("PAIRWISE_TARGET_PROVENANCE_MISMATCH", "joint report does not bind the exact registered pairwise target"))
    scenario = report.get("scenario", {})
    expected_scenario = {
        "scenario_id": SCENARIO_ID,
        "scenario_catalog_digest": release["scenario_catalog"]["content_digest"],
        "scenario_schema_digest": release["scenario_catalog"]["schema_digest"],
    }
    if scenario != expected_scenario:
        errors.append(error("PAIRWISE_SCENARIO_PROVENANCE_MISMATCH", "joint report does not bind the exact registered pairwise scenario"))
    return release, errors


def default_profile_validator(report: dict[str, Any], participant: dict[str, Any]) -> list[str]:
    # Reuse the report-level IUT authority; never recurse through public submission validation.
    scripts_path = str(ROOT / "scripts")
    if scripts_path not in sys.path:
        sys.path.insert(0, scripts_path)
    from interop_submission_validation import _eligible_external_profile_report  # noqa: PLC0415

    return _eligible_external_profile_report(
        report,
        implementation_id=participant["implementation_id"],
        implementation_version=participant["implementation_version"],
        profile_id="AICP-BASE",
        profile_version="0.1",
    )


def evaluate_side_reports(
    report: dict[str, Any],
    *,
    base_dir: Path,
    profile_validator: Callable[[dict[str, Any], dict[str, Any]], list[str]] | None,
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    validator = profile_validator or default_profile_validator
    seen_paths: set[str] = set()
    participants = report.get("participants", [])
    side_evidence = {
        item.get("side"): item
        for item in report.get("side_evidence", [])
        if isinstance(item, dict)
    }
    for participant in participants if isinstance(participants, list) else []:
        if not isinstance(participant, dict):
            continue
        side = str(participant.get("side"))
        expected_side_evidence = {
            "side": side,
            "profile_report": participant.get("profile_report"),
            "binding_report": participant.get("binding_report"),
        }
        if side_evidence.get(side) != expected_side_evidence:
            errors.append(error("PAIRWISE_SIDE_EVIDENCE_BINDING_MISMATCH", f"side {side}"))
        for report_kind in ("profile_report", "binding_report"):
            ref = participant.get(report_kind)
            if not isinstance(ref, dict) or not isinstance(ref.get("path"), str):
                continue
            path_ref = ref["path"]
            if path_ref in seen_paths:
                errors.append(error("PAIRWISE_SIDE_REPORT_REUSED", f"{path_ref} is assigned more than once"))
                continue
            seen_paths.add(path_ref)
            try:
                path = safe_report_path(base_dir, path_ref)
            except ValueError as exc:
                errors.append(error("PAIRWISE_SIDE_REPORT_MISSING", f"side {side}: {exc}"))
                continue
            if ref.get("content_digest") != sha256_file(path):
                errors.append(error("PAIRWISE_SIDE_REPORT_DIGEST_MISMATCH", f"side {side}: {path_ref}"))
                continue
            try:
                side_report = json.loads(path.read_text(encoding="utf-8"))
            except Exception as exc:
                errors.append(error("PAIRWISE_SIDE_REPORT_INVALID", f"side {side}: {exc}"))
                continue
            subject = side_report.get("execution_subject")
            expected_identity = {
                "kind": participant.get("implementation_kind"),
                "implementation_id": participant.get("implementation_id"),
                "implementation_version": participant.get("implementation_version"),
                "implementation_digest": participant.get("implementation_digest"),
            }
            if not isinstance(subject, dict) or any(subject.get(key) != value for key, value in expected_identity.items()):
                errors.append(error("PAIRWISE_SIDE_IDENTITY_MISMATCH", f"side {side}: {report_kind} execution subject does not match the joint participant"))
                continue
            if report_kind == "profile_report":
                for detail in validator(side_report, participant):
                    errors.append(error("PAIRWISE_PROFILE_REPORT_INELIGIBLE", f"side {side}: {detail}"))
            else:
                evaluation = evaluate_binding_report(
                    side_report,
                    expected_implementation_id=str(participant.get("implementation_id")),
                    expected_implementation_version=str(participant.get("implementation_version")),
                )
                exact_target = {"kind": "binding", "target_id": "BIND-MCP", "target_version": "0.1"}
                if evaluation.get("status") != "eligible" or exact_target not in evaluation.get("eligible_targets", []):
                    details = "; ".join(str(item) for item in evaluation.get("errors", []))
                    errors.append(error("PAIRWISE_BINDING_REPORT_INELIGIBLE", f"side {side}: {details}"))
    return errors


def validate_exchange(
    item: dict[str, Any],
    *,
    sequence: int,
    direction: dict[str, Any],
    participants: dict[str, dict[str, Any]],
    previous: dict[str, Any] | None,
    seen_rpc_ids: set[str],
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    producer = direction["producer_side"]
    consumer = direction["consumer_side"]
    sender = producer if sequence in (1, 3) else consumer
    recipient = consumer if sequence in (1, 3) else producer
    prefix = f"{direction.get('direction')} message {sequence}"
    if item.get("sequence") != sequence or item.get("sender_side") != sender or item.get("constructed_by") != sender or item.get("consumed_by") != recipient:
        errors.append(error("PAIRWISE_DIRECTION_ROLE_MISMATCH", prefix))
    message = item.get("message")
    if not isinstance(message, dict):
        return [*errors, error("PAIRWISE_MESSAGE_INVALID", f"{prefix}: missing envelope")]
    if message.get("message_type") != MESSAGE_TYPES[sequence - 1]:
        errors.append(error("PAIRWISE_MESSAGE_ORDER_INVALID", prefix))
    if message.get("session_id") != direction.get("session_id") or message.get("contract_id") != direction.get("contract_id"):
        errors.append(error("PAIRWISE_MESSAGE_SCOPE_MISMATCH", prefix))
    if message.get("sender") != participants.get(sender, {}).get("implementation_id"):
        errors.append(error("PAIRWISE_MESSAGE_SENDER_MISMATCH", prefix))
    if message.get("message_hash") != message_hash(message):
        errors.append(error("PAIRWISE_MESSAGE_HASH_INVALID", prefix))
    expected_previous = previous.get("message_hash") if previous is not None else None
    if sequence == 1:
        if "prev_msg_hash" in message:
            errors.append(error("PAIRWISE_MESSAGE_CHAIN_INVALID", f"{prefix}: proposal must be a root"))
    elif message.get("prev_msg_hash") != expected_previous:
        errors.append(error("PAIRWISE_MESSAGE_CHAIN_INVALID", prefix))
    payload = message.get("payload")
    if not isinstance(payload, dict):
        errors.append(error("PAIRWISE_MESSAGE_PAYLOAD_INVALID", prefix))
    elif sequence == 1:
        contract = payload.get("contract")
        if not isinstance(contract, dict) or contract.get("contract_id") != direction.get("contract_id") or contract.get("roles") != ["initiator", "responder"] or payload.get("contract_hash") != typed_hash("contract", contract):
            errors.append(error("PAIRWISE_PROPOSAL_SEMANTICS_INVALID", prefix))
    elif sequence == 2 and payload != {"accepted": True}:
        errors.append(error("PAIRWISE_ACCEPTANCE_SEMANTICS_INVALID", prefix))
    elif sequence == 3:
        expected_result = typed_hash("result", {"peer_hash": expected_previous})
        if payload.get("action_type") != "pairwise_cross_consumption" or payload.get("result_hash") != expected_result:
            errors.append(error("PAIRWISE_ATTESTATION_SEMANTICS_INVALID", prefix))

    control_request = item.get("control_request", {})
    control_response = item.get("control_response", {})
    phase = ("propose", "accept", "attest")[sequence - 1]
    control_input = control_request.get("input", {}) if isinstance(control_request, dict) else {}
    if control_request.get("control_version") != CONTROL_VERSION or control_request.get("operation") != "construct" or control_input.get("phase") != phase:
        errors.append(error("PAIRWISE_CONTROL_REQUEST_INVALID", prefix))
    if control_response.get("control_version") != CONTROL_VERSION or control_response.get("request_id") != control_request.get("request_id") or control_response.get("operation") != "construct" or control_response.get("success") is not True:
        errors.append(error("PAIRWISE_CONTROL_CORRELATION_INVALID", prefix))
    if control_response.get("result", {}).get("message") != message:
        errors.append(error("PAIRWISE_CONTROL_OUTPUT_MISMATCH", prefix))
    expected_visible = [] if sequence == 1 else [expected_previous]
    if control_input.get("visible_message_hashes") != expected_visible:
        errors.append(error("PAIRWISE_CONTROL_VISIBILITY_INVALID", prefix))
    if sequence == 1:
        if "peer_message" in control_input:
            errors.append(error("PAIRWISE_CONTROL_PRESEED_INVALID", prefix))
    elif control_input.get("peer_message") != previous:
        errors.append(error("PAIRWISE_CROSS_CONSUMPTION_MISSING", prefix))

    for exchange_name, tool in (("mcp_send", "aicp.sendMessage"), ("mcp_poll", "aicp.pollMessages")):
        exchange = item.get(exchange_name, {})
        request = exchange.get("request", {}) if isinstance(exchange, dict) else {}
        response = exchange.get("response", {}) if isinstance(exchange, dict) else {}
        request_id = request.get("id")
        if request.get("jsonrpc") != "2.0" or request.get("method") != "tools/call" or request.get("params", {}).get("name") != tool:
            errors.append(error("PAIRWISE_MCP_REQUEST_INVALID", f"{prefix}: {exchange_name}"))
        if not isinstance(request_id, str) or request_id in seen_rpc_ids:
            errors.append(error("PAIRWISE_MCP_REQUEST_REPLAY", f"{prefix}: {exchange_name}"))
        elif isinstance(request_id, str):
            seen_rpc_ids.add(request_id)
        if response.get("jsonrpc") != "2.0" or response.get("id") != request_id or "error" in response:
            errors.append(error("PAIRWISE_MCP_CORRELATION_INVALID", f"{prefix}: {exchange_name}"))
    send_args = item.get("mcp_send", {}).get("request", {}).get("params", {}).get("arguments", {})
    send_result = item.get("mcp_send", {}).get("response", {}).get("result", {})
    if send_args != {"message": message} or send_result.get("accepted") is not True or send_result.get("message_hash") != message.get("message_hash"):
        errors.append(error("PAIRWISE_MCP_SEND_EVIDENCE_INVALID", prefix))
    poll_args = item.get("mcp_poll", {}).get("request", {}).get("params", {}).get("arguments", {})
    poll_result = item.get("mcp_poll", {}).get("response", {}).get("result", {})
    if poll_args.get("session_id") != direction.get("session_id") or poll_args.get("limit") != 1 or not isinstance(poll_args.get("after_cursor"), str):
        errors.append(error("PAIRWISE_MCP_POLL_REQUEST_INVALID", prefix))
    if poll_result.get("messages") != [message] or not isinstance(poll_result.get("next_cursor"), str):
        errors.append(error("PAIRWISE_MCP_POLL_EVIDENCE_INVALID", prefix))
    first_seen = item.get("first_seen", {})
    expected_before = [] if sequence in (1, 2) else [direction["messages"][0]["message"].get("message_hash")]
    expected_after = [*expected_before, message.get("message_hash")]
    if first_seen.get("visible_hashes_before") != expected_before or first_seen.get("visible_hashes_after") != expected_after:
        errors.append(error("PAIRWISE_FIRST_SEEN_CAUSALITY_INVALID", prefix))
    return errors


def validate_runs(report: dict[str, Any]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    participants_list = report.get("participants", [])
    participants = {item.get("side"): item for item in participants_list if isinstance(item, dict)} if isinstance(participants_list, list) else {}
    if set(participants) != {"A", "B"}:
        errors.append(error("PAIRWISE_PARTICIPANT_SIDES_INVALID", "participants must contain sides A and B exactly once"))
        return errors
    identities = [(item.get("implementation_id"), item.get("implementation_version"), item.get("implementation_digest")) for item in participants.values()]
    if identities[0][0] == identities[1][0] or identities[0][2] == identities[1][2]:
        errors.append(error("PAIRWISE_PARTICIPANTS_NOT_DISTINCT", "implementation IDs and build digests must both differ"))
    for side, participant in participants.items():
        descriptor = participant.get("descriptor_evidence", {})
        request = descriptor.get("request", {}) if isinstance(descriptor, dict) else {}
        response = descriptor.get("response", {}) if isinstance(descriptor, dict) else {}
        result = response.get("result", {}) if isinstance(response, dict) else {}
        if (
            request.get("control_version") != CONTROL_VERSION
            or request.get("operation") != "describe"
            or response.get("control_version") != CONTROL_VERSION
            or response.get("request_id") != request.get("request_id")
            or response.get("operation") != "describe"
            or response.get("success") is not True
            or result.get("implementation_kind") != participant.get("implementation_kind")
            or result.get("implementation_id") != participant.get("implementation_id")
            or result.get("implementation_version") != participant.get("implementation_version")
            or result.get("implementation_digest") != participant.get("implementation_digest")
            or result.get("supported_target") != TARGET_ID
        ):
            errors.append(error("PAIRWISE_PROCESS_DESCRIPTOR_MISMATCH", f"side {side}"))
    runs = report.get("runs", [])
    if not isinstance(runs, list) or len(runs) != 2:
        return [*errors, error("PAIRWISE_CLEAN_RUN_COUNT_INVALID", "exactly two clean runs are required")]
    freshness: dict[str, set[str]] = {name: set() for name in ("run_id", "challenge", "session_id", "contract_id", "message_id")}
    semantic_digests: list[str] = []
    seen_rpc_ids: set[str] = set()
    for run in runs:
        if not isinstance(run, dict):
            errors.append(error("PAIRWISE_RUN_INVALID", "run must be an object"))
            continue
        for name in ("run_id", "challenge"):
            value = run.get(name)
            if not isinstance(value, str) or value in freshness[name]:
                errors.append(error("PAIRWISE_RUN_FRESHNESS_INVALID", f"{name} must be unique across runs"))
            elif isinstance(value, str):
                freshness[name].add(value)
        recomputed = semantic_digest(run)
        semantic_digests.append(recomputed)
        if run.get("semantic_digest") != recomputed:
            errors.append(error("PAIRWISE_SEMANTIC_DIGEST_INVALID", str(run.get("run_id"))))
        directions = run.get("directions", [])
        if not isinstance(directions, list) or [item.get("direction") for item in directions if isinstance(item, dict)] != ["A_TO_B", "B_TO_A"]:
            errors.append(error("PAIRWISE_DIRECTION_COVERAGE_INVALID", str(run.get("run_id"))))
            continue
        for direction in directions:
            expected = ("A", "B") if direction.get("direction") == "A_TO_B" else ("B", "A")
            if (direction.get("producer_side"), direction.get("consumer_side")) != expected:
                errors.append(error("PAIRWISE_DIRECTION_ROLE_MISMATCH", str(direction.get("direction"))))
            for name in ("session_id", "contract_id"):
                value = direction.get(name)
                if not isinstance(value, str) or value in freshness[name]:
                    errors.append(error("PAIRWISE_RUN_FRESHNESS_INVALID", f"{name} must be globally unique"))
                elif isinstance(value, str):
                    freshness[name].add(value)
            messages = direction.get("messages", [])
            if not isinstance(messages, list) or len(messages) != 3:
                errors.append(error("PAIRWISE_MESSAGE_COVERAGE_INVALID", str(direction.get("direction"))))
                continue
            previous = None
            for sequence, item in enumerate(messages, start=1):
                if not isinstance(item, dict):
                    errors.append(error("PAIRWISE_MESSAGE_INVALID", f"sequence {sequence}"))
                    continue
                message_id = item.get("message", {}).get("message_id")
                if not isinstance(message_id, str) or message_id in freshness["message_id"]:
                    errors.append(error("PAIRWISE_MESSAGE_REPLAY", f"message_id at sequence {sequence}"))
                elif isinstance(message_id, str):
                    freshness["message_id"].add(message_id)
                errors.extend(validate_exchange(item, sequence=sequence, direction=direction, participants=participants, previous=previous, seen_rpc_ids=seen_rpc_ids))
                previous = item.get("message")
    if len(semantic_digests) == 2 and semantic_digests[0] != semantic_digests[1]:
        errors.append(error("PAIRWISE_CLEAN_RUNS_NOT_SEMANTICALLY_EQUIVALENT", "fresh runs normalize to different semantics"))
    return errors


def evaluate_pairwise_report(
    report: dict[str, Any],
    *,
    base_dir: Path,
    profile_validator: Callable[[dict[str, Any], dict[str, Any]], list[str]] | None = None,
) -> dict[str, Any]:
    errors = schema_errors(report)
    if errors:
        return {"status": "rejected", "errors": errors, "eligible_pairwise_relations": [], "eligible_marks": []}
    _, release_errors = load_release_errors(report)
    errors.extend(release_errors)
    if report.get("passed") is not True or report.get("failures") != [] or report.get("degraded") is not False or report.get("degraded_reasons") != [] or report.get("skipped_checks") != []:
        errors.append(error("PAIRWISE_REPORT_NOT_CLEAN", "joint report must be passed, non-degraded, unskipped, and failure-free"))
    if report.get("compatibility_marks") != []:
        errors.append(error("PAIRWISE_MARKS_FORBIDDEN", "pairwise relations are not compatibility marks"))
    errors.extend(evaluate_side_reports(report, base_dir=base_dir, profile_validator=profile_validator))
    errors.extend(validate_runs(report))
    if errors:
        return {"status": "rejected", "errors": errors, "eligible_pairwise_relations": [], "eligible_marks": []}
    endpoints = sorted(
        (
            {
                "implementation_id": item["implementation_id"],
                "implementation_version": item["implementation_version"],
                "implementation_digest": item["implementation_digest"],
            }
            for item in report["participants"]
        ),
        key=lambda item: (item["implementation_id"], item["implementation_version"], item["implementation_digest"]),
    )
    relation = {
        "relation_kind": "pairwise_interop",
        "target_id": TARGET_ID,
        "endpoints": endpoints,
        "profile_ref": {"profile_id": "AICP-BASE", "profile_version": "0.1"},
        "binding_ref": {"binding_id": "BIND-MCP", "binding_version": "0.1"},
        "pairwise_tck_release": RELEASE_ID,
        "joint_report_digest": "sha256:" + hashlib.sha256(canonical_bytes(report)).hexdigest(),
    }
    return {"status": "eligible", "errors": [], "eligible_pairwise_relations": [relation], "eligible_marks": []}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report")
    args = parser.parse_args()
    path = Path(args.report).resolve()
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
        result = evaluate_pairwise_report(report, base_dir=path.parent)
    except Exception as exc:
        result = {"status": "rejected", "errors": [error("PAIRWISE_EVALUATOR_FAILURE", str(exc))], "eligible_pairwise_relations": [], "eligible_marks": []}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "eligible" else 1


if __name__ == "__main__":
    raise SystemExit(main())
