from __future__ import annotations

import py_compile
from pathlib import Path


def test_snapshot_validator_compiles() -> None:
    path = Path(__file__).resolve().parents[3] / "scripts/validate_snapshot_manifest.py"
    py_compile.compile(str(path), doraise=True)
