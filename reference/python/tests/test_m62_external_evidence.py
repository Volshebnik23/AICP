from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = ROOT / "conformance" / "evidence"
SCRIPTS_DIR = ROOT / "scripts"
INTEROP_TOOLS = ROOT / "interop" / "tools"
for path in (EVIDENCE_DIR, SCRIPTS_DIR, INTEROP_TOOLS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from aicp_external_evidence_runner import run_evidence  # noqa: E402
from fake_adapters import MODES  # noqa: E402
from interop_matrix import build_matrix  # noqa: E402
from interop_submission_validation import (  # noqa: E402
    build_integrity_manifest,
    evaluate_strong_report_evidence,
    load_schema_and_registry,
    manifest_tracked_paths,
    validate_bundle_integrity,
    validate_common_rules,
    validate_schema,
)
from report_evaluator import evaluate_report  # noqa: E402
from target_catalog import (  # noqa: E402
    EXPECTED_MARK,
    TARGET_CATALOG_PATH,
    TARGET_KEY,
    TCK_RELEASE_ID,
    bundle_digest,
    digest_bytes,
    file_digest,
    load_json,
    runner_bundle_paths,
    target_catalog,
    validate_release_registry,
    validate_target_catalog,
    validate_target_registry,
)


GENERATOR_PATH = ROOT / "scripts" / "generate_evidence_framework.py"
SPEC = importlib.util.spec_from_file_location(
    "generate_evidence_framework_test",
    GENERATOR_PATH,
)
assert SPEC is not None and SPEC.loader is not None
GENERATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENERATOR)


def _command(adapter: str, *args: str) -> list[str]:
    return [sys.executable, adapter, *args]


@pytest.fixture(scope="module")
def external_report() -> dict:
    report = run_evidence(
        _command(
            "conformance/evidence/fake_adapters.py",
            "--mode",
            "external_good",
        ),
        timestamp="2026-07-30T00:00:00Z",
    )
    assert report["passed"] is True
    assert report["compatibility_marks"] == [EXPECTED_MARK]
    return report


@pytest.fixture(scope="module")
def reference_report() -> dict:
    report = run_evidence(
        _command("conformance/evidence/reference_adapter.py"),
        timestamp="2026-07-30T00:00:00Z",
    )
    assert report["passed"] is True
    assert report["compatibility_marks"] == []
    return report


def _evaluate(report: dict, **kwargs: object) -> dict:
    return evaluate_report(
        report,
        expected_implementation_id=kwargs.pop(
            "expected_implementation_id",
            "fictional-projection-v1-test-adapter",
        ),
        expected_implementation_version=kwargs.pop(
            "expected_implementation_version",
            "1.0.0-test",
        ),
        **kwargs,
    )


def _manifest(
    *,
    evidence_status: str = "reproducible",
    capability_version: str = "v1",
    report_ref: str = "reports/capability.json",
) -> dict:
    return {
        "submission_id": "fictional-capability-package",
        "implementation_id": "fictional-projection-v1-test-adapter",
        "implementation_version": "1.0.0-test",
        "capability_refs": [
            {
                "capability_id": "aicp.session_state_projection",
                "capability_version": capability_version,
            }
        ],
        "evidence_types": ["capability_report"],
        "evidence_status": evidence_status,
        "report_refs": [report_ref],
        "suite_refs": ["OR-SESSION-STATE-PROJECTION-V1"],
        "claim_type": "implements_capability",
        "claim_scope": "self_attested",
        "generated_at": "2026-07-30T00:00:00Z",
        "disclosures": [
            "Fictional test package; not a real external submission."
        ],
    }


def _write_package(
    root: Path,
    report: dict,
    *,
    manifest: dict | None = None,
) -> Path:
    package = root / "fictional-capability-package"
    reports = package / "reports"
    reports.mkdir(parents=True)
    submission = manifest or _manifest()
    (package / "submission.json").write_text(
        json.dumps(submission, indent=2) + "\n",
        encoding="utf-8",
    )
    (reports / "capability.json").write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
    )
    return package


