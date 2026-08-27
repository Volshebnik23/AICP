#!/usr/bin/env python3
"""Execute Pairwise 1.3 side/Core checks from the shared immutable 1.1 authority."""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
AUTHORITY_ROOT = HERE / "release_artifacts" / "AICP-PAIRWISE-TCK-1.1.0" / "authority_root"
for path in (
    AUTHORITY_ROOT / "conformance" / "runner",
    AUTHORITY_ROOT / "conformance" / "evidence",
    AUTHORITY_ROOT / "reference" / "python",
    AUTHORITY_ROOT / "interop" / "pairwise",
):
    sys.path.insert(0, str(path))

from _runner_context import build_validator  # noqa: E402
from _runner_provenance import canonical_content_digest  # noqa: E402
from aicp_ref.hashing import message_hash_from_body, object_hash  # noqa: E402
from aicp_ref.jcs import canonicalize_json  # noqa: E402
from live_bindings.live_binding_handler import LiveBindingV01Handler  # noqa: E402
from pairwise_core_validator_v1_1 import validate_core_v01_transcript  # noqa: E402


def _load(relative: str) -> Any:
    return json.loads((AUTHORITY_ROOT / relative).read_text(encoding="utf-8"))


def _schema_errors(report: dict[str, Any], path_ref: str) -> list[str]:
    path = AUTHORITY_ROOT / path_ref
    validator = build_validator(_load(path_ref), path)
    if validator is None:
        return ["release-frozen jsonschema authority is unavailable"]
    return [
        ("/" + "/".join(str(part) for part in issue.path) if issue.path else "/")
        + f": {issue.message}"
        for issue in sorted(validator.iter_errors(report), key=lambda item: list(item.path))
    ]


def _case_map(report: dict[str, Any]) -> tuple[dict[str, dict[str, Any]], Counter[str]]:
    counts: Counter[str] = Counter()
    by_id: dict[str, dict[str, Any]] = {}
    for item in report.get("case_results", []) if isinstance(report.get("case_results"), list) else []:
        if isinstance(item, dict) and isinstance(item.get("case_id"), str):
            counts[item["case_id"]] += 1
            by_id.setdefault(item["case_id"], item)
    return by_id, counts


def _common_errors(
    report: dict[str, Any],
    expected: dict[str, Any],
    identity: dict[str, Any],
) -> tuple[list[str], dict[str, dict[str, Any]]]:
    errors = _schema_errors(report, str(expected["report_schema_path"]))
    subject = report.get("execution_subject")
    if not isinstance(subject, dict) or subject != identity:
        errors.append("execution subject differs from the exact joint participant")
    for field in (
        "report_format_version",
        "report_type",
        "execution_mode",
        "runner",
        "tck_release",
        "required_suites",
        "input_artifacts",
        "compatibility_marks",
    ):
        if report.get(field) != expected.get(field):
            errors.append(f"{field} differs from the exact frozen side authority")
    for field, clean_value in (
        ("passed", True),
        ("failures", []),
        ("degraded", False),
        ("degraded_reasons", []),
        ("skipped_checks", []),
    ):
        if report.get(field) != clean_value:
            errors.append(f"{field} is not clean")
    by_id, counts = _case_map(report)
    if counts != Counter(expected["case_ids"]):
        errors.append("mandatory case coverage differs from the exact frozen release")
    if any(item.get("passed") is not True for item in by_id.values()):
        errors.append("one or more mandatory side-evidence cases did not pass")
    artifacts = report.get("generated_artifacts")
    artifact_counts = Counter(
        item.get("artifact_id") for item in artifacts if isinstance(item, dict)
    ) if isinstance(artifacts, list) else Counter()
    if artifact_counts != Counter(expected["generated_artifact_ids"]):
        errors.append("generated artifact coverage differs from the exact frozen release")
    for artifact in artifacts if isinstance(artifacts, list) else []:
        if not isinstance(artifact, dict):
            errors.append("generated artifact must be an object")
            continue
        if artifact.get("content_digest") != canonical_content_digest(artifact.get("content")):
            errors.append(f"generated artifact digest mismatch for {artifact.get('artifact_id')}")
        if artifact.get("repeat_content_digest") != artifact.get("content_digest"):
            errors.append(f"generated artifact determinism mismatch for {artifact.get('artifact_id')}")
    return errors, by_id


def evaluate_side_report(
    report: dict[str, Any],
    *,
    kind: str,
    identity: dict[str, Any],
) -> list[str]:
    authorities = _load("pairwise_side_authorities.json")
    expected = authorities[kind]
    errors, by_id = _common_errors(report, expected, identity)
    if kind == "profile":
        if report.get("suite") != expected["suite"] or report.get("profile") != expected["profile"]:
            errors.append("Base profile/suite provenance differs from the exact IUT authority")
        expected_observations = expected["consumer_observations"]
        for case_id, observation in expected_observations.items():
            if by_id.get(case_id, {}).get("execution_observation") != observation:
                errors.append(f"consumer observation differs for {case_id}")
    elif kind == "binding":
        if report.get("target") != expected["target"]:
            errors.append("MCP target provenance differs from the exact Evidence authority")
        catalog = _load(str(expected["target_catalog_path"]))
        handler_errors = LiveBindingV01Handler().evaluate_report(
            report,
            catalog,
            by_id,
            "full-binding",
            frozenset(),
        )
        errors.extend(f"{code}: {message}" for code, message in handler_errors)
    else:
        errors.append(f"unknown side authority kind {kind!r}")
    return sorted(set(errors))


def dispatch(request: dict[str, Any]) -> dict[str, Any]:
    operation = request.get("operation")
    if operation == "side":
        return {
            "errors": evaluate_side_report(
                request["report"],
                kind=str(request["kind"]),
                identity=request["identity"],
            )
        }
    if operation == "core":
        return {
            "errors": validate_core_v01_transcript(
                request["messages"],
                authority_root=AUTHORITY_ROOT,
            )
        }
    if operation == "hash":
        value = request["value"]
        object_type = str(request["object_type"])
        return {
            "canonical_json": canonicalize_json(value),
            "object_hash": object_hash(object_type, value),
            "message_hash": message_hash_from_body(value) if object_type == "message" else None,
        }
    raise ValueError(f"unsupported authority operation: {operation!r}")


def main() -> int:
    try:
        request = json.loads(sys.stdin.read())
        response = {"ok": True, "result": dispatch(request)}
    except Exception as exc:
        response = {"ok": False, "error": str(exc)}
    sys.stdout.write(json.dumps(response, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    return 0 if response["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
