from __future__ import annotations

import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
RUNNER_PATH = ROOT / "conformance/runner/aicp_conformance_runner.py"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_display_path_handles_external_paths() -> None:
    runner = _load_module(RUNNER_PATH, "aicp_conformance_runner_outpath_test")
    external = Path("/tmp/some-report.json")
    shown = runner._display_path(external)
    assert shown == str(external)
