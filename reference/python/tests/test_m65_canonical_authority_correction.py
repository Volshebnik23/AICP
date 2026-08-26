from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "conformance/runner"))
sys.path.insert(0, str(ROOT / "reference/python"))

from aicp_conformance_runner import run_suite as run_canonical_suite  # noqa: E402
from aicp_ref.hashing import message_hash_from_body  # noqa: E402
from m65_extension_semantics import run_suite as run_m65_suite  # noqa: E402


def _b64url_no_pad(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _sign(private_key: Ed25519PrivateKey, digest: str) -> str:
    return _b64url_no_pad(
        private_key.sign(f"AICP1\0SIG\0{digest}".encode("utf-8"))
    )


def _private_keys() -> dict[tuple[str, str], Ed25519PrivateKey]:
    test_keys = json.loads(
        (ROOT / "fixtures/keys/TEST_private_keys.json").read_text(encoding="utf-8")
    )
    moderator = test_keys["moderator:Z"]["private_key_b64url"]
    moderator_raw = base64.urlsafe_b64decode(
        moderator + "=" * (-len(moderator) % 4)
    )
    return {
        ("agent:Q", "Q1"): Ed25519PrivateKey.from_private_bytes(bytes(range(1, 33))),
        ("moderator:Z", "Z1"): Ed25519PrivateKey.from_private_bytes(moderator_raw),
        ("auth:IDP", "P1"): Ed25519PrivateKey.from_private_bytes(bytes([11]) * 32),
        ("agent:A", "A1"): Ed25519PrivateKey.from_private_bytes(bytes([22]) * 32),
    }


def _rehash_and_resign(messages: list[dict]) -> None:
    keys = _private_keys()
    previous: str | None = None
    for message in messages:
        signatures = message.pop("signatures", None)
        message.pop("message_hash", None)
        message.pop("prev_msg_hash", None)
        if previous is not None:
            message["prev_msg_hash"] = previous
        digest = message_hash_from_body(message)
        message["message_hash"] = digest
        previous = digest
        if not signatures:
            continue
        for signature in signatures:
            key = keys[(signature["signer"], signature["kid"])]
            signature["object_hash"] = digest
            signature["sig_b64url"] = _sign(key, digest)
        message["signatures"] = signatures


def _write_bypass_case(tmp_path: Path) -> Path:
    suite = json.loads(
        (ROOT / "conformance/extensions/ID_IDENTITY_LC_0.1.json").read_text(
            encoding="utf-8"
        )
    )
    source = ROOT / "fixtures/extensions/identity_lc/IL-04_agent_migration_presence.jsonl"
    messages = [
        json.loads(line)
        for line in source.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    migration = next(
        message for message in messages if message["message_type"] == "AGENT_MIGRATION"
    )
    migration["payload"]["aid_hash"] = "sha256:" + "0" * 64
    _rehash_and_resign(messages)

    fixture = tmp_path / "identity_migration_external_aid.jsonl"
    fixture.write_text(
        "\n".join(json.dumps(message, separators=(",", ":")) for message in messages)
        + "\n",
        encoding="utf-8",
    )
    suite["transcripts"] = [
        {
            "id": "ID-MIGRATION-EXTERNAL-AID",
            "path": fixture.as_posix(),
            "expected_message_types": [
                message["message_type"] for message in messages
            ],
        }
    ]
    suite_path = tmp_path / "ID_IDENTITY_LC_0.1.json"
    suite_path.write_text(json.dumps(suite, indent=2) + "\n", encoding="utf-8")
    return suite_path


def test_pre_fix_canonical_runner_bypass_is_reproduced(tmp_path: Path) -> None:
    suite_path = _write_bypass_case(tmp_path)

    canonical = run_canonical_suite(suite_path)
    m65_wrapper = run_m65_suite(suite_path)

    assert canonical["passed"] is True
    assert canonical["compatibility_marks"]
    assert m65_wrapper["passed"] is False
    assert m65_wrapper["compatibility_marks"] == []
    assert {failure["test_id"] for failure in m65_wrapper["failures"]} == {
        "ID-MIGRATE-01"
    }
