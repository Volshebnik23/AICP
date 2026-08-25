from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from producer_payload_schema_router import (
    payload_route_errors,
    tier1_scenarios,
)


ROOT = Path(__file__).resolve().parents[2]


# This table is an implementation dispatch contract, not a copied suite catalog.
# Coverage is derived from suite.checks[].test_id at runtime and validation fails
# if a mandatory ID has no entry here.
CHECK_IMPLEMENTATIONS: dict[str, tuple[str, str]] = {
    "CT-SCHEMA-JSONL-01": ("executed_common_check", "core envelope schema"),
    "CT-MESSAGE-TYPE-REGISTRY-01": ("executed_common_check", "message type registry"),
    "CT-PAYLOAD-SCHEMA-01": ("executed_common_check", "version-selected payload schema router"),
    "CN-PAYLOAD-SCHEMA-01": ("executed_common_check", "version-selected payload schema router"),
    "CT-HASH-CHAIN-01": ("executed_common_check", "message hash chain"),
    "CT-PREV-MSG-REQUIRED-01": ("executed_common_check", "previous-message requirement"),
    "CT-INVARIANTS-01": ("executed_common_check", "session/contract/message invariants"),
    "CT-CONTRACT-ID-01": ("executed_common_check", "contract envelope identity"),
    "CT-SIGNATURE-HASH-01": ("executed_common_check", "signature object hash"),
    "CT-SIGNATURE-STRUCTURE-01": ("executed_common_check", "signature structure"),
    "CT-MESSAGE-HASH-01": ("executed_common_check", "canonical message hash"),
    "CT-SIGNATURE-VERIFY-01": ("executed_common_check", "Ed25519 signature verification"),
    "CT-SEQUENCE-01": ("executed_scenario_sequence_check", "private exact flow contract"),
    "CT-CONTRACT-SCHEMA-01": ("executed_suite_semantic_check", "Core contract schema"),
    "CT-POLICY-CATEGORIES-01": ("executed_suite_semantic_check", "Core policy registry semantics"),
    "CN-DOWNGRADE-01": ("executed_suite_semantic_check", "CAPNEG downgrade prevention"),
    "CN-AICP-PROFILE-NEGOTIATION-01": ("executed_suite_semantic_check", "profile negotiation"),
    "CN-AUTHENTICATED-CRYPTO-01": ("executed_suite_semantic_check", "profile crypto requirements"),
    "CN-PROFILE-REJECT-SEMANTICS-01": ("executed_suite_semantic_check", "profile rejection semantics"),
    "CN-REASON-CODES-01": ("executed_suite_semantic_check", "CAPNEG reason registry"),
    "CN-PRIVACY-MODES-01": ("executed_suite_semantic_check", "privacy mode registry"),
    "CN-NEGRESULT-HASH-01": ("executed_suite_semantic_check", "negotiation result hash"),
    "CN-CONTRACT-BIND-01": ("executed_suite_semantic_check", "contract negotiation binding"),
    "CN-BINDINGS-01": ("executed_suite_semantic_check", "transport binding negotiation"),
    "CN-CHANNEL-PROPERTIES-01": ("executed_suite_semantic_check", "channel property intersection"),
    "PE-REASON-CODES-01": ("executed_suite_semantic_check", "policy reason registry"),
    "PE-CONTEXT-HASH-01": ("executed_suite_semantic_check", "policy context hash"),
    "PE-ATTEST-01": ("executed_suite_semantic_check", "policy decision attestation binding"),
    "ENF-GATE-01": ("executed_suite_semantic_check", "blocking enforcement gate"),
    "ENF-SANCTION-CODES-01": ("executed_suite_semantic_check", "sanction registry"),
    "ENF-AUTH-01": ("executed_suite_semantic_check", "authorized enforcer"),
    "RS-RESUME-MATCH-01": ("executed_suite_semantic_check", "resume correlation and head"),
    "RS-ACTIONS-01": ("executed_suite_semantic_check", "recommended action registry"),
    "RS-LOOP-01": ("executed_suite_semantic_check", "no-progress loop detection"),
    "OR-OBJECT-HASH-01": ("executed_suite_semantic_check", "object reference hash"),
    "ID-AID-01": ("executed_suite_semantic_check", "agent identity document reference"),
    "ID-ANN-01": ("executed_suite_semantic_check", "identity announcement binding"),
    "ID-ROT-01": ("executed_suite_semantic_check", "key rotation cross-signatures"),
    "ID-REVOKE-01": ("executed_suite_semantic_check", "identity key revocation"),
    "ID-MIGRATE-01": ("executed_suite_semantic_check", "identity migration AID binding"),
    "DI-OBJ-01": ("executed_suite_semantic_check", "subject binding object reference"),
    "DI-ISSUE-01": ("executed_suite_semantic_check", "subject binding issuance"),
    "DI-SIGNED-01": ("executed_suite_semantic_check", "signed binding lifecycle message"),
    "DI-ACT-01": ("executed_suite_semantic_check", "acting binding"),
    "DI-EXPIRY-01": ("executed_suite_semantic_check", "binding expiry"),
    "DI-REVOKE-01": ("executed_suite_semantic_check", "binding revocation"),
}


