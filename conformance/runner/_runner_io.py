from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def resolve_repo_path(path_like: str, root: Path = ROOT) -> Path:
    path = Path(path_like)
    return (root / path).resolve() if not path.is_absolute() else path


def display_path(path: Path, root: Path = ROOT) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def write_json_report(out_path: Path, report: dict[str, Any]) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def format_status_line(prefix: str, report_id: str | None, out_path: Path, passed: bool, degraded: bool, root: Path = ROOT) -> str:
    status = "PASSED" if passed else "FAILED"
    if degraded:
        status = f"{status} (DEGRADED)"
    return f"{prefix} {status}: {report_id} -> {display_path(out_path, root=root)}"
