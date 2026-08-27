#!/usr/bin/env python3
"""Independently evaluate Pairwise TCK 1.3 raw-role and global-causality evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover - dependency validation reports this fail-closed
    Draft202012Validator = None  # type: ignore[assignment]


HERE = Path(__file__).resolve().parent
TARGET_ID = "AICP-BASE@0.1+BIND-MCP@0.1"
SCENARIO_ID = "PAIRWISE-MCP-RAW-ROLE-GLOBAL-CAUSALITY-03"
RELEASE_ID = "AICP-PAIRWISE-TCK-1.3.0"
CLIENT_CONTROL_VERSION = "aicp.pairwise_client_control.v1"
ROLE_DESCRIPTOR_VERSION = "aicp.pairwise_role_descriptor.v1"
TEXT_SUFFIXES = {".json", ".jsonl", ".md", ".py", ".ts", ".mjs", ".yml", ".yaml"}

from pairwise_semantic_normalizer_v1_3 import semantic_digest  # noqa: E402
from pairwise_side_authority_client_v1_3 import (  # noqa: E402
    evaluate_side_report,
    frozen_hash,
    validate_core_transcript,
)


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return "sha256:" + hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix.lower() in TEXT_SUFFIXES:
        data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    return sha256_bytes(data)


def error(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def safe_path(base: Path, reference: str) -> Path:
    path = (base / reference).resolve()
    if not path.is_relative_to(base.resolve()):
        raise ValueError("report reference escapes its package root")
    return path


def schema_errors(report: dict[str, Any], schema_path: Path) -> list[dict[str, str]]:
    if Draft202012Validator is None:
        return [error("PAIRWISE_SCHEMA_DEPENDENCY_MISSING", "jsonschema is required")]
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    return [
        error("PAIRWISE_REPORT_SCHEMA_INVALID", f"{list(item.path)}: {item.message}")
        for item in Draft202012Validator(schema).iter_errors(report)
    ]


def validate_artifact(reference: Any, *, label: str) -> list[dict[str, str]]:
    if not isinstance(reference, dict):
        return [error("PAIRWISE_RELEASE_ARTIFACT_INVALID", f"{label} reference is missing")]
    path_value = reference.get("path")
    digest = reference.get("content_digest") or reference.get("digest")
    if not isinstance(path_value, str) or not isinstance(digest, str):
        return [error("PAIRWISE_RELEASE_ARTIFACT_INVALID", f"{label} reference is incomplete")]
    path = safe_path(HERE.parents[1], path_value)
    if not path.is_file() or sha256_file(path) != digest:
        return [error("PAIRWISE_RELEASE_ARTIFACT_DRIFT", f"{label} bytes differ: {path_value}")]
    return []


def load_release_errors(report: dict[str, Any]) -> tuple[dict[str, Any] | None, list[dict[str, str]]]:
    errors: list[dict[str, str]] = []
    snapshot_path = HERE / "release_registry_snapshots" / f"{RELEASE_ID}.json"
    try:
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, [error("PAIRWISE_RELEASE_SNAPSHOT_INVALID", str(exc))]
    releases = snapshot.get("releases") if isinstance(snapshot, dict) else None
    release = next(
        (item for item in releases or [] if isinstance(item, dict) and item.get("release_id") == RELEASE_ID),
        None,
    )
    if not isinstance(release, dict):
        return None, [error("PAIRWISE_RELEASE_SNAPSHOT_INVALID", "exact 1.3 release is missing")]
    tck = report.get("pairwise_tck_release")
    expected_tck = {
        "release_id": RELEASE_ID,
        "registry_digest": sha256_file(snapshot_path),
        "runner_bundle_digest": release.get("runner_bundle", {}).get("digest"),
        "report_schema_digest": release.get("report_schema", {}).get("content_digest"),
        "evaluator_digest": release.get("evaluator", {}).get("content_digest"),
        "normalizer_digest": release.get("normalizer", {}).get("content_digest"),
    }
    if tck != expected_tck:
        errors.append(error("PAIRWISE_TCK_PROVENANCE_INVALID", "report does not bind the exact Pairwise 1.3 release"))
    for field in (
        "registry_schema", "runner_bundle", "evaluator_bundle", "side_authority_bundle",
        "report_schema", "evaluator", "normalizer",
    ):
        errors.extend(validate_artifact(release.get(field), label=field))
    for field in ("target_registry", "scenario_catalog"):
        reference = release.get(field)
        errors.extend(validate_artifact(reference, label=field))
        if isinstance(reference, dict):
            errors.extend(
                validate_artifact(
                    {"path": reference.get("schema_path"), "content_digest": reference.get("schema_digest")},
                    label=f"{field} schema",
                )
            )
    for index, reference in enumerate(release.get("underlying_authorities", [])):
        errors.extend(validate_artifact(reference, label=f"underlying authority {index}"))
    for bundle_field in ("runner_bundle", "evaluator_bundle", "side_authority_bundle"):
        bundle_ref = release.get(bundle_field, {})
        try:
            bundle_path = safe_path(HERE.parents[1], bundle_ref["path"])
            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
            for index, entry in enumerate(bundle.get("entries", [])):
                errors.extend(validate_artifact(entry, label=f"{bundle_field} entry {index}"))
        except (KeyError, OSError, json.JSONDecodeError, ValueError) as exc:
            errors.append(error("PAIRWISE_RELEASE_BUNDLE_INVALID", f"{bundle_field}: {exc}"))
    registry_ref = release.get("registry_schema", {})
    try:
        registry_path = safe_path(HERE.parents[1], registry_ref["path"])
        errors.extend(schema_errors(snapshot, registry_path))
    except (KeyError, OSError, ValueError) as exc:
        errors.append(error("PAIRWISE_RELEASE_SCHEMA_INVALID", str(exc)))
    return release, errors


def participant_identity(item: dict[str, Any]) -> dict[str, str]:
    return {
        "kind": item.get("implementation_kind"),
        "implementation_id": item.get("implementation_id"),
        "implementation_version": item.get("implementation_version"),
        "implementation_digest": item.get("implementation_digest"),
    }  # type: ignore[return-value]


def descriptor_identity(item: dict[str, Any]) -> dict[str, str]:
    return {
        "kind": item.get("implementation_kind"),
        "implementation_id": item.get("implementation_id"),
        "implementation_version": item.get("implementation_version"),
        "implementation_digest": item.get("implementation_digest"),
    }  # type: ignore[return-value]


ROLE_DESCRIPTOR_FIELDS = {
    "protocol",
    "side",
    "role",
    "target_id",
    "implementation_kind",
    "implementation_id",
    "implementation_version",
    "implementation_digest",
    "transport",
}


def _descriptor_errors(
    descriptor: Any,
    *,
    side: str,
    role: str,
    identity: dict[str, str],
    label: str,
) -> list[dict[str, str]]:
    if not isinstance(descriptor, dict) or set(descriptor) != ROLE_DESCRIPTOR_FIELDS:
        return [error("PAIRWISE_RAW_ROLE_DESCRIPTOR_INVALID", f"{label} has the wrong strict shape")]
    if (
        descriptor.get("protocol") != ROLE_DESCRIPTOR_VERSION
        or descriptor.get("side") != side
        or descriptor.get("role") != role
        or descriptor.get("target_id") != TARGET_ID
        or descriptor.get("transport") != "stdio"
        or descriptor_identity(descriptor) != identity
    ):
        return [error("PAIRWISE_RAW_ROLE_DESCRIPTOR_MISMATCH", f"{label} contradicts side {side} evidence")]
    return []


def _run_role_instances(report: dict[str, Any]) -> tuple[dict[str, dict[str, dict[str, str]]], list[dict[str, str]]]:
    mapped: dict[str, dict[str, dict[str, str]]] = {}
    errors: list[dict[str, str]] = []
    for run in report.get("runs", []) if isinstance(report.get("runs"), list) else []:
        if not isinstance(run, dict) or not isinstance(run.get("run_id"), str) or not run["run_id"]:
            errors.append(error("PAIRWISE_RAW_ROLE_RUN_INVALID", "every clean run needs a non-empty run ID"))
            continue
        run_id = run["run_id"]
        if run_id in mapped:
            errors.append(error("PAIRWISE_RAW_ROLE_RUN_DUPLICATE", run_id))
            continue
        instances = run.get("role_instances")
        if not isinstance(instances, list) or len(instances) != 2:
            errors.append(error("PAIRWISE_ROLE_INSTANCES_INVALID", run_id))
            continue
        by_side: dict[str, dict[str, str]] = {}
        for item in instances:
            if not isinstance(item, dict) or set(item) != {
                "side", "client_process_instance_id", "server_process_instance_id"
            }:
                errors.append(error("PAIRWISE_ROLE_INSTANCES_INVALID", run_id))
                continue
            side = item.get("side")
            client_id = item.get("client_process_instance_id")
            server_id = item.get("server_process_instance_id")
            if side not in {"A", "B"} or side in by_side or not all(
                isinstance(value, str) and value for value in (client_id, server_id)
            ):
                errors.append(error("PAIRWISE_ROLE_INSTANCES_INVALID", run_id))
                continue
            by_side[side] = {"client": client_id, "server": server_id}
        if set(by_side) != {"A", "B"}:
            errors.append(error("PAIRWISE_ROLE_INSTANCES_INVALID", run_id))
        mapped[run_id] = by_side
    return mapped, errors


def validate_raw_role_evidence(report: dict[str, Any]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    roles_by_run, run_errors = _run_role_instances(report)
    errors.extend(run_errors)
    expected_run_ids = set(roles_by_run)
    if len(expected_run_ids) != 2:
        errors.append(error("PAIRWISE_RAW_ROLE_RUN_CARDINALITY_INVALID", "exactly two clean run IDs are required"))
    participants = {
        item.get("side"): item
        for item in report.get("participants", [])
        if isinstance(item, dict) and item.get("side") in {"A", "B"}
    }
    if set(participants) != {"A", "B"}:
        return errors + [error("PAIRWISE_PARTICIPANTS_INVALID", "exactly sides A and B are required")]

    seen_processes: set[str] = set()
    for side in ("A", "B"):
        participant = participants[side]
        identity = participant_identity(participant)
        derived: dict[str, dict[str, Any]] = {}
        for role in ("client", "server"):
            evidence = participant.get(f"{role}_descriptor_evidence")
            if not isinstance(evidence, dict) or set(evidence) != {"descriptor", "runs"}:
                errors.append(error("PAIRWISE_RAW_ROLE_EVIDENCE_INVALID", f"side {side} {role} evidence shape"))
                continue
            records = evidence.get("runs")
            if not isinstance(records, list) or len(records) != 2:
                errors.append(error("PAIRWISE_RAW_ROLE_CARDINALITY_INVALID", f"side {side} {role} requires two records"))
                continue
            by_run: dict[str, dict[str, Any]] = {}
            for record in records:
                expected_fields = (
                    {"run_id", "process_instance_id", "global_event_sequence", "request", "response"}
                    if role == "client"
                    else {"run_id", "process_instance_id", "descriptor"}
                )
                if not isinstance(record, dict) or set(record) != expected_fields:
                    errors.append(error("PAIRWISE_RAW_ROLE_RECORD_INVALID", f"side {side} {role} record shape"))
                    continue
                run_id = record.get("run_id")
                process_id = record.get("process_instance_id")
                if run_id not in expected_run_ids or run_id in by_run:
                    errors.append(error("PAIRWISE_RAW_ROLE_RUN_MAPPING_INVALID", f"side {side} {role} {run_id}"))
                    continue
                expected_process = roles_by_run.get(run_id, {}).get(side, {}).get(role)
                if not isinstance(process_id, str) or process_id != expected_process or process_id in seen_processes:
                    errors.append(error("PAIRWISE_RAW_ROLE_PROCESS_MAPPING_INVALID", f"side {side} {role} {run_id}"))
                else:
                    seen_processes.add(process_id)
                if role == "client":
                    request = record.get("request")
                    response = record.get("response")
                    if (
                        not isinstance(record.get("global_event_sequence"), int)
                        or record["global_event_sequence"] < 1
                        or not isinstance(request, dict)
                        or set(request) != {"control_version", "request_id", "operation"}
                        or request.get("control_version") != CLIENT_CONTROL_VERSION
                        or not isinstance(request.get("request_id"), str)
                        or not request["request_id"]
                        or request.get("operation") != "describe"
                        or not isinstance(response, dict)
                        or set(response) != {"control_version", "request_id", "operation", "success", "result"}
                        or response.get("control_version") != CLIENT_CONTROL_VERSION
                        or response.get("request_id") != request.get("request_id")
                        or response.get("operation") != "describe"
                        or response.get("success") is not True
                    ):
                        errors.append(error("PAIRWISE_RAW_CLIENT_DESCRIBE_INVALID", f"side {side} {run_id}"))
                    descriptor = response.get("result") if isinstance(response, dict) else None
                else:
                    descriptor = record.get("descriptor")
                errors.extend(
                    _descriptor_errors(
                        descriptor,
                        side=side,
                        role=role,
                        identity=identity,
                        label=f"side {side} {role} raw descriptor for {run_id}",
                    )
                )
                if isinstance(descriptor, dict):
                    by_run[str(run_id)] = descriptor
            if set(by_run) != expected_run_ids:
                errors.append(error("PAIRWISE_RAW_ROLE_RUN_MAPPING_INVALID", f"side {side} {role} run set"))
            descriptors = list(by_run.values())
            if descriptors and any(item != descriptors[0] for item in descriptors[1:]):
                errors.append(error("PAIRWISE_RAW_ROLE_CHANGED_BETWEEN_RUNS", f"side {side} {role}"))
            summary = evidence.get("descriptor")
            errors.extend(
                _descriptor_errors(
                    summary,
                    side=side,
                    role=role,
                    identity=identity,
                    label=f"side {side} {role} summary",
                )
            )
            if descriptors and summary != descriptors[0]:
                errors.append(error("PAIRWISE_ROLE_SUMMARY_NOT_DERIVED", f"side {side} {role}"))
            if descriptors:
                derived[role] = descriptors[0]
        if set(derived) == {"client", "server"}:
            expected_server = {**derived["client"], "role": "server"}
            if derived["server"] != expected_server:
                errors.append(error("PAIRWISE_CLIENT_SERVER_BUILD_MISMATCH", f"side {side} raw roles differ"))
    return errors


def evaluate_side_reports(report: dict[str, Any], *, base_dir: Path) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    errors.extend(validate_raw_role_evidence(report))
    participants = report.get("participants", [])
    by_side = {item.get("side"): item for item in participants if isinstance(item, dict)}
    if set(by_side) != {"A", "B"}:
        return [error("PAIRWISE_PARTICIPANTS_INVALID", "exactly sides A and B are required")]
    identities = {side: participant_identity(by_side[side]) for side in ("A", "B")}
    if identities["A"]["implementation_id"] == identities["B"]["implementation_id"]:
        errors.append(error("PAIRWISE_IDENTITIES_NOT_DISTINCT", "participant IDs must differ"))
    if identities["A"]["implementation_digest"] == identities["B"]["implementation_digest"]:
        errors.append(error("PAIRWISE_BUILDS_NOT_DISTINCT", "participant build digests must differ"))
    for side in ("A", "B"):
        participant = by_side[side]
        for kind in ("profile", "binding"):
            reference = participant.get(f"{kind}_report")
            try:
                path = safe_path(base_dir, reference["path"])
                if sha256_file(path) != reference.get("content_digest"):
                    raise ValueError("content digest differs")
                side_report = json.loads(path.read_text(encoding="utf-8"))
                side_errors = evaluate_side_report(side_report, kind=kind, identity=identities[side])
                if side_errors:
                    errors.append(error(f"PAIRWISE_{kind.upper()}_REPORT_INELIGIBLE", "; ".join(side_errors)))
            except (KeyError, OSError, json.JSONDecodeError, ValueError, RuntimeError) as exc:
                errors.append(error(f"PAIRWISE_{kind.upper()}_REPORT_INVALID", f"side {side}: {exc}"))
        for role in ("client", "server"):
            evidence = participant.get(f"{role}_descriptor_evidence", {})
            descriptor = evidence.get("descriptor", {}) if isinstance(evidence, dict) else {}
            if (
                not isinstance(descriptor, dict)
                or descriptor.get("protocol") != ROLE_DESCRIPTOR_VERSION
                or descriptor.get("side") != side
                or descriptor.get("role") != role
                or descriptor.get("target_id") != TARGET_ID
                or descriptor.get("transport") != "stdio"
                or descriptor_identity(descriptor) != identities[side]
            ):
                errors.append(error("PAIRWISE_ROLE_DESCRIPTOR_MISMATCH", f"side {side} {role} descriptor does not match reports"))
        client_descriptor = participant.get("client_descriptor_evidence", {}).get("descriptor", {})
        server_descriptor = participant.get("server_descriptor_evidence", {}).get("descriptor", {})
        if descriptor_identity(client_descriptor) != descriptor_identity(server_descriptor):
            errors.append(error("PAIRWISE_CLIENT_SERVER_BUILD_MISMATCH", f"side {side} client/server builds differ"))
    side_evidence = report.get("side_evidence")
    expected_side_evidence = [
        {
            "side": side,
            "profile_report": by_side[side].get("profile_report"),
            "binding_report": by_side[side].get("binding_report"),
        }
        for side in ("A", "B")
    ]
    if side_evidence != expected_side_evidence:
        errors.append(error("PAIRWISE_SIDE_EVIDENCE_MISMATCH", "side_evidence must exactly mirror participants"))
    return errors


def _contains(value: Any, needle: str) -> bool:
    if isinstance(value, dict):
        return any(_contains(item, needle) for item in value.values())
    if isinstance(value, list):
        return any(_contains(item, needle) for item in value)
    if isinstance(value, str):
        if value == needle:
            return True
        if value[:1] in {"{", "["}:
            try:
                return _contains(json.loads(value), needle)
            except json.JSONDecodeError:
                return False
    return False


def _has_key(value: Any, forbidden: set[str]) -> bool:
    if isinstance(value, dict):
        return any(key in forbidden or _has_key(item, forbidden) for key, item in value.items())
    if isinstance(value, list):
        return any(_has_key(item, forbidden) for item in value)
    return False


def _exchange_by_phase(direction: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        item.get("phase"): item
        for item in direction.get("exchanges", [])
        if isinstance(item, dict) and isinstance(item.get("phase"), str)
    }


MESSAGE_PHASES = {"propose", "accept", "attest"}
POLL_PHASES = {"poll_proposal", "poll_acceptance", "poll_attestation"}


def _strict_client_event_errors(event: Any, *, direction: str) -> list[dict[str, str]]:
    if not isinstance(event, dict) or set(event) != {
        "sequence",
        "global_event_sequence",
        "client_side",
        "client_process_instance_id",
        "request",
        "response",
    }:
        return [error("PAIRWISE_CLIENT_EVENT_SHAPE_INVALID", direction)]
    request = event.get("request")
    response = event.get("response")
    if (
        not isinstance(request, dict)
        or set(request) != {"control_version", "request_id", "operation", "input"}
        or request.get("control_version") != CLIENT_CONTROL_VERSION
        or not isinstance(request.get("request_id"), str)
        or not request["request_id"]
        or request.get("operation") not in {"begin_phase", "mcp_response"}
        or not isinstance(request.get("input"), dict)
        or not isinstance(response, dict)
        or set(response) != {"control_version", "request_id", "operation", "success", "result"}
        or response.get("control_version") != CLIENT_CONTROL_VERSION
        or response.get("request_id") != request.get("request_id")
        or response.get("operation") != request.get("operation")
        or response.get("success") is not True
        or not isinstance(response.get("result"), dict)
    ):
        return [error("PAIRWISE_CLIENT_CONTROL_INVALID", direction)]
    input_value = request["input"]
    result = response["result"]
    phase = input_value.get("phase")
    if phase not in MESSAGE_PHASES | POLL_PHASES:
        return [error("PAIRWISE_CLIENT_PHASE_INVALID", direction)]
    if request["operation"] == "begin_phase":
        allowed = {
            "phase", "side", "run_id", "direction", "session_id", "contract_id", "destination_side"
        }
        if phase in MESSAGE_PHASES:
            allowed |= {"message_id", "timestamp"}
        if phase == "propose":
            allowed.add("challenge")
        expected_result = {
            "event", "phase", "exchange_id", "destination_side", "request", "request_json",
            "client_visible_hashes_before",
        }
        if set(input_value) != allowed or set(result) != expected_result:
            return [error("PAIRWISE_CLIENT_CONTROL_SHAPE_INVALID", f"{direction} {phase} begin_phase")]
        if (
            result.get("event") != "mcp_request"
            or result.get("phase") != phase
            or not isinstance(result.get("exchange_id"), str)
            or not result["exchange_id"]
            or not isinstance(result.get("request"), dict)
            or not isinstance(result.get("request_json"), str)
            or not isinstance(result.get("client_visible_hashes_before"), list)
        ):
            return [error("PAIRWISE_CLIENT_CONTROL_SHAPE_INVALID", f"{direction} {phase} request event")]
    else:
        allowed = {"phase", "side", "run_id", "direction", "exchange_id", "source_side", "response_json"}
        expected_result = (
            {"event", "phase", "message"}
            if phase in MESSAGE_PHASES
            else {
                "event", "phase", "observed_message", "client_visible_hashes_before",
                "client_visible_hashes_after",
            }
        )
        if set(input_value) != allowed or set(result) != expected_result:
            return [error("PAIRWISE_CLIENT_CONTROL_SHAPE_INVALID", f"{direction} {phase} mcp_response")]
        if result.get("event") != "phase_complete" or result.get("phase") != phase:
            return [error("PAIRWISE_CLIENT_CONTROL_SHAPE_INVALID", f"{direction} {phase} completion")]
    return []


def validate_direction(
    direction: dict[str, Any],
    *,
    run_id: str,
    role_instances: dict[str, dict[str, str]],
) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    name = direction.get("direction")
    producer, consumer = (("A", "B") if name == "A_TO_B" else ("B", "A"))
    if direction.get("producer_side") != producer or direction.get("consumer_side") != consumer:
        errors.append(error("PAIRWISE_DIRECTION_ROLE_INVALID", str(name)))
    challenge = direction.get("challenge")
    session = direction.get("session_id")
    contract = direction.get("contract_id")
    messages = direction.get("messages", [])
    if len(messages) != 3:
        return [error("PAIRWISE_MESSAGE_FLOW_INVALID", f"{name} requires three messages")]
    envelopes = [item.get("message", {}) for item in messages]
    if [item.get("message_type") for item in envelopes] != ["CONTRACT_PROPOSE", "CONTRACT_ACCEPT", "ATTEST_ACTION"]:
        errors.append(error("PAIRWISE_MESSAGE_FLOW_INVALID", str(name)))
    expected_sides = [(producer, consumer), (consumer, producer), (producer, consumer)]
    for index, item in enumerate(messages):
        sender, recipient = expected_sides[index]
        if (
            item.get("sequence") != index + 1
            or item.get("sender_side") != sender
            or item.get("constructed_by") != sender
            or item.get("consumed_by") != recipient
        ):
            errors.append(error("PAIRWISE_MESSAGE_ROLE_INVALID", f"{name} sequence {index + 1}"))
        envelope = item.get("message", {})
        if envelope.get("session_id") != session or envelope.get("contract_id") != contract:
            errors.append(error("PAIRWISE_MESSAGE_SCOPE_INVALID", f"{name} sequence {index + 1}"))
    core_errors = validate_core_transcript(envelopes)
    if core_errors:
        errors.append(error("PAIRWISE_CORE_TRANSCRIPT_INVALID", json.dumps(core_errors, sort_keys=True)))
    proposal, acceptance, attestation = envelopes
    if proposal.get("payload", {}).get("contract", {}).get("goal") != challenge:
        errors.append(error("PAIRWISE_PROPOSAL_CHALLENGE_INVALID", str(name)))
    if acceptance.get("prev_msg_hash") != proposal.get("message_hash"):
        errors.append(error("PAIRWISE_ACCEPTANCE_CAUSALITY_INVALID", str(name)))
    if attestation.get("prev_msg_hash") != acceptance.get("message_hash"):
        errors.append(error("PAIRWISE_ATTESTATION_CAUSALITY_INVALID", str(name)))
    expected_result = frozen_hash("result", {"peer_hash": acceptance.get("message_hash")}).get("object_hash")
    if attestation.get("payload", {}).get("result_hash") != expected_result:
        errors.append(error("PAIRWISE_ATTESTATION_RESULT_BINDING_INVALID", str(name)))

    expected_flow = [
        ("propose", "aicp.sendMessage", producer, consumer, proposal),
        ("poll_proposal", "aicp.pollMessages", consumer, consumer, proposal),
        ("accept", "aicp.sendMessage", consumer, producer, acceptance),
        ("poll_acceptance", "aicp.pollMessages", producer, producer, acceptance),
        ("attest", "aicp.sendMessage", producer, consumer, attestation),
        ("poll_attestation", "aicp.pollMessages", consumer, consumer, attestation),
    ]
    exchanges = direction.get("exchanges", [])
    if len(exchanges) != 6:
        errors.append(error("PAIRWISE_MANDATORY_EXCHANGE_MISSING", str(name)))
    by_phase = _exchange_by_phase(direction)
    expected_cursor = {"A": "c0", "B": "c0"}
    for sequence, (phase, operation, client_side, server_side, message) in enumerate(expected_flow, start=1):
        exchange = by_phase.get(phase)
        if not isinstance(exchange, dict):
            errors.append(error("PAIRWISE_MANDATORY_EXCHANGE_MISSING", f"{name} {phase}"))
            continue
        client_instance = role_instances.get(client_side, {}).get("client")
        server_instance = role_instances.get(server_side, {}).get("server")
        if (
            exchange.get("sequence") != sequence
            or not isinstance(exchange.get("global_exchange_sequence"), int)
            or exchange["global_exchange_sequence"] < 1
            or exchange.get("operation") != operation
            or exchange.get("originating_client_side") != client_side
            or exchange.get("destination_server_side") != server_side
            or exchange.get("client_process_instance_id") != client_instance
            or exchange.get("server_process_instance_id") != server_instance
        ):
            errors.append(error("PAIRWISE_ROLE_ROUTING_INVALID", f"{name} {phase}"))
        if exchange.get("request_origin") != "participant_client" or exchange.get("response_origin") != "participant_server":
            errors.append(error("PAIRWISE_TRANSPORT_ORIGIN_INVALID", f"{name} {phase}"))
        try:
            client_request = exchange["client_request"]
            request = exchange["request"]
            response = exchange["response"]
            delivered = exchange["client_delivered_response"]
            request_json = exchange["request_json"]
            response_json = exchange["response_json"]
            if (
                json.loads(request_json) != client_request
                or request != client_request
                or exchange.get("forwarded_request_json") != request_json
                or json.loads(response_json) != response
                or delivered != response
                or exchange.get("delivered_response_json") != response_json
                or sha256_bytes(request_json.encode("utf-8")) != exchange.get("request_byte_digest")
                or sha256_bytes(response_json.encode("utf-8")) != exchange.get("response_byte_digest")
            ):
                errors.append(error("PAIRWISE_RELAY_NOT_TRANSPARENT", f"{name} {phase}"))
            if request.get("jsonrpc") != "2.0" or request.get("method") != "tools/call" or request.get("id") != response.get("id"):
                errors.append(error("PAIRWISE_MCP_CORRELATION_INVALID", f"{name} {phase}"))
            if request.get("params", {}).get("name") != operation or "error" in response:
                errors.append(error("PAIRWISE_MCP_OPERATION_INVALID", f"{name} {phase}"))
            if operation == "aicp.sendMessage":
                if request.get("params", {}).get("arguments", {}).get("message") != message:
                    errors.append(error("PAIRWISE_CLIENT_MESSAGE_MISMATCH", f"{name} {phase}"))
                if response.get("result", {}).get("accepted") is not True or response.get("result", {}).get("message_hash") != message.get("message_hash"):
                    errors.append(error("PAIRWISE_SERVER_ACCEPTANCE_INVALID", f"{name} {phase}"))
            else:
                arguments = request.get("params", {}).get("arguments", {})
                response_result = response.get("result", {})
                polled = response_result.get("messages")
                next_cursor = response_result.get("next_cursor")
                if (
                    not isinstance(arguments, dict)
                    or set(arguments) != {"session_id", "after_cursor", "limit"}
                    or arguments.get("session_id") != session
                    or arguments.get("limit") != 1
                    or arguments.get("after_cursor") != expected_cursor[client_side]
                    or not isinstance(response_result, dict)
                    or set(response_result) != {"messages", "next_cursor"}
                    or not isinstance(polled, list)
                    or polled != [message]
                    or not isinstance(next_cursor, str)
                    or not next_cursor
                    or next_cursor == arguments.get("after_cursor")
                ):
                    errors.append(error("PAIRWISE_CLIENT_POLL_RESULT_INVALID", f"{name} {phase}"))
                if isinstance(next_cursor, str) and next_cursor:
                    expected_cursor[client_side] = next_cursor
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            errors.append(error("PAIRWISE_EXCHANGE_EVIDENCE_INVALID", f"{name} {phase}: {exc}"))

    events = direction.get("client_events", [])
    if len(events) != 12 or [item.get("sequence") for item in events] != list(range(1, 13)):
        errors.append(error("PAIRWISE_CLIENT_EVENT_SEQUENCE_INVALID", str(name)))
    for event in events:
        errors.extend(_strict_client_event_errors(event, direction=str(name)))
        side = event.get("client_side")
        if event.get("client_process_instance_id") != role_instances.get(side, {}).get("client"):
            errors.append(error("PAIRWISE_CLIENT_EVENT_PROCESS_INVALID", str(name)))
        request = event.get("request", {})
        response = event.get("response", {})
        if (
            request.get("control_version") != CLIENT_CONTROL_VERSION
            or response.get("control_version") != CLIENT_CONTROL_VERSION
            or request.get("request_id") != response.get("request_id")
            or request.get("operation") != response.get("operation")
            or response.get("success") is not True
        ):
            errors.append(error("PAIRWISE_CLIENT_CONTROL_INVALID", str(name)))

    phase_events: dict[tuple[str, str], list[tuple[int, dict[str, Any]]]] = {}
    for index, event in enumerate(events):
        request = event.get("request", {})
        result = event.get("response", {}).get("result", {})
        phase = request.get("input", {}).get("phase") or result.get("phase")
        phase_events.setdefault((str(event.get("client_side")), str(phase)), []).append((index, event))
    for phase, _, client_side, server_side, _ in expected_flow:
        exchange = by_phase.get(phase, {})
        candidates = phase_events.get((client_side, phase), [])
        begin_events = [
            item for _, item in candidates
            if item.get("request", {}).get("operation") == "begin_phase"
        ]
        response_events = [
            item for _, item in candidates
            if item.get("request", {}).get("operation") == "mcp_response"
        ]
        if len(begin_events) != 1 or len(response_events) != 1:
            errors.append(error("PAIRWISE_CLIENT_EXCHANGE_LINK_INVALID", f"{name} {phase} event cardinality"))
            continue
        begin = begin_events[0]
        completion = response_events[0]
        begin_input = begin.get("request", {}).get("input", {})
        begin_result = begin.get("response", {}).get("result", {})
        response_input = completion.get("request", {}).get("input", {})
        completion_result = completion.get("response", {}).get("result", {})
        expected_scope = {
            "phase": phase,
            "side": client_side,
            "run_id": run_id,
            "direction": name,
            "session_id": session,
            "contract_id": contract,
            "destination_side": server_side,
        }
        if any(begin_input.get(field) != value for field, value in expected_scope.items()):
            errors.append(error("PAIRWISE_CLIENT_CONTROL_SCOPE_INVALID", f"{name} {phase}"))
        if _has_key(begin_input, {"peer_message", "peer_hash", "preseed_peer_message", "preseed_peer_hash"}):
            errors.append(error("PAIRWISE_HARNESS_PEER_INJECTION", f"{name} {phase}"))
        if (
            begin_result.get("event") != "mcp_request"
            or begin_result.get("phase") != phase
            or begin_result.get("destination_side") != server_side
            or begin_result.get("request") != exchange.get("client_request")
            or begin_result.get("request_json") != exchange.get("request_json")
            or response_input.get("phase") != phase
            or response_input.get("side") != client_side
            or response_input.get("run_id") != run_id
            or response_input.get("direction") != name
            or response_input.get("source_side") != server_side
            or response_input.get("response_json") != exchange.get("delivered_response_json")
            or response_input.get("exchange_id") != begin_result.get("exchange_id")
            or completion_result.get("event") != "phase_complete"
            or completion_result.get("phase") != phase
        ):
            errors.append(error("PAIRWISE_CLIENT_EXCHANGE_LINK_INVALID", f"{name} {phase}"))
        if phase != "propose" and "challenge" in begin_input:
            errors.append(error("PAIRWISE_CONSUMER_CHALLENGE_PRESEEDED", f"{name} {phase}"))
    for poll_phase, client_side, message in (
        ("poll_proposal", consumer, proposal),
        ("poll_acceptance", producer, acceptance),
        ("poll_attestation", consumer, attestation),
    ):
        candidates = phase_events.get((client_side, poll_phase), [])
        response_event = next(
            (item for item in candidates if item[1].get("request", {}).get("operation") == "mcp_response"),
            None,
        )
        if response_event is None or not _contains(
            response_event[1].get("request", {}).get("input", {}),
            message.get("message_hash"),
        ):
            errors.append(error("PAIRWISE_CLIENT_FIRST_SEEN_INVALID", f"{name} {poll_phase}"))
    for phase, client_side, peer_hash in (
        ("accept", consumer, proposal.get("message_hash")),
        ("attest", producer, acceptance.get("message_hash")),
    ):
        begin = next(
            (
                item
                for _, item in phase_events.get((client_side, phase), [])
                if item.get("request", {}).get("operation") == "begin_phase"
            ),
            None,
        )
        if begin is None or _contains(begin.get("request", {}).get("input", {}), peer_hash):
            errors.append(error("PAIRWISE_HARNESS_PEER_INJECTION", f"{name} {phase}"))
    propose_begin = next(
        (
            item
            for _, item in phase_events.get((producer, "propose"), [])
            if item.get("request", {}).get("operation") == "begin_phase"
        ),
        None,
    )
    if propose_begin is None or propose_begin.get("request", {}).get("input", {}).get("challenge") != challenge:
        errors.append(error("PAIRWISE_PRODUCER_CHALLENGE_INPUT_INVALID", str(name)))
    return errors


def validate_run_global_chronology(
    report: dict[str, Any],
    run: dict[str, Any],
    *,
    role_instances: dict[str, dict[str, str]],
) -> list[dict[str, str]]:
    """Validate one causal ledger over each persistent client process in a run."""

    errors: list[dict[str, str]] = []
    run_id = run.get("run_id")
    timeline: list[dict[str, Any]] = []
    participants = {
        item.get("side"): item
        for item in report.get("participants", [])
        if isinstance(item, dict) and item.get("side") in {"A", "B"}
    }
    for side in ("A", "B"):
        records = participants.get(side, {}).get("client_descriptor_evidence", {}).get("runs", [])
        record = next(
            (item for item in records if isinstance(item, dict) and item.get("run_id") == run_id),
            None,
        )
        if isinstance(record, dict):
            timeline.append(
                {
                    "global_event_sequence": record.get("global_event_sequence"),
                    "client_side": side,
                    "client_process_instance_id": record.get("process_instance_id"),
                    "request": record.get("request"),
                    "response": record.get("response"),
                    "direction": "DESCRIBE",
                }
            )

    directions = run.get("directions", [])
    if [item.get("direction") for item in directions if isinstance(item, dict)] != ["A_TO_B", "B_TO_A"]:
        errors.append(error("PAIRWISE_DIRECTION_ORDER_INVALID", str(run_id)))
    all_exchanges: list[dict[str, Any]] = []
    for direction in directions:
        if not isinstance(direction, dict):
            continue
        for event in direction.get("client_events", []):
            if isinstance(event, dict):
                timeline.append({**event, "direction": direction.get("direction")})
        all_exchanges.extend(
            item for item in direction.get("exchanges", []) if isinstance(item, dict)
        )

    event_sequences = [item.get("global_event_sequence") for item in timeline]
    if sorted(event_sequences, key=lambda value: value if isinstance(value, int) else -1) != list(
        range(1, len(timeline) + 1)
    ):
        errors.append(error("PAIRWISE_GLOBAL_EVENT_SEQUENCE_INVALID", str(run_id)))
    exchange_sequences = [item.get("global_exchange_sequence") for item in all_exchanges]
    if sorted(exchange_sequences, key=lambda value: value if isinstance(value, int) else -1) != list(
        range(1, len(all_exchanges) + 1)
    ):
        errors.append(error("PAIRWISE_GLOBAL_EXCHANGE_SEQUENCE_INVALID", str(run_id)))

    ordered = sorted(
        timeline,
        key=lambda item: item.get("global_event_sequence")
        if isinstance(item.get("global_event_sequence"), int)
        else -1,
    )
    ledgers: dict[str, list[dict[str, Any]]] = {
        role_instances[side]["client"]: []
        for side in ("A", "B")
        if side in role_instances and isinstance(role_instances[side].get("client"), str)
    }
    for event in ordered:
        process_id = event.get("client_process_instance_id")
        if process_id in ledgers:
            ledgers[process_id].append(event)

    visible: dict[str, list[str]] = {process_id: [] for process_id in ledgers}
    for direction in directions:
        if not isinstance(direction, dict):
            continue
        name = direction.get("direction")
        producer, consumer = (("A", "B") if name == "A_TO_B" else ("B", "A"))
        message_items = direction.get("messages", [])
        messages = [item.get("message", {}) for item in message_items]
        if len(messages) != 3:
            continue
        proposal, acceptance, attestation = messages
        challenge = direction.get("challenge")
        for message_index, (poll_phase, side, message) in enumerate(
            (
                ("poll_proposal", consumer, proposal),
                ("poll_acceptance", producer, acceptance),
                ("poll_attestation", consumer, attestation),
            )
        ):
            process_id = role_instances.get(side, {}).get("client")
            ledger = ledgers.get(str(process_id), [])
            current_index = next(
                (
                    index
                    for index, event in enumerate(ledger)
                    if event.get("direction") == name
                    and event.get("request", {}).get("operation") == "mcp_response"
                    and event.get("request", {}).get("input", {}).get("phase") == poll_phase
                ),
                None,
            )
            digest = message.get("message_hash")
            if current_index is None or not isinstance(digest, str):
                errors.append(error("PAIRWISE_CLIENT_FIRST_SEEN_INVALID", f"{name} {poll_phase}"))
                continue
            earlier = ledger[:current_index]
            if any(
                _contains(prior.get("request", {}).get("input", {}), digest)
                or _contains(prior.get("response", {}).get("result", {}), digest)
                for prior in earlier
            ):
                errors.append(error("PAIRWISE_CLIENT_ARTIFACT_PRESEEDED", f"{name} {poll_phase}"))
            if poll_phase == "poll_proposal" and isinstance(challenge, str) and any(
                _contains(prior.get("request", {}).get("input", {}), challenge)
                or _contains(prior.get("response", {}).get("result", {}), challenge)
                for prior in earlier
            ):
                errors.append(error("PAIRWISE_CONSUMER_CHALLENGE_PRESEEDED", str(name)))
            current = ledger[current_index]
            if not _contains(current.get("request", {}).get("input", {}), digest):
                errors.append(error("PAIRWISE_CLIENT_FIRST_SEEN_INVALID", f"{name} {poll_phase}"))
            evidence = message_items[message_index]
            before = list(visible.get(str(process_id), []))
            after = before + [digest]
            result = current.get("response", {}).get("result", {})
            if (
                evidence.get("client_visible_hashes_before") != before
                or evidence.get("client_visible_hashes_after") != after
                or result.get("client_visible_hashes_before") != before
                or result.get("client_visible_hashes_after") != after
                or result.get("observed_message") != message
            ):
                errors.append(error("PAIRWISE_CLIENT_VISIBLE_SET_INVALID", f"{name} {poll_phase}"))
            visible[str(process_id)] = after
    return errors


def validate_runs(report: dict[str, Any]) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
    runs = report.get("runs", [])
    if len(runs) != 2:
        return [error("PAIRWISE_RUN_COUNT_INVALID", "exactly two clean runs are required")]
    participants = {item.get("side"): item for item in report.get("participants", [])}
    seen: dict[str, set[str]] = {
        "run": set(), "challenge": set(), "session": set(), "contract": set(),
        "message": set(), "rpc": set(), "process": set(),
    }
    digests: list[str] = []
    for run in runs:
        run_id = run.get("run_id")
        if run_id in seen["run"]:
            errors.append(error("PAIRWISE_RUN_REPLAY", str(run_id)))
        seen["run"].add(run_id)
        role_instances: dict[str, dict[str, str]] = {}
        for item in run.get("role_instances", []):
            side = item.get("side")
            client_id = item.get("client_process_instance_id")
            server_id = item.get("server_process_instance_id")
            role_instances[side] = {"client": client_id, "server": server_id}
            for process_id in (client_id, server_id):
                if process_id in seen["process"]:
                    errors.append(error("PAIRWISE_PROCESS_INSTANCE_REPLAY", str(process_id)))
                seen["process"].add(process_id)
            participant = participants.get(side, {})
            client_runs = participant.get("client_descriptor_evidence", {}).get("runs", [])
            server_runs = participant.get("server_descriptor_evidence", {}).get("runs", [])
            if not any(value.get("run_id") == run_id and value.get("process_instance_id") == client_id for value in client_runs):
                errors.append(error("PAIRWISE_CLIENT_PROCESS_UNBOUND", f"{run_id} {side}"))
            if not any(value.get("run_id") == run_id and value.get("process_instance_id") == server_id for value in server_runs):
                errors.append(error("PAIRWISE_SERVER_PROCESS_UNBOUND", f"{run_id} {side}"))
        if set(role_instances) != {"A", "B"}:
            errors.append(error("PAIRWISE_ROLE_INSTANCES_INVALID", str(run_id)))
        directions = {item.get("direction"): item for item in run.get("directions", [])}
        if set(directions) != {"A_TO_B", "B_TO_A"}:
            errors.append(error("PAIRWISE_DIRECTIONS_INVALID", str(run_id)))
        for name in ("A_TO_B", "B_TO_A"):
            direction = directions.get(name)
            if not isinstance(direction, dict):
                continue
            errors.extend(validate_direction(direction, run_id=run_id, role_instances=role_instances))
            for key, field in (("challenge", "challenge"), ("session", "session_id"), ("contract", "contract_id")):
                value = direction.get(field)
                if value in seen[key]:
                    errors.append(error(f"PAIRWISE_{key.upper()}_REPLAY", str(value)))
                seen[key].add(value)
            for message in direction.get("messages", []):
                message_id = message.get("message", {}).get("message_id")
                if message_id in seen["message"]:
                    errors.append(error("PAIRWISE_MESSAGE_ID_REPLAY", str(message_id)))
                seen["message"].add(message_id)
            for exchange in direction.get("exchanges", []):
                rpc_id = exchange.get("request", {}).get("id")
                if rpc_id in seen["rpc"]:
                    errors.append(error("PAIRWISE_JSONRPC_ID_REPLAY", str(rpc_id)))
                seen["rpc"].add(rpc_id)
        errors.extend(
            validate_run_global_chronology(report, run, role_instances=role_instances)
        )
        recomputed = semantic_digest(run)
        if run.get("semantic_digest") != recomputed:
            errors.append(error("PAIRWISE_SEMANTIC_DIGEST_INVALID", str(run_id)))
        digests.append(recomputed)
    if len(digests) == 2 and digests[0] != digests[1]:
        errors.append(error("PAIRWISE_CLEAN_RUN_SEMANTICS_DIFFER", "normalized role semantics differ"))
    return errors


def evaluate_pairwise_report(report: dict[str, Any], *, base_dir: Path) -> dict[str, Any]:
    release, release_errors = load_release_errors(report)
    if release is None:
        return {"status": "rejected", "errors": release_errors, "eligible_pairwise_relations": [], "eligible_marks": []}
    schema_path = safe_path(HERE.parents[1], release["report_schema"]["path"])
    errors = schema_errors(report, schema_path)
    errors.extend(release_errors)
    if (
        report.get("passed") is not True
        or report.get("failures") != []
        or report.get("degraded") is not False
        or report.get("degraded_reasons") != []
        or report.get("skipped_checks") != []
    ):
        errors.append(error("PAIRWISE_REPORT_NOT_CLEAN", "joint report must be clean and complete"))
    if report.get("compatibility_marks") != []:
        errors.append(error("PAIRWISE_MARKS_FORBIDDEN", "pairwise relations are not compatibility marks"))
    expected_target = release.get("target_registry", {}).get("content_digest")
    expected_scenario = release.get("scenario_catalog", {})
    if report.get("target") != {
        "profile_id": "AICP-BASE", "profile_version": "0.1", "binding_id": "BIND-MCP",
        "binding_version": "0.1", "target_catalog_digest": expected_target,
    }:
        errors.append(error("PAIRWISE_TARGET_INVALID", "exact Pairwise target is required"))
    if report.get("scenario") != {
        "scenario_id": SCENARIO_ID,
        "scenario_catalog_digest": expected_scenario.get("content_digest"),
        "scenario_schema_digest": expected_scenario.get("schema_digest"),
    }:
        errors.append(error("PAIRWISE_SCENARIO_INVALID", "exact role-bound scenario is required"))
    errors.extend(evaluate_side_reports(report, base_dir=base_dir))
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
        "joint_report_digest": sha256_bytes(canonical_bytes(report)),
    }
    return {"status": "eligible", "errors": [], "eligible_pairwise_relations": [relation], "eligible_marks": []}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("report")
    args = parser.parse_args()
    path = Path(args.report).resolve()
    try:
        result = evaluate_pairwise_report(json.loads(path.read_text(encoding="utf-8")), base_dir=path.parent)
    except Exception as exc:
        result = {
            "status": "rejected",
            "errors": [error("PAIRWISE_EVALUATOR_FAILURE", str(exc))],
            "eligible_pairwise_relations": [],
            "eligible_marks": [],
        }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "eligible" else 1


if __name__ == "__main__":
    raise SystemExit(main())
