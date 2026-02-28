#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REF_PY = ROOT / "reference/python"
if str(REF_PY) not in sys.path:
    sys.path.insert(0, str(REF_PY))

from aicp_ref.hashing import message_hash_from_body
from aicp_ref.signatures import signature_verifier_available, verify_ed25519


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def load_jsonl(path: Path):
    rows = []
    errors = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            rows.append((line_no, json.loads(line)))
        except Exception as exc:
            errors.append((line_no, f"invalid JSON: {exc}"))
    return rows, errors


def _load_keys(path: Path | None) -> dict[str, Any]:
    if path is None:
        path = ROOT / "fixtures/keys/GT_public_keys.json"
    if path.is_dir():
        path = path / "GT_public_keys.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(raw, dict):
        return raw
    raise ValueError("keys file must be a JSON object mapping signer -> key metadata")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a sandbox AICP thread JSONL file")
    parser.add_argument("jsonl_path")
    parser.add_argument("--keys", help="Path to key map JSON file or directory containing GT_public_keys.json")
    parser.add_argument("--no-signature-verify", action="store_true", help="Skip signature verification checks")
    args = parser.parse_args()

    path = Path(args.jsonl_path).expanduser().resolve()

    rows, parse_errors = load_jsonl(path)
    failures: list[str] = [f"line {ln}: {msg}" for ln, msg in parse_errors]

    validator = None
    try:
        from jsonschema import Draft202012Validator

        schema = json.loads((ROOT / "schemas/core/aicp-core-message.schema.json").read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema)
    except Exception:
        print("[WARN] jsonschema not installed; skipping core schema validation.")

    key_map: dict[str, Any] = {}
    if not args.no_signature_verify:
        key_path = Path(args.keys).expanduser().resolve() if args.keys else None
        try:
            key_map = _load_keys(key_path)
        except Exception as exc:
            failures.append(f"failed loading keys: {exc}")

    if rows:
        session = rows[0][1].get("session_id")
        seen_ids: set[str] = set()
        prev_hash = None

        for line_no, msg in rows:
            if validator is not None:
                for err in validator.iter_errors(msg):
                    failures.append(f"line {line_no}: schema error: {err.message}")

            if msg.get("session_id") != session:
                failures.append(f"line {line_no}: session_id changed in thread")

            mid = msg.get("message_id")
            if mid in seen_ids:
                failures.append(f"line {line_no}: duplicate message_id '{mid}'")
            seen_ids.add(mid)

            if prev_hash is not None and msg.get("prev_msg_hash") != prev_hash:
                failures.append(
                    f"line {line_no}: prev_msg_hash mismatch (expected {prev_hash}, got {msg.get('prev_msg_hash')})"
                )

            body = dict(msg)
            body.pop("message_hash", None)
            body.pop("signatures", None)
            computed = message_hash_from_body(body)
            if computed != msg.get("message_hash"):
                failures.append(
                    f"line {line_no}: message_hash mismatch (expected {msg.get('message_hash')}, got {computed})"
                )

            prev_hash = msg.get("message_hash")

            if msg.get("signatures"):
                if args.no_signature_verify:
                    continue
                if not signature_verifier_available():
                    failures.append(f"line {line_no}: signatures present but cryptography unavailable")
                else:
                    for sig in msg.get("signatures", []):
                        signer = sig.get("signer")
                        key = key_map.get(signer, {}).get("public_key_b64url", "")
                        if not key:
                            failures.append(f"line {line_no}: missing public key for signer {signer}")
                            continue
                        if not verify_ed25519(key, sig.get("sig_b64url", ""), sig.get("object_hash", "")):
                            failures.append(f"line {line_no}: signature verification failed for signer {signer}")

    if args.no_signature_verify:
        print("[WARN] --no-signature-verify enabled; badge eligibility may be affected in conformance/profile reports.")

    if failures:
        print(f"Sandbox validation FAILED for {_display_path(path)}")
        for f in failures:
            print(f" - {f}")
        return 1

    print(f"Sandbox validation PASSED for {_display_path(path)} ({len(rows)} records)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
