from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = ROOT / "conformance" / "evidence"
IUT_DIR = ROOT / "conformance" / "iut"
RUNNER_DIR = ROOT / "conformance" / "runner"
SCRIPTS_DIR = ROOT / "scripts"
INTEROP_TOOLS = ROOT / "interop" / "tools"
for path in (EVIDENCE_DIR, IUT_DIR, RUNNER_DIR, SCRIPTS_DIR, INTEROP_TOOLS):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from adapter_process import (  # noqa: E402
    AdapterProcessError,
    invoke_adapter as invoke_evidence_adapter,
)
from aicp_external_evidence_runner import (  # noqa: E402
    build_execution_plan,
    run_evidence,
)
from aicp_iut_runner import (  # noqa: E402
    IUTProtocolError,
    invoke_adapter as invoke_iut_adapter,
    run_iut,
)
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
from projection_v1_handler import derive_projection  # noqa: E402
from report_evaluator import evaluate_report  # noqa: E402
from target_catalog import (  # noqa: E402
    BUNDLE_MANIFEST_PATH,
    BINDING_TARGET_KEYS,
    EXPECTED_MARK,
    HISTORICAL_RELEASE_RECORD_DIGEST,
    HISTORICAL_TCK_RELEASE_ID,
    PROFILE_TARGET_KEYS,
    TARGET_CATALOG_PATH,
    TARGET_KEY,
    TCK_RELEASE_ID,
    bundle_digest,
    canonical_digest,
    digest_bytes,
    expected_input_artifacts,
    expected_suite_records,
    file_digest,
    load_json,
    load_jsonl,
    release_record,
    release_supersession,
    resolve_target_record,
    runner_bundle_paths,
    target_catalog,
    validate_bundle_manifest,
    validate_release_registry,
    validate_target_catalog,
    validate_target_registry,
)
from target_handlers import resolve_handler  # noqa: E402


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
    targets, catalog, _profile_catalogs, bundle_manifest, releases = (
        GENERATOR.generated_payloads()
    )
    assert json.loads(
        (EVIDENCE_DIR / "targets.json").read_text(encoding="utf-8")
    ) == targets
    assert json.loads(TARGET_CATALOG_PATH.read_text(encoding="utf-8")) == catalog
    assert json.loads(
        BUNDLE_MANIFEST_PATH.read_text(encoding="utf-8")
    ) == bundle_manifest
    assert json.loads(
        (EVIDENCE_DIR / "evidence_tck_releases.json").read_text(
            encoding="utf-8"
        )
    ) == releases
    assert validate_target_registry(targets) == []
    assert validate_target_catalog(
        catalog,
        handler=resolve_handler("projection_v1"),
    ) == []
    assert validate_bundle_manifest(bundle_manifest) == []
    assert validate_release_registry(
        releases,
        bundle_manifest=bundle_manifest,
    ) == []
    assert [item["target_key"] for item in targets["targets"]] == [
        TARGET_KEY,
        *PROFILE_TARGET_KEYS,
        *BINDING_TARGET_KEYS,
    ]
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


