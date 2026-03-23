from __future__ import annotations

import json
from pathlib import Path

from aicp_ref.chain import verify_transcript_chain
from aicp_ref.hashing import message_hash_from_body
from aicp_ref.jcs import canonicalize_json


ROOT = Path(__file__).resolve().parents[3]


def test_canonicalization_sorts_object_keys_by_unicode_code_point_order() -> None:
    payload = {"😀": 1, "\ue000": 2}
    assert canonicalize_json(payload) == '{"":2,"😀":1}'


def test_tv03_fixture_encodes_shared_hash_and_chain_contract() -> None:
    tv = json.loads((ROOT / "fixtures/core_tv.json").read_text(encoding="utf-8"))
    tv3 = tv["TV-03"]
    m1 = tv3["m1"]
    m2 = tv3["m2"]

    m1_hash = message_hash_from_body(m1["object"])
    m2_hash = message_hash_from_body(m2["object"])

    assert m1_hash == m1["message_hash"]
    assert m2["object"]["prev_msg_hash"] == m1_hash
    assert m2_hash == m2["message_hash"]
    assert not verify_transcript_chain(
        [
            {"message_hash": m1_hash},
            {"message_hash": m2_hash, "prev_msg_hash": m2["object"]["prev_msg_hash"]},
        ]
    )
