from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = ROOT / "conformance" / "evidence"
RUNNER_DIR = ROOT / "conformance" / "runner"
for path in (EVIDENCE_DIR, RUNNER_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from _runner_context import build_validator  # noqa: E402
from target_catalog import (  # noqa: E402
    EXPECTED_MARK,
    REPORT_SCHEMA_PATH,
    TARGET_CATALOG_PATH,
    TARGET_ID,
    TARGET_KEY,
    TARGET_VERSION,
    TARGETS_PATH,
    TCK_RELEASES_PATH,
    canonical_digest,
    expected_input_artifacts,
    expected_suite_records,
    file_digest,
    load_json,
    mandatory_case_ids,
    release_record,
    target_catalog,
    target_record,
    validate_release_registry,
    validate_target_catalog,
    validate_target_registry,
)


ALL_CHECKS = frozenset(
    {
        "target_provenance",
        "case_coverage",
        "determinism",
        "consumer_observations",
        "subject_kind",
    }
)


def _error(code: str, message: str) -> str:
    return f"{code}: {message}"


def _schema_errors(report: dict[str, Any]) -> list[str]:
    schema = load_json(REPORT_SCHEMA_PATH)
    validator = build_validator(schema, REPORT_SCHEMA_PATH)
    if validator is None:
        return [
            _error(
                "EVIDENCE_REPORT_SCHEMA_VALIDATION_UNAVAILABLE",
                "jsonschema is required for strong report evaluation",
            )
        ]
    return [
        _error(
            "EVIDENCE_REPORT_SCHEMA_INVALID",
            (
                "/"
                + "/".join(str(part) for part in issue.path)
                if issue.path
                else "/"
            )
            + f": {issue.message}",
        )
        for issue in sorted(
            validator.iter_errors(report),
            key=lambda item: list(item.path),
        )
    ]


def _case_results_by_id(
    report: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], Counter[str]]:
    results = report.get("case_results")
    if not isinstance(results, list):
        return {}, Counter()
    counts: Counter[str] = Counter()
    by_id: dict[str, dict[str, Any]] = {}
    for item in results:
        if not isinstance(item, dict) or not isinstance(
            item.get("case_id"), str
        ):
            continue
        case_id = str(item["case_id"])
        counts[case_id] += 1
        by_id.setdefault(case_id, item)
    return by_id, counts


