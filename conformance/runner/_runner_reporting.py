from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from _runner_provenance import build_suite_provenance


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
    suite_path: Any | None = None,
    suite_catalog: dict[str, Any] | None = None,
    report_format: str = "legacy",
) -> dict[str, Any]:
    report = {
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
    if report_format == "legacy":
        return report
    if report_format != "v1":
        raise ValueError("report_format must be 'legacy' or 'v1'")
    suite_catalog = suite_catalog or {
        "suite_id": suite_id,
        "suite_version": suite_version,
    }
    return {
        **build_suite_provenance(suite_path, suite_catalog),
        **report,
    }
