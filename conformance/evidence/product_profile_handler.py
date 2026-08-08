from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RUNNER_DIR = ROOT / "conformance" / "runner"
if str(RUNNER_DIR) not in sys.path:
    sys.path.insert(0, str(RUNNER_DIR))

from _runner_context import build_validator  # noqa: E402
from profile_transcript_evaluator import evaluate_profile_transcript  # noqa: E402


HANDLER_ID = "product_profile_v01"
REQUIRED_OPERATIONS = (
    "describe",
    "canonicalize_hash",
    "validate_transcript",
    "generate_scenario",
)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _canonical_digest(value: Any) -> str:
    import hashlib

    encoded = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def expected_error_codes(case: dict[str, Any]) -> list[str]:
    result: list[str] = []
    for observation in case["expected_error_observations"]:
        result.extend(
            [str(observation["code"])] * int(observation["exact_count"])
        )
    return result


def producer_cases(catalog: dict[str, Any], mode: str) -> list[dict[str, Any]]:
    cases = list(catalog["producer_scenarios"])
    if mode == "smoke":
        return cases[:1]
    if mode != "full-profile":
        raise ValueError("product-profile execution mode must be full-profile or smoke")
    return cases


def consumer_cases(catalog: dict[str, Any], mode: str) -> list[dict[str, Any]]:
    cases = list(catalog["consumer_cases"])
    if mode == "smoke":
        return [next(case for case in cases if case["accepted"] is True)]
    if mode != "full-profile":
        raise ValueError("product-profile execution mode must be full-profile or smoke")
    return cases


def _scenario_index(catalog: dict[str, Any]) -> dict[str, dict[str, Any]]:
    path = ROOT / str(catalog["producer_scenario_catalog"]["path"])
    payload = _load_json(path)
    return {
        str(item["scenario_id"]): item
        for item in payload.get("scenarios", [])
        if isinstance(item, dict) and isinstance(item.get("scenario_id"), str)
    }


def build_plan_entries(
    catalog: dict[str, Any],
    mode: str,
) -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    entries: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    target = dict(catalog["target"])
    for vector_entry in catalog["canonicalization_vectors"]:
        vector = _load_json(ROOT / vector_entry["path"])
        entries.append(
            (
                "canonicalize_hash",
                {"object_type": vector["object_type"], "object": vector["object"]},
                {
                    "kind": "canonicalize",
                    "case_id": vector_entry["case_id"],
                    "expected": vector,
                },
            )
        )

    scenarios = _scenario_index(catalog)
    for producer in producer_cases(catalog, mode):
        scenario = scenarios[str(producer["scenario_id"])]
        public_input = {
            "target": target,
            "scenario": scenario,
            "runtime_options": {
                "deterministic_seed": scenario["deterministic_seed"]
            },
        }
        private_check = {
            "kind": "producer",
            "case_id": producer["case_id"],
            "artifact_id": producer["artifact_id"],
            "scenario": scenario,
        }
        entries.append(("generate_scenario", public_input, private_check))
        entries.append(
            (
                "generate_scenario",
                public_input,
                {**private_check, "kind": "producer_repeat"},
            )
        )

    suite_by_id = {
        str(item["suite_id"]): str(item["path"])
        for item in catalog["required_suites"]
    }
    for case in consumer_cases(catalog, mode):
        entries.append(
            (
                "validate_transcript",
                {
                    "target": target,
                    "transcript": _load_jsonl(ROOT / case["fixture"]),
                    "public_verification_material": {
                        "required_suites": list(catalog["required_suite_paths"]),
                        "selected_suite": suite_by_id[
                            str(case["source_suite_id"])
                        ],
                    },
                    "runtime_options": {},
                },
                {"kind": "consumer", **case},
            )
        )
    return entries


def producer_validators(
    scenario_schema_path: Path,
    *,
    simulate_no_jsonschema: bool,
) -> tuple[Any | None, Any | None]:
    if simulate_no_jsonschema:
        return None, None
    schema = _load_json(scenario_schema_path)
    scenario_wrapper = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$defs": schema["$defs"],
        "$ref": "#/$defs/Scenario",
    }
    core_path = ROOT / "schemas/core/aicp-core-message.schema.json"
    return (
        build_validator(scenario_wrapper, scenario_schema_path),
        build_validator(_load_json(core_path), core_path),
    )


def _schema_errors(validator: Any, value: Any, label: str) -> list[str]:
    return [
        f"{label} schema error at /"
        + "/".join(str(part) for part in issue.path)
        + f": {issue.message}"
        for issue in sorted(
            validator.iter_errors(value),
            key=lambda item: list(item.path),
        )
    ]


