from __future__ import annotations

import copy
import json
import os
import ssl
import subprocess
import sys
import tempfile
import time
from io import BytesIO
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[3]
EVIDENCE_DIR = ROOT / "conformance" / "evidence"
LIVE_DIR = EVIDENCE_DIR / "live_bindings"
SCRIPTS_DIR = ROOT / "scripts"
INTEROP_TOOLS_DIR = ROOT / "interop" / "tools"
RUNNER_DIR = ROOT / "conformance" / "runner"
for path in (EVIDENCE_DIR, LIVE_DIR, SCRIPTS_DIR, INTEROP_TOOLS_DIR, RUNNER_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from aicp_external_evidence_runner import run_evidence  # noqa: E402
from aicp_live_binding_runner import run_live_binding_evidence  # noqa: E402
from interop_submission_validation import (  # noqa: E402
    evaluate_strong_report_evidence,
)
from interop_matrix import _manifest_entry  # noqa: E402
from live_binding_process import (  # noqa: E402
    LiveProcessError,
    explicit_environment,
    spawn_process,
    terminate_and_reap,
    validate_loopback_url,
    wait_ready_descriptor,
)
from live_binding_test_implementation import (  # noqa: E402
    CONTROL_NEGATIVE_MODES,
    HTTP_CLIENT_NEGATIVE_MODES,
    HTTP_SERVER_NEGATIVE_MODES,
    MCP_CLIENT_NEGATIVE_MODES,
    MCP_SERVER_NEGATIVE_MODES,
)
from live_binding_trace import (  # noqa: E402
    canonical_digest,
    load_scenario_catalog,
    observation_map,
    semantic_digest,
)
from live_trace_evaluator import evaluate_v2_trace  # noqa: E402
from live_trace_normalization import semantic_digest_v2  # noqa: E402
from live_http_transport import (  # noqa: E402
    LiveProcessError as HttpTransportError,
    execute_http_client,
    http_request,
    message_for_session,
    load_messages,
    start_http_server,
    stop_http_server,
    websocket_pull,
)
from live_http_capture import idempotency_key_valid  # noqa: E402
from live_mcp_transport import execute_mcp_server  # noqa: E402
from live_tls import generate_ephemeral_tls_material, server_ssl_context  # noqa: E402
from report_evaluator import evaluate_report  # noqa: E402
from target_catalog import (  # noqa: E402
    BUNDLE_MANIFEST_PATH,
    BINDING_TARGET_KEYS,
    CURRENT_TCK_RELEASE_ID,
    FROZEN_TCK_1_4_BUNDLE_MANIFEST_DIGEST,
    FROZEN_TCK_1_4_RECORD_DIGEST,
    FROZEN_TCK_1_4_REGISTRY_SNAPSHOT_DIGEST,
    FROZEN_TCK_1_4_REPORT_SCHEMA_DIGEST,
    FROZEN_TCK_1_4_RUNNER_BUNDLE_DIGEST,
    FROZEN_TCK_1_4_TARGET_CATALOG_DIGESTS,
    FROZEN_TCK_1_4_TARGET_REGISTRY_DIGEST,
    FROZEN_TCK_1_4_TARGET_REGISTRY_SCHEMA_DIGEST,
    FROZEN_TCK_1_5_BUNDLE_MANIFEST_DIGEST,
    FROZEN_TCK_1_5_ENDPOINT_DESCRIPTOR_SCHEMA_DIGEST,
    FROZEN_TCK_1_5_LIVE_TRACE_SCHEMA_DIGEST,
    FROZEN_TCK_1_5_RECORD_DIGEST,
    FROZEN_TCK_1_5_REGISTRY_SNAPSHOT_DIGEST,
    FROZEN_TCK_1_5_REPORT_SCHEMA_DIGEST,
    FROZEN_TCK_1_5_RUNNER_BUNDLE_DIGEST,
    FROZEN_TCK_1_5_TARGET_CATALOG_DIGESTS,
    FROZEN_TCK_1_5_TARGET_REGISTRY_DIGEST,
    FROZEN_TCK_1_5_TARGET_REGISTRY_SCHEMA_DIGEST,
    FROZEN_TCK_1_6_BUNDLE_MANIFEST_DIGEST,
    FROZEN_TCK_1_6_ENDPOINT_DESCRIPTOR_SCHEMA_DIGEST,
    FROZEN_TCK_1_6_LIVE_TRACE_SCHEMA_DIGEST,
    FROZEN_TCK_1_6_RECORD_DIGEST,
    FROZEN_TCK_1_6_REGISTRY_SNAPSHOT_DIGEST,
    FROZEN_TCK_1_6_REPORT_SCHEMA_DIGEST,
    FROZEN_TCK_1_6_RUNNER_BUNDLE_DIGEST,
    FROZEN_TCK_1_6_TARGET_CATALOG_DIGESTS,
    FROZEN_TCK_1_6_TARGET_REGISTRY_DIGEST,
    FROZEN_TCK_1_6_TARGET_REGISTRY_SCHEMA_DIGEST,
    FROZEN_TCK_1_7_BUNDLE_MANIFEST_DIGEST,
    FROZEN_TCK_1_7_LIVE_TRACE_SCHEMA_DIGEST,
    FROZEN_TCK_1_7_PUBLIC_SCENARIO_SCHEMA_DIGEST,
    FROZEN_TCK_1_7_RECORD_DIGEST,
    FROZEN_TCK_1_7_REGISTRY_SNAPSHOT_DIGEST,
    FROZEN_TCK_1_7_REPORT_SCHEMA_DIGEST,
    FROZEN_TCK_1_7_RUNNER_BUNDLE_DIGEST,
    FROZEN_TCK_1_7_TARGET_CATALOG_DIGESTS,
    FROZEN_TCK_1_7_TARGET_REGISTRY_DIGEST,
    FROZEN_TCK_1_7_TARGET_REGISTRY_SCHEMA_DIGEST,
    TCK_1_5_RELEASE_ID,
    TCK_1_6_RELEASE_ID,
    TCK_1_7_RELEASE_ID,
    TCK_1_4_RELEASE_ID,
    canonical_digest as target_canonical_digest,
    file_digest,
    load_json,
    release_policy,
    release_record,
    release_snapshot_digest,
    release_target_entry,
    resolve_target_record,
    runtime_import_closure,
    target_catalog,
    validate_bundle_manifest,
    validate_release_registry,
    validate_target_catalog,
    validate_target_registry,
)
from target_handlers import resolve_handler  # noqa: E402
from aicp_conformance_runner import _run_binding_suite  # noqa: E402


IMPLEMENTATION = "conformance/evidence/live_bindings/live_binding_test_implementation.py"
EXPECTED_MARKS = {
    "BIND-HTTP@0.1": "AICP-BIND-HTTP-0.1",
    "BIND-MCP@0.1": "AICP-BIND-MCP-0.1",
}


def _command(
    binding: str,
    role: str,
    kind: str,
    mode: str = "good",
    implementation_id: str | None = None,
) -> list[str]:
    command = [
        sys.executable,
        IMPLEMENTATION,
        "--binding",
        binding,
        "--role",
        role,
        "--kind",
        kind,
        "--mode",
        mode,
    ]
    if implementation_id is not None:
        command.extend(["--implementation-id", implementation_id])
    return command


def _run(
    binding: str,
    *,
    kind: str = "external_implementation",
    server_mode: str = "good",
    client_mode: str = "good",
    full: bool = True,
    timeout: float = 3,
    implementation_id: str | None = None,
) -> dict:
    target = "BIND-HTTP@0.1" if binding == "http" else "BIND-MCP@0.1"
    return run_live_binding_evidence(
        _command(binding, "server_under_test", kind, server_mode, implementation_id),
        _command(binding, "client_under_test", kind, client_mode, implementation_id) if full else None,
        target=target,
        mode="full-binding" if full else "smoke",
        timeout_seconds=timeout,
        timestamp="2026-08-21T00:00:00Z",
    )


@pytest.fixture(scope="module")
def external_reports() -> dict[str, dict]:
    return {binding: _run(binding) for binding in ("http", "mcp")}


def _recompute_trace(report: dict) -> None:
    artifact = report["generated_artifacts"][0]
    runs = artifact["content"]["runs"]
    artifact["content"]["semantic_digest"] = semantic_digest(runs[0])
    artifact["content"]["repeat_semantic_digest"] = semantic_digest(runs[1])
    artifact["content_digest"] = canonical_digest(artifact["content"])
    artifact["repeat_content_digest"] = artifact["content_digest"]


def _set_fact(report: dict, scenario_id: str, name: str, value: object) -> None:
    for run in report["generated_artifacts"][0]["content"]["runs"]:
        interaction = next(
            item for item in run["interactions"] if item["scenario_id"] == scenario_id
        )
        observation = next(
            item for item in interaction["observations"] if item["name"] == name
        )
        observation["value"] = value
    _recompute_trace(report)


def test_exact_binding_targets_and_current_tck_registry() -> None:
    assert BINDING_TARGET_KEYS == ("BIND-HTTP@0.1", "BIND-MCP@0.1")
    assert CURRENT_TCK_RELEASE_ID == "AICP-EVIDENCE-TCK-1.9.0"
    assert validate_target_registry() == []
    assert validate_release_registry() == []
    for key, mark in EXPECTED_MARKS.items():
        record = resolve_target_record(key)
        assert record.target_kind == "binding"
        assert record.execution_mode == "full-binding"
        assert record.evidence_claim_type == "implements_binding"
        assert record.expected_mark == mark
        assert record.current_release_id == CURRENT_TCK_RELEASE_ID
        assert validate_target_catalog(
            target_catalog(record),
            record=record,
            handler=resolve_handler(record.handler_id),
        ) == []


def test_tck_14_is_byte_frozen_and_still_strong_eligible() -> None:
    release = release_record(TCK_1_4_RELEASE_ID)
    assert target_canonical_digest(release) == FROZEN_TCK_1_4_RECORD_DIGEST
    assert release_snapshot_digest(TCK_1_4_RELEASE_ID) == FROZEN_TCK_1_4_REGISTRY_SNAPSHOT_DIGEST
    assert file_digest(EVIDENCE_DIR / "evidence_runner_bundle_v1_4.json") == FROZEN_TCK_1_4_BUNDLE_MANIFEST_DIGEST
    assert release["runner_bundle"]["digest"] == FROZEN_TCK_1_4_RUNNER_BUNDLE_DIGEST
    assert release["report_schema"]["content_digest"] == FROZEN_TCK_1_4_REPORT_SCHEMA_DIGEST
    assert release["target_registry"]["content_digest"] == FROZEN_TCK_1_4_TARGET_REGISTRY_DIGEST
    assert release["target_registry"]["schema_digest"] == FROZEN_TCK_1_4_TARGET_REGISTRY_SCHEMA_DIGEST
    assert {
        item["target_key"]: item["target_catalog"]["content_digest"]
        for item in release["targets"]
    } == FROZEN_TCK_1_4_TARGET_CATALOG_DIGESTS
    assert release_policy(TCK_1_4_RELEASE_ID)["strong_eligible"] is True


def test_exact_tck_11_and_tck_14_reports_remain_eligible() -> None:
    tck_11_report = json.loads(
        (
            ROOT
            / "interop/submissions/examples/capability_claim/reports/"
            "report_capability_projection_v1.json"
        ).read_text(encoding="utf-8")
    )
    assert evaluate_report(
        tck_11_report,
        expected_implementation_id="example-projection-v1-implementation",
        expected_implementation_version="1.0.0-example",
    )["status"] == "eligible"

    tck_14_report = run_evidence(
        [
            sys.executable,
            "conformance/evidence/product_profile_fake_adapters.py",
            "--mode",
            "external_good",
        ],
        target="AICP-MEDIATED-BLOCKING@0.1",
        mode="full-profile",
        timestamp="2026-08-21T00:00:00Z",
    )
    release = release_record(TCK_1_4_RELEASE_ID)
    entry = release_target_entry(release, "AICP-MEDIATED-BLOCKING@0.1")
    tck_14_report["report_format_version"] = "2.1"
    tck_14_report["runner"] = {
        "name": "aicp-external-evidence-runner",
        "version": "2.1",
        "source_revision": release["runner_bundle"]["digest"],
    }
    tck_14_report["tck_release"] = {
        "release_id": release["release_id"],
        "registry_digest": release_snapshot_digest(release["release_id"]),
        "target_registry_digest": release["target_registry"]["content_digest"],
        "target_registry_schema_digest": release["target_registry"]["schema_digest"],
        "target_catalog_digest": entry["target_catalog"]["content_digest"],
        "report_schema_digest": release["report_schema"]["content_digest"],
        "runner_bundle_digest": release["runner_bundle"]["digest"],
    }
    tck_14_report["target"]["target_catalog_digest"] = entry["target_catalog"][
        "content_digest"
    ]
    tck_14_report["required_suites"] = entry["required_suites"]
    tck_14_report["input_artifacts"] = entry["required_input_artifacts"]
    tck_14_report["case_results"] = [
        item
        for item in tck_14_report["case_results"]
        if item["case_id"] in set(entry["mandatory_case_ids"])
    ]
    assert evaluate_report(
        tck_14_report,
        expected_implementation_id="test-only-product-profile-external",
        expected_implementation_version="1.0.0",
    )["status"] == "eligible"


def test_tck_15_is_byte_frozen_and_explicitly_ineligible() -> None:
    release = release_record(TCK_1_5_RELEASE_ID)
    assert target_canonical_digest(release) == FROZEN_TCK_1_5_RECORD_DIGEST
    assert release_snapshot_digest(TCK_1_5_RELEASE_ID) == FROZEN_TCK_1_5_REGISTRY_SNAPSHOT_DIGEST
    assert file_digest(EVIDENCE_DIR / "evidence_runner_bundle_v1_5.json") == FROZEN_TCK_1_5_BUNDLE_MANIFEST_DIGEST
    assert release["runner_bundle"]["digest"] == FROZEN_TCK_1_5_RUNNER_BUNDLE_DIGEST
    assert release["report_schema"]["content_digest"] == FROZEN_TCK_1_5_REPORT_SCHEMA_DIGEST
    assert release["target_registry"]["content_digest"] == FROZEN_TCK_1_5_TARGET_REGISTRY_DIGEST
    assert release["target_registry"]["schema_digest"] == FROZEN_TCK_1_5_TARGET_REGISTRY_SCHEMA_DIGEST
    assert {item["target_key"]: item["target_catalog"]["content_digest"] for item in release["targets"]} == FROZEN_TCK_1_5_TARGET_CATALOG_DIGESTS
    assert file_digest(LIVE_DIR / "live_binding_trace.schema.json") == FROZEN_TCK_1_5_LIVE_TRACE_SCHEMA_DIGEST
    assert file_digest(LIVE_DIR / "live_endpoint_descriptor.schema.json") == FROZEN_TCK_1_5_ENDPOINT_DESCRIPTOR_SCHEMA_DIGEST
    assert release_policy(TCK_1_5_RELEASE_ID)["strong_eligible"] is False


def test_zero_real_external_submissions_and_no_tck_16_adoption() -> None:
    matrix = json.loads((ROOT / "interop/interop_matrix.json").read_text(encoding="utf-8"))
    assert matrix["real_submissions"] == []
    references: list[str] = []
    for path in (ROOT / "interop/submissions").iterdir():
        if not path.is_dir() or path.name in {"examples", "templates"} or path.name.startswith("dryrun-"):
            continue
        for candidate in path.rglob("*.json"):
            if TCK_1_6_RELEASE_ID in candidate.read_text(encoding="utf-8"):
                references.append(candidate.relative_to(ROOT).as_posix())
    assert references == []


def test_tck_16_is_byte_frozen_and_explicitly_ineligible() -> None:
    release = release_record(TCK_1_6_RELEASE_ID)
    assert target_canonical_digest(release) == FROZEN_TCK_1_6_RECORD_DIGEST
    assert release_snapshot_digest(TCK_1_6_RELEASE_ID) == FROZEN_TCK_1_6_REGISTRY_SNAPSHOT_DIGEST
    assert file_digest(EVIDENCE_DIR / "evidence_runner_bundle_v1_6.json") == FROZEN_TCK_1_6_BUNDLE_MANIFEST_DIGEST
    assert release["runner_bundle"]["digest"] == FROZEN_TCK_1_6_RUNNER_BUNDLE_DIGEST
    assert release["report_schema"]["content_digest"] == FROZEN_TCK_1_6_REPORT_SCHEMA_DIGEST
    assert release["target_registry"]["content_digest"] == FROZEN_TCK_1_6_TARGET_REGISTRY_DIGEST
    assert release["target_registry"]["schema_digest"] == FROZEN_TCK_1_6_TARGET_REGISTRY_SCHEMA_DIGEST
    assert {item["target_key"]: item["target_catalog"]["content_digest"] for item in release["targets"]} == FROZEN_TCK_1_6_TARGET_CATALOG_DIGESTS
    assert file_digest(LIVE_DIR / "live_binding_trace_v2.schema.json") == FROZEN_TCK_1_6_LIVE_TRACE_SCHEMA_DIGEST
    assert file_digest(LIVE_DIR / "live_endpoint_descriptor_v2.schema.json") == FROZEN_TCK_1_6_ENDPOINT_DESCRIPTOR_SCHEMA_DIGEST
    assert release_policy(TCK_1_6_RELEASE_ID)["strong_eligible"] is False


def test_zero_real_external_submissions_and_no_tck_17_adoption() -> None:
    matrix = json.loads((ROOT / "interop/interop_matrix.json").read_text(encoding="utf-8"))
    assert matrix["real_submissions"] == []
    references: list[str] = []
    for path in (ROOT / "interop/submissions").iterdir():
        if not path.is_dir() or path.name in {"examples", "templates"} or path.name.startswith("dryrun-"):
            continue
        for candidate in path.rglob("*.json"):
            if TCK_1_7_RELEASE_ID in candidate.read_text(encoding="utf-8"):
                references.append(candidate.relative_to(ROOT).as_posix())
    assert references == []


def test_tck_17_is_byte_frozen_and_explicitly_ineligible() -> None:
    release = release_record(TCK_1_7_RELEASE_ID)
    assert target_canonical_digest(release) == FROZEN_TCK_1_7_RECORD_DIGEST
    assert release_snapshot_digest(TCK_1_7_RELEASE_ID) == FROZEN_TCK_1_7_REGISTRY_SNAPSHOT_DIGEST
    assert file_digest(EVIDENCE_DIR / "evidence_runner_bundle_v1_7.json") == FROZEN_TCK_1_7_BUNDLE_MANIFEST_DIGEST
    assert release["runner_bundle"]["digest"] == FROZEN_TCK_1_7_RUNNER_BUNDLE_DIGEST
    assert release["report_schema"]["content_digest"] == FROZEN_TCK_1_7_REPORT_SCHEMA_DIGEST
    assert release["target_registry"]["content_digest"] == FROZEN_TCK_1_7_TARGET_REGISTRY_DIGEST
    assert release["target_registry"]["schema_digest"] == FROZEN_TCK_1_7_TARGET_REGISTRY_SCHEMA_DIGEST
    assert {item["target_key"]: item["target_catalog"]["content_digest"] for item in release["targets"]} == FROZEN_TCK_1_7_TARGET_CATALOG_DIGESTS
    assert file_digest(LIVE_DIR / "live_binding_trace_v3.schema.json") == FROZEN_TCK_1_7_LIVE_TRACE_SCHEMA_DIGEST
    assert file_digest(LIVE_DIR / "live_public_scenario_v1.schema.json") == FROZEN_TCK_1_7_PUBLIC_SCENARIO_SCHEMA_DIGEST
    assert release_policy(TCK_1_7_RELEASE_ID)["strong_eligible"] is False


def test_tck_16_bundle_closes_over_live_binding_package_imports() -> None:
    paths = set(runtime_import_closure())
    expected_live_runtime = {
        "conformance/evidence/live_bindings/__init__.py",
        "conformance/evidence/live_bindings/live_binding_handler.py",
        "conformance/evidence/live_bindings/live_binding_process.py",
        "conformance/evidence/live_bindings/live_binding_trace.py",
        "conformance/evidence/live_bindings/live_http_capture.py",
        "conformance/evidence/live_bindings/live_http_transport.py",
        "conformance/evidence/live_bindings/live_mcp_capture.py",
        "conformance/evidence/live_bindings/live_mcp_transport.py",
        "conformance/evidence/live_bindings/live_public_scenarios.py",
        "conformance/evidence/live_bindings/live_tls.py",
        "conformance/evidence/live_bindings/live_trace_evaluator.py",
        "conformance/evidence/live_bindings/live_trace_normalization.py",
    }
    assert expected_live_runtime <= paths

    runner_path = "conformance/evidence/aicp_live_binding_runner.py"
    mutated = (ROOT / runner_path).read_bytes() + (
        b"\nfrom live_bindings.live_binding_test_implementation import main\n"
    )
    errors = validate_bundle_manifest(
        load_json(BUNDLE_MANIFEST_PATH),
        overrides={runner_path: mutated},
    )
    assert any("unlisted runtime imports" in error for error in errors)
    assert any("live_binding_test_implementation.py" in error for error in errors)


def test_live_child_environment_is_allowlisted_and_actual_child_cannot_see_secrets(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sentinels = {
        "GITHUB_TOKEN": "AICP_SENTINEL_GITHUB",
        "OPENAI_API_KEY": "AICP_SENTINEL_OPENAI",
        "AWS_SECRET_ACCESS_KEY": "AICP_SENTINEL_AWS",
        "AICP_UNRELATED_SECRET": "AICP_SENTINEL_OTHER",
    }
    for name, value in sentinels.items():
        monkeypatch.setenv(name, value)
    environment = explicit_environment({"AICP_LIVE_RUN_ID": "allowlist-test"})
    assert not set(sentinels) & set(environment)
    child = subprocess.run(
        [
            sys.executable,
            "-c",
            "import os,sys; sys.exit(any(name in os.environ for name in "
            + repr(sorted(sentinels))
            + "))",
        ],
        cwd=ROOT,
        env=environment,
        shell=False,
        check=False,
        capture_output=True,
        text=True,
    )
    assert child.returncode == 0
    assert child.stdout == ""
    assert child.stderr == ""


def test_secret_reflection_is_classified_and_never_serialized(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bearer = "m64-correction-reflection-sentinel"
    import aicp_live_binding_runner as runner

    monkeypatch.setattr(runner.secrets, "token_urlsafe", lambda _size: bearer)
    report = _run("http", server_mode="secret_reflection")
    assert report["passed"] is False
    assert report["compatibility_marks"] == []
    assert any(
        failure["test_id"] == "EVIDENCE_LIVE_SECRET_REFLECTION"
        for failure in report["failures"]
    )
    assert bearer not in json.dumps(report, sort_keys=True)


def test_observation_only_v1_trace_and_forged_v2_observations_are_rejected(
    external_reports: dict[str, dict],
) -> None:
    report = copy.deepcopy(external_reports["http"])
    artifact = report["generated_artifacts"][0]
    artifact["content"]["trace_version"] = "aicp.live_binding_trace.v1"
    for run in artifact["content"]["runs"]:
        run["interactions"] = [
            {
                "interaction_id": item["interaction_id"],
                "role": item["role"],
                "scenario_id": item["scenario_id"],
                "transport": "websocket" if item["transport"] == "wss" else item["transport"],
                "operation": item["operation"],
                "observations": [
                    {"name": "network_boundary", "value": "loopback_socket"},
                    {"name": "message_digest_equal", "value": True},
                    {"name": "websocket_handshake_valid", "value": True},
                ],
            }
            for item in run["interactions"]
            if item["transport"] != "wss"
        ]
    _recompute_trace(report)
    assert evaluate_report(report)["status"] == "rejected"

    contradictory = copy.deepcopy(external_reports["http"])
    _mutate_raw(contradictory, "wrong_http_path", "LIVE-HTTP-SERVER-INGEST")
    for run_index in range(2):
        _interaction(contradictory, "LIVE-HTTP-SERVER-INGEST", run_index)["observations"] = [
            {"name": "request_path_valid", "value": True}
        ]
    _recompute_trace(contradictory)
    assert evaluate_report(contradictory)["status"] == "rejected"


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("m1", True),
        ("tenant-m1", True),
        ("tenant:m1", True),
        ("tenant/m1", True),
        ("prefixm1", False),
        ("xm1", False),
        ("wrong", False),
    ],
)
def test_live_idempotency_rule_has_exact_static_tb_http_parity(
    key: str,
    expected: bool,
    tmp_path: Path,
) -> None:
    case = json.loads(
        (ROOT / "fixtures/bindings/http-ws/TB-HTTP-01_sendMessage.json").read_text(
            encoding="utf-8"
        )
    )
    case["http_request"]["headers"]["Idempotency-Key"] = key
    case_path = tmp_path / f"idempotency-{key.replace('/', '_')}.json"
    case_path.write_text(json.dumps(case), encoding="utf-8")
    schema_path = ROOT / "schemas/bindings/bind-http-ws.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    suite = {
        "suite_id": "TB-HTTP-0.1-IDEMPOTENCY-DIFFERENTIAL",
        "suite_version": "0.1.0-test",
        "aicp_version": "0.1",
        "schema_ref": str(schema_path.relative_to(ROOT)),
        "cases": [str(case_path)],
        "compatibility_mark": "AICP-BIND-HTTP-0.1",
        "checks": [{"test_id": "TB-HTTP-IDEMPOTENCY-01"}],
    }
    ordinary_report = _run_binding_suite(
        suite,
        schema,
        tmp_path / "suite.json",
        "legacy",
    )
    assert ordinary_report["passed"] is expected
    assert idempotency_key_valid(key, "m1") is expected


