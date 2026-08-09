#!/usr/bin/env python3
from __future__ import annotations

import argparse
import copy
import json
import sys
from typing import Any


from product_profile_reference_adapter import handle_request


MODES = (
    "external_good",
    "target_not_declared",
    "wrong_profile_id",
    "wrong_profile_version",
    "missing_producer_scenario",
    "wrong_producer_scenario_identity",
    "nondeterministic_repeat",
    "missing_consumer_case",
    "duplicate_consumer_case",
    "consumer_accepts_every_fixture",
    "consumer_rejects_every_fixture",
    "consumer_missing_fields",
    "unexpected_degradation",
    "hidden_skipped_check",
    "wrong_profile_catalog_digest",
    "wrong_suite_digest",
    "wrong_input_digest",
    "wrong_runner_digest",
    "wrong_report_schema_digest",
    "forged_compatibility_mark",
    "reference_subject_with_external_mark",
    "profile_downgrade",
    "missing_capneg_contract_binding",
    "unsupported_selected_profile",
    "malformed_core_contract",
    "unknown_core_policy_category",
    "duplicate_core_policy_id",
    "wrong_generated_sequence",
    "invalid_capneg_reason_code",
    "invalid_capneg_privacy_mode",
    "invalid_capneg_binding",
    "invalid_capneg_channel_properties",
    "policy_reason_code_failure",
    "policy_context_hash_failure",
    "deny_followed_by_delivery",
    "wrong_enforcement_binding",
    "unauthorized_enforcer",
    "invalid_enforcement_sanction_code",
    "malformed_namespaced_enforcement_sanction",
    "missing_resume_response",
    "mismatched_resume_response",
    "inconsistent_resume_head",
    "forced_resync_loop",
    "invalid_resume_recommended_action",
    "invalid_object_hash",
    "mismatched_object_response",
    "invalid_state_sync",
    "unsigned_binding_issue",
    "invalid_issue_signature",
    "wrong_binding_issuer",
    "binding_object_hash_mismatch",
    "expired_binding_use",
    "revoked_binding_use",
    "revoked_identity_key_use",
    "invalid_rotation_cross_signature",
    "unknown_key",
    "kid_mismatch",
    "acting_agent_mismatch",
)