def test_generated_target_registry_catalog_and_release_are_exact() -> None:
    targets, catalog, releases = GENERATOR.generated_payloads()
    assert json.loads(
        (EVIDENCE_DIR / "targets.json").read_text(encoding="utf-8")
    ) == targets
    assert json.loads(TARGET_CATALOG_PATH.read_text(encoding="utf-8")) == catalog
    assert json.loads(
        (EVIDENCE_DIR / "evidence_tck_releases.json").read_text(
            encoding="utf-8"
        )
    ) == releases
    assert validate_target_registry(targets) == []
    assert validate_target_catalog(catalog) == []
    assert validate_release_registry(releases) == []
    assert [item["target_key"] for item in targets["targets"]] == [TARGET_KEY]
    assert "aicp.session_state_projection@v2" not in json.dumps(targets)


def test_target_catalog_covers_one_producer_and_all_twelve_consumers() -> None:
    catalog = target_catalog()
    suite = load_json(
        ROOT / "conformance/extensions/OR_SESSION_STATE_PROJECTION_V1.json"
    )
    assert catalog["producer_case"]["source_case_id"] == "SP-01"
    assert [item["source_case_id"] for item in catalog["consumer_cases"]] == [
        item["id"] for item in suite["transcripts"]
    ]
    assert len(catalog["consumer_cases"]) == 12
    assert all(
        item["input_digest"] == file_digest(ROOT / item["fixture"])
        for item in catalog["consumer_cases"]
    )


def test_unknown_and_projection_v2_targets_fail_closed() -> None:
    for target in ("unknown@v1", "aicp.session_state_projection@v2"):
        with pytest.raises(ValueError, match="unregistered|unimplemented"):
            run_evidence(
                _command("conformance/evidence/reference_adapter.py"),
                target=target,
            )


def test_report_v2_is_strict_and_target_oriented(
    external_report: dict,
) -> None:
    schema = load_json(
        EVIDENCE_DIR / "external_evidence_report_v2.schema.json"
    )
    from jsonschema import Draft202012Validator

    assert list(Draft202012Validator(schema).iter_errors(external_report)) == []
    assert "profile" not in external_report
    mutated = copy.deepcopy(external_report)
    mutated["raw_badge"] = EXPECTED_MARK
    assert list(Draft202012Validator(schema).iter_errors(mutated))


def test_complete_external_report_is_independently_eligible(
    external_report: dict,
) -> None:
    result = _evaluate(external_report)
    assert result == {
        "status": "eligible",
        "errors": [],
        "eligible_marks": [EXPECTED_MARK],
        "eligible_targets": [
            {
                "kind": "capability",
                "target_id": "aicp.session_state_projection",
                "target_version": "v1",
            }
        ],
    }


def test_reference_and_smoke_reports_never_emit_external_mark(
    reference_report: dict,
) -> None:
    reference_result = evaluate_report(reference_report)
    assert reference_result["status"] == "ineligible"
    assert reference_result["eligible_marks"] == []
    smoke = run_evidence(
        _command(
            "conformance/evidence/fake_adapters.py",
            "--mode",
            "external_good",
        ),
        mode="smoke",
        timestamp="2026-07-30T00:00:00Z",
    )
    assert smoke["passed"] is True
    assert smoke["compatibility_marks"] == []
    assert _evaluate(smoke)["status"] == "ineligible"


@pytest.mark.parametrize("mode", [item for item in MODES if item != "external_good"])
def test_every_negative_fake_adapter_mode_suppresses_mark(mode: str) -> None:
    report = run_evidence(
        _command(
            "conformance/evidence/fake_adapters.py",
            "--mode",
            mode,
        ),
        timestamp="2026-07-30T00:00:00Z",
    )
    assert report["compatibility_marks"] == []
    assert report["passed"] is False
    assert report["failures"]


