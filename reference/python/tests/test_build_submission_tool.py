from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
TOOL = ROOT / "interop/tools/build_submission.py"
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

from interop_submission_validation import (
    INTEGRITY_FILENAME,
    compute_file_digest,
    load_integrity_schema_validator,
    load_schema_and_registry,
    validate_bundle_integrity,
    validate_common_rules,
    validate_schema,
)


def _write_json(path: Path, obj: dict[str, object]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj), encoding="utf-8")
    return path


def _run_tool(*args: str) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(TOOL), *args]
    return subprocess.run(cmd, check=False, text=True, capture_output=True, cwd=ROOT)


def _validate_package(package_dir: Path) -> tuple[list[str], str]:
    submission_path = package_dir / "submission.json"
    _, validator, known_profiles = load_schema_and_registry()
    _, integrity_validator = load_integrity_schema_validator()
    manifest, errors = validate_schema(submission_path, validator)
    if manifest is None:
        return errors, "invalid"
    errors.extend(validate_common_rules(submission_path, manifest, known_profiles, require_existing_refs=True))
    integrity_status, integrity_errors = validate_bundle_integrity(
        package_dir,
        manifest["submission_id"],
        integrity_validator=integrity_validator,
    )
    errors.extend(integrity_errors)
    return errors, integrity_status


def test_build_submission_tool_single_impl_package_with_integrity(tmp_path: Path) -> None:
    report_one = _write_json(
        tmp_path / "inputs" / "report_profile_base.json",
        {"profile_id": "AICP-BASE", "passed": True, "compatibility_marks": ["AICP-Profile-BASE-0.1"]},
    )
    report_two = _write_json(
        tmp_path / "inputs" / "report_core.json",
        {"suite_id": "CT_CORE_0.1", "passed": True, "compatibility_marks": ["AICP-Core-0.1"]},
    )
    out_root = tmp_path / "submissions"

    result = _run_tool(
        "--out-root",
        str(out_root),
        "--submission-id",
        "fictional-single-impl",
        "--implementation-id",
        "fictional-impl-a",
        "--implementation-version",
        "1.2.3",
        "--profile-id",
        "AICP-BASE",
        "--claim-type",
        "implements_profile",
        "--claim-scope",
        "self_attested",
        "--evidence-status",
        "reproducible",
        "--report-path",
        str(report_one),
        "--report-path",
        str(report_two),
        "--suite-ref",
        "PF_AICP_BASE_0.1",
        "--suite-ref",
        "CT_CORE_0.1",
        "--disclosure",
        "Fictional example package generated in a local test; not a market-facing claim.",
        "--note",
        "Single-implementation packaging example.",
        "--with-integrity",
        "--validate",
    )

    assert result.returncode == 0, result.stderr
    package_dir = out_root / "fictional-single-impl"
    manifest = json.loads((package_dir / "submission.json").read_text(encoding="utf-8"))
    integrity_manifest = json.loads((package_dir / INTEGRITY_FILENAME).read_text(encoding="utf-8"))

    assert manifest["implementation_id"] == "fictional-impl-a"
    assert manifest["evidence_status"] == "reproducible"
    assert manifest["evidence_types"] == ["profile_report", "conformance_report"]
    assert manifest["report_refs"] == ["reports/report_profile_base.json", "reports/report_core.json"]
    assert (package_dir / "reports" / "report_profile_base.json").exists()
    assert (package_dir / "reports" / "report_core.json").exists()
    assert integrity_manifest["submission_id"] == manifest["submission_id"]
    assert integrity_manifest["digest_alg"] == "sha256"
    tracked = {entry["path"]: entry["digest"] for entry in integrity_manifest["files"]}
    assert tracked == {
        "submission.json": compute_file_digest(package_dir / "submission.json"),
        "reports/report_profile_base.json": compute_file_digest(package_dir / "reports" / "report_profile_base.json"),
        "reports/report_core.json": compute_file_digest(package_dir / "reports" / "report_core.json"),
    }
    errors, integrity_status = _validate_package(package_dir)
    assert errors == []
    assert integrity_status == "valid"


def test_build_submission_tool_requires_peer_for_pairwise(tmp_path: Path) -> None:
    report_one = _write_json(
        tmp_path / "inputs" / "report_a.json",
        {"profile_id": "AICP-MEDIATED-BLOCKING", "passed": True},
    )
    report_two = _write_json(
        tmp_path / "inputs" / "report_b.json",
        {"profile_id": "AICP-MEDIATED-BLOCKING", "passed": True},
    )

    result = _run_tool(
        "--out-root",
        str(tmp_path / "submissions"),
        "--submission-id",
        "fictional-pairwise",
        "--implementation-id",
        "fictional-impl-a",
        "--implementation-version",
        "1.0.0",
        "--profile-id",
        "AICP-MEDIATED-BLOCKING",
        "--claim-type",
        "pairwise_interop",
        "--claim-scope",
        "pairwise",
        "--evidence-status",
        "pairwise",
        "--report-path",
        str(report_one),
        "--report-path",
        str(report_two),
        "--suite-ref",
        "PF_AICP_MEDIATED_BLOCKING_0.1",
        "--disclosure",
        "Fictional local test package; not a real interop claim.",
    )

    assert result.returncode == 1
    assert "--peer-implementation-id is required" in result.stdout