def test_actual_wss_verification_and_wrong_ca_failure() -> None:
    with tempfile.TemporaryDirectory(prefix="aicp-live-wss-direct-") as temporary:
        root = Path(temporary)
        material = generate_ephemeral_tls_material(root / "trusted", stem="trusted")
        wrong = generate_ephemeral_tls_material(root / "wrong", stem="wrong")
        bearer = "wss-direct-test-bearer"
        server, state, thread = start_http_server(
            bearer,
            ssl_context=server_ssl_context(material),
        )
        base = f"https://127.0.0.1:{server.server_address[1]}"
        wss = f"wss://127.0.0.1:{server.server_address[1]}"
        try:
            status, _, created, _ = http_request(
                base,
                "POST",
                "/aicp/v1/sessions",
                bearer=bearer,
                body={"client_id": "wss-direct"},
                tls_ca_file=str(material.ca_file),
            )
            assert status == 201 and created
            session = str(created["session_id"])
            message = message_for_session(load_messages()[0], session)
            status, _, _, _ = http_request(
                base,
                "POST",
                f"/aicp/v1/sessions/{session}/messages",
                bearer=bearer,
                body=message,
                headers={"Idempotency-Key": str(message["message_id"])},
                tls_ca_file=str(material.ca_file),
            )
            assert status == 202
            status, frame = websocket_pull(
                wss,
                f"/aicp/v1/sessions/{session}/messages/ws",
                bearer=bearer,
                after="c0",
                limit=1,
                tls_ca_file=str(material.ca_file),
            )
            assert status == 101
            assert frame["type"] == "messages"
            with pytest.raises((ssl.SSLCertVerificationError, LiveProcessError)):
                websocket_pull(
                    wss,
                    f"/aicp/v1/sessions/{session}/messages/ws",
                    bearer=bearer,
                    after="c0",
                    limit=1,
                    tls_ca_file=str(wrong.ca_file),
                )
            state.mode = "websocket_wrong_accept"
            with pytest.raises(HttpTransportError, match="handshake validation failed"):
                websocket_pull(
                    wss,
                    f"/aicp/v1/sessions/{session}/messages/ws",
                    bearer=bearer,
                    after="c0",
                    limit=1,
                    tls_ca_file=str(material.ca_file),
                )
        finally:
            stop_http_server(server, thread)