@pytest.mark.parametrize(
    ("name", "mutate"),
    [
        (
            "forged_mark",
            lambda report: report.update(
                {"compatibility_marks": [EXPECTED_MARK, "forged"]}
            ),
        ),
        (
            "passed_with_failure",
            lambda report: report["failures"].append(
                {"test_id": "FORGED", "message": "hidden failure"}
            ),
        ),
        (
            "missing_case",
            lambda report: report["case_results"].pop(),
        ),
        (
            "duplicate_case",
            lambda report: report["case_results"].append(
                copy.deepcopy(report["case_results"][-1])
            ),
        ),
        (
            "unknown_case",
            lambda report: report["case_results"].append(
                {
                    "case_id": "UNKNOWN",
                    "passed": True,
                    "message": "forged",
                }
            ),
        ),
        (
            "missing_producer",
            lambda report: report.update({"generated_artifacts": []}),
        ),
        (
            "nondeterministic_repeat",
            lambda report: report["generated_artifacts"][0].update(
                {"repeat_content_digest": "sha256:" + "1" * 64}
            ),
        ),
        (
            "wrong_target",
            lambda report: report["target"].update(
                {"target_version": "v2"}
            ),
        ),
        (
            "wrong_suite",
            lambda report: report["required_suites"][0].update(
                {"suite_digest": "sha256:" + "2" * 64}
            ),
        ),
        (
            "wrong_release",
            lambda report: report["tck_release"].update(
                {"release_id": "AICP-EVIDENCE-TCK-0.0.0"}
            ),
        ),
        (
            "wrong_runner",
            lambda report: report["runner"].update(
                {"source_revision": "sha256:" + "3" * 64}
            ),
        ),
        (
            "wrong_input",
            lambda report: report["input_artifacts"][0].update(
                {"content_digest": "sha256:" + "4" * 64}
            ),
        ),
        (
            "degraded",
            lambda report: report.update(
                {
                    "degraded": True,
                    "degraded_reasons": ["forged degradation"],
                    "compatibility_marks": [],
                }
            ),
        ),
        (
            "skipped",
            lambda report: report.update(
                {
                    "skipped_checks": ["MANDATORY"],
                    "compatibility_marks": [],
                }
            ),
        ),
        (
            "wrong_subject",
            lambda report: report["execution_subject"].update(
                {"implementation_id": "other-build"}
            ),
        ),
    ],
)
def test_report_forgery_modes_are_rejected(
    external_report: dict,
    name: str,
    mutate,
) -> None:
    report = copy.deepcopy(external_report)
    mutate(report)
    result = _evaluate(report)
    assert result["status"] == "rejected", name
    assert result["eligible_marks"] == [], name


def test_internal_and_profile_reports_cannot_prove_capability() -> None:
    internal = load_json(ROOT / "conformance/report_ext_object_resync.json")
    result = evaluate_report(internal)
    assert result["status"] == "rejected"
    profile = load_json(
        ROOT
        / "interop/submissions/dryrun-reviewed-base/reports/report_profile_base.json"
    )
    result = evaluate_report(profile)
    assert result["status"] == "rejected"


def test_missing_dependencies_are_truthful_and_suppress_mark() -> None:
    command = _command(
        "conformance/evidence/fake_adapters.py",
        "--mode",
        "external_good",
    )
    for kwargs, expected_check in (
        (
            {"simulate_no_jsonschema": True},
            "EVIDENCE-PRODUCER-SCHEMA-01",
        ),
        (
            {"simulate_no_crypto": True},
            "EVIDENCE-CRYPTO-DEPENDENCY-01",
        ),
    ):
        report = run_evidence(
            command,
            timestamp="2026-07-30T00:00:00Z",
            **kwargs,
        )
        assert report["degraded"] is True
        assert report["degraded_reasons"]
        assert expected_check in report["skipped_checks"]
        assert report["compatibility_marks"] == []


