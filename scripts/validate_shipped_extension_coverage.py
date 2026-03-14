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

    if _has_shipped_milestone(roadmap, "M27"):
        if "conformance/extensions/OB_OBSERVABILITY_0.1.json" not in makefile:
            failures.append("ROADMAP marks M27 shipped, but Makefile conformance-ext does not include OB_OBSERVABILITY_0.1")
        if not (ROOT / "docs/extensions/RFC_EXT_OBSERVABILITY.md").exists():
            failures.append("ROADMAP marks M27 shipped, but docs/extensions/RFC_EXT_OBSERVABILITY.md is missing")
        if not (ROOT / "schemas/extensions/ext-observability-payloads.schema.json").exists():
            failures.append("ROADMAP marks M27 shipped, but schemas/extensions/ext-observability-payloads.schema.json is missing")
        if not (ROOT / "conformance/extensions/OB_OBSERVABILITY_0.1.json").exists():
            failures.append("ROADMAP marks M27 shipped, but conformance/extensions/OB_OBSERVABILITY_0.1.json is missing")
        if not (ROOT / "scripts/generate_observability_fixtures.py").exists() and not any((ROOT / "fixtures/extensions/observability").glob("*.jsonl")):
            failures.append("ROADMAP marks M27 shipped, but no fixture generator or deterministic fixtures for observability are present")

    if _has_shipped_milestone(roadmap, "M29"):
        if "conformance/extensions/EB_ENTERPRISE_BINDINGS_0.1.json" not in makefile:
            failures.append("ROADMAP marks M29 shipped, but Makefile conformance-ext does not include EB_ENTERPRISE_BINDINGS_0.1")
        if not (ROOT / "docs/extensions/RFC_EXT_ENTERPRISE_BINDINGS.md").exists():
            failures.append("ROADMAP marks M29 shipped, but docs/extensions/RFC_EXT_ENTERPRISE_BINDINGS.md is missing")
        if not (ROOT / "schemas/extensions/ext-enterprise-bindings-payloads.schema.json").exists():
            failures.append("ROADMAP marks M29 shipped, but schemas/extensions/ext-enterprise-bindings-payloads.schema.json is missing")
        if not (ROOT / "conformance/extensions/EB_ENTERPRISE_BINDINGS_0.1.json").exists():
            failures.append("ROADMAP marks M29 shipped, but conformance/extensions/EB_ENTERPRISE_BINDINGS_0.1.json is missing")
        if not (ROOT / "scripts/generate_enterprise_bindings_fixtures.py").exists() and not any((ROOT / "fixtures/extensions/enterprise_bindings").glob("*.jsonl")):
            failures.append("ROADMAP marks M29 shipped, but no fixture generator or deterministic fixtures for enterprise bindings are present")


    if _has_shipped_milestone(roadmap, "M35"):
        if "conformance/extensions/AD_ADMISSION_0.1.json" not in makefile:
            failures.append("ROADMAP marks M35 shipped, but Makefile conformance-ext does not include AD_ADMISSION_0.1")
        if "conformance/extensions/QL_QUEUE_LEASES_0.1.json" not in makefile:
            failures.append("ROADMAP marks M35 shipped, but Makefile conformance-ext does not include QL_QUEUE_LEASES_0.1")
        if not (ROOT / "docs/extensions/RFC_EXT_ADMISSION.md").exists():
            failures.append("ROADMAP marks M35 shipped, but docs/extensions/RFC_EXT_ADMISSION.md is missing")
        if not (ROOT / "docs/extensions/RFC_EXT_QUEUE_LEASES.md").exists():
            failures.append("ROADMAP marks M35 shipped, but docs/extensions/RFC_EXT_QUEUE_LEASES.md is missing")
        if not (ROOT / "schemas/extensions/ext-admission-payloads.schema.json").exists():
            failures.append("ROADMAP marks M35 shipped, but schemas/extensions/ext-admission-payloads.schema.json is missing")
        if not (ROOT / "schemas/extensions/ext-queue-leases-payloads.schema.json").exists():
            failures.append("ROADMAP marks M35 shipped, but schemas/extensions/ext-queue-leases-payloads.schema.json is missing")
        if not (ROOT / "conformance/extensions/AD_ADMISSION_0.1.json").exists():
            failures.append("ROADMAP marks M35 shipped, but conformance/extensions/AD_ADMISSION_0.1.json is missing")
        if not (ROOT / "conformance/extensions/QL_QUEUE_LEASES_0.1.json").exists():
            failures.append("ROADMAP marks M35 shipped, but conformance/extensions/QL_QUEUE_LEASES_0.1.json is missing")
        if not (ROOT / "scripts/generate_admission_fixtures.py").exists() and not any((ROOT / "fixtures/extensions/admission").glob("*.jsonl")):
            failures.append("ROADMAP marks M35 shipped, but no fixture generator or deterministic admission fixtures are present")
        if not (ROOT / "scripts/generate_queue_leases_fixtures.py").exists() and not any((ROOT / "fixtures/extensions/queue_leases").glob("*.jsonl")):
            failures.append("ROADMAP marks M35 shipped, but no fixture generator or deterministic queue-lease fixtures are present")

    if failures:
        for item in failures:
            print(f"[FAIL] {item}")
        print("Fix roadmap/Makefile mismatch before claiming shipped milestone coverage.")
        return 1

    print("OK: shipped milestone claims align with conformance-ext suite coverage in Makefile.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
