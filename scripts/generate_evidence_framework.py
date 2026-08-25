#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "conformance" / "evidence"
if str(EVIDENCE_DIR) not in sys.path:
    sys.path.insert(0, str(EVIDENCE_DIR))

from target_catalog import (  # noqa: E402
    BUNDLE_MANIFEST_PATH,
    BINDING_TARGET_KEYS,
    CURRENT_TCK_RELEASE_ID,
    EXPECTATIONS_PATH,
    EXPECTED_MARK,
    FROZEN_TCK_1_1_RECORD_DIGEST,
    FROZEN_TCK_1_1_REGISTRY_SNAPSHOT_DIGEST,
    FROZEN_TCK_1_2_RECORD_DIGEST,
    FROZEN_TCK_1_2_REGISTRY_SNAPSHOT_DIGEST,
    FROZEN_TCK_1_3_RECORD_DIGEST,
    FROZEN_TCK_1_3_REGISTRY_SNAPSHOT_DIGEST,
    FROZEN_TCK_1_4_RECORD_DIGEST,
    FROZEN_TCK_1_4_REGISTRY_SNAPSHOT_DIGEST,
    FROZEN_TCK_1_5_RECORD_DIGEST,
    FROZEN_TCK_1_5_REGISTRY_SNAPSHOT_DIGEST,
    FROZEN_TCK_1_6_RECORD_DIGEST,
    FROZEN_TCK_1_6_REGISTRY_SNAPSHOT_DIGEST,
    FROZEN_TCK_1_7_RECORD_DIGEST,
    FROZEN_TCK_1_7_REGISTRY_SNAPSHOT_DIGEST,
    FROZEN_TCK_1_8_RECORD_DIGEST,
    FROZEN_TCK_1_8_REGISTRY_SNAPSHOT_DIGEST,
    HISTORICAL_RELEASE_RECORD_DIGEST,
    HISTORICAL_RELEASE_REGISTRY_DIGEST,
    HISTORICAL_TARGET_SCHEMA_DIGEST,
    HISTORICAL_TCK_RELEASE_ID,
    PRODUCER_SCENARIO_PATH,
    PRODUCER_SCENARIO_SCHEMA_PATH,
    PRODUCER_TRANSCRIPT_PATH,
    PROFILE_TCK_RELEASE_ID,
    PREVIOUS_TCK_RELEASE_ID,
    TCK_1_4_RELEASE_ID,
    TCK_1_5_RELEASE_ID,
    TCK_1_6_RELEASE_ID,
    TCK_1_7_RELEASE_ID,
    TCK_1_8_RELEASE_ID,
    PROFILE_TARGET_KEYS,
    REPORT_SCHEMA_PATH,
    REPORT_SCHEMA_V21_PATH,
    REPORT_SCHEMA_V22_PATH,
    RELEASE_SNAPSHOT_DIR,
    TARGET_CATALOG_PATH,
    TARGET_ID,
    TARGET_KEY,
    TARGET_SCHEMA_PATH,
    TargetRecord,
    TARGET_VERSION,
    TARGETS_PATH,
    TCK_RELEASES_PATH,
    TCK_RELEASE_ID,
    bundle_manifest_payload,
    canonical_digest,
    digest_bytes,
    file_digest,
    load_json,
    mandatory_case_ids,
    validate_release_registry,
    validate_target_catalog,
    validate_target_registry,
)
from target_handlers import resolve_handler  # noqa: E402
from profile_scenario_builder import scenario_template_paths  # noqa: E402
from producer_payload_schema_router import (  # noqa: E402
    tier1_payload_route_input_paths,
)


SUITE_REF = "conformance/extensions/OR_SESSION_STATE_PROJECTION_V1.json"
VECTOR_REFS = ["conformance/vectors/unicode_codepoint_key_order.json"]
STATIC_INPUTS = [
    "conformance/evidence/projection_v1_expectations.json",
    "conformance/evidence/projection_v1_producer_scenario.json",
    "conformance/evidence/projection_v1_producer_scenario.schema.json",
    "conformance/evidence/projection_v1_producer_transcript.json",
    "schemas/core/aicp-core-message.schema.json",
    "schemas/extensions/ext-object-resync-payloads.schema.json",
    "registry/aicp_profiles.json",
    "registry/extension_ids.json",
]

PROFILE_EXPECTATIONS_PATH = EVIDENCE_DIR / "product_profile_consumer_expectations.json"
PROFILE_SCENARIO_SCHEMA_PATH = EVIDENCE_DIR / "product_profile_producer_scenario.schema.json"
PROFILE_CONFIGS = (
    {
        "target_key": "AICP-MEDIATED-BLOCKING@0.1",
        "target_id": "AICP-MEDIATED-BLOCKING",
        "profile_path": "conformance/profiles/PF_AICP_MEDIATED_BLOCKING_0.1.json",
        "catalog_path": "conformance/evidence/mediated_blocking_target.json",
        "scenario_path": "conformance/evidence/mediated_blocking_producer_scenarios.json",
        "case_prefix": "MB",
    },
    {
        "target_key": "AICP-RESUMABLE-SESSIONS@0.1",
        "target_id": "AICP-RESUMABLE-SESSIONS",
        "profile_path": "conformance/profiles/PF_AICP_RESUMABLE_SESSIONS_0.1.json",
        "catalog_path": "conformance/evidence/resumable_sessions_target.json",
        "scenario_path": "conformance/evidence/resumable_sessions_producer_scenarios.json",
        "case_prefix": "RS",
    },
    {
        "target_key": "AICP-DELEGATED-IDENTITY@0.1",
        "target_id": "AICP-DELEGATED-IDENTITY",
        "profile_path": "conformance/profiles/PF_AICP_DELEGATED_IDENTITY_0.1.json",
        "catalog_path": "conformance/evidence/delegated_identity_target.json",
        "scenario_path": "conformance/evidence/delegated_identity_producer_scenarios.json",
        "case_prefix": "DI",
    },
)
BINDING_CONFIGS = (
    {
        "target_key": "BIND-HTTP@0.1",
        "target_id": "BIND-HTTP",
        "canonical_binding_id": "BIND-HTTP-0.1",
        "suite_path": "conformance/bindings/TB_HTTP_WS_0.1.json",
        "catalog_path": "conformance/evidence/live_bindings/http_v01_target_v4.json",
        "scenario_path": "conformance/evidence/live_bindings/http_v01_scenarios.json",
        "spec_path": "docs/bindings/RFC_BIND_HTTP_WS.md",
        "expected_mark": "AICP-BIND-HTTP-0.1",
    },
    {
        "target_key": "BIND-MCP@0.1",
        "target_id": "BIND-MCP",
        "canonical_binding_id": "BIND-MCP-0.1",
        "suite_path": "conformance/bindings/TB_MCP_0.1.json",
        "catalog_path": "conformance/evidence/live_bindings/mcp_v01_target_v4.json",
        "scenario_path": "conformance/evidence/live_bindings/mcp_v01_scenarios.json",
        "spec_path": "docs/bindings/RFC_BIND_MCP.md",
        "expected_mark": "AICP-BIND-MCP-0.1",
    },
)


