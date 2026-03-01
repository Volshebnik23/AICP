#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]

import sys
REF_PY = ROOT / "reference/python"
if str(REF_PY) not in sys.path:
    sys.path.insert(0, str(REF_PY))

from aicp_ref.hashing import message_hash_from_body  # noqa: E402


def _b64url_decode(value: str) -> bytes:
    pad = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + pad)


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    for idx, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError as exc:
            raise SystemExit(f"Invalid JSONL in {path} at line {idx}: {exc}") from exc
        if not isinstance(obj, dict):
            raise SystemExit(f"Invalid JSONL object in {path} at line {idx}: expected object")
        rows.append(obj)
    return rows


def generate_signed_transcript(keys_path: Path, in_path: Path, out_path: Path) -> None:
    keys = json.loads(keys_path.read_text(encoding="utf-8"))
    rows = _load_jsonl(in_path)

    prev_hash: str | None = None
    signed_rows: list[dict] = []

    for idx, msg in enumerate(rows, start=1):
        row = dict(msg)
        row.pop("message_hash", None)
        row.pop("prev_msg_hash", None)
        row.pop("signatures", None)

        sender = row.get("sender")
        if not isinstance(sender, str):
            raise SystemExit(f"Message {idx} missing string sender")

        key_meta = keys.get(sender)
        if not isinstance(key_meta, dict):
            raise SystemExit(f"No private key found for sender '{sender}' in {keys_path}")

        if prev_hash is not None:
            row["prev_msg_hash"] = prev_hash

        message_hash = message_hash_from_body(row)
        row["message_hash"] = message_hash

        private_key_b64url = key_meta.get("private_key_b64url")
        kid = key_meta.get("kid")
        if not isinstance(private_key_b64url, str) or not isinstance(kid, str):
            raise SystemExit(f"Invalid key metadata for sender '{sender}' in {keys_path}")

        private_key = Ed25519PrivateKey.from_private_bytes(_b64url_decode(private_key_b64url))
        signing_input = f"AICP1\0SIG\0{message_hash}".encode("utf-8")
        signature = private_key.sign(signing_input)

        row["signatures"] = [
            {
                "signer": sender,
                "kid": kid,
                "object_type": "message",
                "object_hash": message_hash,
                "sig_b64url": _b64url_encode(signature),
            }
        ]

        prev_hash = message_hash
        signed_rows.append(row)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for row in signed_rows:
            f.write(json.dumps(row, separators=(",", ":"), ensure_ascii=False) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate deterministic signed transcript from JSONL template")
    parser.add_argument("--keys", required=True, help="Path to TEST_private_keys.json")
    parser.add_argument("--in", dest="in_path", required=True, help="Input transcript template JSONL")
    parser.add_argument("--out", required=True, help="Output signed JSONL path")
    args = parser.parse_args()

    generate_signed_transcript(Path(args.keys), Path(args.in_path), Path(args.out))
    print(f"Generated signed transcript: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
