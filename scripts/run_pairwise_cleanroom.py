#!/usr/bin/env python3
"""Exercise the repository-owned Python/Node peers through Pairwise TCK 1.3."""

from __future__ import annotations

import argparse
import hashlib
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
    parser.add_argument("--vector-manifest", action="store_true", help="write the repository vector manifest")
    args = parser.parse_args()
    node = shutil.which("node")
    if node is None:
        raise RuntimeError("Node.js is required for clean-room peer B")
    peer_a = ROOT / "interop" / "pairwise" / "cleanroom" / "peer_a" / "peer_a_v1_3.py"
    peer_b = ROOT / "interop" / "pairwise" / "cleanroom" / "peer_b" / "peer_b_v1_3.mjs"
    frozen_vector = (
        ROOT
        / "interop"
        / "pairwise"
        / "current_vectors"
        / "AICP-PAIRWISE-TCK-1.3.0"
    )
    run([sys.executable, str(peer_a), "self-test"])
    run([node, str(peer_b), "self-test"])
    run(
        [
            sys.executable,
            "interop/pairwise/pairwise_release_router.py",
            str(frozen_vector / "joint.json"),
        ]
    )
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
        for side in ("a", "b"):
            for kind in ("profile", "binding"):
                shutil.copy2(
                    frozen_vector / f"{side}-{kind}.json",
                    reports[f"{side}_{kind}"],
                )
        if args.side_only:
            print(
                "Frozen Pairwise 1.3 side authority passed: "
                "2 full-profile + 2 full-binding reports"
            )
            return 0
        run([
            sys.executable, "interop/pairwise/aicp_pairwise_runner_v1_3.py",
            "--peer-a-client-cmd-json", command_json([sys.executable, str(peer_a), "pairwise-client"]),
            "--peer-a-server-cmd-json", command_json([sys.executable, str(peer_a), "pairwise-server"]),
            "--peer-a-profile-report", str(reports["a_profile"]), "--peer-a-binding-report", str(reports["a_binding"]),
            "--peer-b-client-cmd-json", command_json([node, str(peer_b), "pairwise-client"]),
            "--peer-b-server-cmd-json", command_json([node, str(peer_b), "pairwise-server"]),
            "--peer-b-profile-report", str(reports["b_profile"]), "--peer-b-binding-report", str(reports["b_binding"]),
            "--out", str(reports["joint"]),
        ])
        run([sys.executable, "interop/pairwise/pairwise_release_router.py", str(reports["joint"])])
        if args.vector_manifest:
            files = []
            for name in sorted(path.name for path in reports.values()):
                content = (output / name).read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
                files.append(
                    {
                        "path": name,
                        "sha256": hashlib.sha256(content).hexdigest(),
                    }
                )
            manifest = {
                "vector_format_version": "1.0",
                "pairwise_tck_release": "AICP-PAIRWISE-TCK-1.3.0",
                "classification": "repository-owned-current-clean-room-test-vector",
                "files": files,
                "notes": [
                    "Generated with Pairwise TCK 1.3 from the repository-owned Python and Node clean-room peers.",
                    "Raw per-run roles, run-global causality, and exact continuation cursors are independently evaluated.",
                    "This vector is reproducible test evidence, not genuine external adoption.",
                ],
            }
            (output / "manifest.json").write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
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
