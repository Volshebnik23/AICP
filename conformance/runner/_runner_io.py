from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


@lru_cache(maxsize=512)
def _load_json_cached(path_str: str) -> Any:
    return json.loads(Path(path_str).read_text(encoding="utf-8"))


def load_json(path: Path) -> Any:
    return _load_json_cached(str(path.resolve()))


def display_path(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def add_failure(
    failures: list[dict[str, Any]],
    test_id: str,
    message: str,
    file: str,
    line: int | None = None,
) -> None:
    failures.append({"test_id": test_id, "message": message, "file": file, "line": line})
