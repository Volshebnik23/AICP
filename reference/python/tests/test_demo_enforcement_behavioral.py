from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "demos/enforcement_behavioral/scripts/run_demo.py"


def test_behavioral_demo_generates_transcripts(tmp_path: Path) -> None:
    out_root = tmp_path / "demo"
    cmd = [sys.executable, str(SCRIPT), "--out-root", str(out_root)]
    result = subprocess.run(cmd, cwd=ROOT, check=False, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr

    expected = [
        out_root / "transcripts/01_happy_path.jsonl",
        out_root / "transcripts/02_policy_violation_matrix.jsonl",
        out_root / "transcripts/03_escalation_kick_and_resume.jsonl",
    ]

    for path in expected:
        assert path.exists(), f"missing transcript: {path}"
        lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        assert lines, f"empty transcript: {path}"
        json.loads(lines[0])

    results_md = out_root / "results/RESULTS.md"
    assert results_md.exists()
    assert "04_protocol_misuse_expected_fail" in results_md.read_text(encoding="utf-8")
