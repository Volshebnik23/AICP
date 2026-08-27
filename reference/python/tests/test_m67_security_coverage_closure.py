from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
RUNNER_DIR = ROOT / "conformance" / "runner"
EVIDENCE_DIR = ROOT / "conformance" / "evidence"
for path in (RUNNER_DIR, EVIDENCE_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from aicp_conformance_runner import run_suite  # noqa: E402
import target_catalog as evidence_catalog  # noqa: E402
from profile_transcript_evaluator import evaluate_profile_transcript  # noqa: E402
from report_evaluator import evaluate_report  # noqa: E402


MANIFEST_PATH = ROOT / "security_review" / "threat_coverage.json"
SCHEMA_PATH = ROOT / "security_review" / "threat_coverage.schema.json"
VALIDATOR_PATH = ROOT / "scripts" / "validate_security_coverage.py"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validator_module() -> Any:
    assert VALIDATOR_PATH.is_file(), "M67 security coverage validator is missing"
    spec = importlib.util.spec_from_file_location("validate_security_coverage", VALIDATOR_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _canonical_manifest() -> dict[str, Any]:
    assert MANIFEST_PATH.is_file(), "canonical M67 threat manifest is missing"
    return _load(MANIFEST_PATH)


def _validate(value: dict[str, Any], *, final: bool = True) -> list[str]:
    return _validator_module().validate_manifest(value, root=ROOT, m67_final=final)


def _single_case_raw_failures(
    suite_path: Path, case_id: str, tmp_path: Path
) -> set[str]:
    suite = _load(suite_path)
    case = copy.deepcopy(next(item for item in suite["transcripts"] if item["id"] == case_id))
    case["expect_pass"] = True
    case.pop("expected_failures", None)
    suite["transcripts"] = [case]
    temporary = tmp_path / f"{case_id}-{suite_path.name}"
    temporary.write_text(json.dumps(suite, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = run_suite(temporary)
    return {str(item["test_id"]) for item in report["failures"]}


def _directory_digest(relative: str) -> str:
    digest = hashlib.sha256()
    base = ROOT / relative
    files = (
        item
        for item in base.rglob("*")
        if item.is_file()
        and "__pycache__" not in item.parts
        and item.suffix != ".pyc"
        and not item.name.startswith("report_")
    )
    for path in sorted(files, key=lambda item: item.as_posix()):
        content = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
        digest.update(path.relative_to(ROOT).as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(content)
    return digest.hexdigest()


def test_threat_manifest_schema_and_final_closure_are_valid() -> None:
    assert SCHEMA_PATH.is_file()
    manifest = _canonical_manifest()
    assert not _validate(manifest)
    statuses = [item["status"] for item in manifest["threats"]]
    assert set(statuses) <= {"covered", "deferred"}
    assert "partial" not in statuses
    ids = [item["threat_id"] for item in manifest["threats"]]
    assert len(ids) == len(set(ids))


def test_generated_coverage_map_is_current() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/generate_security_coverage.py", "--check"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        shell=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_nonexistent_check_cannot_fake_coverage() -> None:
    manifest = _canonical_manifest()
    covered = next(
        item
        for item in manifest["threats"]
        if item["status"] == "covered"
        and any(evidence.get("kind") == "suite_case" for evidence in item["executable_evidence"])
    )
    evidence = next(
        item for item in covered["executable_evidence"] if item.get("kind") == "suite_case"
    )
    evidence["expected_failure_ids"] = ["FAKE-SECURITY-CHECK-999"]
    assert any("FAKE-SECURITY-CHECK-999" in error for error in _validate(manifest))


def test_existing_but_unreferenced_fixture_cannot_fake_suite_evidence() -> None:
    manifest = _canonical_manifest()
    covered = next(
        item
        for item in manifest["threats"]
        if item["status"] == "covered"
        and any(evidence.get("kind") == "suite_case" for evidence in item["executable_evidence"])
    )
    evidence = next(
        item for item in covered["executable_evidence"] if item.get("kind") == "suite_case"
    )
    evidence["fixture"] = "fixtures/extensions/object_resync/OR-03_access_denied.jsonl"
    assert any("does not equal claimed fixture" in error for error in _validate(manifest))


def test_validator_real_check_unrelated_case() -> None:
    manifest = _canonical_manifest()
    threat = next(item for item in manifest["threats"] if item["threat_id"] == "SEC-008")
    threat["executable_evidence"] = [
        {
            "kind": "suite_case",
            "suite": "conformance/extensions/AL_ALERTS_0.1.json",
            "case_id": "AL-02",
            "fixture": "fixtures/extensions/alerts/AL-02_unknown_code_expected_fail.jsonl",
            "expectation": "fail",
            "expected_failure_ids": ["AL-ALERT-ACTIONS-01"],
        }
    ]
    assert any("expected failure" in error for error in _validate(manifest))


def test_validator_positive_case_cannot_prove_rejection() -> None:
    manifest = _canonical_manifest()
    threat = next(item for item in manifest["threats"] if item["threat_id"] == "SEC-008")
    threat["executable_evidence"] = [
        {
            "kind": "suite_case",
            "suite": "conformance/extensions/AL_ALERTS_0.1.json",
            "case_id": "AL-01",
            "fixture": "fixtures/extensions/alerts/AL-01_warning_resync_required.jsonl",
            "expectation": "fail",
            "expected_failure_ids": ["AL-ALERT-ACTIONS-01"],
        }
    ]
    assert any("positive" in error for error in _validate(manifest))


def test_validator_extra_check_on_negative() -> None:
    manifest = _canonical_manifest()
    threat = next(item for item in manifest["threats"] if item["threat_id"] == "SEC-008")
    threat["executable_evidence"] = [
        {
            "kind": "suite_case",
            "suite": "conformance/extensions/AL_ALERTS_0.1.json",
            "case_id": "AL-02",
            "fixture": "fixtures/extensions/alerts/AL-02_unknown_code_expected_fail.jsonl",
            "expectation": "fail",
            "expected_failure_ids": ["AL-ALERT-CODES-01", "AL-ALERT-ACTIONS-01"],
        }
    ]
    assert any("expected failure" in error for error in _validate(manifest))


def test_validator_wrong_fixture_for_case() -> None:
    manifest = _canonical_manifest()
    threat = next(item for item in manifest["threats"] if item["threat_id"] == "SEC-008")
    threat["executable_evidence"] = [
        {
            "kind": "suite_case",
            "suite": "conformance/extensions/AL_ALERTS_0.1.json",
            "case_id": "AL-02",
            "fixture": "fixtures/extensions/alerts/AL-01_warning_resync_required.jsonl",
            "expectation": "fail",
            "expected_failure_ids": ["AL-ALERT-CODES-01"],
        }
    ]
    assert any("does not equal claimed fixture" in error for error in _validate(manifest))


def _isolated_direct_test_manifest(
    tmp_path: Path, *, source: str, test_id: str
) -> tuple[Path, dict[str, Any]]:
    root = tmp_path / "coverage-root"
    (root / "security_review").mkdir(parents=True)
    (root / "docs/process").mkdir(parents=True)
    (root / "tests").mkdir(parents=True)
    (root / "security_review/threat_coverage.schema.json").write_text(
        SCHEMA_PATH.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (root / "docs/process/repo_truth_status.json").write_text(
        json.dumps(
            {
                "security_review": {
                    "external_independent_review_completed": False,
                    "external_review_artifacts": [],
                },
                "interop_evidence": {"pairwise_demonstrated_relations": 0},
            }
        ),
        encoding="utf-8",
    )
    (root / "normative.md").write_text("# Normative test boundary\n", encoding="utf-8")
    (root / "tests/test_claim.py").write_text(source, encoding="utf-8")
    manifest = {
        "schema_version": _canonical_manifest()["schema_version"],
        "review_scope": "isolated direct-test validation",
        "generated_map": "security_review/COVERAGE_MAP.md",
        "repository_truth": {
            "external_independent_review_completed": False,
            "external_review_artifacts": [],
            "pairwise_demonstrated_relations": 0,
        },
        "threats": [
            {
                "threat_id": "SEC-999",
                "title": "Isolated validator regression",
                "description": "Proves structural direct-test identity validation.",
                "scope_class": "protocol_observable",
                "status": "covered",
                "normative_refs": ["normative.md"],
                "executable_evidence": [
                    {
                        "kind": "direct_test",
                        "test_file": "tests/test_claim.py",
                        "test_ids": [test_id],
                    }
                ],
                "residual_boundary": "AST identity does not prove arbitrary semantic intent.",
                "remediation_ref": None,
            }
        ],
    }
    return root, manifest


def test_validator_comment_only_test_name(tmp_path: Path) -> None:
    root, manifest = _isolated_direct_test_manifest(
        tmp_path,
        source="# def test_security_claim_is_proven(): pass\n",
        test_id="test_security_claim_is_proven",
    )
    errors = _validator_module().validate_manifest(manifest, root=root, m67_final=True)
    assert any("actual pytest test" in error for error in errors)


def test_validator_string_only_test_name(tmp_path: Path) -> None:
    root, manifest = _isolated_direct_test_manifest(
        tmp_path,
        source='FAKE = "test_security_claim_is_proven"\n',
        test_id="test_security_claim_is_proven",
    )
    errors = _validator_module().validate_manifest(manifest, root=root, m67_final=True)
    assert any("actual pytest test" in error for error in errors)


def test_validator_helper_not_test(tmp_path: Path) -> None:
    root, manifest = _isolated_direct_test_manifest(
        tmp_path,
        source="def helper_security_claim():\n    return True\n",
        test_id="helper_security_claim",
    )
    errors = _validator_module().validate_manifest(manifest, root=root, m67_final=True)
    assert any("actual pytest test" in error for error in errors)


def test_validator_real_pytest_function(tmp_path: Path) -> None:
    root, manifest = _isolated_direct_test_manifest(
        tmp_path,
        source="def test_security_claim_is_proven():\n    assert True\n",
        test_id="test_security_claim_is_proven",
    )
    assert not _validator_module().validate_manifest(manifest, root=root, m67_final=True)


def test_documentation_only_protocol_observable_coverage_is_rejected() -> None:
    manifest = _canonical_manifest()
    covered = next(item for item in manifest["threats"] if item["status"] == "covered")
    covered["scope_class"] = "protocol_observable"
    covered["executable_evidence"] = []
    assert any("executable evidence" in error for error in _validate(manifest))


def test_deferred_without_strict_reason_is_rejected() -> None:
    manifest = _canonical_manifest()
    deferred = next(item for item in manifest["threats"] if item["status"] == "deferred")
    deferred.pop("defer_class", None)
    deferred["defer_reason"] = ""
    errors = _validate(manifest)
    assert any("defer_class" in error for error in errors)
    assert any("defer_reason" in error for error in errors)


def test_partial_is_rejected_at_m67_completion() -> None:
    manifest = _canonical_manifest()
    manifest["threats"][0]["status"] = "partial"
    assert any("partial" in error for error in _validate(manifest, final=True))


def test_false_external_review_and_adoption_claims_are_rejected() -> None:
    manifest = _canonical_manifest()
    manifest["repository_truth"]["external_independent_review_completed"] = True
    manifest["repository_truth"]["pairwise_demonstrated_relations"] = 1
    errors = _validate(manifest)
    assert any("external" in error.lower() for error in errors)
    assert any("Pairwise" in error for error in errors)


def test_new_security_suites_pass_and_negatives_fail_only_for_owning_check(tmp_path: Path) -> None:
    cases = {
        "conformance/extensions/AL_ALERTS_0.1.json": {
            "AL-03": {"AL-ALERT-ACTIONS-01"},
        },
        "conformance/security/SIG_SIGNED_PATHS_0.1.json": {
            "SP-03": {"CT-SEQUENCE-01"},
            "SP-04": {"CT-SIGNATURE-VERIFY-01"},
        },
        "conformance/extensions/CN_CAPNEG_0.1.json": {"CN-13": {"CN-AICP-PROFILE-NEGOTIATION-01"}},
        "conformance/extensions/ENF_ENFORCEMENT_0.1.json": {
            "ENF-03": {"ENF-GATE-01"},
            "ENF-04": {"ENF-GATE-01"},
            "ENF-05": {"ENF-AUTH-01"},
        },
        "conformance/extensions/OR_OBJECT_RESYNC_0.1.json": {"OR-06": {"OR-OBJECT-HASH-01"}},
    }
    for relative, expected in cases.items():
        suite_path = ROOT / relative
        report = run_suite(suite_path)
        assert report["passed"] is True, report["failures"]
        suite_ids = {item["id"] for item in _load(suite_path)["transcripts"]}
        assert set(expected) <= suite_ids
        for case_id, expected_failures in expected.items():
            assert _single_case_raw_failures(suite_path, case_id, tmp_path) == expected_failures


def test_alert_action_fixture_changes_only_the_registered_action_and_hash_chain() -> None:
    source = [
        json.loads(line)
        for line in (ROOT / "fixtures/extensions/alerts/AL-01_warning_resync_required.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    invalid = [
        json.loads(line)
        for line in (
            ROOT / "fixtures/extensions/alerts/AL-03_unknown_recommended_action_expected_fail.jsonl"
        )
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    assert len(source) == len(invalid)
    for source_message, invalid_message in zip(source, invalid, strict=True):
        source_copy = copy.deepcopy(source_message)
        invalid_copy = copy.deepcopy(invalid_message)
        for message in (source_copy, invalid_copy):
            message.pop("message_hash", None)
            message.pop("prev_msg_hash", None)
        if source_copy["message_type"] == "ALERT":
            assert source_copy["payload"]["recommended_actions"] == ["RETRY", "REMEDIATE"]
            assert invalid_copy["payload"]["recommended_actions"] == [
                "RETRY",
                "NOT-REGISTERED",
            ]
            invalid_copy["payload"]["recommended_actions"] = ["RETRY", "REMEDIATE"]
        assert invalid_copy == source_copy


def test_sp04_changes_only_the_alert_signature_bytes() -> None:
    source = [
        json.loads(line)
        for line in (ROOT / "fixtures/security/signed_paths/SP-01_mediated_blocking_signed.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    invalid = [
        json.loads(line)
        for line in (
            ROOT / "fixtures/security/signed_paths/SP-04_invalid_alert_signature_expected_fail.jsonl"
        )
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    assert len(source) == len(invalid)
    changed = []
    for index, (source_message, invalid_message) in enumerate(zip(source, invalid, strict=True)):
        if source_message != invalid_message:
            changed.append(index)
            assert source_message["message_type"] == "ALERT"
            assert invalid_message["message_type"] == "ALERT"
            source_copy = copy.deepcopy(source_message)
            invalid_copy = copy.deepcopy(invalid_message)
            source_signature = source_copy["signatures"][0].pop("sig_b64url")
            invalid_signature = invalid_copy["signatures"][0].pop("sig_b64url")
            assert source_signature != invalid_signature
            assert invalid_signature == "A" * 86
            assert invalid_copy == source_copy
    assert changed == [5]


def test_corrected_threats_use_exact_load_bearing_evidence() -> None:
    threats = {item["threat_id"]: item for item in _canonical_manifest()["threats"]}

    assert threats["SEC-001"]["executable_evidence"] == [
        {
            "kind": "direct_test",
            "test_file": "reference/python/tests/test_tv04_canonicalization_edge_cases.py",
            "test_ids": [
                "test_tv04_to_tv06_canonicalization_vectors",
                "test_supplementary_plane_key_order_vector",
            ],
        }
    ]

    suite_cases = {
        threat_id: {
            (item["suite"], item["case_id"]): tuple(item["expected_failure_ids"])
            for item in threats[threat_id]["executable_evidence"]
            if item["kind"] == "suite_case"
        }
        for threat_id in ("SEC-004", "SEC-005", "SEC-008", "SEC-010")
    }
    assert suite_cases["SEC-004"] == {
        ("conformance/core/CT_CORE_0.2.json", "CT2-NEG-03"): ("CT2-CONTRACT-HASH-01",),
        ("conformance/core/CT_CORE_0.2.json", "CT2-NEG-04"): ("CT2-PROPOSAL-BINDING-01",),
        ("conformance/core/CT_CORE_0.2.json", "CT2-NEG-08"): ("CT2-ACCEPT-BINDING-01",),
        ("conformance/core/CT_CORE_0.2.json", "CT2-NEG-17"): ("CT2-CONTEXT-BINDING-01",),
        ("conformance/core/CT_CORE_0.2.json", "CT2-NEG-20"): ("CT2-ACTIVE-HEAD-01",),
        ("conformance/core/CT_CORE_0.2.json", "CT2-NEG-28"): ("CT2-CONFLICT-BINDING-01",),
    }
    assert suite_cases["SEC-005"] == {
        ("conformance/security/SIG_SIGNED_PATHS_0.1.json", "SP-02"): (
            "CT-SIGNATURE-VERIFY-01",
        ),
        ("conformance/security/AUTH_AUTHENTICATED_MESSAGES_0.1.json", "AB-07"): (
            "CT-SIGNATURE-HASH-01",
            "AUTH-SENDER-SIGNATURE-01",
        ),
        ("conformance/security/AUTH_AUTHENTICATED_MESSAGES_0.1.json", "AB-09"): (
            "AUTH-SENDER-SIGNATURE-01",
        ),
        ("conformance/security/AUTH_AUTHENTICATED_MESSAGES_0.1.json", "AB-10"): (
            "AUTH-KID-01",
            "AUTH-SENDER-SIGNATURE-01",
        ),
        ("conformance/security/AUTH_AUTHENTICATED_MESSAGES_0.1.json", "AB-11"): (
            "AUTH-KEY-RESOLUTION-01",
            "AUTH-SENDER-SIGNATURE-01",
        ),
        ("conformance/security/AUTH_AUTHENTICATED_MESSAGES_0.1.json", "AB-14"): (
            "AUTH-SIGNATURE-VERIFY-01",
        ),
    }
    assert suite_cases["SEC-008"] == {
        ("conformance/extensions/AL_ALERTS_0.1.json", "AL-02"): ("AL-ALERT-CODES-01",),
        ("conformance/extensions/AL_ALERTS_0.1.json", "AL-03"): ("AL-ALERT-ACTIONS-01",),
    }
    assert suite_cases["SEC-010"] == {
        ("conformance/security/SIG_SIGNED_PATHS_0.1.json", "SP-04"): (
            "CT-SIGNATURE-VERIFY-01",
        )
    }

    capneg = threats["SEC-012"]["executable_evidence"]
    assert all(item["kind"] == "direct_test" for item in capneg)
    assert {item["test_file"] for item in capneg} == {
        "reference/python/tests/test_capneg_v02_composition.py",
        "reference/python/tests/test_m61_capneg_correction.py",
        "reference/python/tests/test_m61_direct_reducer_semantics.py",
    }


def test_all_covered_threats_have_only_exact_relational_evidence() -> None:
    covered = [
        item for item in _canonical_manifest()["threats"] if item["status"] == "covered"
    ]
    assert covered
    for threat in covered:
        assert threat["executable_evidence"], threat["threat_id"]
        for evidence in threat["executable_evidence"]:
            assert evidence["kind"] in {"suite_case", "direct_test"}
            assert not ({"check_ids", "fixtures", "case_ids"} & set(evidence))


def test_signed_truncation_retains_exact_valid_prefix() -> None:
    source = (ROOT / "fixtures/security/signed_paths/SP-01_mediated_blocking_signed.jsonl").read_text(
        encoding="utf-8"
    ).splitlines()
    truncated = (ROOT / "fixtures/security/signed_paths/SP-03_truncated_mediated_flow_expected_fail.jsonl").read_text(
        encoding="utf-8"
    ).splitlines()
    assert truncated == source[: len(truncated)]
    assert len(truncated) == 5
    suite = _load(ROOT / "conformance/security/SIG_SIGNED_PATHS_0.1.json")
    case = next(item for item in suite["transcripts"] if item["id"] == "SP-03")
    assert case["expect_pass"] is False
    assert case["expected_failures"] == [{"test_id": "CT-SEQUENCE-01", "min_count": 1}]


def test_object_resync_security_status_mechanisms_are_positive() -> None:
    suite = _load(ROOT / "conformance/extensions/OR_OBJECT_RESYNC_0.1.json")
    positive = {item["id"] for item in suite["transcripts"] if item.get("expect_pass", True)}
    assert {"OR-03", "OR-04", "OR-05"} <= positive


def test_new_ordinary_cases_and_tier1_evidence_consumers_have_exact_parity() -> None:
    expected = {
        "conformance/extensions/CN_CAPNEG_0.1.json": {
            "CN-13": (False, {"CN-AICP-PROFILE-NEGOTIATION-01"}),
        },
        "conformance/extensions/ENF_ENFORCEMENT_0.1.json": {
            "ENF-03": (False, {"ENF-GATE-01"}),
            "ENF-04": (False, {"ENF-GATE-01"}),
            "ENF-05": (False, {"ENF-AUTH-01"}),
        },
        "conformance/extensions/OR_OBJECT_RESYNC_0.1.json": {
            "OR-03": (True, set()),
            "OR-04": (True, set()),
            "OR-05": (True, set()),
            "OR-06": (False, {"OR-OBJECT-HASH-01"}),
        },
    }
    for suite_ref, case_expectations in expected.items():
        suite = _load(ROOT / suite_ref)
        cases = {item["id"]: item for item in suite["transcripts"]}
        for case_id, (accepted, codes) in case_expectations.items():
            messages = [
                json.loads(line)
                for line in (ROOT / cases[case_id]["path"]).read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            result = evaluate_profile_transcript(messages, [suite_ref])
            assert result.accepted is accepted, (case_id, result.errors)
            assert {item["code"] for item in result.errors} == codes

    catalogs = {
        "mediated": _load(EVIDENCE_DIR / "mediated_blocking_target.json"),
        "resumable": _load(EVIDENCE_DIR / "resumable_sessions_target.json"),
        "delegated": _load(EVIDENCE_DIR / "delegated_identity_target.json"),
    }
    ids = {
        name: {item["source_case_id"] for item in catalog["consumer_cases"]}
        for name, catalog in catalogs.items()
    }
    assert {"CN-13", "ENF-03", "ENF-04", "ENF-05"} <= ids["mediated"]
    assert {"OR-03", "OR-04", "OR-05", "OR-06"} <= ids["resumable"]
    assert {"CN-13"} <= ids["delegated"]


def test_public_evidence_schemas_exclude_test_control_secret_fields() -> None:
    schema_paths = (
        "conformance/evidence/external_evidence_report_v2_2.schema.json",
        "conformance/evidence/live_bindings/live_binding_trace_v4.schema.json",
        "conformance/evidence/live_bindings/live_endpoint_descriptor_v2.schema.json",
        "interop/pairwise/pairwise_joint_report_v1_3.schema.json",
        "interop/submissions/submission.schema.json",
    )
    forbidden = {
        "authorization",
        "cookie",
        "set-cookie",
        "proxy-authorization",
        "private_key",
        "private_tls_key",
        "tls_private_key",
        "environment",
        "env",
    }

    def property_names(value: Any) -> set[str]:
        names: set[str] = set()
        if isinstance(value, dict):
            properties = value.get("properties")
            if isinstance(properties, dict):
                names.update(str(name).lower() for name in properties)
            for child in value.values():
                names.update(property_names(child))
        elif isinstance(value, list):
            for child in value:
                names.update(property_names(child))
        return names

    for relative in schema_paths:
        assert not (property_names(_load(ROOT / relative)) & forbidden), relative


def test_evidence_1_10_is_exactly_frozen_and_1_11_is_current() -> None:
    registry = _load(EVIDENCE_DIR / "evidence_tck_releases.json")
    release_1_10 = evidence_catalog.release_record("AICP-EVIDENCE-TCK-1.10.0", registry)
    assert evidence_catalog.canonical_digest(release_1_10) == (
        "sha256:caed5afec58101d1e108f5e64a31f953dca492d8d4a079b173f54591af33eeaf"
    )
    assert evidence_catalog.file_digest(
        EVIDENCE_DIR / "release_registry_snapshots/AICP-EVIDENCE-TCK-1.10.0.json"
    ) == "sha256:7f57814d35cab7d7d50241b41ede7eb182e2b9f890928d04a6c872bb19f743dc"
    assert evidence_catalog.file_digest(EVIDENCE_DIR / "evidence_runner_bundle_v1_10.json") == (
        "sha256:c61e9f4a1e384bcd435765d1457223b2cae1035c62686fedaa7101681d19919b"
    )
    assert release_1_10["runner_bundle"]["digest"] == (
        "sha256:77498e0b1801a2fdc94ebc7947fe3f9df5395332ef272f49ce7cecb6050ceed0"
    )
    policy_1_10 = evidence_catalog.release_policy("AICP-EVIDENCE-TCK-1.10.0", registry)
    assert policy_1_10["lifecycle"] == "historical"
    assert policy_1_10["strong_eligible"] is True
    release_1_11 = evidence_catalog.release_record("AICP-EVIDENCE-TCK-1.11.0", registry)
    assert len(release_1_11["targets"]) == 6
    assert evidence_catalog.release_policy("AICP-EVIDENCE-TCK-1.11.0", registry)["lifecycle"] == "current"


def test_exact_pre_m67_evidence_1_10_profile_reports_remain_eligible() -> None:
    vector_dir = EVIDENCE_DIR / "historical_vectors/AICP-EVIDENCE-TCK-1.10.0"
    manifest = _load(vector_dir / "manifest.json")
    assert manifest["classification"] == "historical-regression-vector"
    assert manifest["source_commit"] == "f3a7ea279575da9ea675997850b33483548c013b"
    assert manifest["adoption_status"].startswith("test-vector-only")

    expected = {
        "mediated-blocking.json": (
            "8d83ea15e8787170f6181e2e5ff3a1e242bd70ae6c52ceb28ee8bd7f942a0c46",
            "AICP-Profile-MEDIATED-BLOCKING-0.1",
        ),
        "resumable-sessions.json": (
            "ffa81932f8330c47b9fe78d54ae2708457678c4a58db6f0f30f8998ea9295980",
            "AICP-Profile-RESUMABLE-SESSIONS-0.1",
        ),
    }
    assert {item["path"] for item in manifest["reports"]} == set(expected)
    for filename, (digest, mark) in expected.items():
        report_path = vector_dir / filename
        assert hashlib.sha256(report_path.read_bytes()).hexdigest() == digest
        report = _load(report_path)
        assert report["tck_release"]["release_id"] == "AICP-EVIDENCE-TCK-1.10.0"
        verdict = evaluate_report(report)
        assert verdict == {
            "status": "eligible",
            "errors": [],
            "eligible_marks": [mark],
            "eligible_targets": [
                {
                    key: report["target"][key]
                    for key in ("kind", "target_id", "target_version")
                }
            ],
        }


def test_evidence_1_11_release_runtime_and_target_bytes_are_frozen() -> None:
    registry = _load(EVIDENCE_DIR / "evidence_tck_releases.json")
    release = evidence_catalog.release_record("AICP-EVIDENCE-TCK-1.11.0", registry)
    assert evidence_catalog.canonical_digest(release) == (
        "sha256:a746f4b1029b500d42e441d266959d7c1146b2e7ddf8738cf849c843595b2cb3"
    )
    assert evidence_catalog.file_digest(
        EVIDENCE_DIR / "release_registry_snapshots/AICP-EVIDENCE-TCK-1.11.0.json"
    ) == "sha256:50f1a62998dd7d110d72462b4cb72fd2a64a3c5bbad07fffe37e0cbe161b799b"
    assert evidence_catalog.file_digest(EVIDENCE_DIR / "evidence_runner_bundle_v1_11.json") == (
        "sha256:7620f68e010550ca5332fa15b59e9ed4f6336b3749cd73ef121989a2d854a9ec"
    )
    assert release["runner_bundle"]["digest"] == (
        "sha256:121f1332f6b31f0d288bf0ca648729e2cf2bd7bdb641478626293995a09e5c5e"
    )
    assert release["report_schema"]["content_digest"] == (
        "sha256:5a2a5ce0c3b12a2c5f7224508bffc47635e20b85526ac8148721b9fe78df6e28"
    )
    assert evidence_catalog.file_digest(ROOT / release["report_schema"]["path"]) == (
        "sha256:5a2a5ce0c3b12a2c5f7224508bffc47635e20b85526ac8148721b9fe78df6e28"
    )
    target_digests = {
        item["target_key"]: item["target_catalog"]["content_digest"]
        for item in release["targets"]
    }
    assert target_digests == {
        "aicp.session_state_projection@v1": "sha256:b1674c1d1a6f211e115d9c0f6a2e43eaf03e3b7e3c6130682342ff31c451ab20",
        "AICP-MEDIATED-BLOCKING@0.1": "sha256:31210e907d0f9b251222cc45491ab9d44cc8ab7c2794c86b083a86f600507b1b",
        "AICP-RESUMABLE-SESSIONS@0.1": "sha256:7636a26a52461f8ae964bdbb876279df4327815d5dbf5084bced682b8deb40f1",
        "AICP-DELEGATED-IDENTITY@0.1": "sha256:f145db6817e3395c1d4f8eacfc75751c441f9e8a14660020e9da03315b6c1d6a",
        "BIND-HTTP@0.1": "sha256:00d440218fb22148ba277b3ebc67beff610cb0dec7bd927409dcd03b0e9cdba3",
        "BIND-MCP@0.1": "sha256:1fa9fd9b3c30758e9561f771c30aba5be608ac2bfe07629fd36297430b67d651",
    }
    profile_targets = [
        item for item in release["targets"] if item["handler_id"] == "product_profile_v01"
    ]
    assert sum(len(item["mandatory_producer_ids"]) for item in profile_targets) == 32
    assert sum(len(item["mandatory_consumer_ids"]) for item in profile_targets) == 82
    required_suites = {
        suite["path"] for item in release["targets"] for suite in item["required_suites"]
    }
    assert "conformance/extensions/AL_ALERTS_0.1.json" not in required_suites
    assert "conformance/security/SIG_SIGNED_PATHS_0.1.json" not in required_suites


def test_product_iut_and_pairwise_release_lines_are_byte_frozen() -> None:
    assert _directory_digest("conformance/iut") == (
        "ae23ec3fa2069ee4535060e382b57250ec079a017e766e46dd70a01a60a6aa10"
    )
    assert _directory_digest("interop/pairwise") == (
        "98601e50e9478adab46260a9af481ad503f27b04dac7368ef4bc003767a0675b"
    )


def test_pairwise_validation_uses_immutable_release_local_authorities() -> None:
    for command in (
        [sys.executable, "scripts/validate_pairwise_targets.py"],
        [sys.executable, "scripts/generate_pairwise_tck.py", "--check"],
    ):
        result = subprocess.run(
            command,
            cwd=ROOT,
            text=True,
            capture_output=True,
            shell=False,
        )
        assert result.returncode == 0, result.stdout + result.stderr
