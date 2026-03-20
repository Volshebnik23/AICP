#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
RUNNER_DIR = Path(__file__).resolve().parent
if str(RUNNER_DIR) not in sys.path:
    sys.path.insert(0, str(RUNNER_DIR))

from aicp_conformance_runner import run_suite  # noqa: E402
from aicp_profile_runner import run_profile  # noqa: E402
from _runner_io import (  # noqa: E402
    format_status_line as _io_format_status_line,
    resolve_repo_path as _io_resolve_repo_path,
    write_json_report as _io_write_json_report,
)


def _resolve_repo_path(path_like: str) -> Path:
    return _io_resolve_repo_path(path_like, root=ROOT)


def _parse_pair(raw: str) -> tuple[str, str]:
    if "::" not in raw:
        raise ValueError(f"invalid pair '{raw}' (expected '<input>::<out>')")
    left, right = raw.split("::", 1)
    if not left.strip() or not right.strip():
        raise ValueError(f"invalid pair '{raw}' (empty input or output)")
    return left.strip(), right.strip()


def _write_report(out_path: Path, report: dict[str, Any]) -> None:
    _io_write_json_report(out_path, report)


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
        print(_io_format_status_line("Conformance", report.get("suite_id"), out_path, passed, bool(report.get("degraded")), root=ROOT))

    for raw in profile_out:
        profile_ref, out_ref = _parse_pair(raw)
        profile_path = _resolve_repo_path(profile_ref)
        out_path = _resolve_repo_path(out_ref)

        report = run_profile(profile_path)
        _write_report(out_path, report)

        passed = bool(report.get("passed"))
        overall_ok = overall_ok and passed
        print(_io_format_status_line("Profile conformance", report.get("profile_id"), out_path, passed, bool(report.get("degraded")), root=ROOT))

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
