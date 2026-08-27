#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "security_review" / "threat_coverage.json"
SCHEMA_PATH = ROOT / "security_review" / "threat_coverage.schema.json"
REPO_TRUTH_PATH = ROOT / "docs" / "process" / "repo_truth_status.json"

SCOPE_CLASSES = {
    "protocol_observable",
    "mixed",
    "deployment_only",
    "policy_dependent",
    "future_version",
}
STATUSES = {"covered", "deferred", "partial"}
DEFER_CLASSES = {
    "deployment_control",
    "local_policy",
    "non_machine_decidable_without_policy",
    "requires_future_versioned_semantics",
    "independent_external_review",
}


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _safe_path(root: Path, reference: str) -> Path | None:
    raw = reference.split("#", 1)[0]
    if not raw:
        return None
    candidate = (root / raw).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate


def _strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)


def _schema_errors(value: dict[str, Any], root: Path) -> list[str]:
    try:
        from jsonschema import Draft202012Validator
    except Exception:
        return ["jsonschema is required for security coverage validation"]
    schema_path = root / SCHEMA_PATH.relative_to(ROOT)
    if not schema_path.is_file():
        return ["security threat-coverage schema does not exist"]
    validator = Draft202012Validator(_load(schema_path))
    return [
        "schema: " + "/".join(str(part) for part in error.absolute_path) + ": " + error.message
        for error in sorted(validator.iter_errors(value), key=lambda item: list(item.absolute_path))
    ]


def _suite_evidence_errors(
    threat_id: str,
    evidence: dict[str, Any],
    root: Path,
) -> list[str]:
    errors: list[str] = []
    suite_ref = evidence.get("suite")
    suite_path = _safe_path(root, str(suite_ref)) if isinstance(suite_ref, str) else None
    if suite_path is None or not suite_path.is_file():
        return [f"{threat_id}: referenced suite does not exist: {suite_ref}"]
    try:
        suite = _load(suite_path)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"{threat_id}: referenced suite is not valid JSON: {suite_ref}: {exc}"]
    suite_checks = {
        str(item.get("test_id"))
        for item in suite.get("checks", [])
        if isinstance(item, dict) and isinstance(item.get("test_id"), str)
    }
    for check_id in evidence.get("check_ids", []):
        if check_id not in suite_checks:
            errors.append(
                f"{threat_id}: check ID {check_id} does not occur in suite {suite_ref}"
            )
    suite_strings = set(_strings(suite))
    case_entries = [
        item
        for item in suite.get("transcripts", suite.get("cases", []))
        if isinstance(item, dict)
    ]
    case_ids = {str(item.get("id")): item for item in case_entries}
    claimed_case_ids = evidence.get("case_ids", [])
    for case_id in claimed_case_ids:
        if case_id not in case_ids:
            errors.append(f"{threat_id}: case ID {case_id} does not occur in suite {suite_ref}")
    for fixture_ref in evidence.get("fixtures", []):
        fixture_path = _safe_path(root, str(fixture_ref))
        if fixture_path is None or not fixture_path.is_file():
            errors.append(f"{threat_id}: referenced fixture does not exist: {fixture_ref}")
            continue
        if fixture_ref not in suite_strings:
            errors.append(
                f"{threat_id}: fixture {fixture_ref} is not referenced by claimed suite {suite_ref}"
            )
            continue
        if claimed_case_ids and not any(
            fixture_ref in set(_strings(case_ids[case_id]))
            for case_id in claimed_case_ids
            if case_id in case_ids
        ):
            errors.append(
                f"{threat_id}: fixture {fixture_ref} is not referenced by claimed suite cases"
            )
    return errors


def _direct_test_errors(
    threat_id: str,
    evidence: dict[str, Any],
    root: Path,
) -> list[str]:
    test_ref = evidence.get("test_file")
    test_path = _safe_path(root, str(test_ref)) if isinstance(test_ref, str) else None
    if test_path is None or not test_path.is_file():
        return [f"{threat_id}: referenced direct test file does not exist: {test_ref}"]
    text = test_path.read_text(encoding="utf-8")
    return [
        f"{threat_id}: direct test ID {test_id} does not occur in {test_ref}"
        for test_id in evidence.get("test_ids", [])
        if test_id not in text
    ]