def _flow_errors(
    flow_id: str,
    messages: list[dict[str, Any]],
    scenario: dict[str, Any],
) -> list[str]:
    errors: list[str] = []
    message_types = [str(message.get("message_type")) for message in messages]

    def require(*types: str) -> None:
        missing = [message_type for message_type in types if message_type not in message_types]
        if missing:
            errors.append(
                f"scenario {flow_id} lacks required semantic messages: {', '.join(missing)}"
            )

    if flow_id == "core_contract_action":
        require("CONTRACT_PROPOSE", "CONTRACT_ACCEPT", "ATTEST_ACTION")
    elif flow_id == "core_conflict_choose":
        require("CONTRACT_PROPOSE", "CONTRACT_ACCEPT", "RESOLVE_CONFLICT")
    elif flow_id in {"core_consent_grant", "core_consent_revoke"}:
        require("CONTRACT_PROPOSE", "CONTRACT_ACCEPT", "CONTEXT_AMEND", "ATTEST_ACTION")
    elif flow_id == "core_resync":
        require("STATE_SYNC_REQUEST", "STATE_SYNC_RESPONSE")
    elif flow_id == "core_error":
        if message_types != ["ERROR"]:
            errors.append("minimal ERROR scenario must contain exactly one ERROR")
    elif flow_id == "profile_accept_contract":
        require("CAPABILITIES_PROPOSE", "CAPABILITIES_ACCEPT", "CONTRACT_PROPOSE")
        selected = next(
            (
                ((message.get("payload") or {}).get("negotiation_result") or {})
                .get("selected", {})
                .get("aicp_profile")
                for message in messages
                if message.get("message_type") == "CAPABILITIES_PROPOSE"
            ),
            None,
        )
        expected = {
            "profile_id": scenario["target"]["target_id"],
            "profile_version": scenario["target"]["target_version"],
        }
        if selected != expected:
            errors.append("CAPNEG producer did not select the exact target profile")
    elif flow_id == "profile_reject":
        require("CAPABILITIES_PROPOSE", "CAPABILITIES_REJECT")
    elif flow_id in {"policy_allow_delivery", "policy_deny_block"}:
        require("POLICY_EVAL_RESULT", "ENFORCEMENT_VERDICT")
        policy = next(
            (
                (message.get("payload") or {}).get("policy_decision") or {}
                for message in messages
                if message.get("message_type") == "POLICY_EVAL_RESULT"
            ),
            {},
        )
        enforcement = next(
            (
                message.get("payload") or {}
                for message in messages
                if message.get("message_type") == "ENFORCEMENT_VERDICT"
            ),
            {},
        )
        expected_decision = "ALLOW" if flow_id == "policy_allow_delivery" else "DENY"
        if policy.get("decision") != expected_decision or enforcement.get(
            "decision"
        ) != expected_decision:
            errors.append("policy and enforcement decisions do not match the scenario")
        delivered = "CONTENT_DELIVER" in message_types
        if delivered is not (expected_decision == "ALLOW"):
            errors.append("blocking delivery behavior does not match the verdict")
    elif flow_id == "resume_in_sync":
        require("RESUME_REQUEST", "RESUME_RESPONSE")
        response = next(
            (
                message
                for message in messages
                if message.get("message_type") == "RESUME_RESPONSE"
            ),
            {},
        )
        if (response.get("payload") or {}).get("status") != "OK":
            errors.append("in-sync resume scenario must return the protocol OK status")
    elif flow_id == "resume_needs_resync":
        require(
            "RESUME_REQUEST",
            "RESUME_RESPONSE",
            "STATE_SYNC_REQUEST",
            "STATE_SYNC_RESPONSE",
        )
        response = next(
            (
                message
                for message in messages
                if message.get("message_type") == "RESUME_RESPONSE"
            ),
            {},
        )
        if (response.get("payload") or {}).get("status") != "NEEDS_RESYNC":
            errors.append("resync scenario must begin with NEEDS_RESYNC")
    elif flow_id == "object_retrieval":
        require("OBJECT_REQUEST", "OBJECT_RESPONSE")
        request = next(
            (
                message
                for message in messages
                if message.get("message_type") == "OBJECT_REQUEST"
            ),
            {},
        )
        response = next(
            (
                message
                for message in messages
                if message.get("message_type") == "OBJECT_RESPONSE"
            ),
            {},
        )
        if (request.get("payload") or {}).get("request_id") != (
            response.get("payload") or {}
        ).get("request_id"):
            errors.append("object response does not correlate to the request")
    elif flow_id == "identity_announce_use":
        require("IDENTITY_ANNOUNCE", "ATTEST_ACTION")
    elif flow_id == "identity_rotate_use":
        require("IDENTITY_ANNOUNCE", "KEY_ROTATION", "ATTEST_ACTION")
    elif flow_id == "identity_revoke_clean":
        require("IDENTITY_ANNOUNCE", "KEY_ROTATION", "KEY_REVOKE")
    elif flow_id == "binding_issue_use":
        require("IDENTITY_ANNOUNCE", "SUBJECT_BINDING_ISSUE", "ATTEST_ACTION")
    elif flow_id == "binding_revoke_clean":
        require("SUBJECT_BINDING_ISSUE", "SUBJECT_BINDING_REVOKE")
    else:
        errors.append(f"unknown producer flow: {flow_id}")
    return errors


