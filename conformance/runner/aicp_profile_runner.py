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


def run_profile(profile_path: Path) -> dict[str, Any]:
    profile = load_json(profile_path)
    suite_reports: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    marks: list[str] = []

    for rel_suite in profile.get("required_suites", []):
        suite_path = (ROOT / rel_suite).resolve() if not Path(rel_suite).is_absolute() else Path(rel_suite)
        suite_report = run_suite(suite_path)
        suite_reports.append(suite_report)

        for failure in suite_report.get("failures", []):
            entry = dict(failure)
            entry["suite_id"] = suite_report.get("suite_id")
            entry["suite_path"] = rel_suite
            failures.append(entry)

        for mark in suite_report.get("compatibility_marks", []):
            if isinstance(mark, str) and mark not in marks:
                marks.append(mark)

    passed = all(r.get("passed") for r in suite_reports)
    profile_mark = profile.get("compatibility_mark")
    if passed and isinstance(profile_mark, str):
        marks.insert(0, profile_mark)

    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    return {
        "aicp_version": version,
        "profile_id": profile.get("profile_id"),
        "profile_version": profile.get("profile_version"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "suite_reports": suite_reports,
        "failures": failures,
        "compatibility_marks": marks,
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

    print(
        f"Profile conformance {'PASSED' if report['passed'] else 'FAILED'}: "
        f"{report['profile_id']} -> {out_path.relative_to(ROOT)}"
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
