#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aicp_core_v02_runner import run_suite


ROOT = Path(__file__).resolve().parents[2]


def run_profile(profile_path: Path) -> dict[str, Any]:
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    if profile.get("aicp_version") != "0.2":
        raise ValueError("isolated Core v0.2 profile runner accepts only version 0.2")
    suite_reports = [
        run_suite(ROOT / suite_path)
        for suite_path in profile.get("required_suites", [])
    ]
    failures: list[dict[str, Any]] = []
    child_marks: list[str] = []
    degraded_reasons: list[str] = []
    skipped_checks: list[str] = []
    for report in suite_reports:
        failures.extend(report.get("failures", []))
        for reason in report.get("degraded_reasons", []):
            if reason not in degraded_reasons:
                degraded_reasons.append(reason)
        for check_id in report.get("skipped_checks", []):
            if check_id not in skipped_checks:
                skipped_checks.append(check_id)
        for mark in report.get("compatibility_marks", []):
            if mark not in child_marks:
                child_marks.append(mark)
    passed = bool(suite_reports) and all(
        report.get("passed") for report in suite_reports
    )
    degraded = any(report.get("degraded") for report in suite_reports) or bool(
        degraded_reasons or skipped_checks
    )
    badge_eligible = (
        passed
        and not degraded
        and degraded_reasons == []
        and skipped_checks == []
        and all(report.get("compatibility_marks") for report in suite_reports)
    )
    marks = (
        [profile["compatibility_mark"], *child_marks]
        if badge_eligible
        else []
    )
    return {
        "aicp_version": profile["aicp_version"],
        "profile_id": profile["profile_id"],
        "profile_version": profile["profile_version"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "suite_reports": suite_reports,
        "failures": failures,
        "compatibility_marks": marks,
        "degraded": degraded,
        "degraded_reasons": degraded_reasons,
        "skipped_checks": skipped_checks,
    }


def _status_label(report: dict[str, Any]) -> str:
    if not report.get("passed"):
        return "FAILED"
    return "PASSED (DEGRADED)" if report.get("degraded") else "PASSED"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Aggregate the experimental Base 0.2 profile"
    )
    parser.add_argument(
        "--profile",
        default="conformance/profiles/PF_AICP_BASE_0.2.json",
    )
    parser.add_argument(
        "--out", default="conformance/report_profile_base_v02.json"
    )
    args = parser.parse_args()
    report = run_profile(ROOT / args.profile)
    out_path = ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    status = _status_label(report)
    print(f"Profile conformance {status}: AICP-BASE@0.2 -> {args.out}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
