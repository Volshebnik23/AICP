from __future__ import annotations

import json
from pathlib import Path

from aicp_ref.hashing import object_hash


ROOT = Path(__file__).resolve().parents[3]


def test_tv03_message_chain_hash() -> None:
    tv = json.loads((ROOT / "fixtures/core_tv.json").read_text(encoding="utf-8"))
    tv3 = tv["TV-03"]
    m1 = tv3["m1"]
    m2 = tv3["m2"]

    m1_hash = object_hash(m1["object_type"], m1["object"])
    m2_hash = object_hash(m2["object_type"], m2["object"])

    assert m1_hash == m1["message_hash"]
    assert m2_hash == m2["message_hash"]
    assert m2["object"]["prev_msg_hash"] == m1_hash