def producer_errors(
    result: dict[str, Any],
    check: dict[str, Any],
    *,
    scenario_validator: Any | None,
    projection_validator: Any | None,
) -> list[str]:
    scenario = check["scenario"]
    if scenario_validator is None or projection_validator is None:
        return ["producer schema validation unavailable"]
    errors = _schema_errors(scenario_validator, scenario, "producer scenario")
    if not isinstance(result, dict):
        return [*errors, "producer result must be an object"]
    if result.get("artifact_kind") != "transcript":
        errors.append("producer result artifact_kind must be transcript")
    if result.get("scenario_id") != scenario.get("scenario_id"):
        errors.append("producer result scenario identity mismatch")
    if result.get("target") != scenario.get("target"):
        errors.append("producer result target identity mismatch")
    messages = result.get("messages")
    if not isinstance(messages, list) or not all(
        isinstance(message, dict) for message in messages
    ):
        return [*errors, "producer result messages must be an array of objects"]
    for message in messages:
        errors.extend(_schema_errors(projection_validator, message, "generated message"))
    if any(message.get("session_id") != scenario.get("session_id") for message in messages):
        errors.append("generated transcript session differs from neutral scenario")
    if any(message.get("contract_id") != scenario.get("contract_id") for message in messages):
        errors.append("generated transcript contract differs from neutral scenario")
    senders = {
        str(message.get("sender"))
        for message in messages
        if isinstance(message.get("sender"), str)
    }
    if not senders.issubset(set(scenario.get("participant_ids", []))):
        errors.append("generated transcript contains an undeclared participant")
    evaluation = evaluate_profile_transcript(messages, scenario["required_suites"])
    if not evaluation.accepted:
        errors.extend(
            f"generated transcript failed {item['code']}: {item['message']}"
            for item in evaluation.errors
        )
    if evaluation.degraded:
        errors.append("generated transcript validation was degraded")
    errors.extend(_flow_errors(str(scenario.get("flow_id")), messages, scenario))
    return sorted(set(errors))


def validate_catalog(
    catalog: dict[str, Any],
    *,
    simulate_no_jsonschema: bool = False,
) -> list[str]:
    errors: list[str] = []
    scenario_record = catalog.get("producer_scenario_catalog")
    if not isinstance(scenario_record, dict):
        return ["product profile producer scenario catalog is missing"]
    scenario_path = ROOT / str(scenario_record.get("path"))
    schema_path = ROOT / str(scenario_record.get("schema_path"))
    if not scenario_path.is_file() or not schema_path.is_file():
        return ["product profile producer scenario paths do not resolve"]
    schema = _load_json(schema_path)
    validator = None if simulate_no_jsonschema else build_validator(schema, schema_path)
    if validator is None:
        return ["jsonschema is required for product profile producer scenarios"]
    payload = _load_json(scenario_path)
    errors.extend(_schema_errors(validator, payload, "producer scenario catalog"))
    if payload.get("target") != catalog.get("target"):
        errors.append("producer scenario catalog target does not match target catalog")
    scenarios = payload.get("scenarios") if isinstance(payload.get("scenarios"), list) else []
    scenario_ids = [item.get("scenario_id") for item in scenarios if isinstance(item, dict)]
    producer_ids = [item.get("scenario_id") for item in catalog.get("producer_scenarios", [])]
    if Counter(scenario_ids) != Counter(producer_ids):
        errors.append("producer cases must cover every reviewed scenario exactly once")
    union = {
        str(suite)
        for scenario in scenarios
        if isinstance(scenario, dict)
        for suite in scenario.get("required_suites", [])
        if isinstance(suite, str)
    }
    if union != set(catalog.get("required_suite_paths", [])):
        errors.append("producer scenarios do not exercise every required profile suite")
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    for forbidden in (
        "fixture",
        "source_case_id",
        "expected_message",
        "message_hash",
        "compatibility_mark",
        "expect_pass",
        "expected_failure",
        "prebuilt",
    ):
        if forbidden in serialized:
            errors.append(f"neutral producer scenarios contain forbidden answer material: {forbidden}")
    return sorted(set(errors))


