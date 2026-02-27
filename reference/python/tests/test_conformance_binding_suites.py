from __future__ import annotations

import importlib.util
import subprocess
import sys
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUNNER = ROOT / "conformance/runner/aicp_conformance_runner.py"


def _load_runner_module():
    spec = importlib.util.spec_from_file_location("aicp_conformance_runner", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_binding_conformance_suite_passes() -> None:
    report = "conformance/report_bind_mcp_test.json"
    cmd = [
        sys.executable,
        str(RUNNER),
        "--suite",
        "conformance/bindings/TB_MCP_0.1.json",
        "--out",
        report,
    ]
    result = subprocess.run(cmd, cwd=ROOT, check=False)
    try:
        assert result.returncode == 0
    finally:
        (ROOT / report).unlink(missing_ok=True)


def test_binding_suite_does_not_use_network_for_schema_resolution(monkeypatch) -> None:
    runner = _load_runner_module()
    called: list[str] = []

    def _blocked_urlopen(*args, **kwargs):
        called.append(str(args[0]) if args else "")
        raise AssertionError("urlopen must not be called during schema validation")

    monkeypatch.setattr(urllib.request, "urlopen", _blocked_urlopen)

    report = runner.run_suite(ROOT / "conformance/bindings/TB_MCP_0.1.json")
    assert report["passed"] is True
    assert called == []
