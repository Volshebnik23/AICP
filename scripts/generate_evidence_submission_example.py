#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE_DIR = ROOT / "conformance" / "evidence"
SCRIPTS_DIR = ROOT / "scripts"
for path in (EVIDENCE_DIR, SCRIPTS_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from interop_submission_validation import (  # noqa: E402
    build_integrity_manifest,
    manifest_tracked_paths,
)


EXAMPLE_DIR = (
    ROOT / "interop" / "submissions" / "examples" / "capability_claim"
)
REPORT_REF = "reports/report_capability_projection_v1.json"
TIMESTAMP = "2026-07-30T00:00:00Z"
FROZEN_REPORT_SHA256 = (
    "0f6987c223bb6ee962a6668ede5b0fc719019174160361a478631638969da695"
)


def render(value: Any) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False) + "\n"


def example_manifest() -> dict[str, Any]:
    return {
        "submission_id": "example-capability-claim",
        "implementation_id": "example-projection-v1-implementation",
        "implementation_version": "1.0.0-example",
        "capability_refs": [
            {
                "capability_id": "aicp.session_state_projection",
                "capability_version": "v1",
            }
        ],
        "evidence_types": ["capability_report"],
        "evidence_status": "example",
        "report_refs": [REPORT_REF],
        "suite_refs": ["OR-SESSION-STATE-PROJECTION-V1"],
        "claim_type": "implements_capability",
        "claim_scope": "self_attested",
        "generated_at": TIMESTAMP,
        "notes": (
            "Fictional instructional package for the M62 capability claim format."
        ),
        "disclosures": [
            "Example artifact only; not a real external implementation submission.",
            "The external-kind adapter is a repository test double and is not counted as independent evidence.",
        ],
    }


def generated_files() -> dict[str, str]:
    frozen_report_path = EXAMPLE_DIR / REPORT_REF
    report_text = frozen_report_path.read_text(encoding="utf-8")
    normalized = report_text.replace("\r\n", "\n").replace("\r", "\n")
    if hashlib.sha256(normalized.encode("utf-8")).hexdigest() != FROZEN_REPORT_SHA256:
        raise ValueError("frozen pre-M63 projection report bytes changed")
    manifest = example_manifest()
    with tempfile.TemporaryDirectory(prefix="aicp-evidence-example-") as raw:
        package = Path(raw)
        report_path = package / REPORT_REF
        report_path.parent.mkdir(parents=True)
        (package / "submission.json").write_text(
            render(manifest),
            encoding="utf-8",
        )
        report_path.write_text(report_text, encoding="utf-8")
        integrity = build_integrity_manifest(
            package,
            manifest["submission_id"],
            manifest_tracked_paths(manifest),
            generated_at=TIMESTAMP,
        )
    return {
        "submission.json": render(manifest),
        REPORT_REF: report_text,
        "bundle-integrity.json": render(integrity),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    args = parser.parse_args()
    generated = generated_files()
    if args.write:
        for relative, content in generated.items():
            path = EXAMPLE_DIR / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
        print(
            "Generated fictional projection-v1 capability submission example."
        )
        return 0
    stale = [
        relative
        for relative, content in generated.items()
        if not (EXAMPLE_DIR / relative).is_file()
        or (EXAMPLE_DIR / relative).read_text(encoding="utf-8") != content
    ]
    if stale:
        print("[FAIL] stale capability example files: " + ", ".join(stale))
        return 1
    print("OK: fictional projection-v1 capability example is current.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