def _mutate_generated(mode: str, result: dict[str, Any], call: int) -> dict[str, Any]:
    value = copy.deepcopy(result)
    messages = value.get("messages") if isinstance(value.get("messages"), list) else []
    if mode == "nondeterministic_repeat" and call % 2 == 0:
        value["scenario_id"] = str(value.get("scenario_id")) + "-changed"
    elif mode in {"profile_downgrade", "unsupported_selected_profile"}:
        for message in messages:
            selected = (((message.get("payload") or {}).get("negotiation_result") or {}).get("selected") or {})
            if isinstance(selected.get("aicp_profile"), dict):
                selected["aicp_profile"]["profile_version"] = "0.0"
                break
    elif mode == "missing_capneg_contract_binding":
        for message in messages:
            contract = ((message.get("payload") or {}).get("contract") or {})
            if isinstance((contract.get("ext") or {}).get("capneg"), dict):
                contract["ext"].pop("capneg", None)
                break
    elif mode in {
        "malformed_core_contract",
        "unknown_core_policy_category",
        "duplicate_core_policy_id",
    }:
        for message in messages:
            contract = ((message.get("payload") or {}).get("contract") or {})
            if not isinstance(contract, dict) or not contract:
                continue
            if mode == "malformed_core_contract":
                contract.pop("goal", None)
            elif mode == "unknown_core_policy_category":
                contract["policies"] = [
                    {
                        "policy_id": "policy-1",
                        "category": "NOT_REGISTERED",
                        "parameters": {},
                    }
                ]
            else:
                contract["policies"] = [
                    {"policy_id": "policy-1", "category": "safety", "parameters": {}},
                    {"policy_id": "policy-1", "category": "safety", "parameters": {}},
                ]
            break
    elif mode == "wrong_generated_sequence" and len(messages) >= 3:
        messages[1], messages[2] = messages[2], messages[1]
    elif mode == "invalid_capneg_reason_code":
        for message in messages:
            if message.get("message_type") == "CAPABILITIES_REJECT":
                (message.get("payload") or {})["reason_code"] = "NOT_REGISTERED"
                break
    elif mode in {
        "invalid_capneg_privacy_mode",
        "invalid_capneg_binding",
        "invalid_capneg_channel_properties",
    }:
        for message in messages:
            if message.get("message_type") != "CAPABILITIES_PROPOSE":
                continue
            selected = (((message.get("payload") or {}).get("negotiation_result") or {}).get("selected") or {})
            if mode == "invalid_capneg_privacy_mode":
                selected["privacy_mode"] = "not-registered"
            elif mode == "invalid_capneg_binding":
                selected["binding"] = "NOT-REGISTERED"
            else:
                selected["channel_properties"] = {"CP-ORDERING-0.1": "ordered"}
            break
    elif mode == "policy_reason_code_failure":
        for message in messages:
            decision = ((message.get("payload") or {}).get("policy_decision") or {})
            if decision:
                decision["reason_codes"] = ["NOT_REGISTERED"]
                break
    elif mode == "policy_context_hash_failure":
        for message in messages:
            context = ((message.get("payload") or {}).get("evaluation_context") or {})
            if context:
                context["context_hash"] = "sha256:wrong"
                break
    elif mode == "deny_followed_by_delivery":
        for message in messages:
            if message.get("message_type") == "ENFORCEMENT_VERDICT":
                (message.get("payload") or {})["decision"] = "DENY"
    elif mode == "wrong_enforcement_binding":
        for message in messages:
            if message.get("message_type") == "CONTENT_DELIVER":
                (message.get("payload") or {})["verdict_message_id"] = "missing"
    elif mode == "unauthorized_enforcer":
        for message in messages:
            if message.get("message_type") == "ENFORCEMENT_VERDICT":
                message["sender"] = "agent:unauthorized"
    elif mode in {
        "invalid_enforcement_sanction_code",
        "malformed_namespaced_enforcement_sanction",
    }:
        for message in messages:
            if message.get("message_type") == "ENFORCEMENT_VERDICT":
                sanctions = (message.get("payload") or {}).get("sanctions") or []
                if sanctions:
                    sanctions[0]["code"] = (
                        "vendor bad:code"
                        if mode == "malformed_namespaced_enforcement_sanction"
                        else "NOT-REGISTERED"
                    )
                break
    elif mode == "missing_resume_response":
        value["messages"] = [m for m in messages if m.get("message_type") != "RESUME_RESPONSE"]
    elif mode == "mismatched_resume_response":
        for message in messages:
            if message.get("message_type") == "RESUME_RESPONSE":
                (message.get("payload") or {})["resume_id"] = "wrong"
    elif mode == "inconsistent_resume_head":
        for message in messages:
            if message.get("message_type") == "RESUME_RESPONSE":
                payload = message.get("payload") or {}
                payload["current_head_hash"] = ((next((m for m in messages if m.get("message_type") == "RESUME_REQUEST"), {}).get("payload") or {}).get("last_seen_message_hash"))
    elif mode == "forced_resync_loop":
        pair = [m for m in messages if m.get("message_type") in {"RESUME_REQUEST", "RESUME_RESPONSE"}]
        value["messages"] = [*messages, *copy.deepcopy(pair), *copy.deepcopy(pair)]
    elif mode == "invalid_resume_recommended_action":
        for message in messages:
            if message.get("message_type") == "RESUME_RESPONSE":
                (message.get("payload") or {})["recommended_actions"] = [
                    "NOT-REGISTERED"
                ]
                break
    elif mode == "invalid_object_hash":
        for message in messages:
            refs = (message.get("payload") or {}).get("entries")
            if isinstance(refs, list) and refs:
                refs[0]["object_hash"] = "sha256:wrong"
                break
    elif mode == "mismatched_object_response":
        for message in messages:
            if message.get("message_type") == "OBJECT_RESPONSE":
                (message.get("payload") or {})["request_id"] = "wrong"
    elif mode == "invalid_state_sync":
        value["messages"] = [m for m in messages if m.get("message_type") != "STATE_SYNC_RESPONSE"]
    elif mode == "unsigned_binding_issue":
        for message in messages:
            if message.get("message_type") == "SUBJECT_BINDING_ISSUE":
                message.pop("signatures", None)
    elif mode in {"invalid_issue_signature", "unknown_key", "kid_mismatch"}:
        for message in messages:
            if message.get("message_type") == "SUBJECT_BINDING_ISSUE" and message.get("signatures"):
                signature = message["signatures"][0]
                if mode == "invalid_issue_signature":
                    signature["sig_b64url"] = "invalid"
                elif mode == "unknown_key":
                    signature["signer"] = "unknown:issuer"
                else:
                    signature["kid"] = "wrong-kid"
                break
    elif mode == "wrong_binding_issuer":
        for message in messages:
            ref = ((message.get("payload") or {}).get("binding_ref") or {})
            if isinstance(ref.get("object"), dict):
                ref["object"]["issuer"] = "wrong:issuer"
                break
    elif mode == "binding_object_hash_mismatch":
        for message in messages:
            ref = ((message.get("payload") or {}).get("binding_ref") or {})
            if ref:
                ref["object_hash"] = "sha256:wrong"
                break
    elif mode in {"expired_binding_use", "revoked_binding_use", "acting_agent_mismatch"}:
        for message in messages:
            if isinstance(message.get("ext"), dict) and message["ext"].get("subject_binding_hash"):
                if mode == "expired_binding_use":
                    message["timestamp"] = "2099-01-01T00:00:00Z"
                elif mode == "acting_agent_mismatch":
                    message["sender"] = "agent:other"
                break
        if mode == "revoked_binding_use":
            revocation = next((m for m in messages if m.get("message_type") == "SUBJECT_BINDING_REVOKE"), None)
            acting = next((m for m in messages if isinstance(m.get("ext"), dict) and m["ext"].get("subject_binding_hash")), None)
            if revocation:
                if acting is None:
                    acting = copy.deepcopy(revocation)
                    acting["message_id"] = "revoked-binding-use"
                    acting["timestamp"] = "2026-03-01T00:00:10Z"
                    acting["sender"] = "agent:A"
                    acting["message_type"] = "ATTEST_ACTION"
                    acting["ext"] = {
                        "subject_binding_hash": (
                            (revocation.get("payload") or {}).get("binding_hash")
                        )
                    }
                    acting["payload"] = {
                        "action": "use_revoked_binding",
                        "result_hash": "sha256:revoked-binding-result",
                    }
                    acting.pop("signatures", None)
                value["messages"] = [*messages, copy.deepcopy(acting)]
    elif mode == "revoked_identity_key_use":
        revoked = next((m for m in messages if m.get("message_type") == "KEY_REVOKE"), None)
        signed = next((m for m in messages if m.get("signatures")), None)
        if revoked and signed:
            value["messages"] = [*messages, copy.deepcopy(signed)]
    elif mode == "invalid_rotation_cross_signature":
        for message in messages:
            if message.get("message_type") == "KEY_ROTATION":
                (((message.get("payload") or {}).get("cross_signatures") or {}).get("old_signs_new") or {})["sig_b64url"] = "invalid"
                break
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=MODES, required=True)
    args = parser.parse_args()
    calls = 0
    consumer_calls = 0
    for raw_bytes in sys.stdin.buffer:
        raw = raw_bytes.decode("utf-8")
        if not raw.strip():
            continue
        request = json.loads(raw)
        calls += 1
        result = handle_request(request, implementation_kind=("reference_corpus" if args.mode == "reference_subject_with_external_mark" else "external_implementation"))
        operation = request.get("operation")
        if operation == "describe":
            if args.mode == "target_not_declared":
                result["supported_aicp_profiles"] = []
            elif args.mode == "wrong_profile_id":
                result["supported_aicp_profiles"] = [{"profile_id": "AICP-WRONG", "profile_version": "0.1"}]
            elif args.mode == "wrong_profile_version":
                result["supported_aicp_profiles"] = [{"profile_id": "AICP-MEDIATED-BLOCKING", "profile_version": "9.9"}]
            elif args.mode == "unexpected_degradation":
                result["claimed_degraded"] = True
            elif args.mode == "forged_compatibility_mark":
                result["claimed_compatibility_marks"] = ["forged"]
            provenance_fields = {
                "wrong_profile_catalog_digest": "claimed_target_catalog_digest",
                "wrong_suite_digest": "claimed_suite_digest",
                "wrong_input_digest": "claimed_input_digest",
                "wrong_runner_digest": "claimed_runner_digest",
                "wrong_report_schema_digest": "claimed_report_schema_digest",
            }
            if args.mode in provenance_fields:
                result[provenance_fields[args.mode]] = "sha256:" + "0" * 64
        elif operation == "validate_transcript":
            consumer_calls += 1
            if args.mode == "consumer_accepts_every_fixture":
                result = {"accepted": True, "errors": [], "degraded": False, "degraded_reasons": [], "skipped_checks": []}
            elif args.mode == "consumer_rejects_every_fixture":
                result = {"accepted": False, "errors": [{"code": "REJECT_ALL", "message": "rejected"}], "degraded": False, "degraded_reasons": [], "skipped_checks": []}
            elif args.mode == "consumer_missing_fields":
                result = {"accepted": True}
            elif args.mode == "unexpected_degradation":
                result.update({"degraded": True, "degraded_reasons": ["forced"], "skipped_checks": ["forced"]})
            elif args.mode == "hidden_skipped_check":
                result["skipped_checks"] = ["hidden"]
        elif operation == "generate_scenario":
            result = _mutate_generated(args.mode, result, calls)
            if args.mode == "missing_producer_scenario":
                result = {"artifact_kind": "transcript", "scenario_id": "missing", "target": result.get("target"), "messages": []}
            elif args.mode == "wrong_producer_scenario_identity":
                result["scenario_id"] = "duplicate"
        response = {
            "adapter_protocol_version": "1.1",
            "request_id": request["request_id"],
            "operation": request["operation"],
            "success": True,
            "result": result,
        }
        if operation == "validate_transcript" and args.mode == "missing_consumer_case" and consumer_calls == 1:
            continue
        encoded_response = (
            json.dumps(response, ensure_ascii=False) + "\n"
        ).encode("utf-8")
        sys.stdout.buffer.write(encoded_response)
        sys.stdout.buffer.flush()
        if operation == "validate_transcript" and args.mode == "duplicate_consumer_case" and consumer_calls == 1:
            sys.stdout.buffer.write(encoded_response)
            sys.stdout.buffer.flush()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