def test_tck_digests_are_load_bearing() -> None:
    paths = runner_bundle_paths()
    original = bundle_digest(paths)
    changed = bundle_digest(
        paths,
        overrides={paths[0]: b"mutated runner bytes"},
    )
    assert changed != original
    catalog_bytes = TARGET_CATALOG_PATH.read_bytes()
    assert digest_bytes(catalog_bytes + b"\nmutated") != file_digest(
        TARGET_CATALOG_PATH
    )
    fixture = ROOT / target_catalog()["consumer_cases"][0]["fixture"]
    assert digest_bytes(fixture.read_bytes() + b"\nmutated") != file_digest(
        fixture
    )


@pytest.mark.parametrize(
    ("check", "mutate"),
    [
        (
            "target_provenance",
            lambda report: report["target"].update(
                {"target_catalog_digest": "sha256:" + "5" * 64}
            ),
        ),
        (
            "case_coverage",
            lambda report: report["case_results"].pop(0),
        ),
        (
            "determinism",
            lambda report: report["generated_artifacts"][0].update(
                {"repeat_content_digest": "sha256:" + "6" * 64}
            ),
        ),
        (
            "consumer_observations",
            lambda report: next(
                item
                for item in report["case_results"]
                if item["case_id"] == "EVIDENCE-CONSUMER-SP-01"
            )["execution_observation"].update({"accepted": False}),
        ),
        (
            "subject_kind",
            lambda report: report["execution_subject"].update(
                {"kind": "reference_corpus"}
            ),
        ),
    ],
)
def test_evaluator_mutation_controls_are_load_bearing(
    external_report: dict,
    check: str,
    mutate,
) -> None:
    report = copy.deepcopy(external_report)
    mutate(report)
    assert _evaluate(report)["status"] == "rejected"
    corrupted = _evaluate(report, disabled_checks=frozenset({check}))
    assert corrupted["status"] == "eligible"
    assert corrupted["eligible_marks"] == [EXPECTED_MARK]


def test_public_capability_claim_and_integrity_binding(
    tmp_path: Path,
    external_report: dict,
) -> None:
    package = _write_package(tmp_path, external_report)
    submission_path = package / "submission.json"
    _, validator, known_profiles = load_schema_and_registry()
    manifest, errors = validate_schema(submission_path, validator)
    assert manifest is not None
    assert errors == []
    assert (
        validate_common_rules(
            submission_path,
            manifest,
            known_profiles,
            require_existing_refs=True,
        )
        == []
    )
    evaluation = evaluate_strong_report_evidence(submission_path, manifest)
    assert evaluation.status == "eligible"
    assert evaluation.eligible_profile_marks == ()
    assert evaluation.eligible_capability_marks == (EXPECTED_MARK,)
    assert evaluation.eligible_targets == (
        (
            "capability",
            "aicp.session_state_projection",
            "v1",
        ),
    )

    integrity = build_integrity_manifest(
        package,
        manifest["submission_id"],
        manifest_tracked_paths(manifest),
        generated_at=manifest["generated_at"],
    )
    (package / "bundle-integrity.json").write_text(
        json.dumps(integrity, indent=2) + "\n",
        encoding="utf-8",
    )
    status, integrity_errors = validate_bundle_integrity(
        package,
        manifest["submission_id"],
    )
    assert status == "valid"
    assert integrity_errors == []


def test_self_attested_wrong_version_and_subject_mismatch_are_rejected(
    tmp_path: Path,
    external_report: dict,
) -> None:
    cases = [
        _manifest(evidence_status="self_attested"),
        _manifest(capability_version="v2"),
    ]
    mismatched = copy.deepcopy(external_report)
    mismatched["execution_subject"]["implementation_version"] = "other"
    for index, manifest in enumerate(cases):
        root = tmp_path / f"case-{index}"
        package = _write_package(root, external_report, manifest=manifest)
        evaluation = evaluate_strong_report_evidence(
            package / "submission.json",
            manifest,
        )
        assert evaluation.status == "rejected"
        assert evaluation.eligible_capability_marks == ()
    package = _write_package(tmp_path / "subject", mismatched)
    evaluation = evaluate_strong_report_evidence(
        package / "submission.json",
        _manifest(),
    )
    assert evaluation.status == "rejected"