def evaluate_report(
    report: dict[str, Any],
    catalog: dict[str, Any],
    by_id: dict[str, dict[str, Any]],
    mode: str,
    disabled_checks: frozenset[str],
) -> list[tuple[str, str]]:
    errors: list[tuple[str, str]] = []
    expected_producers = producer_cases(catalog, mode)
    generated = report.get("generated_artifacts")
    if not isinstance(generated, list):
        return [("EVIDENCE_GENERATED_ARTIFACTS", "generated artifacts are missing")]
    by_artifact = {
        item.get("artifact_id"): item
        for item in generated
        if isinstance(item, dict)
    }
    scenarios = _scenario_index(catalog)
    scenario_schema = ROOT / str(catalog["producer_scenario_catalog"]["schema_path"])
    scenario_validator, core_validator = producer_validators(
        scenario_schema,
        simulate_no_jsonschema=False,
    )
    for producer in expected_producers:
        artifact = by_artifact.get(producer["artifact_id"])
        if not isinstance(artifact, dict):
            errors.append(("EVIDENCE_PRODUCER_COVERAGE", f"missing artifact {producer['artifact_id']}"))
            continue
        content = artifact.get("content")
        digest = _canonical_digest(content)
        if artifact.get("artifact_kind") != "transcript":
            errors.append(("EVIDENCE_ARTIFACT_KIND", "profile artifact kind must be transcript"))
        if artifact.get("content_digest") != digest:
            errors.append(("EVIDENCE_ARTIFACT_DIGEST", "producer artifact content digest mismatch"))
        if "determinism" not in disabled_checks and artifact.get(
            "repeat_content_digest"
        ) != digest:
            errors.append(("EVIDENCE_PRODUCER_NONDETERMINISTIC", "producer repeat digest mismatch"))
        if isinstance(content, dict):
            semantic_errors = producer_errors(
                content,
                {
                    "scenario": scenarios[producer["scenario_id"]],
                    "case_id": producer["case_id"],
                },
                scenario_validator=scenario_validator,
                projection_validator=core_validator,
            )
            errors.extend(
                ("EVIDENCE_GENERATED_TRANSCRIPT_INVALID", message)
                for message in semantic_errors
            )
        else:
            errors.append(("EVIDENCE_GENERATED_TRANSCRIPT_INVALID", "artifact content is missing"))
    if set(by_artifact) != {item["artifact_id"] for item in expected_producers}:
        errors.append(("EVIDENCE_PRODUCER_COVERAGE", "producer artifact coverage is duplicated or unknown"))

    if "consumer_observations" not in disabled_checks:
        for case in consumer_cases(catalog, mode):
            result = by_id.get(case["case_id"])
            observation = result.get("execution_observation") if isinstance(result, dict) else None
            expected = {
                "accepted": case["accepted"],
                "errors": [
                    {"code": code, "message": next(
                        (
                            item.get("message", "")
                            for item in (observation or {}).get("errors", [])
                            if item.get("code") == code
                        ),
                        "",
                    )}
                    for code in expected_error_codes(case)
                ],
                "degraded": case["expected_degraded"],
                "degraded_reasons": case["expected_degraded_reasons"],
                "skipped_checks": case["expected_skipped_checks"],
            }
            if not isinstance(observation, dict):
                errors.append(("EVIDENCE_CONSUMER_OBSERVATION", f"missing observation for {case['case_id']}"))
                continue
            if (
                observation.get("accepted") != expected["accepted"]
                or [item.get("code") for item in observation.get("errors", [])]
                != expected_error_codes(case)
                or observation.get("degraded") != expected["degraded"]
                or observation.get("degraded_reasons") != expected["degraded_reasons"]
                or observation.get("skipped_checks") != expected["skipped_checks"]
            ):
                errors.append(("EVIDENCE_CONSUMER_OBSERVATION", f"{case['case_id']} does not match reviewed exact observations"))
    return errors


class ProductProfileV01Handler:
    handler_id = HANDLER_ID
    required_operations = REQUIRED_OPERATIONS

    build_plan_entries = staticmethod(build_plan_entries)
    consumer_cases = staticmethod(consumer_cases)
    producer_cases = staticmethod(producer_cases)
    expected_error_codes = staticmethod(expected_error_codes)
    producer_errors = staticmethod(producer_errors)
    producer_validators = staticmethod(producer_validators)
    validate_catalog = staticmethod(validate_catalog)
    evaluate_report = staticmethod(evaluate_report)