def test_exact_live_scenario_counts_and_fresh_websocket_keys(
    external_reports: dict[str, dict],
) -> None:
    http_run = external_reports["http"]["generated_artifacts"][0]["content"]["runs"][0]
    mcp_run = external_reports["mcp"]["generated_artifacts"][0]["content"]["runs"][0]
    assert sum(item["role"] == "server_under_test" for item in http_run["interactions"]) == 16
    assert sum(item["role"] == "client_under_test" for item in http_run["interactions"]) == 16
    assert sum(item["role"] == "server_under_test" for item in mcp_run["interactions"]) == 6
    assert sum(item["role"] == "client_under_test" for item in mcp_run["interactions"]) == 6
    websocket_interactions = [
        item
        for item in http_run["interactions"]
        if item["transport"] in {"websocket", "wss"}
    ]
    keys = [
        exchange["request"]["headers"]["sec-websocket-key"]
        for item in websocket_interactions
        for exchange in item["transport_evidence"]["exchanges"]
        if exchange.get("scheme") in {"ws", "wss"}
    ]
    assert len(keys) == 8
    assert len(set(keys)) == len(keys)
    assert all(
        exchange.get("tls_verified") is True
        for item in websocket_interactions
        if item["transport"] == "wss"
        for exchange in item["transport_evidence"]["exchanges"]
    )


