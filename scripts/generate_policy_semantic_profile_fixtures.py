#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
REF_PY = ROOT / "reference/python"
if str(REF_PY) not in sys.path:
    sys.path.insert(0, str(REF_PY))

from aicp_ref.hashing import message_hash_from_body, object_hash  # noqa: E402

OUT = ROOT / "fixtures/extensions/policy_profiles"


def _finalize(rows: list[dict]) -> list[dict]:
    out: list[dict] = []
    prev_hash: str | None = None
    for row in rows:
        msg = dict(row)
        if prev_hash:
            msg["prev_msg_hash"] = prev_hash
        msg["message_hash"] = message_hash_from_body(msg)
        prev_hash = msg["message_hash"]
        out.append(msg)
    return out


def _ctx(context_id: str, subject: str, action: str, resource: str) -> dict:
    base = {
        "context_id": context_id,
        "contract_head_version": "v1",
        "subject": subject,
        "action": action,
        "resource": resource,
    }
    base["context_hash"] = object_hash("evaluation_context", base)
    return base


def _write(name: str, rows: list[dict]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / name
    path.write_text("\n".join(json.dumps(r, separators=(",", ":")) for r in _finalize(rows)) + "\n", encoding="utf-8")


def main() -> int:
    opa_ctx = _ctx("ctx-opa-01", "agent:alice", "tool.call", "resource:payments")
    _write(
        "PPS-OPA-01_deterministic_pass.jsonl",
        [
            {
                "session_id": "sPPOPA01",
                "message_id": "m1",
                "timestamp": "2026-03-14T00:00:00Z",
                "sender": "vendor:a",
                "message_type": "POLICY_EVAL_REQUEST",
                "contract_id": "cPPOPA01",
                "payload": {
                    "eval_id": "opa-eval-1",
                    "policy_bundle_ref": {
                        "policy_bundle_id": "bundle-opa-1",
                        "version": "1",
                        "language_id": "rego.v1",
                        "content_hash": "sha256:bundle-opa-1",
                    },
                    "policy_binding_ref": {"binding_id": "opa.input.v1", "input_schema_version": "1"},
                    "evaluation_context": opa_ctx,
                },
            },
            {
                "session_id": "sPPOPA01",
                "message_id": "m2",
                "timestamp": "2026-03-14T00:00:02Z",
                "sender": "vendor:a",
                "message_type": "POLICY_EVAL_RESULT",
                "contract_id": "cPPOPA01",
                "payload": {
                    "eval_id": "opa-eval-1",
                    "policy_decision": {
                        "decision": "DENY",
                        "reason_codes": ["SCOPE_VIOLATION"],
                        "evaluated_at": "2026-03-14T00:00:02Z",
                        "context_hash": opa_ctx["context_hash"],
                    },
                },
            },
            {
                "session_id": "sPPOPA01",
                "message_id": "m3",
                "timestamp": "2026-03-14T00:00:03Z",
                "sender": "vendor:b",
                "message_type": "POLICY_EVAL_REQUEST",
                "contract_id": "cPPOPA01",
                "payload": {
                    "eval_id": "opa-eval-2",
                    "policy_bundle_ref": {
                        "policy_bundle_id": "bundle-opa-1",
                        "version": "1",
                        "language_id": "rego.v1",
                        "content_hash": "sha256:bundle-opa-1",
                    },
                    "policy_binding_ref": {"binding_id": "opa.input.v1", "input_schema_version": "1"},
                    "evaluation_context": opa_ctx,
                },
            },
            {
                "session_id": "sPPOPA01",
                "message_id": "m4",
                "timestamp": "2026-03-14T00:00:05Z",
                "sender": "vendor:b",
                "message_type": "POLICY_EVAL_RESULT",
                "contract_id": "cPPOPA01",
                "payload": {
                    "eval_id": "opa-eval-2",
                    "policy_decision": {
                        "decision": "DENY",
                        "reason_codes": ["SCOPE_VIOLATION"],
                        "evaluated_at": "2026-03-14T00:00:05Z",
                        "context_hash": opa_ctx["context_hash"],
                    },
                },
            },
        ],
    )

    bad_ctx = _ctx("ctx-opa-02", "agent:bob", "tool.call", "resource:db")
    _write(
        "PPS-OPA-02_unregistered_language_binding_expected_fail.jsonl",
        [
            {
                "session_id": "sPPOPA02",
                "message_id": "m1",
                "timestamp": "2026-03-14T00:10:00Z",
                "sender": "vendor:a",
                "message_type": "POLICY_EVAL_REQUEST",
                "contract_id": "cPPOPA02",
                "payload": {
                    "eval_id": "opa-bad-1",
                    "policy_bundle_ref": {
                        "policy_bundle_id": "bundle-opa-bad",
                        "version": "1",
                        "language_id": "rego.experimental",
                        "content_hash": "sha256:bundle-opa-bad",
                    },
                    "policy_binding_ref": {"binding_id": "opa.input.experimental", "input_schema_version": "1"},
                    "evaluation_context": bad_ctx,
                },
            },
            {
                "session_id": "sPPOPA02",
                "message_id": "m2",
                "timestamp": "2026-03-14T00:10:02Z",
                "sender": "vendor:a",
                "message_type": "POLICY_EVAL_RESULT",
                "contract_id": "cPPOPA02",
                "payload": {
                    "eval_id": "opa-bad-1",
                    "policy_decision": {
                        "decision": "DENY",
                        "reason_codes": ["UNREGISTERED_REASON"],
                        "evaluated_at": "2026-03-14T00:10:02Z",
                        "context_hash": bad_ctx["context_hash"],
                    },
                },
            },
        ],
    )

    abac_ctx = _ctx("ctx-abac-01", "subject:analyst", "dataset.read", "resource:ledger")
    _write(
        "PPS-ABAC-01_dimensions_deterministic_pass.jsonl",
        [
            {
                "session_id": "sPPABAC01",
                "message_id": "m1",
                "timestamp": "2026-03-14T00:20:00Z",
                "sender": "vendor:a",
                "message_type": "POLICY_EVAL_REQUEST",
                "contract_id": "cPPABAC01",
                "payload": {
                    "eval_id": "abac-eval-1",
                    "policy_bundle_ref": {
                        "policy_bundle_id": "bundle-abac-1",
                        "version": "1",
                        "language_id": "abac-rbac.v1",
                        "content_hash": "sha256:bundle-abac-1",
                    },
                    "policy_binding_ref": {"binding_id": "abac-rbac.input.v1", "input_schema_version": "1"},
                    "evaluation_context": abac_ctx,
                },
            },
            {
                "session_id": "sPPABAC01",
                "message_id": "m2",
                "timestamp": "2026-03-14T00:20:02Z",
                "sender": "vendor:a",
                "message_type": "POLICY_EVAL_RESULT",
                "contract_id": "cPPABAC01",
                "payload": {
                    "eval_id": "abac-eval-1",
                    "policy_decision": {
                        "decision": "ALLOW",
                        "reason_codes": [],
                        "evaluated_at": "2026-03-14T00:20:02Z",
                        "context_hash": abac_ctx["context_hash"],
                    },
                },
            },
            {
                "session_id": "sPPABAC01",
                "message_id": "m3",
                "timestamp": "2026-03-14T00:20:03Z",
                "sender": "vendor:b",
                "message_type": "POLICY_EVAL_REQUEST",
                "contract_id": "cPPABAC01",
                "payload": {
                    "eval_id": "abac-eval-2",
                    "policy_bundle_ref": {
                        "policy_bundle_id": "bundle-abac-1",
                        "version": "1",
                        "language_id": "abac-rbac.v1",
                        "content_hash": "sha256:bundle-abac-1",
                    },
                    "policy_binding_ref": {"binding_id": "abac-rbac.input.v1", "input_schema_version": "1"},
                    "evaluation_context": abac_ctx,
                },
            },
            {
                "session_id": "sPPABAC01",
                "message_id": "m4",
                "timestamp": "2026-03-14T00:20:05Z",
                "sender": "vendor:b",
                "message_type": "POLICY_EVAL_RESULT",
                "contract_id": "cPPABAC01",
                "payload": {
                    "eval_id": "abac-eval-2",
                    "policy_decision": {
                        "decision": "ALLOW",
                        "reason_codes": [],
                        "evaluated_at": "2026-03-14T00:20:05Z",
                        "context_hash": abac_ctx["context_hash"],
                    },
                },
            },
        ],
    )

    _write(
        "PPS-ABAC-02_semantic_mismatch_expected_fail.jsonl",
        [
            {
                "session_id": "sPPABAC02",
                "message_id": "m1",
                "timestamp": "2026-03-14T00:30:00Z",
                "sender": "vendor:a",
                "message_type": "POLICY_EVAL_REQUEST",
                "contract_id": "cPPABAC02",
                "payload": {
                    "eval_id": "abac-mm-1",
                    "policy_bundle_ref": {
                        "policy_bundle_id": "bundle-abac-mm",
                        "version": "1",
                        "language_id": "abac-rbac.v1",
                        "content_hash": "sha256:bundle-abac-mm",
                    },
                    "policy_binding_ref": {"binding_id": "abac-rbac.input.v1", "input_schema_version": "1"},
                    "evaluation_context": abac_ctx,
                },
            },
            {
                "session_id": "sPPABAC02",
                "message_id": "m2",
                "timestamp": "2026-03-14T00:30:02Z",
                "sender": "vendor:a",
                "message_type": "POLICY_EVAL_RESULT",
                "contract_id": "cPPABAC02",
                "payload": {
                    "eval_id": "abac-mm-1",
                    "policy_decision": {
                        "decision": "ALLOW",
                        "reason_codes": [],
                        "evaluated_at": "2026-03-14T00:30:02Z",
                        "context_hash": abac_ctx["context_hash"],
                    },
                },
            },
            {
                "session_id": "sPPABAC02",
                "message_id": "m3",
                "timestamp": "2026-03-14T00:30:03Z",
                "sender": "vendor:b",
                "message_type": "POLICY_EVAL_REQUEST",
                "contract_id": "cPPABAC02",
                "payload": {
                    "eval_id": "abac-mm-2",
                    "policy_bundle_ref": {
                        "policy_bundle_id": "bundle-abac-mm",
                        "version": "1",
                        "language_id": "abac-rbac.v1",
                        "content_hash": "sha256:bundle-abac-mm",
                    },
                    "policy_binding_ref": {"binding_id": "abac-rbac.input.v1", "input_schema_version": "1"},
                    "evaluation_context": abac_ctx,
                },
            },
            {
                "session_id": "sPPABAC02",
                "message_id": "m4",
                "timestamp": "2026-03-14T00:30:05Z",
                "sender": "vendor:b",
                "message_type": "POLICY_EVAL_RESULT",
                "contract_id": "cPPABAC02",
                "payload": {
                    "eval_id": "abac-mm-2",
                    "policy_decision": {
                        "decision": "DENY",
                        "reason_codes": ["TOOL_ACCESS_DENIED"],
                        "evaluated_at": "2026-03-14T00:30:05Z",
                        "context_hash": abac_ctx["context_hash"],
                    },
                },
            },
        ],
    )

    llm_ctx = _ctx("ctx-llm-01", "agent:user", "prompt.submit", "resource:model")
    _write(
        "PPS-LLM-01_evidence_boundary_pass.jsonl",
        [
            {
                "session_id": "sPPLLM01",
                "message_id": "m1",
                "timestamp": "2026-03-14T00:40:00Z",
                "sender": "vendor:a",
                "message_type": "POLICY_EVAL_REQUEST",
                "contract_id": "cPPLLM01",
                "payload": {
                    "eval_id": "llm-eval-1",
                    "policy_bundle_ref": {
                        "policy_bundle_id": "bundle-llm-1",
                        "version": "1",
                        "language_id": "llm-safety-taxonomy.v1",
                        "content_hash": "sha256:bundle-llm-1",
                    },
                    "policy_binding_ref": {"binding_id": "llm-safety.evidence.v1", "input_schema_version": "1"},
                    "evaluation_context": llm_ctx,
                },
            },
            {
                "session_id": "sPPLLM01",
                "message_id": "m2",
                "timestamp": "2026-03-14T00:40:02Z",
                "sender": "vendor:a",
                "message_type": "POLICY_EVAL_RESULT",
                "contract_id": "cPPLLM01",
                "payload": {
                    "eval_id": "llm-eval-1",
                    "policy_decision": {
                        "decision": "INCONCLUSIVE",
                        "reason_codes": ["LLM_SAFETY_REVIEW_REQUIRED"],
                        "evaluated_at": "2026-03-14T00:40:02Z",
                        "engine_info": {"model_id": "classifier-v1", "nondeterministic": True},
                        "context_hash": llm_ctx["context_hash"],
                    },
                    "evidence_refs": ["msgid:m1"],
                },
            },
        ],
    )

    _write(
        "PPS-LLM-02_missing_evidence_expected_fail.jsonl",
        [
            {
                "session_id": "sPPLLM02",
                "message_id": "m1",
                "timestamp": "2026-03-14T00:50:00Z",
                "sender": "vendor:a",
                "message_type": "POLICY_EVAL_REQUEST",
                "contract_id": "cPPLLM02",
                "payload": {
                    "eval_id": "llm-eval-2",
                    "policy_bundle_ref": {
                        "policy_bundle_id": "bundle-llm-2",
                        "version": "1",
                        "language_id": "llm-safety-taxonomy.v1",
                        "content_hash": "sha256:bundle-llm-2",
                    },
                    "policy_binding_ref": {"binding_id": "llm-safety.evidence.v1", "input_schema_version": "1"},
                    "evaluation_context": llm_ctx,
                },
            },
            {
                "session_id": "sPPLLM02",
                "message_id": "m2",
                "timestamp": "2026-03-14T00:50:02Z",
                "sender": "vendor:a",
                "message_type": "POLICY_EVAL_RESULT",
                "contract_id": "cPPLLM02",
                "payload": {
                    "eval_id": "llm-eval-2",
                    "policy_decision": {
                        "decision": "DENY",
                        "reason_codes": ["PROMPT_INJECTION_SUSPECTED"],
                        "evaluated_at": "2026-03-14T00:50:02Z",
                        "engine_info": {"model_id": "classifier-v1", "nondeterministic": True},
                        "context_hash": llm_ctx["context_hash"],
                    }
                },
            },
        ],
    )

    print("Wrote policy semantic profile fixtures to", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
