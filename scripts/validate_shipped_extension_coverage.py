#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
ROADMAP = ROOT / "ROADMAP.md"
MAKEFILE = ROOT / "Makefile"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _has_shipped_milestone(roadmap_text: str, milestone: str) -> bool:
    return f"### ✅ {milestone}" in roadmap_text


def main() -> int:
    roadmap = _read(ROADMAP)
    makefile = _read(MAKEFILE)

    failures: list[str] = []

    if _has_shipped_milestone(roadmap, "M23"):
        if "conformance/extensions/CF_CONFIDENTIALITY_0.1.json" not in makefile:
            failures.append("ROADMAP marks M23 shipped, but Makefile conformance-ext does not include CF_CONFIDENTIALITY_0.1")

    if _has_shipped_milestone(roadmap, "M24"):
        if "conformance/extensions/RD_REDACTION_0.1.json" not in makefile:
            failures.append("ROADMAP marks M24 shipped, but Makefile conformance-ext does not include RD_REDACTION_0.1")

    if _has_shipped_milestone(roadmap, "M26"):
        if "conformance/extensions/HA_HUMAN_APPROVAL_0.1.json" not in makefile:
            failures.append("ROADMAP marks M26 shipped, but Makefile conformance-ext does not include HA_HUMAN_APPROVAL_0.1")

    if _has_shipped_milestone(roadmap, "M28"):
        if "conformance/extensions/IB_IAM_BRIDGE_0.1.json" not in makefile:
            failures.append("ROADMAP marks M28 shipped, but Makefile conformance-ext does not include IB_IAM_BRIDGE_0.1")

    if failures:
        for item in failures:
            print(f"[FAIL] {item}")
        print("Fix roadmap/Makefile mismatch before claiming shipped milestone coverage.")
        return 1

    print("OK: shipped milestone claims align with conformance-ext suite coverage in Makefile.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