def evaluate_report(
    report: dict[str, Any],
    *,
    expected_implementation_id: str | None = None,
    expected_implementation_version: str | None = None,
    disabled_checks: frozenset[str] = frozenset(),
) -> dict[str, Any]:
    unknown_disabled = set(disabled_checks) - ALL_CHECKS
    if unknown_disabled:
        raise ValueError(
            "unknown evaluator checks: " + ", ".join(sorted(unknown_disabled))
        )
    errors = _schema_errors(report)
    if errors:
        return {
            "status": "rejected",
            "errors": sorted(set(errors)),
            "eligible_marks": [],
            "eligible_targets": [],
        }

    catalog = target_catalog()
    release = release_record()
    registry_target = target_record()
    expected_catalog_digest = file_digest(TARGET_CATALOG_PATH)
    expected_registry_digest = file_digest(TARGETS_PATH)
    expected_report_schema_digest = file_digest(REPORT_SCHEMA_PATH)
    expected_tck_registry_digest = file_digest(TCK_RELEASES_PATH)
    expected_suites = expected_suite_records(release)
    expected_inputs = expected_input_artifacts(release)
    mode = report.get("execution_mode")

    for message in [
        *validate_target_registry(),
        *validate_target_catalog(catalog),
        *validate_release_registry(),
    ]:
        errors.append(_error("EVIDENCE_CURRENT_PROVENANCE_INVALID", message))

    if report.get("report_format_version") != "2.0":
        errors.append(_error("EVIDENCE_REPORT_VERSION", "report format must be 2.0"))
    if report.get("report_type") != "aicp.external_evidence":
        errors.append(
            _error(
                "EVIDENCE_REPORT_TYPE",
                "legacy/internal/profile reports cannot substantiate capability evidence",
            )
        )

    target = report.get("target")
    if "target_provenance" not in disabled_checks:
        if not isinstance(target, dict) or target != {
            "kind": "capability",
            "target_id": TARGET_ID,
            "target_version": TARGET_VERSION,
            "target_catalog_digest": expected_catalog_digest,
        }:
            errors.append(
                _error(
                    "EVIDENCE_TARGET_MISMATCH",
                    "report target does not exactly match the registered executable capability",
                )
            )
        if registry_target.get("target_key") != TARGET_KEY:
            errors.append(
                _error(
                    "EVIDENCE_TARGET_UNREGISTERED",
                    "target does not resolve in the current registry",
                )
            )

    tck = report.get("tck_release")
    expected_tck = {
        "release_id": release["release_id"],
        "registry_digest": expected_tck_registry_digest,
        "target_registry_digest": expected_registry_digest,
        "target_catalog_digest": expected_catalog_digest,
        "report_schema_digest": expected_report_schema_digest,
        "runner_bundle_digest": release["runner_bundle"]["digest"],
    }
    if tck != expected_tck:
        errors.append(
            _error(
                "EVIDENCE_TCK_PROVENANCE_MISMATCH",
                "report TCK provenance does not match the registered release and current bytes",
            )
        )
    runner = report.get("runner")
    if runner != {
        "name": "aicp-external-evidence-runner",
        "version": "2.0",
        "source_revision": release["runner_bundle"]["digest"],
    }:
        errors.append(
            _error(
                "EVIDENCE_RUNNER_PROVENANCE_MISMATCH",
                "runner bundle is not registered for the selected evidence TCK",
            )
        )
    if report.get("required_suites") != expected_suites:
        errors.append(
            _error(
                "EVIDENCE_SUITE_PROVENANCE_MISMATCH",
                "required suite set or digest does not exactly match the release",
            )
        )
    if report.get("input_artifacts") != expected_inputs:
        errors.append(
            _error(
                "EVIDENCE_INPUT_PROVENANCE_MISMATCH",
                "required input set or digest does not exactly match the release",
            )
        )

    subject = report.get("execution_subject")
    if not isinstance(subject, dict):
        errors.append(
            _error("EVIDENCE_SUBJECT_INVALID", "execution subject is missing")
        )
        subject_kind = None
    else:
        subject_kind = subject.get("kind")
        if expected_implementation_id is not None and subject.get(
            "implementation_id"
        ) != expected_implementation_id:
            errors.append(
                _error(
                    "EVIDENCE_SUBJECT_MISMATCH",
                    "implementation ID does not match the submission manifest",
                )
            )
        if expected_implementation_version is not None and subject.get(
            "implementation_version"
        ) != expected_implementation_version:
            errors.append(
                _error(
                    "EVIDENCE_SUBJECT_MISMATCH",
                    "implementation version does not match the submission manifest",
                )
            )

    by_id, counts = _case_results_by_id(report)
    expected_ids = Counter(mandatory_case_ids(catalog, str(mode)))
    if "case_coverage" not in disabled_checks and counts != expected_ids:
        errors.append(
            _error(
                "EVIDENCE_CASE_COVERAGE_MISMATCH",
                "mandatory cases are missing, duplicated, or unknown",
            )
        )
    if any(item.get("passed") is not True for item in by_id.values()):
        errors.append(
            _error(
                "EVIDENCE_CASE_FAILED",
                "every observed mandatory case result must pass",
            )
        )

    generated = report.get("generated_artifacts")
    producer = catalog["producer_case"]
    if not isinstance(generated, list) or len(generated) != 1:
        errors.append(
            _error(
                "EVIDENCE_PRODUCER_ARTIFACT_MISSING",
                "exactly one producer artifact is required",
            )
        )
    else:
        artifact = generated[0]
        content = artifact.get("content") if isinstance(artifact, dict) else None
        if (
            not isinstance(artifact, dict)
            or artifact.get("artifact_id") != producer["case_id"]
            or content
            != {
                "projection": producer["expected_projection"],
                "session_state_hash": producer["expected_projection_hash"],
            }
            or artifact.get("content_digest") != canonical_digest(content)
        ):
            errors.append(
                _error(
                    "EVIDENCE_PRODUCER_ARTIFACT_INVALID",
                    "producer content or content digest does not match reviewed expectations",
                )
            )
        if (
            "determinism" not in disabled_checks
            and isinstance(artifact, dict)
            and artifact.get("repeat_content_digest")
            != artifact.get("content_digest")
        ):
            errors.append(
                _error(
                    "EVIDENCE_PRODUCER_NONDETERMINISTIC",
                    "producer repeat digest does not match",
                )
            )

    if "consumer_observations" not in disabled_checks:
        for case in consumer_cases_for_mode(catalog, str(mode)):
            result = by_id.get(str(case["case_id"]))
            observation = (
                result.get("execution_observation")
                if isinstance(result, dict)
                else None
            )
            if not isinstance(observation, dict):
                errors.append(
                    _error(
                        "EVIDENCE_CONSUMER_OBSERVATION_MISSING",
                        f"{case['case_id']} has no structured observation",
                    )
                )
                continue
            error_codes = [
                item.get("code")
                for item in observation.get("errors", [])
                if isinstance(item, dict)
            ]
            actual = {
                "accepted": observation.get("accepted"),
                "error_codes": error_codes,
                "degraded": observation.get("degraded"),
                "degraded_reasons": observation.get("degraded_reasons"),
                "skipped_checks": observation.get("skipped_checks"),
            }
            expected = {
                "accepted": case["accepted"],
                "error_codes": case["expected_error_codes"],
                "degraded": case["expected_degraded"],
                "degraded_reasons": case["expected_degraded_reasons"],
                "skipped_checks": case["expected_skipped_checks"],
            }
            if actual != expected:
                errors.append(
                    _error(
                        "EVIDENCE_CONSUMER_OBSERVATION_MISMATCH",
                        f"{case['case_id']} does not match the reviewed target catalog",
                    )
                )

    if report.get("passed") is not True:
        errors.append(
            _error("EVIDENCE_REPORT_NOT_PASSED", "report must have passed=true")
        )
    if report.get("failures") != []:
        errors.append(
            _error("EVIDENCE_REPORT_FAILURES", "report failures must be empty")
        )
    if report.get("degraded") is not False:
        errors.append(
            _error("EVIDENCE_REPORT_DEGRADED", "degraded evidence is ineligible")
        )
    if report.get("degraded_reasons") != []:
        errors.append(
            _error(
                "EVIDENCE_REPORT_DEGRADED_REASONS",
                "degraded reasons must be empty",
            )
        )
    if report.get("skipped_checks") != []:
        errors.append(
            _error(
                "EVIDENCE_REPORT_SKIPPED_CHECKS",
                "skipped checks make evidence ineligible",
            )
        )

    eligible_subject = subject_kind == "external_implementation"
    if "subject_kind" in disabled_checks:
        eligible_subject = True
    eligible_mode = mode == "full-capability"
    computed_marks = (
        [EXPECTED_MARK]
        if not errors and eligible_subject and eligible_mode
        else []
    )
    if report.get("compatibility_marks") != computed_marks:
        errors.append(
            _error(
                "EVIDENCE_FORGED_OR_MISSING_MARK",
                "raw marks do not equal independently computed eligibility",
            )
        )
        computed_marks = []

    if errors:
        return {
            "status": "rejected",
            "errors": sorted(set(errors)),
            "eligible_marks": [],
            "eligible_targets": [],
        }
    if not eligible_subject or not eligible_mode:
        return {
            "status": "ineligible",
            "errors": [],
            "eligible_marks": [],
            "eligible_targets": [],
        }
    return {
        "status": "eligible",
        "errors": [],
        "eligible_marks": computed_marks,
        "eligible_targets": [
            {
                "kind": "capability",
                "target_id": TARGET_ID,
                "target_version": TARGET_VERSION,
            }
        ],
    }


def consumer_cases_for_mode(
    catalog: dict[str, Any],
    mode: str,
) -> list[dict[str, Any]]:
    cases = list(catalog["consumer_cases"])
    if mode == "smoke":
        return [item for item in cases if item["source_case_id"] == "SP-01"]
    return cases