def render(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def target_registry_payload() -> dict[str, Any]:
    targets = [
        {
            "target_key": TARGET_KEY,
            "target_kind": "capability",
            "target_id": TARGET_ID,
            "target_version": TARGET_VERSION,
            "status": "experimental",
            "catalog_path": TARGET_CATALOG_PATH.relative_to(ROOT).as_posix(),
            "expected_mark": EXPECTED_MARK,
            "execution_mode": "full-capability",
            "evidence_claim_type": "implements_capability",
            "handler_id": "projection_v1",
            "current_release_id": CURRENT_TCK_RELEASE_ID,
            "required_suites": [SUITE_REF],
            "required_operations": [
                "describe",
                "canonicalize_hash",
                "validate_transcript",
                "project_session_state",
            ],
        }
    ]
    registry = load_json(ROOT / "registry/aicp_profiles.json")
    profile_entries = {
        (str(item.get("profile_id")), str(item.get("profile_version"))): item
        for item in registry
        if isinstance(item, dict)
    }
    for config in PROFILE_CONFIGS:
        profile = load_json(ROOT / config["profile_path"])
        entry = profile_entries[(config["target_id"], "0.1")]
        targets.append(
            {
                "target_key": config["target_key"],
                "target_kind": "product_profile",
                "target_id": config["target_id"],
                "target_version": "0.1",
                "status": str(entry["status"]),
                "catalog_path": config["catalog_path"],
                "expected_mark": str(profile["compatibility_mark"]),
                "execution_mode": "full-profile",
                "evidence_claim_type": "implements_profile",
                "handler_id": "product_profile_v01",
                "current_release_id": CURRENT_TCK_RELEASE_ID,
                "required_suites": list(profile["required_suites"]),
                "required_operations": [
                    "describe",
                    "canonicalize_hash",
                    "validate_transcript",
                    "generate_scenario",
                ],
            }
        )
    bindings = {
        str(item.get("id")): item
        for item in load_json(ROOT / "registry/transport_bindings.json")
        if isinstance(item, dict)
    }
    for config in BINDING_CONFIGS:
        binding = bindings[config["canonical_binding_id"]]
        targets.append(
            {
                "target_key": config["target_key"],
                "target_kind": "binding",
                "target_id": config["target_id"],
                "target_version": "0.1",
                "status": str(binding["status"]),
                "catalog_path": config["catalog_path"],
                "expected_mark": config["expected_mark"],
                "execution_mode": "full-binding",
                "evidence_claim_type": "implements_binding",
                "handler_id": "live_binding_v01",
                "current_release_id": CURRENT_TCK_RELEASE_ID,
                "required_suites": [config["suite_path"]],
                "required_operations": ["live_server", "live_client"],
            }
        )
    return {"registry_version": "1.1", "targets": targets}


def target_catalog_payload() -> dict[str, Any]:
    suite = load_json(ROOT / SUITE_REF)
    expectations = load_json(EXPECTATIONS_PATH)
    if expectations.get("target_key") != TARGET_KEY:
        raise ValueError("reviewed expectation target key is stale")
    suite_cases = [
        item for item in suite.get("transcripts", []) if isinstance(item, dict)
    ]
    expected_cases = expectations.get("consumers")
    if not isinstance(expected_cases, dict):
        raise ValueError("reviewed consumer expectations must be an object")
    suite_ids = [str(item["id"]) for item in suite_cases]
    if set(suite_ids) != set(expected_cases):
        raise ValueError(
            "reviewed consumer expectations must exactly cover the suite"
        )

    consumers: list[dict[str, Any]] = []
    fixture_paths: list[str] = []
    for item in suite_cases:
        source_id = str(item["id"])
        fixture = str(item["path"])
        oracle = expected_cases[source_id]
        accepted = item.get("expect_pass", True) is True
        if oracle.get("accepted") is not accepted:
            raise ValueError(f"reviewed acceptance drifts from suite: {source_id}")
        observations = oracle.get("error_observations")
        if not isinstance(observations, list):
            raise ValueError(
                f"reviewed error observations are missing: {source_id}"
            )
        suite_counts = {
            str(failure["test_id"]): sum(
                1
                for candidate in item.get("expected_failures", [])
                if isinstance(candidate, dict)
                and candidate.get("test_id") == failure.get("test_id")
            )
            for failure in item.get("expected_failures", [])
            if isinstance(failure, dict)
        }
        reviewed_counts: dict[str, int] = {}
        for observation in observations:
            code = str(observation["code"])
            reviewed_counts[code] = reviewed_counts.get(code, 0) + int(
                observation["exact_count"]
            )
            if (
                reviewed_counts[code] > suite_counts.get(code, 0)
                and not observation.get("supplemental_reason")
            ):
                raise ValueError(
                    f"supplemental error lacks reviewed rationale: {source_id}/{code}"
                )
        if any(
            reviewed_counts.get(code, 0) < count
            for code, count in suite_counts.items()
        ):
            raise ValueError(
                f"reviewed errors omit owning-suite code: {source_id}"
            )
        fixture_paths.append(fixture)
        consumers.append(
            {
                "case_id": f"EVIDENCE-CONSUMER-{source_id}",
                "source_case_id": source_id,
                "fixture": fixture,
                "input_digest": file_digest(ROOT / fixture),
                "accepted": accepted,
                "expected_error_observations": observations,
                "expected_degraded": False,
                "expected_degraded_reasons": [],
                "expected_skipped_checks": [],
            }
        )

    producer_oracle = expectations.get("producer")
    if not isinstance(producer_oracle, dict):
        raise ValueError("reviewed producer expectation is missing")
    producer_source = str(producer_oracle.get("source_case_id"))
    producer_suite_case = next(
        (item for item in suite_cases if item.get("id") == producer_source),
        None,
    )
    if (
        producer_suite_case is None
        or producer_suite_case.get("expect_pass", True) is not True
    ):
        raise ValueError("producer must resolve to a positive owning-suite case")
    producer_fixture = str(producer_suite_case["path"])

    canonicalization_vectors: list[dict[str, Any]] = []
    for vector_ref in VECTOR_REFS:
        vector = load_json(ROOT / vector_ref)
        canonicalization_vectors.append(
            {
                "case_id": str(vector["vector_id"]),
                "path": vector_ref,
                "input_digest": file_digest(ROOT / vector_ref),
            }
        )

    required_paths = sorted(
        set([SUITE_REF, *fixture_paths, *VECTOR_REFS, *STATIC_INPUTS])
    )
    required_inputs = [
        {"path": relative, "content_digest": file_digest(ROOT / relative)}
        for relative in required_paths
    ]
    return {
        "catalog_version": "1.1",
        "target_key": TARGET_KEY,
        "target": {
            "kind": "capability",
            "target_id": TARGET_ID,
            "target_version": TARGET_VERSION,
        },
        "handler_id": "projection_v1",
        "owning_suite": {
            "path": SUITE_REF,
            "suite_id": str(suite["suite_id"]),
            "suite_version": str(suite["suite_version"]),
            "suite_digest": file_digest(ROOT / SUITE_REF),
        },
        "expected_mark": EXPECTED_MARK,
        "external_execution_mode": "full-capability",
        "required_operations": [
            "describe",
            "canonicalize_hash",
            "validate_transcript",
            "project_session_state",
        ],
        "canonicalization_vectors": canonicalization_vectors,
        "producer_case": {
            "case_id": "EVIDENCE-PRODUCER-SP-01",
            "source_case_id": producer_source,
            "transcript_fixture": producer_fixture,
            "transcript_fixture_digest": file_digest(ROOT / producer_fixture),
            "transcript_prefix_path": PRODUCER_TRANSCRIPT_PATH.relative_to(
                ROOT
            ).as_posix(),
            "transcript_prefix_digest": file_digest(PRODUCER_TRANSCRIPT_PATH),
            "scenario_path": PRODUCER_SCENARIO_PATH.relative_to(ROOT).as_posix(),
            "scenario_digest": file_digest(PRODUCER_SCENARIO_PATH),
            "scenario_schema_path": PRODUCER_SCENARIO_SCHEMA_PATH.relative_to(
                ROOT
            ).as_posix(),
            "scenario_schema_digest": file_digest(PRODUCER_SCENARIO_SCHEMA_PATH),
            "expected_projection": producer_oracle["expected_projection"],
            "expected_projection_hash": producer_oracle[
                "expected_projection_hash"
            ],
        },
        "consumer_error_ordering": (
            "observation-list order, repeated code exact_count times"
        ),
        "consumer_cases": consumers,
        "required_input_artifacts": required_inputs,
    }


def _bounded_case_token(value: str) -> str:
    return "".join(
        character if character.isalnum() else "-" for character in value.upper()
    ).strip("-")


def profile_target_catalog_payload(config: dict[str, str]) -> dict[str, Any]:
    profile = load_json(ROOT / config["profile_path"])
    expectations = load_json(PROFILE_EXPECTATIONS_PATH)
    target_expectation_suites = expectations["target_suites"].get(
        config["target_key"]
    )
    required_suite_paths = list(profile["required_suites"])
    if target_expectation_suites != required_suite_paths:
        raise ValueError(
            f"reviewed suite expectations drift from profile: {config['target_key']}"
        )
    suite_records: list[dict[str, str]] = []
    consumers: list[dict[str, Any]] = []
    fixture_paths: list[str] = []
    schema_paths: set[str] = {"schemas/core/aicp-core-message.schema.json"}
    for suite_path in required_suite_paths:
        suite = load_json(ROOT / suite_path)
        suite_records.append(
            {
                "path": suite_path,
                "suite_id": str(suite["suite_id"]),
                "suite_version": str(suite["suite_version"]),
                "suite_digest": file_digest(ROOT / suite_path),
            }
        )
        for field in ("schema_ref", "payload_schema_ref"):
            if isinstance(suite.get(field), str):
                schema_paths.add(str(suite[field]))
        suite_expectations = expectations["suite_expectations"].get(suite_path)
        if not isinstance(suite_expectations, dict):
            raise ValueError(f"reviewed suite expectations missing: {suite_path}")
        source_ids = [str(item["id"]) for item in suite.get("transcripts", [])]
        if set(source_ids) != set(suite_expectations):
            raise ValueError(f"reviewed suite cases drift: {suite_path}")
        for transcript in suite["transcripts"]:
            source_id = str(transcript["id"])
            oracle = suite_expectations[source_id]
            accepted = transcript.get("expect_pass", True) is True
            if oracle.get("accepted") is not accepted:
                raise ValueError(f"reviewed acceptance drift: {suite_path}/{source_id}")
            suite_codes = [
                str(item["test_id"])
                for item in transcript.get("expected_failures", [])
                if isinstance(item, dict)
            ]
            reviewed_codes = [
                str(observation["code"])
                for observation in oracle.get("error_observations", [])
                for _ in range(int(observation["exact_count"]))
            ]
            if reviewed_codes != suite_codes:
                raise ValueError(
                    f"reviewed exact errors drift: {suite_path}/{source_id}"
                )
            fixture = str(transcript["path"])
            fixture_paths.append(fixture)
            case_id = (
                f"EVIDENCE-CONSUMER-{config['case_prefix']}-"
                f"{_bounded_case_token(str(suite['suite_id']))}-"
                f"{_bounded_case_token(source_id)}"
            )
            consumers.append(
                {
                    "case_id": case_id,
                    "source_suite_id": str(suite["suite_id"]),
                    "source_case_id": source_id,
                    "fixture": fixture,
                    "input_digest": file_digest(ROOT / fixture),
                    "accepted": accepted,
                    "expected_error_observations": oracle[
                        "error_observations"
                    ],
                    "expected_degraded": False,
                    "expected_degraded_reasons": [],
                    "expected_skipped_checks": [],
                }
            )

    scenario_path = ROOT / config["scenario_path"]
    scenario_catalog = load_json(scenario_path)
    if scenario_catalog.get("target") != {
        "kind": "product_profile",
        "target_id": config["target_id"],
        "target_version": "0.1",
    }:
        raise ValueError(f"producer scenario target drift: {config['target_key']}")
    producer_scenarios = [
        {
            "case_id": f"EVIDENCE-PRODUCER-{scenario['scenario_id']}",
            "scenario_id": str(scenario["scenario_id"]),
            "artifact_id": f"PROFILE-TRANSCRIPT-{scenario['scenario_id']}",
        }
        for scenario in scenario_catalog["scenarios"]
    ]
    vector_entries: list[dict[str, Any]] = []
    for vector_ref in VECTOR_REFS:
        vector = load_json(ROOT / vector_ref)
        vector_entries.append(
            {
                "case_id": str(vector["vector_id"]),
                "path": vector_ref,
                "input_digest": file_digest(ROOT / vector_ref),
            }
        )
    static_paths = {
        config["profile_path"],
        config["scenario_path"],
        PROFILE_SCENARIO_SCHEMA_PATH.relative_to(ROOT).as_posix(),
        PROFILE_EXPECTATIONS_PATH.relative_to(ROOT).as_posix(),
        "fixtures/keys/GT_public_keys.json",
        "registry/aicp_profiles.json",
        "registry/message_types.json",
        "registry/policy_reason_codes.json",
        "registry/crypto_profiles.json",
        *required_suite_paths,
        *tier1_payload_route_input_paths(),
        *fixture_paths,
        *schema_paths,
        *VECTOR_REFS,
        *scenario_template_paths(),
    }
    required_inputs = [
        {"path": relative, "content_digest": file_digest(ROOT / relative)}
        for relative in sorted(static_paths)
    ]
    return {
        "catalog_version": "1.2",
        "target_key": config["target_key"],
        "target": {
            "kind": "product_profile",
            "target_id": config["target_id"],
            "target_version": "0.1",
        },
        "handler_id": "product_profile_v01",
        "profile_catalog": {
            "path": config["profile_path"],
            "content_digest": file_digest(ROOT / config["profile_path"]),
        },
        "expected_mark": str(profile["compatibility_mark"]),
        "external_execution_mode": "full-profile",
        "required_operations": [
            "describe",
            "canonicalize_hash",
            "validate_transcript",
            "generate_scenario",
        ],
        "required_suite_paths": required_suite_paths,
        "required_suites": suite_records,
        "canonicalization_vectors": vector_entries,
        "producer_scenario_catalog": {
            "path": config["scenario_path"],
            "content_digest": file_digest(scenario_path),
            "schema_path": PROFILE_SCENARIO_SCHEMA_PATH.relative_to(ROOT).as_posix(),
            "schema_digest": file_digest(PROFILE_SCENARIO_SCHEMA_PATH),
        },
        "producer_scenarios": producer_scenarios,
        "consumer_error_ordering": expectations["error_ordering"],
        "consumer_cases": consumers,
        "required_input_artifacts": required_inputs,
    }


def binding_target_catalog_payload(config: dict[str, str]) -> dict[str, Any]:
    suite = load_json(ROOT / config["suite_path"])
    scenario_path = ROOT / config["scenario_path"]
    scenario_schema_path = EVIDENCE_DIR / "live_bindings/live_binding_scenario.schema.json"
    trace_schema_path = EVIDENCE_DIR / "live_bindings/live_binding_trace_v4.schema.json"
    endpoint_schema_path = EVIDENCE_DIR / "live_bindings/live_endpoint_descriptor_v2.schema.json"
    scenarios = load_json(scenario_path)
    expected_target = {
        "kind": "binding",
        "target_id": config["target_id"],
        "target_version": "0.1",
    }
    if scenarios.get("target") != expected_target:
        raise ValueError(f"live scenario target drift: {config['target_key']}")
    static_checks = [
        str(item["test_id"])
        for item in suite.get("checks", [])
        if isinstance(item, dict) and isinstance(item.get("test_id"), str)
    ]
    if config["target_id"] == "BIND-MCP":
        static_checks.extend(
            str(load_json(ROOT / relative)["case_id"])
            for relative in suite["cases"]
        )
    static_paths = {
        config["suite_path"],
        str(suite["schema_ref"]),
        *[str(item) for item in suite["cases"]],
        config["scenario_path"],
        config["spec_path"],
        scenario_schema_path.relative_to(ROOT).as_posix(),
        trace_schema_path.relative_to(ROOT).as_posix(),
        endpoint_schema_path.relative_to(ROOT).as_posix(),
        "conformance/evidence/live_bindings/live_public_scenario_v1.schema.json",
        "fixtures/golden_transcripts/GT-01_happy_path_signed.jsonl",
        "registry/transport_bindings.json",
        "registry/message_types.json",
        "schemas/core/aicp-core-message.schema.json",
    }
    required_inputs = [
        {"path": relative, "content_digest": file_digest(ROOT / relative)}
        for relative in sorted(static_paths)
    ]
    return {
        "catalog_version": "1.0",
        "target_key": config["target_key"],
        "target": expected_target,
        "handler_id": "live_binding_v01",
        "expected_mark": config["expected_mark"],
        "external_execution_mode": "full-binding",
        "required_operations": ["live_server", "live_client"],
        "required_suites": [
            {
                "path": config["suite_path"],
                "suite_id": str(suite["suite_id"]),
                "suite_version": str(suite["suite_version"]),
                "suite_digest": file_digest(ROOT / config["suite_path"]),
            }
        ],
        "live_scenario_catalog": {
            "path": config["scenario_path"],
            "content_digest": file_digest(scenario_path),
            "schema_path": scenario_schema_path.relative_to(ROOT).as_posix(),
            "schema_digest": file_digest(scenario_schema_path),
        },
        "live_trace_schema": {
            "path": trace_schema_path.relative_to(ROOT).as_posix(),
            "content_digest": file_digest(trace_schema_path),
        },
        "endpoint_descriptor_schema": {
            "path": endpoint_schema_path.relative_to(ROOT).as_posix(),
            "content_digest": file_digest(endpoint_schema_path),
        },
        "role_coverage": ["server_under_test", "client_under_test"],
        "live_relevant_static_checks": sorted(set(static_checks)),
        "required_input_artifacts": required_inputs,
    }


def _frozen_release(release_id: str, expected_digest: str) -> dict[str, Any]:
    registry = load_json(TCK_RELEASES_PATH)
    frozen = next(
        (
            item
            for item in registry.get("releases", [])
            if item.get("release_id") == release_id
        ),
        None,
    )
    if not isinstance(frozen, dict):
        raise ValueError(f"frozen evidence TCK record is missing: {release_id}")
    if canonical_digest(frozen) != expected_digest:
        raise ValueError(f"frozen evidence TCK record changed: {release_id}")
    return frozen


def release_registry_payload(
    targets_rendered: str,
    projection_catalog_rendered: str,
    catalogs_rendered: dict[str, str],
    bundle_manifest_rendered: str,
    projection_catalog: dict[str, Any],
    catalogs: dict[str, dict[str, Any]],
    bundle_manifest: dict[str, Any],
) -> dict[str, Any]:
    historical = _frozen_release(
        HISTORICAL_TCK_RELEASE_ID,
        HISTORICAL_RELEASE_RECORD_DIGEST,
    )
    projection_release = _frozen_release(
        TCK_RELEASE_ID,
        FROZEN_TCK_1_1_RECORD_DIGEST,
    )
    profile_release = _frozen_release(
        PROFILE_TCK_RELEASE_ID,
        FROZEN_TCK_1_2_RECORD_DIGEST,
    )
    previous_release = _frozen_release(
        PREVIOUS_TCK_RELEASE_ID,
        FROZEN_TCK_1_3_RECORD_DIGEST,
    )
    frozen_1_4_release = _frozen_release(
        TCK_1_4_RELEASE_ID,
        FROZEN_TCK_1_4_RECORD_DIGEST,
    )
    frozen_1_5_release = _frozen_release(
        TCK_1_5_RELEASE_ID,
        FROZEN_TCK_1_5_RECORD_DIGEST,
    )
    frozen_1_6_release = _frozen_release(
        TCK_1_6_RELEASE_ID,
        FROZEN_TCK_1_6_RECORD_DIGEST,
    )
    frozen_1_7_release = _frozen_release(
        TCK_1_7_RELEASE_ID,
        FROZEN_TCK_1_7_RECORD_DIGEST,
    )
    frozen_1_8_release = _frozen_release(
        TCK_1_8_RELEASE_ID,
        FROZEN_TCK_1_8_RECORD_DIGEST,
    )
    projection_handler = resolve_handler("projection_v1")
    product_handler = resolve_handler("product_profile_v01")
    binding_handler = resolve_handler("live_binding_v01")
    release_targets: list[dict[str, Any]] = [
        {
            "target_key": TARGET_KEY,
            "handler_id": "projection_v1",
            "expected_mark": projection_catalog["expected_mark"],
            "target_catalog": {
                "path": TARGET_CATALOG_PATH.relative_to(ROOT).as_posix(),
                "content_digest": digest_bytes(
                    projection_catalog_rendered.encode("utf-8")
                ),
            },
            "required_suites": [projection_catalog["owning_suite"]],
            "required_input_artifacts": projection_catalog[
                "required_input_artifacts"
            ],
            "canonicalization_vectors": [
                {
                    "case_id": item["case_id"],
                    "path": item["path"],
                    "content_digest": item["input_digest"],
                }
                for item in projection_catalog["canonicalization_vectors"]
            ],
            "mandatory_producer_ids": [
                item["case_id"]
                for item in projection_handler.producer_cases(
                    projection_catalog, "full-capability"
                )
            ],
            "mandatory_consumer_ids": [
                item["case_id"]
                for item in projection_handler.consumer_cases(
                    projection_catalog, "full-capability"
                )
            ],
            "mandatory_case_ids": mandatory_case_ids(
                projection_catalog,
                "full-capability",
                projection_handler,
            ),
        }
    ]
    for config in PROFILE_CONFIGS:
        key = config["target_key"]
        catalog = catalogs[key]
        release_targets.append(
            {
                "target_key": key,
                "handler_id": "product_profile_v01",
                "expected_mark": catalog["expected_mark"],
                "target_catalog": {
                    "path": config["catalog_path"],
                    "content_digest": digest_bytes(
                        catalogs_rendered[key].encode("utf-8")
                    ),
                },
                "profile_catalog": catalog["profile_catalog"],
                "required_suites": catalog["required_suites"],
                "required_input_artifacts": catalog[
                    "required_input_artifacts"
                ],
                "canonicalization_vectors": [
                    {
                        "case_id": item["case_id"],
                        "path": item["path"],
                        "content_digest": item["input_digest"],
                    }
                    for item in catalog["canonicalization_vectors"]
                ],
                "mandatory_producer_ids": [
                    item["case_id"] for item in catalog["producer_scenarios"]
                ],
                "mandatory_consumer_ids": [
                    item["case_id"] for item in catalog["consumer_cases"]
                ],
                "mandatory_case_ids": mandatory_case_ids(
                    catalog,
                    "full-profile",
                    product_handler,
                ),
            }
        )
    for config in BINDING_CONFIGS:
        key = config["target_key"]
        catalog = catalogs[key]
        release_targets.append(
            {
                "target_key": key,
                "handler_id": "live_binding_v01",
                "expected_mark": catalog["expected_mark"],
                "target_catalog": {
                    "path": config["catalog_path"],
                    "content_digest": digest_bytes(
                        catalogs_rendered[key].encode("utf-8")
                    ),
                },
                "required_suites": catalog["required_suites"],
                "required_input_artifacts": catalog["required_input_artifacts"],
                "mandatory_case_ids": mandatory_case_ids(
                    catalog,
                    "full-binding",
                    binding_handler,
                ),
            }
        )
    return {
        "registry_version": "1.9",
        "supersessions": [
            {
                "release_id": HISTORICAL_TCK_RELEASE_ID,
                "status": "superseded-experimental",
                "superseded_by": TCK_RELEASE_ID,
                "frozen_record_digest": HISTORICAL_RELEASE_RECORD_DIGEST,
                "target_registry_schema_digest": HISTORICAL_TARGET_SCHEMA_DIGEST,
                "release_registry_digest": HISTORICAL_RELEASE_REGISTRY_DIGEST,
                "current_strong_eligibility": False,
                "reason": (
                    "Producer answer isolation was insufficient; no real external "
                    "submission depended on this release."
                ),
            }
        ],
        "release_policies": [
            {
                "release_id": HISTORICAL_TCK_RELEASE_ID,
                "lifecycle": "historical",
                "strong_eligible": False,
                "reason": "Known M62 producer answer-isolation defect.",
            },
            {
                "release_id": TCK_RELEASE_ID,
                "lifecycle": "historical",
                "strong_eligible": True,
                "reason": "Exact frozen projection-v1 evidence remains valid; no security revocation applies.",
            },
            {
                "release_id": PROFILE_TCK_RELEASE_ID,
                "lifecycle": "historical",
                "strong_eligible": False,
                "reason": "Incomplete producer-suite semantic closure and generated-artifact multiplicity defect.",
            },
            {
                "release_id": PREVIOUS_TCK_RELEASE_ID,
                "lifecycle": "historical",
                "strong_eligible": False,
                "reason": (
                    "Incomplete message-owner payload-schema closure and "
                    "ordinary-conformance namespace parity."
                ),
            },
            {
                "release_id": TCK_1_4_RELEASE_ID,
                "lifecycle": "historical",
                "strong_eligible": True,
                "reason": (
                    "Corrected message-owner payload-schema closure and "
                    "behavioral conformance parity."
                ),
            },
            {
                "release_id": TCK_1_5_RELEASE_ID,
                "lifecycle": "historical",
                "strong_eligible": False,
                "reason": (
                    "Live trace did not independently encode transport evidence, "
                    "subprocess environment isolation was incomplete, and several "
                    "live transport semantics were incomplete."
                ),
            },
            {
                "release_id": TCK_1_6_RELEASE_ID,
                "lifecycle": "historical",
                "strong_eligible": False,
                "reason": (
                    "Client-under-test runtime response causality and WSS "
                    "certificate verification were not independently challenged."
                ),
            },
            {
                "release_id": TCK_1_7_RELEASE_ID,
                "lifecycle": "historical",
                "strong_eligible": False,
                "reason": (
                    "MCP continuation evidence could reuse a cursor exposed before "
                    "poll-1, and WSS client evidence did not distinguish certificate "
                    "rejection from a TCP-only/non-TLS probe."
                ),
            },
            {
                "release_id": TCK_1_8_RELEASE_ID,
                "lifecycle": "historical",
                "strong_eligible": True,
                "reason": (
                    "Requires first-seen MCP poll continuation evidence and "
                    "repository-observed TLS certificate-rejection classification."
                ),
            },
            {
                "release_id": CURRENT_TCK_RELEASE_ID,
                "lifecycle": "current",
                "strong_eligible": True,
                "reason": (
                    "Completes actual positive-fixture coverage for every registered "
                    "message type and binds the expanded corpus into evidence targets."
                ),
            },
        ],
        "releases": [
            historical,
            projection_release,
            profile_release,
            previous_release,
            frozen_1_4_release,
            frozen_1_5_release,
            frozen_1_6_release,
            frozen_1_7_release,
            frozen_1_8_release,
            {
                "release_id": CURRENT_TCK_RELEASE_ID,
                "status": "experimental",
                "report_schema": {
                    "path": REPORT_SCHEMA_V22_PATH.relative_to(ROOT).as_posix(),
                    "content_digest": file_digest(REPORT_SCHEMA_V22_PATH),
                },
                "target_registry": {
                    "path": TARGETS_PATH.relative_to(ROOT).as_posix(),
                    "schema_path": TARGET_SCHEMA_PATH.relative_to(ROOT).as_posix(),
                    "schema_digest": file_digest(TARGET_SCHEMA_PATH),
                    "content_digest": digest_bytes(
                        targets_rendered.encode("utf-8")
                    ),
                },
                "runner_bundle": {
                    "manifest_path": BUNDLE_MANIFEST_PATH.relative_to(
                        ROOT
                    ).as_posix(),
                    "manifest_digest": digest_bytes(
                        bundle_manifest_rendered.encode("utf-8")
                    ),
                    "paths": [
                        item["path"] for item in bundle_manifest["entries"]
                    ],
                    "digest": bundle_manifest["bundle_digest"],
                },
                "targets": release_targets,
            },
        ],
    }


def generated_payloads() -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, dict[str, Any]],
    dict[str, Any],
    dict[str, Any],
]:
    targets = target_registry_payload()
    projection_catalog = target_catalog_payload()
    profile_catalogs = {
        config["target_key"]: profile_target_catalog_payload(config)
        for config in PROFILE_CONFIGS
    }
    binding_catalogs = {
        config["target_key"]: binding_target_catalog_payload(config)
        for config in BINDING_CONFIGS
    }
    catalogs = {**profile_catalogs, **binding_catalogs}
    bundle_manifest = bundle_manifest_payload()
    targets_rendered = render(targets)
    catalogs_rendered = {
        key: render(value) for key, value in catalogs.items()
    }
    bundle_manifest_rendered = render(bundle_manifest)
    releases = release_registry_payload(
        targets_rendered,
        render(projection_catalog),
        catalogs_rendered,
        bundle_manifest_rendered,
        projection_catalog,
        catalogs,
        bundle_manifest,
    )
    return targets, projection_catalog, catalogs, bundle_manifest, releases


