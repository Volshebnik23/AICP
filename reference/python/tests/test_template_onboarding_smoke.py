from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SANDBOX = ROOT / "sandbox/run.py"


def test_protocol_adapter_template_smoke() -> None:
    transcript = ROOT / "fixtures/golden_transcripts/GT-01_happy_path_signed.jsonl"
    run = subprocess.run(
        [sys.executable, str(ROOT / "templates/protocol-adapter/adapter.py"), str(transcript)],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert run.returncode == 0, run.stdout + run.stderr
    mapped = json.loads(run.stdout)
    assert mapped and isinstance(mapped, list)
    first = mapped[0]
    assert "audit_envelope" in first
    assert "signatures" in first


def test_ts_agent_template_smoke(tmp_path: Path) -> None:
    node = shutil.which("node")
    if node is None:
        return

    out = tmp_path / "template-thread.jsonl"
    gen = subprocess.run(
        [node, str(ROOT / "templates/ts-agent/agent.js")],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert gen.returncode == 0, gen.stdout + gen.stderr
    out.write_text(gen.stdout, encoding="utf-8")

    verify = subprocess.run(
        [sys.executable, str(SANDBOX), str(out), "--no-signature-verify"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert verify.returncode == 0, verify.stdout + verify.stderr
    assert "PASSED" in verify.stdout
