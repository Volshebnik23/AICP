from __future__ import annotations

import json
from pathlib import Path

from aicp_ref.hashing import object_hash
from aicp_ref.jcs import canonicalize_json


ROOT = Path(__file__).resolve().parents[3]


def test_tv01_contract_hash() -> None:
    tv = json.loads((ROOT / "fixtures/core_tv.json").read_text(encoding="utf-8"))
    tv1 = tv["TV-01"]
    assert canonicalize_json(tv1["object"]) == tv1["canonical_json"]
    assert object_hash(tv1["object_type"], tv1["object"]) == tv1["object_hash"]
