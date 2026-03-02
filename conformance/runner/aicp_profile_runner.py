#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RUNNER_DIR = Path(__file__).resolve().parent
if str(RUNNER_DIR) not in sys.path:
    sys.path.insert(0, str(RUNNER_DIR))

from aicp_conformance_runner import run_suite  # noqa: E402


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _format_out_path(out_path: Path) -> str:
    try:
        return str(out_path.relative_to(ROOT))
    except ValueError:
        return str(out_path)


def run_profile(profile_path: Path) -> dict[str, Any]:
    profile = load_json(profile_path)
    suite_reports: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    marks: list[str] = []
    degraded = False
    degraded_reasons: list[str] = []
    observed_protocol_versions: set[str] = set()

    for rel_suite in profile.get("required_suites", []):
        suite_path = (ROOT / rel_suite).resolve() if not Path(rel_suite).is_absolute() else Path(rel_suite)
        suite_report = run_suite(suite_path)
        suite_reports.append(suite_report)

        suite_protocol_version = suite_report.get("aicp_version")
        if isinstance(suite_protocol_version, str):
            observed_protocol_versions.add(suite_protocol_version)
        else:
            suite_catalog = load_json(suite_path)
            fallback_protocol_version = suite_catalog.get("aicp_version")
            if isinstance(fallback_protocol_version, str):
                observed_protocol_versions.add(fallback_protocol_version)

        for failure in suite_report.get("failures", []):
            entry = dict(failure)
            entry["suite_id"] = suite_report.get("suite_id")
            entry["suite_path"] = rel_suite
            failures.append(entry)

        if suite_report.get("degraded"):
            degraded = True
            for reason in suite_report.get("degraded_reasons", []) or []:
                if isinstance(reason, str) and reason not in degraded_reasons:
                    degraded_reasons.append(reason)

        for mark in suite_report.get("compatibility_marks", []):
            if isinstance(mark, str) and mark not in marks:
                marks.append(mark)

    passed = all(r.get("passed") for r in suite_reports)
    profile_mark = profile.get("compatibility_mark")
    if degraded:
        marks = []
    elif passed and isinstance(profile_mark, str):
        marks.insert(0, profile_mark)

    protocol_version = profile.get("aicp_version")
    if not isinstance(protocol_version, str):
        if len(observed_protocol_versions) == 1:
            protocol_version = next(iter(observed_protocol_versions))
        elif not observed_protocol_versions:
            raise ValueError("Profile has no suites to infer aicp_version; set profile['aicp_version'] explicitly.")
        else:
            raise ValueError(f"Profile suites disagree on aicp_version: {sorted(observed_protocol_versions)}")

    return {
        "aicp_version": protocol_version,
        "profile_id": profile.get("profile_id"),
        "profile_version": profile.get("profile_version"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "suite_reports": suite_reports,
        "failures": failures,
        "compatibility_marks": marks,
        "degraded": degraded,
        "degraded_reasons": degraded_reasons,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run AICP profile conformance aggregation")
    parser.add_argument("--profile", required=True, help="Path to profile catalog JSON")
    parser.add_argument("--out", required=True, help="Path to output profile report JSON")
    args = parser.parse_args()

    profile_path = (ROOT / args.profile).resolve() if not Path(args.profile).is_absolute() else Path(args.profile)
    out_path = (ROOT / args.out).resolve() if not Path(args.out).is_absolute() else Path(args.out)

    try:
        report = run_profile(profile_path)
    except Exception as exc:
        print(f"[FAIL] {exc}")
        return 1

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    status = 'PASSED' if report['passed'] else 'FAILED'
    if report.get('degraded'):
        status = f"{status} (DEGRADED)"
    print(
        f"Profile conformance {status}: "
        f"{report['profile_id']} -> {_format_out_path(out_path)}"
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
