from __future__ import annotations

import copy
import json
import shutil
import sys
from pathlib import Path
from typing import Any, Callable

import pytest


ROOT = Path(__file__).resolve().parents[3]
RUNNER_DIR = ROOT / "conformance/capneg_v02_runner"
SCRIPTS = ROOT / "scripts"
for path in (RUNNER_DIR, SCRIPTS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from aicp_capneg_v02_runner import (  # noqa: E402
    _load_without_duplicate_keys,
    evaluate_case,
    run_suite,
)
from aicp_ref_capneg_v02.profile_composition import (  # noqa: E402
    resolve_profile_composition,
)
from aicp_ref_capneg_v02.state_machine import reduce_capneg_v02  # noqa: E402
from generate_profile_composition_registry import build_registry  # noqa: E402
import generate_capneg_v02_fixtures as fixture_generator  # noqa: E402
from validation import normalize_observations  # noqa: E402


def load(relative: str) -> Any:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


RULES = load("registry/aicp_profile_composition_rules.json")
CAPNEG_SUITE = ROOT / "conformance/extensions/CN_CAPNEG_0.2.json"
STATE_FIELDS = {
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


def _broken_reducer(
    removed_codes: set[str],
) -> Callable[..., dict[str, Any]]:
    def reducer(*args: Any, **kwargs: Any) -> dict[str, Any]:
        snapshot = reduce_capneg_v02(*args, **kwargs)
        snapshot["issues"] = [
            item
            for item in snapshot["issues"]
            if item.get("code") not in removed_codes
        ]
        snapshot["errors"] = [
            item["code"] for item in snapshot["issues"]
        ]
        snapshot["state"] = "ACCEPTED"
        for negotiation in snapshot["negotiations"]:
            if negotiation["negotiation_id"] == snapshot["negotiation_id"]:
                negotiation["state"] = "ACCEPTED"
        return snapshot

    return reducer


def test_real_oracle_mutation_controls_fail_the_suite_comparator() -> None:
    controls = {
        "N52": {
            "CAPNEG_TRANSCRIPT_SESSION_MISMATCH",
            "DECISION_SESSION_MISMATCH",
        },
        "N56": {"AUTHENTICATED_ACCEPTANCE_SIGNATURE_REQUIRED"},
        "N73": {"REVISION_REJECTED"},
        "N76": {"PARTICIPANT_REQUIRED_CRYPTO_MISSING"},
    }
    for case_id, removed_codes in controls.items():
        report = run_suite(
            CAPNEG_SUITE,
            case_ids={case_id},
            reducer_function=_broken_reducer(removed_codes),
        )
        assert report["passed"] is False, case_id
        assert [
            (failure["test_id"], failure["case_id"])
            for failure in report["failures"]
        ] == [
            ("RUNNER-EXPECTED-ERRORS-01", case_id),
            ("RUNNER-EXPECTED-STATE-01", case_id),
        ]
        assert next(iter(removed_codes)) in report["failures"][0]["detail"]

    def final_state_projection(
        message: dict[str, Any],
        transcript: list[dict[str, Any]],
        message_index: int,
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        final = reduce_capneg_v02(
            transcript,
            rules=kwargs["rules"],
            registered_reason_codes=kwargs["registered_reason_codes"],
            key_map=kwargs["key_map"],
            crypto_available=kwargs["crypto_available"],
            invalid_messages=kwargs["invalid_messages"],
        )
        projection = message["payload"]["session_state"]
        assert final["state"] == "ACCEPTED"
        assert (
            projection["accepted_negotiation_result_hash"]
            == final["accepted_result_hash"]
        )
        return []

    report = run_suite(
        CAPNEG_SUITE,
        case_ids={"N83"},
        projection_validator_function=final_state_projection,
    )
    assert report["passed"] is False
    assert [
        (failure["test_id"], failure["case_id"])
        for failure in report["failures"]
    ] == [("RUNNER-EXPECTED-ERRORS-01", "N83")]
    assert "PROJECTION_ACCEPTANCE_NOT_ESTABLISHED" in report["failures"][0][
        "detail"
    ]


@pytest.mark.parametrize(
    ("case_id", "mutation"),
    [
        (
            "N52",
            lambda values: [
                {
                    **value,
                    "message_index": 3
                    if index == 0
                    else value["message_index"],
                }
                for index, value in enumerate(values)
            ],
        ),
        (
            "N52",
            lambda values: [
                {
                    **value,
                    "message_id": "wrong-message"
                    if index == 0
                    else value["message_id"],
                }
                for index, value in enumerate(values)
            ],
        ),
        (
            "N15",
            lambda values: [
                {
                    **value,
                    "exact_count": 1
                    if value["exact_count"] == 2
                    else value["exact_count"],
                }
                for value in values
            ],
        ),
        (
            "N52",
            lambda values: [
                *values,
                {
                    "code": "UNEXPECTED_MUTATION",
                    "message_index": 4,
                    "message_id": "m5",
                    "exact_count": 1,
                },
            ],
        ),
    ],
)
def test_error_origin_and_count_mutations_use_the_real_comparator(
    case_id: str,
    mutation: Callable[[list[dict[str, Any]]], list[dict[str, Any]]],
) -> None:
    def broken_normalizer(
        issues: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        return mutation(normalize_observations(issues))

    report = run_suite(
        CAPNEG_SUITE,
        case_ids={case_id},
        observation_normalizer=broken_normalizer,
    )
    assert report["passed"] is False
    assert [
        (failure["test_id"], failure["case_id"])
        for failure in report["failures"]
    ] == [("RUNNER-EXPECTED-ERRORS-01", case_id)]


def test_fixture_expectations_have_no_production_semantic_import_path() -> None:
    forbidden = {
        "aicp_ref_capneg_v02.profile_composition",
        "aicp_ref_capneg_v02.state_machine",
        "aicp_ref_capneg_v02.session_state_v2",
        "conformance.capneg_v02_runner",
        "aicp_capneg_v02_runner",
        "resolve_fixture_composition",
    }
    for relative in (
        "scripts/generate_capneg_v02_fixtures.py",
        "scripts/capneg_v02_fixture_model.py",
    ):
        source = (ROOT / relative).read_text(encoding="utf-8")
        assert all(name not in source for name in forbidden), relative


def test_reviewed_oracle_is_explicit_complete_and_single_source() -> None:
    oracle = load("fixtures/extensions/capneg_v0_2/oracle_expectations.json")
    expected_ids = {
        *(f"P{index:02d}" for index in range(1, 21)),
        *(f"N{index:02d}" for index in range(1, 105)),
    }
    assert set(oracle["cases"]) == expected_ids
    for expectation in oracle["cases"].values():
        assert set(expectation["expected_final_state"]) == STATE_FIELDS
        for observation in expectation["expected_error_observations"]:
            assert set(observation) == {
                "code",
                "message_index",
                "message_id",
                "exact_count",
            }


def test_missing_and_duplicate_oracle_entries_fail_deterministically(
    tmp_path: Path,
) -> None:
    result = evaluate_case(
        {"id": "missing", "oracle_case_id": "missing", "messages": []},
        oracle_cases={},
    )
    assert result["passed"] is False
    assert result["failures"] == [
        {
            "test_id": "RUNNER-ORACLE-MISSING-01",
            "detail": "oracle entry 'missing' does not resolve",
            "case_id": "missing",
            "message_id": None,
        }
    ]

    duplicate = tmp_path / "duplicate-oracle.json"
    duplicate.write_text(
        '{"cases":{"same":{},"same":{}}}', encoding="utf-8"
    )
    with pytest.raises(ValueError, match="duplicate JSON object key 'same'"):
        _load_without_duplicate_keys(duplicate)

    for catalog_ref in (
        "fixtures/extensions/capneg_v0_2/positive_cases.json",
        "fixtures/extensions/capneg_v0_2/negative_cases.json",
    ):
        for case in load(catalog_ref)["cases"]:
            assert "expected_error_observations" not in case
            assert "expected_final_state" not in case
            assert case["oracle_case_id"] == case["id"]


def test_compact_manifests_reference_messages_and_oracles_once() -> None:
    vectors = load(
        "fixtures/extensions/capneg_v0_2/cross_language_vectors.json"
    )
    assert vectors["composition_oracle_ref"].endswith(
        "composition_oracle.json"
    )
    assert vectors["negotiation_oracle_ref"].endswith(
        "oracle_expectations.json"
    )
    for vector in vectors["negotiation_vectors"]:
        assert set(vector) == {
            "id",
            "source_catalog",
            "case_id",
            "oracle_case_id",
        }
        assert vector["id"] == vector["case_id"] == vector["oracle_case_id"]
    for relative in (
        "fixtures/extensions/object_resync/state_projection_v2/positive_cases.json",
        "fixtures/extensions/object_resync/state_projection_v2/negative_cases.json",
    ):
        for reference in load(relative)["cases"]:
            assert set(reference) == {
                "id",
                "source_catalog",
                "case_id",
                "oracle_case_id",
            }


def test_reviewed_composition_oracle_rejects_a_broken_resolver() -> None:
    oracle = load(
        "fixtures/extensions/capneg_v0_2/composition_oracle.json"
    )["cases"]
    for case_id, case in oracle.items():
        actual = resolve_profile_composition(case["input"], RULES)
        for field, expected in case["expected"].items():
            assert actual[field] == expected, (case_id, field)

    case = oracle["mediated-resumable"]
    broken = resolve_profile_composition(case["input"], RULES)
    broken["required_extensions"] = []
    assert broken["required_extensions"] != case["expected"][
        "required_extensions"
    ]


def test_profile_registry_generator_is_hermetic(tmp_path: Path) -> None:
    for relative in ("registry/aicp_profiles.json", "conformance"):
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
    assert build_registry(root=tmp_path) != actual

    suite_path = tmp_path / actual["profiles"][0]["required_suites"][0]
    suite_path.unlink()
    with pytest.raises(ValueError, match="unresolved suite"):
        build_registry(root=tmp_path)


def test_capneg_fixture_generator_uses_only_the_configured_root(
    tmp_path: Path,
) -> None:
    for relative in (
        "fixtures/keys/TEST_private_keys.json",
        "fixtures/keys/GT_public_keys.json",
        "fixtures/extensions/capneg_v0_2/oracle_expectations.json",
        "fixtures/extensions/capneg_v0_2/composition_oracle.json",
    ):
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, destination)
    try:
        fixture_generator.configure_root(tmp_path)
        baseline = fixture_generator.positive_cases()[0]["messages"]
        composition_path = (
            tmp_path
            / "fixtures/extensions/capneg_v0_2/composition_oracle.json"
        )
        composition_oracle = json.loads(
            composition_path.read_text(encoding="utf-8")
        )
        composition_oracle["cases"]["singleton-base"]["expected"][
            "required_extensions"
        ] = ["EXT-CAPNEG"]
        composition_path.write_text(
            json.dumps(composition_oracle), encoding="utf-8"
        )
        mutated = fixture_generator.positive_cases()[0]["messages"]
        assert baseline != mutated

        (
            tmp_path
            / "fixtures/extensions/capneg_v0_2/oracle_expectations.json"
        ).unlink()
        with pytest.raises(FileNotFoundError):
            fixture_generator.positive_cases()
    finally:
        fixture_generator.configure_root(ROOT)
