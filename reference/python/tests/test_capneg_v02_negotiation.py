from __future__ import annotations

import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator


ROOT = Path(__file__).resolve().parents[3]
RUNNER_DIR = ROOT / "conformance/capneg_v02_runner"
if str(RUNNER_DIR) not in sys.path:
    sys.path.insert(0, str(RUNNER_DIR))

from aicp_capneg_v02_runner import run_suite  # noqa: E402


def _load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_capneg_v02_has_exact_generated_fixture_totals() -> None:
    positive = _load("fixtures/extensions/capneg_v0_2/positive_cases.json")
    negative = _load("fixtures/extensions/capneg_v0_2/negative_cases.json")
    oracle = _load("fixtures/extensions/capneg_v0_2/oracle_expectations.json")[
        "cases"
    ]
    assert positive["case_count"] == len(positive["cases"]) == 20
    assert negative["case_count"] == len(negative["cases"]) == 104
    assert [case["id"] for case in positive["cases"]] == [
        f"P{index:02d}" for index in range(1, 21)
    ]
    assert [case["id"] for case in negative["cases"]] == [
        f"N{index:02d}" for index in range(1, 105)
    ]
    for case in negative["cases"]:
        assert case["oracle_case_id"] == case["id"]
        expectation = oracle[case["oracle_case_id"]]
        assert expectation["expected_error_observations"]
        for observation in expectation["expected_error_observations"]:
            assert set(observation) == {
                "code",
                "message_index",
                "message_id",
                "exact_count",
            }
            assert observation["exact_count"] >= 1
        final_state = expectation["expected_final_state"]
        assert "state" in final_state
        assert "current_revision" in final_state
        assert "acceptances" in final_state
        assert "rejections" in final_state
        assert "accepted_profile_composition" in final_state


def test_capneg_payload_versions_are_schema_separated() -> None:
    v01_schema = _load("schemas/extensions/ext-capneg-payloads.schema.json")
    v02_schema = _load(
        "schemas/extensions/ext-capneg-v0.2-payloads.schema.json"
    )
    positive = _load("fixtures/extensions/capneg_v0_2/positive_cases.json")
    v02_declaration = positive["cases"][0]["messages"][0]["payload"]
    v01_declaration = json.loads(
        (
            ROOT / "fixtures/extensions/capneg/CN-01_basic_negotiation.jsonl"
        )
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )["payload"]
    v01_validator = Draft202012Validator(
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$ref": "#/$defs/CAPABILITIES_DECLARE",
            "$defs": v01_schema["$defs"],
        }
    )
    v02_validator = Draft202012Validator(
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$ref": "#/$defs/CAPABILITIES_DECLARE",
            "$defs": v02_schema["$defs"],
        }
    )
    assert list(v01_validator.iter_errors(v01_declaration)) == []
    assert list(v02_validator.iter_errors(v02_declaration)) == []
    assert list(v01_validator.iter_errors(v02_declaration))
    assert list(v02_validator.iter_errors(v01_declaration))
    for case in positive["cases"]:
        for message in case["messages"]:
            if message["message_type"].startswith("CAPABILITIES_"):
                assert message["payload"]["capneg_version"] == "0.2"


def test_capneg_v02_full_suite_emits_only_its_direct_mark() -> None:
    report = run_suite(
        ROOT / "conformance/extensions/CN_CAPNEG_0.2.json"
    )
    assert report["passed"] is True
    assert report["degraded"] is False
    assert report["positive_cases"] == 20
    assert report["negative_cases"] == 104
    assert report["compatibility_marks"] == ["AICP-EXT-CAPNEG-0.2"]


def test_capneg_v02_missing_dependencies_suppress_marks() -> None:
    no_schema = run_suite(
        ROOT / "conformance/extensions/CN_CAPNEG_0.2.json",
        simulate_no_jsonschema=True,
    )
    assert no_schema["passed"] is True
    assert no_schema["degraded"] is True
    assert no_schema["degraded_reasons"]
    assert no_schema["skipped_checks"]
    assert no_schema["compatibility_marks"] == []

    no_crypto = run_suite(
        ROOT / "conformance/extensions/CN_CAPNEG_0.2.json",
        simulate_no_crypto=True,
    )
    assert no_crypto["passed"] is True
    assert no_crypto["degraded"] is True
    assert no_crypto["degraded_reasons"]
    assert no_crypto["skipped_checks"]
    assert no_crypto["skipped_case_ids"]
    assert no_crypto["compatibility_marks"] == []


def test_projection_v2_is_internal_and_has_a_separate_evidence_mark() -> None:
    report = run_suite(
        ROOT / "conformance/extensions/OR_SESSION_STATE_PROJECTION_V2.json"
    )
    assert report["passed"] is True
    assert report["degraded"] is False
    assert report["positive_cases"] == 4
    assert report["negative_cases"] == 9
    assert report["compatibility_marks"] == [
        "AICP-Evidence-SESSION-STATE-PROJECTION-v2"
    ]
