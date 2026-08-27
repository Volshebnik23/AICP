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
        if item["status"] == "covered" and item["executable_evidence"]
    )
    covered["executable_evidence"][0]["check_ids"] = ["FAKE-SECURITY-CHECK-999"]
    assert any("FAKE-SECURITY-CHECK-999" in error for error in _validate(manifest))


def test_existing_but_unreferenced_fixture_cannot_fake_suite_evidence() -> None:
    manifest = _canonical_manifest()
    covered = next(
        item
        for item in manifest["threats"]
        if item["status"] == "covered"
        and any(evidence.get("kind") == "suite" for evidence in item["executable_evidence"])
    )
    evidence = next(item for item in covered["executable_evidence"] if item.get("kind") == "suite")
    evidence["fixtures"] = ["fixtures/extensions/object_resync/OR-03_access_denied.jsonl"]
    assert any("not referenced" in error for error in _validate(manifest))


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
        "conformance/security/SIG_SIGNED_PATHS_0.1.json": {"SP-03": {"CT-SEQUENCE-01"}},
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


def test_signed_truncation_retains_exact_valid_prefix() -> None:
    source = (ROOT / "fixtures/security/signed_paths/SP-01_mediated_blocking_signed.jsonl").read_text(
        encoding="utf-8"
    ).splitlines()
    truncated = (ROOT / "fixtures/security/signed_paths/SP-03_truncated_mediated_flow_expected_fail.jsonl").read_text(
        encoding="utf-8"
    ).splitlines()
    assert truncated == source[: len(truncated)]
    assert len(truncated) == 5


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


def test_product_iut_and_pairwise_release_lines_are_byte_frozen() -> None:
    assert _directory_digest("conformance/iut") == (
        "ae23ec3fa2069ee4535060e382b57250ec079a017e766e46dd70a01a60a6aa10"
    )
    assert _directory_digest("interop/pairwise") == (
        "98601e50e9478adab46260a9af481ad503f27b04dac7368ef4bc003767a0675b"
    )