SEMANTIC_PARITY_EVIDENCE: dict[str, dict[str, str]] = {
    "core_envelope_hash_signature": {
        "parity_mode": "shared_implementation",
        "evidence": "Core schemas plus aicp_ref hashing/signature helpers",
    },
    "core_payload_schemas": {
        "parity_mode": "shared_implementation",
        "evidence": "suite payload_schema_map plus _runner_context validator builder",
    },
    "extension_payload_schemas": {
        "parity_mode": "shared_implementation",
        "evidence": "suite payload_schema_map plus _runner_context validator builder",
    },
    "private_sequence": {
        "parity_mode": "differential_test",
        "evidence": "test_m63_payload_semantic_parity_correction.py",
    },
    "core_contract": {
        "parity_mode": "differential_test",
        "evidence": "test_m63_payload_semantic_parity_correction.py",
    },
    "core_policy_categories": {
        "parity_mode": "differential_test",
        "evidence": "evidence_identifier_rules.is_broad_namespaced_identifier plus differential corpus",
    },
    "capneg_reason_codes": {
        "parity_mode": "differential_test",
        "evidence": "test_m63_payload_semantic_parity_correction.py",
    },
    "capneg_privacy_modes": {
        "parity_mode": "differential_test",
        "evidence": "evidence_identifier_rules.is_vendor_or_org_namespaced_identifier plus differential corpus",
    },
    "capneg_bindings": {
        "parity_mode": "differential_test",
        "evidence": "test_m63_payload_semantic_parity_correction.py",
    },
    "capneg_channel_properties": {
        "parity_mode": "differential_test",
        "evidence": "test_m63_payload_semantic_parity_correction.py",
    },
    "policy_reason_codes": {
        "parity_mode": "differential_test",
        "evidence": "evidence_identifier_rules.is_vendor_or_org_namespaced_identifier plus differential corpus",
    },
    "policy_context_hash": {
        "parity_mode": "shared_implementation",
        "evidence": "aicp_ref.hashing.object_hash",
    },
    "policy_attestation": {
        "parity_mode": "differential_test",
        "evidence": "test_m65_message_surface_completion.py",
    },
    "enforcement_sanctions": {
        "parity_mode": "differential_test",
        "evidence": "evidence_identifier_rules.is_broad_namespaced_identifier plus differential corpus",
    },
    "enforcement_gate_authorization": {
        "parity_mode": "differential_test",
        "evidence": "test_m63_payload_semantic_parity_correction.py",
    },
    "resume_semantics": {
        "parity_mode": "differential_test",
        "evidence": "test_m63_payload_semantic_parity_correction.py",
    },
    "object_hash": {
        "parity_mode": "shared_implementation",
        "evidence": "aicp_ref.hashing.object_hash",
    },
    "identity_lifecycle": {
        "parity_mode": "differential_test",
        "evidence": "test_m63_payload_semantic_parity_correction.py",
    },
    "delegated_identity": {
        "parity_mode": "differential_test",
        "evidence": "test_m63_payload_semantic_parity_correction.py",
    },
}


def parity_family(check_id: str) -> str:
    if check_id in {
        "CT-SCHEMA-JSONL-01",
        "CT-MESSAGE-TYPE-REGISTRY-01",
        "CT-HASH-CHAIN-01",
        "CT-PREV-MSG-REQUIRED-01",
        "CT-INVARIANTS-01",
        "CT-CONTRACT-ID-01",
        "CT-SIGNATURE-HASH-01",
        "CT-SIGNATURE-STRUCTURE-01",
        "CT-MESSAGE-HASH-01",
        "CT-SIGNATURE-VERIFY-01",
    }:
        return "core_envelope_hash_signature"
    exact = {
        "CT-PAYLOAD-SCHEMA-01": "core_payload_schemas",
        "CN-PAYLOAD-SCHEMA-01": "extension_payload_schemas",
        "CT-SEQUENCE-01": "private_sequence",
        "CT-CONTRACT-SCHEMA-01": "core_contract",
        "CT-POLICY-CATEGORIES-01": "core_policy_categories",
        "CN-REASON-CODES-01": "capneg_reason_codes",
        "CN-PRIVACY-MODES-01": "capneg_privacy_modes",
        "CN-CHANNEL-PROPERTIES-01": "capneg_channel_properties",
        "PE-REASON-CODES-01": "policy_reason_codes",
        "PE-CONTEXT-HASH-01": "policy_context_hash",
        "PE-ATTEST-01": "policy_attestation",
        "ENF-SANCTION-CODES-01": "enforcement_sanctions",
        "OR-OBJECT-HASH-01": "object_hash",
    }
    if check_id in exact:
        return exact[check_id]
    if check_id.startswith("CN-"):
        return "capneg_bindings"
    if check_id.startswith("ENF-"):
        return "enforcement_gate_authorization"
    if check_id.startswith("RS-"):
        return "resume_semantics"
    if check_id.startswith("ID-"):
        return "identity_lifecycle"
    if check_id.startswith("DI-"):
        return "delegated_identity"
    raise ValueError(f"producer semantic check has no parity family: {check_id}")


