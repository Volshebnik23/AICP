from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "demos/enforcement_behavioral/scripts/run_demo.py"


def test_behavioral_demo_generates_history_run(tmp_path: Path) -> None:
    out_root = tmp_path / "demo"
    (out_root / "rules").mkdir(parents=True)
    (out_root / "rules/CHAT_RULES.md").write_text("# rules\n", encoding="utf-8")
    (out_root / "PERSONA_VALUE_FEATURE_TEST.md").write_text("# mapping\n", encoding="utf-8")

    cmd = [sys.executable, str(SCRIPT), "--out-root", str(out_root)]
    result = subprocess.run(cmd, cwd=ROOT, check=False, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr

    run_dir = out_root / "history/run_0001"
    assert run_dir.exists()

    expected = [
        run_dir / "transcripts/01_happy_path.jsonl",
        run_dir / "transcripts/02_policy_violation_matrix.jsonl",
        run_dir / "transcripts/03_escalation_kick_and_resume.jsonl",
        run_dir / "transcripts/04_inconclusive_escalate.jsonl",
        run_dir / "transcripts/05_resume_needs_resync.jsonl",
        run_dir / "transcripts/06_malicious_mediator_delivers_after_deny_expected_fail.jsonl",
        run_dir / "transcripts/07_spoofed_verdict_sender_expected_fail.jsonl",
        run_dir / "transcripts/08_duplicate_message_id_replay_expected_fail.jsonl",
    ]

    for path in expected:
        assert path.exists(), f"missing transcript: {path}"
        lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        assert lines, f"empty transcript: {path}"
        json.loads(lines[0])

    results_md = out_root / "results/RESULTS.md"
    assert results_md.exists()
    assert "history/run_0001" in results_md.read_text(encoding="utf-8")
