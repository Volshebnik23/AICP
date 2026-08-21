from __future__ import annotations

import copy
import json
import os
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
for path in (EVIDENCE_DIR, LIVE_DIR, SCRIPTS_DIR, INTEROP_TOOLS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from aicp_live_binding_runner import run_live_binding_evidence  # noqa: E402
from interop_submission_validation import (  # noqa: E402
    evaluate_strong_report_evidence,
)
from interop_matrix import _manifest_entry  # noqa: E402
from live_binding_process import (  # noqa: E402
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
from live_http_transport import (  # noqa: E402
    execute_http_client,
    start_http_server,
    stop_http_server,
)
from live_mcp_transport import execute_mcp_server  # noqa: E402
from report_evaluator import evaluate_report  # noqa: E402
from target_catalog import (  # noqa: E402
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
    TCK_1_4_RELEASE_ID,
    canonical_digest as target_canonical_digest,
    file_digest,
    release_policy,
    release_record,
    release_snapshot_digest,
    resolve_target_record,
    target_catalog,
    validate_release_registry,
    validate_target_catalog,
    validate_target_registry,
)
from target_handlers import resolve_handler  # noqa: E402


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


def test_exact_binding_targets_and_tck_15_registry() -> None:
    assert BINDING_TARGET_KEYS == ("BIND-HTTP@0.1", "BIND-MCP@0.1")
    assert CURRENT_TCK_RELEASE_ID == "AICP-EVIDENCE-TCK-1.5.0"
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


HTTP_MUTATIONS = [
    ("LIVE-HTTP-SERVER-AUTH", "auth_rejected", False),
    ("LIVE-HTTP-SERVER-SESSION", "session_distinct", False),
    ("LIVE-HTTP-SERVER-INGEST", "message_digest_equal", False),
    ("LIVE-HTTP-SERVER-REPLAY", "duplicate_count", 1),
    ("LIVE-HTTP-SERVER-REPLAY-SCOPE", "replay_scope_isolated", False),
    ("LIVE-HTTP-SERVER-POLL", "no_cross_session_leakage", False),
    ("LIVE-HTTP-SERVER-HEAD", "head_session_match", False),
    ("LIVE-HTTP-SERVER-ACK", "ack_matches", False),
    ("LIVE-HTTP-SERVER-REPLAY-WINDOW", "status", 200),
    ("LIVE-HTTP-SERVER-ORDERING", "ordered_chain_valid", False),
    ("LIVE-HTTP-SERVER-OVERLOAD", "retry_after_present", False),
    ("LIVE-HTTP-SERVER-SSE", "event_ids_match_cursors", False),
    ("LIVE-HTTP-SERVER-SSE-RECONNECT", "reconnect_stable", False),
    ("LIVE-HTTP-SERVER-WEBSOCKET", "cursor_relationship_valid", False),
    ("LIVE-HTTP-SERVER-CLOSE", "closed_session_rejected", False),
]


@pytest.mark.parametrize(("scenario_id", "fact", "value"), HTTP_MUTATIONS)
def test_each_http_evaluator_family_is_load_bearing(
    external_reports: dict[str, dict], scenario_id: str, fact: str, value: object
) -> None:
    report = copy.deepcopy(external_reports["http"])
    _set_fact(report, scenario_id, fact, value)
    assert evaluate_report(report)["status"] == "rejected"


@pytest.mark.parametrize(
    ("scenario_id", "fact", "value"),
    [
        ("LIVE-MCP-SERVER-SEND", "message_digest_equal", False),
        ("LIVE-MCP-SERVER-DUPLICATE", "duplicate_hash_stable", False),
        ("LIVE-MCP-SERVER-POLL", "poll_limit_respected", False),
        ("LIVE-MCP-SERVER-HEAD", "head_session_match", False),
        ("LIVE-MCP-SERVER-OBJECT", "object_hash_recomputed", False),
        ("LIVE-MCP-SERVER-INTEGRITY", "request_response_correlated", False),
    ],
)
def test_each_mcp_evaluator_family_is_load_bearing(
    external_reports: dict[str, dict], scenario_id: str, fact: str, value: object
) -> None:
    report = copy.deepcopy(external_reports["mcp"])
    _set_fact(report, scenario_id, fact, value)
    assert evaluate_report(report)["status"] == "rejected"


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

    schema = json.loads((LIVE_DIR / "live_binding_trace.schema.json").read_text(encoding="utf-8"))
    artifact = copy.deepcopy(external_reports["http"]["generated_artifacts"][0])
    artifact["content"]["runs"][0]["interactions"][0]["observations"].append(
        {"name": "authorization", "value": "Bearer forbidden"}
    )
    assert list(Draft202012Validator(schema).iter_errors(artifact))


def test_semantic_normalization_allows_opaque_spelling_and_order_only(
    external_reports: dict[str, dict]
) -> None:
    report = copy.deepcopy(external_reports["http"])
    artifact = report["generated_artifacts"][0]
    first, second = artifact["content"]["runs"]
    second["interactions"].reverse()
    mappings: dict[str, dict[str, str]] = {
        "session": {},
        "cursor": {},
        "request": {},
    }
    session_names = {"session_id", "second_session_id"}
    cursor_names = {
        "poll_after",
        "next_cursor",
        "cursor_after_last",
        "ack_cursor",
        "expired_cursor",
        "min_cursor",
        "last_event_id",
    }
    request_names = {"request_id", "response_id"}
    for interaction in second["interactions"]:
        for fact in interaction["observations"]:
            name = fact["name"]
            value = fact["value"]
            group = (
                "session"
                if name in session_names
                else "cursor"
                if name in cursor_names
                else "request"
                if name in request_names
                else None
            )
            if group is not None and isinstance(value, str) and value:
                mapping = mappings[group]
                mapping.setdefault(value, f"opaque-{group}-{len(mapping) + 1}")
                fact["value"] = mapping[value]
    _recompute_trace(report)
    assert semantic_digest(first) == semantic_digest(second)
    assert evaluate_report(report)["status"] == "eligible"

    broken = copy.deepcopy(report)
    interaction = next(
        item
        for item in broken["generated_artifacts"][0]["content"]["runs"][1]["interactions"]
        if item["scenario_id"] == "LIVE-HTTP-SERVER-ACK"
    )
    next(
        item for item in interaction["observations"] if item["name"] == "ack_cursor"
    )["value"] = "relationship-broken"
    _recompute_trace(broken)
    assert evaluate_report(broken)["status"] == "rejected"

    message_changed = copy.deepcopy(report)
    interaction = next(
        item
        for item in message_changed["generated_artifacts"][0]["content"]["runs"][1]["interactions"]
        if item["scenario_id"] == "LIVE-HTTP-SERVER-INGEST"
    )
    next(
        item
        for item in interaction["observations"]
        if item["name"] == "observed_message_hash"
    )["value"] = "sha256:" + "0" * 64
    _recompute_trace(message_changed)
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
    assert "authorization" not in encoded.lower()


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
            observation_map(item)["network_boundary"] == "loopback_socket"
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
                _command("http", "client_under_test", "external_implementation"),
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
            assert all(observation_map(item)["process_boundary"] is True for item in interactions)
            assert all(
                observation_map(item)["request_id"]
                == observation_map(item)["response_id"]
                for item in interactions
            )
        finally:
            terminate_and_reap(process)
            stderr.finish()


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
