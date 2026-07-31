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
    EXPECTATIONS_PATH,
    EXPECTED_MARK,
    REPORT_SCHEMA_PATH,
    TARGET_CATALOG_PATH,
    TARGET_ID,
    TARGET_KEY,
    TARGET_SCHEMA_PATH,
    TARGET_VERSION,
    TARGETS_PATH,
    TCK_RELEASES_PATH,
    TCK_RELEASE_ID,
    bundle_digest,
    digest_bytes,
    file_digest,
    load_json,
    runner_bundle_paths,
    validate_release_registry,
    validate_target_catalog,
    validate_target_registry,
)


SUITE_REF = "conformance/extensions/OR_SESSION_STATE_PROJECTION_V1.json"
VECTOR_REFS = ["conformance/vectors/unicode_codepoint_key_order.json"]
STATIC_INPUTS = [
    "conformance/evidence/projection_v1_expectations.json",
    "schemas/core/aicp-core-message.schema.json",
    "schemas/extensions/ext-object-resync-payloads.schema.json",
    "registry/aicp_profiles.json",
    "registry/extension_ids.json",
]


def render(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def target_registry_payload() -> dict[str, Any]:
    return {
        "registry_version": "1.0",
        "targets": [
            {
                "target_key": TARGET_KEY,
                "target_kind": "capability",
                "target_id": TARGET_ID,
                "target_version": TARGET_VERSION,
                "status": "experimental",
                "target_catalog": (
                    "conformance/evidence/session_state_projection_v1_target.json"
                ),
                "expected_mark": EXPECTED_MARK,
                "required_suites": [SUITE_REF],
                "required_operations": [
                    "describe",
                    "canonicalize_hash",
                    "validate_transcript",
                    "project_session_state",
                ],
                "external_execution_mode": "full-capability",
                "evidence_claim_type": "implements_capability",
            }
        ],
    }


def target_catalog_payload() -> dict[str, Any]:
    suite = load_json(ROOT / SUITE_REF)
    expectations = load_json(EXPECTATIONS_PATH)
    if expectations.get("target_key") != TARGET_KEY:
        raise ValueError("reviewed expectation target key is stale")
    suite_cases = [
        item
        for item in suite.get("transcripts", [])
        if isinstance(item, dict)
    ]
    expected_cases = expectations.get("consumers")
    if not isinstance(expected_cases, dict):
        raise ValueError("reviewed consumer expectations must be an object")
    suite_ids = [str(item["id"]) for item in suite_cases]
    if set(suite_ids) != set(expected_cases):
        raise ValueError("reviewed consumer expectations must exactly cover the suite")

    consumers: list[dict[str, Any]] = []
    fixture_paths: list[str] = []
    for item in suite_cases:
        source_id = str(item["id"])
        fixture = str(item["path"])
        oracle = expected_cases[source_id]
        accepted = item.get("expect_pass", True) is True
        if oracle.get("accepted") is not accepted:
            raise ValueError(f"reviewed acceptance drifts from suite: {source_id}")
        suite_failures = [
            str(failure["test_id"])
            for failure in item.get("expected_failures", [])
            if isinstance(failure, dict)
        ]
        error_codes = [str(code) for code in oracle.get("error_codes", [])]
        if any(code not in error_codes for code in suite_failures):
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
                "expected_error_codes": error_codes,
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
    if producer_suite_case is None or producer_suite_case.get(
        "expect_pass", True
    ) is not True:
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
        {
            "path": relative,
            "content_digest": file_digest(ROOT / relative),
        }
        for relative in required_paths
    ]
    return {
        "catalog_version": "1.0",
        "target_key": TARGET_KEY,
        "target": {
            "kind": "capability",
            "target_id": TARGET_ID,
            "target_version": TARGET_VERSION,
        },
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
            "fixture": producer_fixture,
            "input_digest": file_digest(ROOT / producer_fixture),
            "deterministic_seed": "aicp-evidence-projection-v1-seed-1",
            "expected_projection": producer_oracle["expected_projection"],
            "expected_projection_hash": producer_oracle[
                "expected_projection_hash"
            ],
        },
        "consumer_cases": consumers,
        "required_input_artifacts": required_inputs,
    }


def release_registry_payload(
    targets_rendered: str,
    catalog_rendered: str,
    catalog: dict[str, Any],
) -> dict[str, Any]:
    suite = catalog["owning_suite"]
    bundle_paths = runner_bundle_paths()
    return {
        "registry_version": "1.0",
        "releases": [
            {
                "release_id": TCK_RELEASE_ID,
                "status": "experimental",
                "report_schema": {
                    "path": REPORT_SCHEMA_PATH.relative_to(ROOT).as_posix(),
                    "content_digest": file_digest(REPORT_SCHEMA_PATH),
                },
                "target_registry": {
                    "path": TARGETS_PATH.relative_to(ROOT).as_posix(),
                    "schema_path": TARGET_SCHEMA_PATH.relative_to(
                        ROOT
                    ).as_posix(),
                    "content_digest": digest_bytes(
                        targets_rendered.encode("utf-8")
                    ),
                },
                "runner_bundle": {
                    "paths": bundle_paths,
                    "digest": bundle_digest(bundle_paths),
                },
                "target": {
                    "target_key": TARGET_KEY,
                    "expected_mark": EXPECTED_MARK,
                    "target_catalog": {
                        "path": TARGET_CATALOG_PATH.relative_to(
                            ROOT
                        ).as_posix(),
                        "content_digest": digest_bytes(
                            catalog_rendered.encode("utf-8")
                        ),
                    },
                    "required_suites": [
                        {
                            "path": suite["path"],
                            "suite_id": suite["suite_id"],
                            "suite_version": suite["suite_version"],
                            "suite_digest": suite["suite_digest"],
                        }
                    ],
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
                        catalog["producer_case"]["case_id"]
                    ],
                    "mandatory_consumer_ids": [
                        item["case_id"] for item in catalog["consumer_cases"]
                    ],
                },
            }
        ],
    }


def generated_payloads() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    targets = target_registry_payload()
    catalog = target_catalog_payload()
    targets_rendered = render(targets)
    catalog_rendered = render(catalog)
    releases = release_registry_payload(
        targets_rendered,
        catalog_rendered,
        catalog,
    )
    return targets, catalog, releases


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()

    targets, catalog, releases = generated_payloads()
    paths = (TARGETS_PATH, TARGET_CATALOG_PATH, TCK_RELEASES_PATH)
    rendered = tuple(render(value) for value in (targets, catalog, releases))
    if args.write:
        EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
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
            print("[FAIL] stale evidence framework artifacts: " + ", ".join(stale))
            return 1

    errors = [
        *validate_target_registry(targets),
        *validate_target_catalog(catalog),
    ]
    if args.check:
        errors.extend(validate_release_registry(releases))
    if errors:
        for error in sorted(set(errors)):
            print(f"[FAIL] {error}")
        return 1
    action = "Generated" if args.write else "OK"
    print(
        f"{action}: one external evidence target, 1 producer, "
        f"{len(catalog['consumer_cases'])} consumers, {TCK_RELEASE_ID}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