def test_reviewed_public_capability_negative_examples_are_enforced(
    tmp_path: Path,
    external_report: dict,
) -> None:
    catalog = load_json(
        ROOT / "fixtures/interop/capability_claims/negative_examples.json"
    )
    assert [item["id"] for item in catalog["cases"]] == [
        "CAP-CLAIM-NEG-01",
        "CAP-CLAIM-NEG-02",
        "CAP-CLAIM-NEG-03",
        "CAP-CLAIM-NEG-04",
        "CAP-CLAIM-NEG-05",
    ]
    _, validator, known_profiles = load_schema_and_registry()
    profile_report = load_json(
        ROOT
        / "interop/submissions/dryrun-reviewed-base/reports/report_profile_base.json"
    )

    for case in catalog["cases"]:
        manifest = _manifest()
        report = copy.deepcopy(external_report)
        mutation = case["mutation"]
        if mutation == "add_profile_fields":
            manifest["profile_ids"] = ["AICP-BASE"]
            manifest["profile_refs"] = [
                {"profile_id": "AICP-BASE", "profile_version": "0.1"}
            ]
        elif mutation == "wrong_capability_version":
            manifest["capability_refs"][0]["capability_version"] = "v2"
        elif mutation == "self_attested":
            manifest["evidence_status"] = "self_attested"
        elif mutation == "profile_report_confusion":
            report = profile_report
        elif mutation == "subject_mismatch":
            report["execution_subject"]["implementation_id"] = "other"
        else:  # pragma: no cover - reviewed catalog is closed by the assertion above
            pytest.fail(f"unknown reviewed mutation: {mutation}")

        package = _write_package(
            tmp_path / case["id"],
            report,
            manifest=manifest,
        )
        submission_path = package / "submission.json"
        _parsed, schema_errors = validate_schema(submission_path, validator)
        common_errors = validate_common_rules(
            submission_path,
            manifest,
            known_profiles,
            require_existing_refs=True,
        )
        evaluation = evaluate_strong_report_evidence(
            submission_path,
            manifest,
        )
        all_errors = [
            *schema_errors,
            *common_errors,
            *evaluation.errors,
        ]
        assert evaluation.status == "rejected"
        assert evaluation.eligible_capability_marks == ()
        assert case["expected_error_fragment"].lower() in " ".join(
            all_errors
        ).lower()


def test_capability_and_profile_evidence_are_not_interchangeable(
    tmp_path: Path,
    external_report: dict,
) -> None:
    profile_report = load_json(
        ROOT
        / "interop/submissions/dryrun-reviewed-base/reports/report_profile_base.json"
    )
    capability_package = _write_package(
        tmp_path / "capability",
        profile_report,
    )
    capability_manifest = _manifest()
    assert (
        evaluate_strong_report_evidence(
            capability_package / "submission.json",
            capability_manifest,
        ).status
        == "rejected"
    )

    profile_manifest = {
        **_manifest(),
        "profile_ids": ["AICP-BASE"],
        "profile_refs": [
            {"profile_id": "AICP-BASE", "profile_version": "0.1"}
        ],
        "evidence_types": ["profile_report"],
        "claim_type": "implements_profile",
    }
    profile_manifest.pop("capability_refs")
    profile_package = _write_package(
        tmp_path / "profile",
        external_report,
        manifest=profile_manifest,
    )
    assert (
        evaluate_strong_report_evidence(
            profile_package / "submission.json",
            profile_manifest,
        ).status
        == "rejected"
    )


def test_matrix_keeps_profile_and_capability_marks_typed(
    tmp_path: Path,
    external_report: dict,
) -> None:
    _write_package(tmp_path, external_report)
    matrix = build_matrix(tmp_path)
    row = matrix["real_submissions"][0]
    assert row["computed_profile_marks"] == []
    assert row["computed_capability_marks"] == [EXPECTED_MARK]
    assert row["computed_marks"] == [EXPECTED_MARK]
    assert row["eligible_targets"] == [
        {
            "kind": "capability",
            "target_id": "aicp.session_state_projection",
            "target_version": "v1",
        }
    ]