def test_producer_requests_are_answer_isolated_and_repeat_is_opaque() -> None:
    record = resolve_target_record(TARGET_KEY)
    handler = resolve_handler(record.handler_id)
    catalog = target_catalog(record)
    requests, _checks = build_execution_plan(
        record,
        catalog,
        handler,
        "full-capability",
    )
    producer_requests = [
        request
        for request in requests
        if request["operation"] == "project_session_state"
    ]
    assert len(producer_requests) == 2
    assert producer_requests[0]["request_id"] != producer_requests[1]["request_id"]
    assert producer_requests[0]["input"] == producer_requests[1]["input"]

    producer = catalog["producer_case"]
    forbidden_values = (
        producer["expected_projection_hash"],
        producer["transcript_fixture"],
        producer["source_case_id"],
        "m2",
        "projection_version",
    )
    reviewed_projection = json.dumps(
        producer["expected_projection"],
        separators=(",", ":"),
        sort_keys=True,
    )
    for request in producer_requests:
        serialized = json.dumps(
            request,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        assert reviewed_projection not in serialized
        assert all(value not in serialized for value in forbidden_values)
        assert "context" not in request["input"]
        assert all(
            message.get("message_type") != "STATE_SYNC_RESPONSE"
            for message in request["input"]["transcript"]
        )


def test_neutral_scenario_derives_exact_reviewed_projection() -> None:
    record = resolve_target_record(TARGET_KEY)
    handler = resolve_handler(record.handler_id)
    catalog = target_catalog(record)
    requests, _checks = build_execution_plan(
        record,
        catalog,
        handler,
        "full-capability",
    )
    producer_input = next(
        request["input"]
        for request in requests
        if request["operation"] == "project_session_state"
    )
    projection, projection_hash = derive_projection(
        producer_input["scenario"],
        producer_input["transcript"],
    )
    assert projection == catalog["producer_case"]["expected_projection"]
    assert projection_hash == catalog["producer_case"][
        "expected_projection_hash"
    ]
    assert set(producer_input["scenario"]).isdisjoint(
        {
            "projection_version",
            "as_of_message_hash",
            "evidence_refs",
            "active_contract_ref",
            "session_state_hash",
        }
    )


def test_producer_catalog_rejects_completed_projection_response() -> None:
    record = resolve_target_record(TARGET_KEY)
    handler = resolve_handler(record.handler_id)
    catalog = target_catalog(record)
    full_transcript = load_jsonl(
        ROOT / catalog["producer_case"]["transcript_fixture"]
    )
    errors = handler.validate_catalog(
        catalog,
        transcript_override=full_transcript,
    )
    assert any("strict projection object" in error for error in errors)


@pytest.mark.parametrize(
    ("target_kind", "target_id", "target_version", "execution_mode"),
    [
        ("capability", "aicp.session_state_projection", "v1", "full-capability"),
        ("product_profile", "AICP-MEDIATED-BLOCKING", "0.1", "full-profile"),
        ("binding", "BIND-HTTP-WS", "0.1", "full-binding"),
    ],
)
def test_registry_schema_accepts_kind_appropriate_versions_and_dispatch_fails_closed(
    target_kind: str,
    target_id: str,
    target_version: str,
    execution_mode: str,
) -> None:
    item = copy.deepcopy(load_json(EVIDENCE_DIR / "targets.json")["targets"][0])
    item.update(
        {
            "target_key": f"{target_id}@{target_version}",
            "target_kind": target_kind,
            "target_id": target_id,
            "target_version": target_version,
            "execution_mode": execution_mode,
            "evidence_claim_type": f"implements_{target_kind.removeprefix('product_')}",
            "handler_id": "projection_v1"
            if target_kind == "capability"
            else f"future_{target_kind}",
        }
    )
    registry = {"registry_version": "1.1", "targets": [item]}
    assert validate_target_registry(
        registry,
        require_repository_references=False,
        enforce_current_scope=False,
    ) == []
    resolved = resolve_target_record(item["target_key"], registry)
    if target_kind == "capability":
        assert resolve_handler(resolved.handler_id).handler_id == "projection_v1"
    else:
        with pytest.raises(
            ValueError,
            match="target registered but handler unavailable",
        ):
            resolve_handler(resolved.handler_id)


def test_invalid_registered_profile_and_binding_references_are_rejected() -> None:
    template = load_json(EVIDENCE_DIR / "targets.json")["targets"][0]
    for kind, target_id, version, mode in (
        ("product_profile", "AICP-NOT-REGISTERED", "0.1", "full-profile"),
        ("binding", "BIND-NOT-REGISTERED", "0.1", "full-binding"),
    ):
        item = copy.deepcopy(template)
        item.update(
            {
                "target_key": f"{target_id}@{version}",
                "target_kind": kind,
                "target_id": target_id,
                "target_version": version,
                "execution_mode": mode,
                "evidence_claim_type": "implements_profile"
                if kind == "product_profile"
                else "implements_binding",
                "handler_id": "future",
            }
        )
        errors = validate_target_registry(
            {"registry_version": "1.1", "targets": [item]},
            enforce_current_scope=False,
        )
        assert any("not registered" in error for error in errors)


def test_unknown_and_projection_v2_targets_fail_closed() -> None:
    for target in ("unknown@v1", "aicp.session_state_projection@v2"):
        with pytest.raises(ValueError, match="unregistered|unimplemented"):
            run_evidence(
                _command("conformance/evidence/reference_adapter.py"),
                target=target,
            )


def test_current_projection_report_is_strict_and_target_oriented(
    external_report: dict,
) -> None:
    schema = load_json(
        EVIDENCE_DIR / "external_evidence_report_v2_2.schema.json"
    )
    from jsonschema import Draft202012Validator

    assert list(Draft202012Validator(schema).iter_errors(external_report)) == []
    assert external_report["report_format_version"] == "2.2"
    assert external_report["generated_artifacts"][0]["artifact_kind"] == "projection"
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


def _as_historical_report(report: dict) -> dict:
    historical = release_record(HISTORICAL_TCK_RELEASE_ID)
    supersession = release_supersession(HISTORICAL_TCK_RELEASE_ID)
    assert supersession is not None
    mutated = copy.deepcopy(report)
    mutated["report_format_version"] = "2.0"
    mutated["runner"]["version"] = "2.0"
    for artifact in mutated["generated_artifacts"]:
        artifact.pop("artifact_kind", None)
    mutated["case_results"] = [
        item
        for item in mutated["case_results"]
        if item["case_id"] != "EVIDENCE-RUNNER-WORKTREE-01"
    ]
    catalog_digest = historical["target"]["target_catalog"]["content_digest"]
    mutated["target"]["target_catalog_digest"] = catalog_digest
    mutated["runner"]["source_revision"] = historical["runner_bundle"]["digest"]
    mutated["tck_release"] = {
        "release_id": HISTORICAL_TCK_RELEASE_ID,
        "registry_digest": supersession["release_registry_digest"],
        "target_registry_digest": historical["target_registry"][
            "content_digest"
        ],
        "target_registry_schema_digest": supersession[
            "target_registry_schema_digest"
        ],
        "target_catalog_digest": catalog_digest,
        "report_schema_digest": historical["report_schema"]["content_digest"],
        "runner_bundle_digest": historical["runner_bundle"]["digest"],
    }
    mutated["required_suites"] = expected_suite_records(historical)
    mutated["input_artifacts"] = expected_input_artifacts(historical)
    mutated["compatibility_marks"] = []
    return mutated


def test_evidence_tck_100_record_is_frozen_and_superseded() -> None:
    historical = release_record(HISTORICAL_TCK_RELEASE_ID)
    assert canonical_digest(historical) == HISTORICAL_RELEASE_RECORD_DIGEST
    supersession = release_supersession(HISTORICAL_TCK_RELEASE_ID)
    assert supersession is not None
    assert supersession["status"] == "superseded-experimental"
    assert supersession["superseded_by"] == TCK_RELEASE_ID
    assert supersession["current_strong_eligibility"] is False


def test_structurally_valid_historical_report_is_currently_ineligible(
    external_report: dict,
) -> None:
    historical = _as_historical_report(external_report)
    schema = load_json(EVIDENCE_DIR / "external_evidence_report_v2.schema.json")
    from jsonschema import Draft202012Validator

    assert list(Draft202012Validator(schema).iter_errors(historical)) == []
    result = _evaluate(historical)
    assert result == {
        "status": "ineligible",
        "errors": [],
        "eligible_marks": [],
        "eligible_targets": [],
    }


def test_target_registry_schema_digest_is_independently_load_bearing(
    external_report: dict,
) -> None:
    report = copy.deepcopy(external_report)
    report["tck_release"]["target_registry_schema_digest"] = (
        "sha256:" + "9" * 64
    )
    result = _evaluate(report)
    assert result["status"] == "rejected"
    assert result["eligible_marks"] == []
    assert any("TCK_PROVENANCE" in error for error in result["errors"])


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


def test_echo_context_adapter_is_rejected() -> None:
    report = run_evidence(
        _command(
            "conformance/evidence/fake_adapters.py",
            "--mode",
            "echo_context",
        ),
        timestamp="2026-07-30T00:00:00Z",
    )
    assert report["passed"] is False
    assert report["compatibility_marks"] == []


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
    for path in paths:
        changed = bundle_digest(
            paths,
            overrides={path: b"mutated load-bearing bytes"},
        )
        assert changed != original, path
    catalog_bytes = TARGET_CATALOG_PATH.read_bytes()
    assert digest_bytes(catalog_bytes + b"\nmutated") != file_digest(
        TARGET_CATALOG_PATH
    )
    fixture = ROOT / target_catalog()["consumer_cases"][0]["fixture"]
    assert digest_bytes(fixture.read_bytes() + b"\nmutated") != file_digest(
        fixture
    )


def test_new_unlisted_runtime_import_fails_bundle_validation() -> None:
    manifest = load_json(BUNDLE_MANIFEST_PATH)
    runner_path = "conformance/evidence/aicp_external_evidence_runner.py"
    mutated = (ROOT / runner_path).read_bytes() + (
        b"\nfrom aicp_ref.session_state import project_session_state\n"
    )
    errors = validate_bundle_manifest(
        manifest,
        overrides={runner_path: mutated},
    )
    assert any("unlisted runtime imports" in error for error in errors)
    assert any("session_state.py" in error for error in errors)


@pytest.mark.parametrize(
    "mode",
    [
        "success",
        "timeout",
        "stdout_overflow",
        "stderr_overflow",
        "malformed_json",
        "missing_response",
        "correlation_mismatch",
        "early_exit",
    ],
)
def test_evidence_process_supervisor_matches_frozen_iut_behavior(
    tmp_path: Path,
    mode: str,
) -> None:
    adapter = tmp_path / "adapter.py"
    adapter.write_text(
        """import json
import sys
import time

mode = sys.argv[1]
requests = [json.loads(line) for line in sys.stdin if line.strip()]
if mode == "timeout":
    time.sleep(2)
elif mode == "stdout_overflow":
    sys.stdout.write("X" * 2048)
elif mode == "stderr_overflow":
    sys.stderr.write("X" * 2048)
elif mode == "malformed_json":
    print("{")
elif mode == "missing_response":
    pass
elif mode == "early_exit":
    raise SystemExit(7)
else:
    for request in requests:
        response = {
            "adapter_protocol_version": "1.1",
            "request_id": request["request_id"],
            "operation": request["operation"],
            "success": True,
            "result": {},
        }
        if mode == "correlation_mismatch":
            response["request_id"] = "wrong"
        print(json.dumps(response, separators=(",", ":")))
""",
        encoding="utf-8",
    )
    requests = [
        {
            "adapter_protocol_version": "1.1",
            "request_id": "parity-1",
            "operation": "describe",
            "input": {},
        }
    ]
    kwargs = {
        "timeout_seconds": 0.15,
        "max_stdout_bytes": 512,
        "max_stderr_bytes": 512,
    }

    def outcome(invoke, error_type):
        try:
            return ("ok", invoke([sys.executable, str(adapter), mode], requests, **kwargs))
        except error_type as exc:
            return ("error", str(exc))

    assert outcome(invoke_evidence_adapter, AdapterProcessError) == outcome(
        invoke_iut_adapter,
        IUTProtocolError,
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
        "CAP-CLAIM-NEG-06",
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
        elif mutation == "historical_release":
            report = _as_historical_report(report)
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


def test_product_profile_iut_v1_bytes_and_eligibility_remain_unchanged() -> None:
    protected = {
        "conformance/iut/iut_report_v1.schema.json": "sha256:728cc512439c162327412570576754d07244da694aceb90e681cb7fa15ba0ee4",
        "conformance/iut/cases.json": "sha256:6b033ce91eee939f637df6efda2ea7c2f011b752b6b09c810d51dbe83bf637fe",
        "conformance/iut/aicp_iut_runner.py": "sha256:bc82d59ffe919098606d9543a823811da43bc1720436fe1197636edc46e9e2fd",
        "conformance/iut/aicp_iut_catalog.py": "sha256:ea4ee227426aa26d342ae1497ccd6917fddf17ffb05da211929daa783d858b87",
        "conformance/iut/_iut_evaluator.py": "sha256:764cfce25e05083a1a94d11d6604475b1e5d71f372825b1d04322b418fad96f3",
        "conformance/iut/adapter_protocol.schema.json": "sha256:6cc75fbed08796385a59a934dd85ffd88f0be308ffd1645c337e5bbb122b0186",
        "conformance/iut/tck_releases.json": "sha256:f89c7dc476041f79558157bb6d0178d7b43158913a2dbe5ee0191d017903a25e",
    }
    assert {
        path: file_digest(ROOT / path) for path in protected
    } == protected
    report = run_iut(
        [
            sys.executable,
            "conformance/iut/fakes/fake_adapter.py",
            "--mode",
            "external_good",
        ],
        "AICP-BASE@0.1",
        mode="full-profile",
    )
    assert report["passed"] is True
    assert report["compatibility_marks"] == ["AICP-Profile-BASE-0.1"]
