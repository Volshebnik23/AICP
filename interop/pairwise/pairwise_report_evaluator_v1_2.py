#!/usr/bin/env python3
"""Independently evaluate Pairwise TCK 1.2 role-bound joint evidence."""

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
SCENARIO_ID = "PAIRWISE-MCP-ROLE-BOUND-CROSS-CONSUMPTION-02"
RELEASE_ID = "AICP-PAIRWISE-TCK-1.2.0"
CLIENT_CONTROL_VERSION = "aicp.pairwise_client_control.v1"
ROLE_DESCRIPTOR_VERSION = "aicp.pairwise_role_descriptor.v1"
TEXT_SUFFIXES = {".json", ".jsonl", ".md", ".py", ".ts", ".mjs", ".yml", ".yaml"}

from pairwise_semantic_normalizer_v1_2 import semantic_digest  # noqa: E402
from pairwise_side_report_evaluator_v1_1 import (  # noqa: E402
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
        return None, [error("PAIRWISE_RELEASE_SNAPSHOT_INVALID", "exact 1.2 release is missing")]
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
        errors.append(error("PAIRWISE_TCK_PROVENANCE_INVALID", "report does not bind the exact Pairwise 1.2 release"))
    for field in ("registry_schema", "runner_bundle", "evaluator_bundle", "report_schema", "evaluator", "normalizer"):
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
    for bundle_field in ("runner_bundle", "evaluator_bundle"):
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


def evaluate_side_reports(report: dict[str, Any], *, base_dir: Path) -> list[dict[str, str]]:
    errors: list[dict[str, str]] = []
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
    for sequence, (phase, operation, client_side, server_side, message) in enumerate(expected_flow, start=1):
        exchange = by_phase.get(phase)
        if not isinstance(exchange, dict):
            errors.append(error("PAIRWISE_MANDATORY_EXCHANGE_MISSING", f"{name} {phase}"))
            continue
        client_instance = role_instances.get(client_side, {}).get("client")
        server_instance = role_instances.get(server_side, {}).get("server")
        if (
            exchange.get("sequence") != sequence
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
                polled = response.get("result", {}).get("messages")
                if arguments.get("session_id") != session or not isinstance(polled, list) or polled != [message]:
                    errors.append(error("PAIRWISE_CLIENT_POLL_RESULT_INVALID", f"{name} {phase}"))
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
            errors.append(error("PAIRWISE_EXCHANGE_EVIDENCE_INVALID", f"{name} {phase}: {exc}"))

    events = direction.get("client_events", [])
    if len(events) != 12 or [item.get("sequence") for item in events] != list(range(1, 13)):
        errors.append(error("PAIRWISE_CLIENT_EVENT_SEQUENCE_INVALID", str(name)))
    for event in events:
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
    visible_by_client = {"A": [], "B": []}
    for message_index, (poll_phase, client_side, message) in enumerate(
        [
            ("poll_proposal", consumer, proposal),
            ("poll_acceptance", producer, acceptance),
            ("poll_attestation", consumer, attestation),
        ]
    ):
        candidates = phase_events.get((client_side, poll_phase), [])
        response_event = next(
            (item for item in candidates if item[1].get("request", {}).get("operation") == "mcp_response"),
            None,
        )
        if response_event is None:
            errors.append(error("PAIRWISE_CLIENT_FIRST_SEEN_INVALID", f"{name} {poll_phase} missing"))
            continue
        event_index, event = response_event
        digest = message.get("message_hash")
        previous_inputs = [
            prior.get("request", {}).get("input", {})
            for prior in events[:event_index]
            if prior.get("client_side") == client_side
        ]
        if any(_contains(value, digest) for value in previous_inputs):
            errors.append(error("PAIRWISE_CLIENT_ARTIFACT_PRESEEDED", f"{name} {poll_phase}"))
        if poll_phase == "poll_proposal" and any(_contains(value, challenge) for value in previous_inputs):
            errors.append(error("PAIRWISE_CONSUMER_CHALLENGE_PRESEEDED", str(name)))
        current_input = event.get("request", {}).get("input", {})
        if not _contains(current_input, digest):
            errors.append(error("PAIRWISE_CLIENT_FIRST_SEEN_INVALID", f"{name} {poll_phase}"))
        evidence_item = messages[message_index]
        expected_before = list(visible_by_client[client_side])
        visible_by_client[client_side].append(digest)
        expected_after = list(visible_by_client[client_side])
        if (
            evidence_item.get("client_visible_hashes_before") != expected_before
            or evidence_item.get("client_visible_hashes_after") != expected_after
        ):
            errors.append(error("PAIRWISE_CLIENT_VISIBLE_SET_INVALID", f"{name} {poll_phase}"))
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
