#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator
except Exception:  # pragma: no cover - environment dependent
    Draft202012Validator = None

ROOT = Path(__file__).resolve().parents[2]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def add_failure(failures: list[dict[str, Any]], test_id: str, message: str, file: str, line: int | None = None) -> None:
    failures.append({"test_id": test_id, "message": message, "file": file, "line": line})


def run_suite(suite_path: Path) -> dict[str, Any]:
    suite = load_json(suite_path)
    schema_path = ROOT / suite["schema_ref"]
    schema = load_json(schema_path)
    validator = Draft202012Validator(schema) if Draft202012Validator is not None else None

    failures: list[dict[str, Any]] = []

    for transcript in suite["transcripts"]:
        rel_file = transcript["path"]
        file_path = ROOT / rel_file
        rows = []
        for i, line in enumerate(file_path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except Exception as exc:
                add_failure(failures, "CT-SCHEMA-JSONL-01", f"Invalid JSON line: {exc}", rel_file, i)
                continue
            rows.append((i, obj))
            if validator is None:
                pass
            else:
                for err in sorted(validator.iter_errors(obj), key=lambda e: list(e.path)):
                    add_failure(failures, "CT-SCHEMA-JSONL-01", err.message, rel_file, i)

        if not rows:
            add_failure(failures, "CT-INVARIANTS-01", "Transcript has no JSONL records", rel_file, None)
            continue

        # session_id constant + message_id uniqueness
        session_id = rows[0][1].get("session_id")
        seen_ids: set[str] = set()
        for line_no, msg in rows:
            if msg.get("session_id") != session_id:
                add_failure(failures, "CT-INVARIANTS-01", "session_id changed within transcript", rel_file, line_no)

            mid = msg.get("message_id")
            if mid in seen_ids:
                add_failure(failures, "CT-INVARIANTS-01", f"duplicate message_id '{mid}'", rel_file, line_no)
            else:
                seen_ids.add(mid)

        # hash chain
        prev_hash = None
        for line_no, msg in rows:
            if prev_hash is not None and "prev_msg_hash" in msg and msg.get("prev_msg_hash") != prev_hash:
                add_failure(
                    failures,
                    "CT-HASH-CHAIN-01",
                    f"prev_msg_hash mismatch (expected {prev_hash}, got {msg.get('prev_msg_hash')})",
                    rel_file,
                    line_no,
                )
            prev_hash = msg.get("message_hash")

        # expected sequence
        actual_types = [m.get("message_type") for _, m in rows]
        expected_types = transcript.get("expected_message_types", [])
        if actual_types != expected_types:
            add_failure(
                failures,
                "CT-SEQUENCE-01",
                f"message_type sequence mismatch (expected {expected_types}, got {actual_types})",
                rel_file,
                None,
            )

        # signatures object_hash consistency
        for line_no, msg in rows:
            mhash = msg.get("message_hash")
            for sig in msg.get("signatures", []) or []:
                obj_hash = sig.get("object_hash")
                if obj_hash is not None and obj_hash != mhash:
                    add_failure(
                        failures,
                        "CT-SIGNATURE-HASH-01",
                        f"signatures.object_hash mismatch (expected {mhash}, got {obj_hash})",
                        rel_file,
                        line_no,
                    )

    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    passed = not failures
    marks = ["AICP-Core-0.1"] if passed else []

    return {
        "aicp_version": version,
        "suite_id": suite["suite_id"],
        "suite_version": suite["suite_version"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "failures": failures,
        "compatibility_marks": marks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run AICP conformance suite")
    parser.add_argument("--suite", required=True, help="Path to suite catalog JSON")
    parser.add_argument("--out", required=True, help="Path to output report JSON")
    args = parser.parse_args()

    suite_path = (ROOT / args.suite).resolve() if not Path(args.suite).is_absolute() else Path(args.suite)
    out_path = (ROOT / args.out).resolve() if not Path(args.out).is_absolute() else Path(args.out)

    report = run_suite(suite_path)

    if Draft202012Validator is None:
        print("[WARN] jsonschema is not installed. Skipping message schema validation checks.")

    if Draft202012Validator is not None:
        report_schema = load_json(ROOT / "conformance/conformance_report_schema.json")
        Draft202012Validator(report_schema).validate(report)
    else:
        print("[WARN] jsonschema is not installed. Skipping conformance report schema validation.")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(f"Conformance {'PASSED' if report['passed'] else 'FAILED'}: {report['suite_id']} -> {out_path.relative_to(ROOT)}")
    if report["failures"]:
        for f in report["failures"]:
            print(f" - [{f['test_id']}] {f['file']}:{f['line']} {f['message']}")

    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
