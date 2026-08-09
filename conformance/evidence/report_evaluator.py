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
    TARGETS_PATH,
    canonical_target_key,
    expected_input_artifacts,
    expected_suite_records,
    file_digest,
    load_json,
    mandatory_case_ids,
    release_record,
    release_policy,
    release_snapshot_digest,
    release_supersession,
    release_target_entry,
    resolve_target_record,
    target_catalog,
    validate_release_registry,
    validate_target_catalog,
    validate_target_registry,
)
from target_handlers import resolve_handler  # noqa: E402
from producer_suite_semantics import CHECK_IMPLEMENTATIONS  # noqa: E402


ALL_CHECKS = frozenset(
    {
        "target_provenance",
        "case_coverage",
        "determinism",
        "consumer_observations",
        "subject_kind",
        "artifact_multiplicity",
        "EVIDENCE-GENERATED-PAYLOAD-SCHEMA-01",
        *CHECK_IMPLEMENTATIONS,
    }
)


def _error(code: str, message: str) -> str:
    return f"{code}: {message}"


def _schema_errors(
    report: dict[str, Any],
    release: dict[str, Any],
) -> list[str]:
    schema_path = ROOT / str(release["report_schema"]["path"])
    schema = load_json(schema_path)
    validator = build_validator(schema, schema_path)
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
                "/" + "/".join(str(part) for part in issue.path)
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
        if not isinstance(item, dict) or not isinstance(item.get("case_id"), str):
            continue
        case_id = str(item["case_id"])
        counts[case_id] += 1
        by_id.setdefault(case_id, item)
    return by_id, counts


