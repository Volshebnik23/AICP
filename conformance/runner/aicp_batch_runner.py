#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RUNNER_DIR = Path(__file__).resolve().parent
if str(RUNNER_DIR) not in sys.path:
    sys.path.insert(0, str(RUNNER_DIR))

from aicp_conformance_runner import run_suite  # noqa: E402
from aicp_profile_runner import run_profile  # noqa: E402


def _resolve_repo_path(path_like: str) -> Path:
    p = Path(path_like)
    return (ROOT / p).resolve() if not p.is_absolute() else p


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def _parse_pair(raw: str) -> tuple[str, str]:
    if "::" not in raw:
        raise ValueError(f"invalid pair '{raw}' (expected '<input>::<out>')")
    left, right = raw.split("::", 1)
    if not left.strip() or not right.strip():
        raise ValueError(f"invalid pair '{raw}' (empty input or output)")
    return left.strip(), right.strip()


def _write_report(out_path: Path, report: dict[str, Any]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def run_batch(suite_out: list[str], profile_out: list[str]) -> int:
    overall_ok = True

    for raw in suite_out:
        suite_ref, out_ref = _parse_pair(raw)
        suite_path = _resolve_repo_path(suite_ref)
        out_path = _resolve_repo_path(out_ref)

        report = run_suite(suite_path)
        _write_report(out_path, report)

        passed = bool(report.get("passed"))
        overall_ok = overall_ok and passed
        status = "PASSED" if passed else "FAILED"
        if report.get("degraded"):
            status = f"{status} (DEGRADED)"
        print(f"Conformance {status}: {report.get('suite_id')} -> {_display_path(out_path)}")

    for raw in profile_out:
        profile_ref, out_ref = _parse_pair(raw)
        profile_path = _resolve_repo_path(profile_ref)
        out_path = _resolve_repo_path(out_ref)

        report = run_profile(profile_path)
        _write_report(out_path, report)

        passed = bool(report.get("passed"))
        overall_ok = overall_ok and passed
        status = "PASSED" if passed else "FAILED"
        if report.get("degraded"):
            status = f"{status} (DEGRADED)"
        print(f"Profile conformance {status}: {report.get('profile_id')} -> {_display_path(out_path)}")

    return 0 if overall_ok else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Run multiple AICP conformance/profile catalogs in one process")
    parser.add_argument(
        "--suite-out",
        action="append",
        default=[],
        help="Pair '<suite_path>::<report_out_path>' (repeatable)",
    )
    parser.add_argument(
        "--profile-out",
        action="append",
        default=[],
        help="Pair '<profile_path>::<report_out_path>' (repeatable)",
    )
    args = parser.parse_args()

    if not args.suite_out and not args.profile_out:
        print("[FAIL] provide at least one --suite-out or --profile-out pair")
        return 1

    try:
        return run_batch(args.suite_out, args.profile_out)
    except Exception as exc:
        print(f"[FAIL] {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