def _prefixed_values(value: object, prefix: str) -> set[str]:
    if isinstance(value, str):
        return {value} if value.startswith(prefix) else set()
    if isinstance(value, dict):
        return {
            item
            for child in value.values()
            for item in _prefixed_values(child, prefix)
        }
    if isinstance(value, list):
        return {
            item for child in value for item in _prefixed_values(child, prefix)
        }
    return set()


@pytest.mark.parametrize("binding", ["http", "mcp"])
def test_two_clean_runs_use_distinct_opaque_challenges_but_equal_semantics(
    external_reports: dict[str, dict], binding: str
) -> None:
    content = external_reports[binding]["generated_artifacts"][0]["content"]
    first, second = content["runs"]
    prefixes = ("session:", "cursor:") if binding == "http" else ("cursor:",)
    for prefix in prefixes:
        first_values = _prefixed_values(first, prefix)
        second_values = _prefixed_values(second, prefix)
        assert first_values
        assert second_values
        assert first_values.isdisjoint(second_values)
    assert content["semantic_digest"] == content["repeat_semantic_digest"]


def test_wss_client_challenge_is_repository_observed(
    external_reports: dict[str, dict]
) -> None:
    for run_index in range(2):
        evidence = _interaction(
            external_reports["http"], "LIVE-HTTP-CLIENT-WSS", run_index
        )["transport_evidence"]
        assert evidence["tls_challenges"] == [
            {
                "endpoint_class": "untrusted",
                "connection_attempted": True,
                "tls_failure_class": "certificate_rejected",
                "tls_handshake_completed": False,
                "websocket_application_handshake_observed": False,
                "connection_order": 1,
                "tls_failure_order": 2,
                "tls_handshake_order": None,
                "websocket_application_handshake_order": None,
            },
            {
                "endpoint_class": "trusted",
                "connection_attempted": True,
                "tls_failure_class": "tls_handshake_completed",
                "tls_handshake_completed": True,
                "websocket_application_handshake_observed": True,
                "connection_order": 3,
                "tls_failure_order": None,
                "tls_handshake_order": 4,
                "websocket_application_handshake_order": 5,
            },
        ]


