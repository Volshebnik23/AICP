from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def build_conformance_report(
    *,
    aicp_version: str,
    suite_id: str,
    suite_version: str,
    passed: bool,
    failures: list[dict[str, Any]],
    compatibility_marks: list[str],
    degraded: bool,
    degraded_reasons: list[str],
    skipped_checks: list[str],
) -> dict[str, Any]:
    return {
        "aicp_version": aicp_version,
        "suite_id": suite_id,
        "suite_version": suite_version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "failures": failures,
        "compatibility_marks": compatibility_marks,
        "degraded": degraded,
        "degraded_reasons": degraded_reasons,
        "skipped_checks": skipped_checks,
    }
