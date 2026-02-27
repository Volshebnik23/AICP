from __future__ import annotations

import json
from pathlib import Path

import pytest

from aicp_ref.signatures import verify_ed25519


pytest.importorskip("cryptography")

ROOT = Path(__file__).resolve().parents[3]


def test_tv02_signature_verify() -> None:
    tv = json.loads((ROOT / "fixtures/core_tv.json").read_text(encoding="utf-8"))
    tv2 = tv["TV-02"]
    assert verify_ed25519(tv2["public_key_b64url"], tv2["signature_b64url"], tv2["object_hash"])