@pytest.mark.parametrize(
    "mutation",
    [
        "remove_untrusted",
        "accept_untrusted_tls",
        "upgrade_untrusted",
        "remove_trusted_success",
        "swap_endpoint_classes",
        "change_role_binding",
        "raw_tcp_failure_class",
        "plaintext_failure_class",
        "pre_certificate_abort",
        "missing_failure_order",
    ],
)
def test_wss_challenge_mutations_are_rejected(
    external_reports: dict[str, dict], mutation: str
) -> None:
    report = copy.deepcopy(external_reports["http"])
    for run_index in range(2):
        interaction = _interaction(report, "LIVE-HTTP-CLIENT-WSS", run_index)
        challenges = interaction["transport_evidence"]["tls_challenges"]
        if mutation == "remove_untrusted":
            challenges.pop(0)
        elif mutation == "accept_untrusted_tls":
            challenges[0]["tls_handshake_completed"] = True
        elif mutation == "upgrade_untrusted":
            challenges[0]["websocket_application_handshake_observed"] = True
        elif mutation == "remove_trusted_success":
            challenges[1]["tls_handshake_completed"] = False
        elif mutation == "swap_endpoint_classes":
            challenges[0]["endpoint_class"] = "trusted"
            challenges[1]["endpoint_class"] = "untrusted"
        elif mutation == "raw_tcp_failure_class":
            challenges[0]["tls_failure_class"] = "no_tls_handshake"
        elif mutation == "plaintext_failure_class":
            challenges[0]["tls_failure_class"] = "non_tls_protocol"
        elif mutation == "pre_certificate_abort":
            challenges[0]["tls_failure_class"] = "tls_pre_certificate_abort"
        elif mutation == "missing_failure_order":
            challenges[0]["tls_failure_order"] = None
        else:
            interaction["role"] = "server_under_test"
    _recompute_trace(report)
    assert evaluate_report(report)["status"] == "rejected"


@pytest.mark.parametrize("binding", ["http", "mcp"])
def test_reference_full_and_smoke_have_no_external_mark(binding: str) -> None:
    reference = _run(binding, kind="reference_corpus")
    assert reference["passed"] is True
    assert reference["compatibility_marks"] == []
    assert evaluate_report(reference)["status"] == "ineligible"
    smoke = _run(binding, kind="reference_corpus", full=False)
    assert smoke["passed"] is True
    assert smoke["compatibility_marks"] == []
    assert evaluate_report(smoke)["status"] == "ineligible"


@pytest.mark.parametrize("binding", ["http", "mcp"])
def test_external_two_role_report_gets_only_exact_binding_mark(
    binding: str, external_reports: dict[str, dict]
) -> None:
    report = external_reports[binding]
    target = "BIND-HTTP@0.1" if binding == "http" else "BIND-MCP@0.1"
    assert report["passed"] is True
    assert report["report_format_version"] == "2.2"
    assert report["compatibility_marks"] == [EXPECTED_MARKS[target]]
    evaluation = evaluate_report(report)
    assert evaluation["status"] == "eligible"
    assert evaluation["eligible_targets"] == [
        {
            "kind": "binding",
            "target_id": target.rsplit("@", 1)[0],
            "target_version": "0.1",
        }
    ]


@pytest.mark.parametrize("mode", ["request_response_only", "no_sse", "no_websocket"])
def test_optional_http_features_are_descriptor_driven(mode: str) -> None:
    report = _run("http", server_mode=mode, client_mode=mode)
    assert report["passed"] is True
    assert report["compatibility_marks"] == ["AICP-BIND-HTTP-0.1"]
    roles = report["generated_artifacts"][0]["content"]["roles"]
    if mode in {"request_response_only", "no_sse"}:
        assert all(role["declared_features"]["sse"] is False for role in roles.values())
    if mode in {"request_response_only", "no_websocket"}:
        assert all(role["declared_features"]["websocket"] is False for role in roles.values())


@pytest.mark.parametrize("mode", sorted(CONTROL_NEGATIVE_MODES))
def test_generic_control_negative_modes_suppress_mark(mode: str) -> None:
    if mode == "subject_mismatch":
        report = _run("http", client_mode=mode, timeout=0.35)
    else:
        report = _run("http", server_mode=mode, timeout=0.35)
    assert report["passed"] is False
    assert report["compatibility_marks"] == []


@pytest.mark.parametrize("mode", sorted(HTTP_SERVER_NEGATIVE_MODES))
def test_every_http_server_negative_mode_suppresses_mark(mode: str) -> None:
    report = _run("http", server_mode=mode, timeout=0.75)
    assert report["passed"] is False
    assert report["compatibility_marks"] == []


@pytest.mark.parametrize("mode", sorted(HTTP_CLIENT_NEGATIVE_MODES))
def test_every_http_client_negative_mode_suppresses_mark(mode: str) -> None:
    report = _run("http", client_mode=mode, timeout=0.75)
    assert report["passed"] is False
    assert report["compatibility_marks"] == []


@pytest.mark.parametrize("mode", sorted(MCP_SERVER_NEGATIVE_MODES))
def test_every_mcp_server_negative_mode_suppresses_mark(mode: str) -> None:
    report = _run("mcp", server_mode=mode, timeout=0.35)
    assert report["passed"] is False
    assert report["compatibility_marks"] == []