def _rejected(errors: list[str]) -> dict[str, Any]:
    return {
        "status": "rejected",
        "errors": sorted(set(errors)),
        "eligible_marks": [],
        "eligible_targets": [],
    }


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
    tck = report.get("tck_release")
    declared_release_id = (
        tck.get("release_id") if isinstance(tck, dict) else None
    )
    if not isinstance(declared_release_id, str):
        return _rejected(
            [_error("EVIDENCE_TCK_RELEASE_INVALID", "release ID is missing")]
        )
    try:
        selected_release = release_record(declared_release_id)
    except ValueError as exc:
        return _rejected(
            [_error("EVIDENCE_TCK_RELEASE_UNKNOWN", str(exc))]
        )
    errors = _schema_errors(report, selected_release)
    if errors:
        return _rejected(errors)

    target = report.get("target")
    if not isinstance(target, dict):
        return _rejected(
            [_error("EVIDENCE_TARGET_INVALID", "report target is missing")]
        )
    try:
        target_key = canonical_target_key(
            str(target.get("kind")),
            str(target.get("target_id")),
            str(target.get("target_version")),
        )
        registry_target = resolve_target_record(target_key)
    except (KeyError, TypeError, ValueError) as exc:
        return _rejected(
            [
                _error(
                    "EVIDENCE_TARGET_UNREGISTERED",
                    f"target does not resolve exactly in the registry: {exc}",
                )
            ]
        )
    try:
        handler = resolve_handler(registry_target.handler_id)
    except ValueError as exc:
        return _rejected(
            [_error("EVIDENCE_TARGET_HANDLER_UNAVAILABLE", str(exc))]
        )
    catalog = target_catalog(registry_target)

    try:
        selected_target = release_target_entry(selected_release, target_key)
    except ValueError as exc:
        errors.append(
            _error(
                "EVIDENCE_TCK_TARGET_MISMATCH",
                f"declared release does not bind the report target: {exc}",
            )
        )
        selected_target = {}
    try:
        policy = release_policy(declared_release_id)
    except ValueError as exc:
        errors.append(_error("EVIDENCE_TCK_RELEASE_POLICY_MISSING", str(exc)))
        policy = {"strong_eligible": False}
    strong_eligible_release = policy.get("strong_eligible") is True

    for message in [
        *validate_target_registry(),
        *validate_target_catalog(
            catalog,
            record=registry_target,
            handler=handler,
        ),
        *validate_release_registry(),
    ]:
        errors.append(_error("EVIDENCE_CURRENT_PROVENANCE_INVALID", message))

    expected_report_version = (
        "2.1"
        if str(selected_release["report_schema"]["path"]).endswith(
            "v2_1.schema.json"
        )
        else "2.0"
    )
    if report.get("report_format_version") != expected_report_version:
        errors.append(
            _error(
                "EVIDENCE_REPORT_VERSION",
                f"report format must be {expected_report_version}",
            )
        )
    if report.get("report_type") != "aicp.external_evidence":
        errors.append(
            _error(
                "EVIDENCE_REPORT_TYPE",
                "legacy, internal, and profile reports cannot substantiate this target",
            )
        )

    expected_catalog_digest = selected_target.get("target_catalog", {}).get(
        "content_digest"
    )
    if "target_provenance" not in disabled_checks:
        expected_target = {
            **registry_target.identity(),
            "target_catalog_digest": expected_catalog_digest,
        }
        if target != expected_target:
            errors.append(
                _error(
                    "EVIDENCE_TARGET_MISMATCH",
                    "report target does not exactly match the registered target and selected release",
                )
            )

    schema_digest = selected_release["target_registry"].get("schema_digest")
    try:
        registry_digest = release_snapshot_digest(declared_release_id)
    except ValueError as exc:
        supersession = release_supersession(declared_release_id)
        if isinstance(supersession, dict) and isinstance(
            supersession.get("release_registry_digest"), str
        ):
            registry_digest = supersession["release_registry_digest"]
            schema_digest = supersession.get(
                "target_registry_schema_digest", schema_digest
            )
        else:
            errors.append(_error("EVIDENCE_RELEASE_SNAPSHOT_MISSING", str(exc)))
            registry_digest = None
    expected_tck = {
        "release_id": selected_release["release_id"],
        "registry_digest": registry_digest,
        "target_registry_digest": selected_release["target_registry"][
            "content_digest"
        ],
        "target_registry_schema_digest": schema_digest,
        "target_catalog_digest": expected_catalog_digest,
        "report_schema_digest": selected_release["report_schema"][
            "content_digest"
        ],
        "runner_bundle_digest": selected_release["runner_bundle"]["digest"],
    }
    if tck != expected_tck:
        errors.append(
            _error(
                "EVIDENCE_TCK_PROVENANCE_MISMATCH",
                "report provenance does not match the exact declared release",
            )
        )
    runner = report.get("runner")
    if runner != {
        "name": "aicp-external-evidence-runner",
        "version": expected_report_version,
        "source_revision": selected_release["runner_bundle"]["digest"],
    }:
        errors.append(
            _error(
                "EVIDENCE_RUNNER_PROVENANCE_MISMATCH",
                "runner bundle is not registered for the selected release",
            )
        )
    expected_suites = expected_suite_records(selected_release, target_key)
    expected_inputs = expected_input_artifacts(selected_release, target_key)
    if report.get("required_suites") != expected_suites:
        errors.append(
            _error(
                "EVIDENCE_SUITE_PROVENANCE_MISMATCH",
                "required suite set does not match the selected release",
            )
        )
    if report.get("input_artifacts") != expected_inputs:
        errors.append(
            _error(
                "EVIDENCE_INPUT_PROVENANCE_MISMATCH",
                "required input set does not match the selected release",
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
        if (
            expected_implementation_id is not None
            and subject.get("implementation_id") != expected_implementation_id
        ):
            errors.append(
                _error(
                    "EVIDENCE_SUBJECT_MISMATCH",
                    "implementation ID does not match the submission manifest",
                )
            )
        if (
            expected_implementation_version is not None
            and subject.get("implementation_version")
            != expected_implementation_version
        ):
            errors.append(
                _error(
                    "EVIDENCE_SUBJECT_MISMATCH",
                    "implementation version does not match the submission manifest",
                )
            )

    mode = str(report.get("execution_mode"))
    by_id, counts = _case_results_by_id(report)
    release_case_ids = selected_target.get("mandatory_case_ids")
    if mode == "smoke":
        expected_case_ids = mandatory_case_ids(catalog, mode, handler)
    elif isinstance(release_case_ids, list):
        expected_case_ids = [str(item) for item in release_case_ids]
    elif isinstance(selected_target.get("mandatory_producer_ids"), list) and isinstance(
        selected_target.get("mandatory_consumer_ids"), list
    ):
        expected_case_ids = [
            "EVIDENCE-TARGET-CATALOG-01",
            "EVIDENCE-TCK-PROVENANCE-01",
            "EVIDENCE-DESCRIBE-START-01",
            *[
                str(item["case_id"])
                for item in selected_target.get("canonicalization_vectors", [])
                if isinstance(item, dict) and isinstance(item.get("case_id"), str)
            ],
            *[str(item) for item in selected_target["mandatory_producer_ids"]],
            *[str(item) for item in selected_target["mandatory_consumer_ids"]],
            "EVIDENCE-DESCRIBE-STABILITY-01",
            "EVIDENCE-TARGET-SUPPORT-01",
        ]
    else:
        expected_case_ids = mandatory_case_ids(catalog, mode, handler)
    expected_ids = Counter(expected_case_ids)
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

    if strong_eligible_release:
        for code, message in handler.evaluate_report(
            report,
            catalog,
            by_id,
            mode,
            disabled_checks,
        ):
            errors.append(_error(code, message))

    eligible_subject = subject_kind == "external_implementation"
    if "subject_kind" in disabled_checks:
        eligible_subject = True
    eligible_mode = mode == registry_target.execution_mode
    computed_marks = (
        [registry_target.expected_mark]
        if not errors
        and strong_eligible_release
        and eligible_subject
        and eligible_mode
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
        return _rejected(errors)
    if not strong_eligible_release or not eligible_subject or not eligible_mode:
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
        "eligible_targets": [registry_target.identity()],
    }
