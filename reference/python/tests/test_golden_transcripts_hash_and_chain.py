from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from aicp_ref.validate import load_jsonl, recompute_message_hashes, validate_transcript


ROOT = Path(__file__).resolve().parents[3]


def test_positive_golden_transcripts_hash_and_chain() -> None:
    key_map = json.loads((ROOT / "fixtures/keys/GT_public_keys.json").read_text(encoding="utf-8"))
    gt_files = [
        ROOT / "fixtures/golden_transcripts/GT-01_happy_path_signed.jsonl",
        ROOT / "fixtures/golden_transcripts/GT-02_conflict_choose_signed.jsonl",
        ROOT / "fixtures/golden_transcripts/GT-04_consent_required_and_grant.jsonl",
        ROOT / "fixtures/golden_transcripts/GT-05_consent_revoke.jsonl",
        ROOT / "fixtures/golden_transcripts/GT-06_unknown_base_and_resync.jsonl",
    ]
    has_crypto = importlib.util.find_spec("cryptography") is not None
    for gt in gt_files:
        if ("signed" in gt.name) and not has_crypto:
            continue
        errors = validate_transcript(gt, key_map)
        assert not errors, f"{gt}: {errors}"


def test_negative_duplicate_message_id_detected() -> None:
    messages = load_jsonl(ROOT / "fixtures/golden_transcripts/GT-08_replay_duplicate_message_id.jsonl")
    ids = [m["message_id"] for m in messages]
    assert len(ids) != len(set(ids))


def test_negative_invalid_signature_transcript_has_recomputed_hashes() -> None:
    messages = load_jsonl(ROOT / "fixtures/golden_transcripts/GT-07_invalid_signature_reject.jsonl")
    assert not recompute_message_hashes(messages)
    assert messages[0].get("signatures"), "GT-07 should contain signature to exercise invalid-signature path"