@pytest.mark.parametrize("mode", sorted(MCP_CLIENT_NEGATIVE_MODES))
def test_every_mcp_client_negative_mode_suppresses_mark(mode: str) -> None:
    report = _run("mcp", client_mode=mode, timeout=0.35)
    assert report["passed"] is False
    assert report["compatibility_marks"] == []


RAW_EVIDENCE_MUTATIONS = [
    ("http", "wrong_http_path", "LIVE-HTTP-SERVER-INGEST", "message_ingest"),
    ("http", "wrong_idempotency_delimiter", "LIVE-HTTP-SERVER-INGEST", "message_ingest"),
    ("http", "changed_message_hash", "LIVE-HTTP-SERVER-INGEST", "message_ingest"),
    ("http", "cross_session_poll", "LIVE-HTTP-SERVER-POLL", "polling_cursor"),
    ("http", "wrong_cursor", "LIVE-HTTP-SERVER-ACK", "explicit_ack"),
    ("http", "wrong_ack", "LIVE-HTTP-SERVER-ACK", "explicit_ack"),
    ("http", "wrong_sse_event_id", "LIVE-HTTP-SERVER-SSE", "sse_stream"),
    ("http", "wrong_sse_more", "LIVE-HTTP-SERVER-SSE", "sse_stream"),
    ("http", "wrong_last_event_id", "LIVE-HTTP-SERVER-SSE-RECONNECT", "sse_reconnect"),
    ("http", "wrong_websocket_accept", "LIVE-HTTP-SERVER-WEBSOCKET", "websocket_pull"),
    ("http", "wrong_websocket_cursor", "LIVE-HTTP-SERVER-WEBSOCKET", "websocket_pull"),
    ("mcp", "wrong_mcp_request_id", "LIVE-MCP-SERVER-SEND", "send_message"),
    ("mcp", "wrong_mcp_tool", "LIVE-MCP-SERVER-SEND", "send_message"),
    ("mcp", "wrong_mcp_after_cursor", "LIVE-MCP-SERVER-POLL", "poll_messages"),
    ("mcp", "wrong_mcp_session", "LIVE-MCP-SERVER-POLL", "poll_messages"),
    ("mcp", "wrong_object_content", "LIVE-MCP-SERVER-OBJECT", "get_object"),
]


def _interaction(report: dict, scenario_id: str, run_index: int) -> dict:
    return next(
        item
        for item in report["generated_artifacts"][0]["content"]["runs"][run_index]["interactions"]
        if item["scenario_id"] == scenario_id
    )


def _mutate_raw(report: dict, mutation: str, scenario_id: str) -> None:
    for run_index in range(2):
        evidence = _interaction(report, scenario_id, run_index)["transport_evidence"]
        exchanges = evidence["exchanges"]
        if mutation == "wrong_http_path":
            exchanges[0]["request"]["path"] = "/aicp/v1/sessions/wrong/messages"
        elif mutation == "wrong_idempotency_delimiter":
            exchanges[0]["request"]["headers"]["idempotency-key"] = "prefixm1"
        elif mutation == "changed_message_hash":
            exchanges[0]["request"]["body"]["message_refs"][0]["message_hash"] = "sha256:" + "0" * 64
        elif mutation == "cross_session_poll":
            exchanges[0]["response"]["body"]["message_refs"][0]["session_id"] = "other-session"
        elif mutation == "wrong_cursor":
            exchanges[0]["response"]["body"]["next_cursor"] = "other-cursor"
        elif mutation == "wrong_ack":
            exchanges[1]["request"]["body"]["cursor"] = "other-cursor"
        elif mutation == "wrong_sse_event_id":
            exchanges[0]["events"][0]["id"] = "other-cursor"
        elif mutation == "wrong_sse_more":
            exchanges[0]["events"][-1]["more"] = True
        elif mutation == "wrong_last_event_id":
            exchanges[1]["request"]["headers"]["last-event-id"] = "other-cursor"
        elif mutation == "wrong_websocket_accept":
            ws = next(item for item in exchanges if item.get("scheme") == "ws")
            ws["response"]["headers"]["sec-websocket-accept"] = "wrong-accept"
        elif mutation == "wrong_websocket_cursor":
            ws = next(item for item in exchanges if item.get("server_frame", {}).get("type") == "messages")
            ws["server_frame"]["cursor_after_last"] = "other-cursor"
        elif mutation == "wrong_mcp_request_id":
            exchanges[0]["response"]["id"] = "other-request"
        elif mutation == "wrong_mcp_tool":
            exchanges[0]["request"]["tool"] = "aicp.wrongTool"
        elif mutation == "wrong_mcp_after_cursor":
            exchanges[1]["request"]["arguments"]["after_cursor"] = "other-cursor"
        elif mutation == "wrong_mcp_session":
            exchanges[1]["request"]["arguments"]["session_id"] = "other-session"
        elif mutation == "wrong_object_content":
            exchanges[0]["response"]["result"]["object_content"]["goal"] = "rewritten"
    _recompute_trace(report)


@pytest.mark.parametrize(
    ("binding", "mutation", "scenario_id", "family"),
    RAW_EVIDENCE_MUTATIONS,
)
def test_v2_raw_evidence_mutations_are_load_bearing(
    external_reports: dict[str, dict],
    binding: str,
    mutation: str,
    scenario_id: str,
    family: str,
) -> None:
    report = copy.deepcopy(external_reports[binding])
    _mutate_raw(report, mutation, scenario_id)
    assert evaluate_report(report)["status"] == "rejected"
    target_id = "BIND-HTTP" if binding == "http" else "BIND-MCP"
    errors = evaluate_v2_trace(
        report["generated_artifacts"][0],
        load_scenario_catalog(target_id),
        full_binding=True,
        disabled_families=frozenset({family}),
    )
    assert errors == []


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_interaction",
        "duplicate_interaction",
        "unknown_interaction",
        "duplicate_role",
        "subject_mismatch",
        "wrong_binding",
        "wrong_target_version",
        "wrong_release",
        "wrong_semantic_digest",
        "replayed_subject",
        "forged_pass",
        "forged_mark",
    ],
)
def test_trace_and_report_forgery_mutations_are_rejected(
    external_reports: dict[str, dict], mutation: str
) -> None:
    report = copy.deepcopy(external_reports["http"])
    artifact = report["generated_artifacts"][0]
    content = artifact["content"]
    if mutation == "missing_interaction":
        for run in content["runs"]:
            run["interactions"].pop()
        _recompute_trace(report)
    elif mutation == "duplicate_interaction":
        for run in content["runs"]:
            run["interactions"].append(copy.deepcopy(run["interactions"][-1]))
        _recompute_trace(report)
    elif mutation == "unknown_interaction":
        for run in content["runs"]:
            run["interactions"][0]["scenario_id"] = "LIVE-HTTP-UNKNOWN"
        _recompute_trace(report)
    elif mutation == "duplicate_role":
        content["roles"]["duplicate"] = copy.deepcopy(content["roles"]["server_under_test"])
        _recompute_trace(report)
    elif mutation == "subject_mismatch":
        content["roles"]["client_under_test"]["implementation_digest"] = "sha256:" + "f" * 64
        _recompute_trace(report)
    elif mutation == "replayed_subject":
        for role in content["roles"].values():
            role["implementation_id"] = "another-implementation"
            role["implementation_digest"] = "sha256:" + "f" * 64
        _recompute_trace(report)
    elif mutation == "wrong_binding":
        content["binding"]["binding_id"] = "BIND-MCP"
        _recompute_trace(report)
    elif mutation == "wrong_target_version":
        report["target"]["target_version"] = "9.9"
    elif mutation == "wrong_release":
        report["tck_release"]["release_id"] = "AICP-EVIDENCE-TCK-1.4.0"
    elif mutation == "wrong_semantic_digest":
        content["semantic_digest"] = "sha256:" + "0" * 64
        artifact["content_digest"] = canonical_digest(content)
        artifact["repeat_content_digest"] = artifact["content_digest"]
    elif mutation == "forged_pass":
        report["case_results"][0]["passed"] = False
    else:
        report["compatibility_marks"] = ["AICP-BIND-MCP-0.1"]
    assert evaluate_report(report)["status"] == "rejected"