def _repository_truth_errors(value: dict[str, Any], root: Path) -> list[str]:
    errors: list[str] = []
    claimed = value.get("repository_truth")
    if not isinstance(claimed, dict):
        return ["repository_truth is missing"]
    status_path = root / REPO_TRUTH_PATH.relative_to(ROOT)
    if not status_path.is_file():
        return ["repo-truth status does not exist"]
    actual = _load(status_path)
    security = actual.get("security_review", {})
    interop = actual.get("interop_evidence", {})
    claimed_external = claimed.get("external_independent_review_completed")
    actual_external = security.get("external_independent_review_completed")
    if claimed_external != actual_external:
        errors.append(
            "external independent review completion claim differs from repo truth"
        )
    claimed_artifacts = claimed.get("external_review_artifacts")
    actual_artifacts = security.get("external_review_artifacts")
    if claimed_artifacts != actual_artifacts:
        errors.append("external review artifact list differs from repo truth")
    if claimed_external is True and not claimed_artifacts:
        errors.append("external review completion requires an actual contracted artifact")
    claimed_relations = claimed.get("pairwise_demonstrated_relations")
    actual_relations = interop.get("pairwise_demonstrated_relations")
    if claimed_relations != actual_relations:
        errors.append(
            "Pairwise demonstrated-relations claim differs from repo truth"
        )
    return errors


def validate_manifest(
    value: dict[str, Any],
    *,
    root: Path = ROOT,
    m67_final: bool = True,
) -> list[str]:
    errors = _schema_errors(value, root)
    threats = value.get("threats")
    if not isinstance(threats, list):
        return sorted(set([*errors, "threats must be a list"]))
    ids = [item.get("threat_id") for item in threats if isinstance(item, dict)]
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    for threat_id in duplicates:
        errors.append(f"duplicate threat ID: {threat_id}")
    for index, threat in enumerate(threats):
        if not isinstance(threat, dict):
            errors.append(f"threat[{index}] must be an object")
            continue
        threat_id = str(threat.get("threat_id", f"threat[{index}]"))
        status = threat.get("status")
        scope = threat.get("scope_class")
        if status not in STATUSES:
            errors.append(f"{threat_id}: unknown status: {status}")
        if scope not in SCOPE_CLASSES:
            errors.append(f"{threat_id}: unknown scope_class: {scope}")
        if m67_final and status == "partial":
            errors.append(f"{threat_id}: partial status is forbidden at M67 completion")
        evidence_items = threat.get("executable_evidence")
        if status == "covered" and not evidence_items:
            errors.append(f"{threat_id}: covered threat requires executable evidence")
        if status == "deferred":
            if threat.get("defer_class") not in DEFER_CLASSES:
                errors.append(f"{threat_id}: deferred threat requires a strict defer_class")
            reason = threat.get("defer_reason")
            if not isinstance(reason, str) or not reason.strip() or reason.strip().lower() == "future work":
                errors.append(f"{threat_id}: deferred threat requires a concrete defer_reason")
        for reference in threat.get("normative_refs", []):
            path = _safe_path(root, str(reference))
            if path is None or not path.is_file():
                errors.append(f"{threat_id}: normative reference does not resolve: {reference}")
        if not isinstance(evidence_items, list):
            continue
        for evidence in evidence_items:
            if not isinstance(evidence, dict):
                errors.append(f"{threat_id}: executable evidence entry must be an object")
                continue
            if evidence.get("kind") == "suite":
                errors.extend(_suite_evidence_errors(threat_id, evidence, root))
            elif evidence.get("kind") in {"direct_test", "freeze_control"}:
                errors.extend(_direct_test_errors(threat_id, evidence, root))
            else:
                errors.append(f"{threat_id}: unknown executable evidence kind")
    errors.extend(_repository_truth_errors(value, root))
    return sorted(set(errors))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--m67-final", action="store_true")
    parser.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args()
    path = args.manifest if args.manifest.is_absolute() else ROOT / args.manifest
    if not path.is_file():
        print(f"[FAIL] security coverage manifest does not exist: {path}")
        return 1
    value = _load(path)
    errors = validate_manifest(value, root=ROOT, m67_final=not args.allow_partial)
    if errors:
        print("[FAIL] security coverage")
        for error in errors:
            print(f" - {error}")
        return 1
    statuses = [item["status"] for item in value["threats"]]
    print(
        "[OK] security threat components: "
        f"{len(statuses)}; covered: {statuses.count('covered')}; "
        f"deferred: {statuses.count('deferred')}; partial: {statuses.count('partial')}; "
        "external independent review completed: "
        f"{str(value['repository_truth']['external_independent_review_completed']).lower()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
