#!/usr/bin/env python3
"""Exercise the repository-owned Python/Node peers through Pairwise TCK 1.2."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(command: list[str]) -> None:
    result = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, shell=False, timeout=120)
    if result.returncode != 0:
        raise RuntimeError(result.stdout + result.stderr)
    if result.stdout.strip():
        print(result.stdout.strip())


def command_json(command: list[str]) -> str:
    return json.dumps(command)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--side-only", action="store_true")
    parser.add_argument("--output-dir", help="retain the exact five reports in this directory")
    args = parser.parse_args()
    node = shutil.which("node")
    if node is None:
        raise RuntimeError("Node.js is required for clean-room peer B")
    peer_a = ROOT / "interop" / "pairwise" / "cleanroom" / "peer_a" / "peer_a.py"
    peer_b = ROOT / "interop" / "pairwise" / "cleanroom" / "peer_b" / "peer_b.mjs"
    run([sys.executable, str(peer_a), "self-test"])
    run([node, str(peer_b), "self-test"])
    temporary_context = None
    if args.output_dir:
        output = Path(args.output_dir).resolve()
        output.mkdir(parents=True, exist_ok=True)
    else:
        temporary_context = tempfile.TemporaryDirectory(prefix="aicp-pairwise-")
        output = Path(temporary_context.name)
    try:
        reports = {
            "a_profile": output / "a-profile.json",
            "a_binding": output / "a-binding.json",
            "b_profile": output / "b-profile.json",
            "b_binding": output / "b-binding.json",
            "joint": output / "joint.json",
        }
        for side, command in (("a", [sys.executable, str(peer_a)]), ("b", [node, str(peer_b)])):
            run([
                sys.executable, "conformance/iut/aicp_iut_runner.py", "--cmd-json", command_json([*command, "iut"]),
                "--profile", "AICP-BASE@0.1", "--mode", "full-profile", "--out", str(reports[f"{side}_profile"]),
            ])
            run([
                sys.executable, "conformance/evidence/aicp_live_binding_runner.py", "--target", "BIND-MCP@0.1",
                "--server-cmd-json", command_json([*command, "binding-server"]),
                "--client-cmd-json", command_json([*command, "binding-client"]),
                "--mode", "full-binding", "--out", str(reports[f"{side}_binding"]),
            ])
        if args.side_only:
            print("Clean-room side evidence passed: 2 full-profile + 2 full-binding reports")
            return 0
        run([
            sys.executable, "interop/pairwise/aicp_pairwise_runner_v1_2.py",
            "--peer-a-client-cmd-json", command_json([sys.executable, str(peer_a), "pairwise-client"]),
            "--peer-a-server-cmd-json", command_json([sys.executable, str(peer_a), "pairwise-server"]),
            "--peer-a-profile-report", str(reports["a_profile"]), "--peer-a-binding-report", str(reports["a_binding"]),
            "--peer-b-client-cmd-json", command_json([node, str(peer_b), "pairwise-client"]),
            "--peer-b-server-cmd-json", command_json([node, str(peer_b), "pairwise-server"]),
            "--peer-b-profile-report", str(reports["b_profile"]), "--peer-b-binding-report", str(reports["b_binding"]),
            "--out", str(reports["joint"]),
        ])
        run([sys.executable, "interop/pairwise/pairwise_report_dispatcher.py", str(reports["joint"])])
    finally:
        if temporary_context is not None:
            temporary_context.cleanup()
    if args.output_dir:
        print(f"Clean-room pairwise external-kind test passed; exact evidence retained at {output}")
    else:
        print("Clean-room pairwise external-kind test passed; temporary evidence removed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
