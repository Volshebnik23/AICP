from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RUNNER_DIR = ROOT / "conformance" / "runner"
REF_PY = ROOT / "reference" / "python"
for path in (RUNNER_DIR, REF_PY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from _runner_context import build_validator  # noqa: E402
from aicp_ref.hashing import message_hash_from_body, object_hash  # noqa: E402


HANDLER_ID = "projection_v1"
TARGET_ID = "aicp.session_state_projection"
TARGET_VERSION = "v1"
TARGET_KEY = f"{TARGET_ID}@{TARGET_VERSION}"
PROJECTION_VERSION = "aicp.session_state_projection.v1"
PROJECTION_OBJECT_TYPE = "session_state_projection"
PROJECTION_SCHEMA_PATH = (
    ROOT / "schemas/extensions/ext-object-resync-payloads.schema.json"
)


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _is_projection_response(message: dict[str, Any]) -> bool:
    state = (message.get("payload") or {}).get("session_state")
    return (
        message.get("message_type") == "STATE_SYNC_RESPONSE"
        and isinstance(state, dict)
        and state.get("projection_version") == PROJECTION_VERSION
    )


def transcript_prefix(transcript: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for index, message in enumerate(transcript):
        if _is_projection_response(message):
            return transcript[:index]
    return transcript


def _validated_message_hashes(
    transcript: list[dict[str, Any]],
) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for message in transcript:
        if _is_projection_response(message):
            raise ValueError(
                "producer transcript contains a completed projection response"
            )
        message_id = message.get("message_id")
        claimed_hash = message.get("message_hash")
        if not isinstance(message_id, str) or not message_id:
            raise ValueError("producer transcript message_id is missing")
        if message_id in hashes:
            raise ValueError("producer transcript message IDs must be unique")
        body = {key: value for key, value in message.items() if key != "message_hash"}
        computed_hash = message_hash_from_body(body)
        if claimed_hash != computed_hash:
            raise ValueError(
                f"producer transcript message hash mismatch: {message_id}"
            )
        hashes[message_id] = computed_hash
    return hashes


def derive_projection(
    scenario: dict[str, Any],
    transcript: list[dict[str, Any]],
) -> tuple[dict[str, Any], str]:
    """Derive projection v1 from raw scenario facts and verified messages."""

    hashes = _validated_message_hashes(transcript)
    session = scenario["session"]
    as_of = scenario["as_of"]
    contract = scenario["contract"]
    profile = scenario["selected_profile"]
    for message in transcript:
        if message.get("session_id") != session["session_id"]:
            raise ValueError("producer transcript session does not match scenario")
        if message.get("contract_id") != session["contract_id"]:
            raise ValueError("producer transcript contract does not match scenario")
    if as_of["message_id"] not in hashes:
        raise ValueError("producer as_of message_id is unresolved")
    if (
        as_of["branch_id"] != contract["branch_id"]
        or as_of["head_version"] != contract["head_version"]
    ):
        raise ValueError("producer as_of does not resolve to the active contract head")

    ordered_fields = (
        "active_extension_ids",
        "participant_ids",
        "evidence_message_ids",
    )
    for field in ordered_fields:
        values = scenario[field]
        if values != sorted(values):
            raise ValueError(f"producer scenario {field} is not canonically ordered")
    missing_evidence = [
        message_id
        for message_id in scenario["evidence_message_ids"]
        if message_id not in hashes
    ]
    if missing_evidence:
        raise ValueError(
            "producer evidence message IDs are unresolved: "
            + ", ".join(missing_evidence)
        )

    projection: dict[str, Any] = {
        "projection_version": PROJECTION_VERSION,
        "session_id": session["session_id"],
        "contract_id": session["contract_id"],
        "as_of_message_hash": hashes[as_of["message_id"]],
        "session_status": session["status"],
        "active_contract_ref": {
            "branch_id": contract["branch_id"],
            "base_version": contract["base_version"],
            "head_version": contract["head_version"],
        },
        "selected_aicp_profile": {
            "profile_id": profile["profile_id"],
            "profile_version": profile["profile_version"],
        },
        "active_extensions": list(scenario["active_extension_ids"]),
        "participant_refs": list(scenario["participant_ids"]),
        "evidence_refs": [
            f"msghash:{hashes[message_id]}"
            for message_id in scenario["evidence_message_ids"]
        ],
    }
    return projection, object_hash(PROJECTION_OBJECT_TYPE, projection)


def producer_validators(
    scenario_schema_path: Path,
    *,
    simulate_no_jsonschema: bool,
) -> tuple[Any | None, Any | None]:
    if simulate_no_jsonschema:
        return None, None
    scenario_schema = _load_json(scenario_schema_path)
    scenario_validator = build_validator(
        scenario_schema,
        scenario_schema_path,
    )
    projection_schema = _load_json(PROJECTION_SCHEMA_PATH)
    projection_wrapper = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$defs": projection_schema["$defs"],
        "$ref": "#/$defs/SessionStateProjectionV1",
    }
    projection_validator = build_validator(
        projection_wrapper,
        PROJECTION_SCHEMA_PATH,
    )
    return scenario_validator, projection_validator


def _schema_error_messages(
    validator: Any,
    value: dict[str, Any],
    label: str,
) -> list[str]:
    return [
        f"{label} schema error at /"
        + "/".join(str(part) for part in issue.path)
        + f": {issue.message}"
        for issue in sorted(
            validator.iter_errors(value),
            key=lambda item: list(item.path),
        )
    ]


def producer_errors(
    result: dict[str, Any],
    check: dict[str, Any],
    *,
    scenario_validator: Any | None,
    projection_validator: Any | None,
) -> list[str]:
    errors: list[str] = []
    projection = result.get("projection")
    projection_hash = result.get("session_state_hash")
    scenario = check["scenario"]
    transcript = check["transcript"]
    if scenario_validator is None or projection_validator is None:
        errors.append("producer schema validation unavailable")
        return errors
    errors.extend(
        _schema_error_messages(scenario_validator, scenario, "producer scenario")
    )
    if not isinstance(projection, dict):
        errors.append("producer result must contain projection object")
        return errors
    errors.extend(
        _schema_error_messages(projection_validator, projection, "projection")
    )
    try:
        derived_projection, derived_hash = derive_projection(
            scenario,
            transcript,
        )
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(f"producer scenario derivation failed: {exc}")
        return errors
    if projection != derived_projection:
        errors.append(
            "producer projection does not match independently derived scenario facts"
        )
    if projection != check["expected_projection"]:
        errors.append(
            "producer projection does not equal the private reviewed projection"
        )
    computed_hash = object_hash(PROJECTION_OBJECT_TYPE, projection)
    if projection_hash != computed_hash:
        errors.append(
            "producer projection hash does not match independently recomputed hash"
        )
    if projection_hash != derived_hash:
        errors.append(
            "producer projection hash does not match scenario-derived projection"
        )
    if projection_hash != check["expected_projection_hash"]:
        errors.append(
            "producer projection hash does not equal the private reviewed expectation"
        )
    return errors


def expected_error_codes(case: dict[str, Any]) -> list[str]:
    codes: list[str] = []
    for observation in case["expected_error_observations"]:
        codes.extend(
            [str(observation["code"])] * int(observation["exact_count"])
        )
    return codes


def consumer_cases(catalog: dict[str, Any], mode: str) -> list[dict[str, Any]]:
    cases = list(catalog["consumer_cases"])
    if mode == "smoke":
        return [case for case in cases if case["source_case_id"] == "SP-01"]
    if mode != "full-capability":
        raise ValueError("execution mode must be full-capability or smoke")
    return cases


def producer_cases(catalog: dict[str, Any], mode: str) -> list[dict[str, Any]]:
    if mode not in {"smoke", "full-capability"}:
        raise ValueError("execution mode must be full-capability or smoke")
    return [catalog["producer_case"]]


def build_plan_entries(
    catalog: dict[str, Any],
    mode: str,
) -> list[tuple[str, dict[str, Any], dict[str, Any]]]:
    entries: list[tuple[str, dict[str, Any], dict[str, Any]]] = []
    for vector_entry in catalog["canonicalization_vectors"]:
        vector = _load_json(ROOT / vector_entry["path"])
        entries.append(
            (
                "canonicalize_hash",
                {
                    "object_type": vector["object_type"],
                    "object": vector["object"],
                },
                {
                    "kind": "canonicalize",
                    "case_id": vector_entry["case_id"],
                    "expected": vector,
                },
            )
        )

    producer = catalog["producer_case"]
    scenario = _load_json(ROOT / producer["scenario_path"])
    prefix = _load_json(ROOT / producer["transcript_prefix_path"])
    if not isinstance(prefix, list) or not all(
        isinstance(message, dict) for message in prefix
    ):
        raise ValueError("producer transcript prefix must be an array of messages")
    producer_input = {
        "target": {
            "kind": "capability",
            "target_id": TARGET_ID,
            "target_version": TARGET_VERSION,
        },
        "scenario": scenario,
        "transcript": prefix,
    }
    private_check = {
        "kind": "producer",
        "case_id": producer["case_id"],
        "scenario": scenario,
        "transcript": prefix,
        "expected_projection": producer["expected_projection"],
        "expected_projection_hash": producer["expected_projection_hash"],
    }
    entries.append(("project_session_state", producer_input, private_check))
    entries.append(
        (
            "project_session_state",
            producer_input,
            {**private_check, "kind": "producer_repeat"},
        )
    )
    for case in consumer_cases(catalog, mode):
        entries.append(
            (
                "validate_transcript",
                {
                    "target": {
                        "kind": "capability",
                        "target_id": TARGET_ID,
                        "target_version": TARGET_VERSION,
                    },
                    "transcript": _load_jsonl(ROOT / case["fixture"]),
                    "runtime_options": {},
                },
                {"kind": "consumer", **case},
            )
        )
    return entries


def validate_catalog(
    catalog: dict[str, Any],
    *,
    simulate_no_jsonschema: bool = False,
    transcript_override: list[dict[str, Any]] | None = None,
) -> list[str]:
    errors: list[str] = []
    producer = catalog.get("producer_case")
    if not isinstance(producer, dict):
        return ["projection v1 producer case is missing"]
    scenario_path = producer.get("scenario_path")
    transcript_path = producer.get("transcript_fixture")
    prefix_path = producer.get("transcript_prefix_path")
    schema_path = producer.get("scenario_schema_path")
    if not all(
        isinstance(item, str)
        for item in (scenario_path, transcript_path, prefix_path, schema_path)
    ):
        return ["projection v1 producer paths are incomplete"]
    scenario = _load_json(ROOT / str(scenario_path))
    full_transcript = _load_jsonl(ROOT / str(transcript_path))
    reviewed_prefix = _load_json(ROOT / str(prefix_path))
    if not isinstance(reviewed_prefix, list) or not all(
        isinstance(message, dict) for message in reviewed_prefix
    ):
        return ["producer transcript prefix must be an array of messages"]
    transcript = transcript_override or reviewed_prefix
    scenario_validator, projection_validator = producer_validators(
        ROOT / str(schema_path),
        simulate_no_jsonschema=simulate_no_jsonschema,
    )
    if scenario_validator is None or projection_validator is None:
        errors.append(
            "jsonschema is required to validate the projection v1 producer catalog"
        )
        return errors
    errors.extend(
        _schema_error_messages(scenario_validator, scenario, "producer scenario")
    )
    if any(_is_projection_response(message) for message in transcript):
        errors.append("producer transcript prefix contains a strict projection object")
    if transcript_override is None and transcript != transcript_prefix(full_transcript):
        errors.append(
            "producer transcript prefix does not exactly omit the requested projection response"
        )
    try:
        expected_projection, expected_hash = derive_projection(
            scenario,
            transcript,
        )
    except (KeyError, TypeError, ValueError) as exc:
        errors.append(f"producer scenario cannot be derived: {exc}")
    else:
        if expected_projection != producer.get("expected_projection"):
            errors.append("reviewed projection does not match neutral producer input")
        if expected_hash != producer.get("expected_projection_hash"):
            errors.append("reviewed projection hash does not match neutral producer input")
    serialized = json.dumps(
        {"scenario": scenario, "transcript": transcript},
        ensure_ascii=False,
        sort_keys=True,
    )
    for forbidden in (
        '"projection_version"',
        str(producer.get("expected_projection_hash")),
    ):
        if forbidden and forbidden in serialized:
            errors.append("producer request material contains reviewed answer data")
    return sorted(set(errors))


def evaluate_report(
    report: dict[str, Any],
    catalog: dict[str, Any],
    by_id: dict[str, dict[str, Any]],
    mode: str,
    disabled_checks: frozenset[str],
) -> list[tuple[str, str]]:
    errors: list[tuple[str, str]] = []
    generated = report.get("generated_artifacts")
    producer = catalog["producer_case"]
    if not isinstance(generated, list) or len(generated) != 1:
        errors.append(
            (
                "EVIDENCE_PRODUCER_ARTIFACT_MISSING",
                "exactly one producer artifact is required",
            )
        )
    else:
        artifact = generated[0]
        content = artifact.get("content") if isinstance(artifact, dict) else None
        expected_content = {
            "projection": producer["expected_projection"],
            "session_state_hash": producer["expected_projection_hash"],
        }
        if (
            not isinstance(artifact, dict)
            or artifact.get("artifact_id") != producer["case_id"]
            or (
                report.get("report_format_version") == "2.1"
                and artifact.get("artifact_kind") != "projection"
            )
            or content != expected_content
            or artifact.get("content_digest")
            != _canonical_digest(expected_content)
        ):
            errors.append(
                (
                    "EVIDENCE_PRODUCER_ARTIFACT_INVALID",
                    "producer content or digest does not match private reviewed expectations",
                )
            )
        if (
            "determinism" not in disabled_checks
            and isinstance(artifact, dict)
            and artifact.get("repeat_content_digest")
            != artifact.get("content_digest")
        ):
            errors.append(
                (
                    "EVIDENCE_PRODUCER_NONDETERMINISTIC",
                    "producer repeat digest does not match",
                )
            )

    if "consumer_observations" not in disabled_checks:
        for case in consumer_cases(catalog, mode):
            result = by_id.get(str(case["case_id"]))
            observation = (
                result.get("execution_observation")
                if isinstance(result, dict)
                else None
            )
            if not isinstance(observation, dict):
                errors.append(
                    (
                        "EVIDENCE_CONSUMER_OBSERVATION_MISSING",
                        f"{case['case_id']} has no structured observation",
                    )
                )
                continue
            actual_codes = [
                item.get("code")
                for item in observation.get("errors", [])
                if isinstance(item, dict)
            ]
            actual = {
                "accepted": observation.get("accepted"),
                "error_codes": actual_codes,
                "degraded": observation.get("degraded"),
                "degraded_reasons": observation.get("degraded_reasons"),
                "skipped_checks": observation.get("skipped_checks"),
            }
            expected = {
                "accepted": case["accepted"],
                "error_codes": expected_error_codes(case),
                "degraded": case["expected_degraded"],
                "degraded_reasons": case["expected_degraded_reasons"],
                "skipped_checks": case["expected_skipped_checks"],
            }
            if actual != expected:
                errors.append(
                    (
                        "EVIDENCE_CONSUMER_OBSERVATION_MISMATCH",
                        f"{case['case_id']} does not match reviewed exact observations",
                    )
                )
    return errors


def _canonical_digest(value: Any) -> str:
    import hashlib

    data = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return "sha256:" + hashlib.sha256(data).hexdigest()


class ProjectionV1Handler:
    handler_id = HANDLER_ID
    artifact_kind = "projection"

    build_plan_entries = staticmethod(build_plan_entries)
    consumer_cases = staticmethod(consumer_cases)
    producer_cases = staticmethod(producer_cases)
    expected_error_codes = staticmethod(expected_error_codes)
    producer_errors = staticmethod(producer_errors)
    producer_validators = staticmethod(producer_validators)
    validate_catalog = staticmethod(validate_catalog)
    evaluate_report = staticmethod(evaluate_report)