def test_build_submission_tool_pairwise_package_with_integrity_validates(tmp_path: Path) -> None:
    report_one = _write_json(
        tmp_path / "inputs" / "pair_a.json",
        {"profile_id": "AICP-MEDIATED-BLOCKING", "passed": True, "compatibility_marks": ["AICP-Profile-MEDIATED-BLOCKING-0.1"]},
    )
    report_two = _write_json(
        tmp_path / "inputs" / "pair_b.json",
        {"profile_id": "AICP-MEDIATED-BLOCKING", "passed": True, "compatibility_marks": ["AICP-Profile-MEDIATED-BLOCKING-0.1"]},
    )
    out_root = tmp_path / "submissions"

    result = _run_tool(
        "--out-root",
        str(out_root),
        "--submission-id",
        "fictional-pairwise",
        "--implementation-id",
        "fictional-impl-a",
        "--peer-implementation-id",
        "fictional-impl-b",
        "--implementation-version",
        "2.0.0",
        "--profile-id",
        "AICP-MEDIATED-BLOCKING",
        "--claim-type",
        "pairwise_interop",
        "--claim-scope",
        "pairwise",
        "--evidence-status",
        "pairwise",
        "--report-path",
        str(report_one),
        "--report-path",
        str(report_two),
        "--suite-ref",
        "PF_AICP_MEDIATED_BLOCKING_0.1",
        "--suite-ref",
        "ENF_ENFORCEMENT_0.1",
        "--disclosure",
        "Fictional local test package; not a market-facing claim.",
        "--with-integrity",
        "--validate",
    )

    assert result.returncode == 0, result.stderr
    package_dir = out_root / "fictional-pairwise"
    manifest = json.loads((package_dir / "submission.json").read_text(encoding="utf-8"))

    assert manifest["peer_implementation_id"] == "fictional-impl-b"
    assert manifest["claim_type"] == "pairwise_interop"
    assert manifest["evidence_status"] == "pairwise"
    assert manifest["report_refs"] == ["reports/pair_a.json", "reports/pair_b.json"]
    assert manifest["evidence_types"] == ["profile_report"]
    errors, integrity_status = _validate_package(package_dir)
    assert errors == []
    assert integrity_status == "valid"


def test_validate_bundle_integrity_detects_tampering(tmp_path: Path) -> None:
    report_one = _write_json(
        tmp_path / "inputs" / "report_profile_base.json",
        {"profile_id": "AICP-BASE", "passed": True, "compatibility_marks": ["AICP-Profile-BASE-0.1"]},
    )
    report_two = _write_json(
        tmp_path / "inputs" / "report_core.json",
        {"suite_id": "CT_CORE_0.1", "passed": True, "compatibility_marks": ["AICP-Core-0.1"]},
    )
    out_root = tmp_path / "submissions"

    result = _run_tool(
        "--out-root",
        str(out_root),
        "--submission-id",
        "fictional-single-impl",
        "--implementation-id",
        "fictional-impl-a",
        "--implementation-version",
        "1.2.3",
        "--profile-id",
        "AICP-BASE",
        "--claim-type",
        "implements_profile",
        "--claim-scope",
        "self_attested",
        "--evidence-status",
        "reproducible",
        "--report-path",
        str(report_one),
        "--report-path",
        str(report_two),
        "--suite-ref",
        "PF_AICP_BASE_0.1",
        "--suite-ref",
        "CT_CORE_0.1",
        "--disclosure",
        "Fictional example package generated in a local test; not a market-facing claim.",
        "--with-integrity",
        "--validate",
    )
    assert result.returncode == 0, result.stderr

    package_dir = out_root / "fictional-single-impl"
    tampered_report = package_dir / "reports" / "report_core.json"
    tampered_report.write_text(
        json.dumps({"suite_id": "CT_CORE_0.1", "passed": False, "compatibility_marks": ["AICP-Core-0.1"]}),
        encoding="utf-8",
    )

    errors, integrity_status = _validate_package(package_dir)
    assert integrity_status == "invalid"
    assert any("digest mismatch for reports/report_core.json" in error for error in errors)
