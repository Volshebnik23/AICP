#!/usr/bin/env python3
"""Render the generator-owned CAPNEG v0.2 implementer transcript."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "fixtures/extensions/capneg_v0_2/positive_cases.json"
CASE_ID = "P09"


def load_quickstart_messages() -> list[dict[str, Any]]:
    catalog = json.loads(SOURCE.read_text(encoding="utf-8"))
    case = next(
        (item for item in catalog["cases"] if item.get("id") == CASE_ID),
        None,
    )
    if case is None:
        raise ValueError(f"generated quickstart case {CASE_ID} is missing")
    return case["messages"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out", default="out/quickstart/capneg-v02-py/profile-composition.jsonl"
    )
    args = parser.parse_args()
    output = ROOT / args.out
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        "".join(
            json.dumps(message, separators=(",", ":"), ensure_ascii=False)
            + "\n"
            for message in load_quickstart_messages()
        ),
        encoding="utf-8",
    )
    print(f"Generated CAPNEG v0.2 Python quickstart: {output.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
