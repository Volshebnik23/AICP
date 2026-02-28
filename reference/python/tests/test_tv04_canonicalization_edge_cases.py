from __future__ import annotations

import json
from pathlib import Path

from aicp_ref.hashing import object_hash
from aicp_ref.jcs import canonicalize_json


ROOT = Path(__file__).resolve().parents[3]


def test_tv04_to_tv06_canonicalization_vectors() -> None:
    tv = json.loads((ROOT / "fixtures/core_tv.json").read_text(encoding="utf-8"))

    for case_id in ("TV-04", "TV-05", "TV-06"):
        case = tv[case_id]
        obj = case["object"]
        assert canonicalize_json(obj) == case["canonical_json"]
        assert object_hash(case["object_type"], obj) == case["object_hash"]
