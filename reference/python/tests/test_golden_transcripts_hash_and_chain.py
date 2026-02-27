from __future__ import annotations

import json
from pathlib import Path

import pytest

from aicp_ref.validate import validate_transcript


pytest.importorskip("cryptography")

ROOT = Path(__file__).resolve().parents[3]


def test_golden_transcripts_hash_chain_and_signatures() -> None:
    key_map = json.loads((ROOT / "fixtures/keys/GT_public_keys.json").read_text(encoding="utf-8"))
    gt_files = [
        ROOT / "fixtures/golden_transcripts/GT-01_happy_path_signed.jsonl",
        ROOT / "fixtures/golden_transcripts/GT-02_conflict_choose_signed.jsonl",
    ]
    for gt in gt_files:
        errors = validate_transcript(gt, key_map)
        assert not errors, f"{gt}: {errors}"