def test_trace_schema_structurally_rejects_secret_fields(
    external_reports: dict[str, dict]
) -> None:
    from jsonschema import Draft202012Validator

    schema = json.loads((LIVE_DIR / "live_binding_trace_v4.schema.json").read_text(encoding="utf-8"))
    artifact = copy.deepcopy(external_reports["http"]["generated_artifacts"][0])
    artifact["content"]["runs"][0]["interactions"][0]["observations"] = [
        {"name": "authorization", "value": "Bearer forbidden"}
    ]
    assert list(Draft202012Validator(schema).iter_errors(artifact))

    exchange_leak = copy.deepcopy(external_reports["http"]["generated_artifacts"][0])
    exchange_leak["content"]["runs"][0]["interactions"][0][
        "transport_evidence"
    ]["exchanges"][0]["private_oracle"] = "Bearer forbidden"
    assert list(Draft202012Validator(schema).iter_errors(exchange_leak))


def test_semantic_normalization_allows_opaque_spelling_and_order_only(
    external_reports: dict[str, dict]
) -> None:
    report = copy.deepcopy(external_reports["http"])
    artifact = report["generated_artifacts"][0]
    first, second = artifact["content"]["runs"]
    assert first != second
    assert semantic_digest_v2(first) == semantic_digest_v2(second)
    assert evaluate_report(report)["status"] == "eligible"

    broken = copy.deepcopy(report)
    _mutate_raw(broken, "wrong_ack", "LIVE-HTTP-SERVER-ACK")
    assert evaluate_report(broken)["status"] == "rejected"

    message_changed = copy.deepcopy(report)
    _mutate_raw(message_changed, "changed_message_hash", "LIVE-HTTP-SERVER-INGEST")
    assert evaluate_report(message_changed)["status"] == "rejected"