def release_snapshot_payloads(releases: dict[str, Any]) -> dict[str, dict[str, Any]]:
    frozen_1_1 = {
        "registry_version": "1.1",
        "supersessions": releases["supersessions"],
        "releases": releases["releases"][:2],
    }
    if digest_bytes(render(frozen_1_1).encode("utf-8")) != (
        FROZEN_TCK_1_1_REGISTRY_SNAPSHOT_DIGEST
    ):
        raise ValueError("reconstructed evidence TCK 1.1.0 registry snapshot changed")

    frozen_1_2_path = (
        RELEASE_SNAPSHOT_DIR / f"{PROFILE_TCK_RELEASE_ID}.json"
    )
    if frozen_1_2_path.is_file():
        frozen_1_2 = load_json(frozen_1_2_path)
    else:
        if file_digest(TCK_RELEASES_PATH) != FROZEN_TCK_1_2_REGISTRY_SNAPSHOT_DIGEST:
            raise ValueError("cannot bootstrap the exact merged M63 registry snapshot")
        frozen_1_2 = load_json(TCK_RELEASES_PATH)
    if digest_bytes(render(frozen_1_2).encode("utf-8")) != (
        FROZEN_TCK_1_2_REGISTRY_SNAPSHOT_DIGEST
    ):
        raise ValueError("evidence TCK 1.2.0 registry snapshot changed")

    frozen_1_3_path = RELEASE_SNAPSHOT_DIR / f"{PREVIOUS_TCK_RELEASE_ID}.json"
    if not frozen_1_3_path.is_file():
        raise ValueError("frozen evidence TCK 1.3.0 registry snapshot is missing")
    frozen_1_3 = load_json(frozen_1_3_path)
    if digest_bytes(render(frozen_1_3).encode("utf-8")) != (
        FROZEN_TCK_1_3_REGISTRY_SNAPSHOT_DIGEST
    ):
        raise ValueError("evidence TCK 1.3.0 registry snapshot changed")

    frozen_1_4_path = RELEASE_SNAPSHOT_DIR / f"{TCK_1_4_RELEASE_ID}.json"
    if not frozen_1_4_path.is_file():
        raise ValueError("frozen evidence TCK 1.4.0 registry snapshot is missing")
    frozen_1_4 = load_json(frozen_1_4_path)
    if digest_bytes(render(frozen_1_4).encode("utf-8")) != (
        FROZEN_TCK_1_4_REGISTRY_SNAPSHOT_DIGEST
    ):
        raise ValueError("evidence TCK 1.4.0 registry snapshot changed")

    frozen_1_5_path = RELEASE_SNAPSHOT_DIR / f"{TCK_1_5_RELEASE_ID}.json"
    if not frozen_1_5_path.is_file():
        raise ValueError("frozen evidence TCK 1.5.0 registry snapshot is missing")
    frozen_1_5 = load_json(frozen_1_5_path)
    if digest_bytes(render(frozen_1_5).encode("utf-8")) != (
        FROZEN_TCK_1_5_REGISTRY_SNAPSHOT_DIGEST
    ):
        raise ValueError("evidence TCK 1.5.0 registry snapshot changed")

    frozen_1_6_path = RELEASE_SNAPSHOT_DIR / f"{TCK_1_6_RELEASE_ID}.json"
    if not frozen_1_6_path.is_file():
        raise ValueError("frozen evidence TCK 1.6.0 registry snapshot is missing")
    frozen_1_6 = load_json(frozen_1_6_path)
    if digest_bytes(render(frozen_1_6).encode("utf-8")) != (
        FROZEN_TCK_1_6_REGISTRY_SNAPSHOT_DIGEST
    ):
        raise ValueError("evidence TCK 1.6.0 registry snapshot changed")

    frozen_1_7_path = RELEASE_SNAPSHOT_DIR / f"{TCK_1_7_RELEASE_ID}.json"
    if not frozen_1_7_path.is_file():
        raise ValueError("frozen evidence TCK 1.7.0 registry snapshot is missing")
    frozen_1_7 = load_json(frozen_1_7_path)
    if digest_bytes(render(frozen_1_7).encode("utf-8")) != (
        FROZEN_TCK_1_7_REGISTRY_SNAPSHOT_DIGEST
    ):
        raise ValueError("evidence TCK 1.7.0 registry snapshot changed")

    frozen_1_8_path = RELEASE_SNAPSHOT_DIR / f"{TCK_1_8_RELEASE_ID}.json"
    if not frozen_1_8_path.is_file():
        raise ValueError("frozen evidence TCK 1.8.0 registry snapshot is missing")
    frozen_1_8 = load_json(frozen_1_8_path)
    if digest_bytes(render(frozen_1_8).encode("utf-8")) != (
        FROZEN_TCK_1_8_REGISTRY_SNAPSHOT_DIGEST
    ):
        raise ValueError("evidence TCK 1.8.0 registry snapshot changed")

    return {
        TCK_RELEASE_ID: frozen_1_1,
        PROFILE_TCK_RELEASE_ID: frozen_1_2,
        PREVIOUS_TCK_RELEASE_ID: frozen_1_3,
        TCK_1_4_RELEASE_ID: frozen_1_4,
        TCK_1_5_RELEASE_ID: frozen_1_5,
        TCK_1_6_RELEASE_ID: frozen_1_6,
        TCK_1_7_RELEASE_ID: frozen_1_7,
        TCK_1_8_RELEASE_ID: frozen_1_8,
        CURRENT_TCK_RELEASE_ID: releases,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()

    (
        targets,
        projection_catalog,
        catalogs,
        bundle_manifest,
        releases,
    ) = generated_payloads()
    snapshots = release_snapshot_payloads(releases)
    paths = [
        TARGETS_PATH,
        TARGET_CATALOG_PATH,
        *[ROOT / config["catalog_path"] for config in PROFILE_CONFIGS],
        *[ROOT / config["catalog_path"] for config in BINDING_CONFIGS],
        BUNDLE_MANIFEST_PATH,
        TCK_RELEASES_PATH,
        *[
            RELEASE_SNAPSHOT_DIR / f"{release_id}.json"
            for release_id in (
                TCK_RELEASE_ID,
                PROFILE_TCK_RELEASE_ID,
                PREVIOUS_TCK_RELEASE_ID,
                TCK_1_4_RELEASE_ID,
                TCK_1_5_RELEASE_ID,
                TCK_1_6_RELEASE_ID,
                TCK_1_7_RELEASE_ID,
                TCK_1_8_RELEASE_ID,
                CURRENT_TCK_RELEASE_ID,
            )
        ],
    ]
    values = [
        targets,
        projection_catalog,
        *[catalogs[config["target_key"]] for config in PROFILE_CONFIGS],
        *[catalogs[config["target_key"]] for config in BINDING_CONFIGS],
        bundle_manifest,
        releases,
        *[
            snapshots[release_id]
            for release_id in (
                TCK_RELEASE_ID,
                PROFILE_TCK_RELEASE_ID,
                PREVIOUS_TCK_RELEASE_ID,
                TCK_1_4_RELEASE_ID,
                TCK_1_5_RELEASE_ID,
                TCK_1_6_RELEASE_ID,
                TCK_1_7_RELEASE_ID,
                TCK_1_8_RELEASE_ID,
                CURRENT_TCK_RELEASE_ID,
            )
        ],
    ]
    rendered = [render(value) for value in values]
    if args.write:
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
        RELEASE_SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
        for path, content in zip(paths, rendered):
            path.write_text(content, encoding="utf-8")
    else:
        stale = [
            path.relative_to(ROOT).as_posix()
            for path, content in zip(paths, rendered)
            if not path.is_file()
            or path.read_text(encoding="utf-8") != content
        ]
        if stale:
            print(
                "[FAIL] stale evidence framework artifacts: "
                + ", ".join(stale)
            )
            return 1

    errors = [
        *validate_target_registry(targets, enforce_current_scope=True),
        *validate_target_catalog(
            projection_catalog,
            record=next(
                record
                for record in (
                    TargetRecord.from_mapping(item)
                    for item in targets["targets"]
                )
                if record.target_key == TARGET_KEY
            ),
            handler=resolve_handler("projection_v1"),
        ),
    ]
    for item in targets["targets"]:
        if item["target_key"] not in (*PROFILE_TARGET_KEYS, *BINDING_TARGET_KEYS):
            continue
        record = TargetRecord.from_mapping(item)
        errors.extend(
            validate_target_catalog(
                catalogs[record.target_key],
                record=record,
                handler=resolve_handler(record.handler_id),
            )
        )
    errors.extend(
        validate_release_registry(
            releases,
            bundle_manifest=bundle_manifest,
        )
    )
    if errors:
        for error in sorted(set(errors)):
            print(f"[FAIL] {error}")
        return 1
    action = "Generated" if args.write else "OK"
    producer_count = sum(
        len(catalogs[config["target_key"]]["producer_scenarios"])
        for config in PROFILE_CONFIGS
    )
    consumer_count = sum(
        len(catalogs[config["target_key"]]["consumer_cases"])
        for config in PROFILE_CONFIGS
    )
    print(
        f"{action}: three Tier-1 profile targets, {producer_count} producers, "
        f"{consumer_count} consumers, {CURRENT_TCK_RELEASE_ID}; "
        f"{HISTORICAL_TCK_RELEASE_ID}, {TCK_RELEASE_ID}, "
        f"{PROFILE_TCK_RELEASE_ID}, {PREVIOUS_TCK_RELEASE_ID}, and "
        f"{TCK_1_4_RELEASE_ID}, {TCK_1_5_RELEASE_ID}, "
        f"{TCK_1_6_RELEASE_ID}, {TCK_1_7_RELEASE_ID}, and "
        f"{TCK_1_8_RELEASE_ID} retained; "
        "two live binding targets registered."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