def semantic_parity_inventory() -> list[dict[str, Any]]:
    covered: dict[str, list[str]] = defaultdict(list)
    for check_id in CHECK_IMPLEMENTATIONS:
        covered[parity_family(check_id)].append(check_id)
    return [
        {
            "family": family,
            **SEMANTIC_PARITY_EVIDENCE[family],
            "check_ids": sorted(check_ids),
        }
        for family, check_ids in sorted(covered.items())
    ]


PRIVATE_FLOW_SEQUENCES: dict[str, tuple[str, ...]] = {
    "core_contract_action": ("CONTRACT_PROPOSE", "CONTRACT_ACCEPT", "ATTEST_ACTION"),
    "core_conflict_choose": (
        "CONTRACT_PROPOSE", "CONTRACT_ACCEPT", "CONTEXT_AMEND", "CONTEXT_AMEND", "RESOLVE_CONFLICT"
    ),
    "core_consent_grant": ("CONTRACT_PROPOSE", "CONTRACT_ACCEPT", "CONTEXT_AMEND", "ATTEST_ACTION"),
    "core_consent_revoke": (
        "CONTRACT_PROPOSE", "CONTRACT_ACCEPT", "CONTEXT_AMEND", "CONTEXT_AMEND", "ATTEST_ACTION"
    ),
    "core_resync": (
        "CONTRACT_PROPOSE", "CONTRACT_ACCEPT", "STATE_SYNC_REQUEST", "STATE_SYNC_RESPONSE", "CONTEXT_AMEND"
    ),
    "core_error": ("ERROR",),
    "profile_accept_contract": (
        "CAPABILITIES_DECLARE", "CAPABILITIES_DECLARE", "CAPABILITIES_PROPOSE", "CAPABILITIES_ACCEPT",
        "CONTRACT_PROPOSE", "CONTRACT_ACCEPT",
    ),
    "profile_reject": ("CAPABILITIES_DECLARE", "CAPABILITIES_PROPOSE", "CAPABILITIES_REJECT"),
    "policy_allow_delivery": (
        "CONTRACT_PROPOSE", "CONTRACT_ACCEPT", "POLICY_EVAL_REQUEST", "POLICY_EVAL_RESULT",
        "CONTENT_MESSAGE", "ENFORCEMENT_VERDICT", "CONTENT_DELIVER",
    ),
    "policy_deny_block": (
        "CONTRACT_PROPOSE", "CONTRACT_ACCEPT", "POLICY_EVAL_REQUEST", "POLICY_EVAL_RESULT",
        "CONTENT_MESSAGE", "ENFORCEMENT_VERDICT",
    ),
    "resume_in_sync": (
        "CONTRACT_PROPOSE", "CONTRACT_ACCEPT", "ATTEST_ACTION", "RESUME_REQUEST", "RESUME_RESPONSE"
    ),
    "resume_needs_resync": (
        "CONTRACT_PROPOSE", "CONTRACT_ACCEPT", "ATTEST_ACTION", "ATTEST_ACTION", "RESUME_REQUEST",
        "RESUME_RESPONSE", "STATE_SYNC_REQUEST", "STATE_SYNC_RESPONSE",
    ),
    "object_retrieval": ("OBJECT_REQUEST", "OBJECT_RESPONSE"),
    "identity_announce_use": ("CONTRACT_PROPOSE", "CONTRACT_ACCEPT", "IDENTITY_ANNOUNCE", "ATTEST_ACTION"),
    "identity_rotate_use": (
        "CONTRACT_PROPOSE", "CONTRACT_ACCEPT", "IDENTITY_ANNOUNCE", "KEY_ROTATION", "ATTEST_ACTION"
    ),
    "identity_revoke_clean": (
        "CONTRACT_PROPOSE", "CONTRACT_ACCEPT", "IDENTITY_ANNOUNCE", "KEY_ROTATION", "KEY_REVOKE"
    ),
    "binding_issue_use": (
        "CONTRACT_PROPOSE", "CONTRACT_ACCEPT", "IDENTITY_ANNOUNCE", "IDENTITY_ANNOUNCE",
        "SUBJECT_BINDING_ISSUE", "ATTEST_ACTION",
    ),
    "binding_revoke_clean": (
        "CONTRACT_PROPOSE", "CONTRACT_ACCEPT", "IDENTITY_ANNOUNCE", "IDENTITY_ANNOUNCE",
        "SUBJECT_BINDING_ISSUE", "SUBJECT_BINDING_REVOKE",
    ),
}