def test_complete_report_never_contains_bearer_or_test_key_material(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    bearer = "m64-secret-bearer-never-serialize"
    key_material = "m64-ephemeral-private-key-never-serialize"
    import aicp_live_binding_runner as runner

    monkeypatch.setattr(runner.secrets, "token_urlsafe", lambda _size: bearer)
    monkeypatch.setenv("AICP_LIVE_TLS_KEY_FILE", key_material)
    encoded = json.dumps(_run("http"), sort_keys=True)
    assert bearer not in encoded
    assert key_material not in encoded
    assert '"authorization":' not in encoded.lower()
    assert '"cookie"' not in encoded.lower()
    assert '"set-cookie"' not in encoded.lower()
    assert '"proxy-authorization"' not in encoded.lower()


def test_direct_http_socket_sse_websocket_and_client_process_capture() -> None:
    bearer = "direct-live-bearer"
    server, state, thread = start_http_server(bearer)
    port = int(server.server_address[1])
    assert port > 0
    base_url = f"http://127.0.0.1:{port}"
    try:
        interactions = execute_http_client(
            base_url,
            bearer,
            role="server_under_test",
        )
        assert state.records
        assert any(item["transport"] == "sse" for item in state.records)
        assert any(item["transport"] == "websocket" for item in state.records)
        assert all(
            item["transport_evidence"]["boundary"]["kind"] == "loopback_socket"
            for item in interactions
        )
    finally:
        stop_http_server(server, thread)

    server, state, thread = start_http_server(bearer)
    try:
        with tempfile.TemporaryDirectory(prefix="aicp-direct-client-") as directory_name:
            directory = Path(directory_name)
            ready = directory / "ready.json"
            scenario = directory / "scenario.json"
            scenario.write_text("{}", encoding="utf-8")
            values = {
                "AICP_LIVE_RUN_ID": "direct-client",
                "AICP_LIVE_BINDING_ID": "BIND-HTTP",
                "AICP_LIVE_BINDING_VERSION": "0.1",
                "AICP_LIVE_ROLE": "client_under_test",
                "AICP_LIVE_READY_FILE": str(ready),
                "AICP_LIVE_SCENARIO_FILE": str(scenario),
                "AICP_LIVE_TEST_BEARER": bearer,
                "AICP_LIVE_ENDPOINT_URL": f"http://127.0.0.1:{server.server_address[1]}",
            }
            process = subprocess.Popen(
                _command("http", "client_under_test", "external_implementation", "request_response_only"),
                cwd=ROOT,
                env=explicit_environment(values),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=False,
            )
            try:
                deadline = time.monotonic() + 5
                wait_ready_descriptor(process, ready, deadline=deadline)
                process.wait(timeout=max(0.1, deadline - time.monotonic()))
                assert process.returncode == 0
                assert any(
                    item["method"] == "POST"
                    and item["path"] == "/aicp/v1/sessions"
                    and "authorization" in item["headers"]
                    for item in state.records
                )
            finally:
                terminate_and_reap(process)
    finally:
        stop_http_server(server, thread)


def test_direct_mcp_child_process_stdio_and_jsonrpc_correlation() -> None:
    with tempfile.TemporaryDirectory(prefix="aicp-direct-mcp-") as directory_name:
        directory = Path(directory_name)
        ready = directory / "ready.json"
        values = {
            "AICP_LIVE_RUN_ID": "direct-mcp",
            "AICP_LIVE_BINDING_ID": "BIND-MCP",
            "AICP_LIVE_BINDING_VERSION": "0.1",
            "AICP_LIVE_ROLE": "server_under_test",
            "AICP_LIVE_READY_FILE": str(ready),
            "AICP_LIVE_SCENARIO_FILE": str(directory / "scenario.json"),
            "AICP_LIVE_TEST_BEARER": "",
        }
        process, _collector, stderr = spawn_process(
            _command("mcp", "server_under_test", "external_implementation"),
            environment=explicit_environment(values),
            root=ROOT,
            stdout_transport=True,
        )
        assert process.pid != os.getpid()
        deadline = time.monotonic() + 5
        try:
            wait_ready_descriptor(process, ready, deadline=deadline)
            interactions = execute_mcp_server(
                process,
                role="server_under_test",
                deadline=deadline,
            )
            assert all(
                item["transport_evidence"]["boundary"]["kind"]
                == "child_process_stdio"
                for item in interactions
            )
            assert all(
                exchange["request"]["id"] == exchange["response"]["id"]
                for item in interactions
                for exchange in item["transport_evidence"]["exchanges"]
            )
        finally:
            terminate_and_reap(process)
            stderr.finish()


def test_ready_descriptor_retries_transient_windows_read_denial(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    ready = tmp_path / "ready.json"
    ready.write_text('{"transport":"stdio"}', encoding="utf-8")
    original_read_bytes = Path.read_bytes
    attempts = 0

    def transient_read_denial(path: Path) -> bytes:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise PermissionError("transient sharing violation")
        return original_read_bytes(path)

    class RunningProcess:
        @staticmethod
        def poll() -> None:
            return None

    monkeypatch.setattr(Path, "read_bytes", transient_read_denial)
    assert wait_ready_descriptor(
        RunningProcess(),  # type: ignore[arg-type]
        ready,
        deadline=time.monotonic() + 1,
    ) == {"transport": "stdio"}
    assert attempts == 2


def test_loopback_policy_and_subprocess_argument_vector_are_load_bearing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import live_binding_process as process_module

    for value in (
        "http://localhost:8000",
        "http://example.test:8000",
        "http://192.0.2.1:8000",
        "http://127.0.0.1:8000/path",
    ):
        with pytest.raises(Exception):
            validate_loopback_url(value)
    assert validate_loopback_url("http://127.0.0.1:8000") == "http://127.0.0.1:8000"

    captured: dict[str, object] = {}

    class FakeProcess:
        def __init__(self) -> None:
            self.stdout = BytesIO()
            self.stderr = BytesIO()
            self.stdin = BytesIO()
            self.returncode = 0

        def poll(self) -> int:
            return 0

        def wait(self, timeout: float | None = None) -> int:
            return 0

    def fake_popen(command: list[str], **kwargs: object) -> FakeProcess:
        captured["command"] = command
        captured["shell"] = kwargs.get("shell")
        return FakeProcess()

    monkeypatch.setattr(process_module.subprocess, "Popen", fake_popen)
    command = ["implementation", "argument;must-not-run"]
    process, stdout, stderr = process_module.spawn_process(
        command,
        environment={},
        root=ROOT,
    )
    assert captured == {"command": command, "shell": False}
    assert stdout is not None
    stdout.finish()
    stderr.finish()
    assert process.poll() == 0


def _binding_manifest(binding: str, report_name: str) -> dict:
    binding_id = "BIND-HTTP" if binding == "http" else "BIND-MCP"
    suite_id = "TB-HTTP-0.1" if binding == "http" else "TB-MCP-0.1"
    implementation_id = f"aicp-{binding}-external-test"
    return {
        "submission_id": f"example-{binding}-binding",
        "implementation_id": implementation_id,
        "implementation_version": "1.0.0-test",
        "binding_refs": [
            {"binding_id": binding_id, "binding_version": "0.1"}
        ],
        "evidence_types": ["binding_report"],
        "evidence_status": "reproducible",
        "report_refs": [report_name],
        "suite_refs": [suite_id],
        "claim_type": "implements_binding",
        "claim_scope": "self_attested",
        "generated_at": "2026-08-21T00:00:00Z",
        "disclosures": ["Test-only package."],
    }


@pytest.mark.parametrize("binding", ["http", "mcp"])
def test_public_binding_claim_is_exact_and_typed(
    tmp_path: Path, external_reports: dict[str, dict], binding: str
) -> None:
    report_path = tmp_path / f"{binding}.json"
    report_path.write_text(json.dumps(external_reports[binding]), encoding="utf-8")
    manifest = _binding_manifest(binding, report_path.name)
    evaluation = evaluate_strong_report_evidence(tmp_path / "submission.json", manifest)
    assert evaluation.status == "eligible"
    assert evaluation.eligible_profile_marks == ()
    assert evaluation.eligible_capability_marks == ()
    assert evaluation.eligible_binding_marks == (
        "AICP-BIND-HTTP-0.1" if binding == "http" else "AICP-BIND-MCP-0.1",
    )
    wrong_suite = copy.deepcopy(manifest)
    wrong_suite["suite_refs"] = [
        "TB-MCP-0.1" if binding == "http" else "TB-HTTP-0.1"
    ]
    assert evaluate_strong_report_evidence(
        tmp_path / "submission.json", wrong_suite
    ).status == "rejected"


@pytest.mark.parametrize("binding", ["http", "mcp"])
def test_matrix_promotes_only_the_typed_binding_mark(
    tmp_path: Path, external_reports: dict[str, dict], binding: str
) -> None:
    report_name = f"{binding}.json"
    (tmp_path / report_name).write_text(
        json.dumps(external_reports[binding]), encoding="utf-8"
    )
    manifest = _binding_manifest(binding, report_name)
    (tmp_path / "submission.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )

    entry = _manifest_entry(tmp_path)

    expected_mark = (
        "AICP-BIND-HTTP-0.1" if binding == "http" else "AICP-BIND-MCP-0.1"
    )
    assert entry["evidence_validation_status"] == "eligible"
    assert entry["computed_binding_marks"] == [expected_mark]
    assert entry["computed_profile_marks"] == []
    assert entry["computed_capability_marks"] == []


def test_reference_report_cannot_support_public_binding_claim(tmp_path: Path) -> None:
    report = _run("http", kind="reference_corpus")
    report_path = tmp_path / "reference.json"
    report_path.write_text(json.dumps(report), encoding="utf-8")
    manifest = _binding_manifest("http", report_path.name)
    assert evaluate_strong_report_evidence(
        tmp_path / "submission.json", manifest
    ).status == "rejected"


def test_multiple_binding_refs_require_separate_eligible_reports(tmp_path: Path) -> None:
    implementation_id = "aicp-multi-binding-external-test"
    http = _run("http", implementation_id=implementation_id)
    mcp = _run("mcp", implementation_id=implementation_id)
    (tmp_path / "http.json").write_text(json.dumps(http), encoding="utf-8")
    (tmp_path / "mcp.json").write_text(json.dumps(mcp), encoding="utf-8")
    manifest = {
        **_binding_manifest("http", "http.json"),
        "implementation_id": implementation_id,
        "binding_refs": [
            {"binding_id": "BIND-HTTP", "binding_version": "0.1"},
            {"binding_id": "BIND-MCP", "binding_version": "0.1"},
        ],
        "report_refs": ["http.json", "mcp.json"],
        "suite_refs": ["TB-HTTP-0.1", "TB-MCP-0.1"],
    }
    evaluation = evaluate_strong_report_evidence(tmp_path / "submission.json", manifest)
    assert evaluation.status == "eligible"
    assert evaluation.eligible_binding_marks == (
        "AICP-BIND-HTTP-0.1",
        "AICP-BIND-MCP-0.1",
    )

    missing = copy.deepcopy(manifest)
    missing["report_refs"] = ["http.json"]
    assert evaluate_strong_report_evidence(
        tmp_path / "submission.json", missing
    ).status == "rejected"

    mixed = copy.deepcopy(manifest)
    mixed["profile_ids"] = ["AICP-BASE@0.1"]
    assert evaluate_strong_report_evidence(
        tmp_path / "submission.json", mixed
    ).status == "rejected"


def test_missing_jsonschema_fails_live_catalog_closed() -> None:
    record = resolve_target_record("BIND-HTTP@0.1")
    handler = resolve_handler(record.handler_id)
    errors = handler.validate_catalog(
        target_catalog(record), simulate_no_jsonschema=True
    )
    assert "jsonschema is required to validate live binding scenarios" in errors


def test_mcp_static_suite_covers_all_four_minimum_tools() -> None:
    suite = json.loads(
        (ROOT / "conformance/bindings/TB_MCP_0.1.json").read_text(encoding="utf-8")
    )
    fixtures = [json.loads((ROOT / path).read_text(encoding="utf-8")) for path in suite["cases"]]
    assert {item["mcp_request"]["params"]["name"] for item in fixtures} == {
        "aicp.sendMessage",
        "aicp.pollMessages",
        "aicp.getHead",
        "aicp.getObject",
    }
