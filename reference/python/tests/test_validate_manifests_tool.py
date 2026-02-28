from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
TOOL = ROOT / "interop/tools/validate_manifests.py"
SCHEMA = ROOT / "interop/schemas/implementation_manifest.schema.json"


def _run(paths: list[Path]) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(TOOL), "--schema", str(SCHEMA)] + [str(p) for p in paths]
    return subprocess.run(cmd, cwd=ROOT, check=False, capture_output=True, text=True)


def test_validate_manifests_tool_valid_and_invalid(tmp_path: Path) -> None:
    valid = tmp_path / "valid.json"
    invalid = tmp_path / "invalid.json"

    valid.write_text(
        json.dumps(
            {
                "implementation_id": "impl-one",
                "name": "Implementation One",
                "language": "python",
                "version": "0.1.0",
                "maintainer": "Maintainer One",
                "contact": "@impl-one",
            }
        ),
        encoding="utf-8",
    )
    invalid.write_text(json.dumps({"implementation_id": "impl-two"}), encoding="utf-8")

    result = _run([valid, invalid])
    assert result.returncode == 1
    assert f"[OK] {valid}" in result.stdout
    assert f"[FAIL] {invalid}" in result.stdout


def test_validate_manifests_tool_no_files(tmp_path: Path) -> None:
    result = _run([])
    assert result.returncode == 0
    assert "No manifest files provided; skipping." in result.stdout
