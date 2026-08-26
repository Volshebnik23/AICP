from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = ROOT / "conformance" / "evidence"
RUNNER_DIR = ROOT / "conformance" / "runner"

import sys

for path in (EVIDENCE_DIR, RUNNER_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from _runner_context import build_validator  # noqa: E402
from target_catalog import canonical_digest, file_digest, load_json  # noqa: E402
from live_bindings.live_binding_trace import evaluate_live_binding_trace  # noqa: E402


HTTP_FAMILIES = {
    "authentication",
    "session_lifecycle",
    "message_ingest",
    "idempotent_replay",
    "session_scoped_replay",
    "polling_cursor",
    "head",
    "explicit_ack",
    "replay_window",
    "ordering",
    "overload",
    "sse_stream",
    "sse_reconnect",
    "websocket_pull",
    "close_session",
}
MCP_FAMILIES = {
    "send_message",
    "duplicate_send",
    "poll_messages",
    "get_head",
    "get_object",
    "jsonrpc_integrity",
}
CLIENT_OBSERVABLE_ACTIONS = {
    "authentication": "send authenticated request after observing rejection",
    "session_lifecycle": "send two create-session requests and consume distinct session IDs",
    "message_ingest": "send the deterministic message on its session path with exact headers",
    "idempotent_replay": "repeat the same session/message operation",
    "session_scoped_replay": "send the same message ID in a second session",
    "polling_cursor": "send poll with explicit after and limit",
    "head": "request head for the created session",
    "explicit_ack": "send the exact cursor returned by poll",
    "replay_window": "send an expired-cursor request and consume the rejection",
    "ordering": "request and consume adjacent message references",
    "overload": "issue overload probe and consume retry metadata",
    "sse_stream": "open and parse the SSE byte stream",
    "sse_reconnect": "reuse the prior SSE event ID in both resume controls",
    "websocket_pull": "send a masked pull frame after a verified handshake",
    "wss_pull": "perform verified TLS then send a masked WebSocket pull frame",
    "close_session": "close the session and retry an ingest",
    "send_message": "emit an exact sendMessage JSON-RPC request",
    "duplicate_send": "emit the same sendMessage request again",
    "poll_messages": "reuse the first returned cursor in a second poll request",
    "get_head": "emit getHead for the tested session",
    "get_object": "emit known and unknown getObject requests",
    "jsonrpc_integrity": "correlate unique request IDs and emit a malformed-envelope probe",
}
FORBIDDEN_ANSWER_KEYS = {
    "expected_response",
    "expected_headers",
    "expected_pass",
    "pass_flag",
    "ready_made_trace",
    "canonical_fixture_id",
}


def _walk_keys(value: Any) -> set[str]:
    keys: set[str] = set()
    if isinstance(value, dict):
        for key, child in value.items():
            keys.add(str(key))
            keys.update(_walk_keys(child))
    elif isinstance(value, list):
        for child in value:
            keys.update(_walk_keys(child))
    return keys


class LiveBindingV01Handler:
    handler_id = "live_binding_v01"
    artifact_kind = "live_binding_trace"

    def mandatory_case_ids(
        self,
        _catalog: dict[str, Any],
        mode: str,
    ) -> list[str]:
        ids = [
            "EVIDENCE-TARGET-CATALOG-01",
            "EVIDENCE-TCK-PROVENANCE-01",
            "EVIDENCE-RUNNER-WORKTREE-01",
            "EVIDENCE-LIVE-SERVER-ROLE-01",
        ]
        if mode == "full-binding":
            ids.append("EVIDENCE-LIVE-CLIENT-ROLE-01")
        ids.extend(
            [
                "EVIDENCE-LIVE-SUBJECT-01",
                "EVIDENCE-LIVE-TRACE-SCHEMA-01",
                "EVIDENCE-LIVE-TRACE-EVALUATION-01",
                "EVIDENCE-LIVE-DETERMINISM-01",
                "EVIDENCE-TARGET-SUPPORT-01",
            ]
        )
        return ids

    def validate_catalog(
        self,
        catalog: dict[str, Any],
        *,
        simulate_no_jsonschema: bool = False,
    ) -> list[str]:
        errors: list[str] = []
        scenario_record = catalog.get("live_scenario_catalog")
        if not isinstance(scenario_record, dict):
            return ["binding target live scenario catalog is missing"]
        scenario_path = ROOT / str(scenario_record.get("path"))
        schema_path = ROOT / str(scenario_record.get("schema_path"))
        if not scenario_path.is_file() or not schema_path.is_file():
            return ["binding live scenario catalog or schema does not resolve"]
        scenarios = load_json(scenario_path)
        schema = load_json(schema_path)
        validator = None if simulate_no_jsonschema else build_validator(schema, schema_path)
        if validator is None:
            errors.append("jsonschema is required to validate live binding scenarios")
        else:
            for issue in sorted(validator.iter_errors(scenarios), key=lambda item: list(item.path)):
                pointer = "/" + "/".join(str(part) for part in issue.path)
                errors.append(f"live scenario schema error at {pointer}: {issue.message}")
        if scenarios.get("target") != catalog.get("target"):
            errors.append("live scenario target differs from binding target")
        if scenario_record.get("content_digest") != file_digest(scenario_path):
            errors.append("live scenario catalog digest is stale")
        if scenario_record.get("schema_digest") != file_digest(schema_path):
            errors.append("live scenario schema digest is stale")
        scenario_items = scenarios.get("scenarios")
        if not isinstance(scenario_items, list):
            return sorted(set([*errors, "live scenarios must be an array"]))
        ids = [str(item.get("scenario_id")) for item in scenario_items if isinstance(item, dict)]
        if len(ids) != len(set(ids)):
            errors.append("live scenario IDs must be unique")
        if FORBIDDEN_ANSWER_KEYS & _walk_keys(scenarios):
            errors.append("live scenario catalog embeds answer material")
        target_id = catalog.get("target", {}).get("target_id")
        expected_families = HTTP_FAMILIES if target_id == "BIND-HTTP" else MCP_FAMILIES
        observed = Counter(
            (str(item.get("tested_role")), str(item.get("semantic_family")))
            for item in scenario_items
            if isinstance(item, dict)
        )
        required = Counter(
            (role, family)
            for role in ("server_under_test", "client_under_test")
            for family in expected_families
        )
        if observed != required:
            errors.append("live scenario catalog does not cover every mandatory family once per role")
        client_families = {
            str(item.get("semantic_family"))
            for item in scenario_items
            if isinstance(item, dict) and item.get("tested_role") == "client_under_test"
        }
        missing_client_actions = sorted(client_families - set(CLIENT_OBSERVABLE_ACTIONS))
        if missing_client_actions:
            errors.append(
                "client scenarios lack observable client-action mappings: "
                + ", ".join(missing_client_actions)
            )
        static_refs = {
            str(ref)
            for item in scenario_items
            if isinstance(item, dict)
            for ref in item.get("required_static_suite_checks", [])
        }
        expected_static = set(catalog.get("live_relevant_static_checks", []))
        if static_refs != expected_static:
            errors.append("live scenario mappings do not exactly cover live-relevant static checks")
        for item in catalog.get("required_input_artifacts", []):
            if not isinstance(item, dict):
                errors.append("binding target input artifact is not an object")
                continue
            relative = item.get("path")
            if not isinstance(relative, str) or not (ROOT / relative).is_file():
                errors.append(f"binding target input artifact does not resolve: {relative}")
            elif item.get("content_digest") != file_digest(ROOT / relative):
                errors.append(f"binding target input artifact digest is stale: {relative}")
        return sorted(set(errors))

    def evaluate_report(
        self,
        report: dict[str, Any],
        catalog: dict[str, Any],
        _by_id: dict[str, dict[str, Any]],
        mode: str,
        _disabled_checks: frozenset[str],
    ) -> list[tuple[str, str]]:
        artifacts = report.get("generated_artifacts")
        if not isinstance(artifacts, list) or len(artifacts) != 1:
            return [
                (
                    "EVIDENCE_LIVE_ARTIFACT_MULTIPLICITY",
                    "binding report must contain exactly one live binding trace",
                )
            ]
        artifact = artifacts[0]
        if not isinstance(artifact, dict):
            return [("EVIDENCE_LIVE_ARTIFACT_INVALID", "live binding trace is not an object")]
        trace_schema_path = ROOT / str(catalog["live_trace_schema"]["path"])
        trace_schema = load_json(trace_schema_path)
        validator = build_validator(trace_schema, trace_schema_path)
        if validator is None:
            return [
                (
                    "EVIDENCE_LIVE_TRACE_SCHEMA_UNAVAILABLE",
                    "jsonschema is required to validate a live binding trace",
                )
            ]
        errors = [
            "live trace schema error at "
            + ("/" + "/".join(str(part) for part in issue.path) if issue.path else "/")
            + f": {issue.message}"
            for issue in sorted(validator.iter_errors(artifact), key=lambda item: list(item.path))
        ]
        errors.extend(evaluate_live_binding_trace(
            artifact,
            load_json(ROOT / str(catalog["live_scenario_catalog"]["path"])),
            full_binding=mode == "full-binding",
            disabled_families=frozenset(
                value.removeprefix("LIVE-FAMILY-")
                for value in _disabled_checks
                if value.startswith("LIVE-FAMILY-")
            ),
        ))
        content = artifact.get("content")
        roles = content.get("roles") if isinstance(content, dict) else None
        subject = report.get("execution_subject")
        if isinstance(roles, dict) and isinstance(subject, dict):
            expected_identity = (
                subject.get("kind"),
                subject.get("implementation_id"),
                subject.get("implementation_version"),
                subject.get("implementation_digest"),
            )
            for role_name, role in roles.items():
                actual_identity = (
                    role.get("implementation_kind"),
                    role.get("implementation_id"),
                    role.get("implementation_version"),
                    role.get("implementation_digest"),
                ) if isinstance(role, dict) else None
                if actual_identity != expected_identity:
                    errors.append(
                        f"live trace role {role_name} is not bound to the report execution subject"
                    )
        if artifact.get("content_digest") != canonical_digest(artifact.get("content")):
            errors.append("live binding artifact content digest differs")
        return [("EVIDENCE_LIVE_TRACE_INVALID", message) for message in errors]
