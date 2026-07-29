from __future__ import annotations

import copy
import json
import shutil
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
RUNNER_DIR = ROOT / "conformance/capneg_v02_runner"
SCRIPTS = ROOT / "scripts"
for path in (RUNNER_DIR, SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from aicp_ref_capneg_v02.session_state_v2 import (  # noqa: E402
    validate_session_state_projection_v2,
)
from aicp_ref_capneg_v02.state_machine import reduce_capneg_v02  # noqa: E402
from generate_profile_composition_registry import build_registry  # noqa: E402
import generate_capneg_v02_fixtures as fixture_generator  # noqa: E402
from validation import normalize_observations, validate_messages  # noqa: E402


def load(relative: str):
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


RULES = load("registry/aicp_profile_composition_rules.json")
REASONS = {entry["id"] for entry in load("registry/capneg_reason_codes.json")}
KEYS = load("fixtures/keys/GT_public_keys.json")
EXTENSIONS = {entry["id"] for entry in load("registry/extension_ids.json")}
MESSAGES = {entry["id"] for entry in load("registry/message_types.json")}
NEGATIVE = {
    case["id"]: case
    for case in load("fixtures/extensions/capneg_v0_2/negative_cases.json")[
        "cases"
    ]
}


def execute(case_id: str) -> tuple[list[dict], dict]:
    case = NEGATIVE[case_id]
    messages = copy.deepcopy(case["messages"])
    invalid, transcript_issues = validate_messages(
        messages,
        message_schema=load("schemas/core/aicp-core-message.schema.json"),
        capneg_schema=load(
            "schemas/extensions/ext-capneg-v0.2-payloads.schema.json"
        ),
        projection_schema=load(
            "schemas/extensions/session-state-projection-v2.schema.json"
        ),
        core_payload_schema=load("schemas/core/aicp-core-payloads.schema.json"),
        core_contract_schema=load(
            "schemas/core/aicp-core-contract.schema.json"
        ),
        registered_messages=MESSAGES,
        key_map=KEYS,
        jsonschema_available=True,
        crypto_available=True,
    )
    state = reduce_capneg_v02(
        messages,
        rules=RULES,
        registered_reason_codes=REASONS,
        key_map=KEYS,
        invalid_messages=invalid,
    )
    issues = list(state["issues"]) + transcript_issues
    for index, message in enumerate(messages):
        if index not in invalid and message.get("message_type") == "STATE_SYNC_RESPONSE":
            issues.extend(
                validate_session_state_projection_v2(
                    message,
                    messages,
                    index,
                    registered_extensions=EXTENSIONS,
                    rules=RULES,
                    registered_reason_codes=REASONS,
                    key_map=KEYS,
                    invalid_messages=invalid,
                )
            )
    return normalize_observations(issues), state


def test_direct_load_bearing_cases_use_hand_authored_codes_and_states() -> None:
    expected = {
        "N52": (
            {"CAPNEG_TRANSCRIPT_SESSION_MISMATCH", "DECISION_SESSION_MISMATCH"},
            "PARTIALLY_ACCEPTED",
        ),
        "N53": (
            {"CAPNEG_TRANSCRIPT_CONTRACT_MISMATCH", "DECISION_CONTRACT_MISMATCH"},
            "PARTIALLY_ACCEPTED",
        ),
        "N56": ({"AUTHENTICATED_ACCEPTANCE_SIGNATURE_REQUIRED"}, "PARTIALLY_ACCEPTED"),
        "N58": (
            {
                "ACCEPTANCE_SIGNATURE_INVALID",
                "AUTHENTICATED_ACCEPTANCE_SIGNATURE_REQUIRED",
            },
            "ACCEPTED",
        ),
        "N59": (
            {
                "CAPNEG_SIGNATURE_INVALID",
                "MISSING_DECLARATION_BINDING",
                "PROFILE_SET_UNSUPPORTED",
                "SELECTION_OUTSIDE_DECLARATION",
            },
            "COLLECTING_DECLARATIONS",
        ),
        "N60": ({"CAPNEG_SIGNATURE_INVALID"}, "COLLECTING_DECLARATIONS"),
        "N61": ({"CAPNEG_SIGNATURE_INVALID"}, "PROPOSED"),
        "N69": ({"STALE_CAPABILITIES_DECLARATION"}, "PROPOSED"),
        "N73": ({"REVISION_REJECTED"}, "REJECTED"),
        "N76": ({"PARTICIPANT_REQUIRED_CRYPTO_MISSING"}, "COLLECTING_DECLARATIONS"),
        "N77": ({"SELECTION_OUTSIDE_DECLARATION"}, "COLLECTING_DECLARATIONS"),
        "N78": ({"SELECTION_OUTSIDE_DECLARATION"}, "COLLECTING_DECLARATIONS"),
        "N79": (
            {
                "NEGOTIATION_SESSION_MISMATCH",
                "NEGOTIATION_SUPERSESSION_CONTEXT_MISMATCH",
            },
            "ACCEPTED",
        ),
        "N83": (
            {
                "PROJECTION_ACCEPTANCE_NOT_ESTABLISHED",
                "PROJECTION_ACCEPTED_RESULT_HASH_MISMATCH",
                "PROJECTION_PROFILE_SET_MISMATCH",
            },
            "ACCEPTED",
        ),
        "N88": (
            {"CONTRACT_ID_MISMATCH", "CORE_CONTRACT_SCHEMA_INVALID"},
            "ACCEPTED",
        ),
    }
    for case_id, (expected_codes, expected_state) in expected.items():
        observations, state = execute(case_id)
        assert {item["code"] for item in observations} == expected_codes, case_id
        assert state["state"] == expected_state, case_id


def test_fixture_expectations_have_no_production_semantic_import_path() -> None:
    forbidden = {
        "aicp_ref_capneg_v02.profile_composition",
        "aicp_ref_capneg_v02.state_machine",
        "aicp_ref_capneg_v02.session_state_v2",
        "conformance.capneg_v02_runner",
        "aicp_capneg_v02_runner",
    }
    for relative in (
        "scripts/generate_capneg_v02_fixtures.py",
        "scripts/capneg_v02_fixture_model.py",
    ):
        source = (ROOT / relative).read_text(encoding="utf-8")
        assert forbidden.isdisjoint(
            {name for name in forbidden if name in source}
        ), relative


def test_reviewed_oracle_is_explicit_and_complete() -> None:
    oracle = load("fixtures/extensions/capneg_v0_2/oracle_expectations.json")
    expected_ids = {
        *(f"P{index:02d}" for index in range(1, 18)),
        *(f"N{index:02d}" for index in range(1, 99)),
    }
    assert set(oracle["cases"]) == expected_ids
    state_fields = {
        "state",
        "latest_declarations",
        "negotiation_id",
        "current_revision",
        "proposal_message_id",
        "acceptances",
        "rejections",
        "accepted_profile_composition",
        "accepted_result_hash",
        "superseded_negotiations",
        "bound_contracts",
        "negotiations",
    }
    for expectation in oracle["cases"].values():
        assert set(expectation["expected_final_state"]) == state_fields
        for observation in expectation["expected_error_observations"]:
            assert set(observation) == {
                "code",
                "message_index",
                "message_id",
                "exact_count",
            }


def test_oracle_negative_controls_detect_five_broken_reducers() -> None:
    oracle = load("fixtures/extensions/capneg_v0_2/oracle_expectations.json")[
        "cases"
    ]
    controls = {
        "wrong-session acceptance accepted": "N52",
        "wrong signer accepted": "N56",
        "state mutates after rejection": "N73",
        "participant-required crypto ignored": "N76",
        "future state used for projection": "N83",
    }
    for label, case_id in controls.items():
        expected = oracle[case_id]
        broken = {
            "expected_error_observations": [],
            "expected_final_state": {
                **expected["expected_final_state"],
                "state": "ACCEPTED",
            },
        }
        assert broken["expected_error_observations"] != expected[
            "expected_error_observations"
        ], label
        assert broken != {
            "expected_error_observations": expected[
                "expected_error_observations"
            ],
            "expected_final_state": expected["expected_final_state"],
        }, label


def test_oracle_rejects_right_code_at_wrong_message() -> None:
    expected = load(
        "fixtures/extensions/capneg_v0_2/oracle_expectations.json"
    )["cases"]["N52"]["expected_error_observations"]
    wrong_origin = copy.deepcopy(expected)
    wrong_origin[0]["message_index"] = 3
    wrong_origin[0]["message_id"] = "m4"
    assert wrong_origin != expected


def test_profile_registry_generator_is_hermetic(tmp_path: Path) -> None:
    for relative in (
        "registry/aicp_profiles.json",
        "conformance",
    ):
        source = ROOT / relative
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, destination)
        else:
            shutil.copy2(source, destination)

    actual = build_registry(root=tmp_path)
    assert actual == load("registry/aicp_profile_composition_rules.json")

    registry_path = tmp_path / "registry/aicp_profiles.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry[0]["required_extensions"] = ["EXT-CAPNEG"]
    registry_path.write_text(json.dumps(registry), encoding="utf-8")
    mutated = build_registry(root=tmp_path)
    assert mutated != actual

    suite_path = tmp_path / actual["profiles"][0]["required_suites"][0]
    suite_path.unlink()
    with pytest.raises(ValueError, match="unresolved suite"):
        build_registry(root=tmp_path)


