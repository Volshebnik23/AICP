from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


def test_validate_dropins_assets_passes() -> None:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts/validate_dropins_assets.py")],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
