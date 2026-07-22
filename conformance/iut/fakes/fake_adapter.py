#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

IUT_DIR = Path(__file__).resolve().parents[1]
if str(IUT_DIR) not in sys.path:
    sys.path.insert(0, str(IUT_DIR))

from reference_adapter import handle_request  # noqa: E402

if hasattr(sys.stdin, "reconfigure"):
    sys.stdin.reconfigure(encoding="utf-8", errors="strict")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="strict")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=["wrong_canonicalization", "accepts_invalid_chain", "accepts_invalid_signature", "mismatched_projection", "lies_metadata", "timeout"])
    args = parser.parse_args()
    describes = 0
    for raw in sys.stdin:
        if args.mode == "timeout":
            time.sleep(10)
        request: dict[str, Any] = json.loads(raw)
        response = handle_request(request)
        operation = request.get("operation")
        case_id = (request.get("input") or {}).get("case_id")
        if operation == "describe":
            describes += 1
            result = response["result"]
            result["implementation_kind"] = "external_implementation"
            result["implementation_id"] = "fake-external-iut"
            result["implementation_version"] = "1.0.0"
            result["implementation_digest"] = "build:fake-stable"
            if args.mode == "lies_metadata" and describes > 1:
                result["implementation_digest"] = "build:fake-changed"
        elif args.mode == "wrong_canonicalization" and operation == "canonicalize_hash":
            response["result"]["canonical_json"] = "{}"
        elif args.mode == "accepts_invalid_chain" and case_id == "BASE-CONSUMER-INVALID-CHAIN":
            response["result"].update({"accepted": True, "errors": []})
        elif args.mode == "accepts_invalid_signature" and isinstance(case_id, str) and case_id.startswith("AUTH-CONSUMER-") and case_id not in {"AUTH-CONSUMER-VALID", "AUTH-CONSUMER-MULTISIG-VALID"}:
            response["result"].update({"accepted": True, "errors": []})
        elif args.mode == "mismatched_projection" and operation == "project_session_state":
            response["result"]["projection"]["session_id"] = "fake-mismatch"
        sys.stdout.write(json.dumps(response, separators=(",", ":")) + "\n")
        sys.stdout.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