def load_suite_checks(suite_paths: list[str] | tuple[str, ...]) -> list[tuple[str, str]]:
    checks: list[tuple[str, str]] = []
    for relative in suite_paths:
        suite = json.loads((ROOT / relative).read_text(encoding="utf-8"))
        suite_id = str(suite.get("suite_id"))
        for item in suite.get("checks", []):
            if isinstance(item, dict) and isinstance(item.get("test_id"), str):
                checks.append((suite_id, str(item["test_id"])))
    return checks


def unknown_suite_checks(suite_paths: list[str] | tuple[str, ...]) -> list[str]:
    return sorted(
        {
            check_id
            for _, check_id in load_suite_checks(suite_paths)
            if check_id not in CHECK_IMPLEMENTATIONS
        }
    )


def producer_check_inventory(scenarios: list[dict[str, Any]]) -> list[dict[str, Any]]:
    exercising: dict[tuple[str, str], set[str]] = defaultdict(set)
    suite_paths: set[str] = set()
    for scenario in scenarios:
        scenario_id = str(scenario.get("scenario_id"))
        for relative in scenario.get("required_suites", []):
            if not isinstance(relative, str):
                continue
            suite_paths.add(relative)
            for suite_id, check_id in load_suite_checks([relative]):
                exercising[(suite_id, check_id)].add(scenario_id)
    inventory: list[dict[str, Any]] = []
    for suite_id, check_id in load_suite_checks(sorted(suite_paths)):
        implementation = CHECK_IMPLEMENTATIONS.get(check_id)
        inventory.append(
            {
                "suite": suite_id,
                "check_id": check_id,
                "execution_kind": implementation[0] if implementation else "unimplemented",
                "implementation": implementation[1] if implementation else "unimplemented",
                "parity_family": (
                    parity_family(check_id) if implementation else "unimplemented"
                ),
                "parity_evidence": (
                    SEMANTIC_PARITY_EVIDENCE[parity_family(check_id)]
                    if implementation
                    else None
                ),
                "producer_scenarios": sorted(exercising[(suite_id, check_id)]),
            }
        )
    return inventory


def suite_coverage_errors(scenarios: list[dict[str, Any]]) -> list[str]:
    paths = sorted(
        {
            relative
            for scenario in scenarios
            for relative in scenario.get("required_suites", [])
            if isinstance(relative, str)
        }
    )
    errors = [
        f"mandatory producer suite check has no execution implementation: {check_id}"
        for check_id in unknown_suite_checks(paths)
    ]
    errors.extend(
        payload_route_errors(tier1_scenarios(), PRIVATE_FLOW_SEQUENCES)
    )
    for scenario in scenarios:
        flow_id = scenario.get("flow_id")
        if "CT-SEQUENCE-01" in {
            check_id for _, check_id in load_suite_checks(scenario.get("required_suites", []))
        } and flow_id not in PRIVATE_FLOW_SEQUENCES:
            errors.append(f"producer scenario has no private sequence contract: {flow_id}")
    for item in producer_check_inventory(scenarios):
        if not item["producer_scenarios"]:
            errors.append(
                f"mandatory producer suite check is not exercised: {item['suite']}/{item['check_id']}"
            )
        if not isinstance(item.get("parity_evidence"), dict):
            errors.append(
                f"mandatory producer suite check lacks parity evidence: {item['suite']}/{item['check_id']}"
            )
    return sorted(set(errors))


def sequence_errors(flow_id: str, messages: list[dict[str, Any]]) -> list[str]:
    expected = PRIVATE_FLOW_SEQUENCES.get(flow_id)
    if expected is None:
        return [f"unknown producer flow: {flow_id}"]
    observed = tuple(str(message.get("message_type")) for message in messages)
    if observed != expected:
        return [
            "generated transcript message sequence differs from the private flow contract: "
            f"expected={list(expected)}, observed={list(observed)}"
        ]
    return []