def test_capneg_fixture_generator_uses_only_the_configured_root(
    tmp_path: Path,
) -> None:
    for relative in (
        "registry/aicp_profile_composition_rules.json",
        "registry/capneg_reason_codes.json",
        "fixtures/keys/TEST_private_keys.json",
        "fixtures/keys/GT_public_keys.json",
        "fixtures/extensions/capneg_v0_2/oracle_expectations.json",
    ):
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, destination)
    try:
        fixture_generator.configure_root(tmp_path)
        baseline = fixture_generator.positive_cases()[0]
        oracle_path = (
            tmp_path
            / "fixtures/extensions/capneg_v0_2/oracle_expectations.json"
        )
        oracle = json.loads(oracle_path.read_text(encoding="utf-8"))
        oracle["cases"]["P01"]["expected_final_state"]["state"] = "TEMP_ONLY"
        oracle_path.write_text(json.dumps(oracle), encoding="utf-8")
        mutated = fixture_generator.positive_cases()[0]
        assert baseline["expected_final_state"]["state"] != "TEMP_ONLY"
        assert mutated["expected_final_state"]["state"] == "TEMP_ONLY"
        oracle_path.unlink()
        with pytest.raises(FileNotFoundError):
            fixture_generator.positive_cases()
    finally:
        fixture_generator.configure_root(ROOT)
