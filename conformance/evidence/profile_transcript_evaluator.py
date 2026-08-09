from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
RUNNER_DIR = ROOT / "conformance" / "runner"
REF_PY = ROOT / "reference" / "python"
for path in (RUNNER_DIR, REF_PY):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

from evidence_identifier_rules import (  # noqa: E402
    is_broad_namespaced_identifier,
    is_vendor_or_org_namespaced_identifier,
)
from _runner_context import build_validator  # noqa: E402
from aicp_ref.hashing import message_hash_from_body, object_hash  # noqa: E402
from aicp_ref.signatures import (  # noqa: E402
    signature_verifier_available,
    verify_ed25519,
)
from aicp_ref.validate import validate_message_signatures  # noqa: E402
from producer_suite_semantics import unknown_suite_checks  # noqa: E402
from producer_payload_schema_router import tier1_payload_routes  # noqa: E402


@dataclass(frozen=True)
class TranscriptEvaluation:
    accepted: bool
    errors: tuple[dict[str, str], ...]
    degraded: bool
    degraded_reasons: tuple[str, ...]
    skipped_checks: tuple[str, ...]

    def as_adapter_result(self) -> dict[str, Any]:
        return {
            "accepted": self.accepted,
            "errors": [dict(item) for item in self.errors],
            "degraded": self.degraded,
            "degraded_reasons": list(self.degraded_reasons),
            "skipped_checks": list(self.skipped_checks),
        }


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _message_body(message: dict[str, Any]) -> dict[str, Any]:
    body = dict(message)
    body.pop("message_hash", None)
    body.pop("signatures", None)
    return body


def _parse_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _baseline_keyring() -> dict[str, dict[str, str]]:
    source = _load_json(ROOT / "fixtures/keys/GT_public_keys.json")
    result: dict[str, dict[str, str]] = {}
    for signer, metadata in source.items():
        if not isinstance(signer, str) or not isinstance(metadata, dict):
            continue
        kid = metadata.get("kid")
        public_key = metadata.get("public_key_b64url")
        if isinstance(kid, str) and isinstance(public_key, str):
            result.setdefault(signer, {})[kid] = public_key
    return result


def _collect_object_refs(value: Any) -> list[tuple[str, Any, str]]:
    found: list[tuple[str, Any, str]] = []
    if isinstance(value, dict):
        object_type = value.get("object_type")
        object_value = value.get("object")
        object_digest = value.get("object_hash")
        if (
            isinstance(object_type, str)
            and isinstance(object_value, (dict, list))
            and isinstance(object_digest, str)
        ):
            found.append((object_type, object_value, object_digest))
        for child in value.values():
            found.extend(_collect_object_refs(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_collect_object_refs(child))
    return found


def _suite_context(
    suite_paths: list[str] | tuple[str, ...],
) -> tuple[set[str], list[tuple[str, Any]], set[tuple[str, str]]]:
    enabled: set[str] = set()
    payload_validators: list[tuple[str, Any]] = []
    for relative in suite_paths:
        suite_path = ROOT / relative
        suite = _load_json(suite_path)
        enabled.update(
            str(item.get("test_id"))
            for item in suite.get("checks", [])
            if isinstance(item, dict) and isinstance(item.get("test_id"), str)
        )
        schema_ref = suite.get("payload_schema_ref")
        schema_map = suite.get("payload_schema_map")
        if not isinstance(schema_ref, str) or not isinstance(schema_map, dict):
            continue
        schema_path = ROOT / schema_ref
        schema = _load_json(schema_path)
        check_id = str(suite.get("payload_schema_check_id", "CN-PAYLOAD-SCHEMA-01"))
        for message_type, pointer in schema_map.items():
            if not isinstance(message_type, str) or not isinstance(pointer, str):
                continue
            wrapper = {
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "$defs": schema.get("$defs", {}),
                "$ref": pointer if pointer.startswith("#") else "#" + pointer,
            }
            validator = build_validator(wrapper, schema_path)
            if validator is not None:
                payload_validators.append((f"{message_type}\0{check_id}", validator))
    profiles = {
        (str(item.get("profile_id")), str(item.get("profile_version")))
        for item in _load_json(ROOT / "registry/aicp_profiles.json")
        if isinstance(item, dict)
    }
    return enabled, payload_validators, profiles


def evaluate_profile_transcript(
    messages: list[dict[str, Any]],
    suite_paths: list[str] | tuple[str, ...],
    *,
    simulate_no_crypto: bool = False,
    disabled_checks: frozenset[str] = frozenset(),
    enforce_core_contract_semantics: bool = False,
    enforce_generated_payload_routes: bool | None = None,
) -> TranscriptEvaluation:
    """Evaluate an in-memory transcript without fixture or suite-case identity.

    Error codes are intentionally de-duplicated. The external evidence catalogs
    review exact code observations, while detailed messages remain diagnostic.
    """

    errors: list[dict[str, str]] = []
    seen_codes: set[str] = set()
    degraded_reasons: list[str] = []
    skipped_checks: list[str] = []

    def add(code: str, message: str) -> None:
        if code not in seen_codes:
            seen_codes.add(code)
            errors.append({"code": code, "message": message})

    enabled, payload_validators, registered_profiles = _suite_context(suite_paths)
    generated_payload_routes = (
        enforce_core_contract_semantics
        if enforce_generated_payload_routes is None
        else enforce_generated_payload_routes
    )
    for check_id in unknown_suite_checks(suite_paths):
        add(
            "EVIDENCE_PRODUCER_SUITE_CHECK_UNIMPLEMENTED",
            f"mandatory suite check has no generated-transcript implementation: {check_id}",
        )
    # Core contract objects remain Core contracts even when a neutral scenario
    # is primarily exercising an extension suite.
    if enforce_core_contract_semantics:
        enabled.update({"CT-CONTRACT-SCHEMA-01", "CT-POLICY-CATEGORIES-01"})
    enabled.difference_update(disabled_checks)
    if not messages:
        add("CT-INVARIANTS-01", "transcript has no messages")
        return TranscriptEvaluation(False, tuple(errors), False, (), ())

    core_schema_path = ROOT / "schemas/core/aicp-core-message.schema.json"
    core_validator = build_validator(_load_json(core_schema_path), core_schema_path)
    if core_validator is None:
        return TranscriptEvaluation(
            False,
            ({"code": "CT-SCHEMA-JSONL-01", "message": "jsonschema unavailable"},),
            True,
            ("jsonschema dependency unavailable",),
            ("CT-SCHEMA-JSONL-01",),
        )

    registered_message_types = {
        str(item.get("id"))
        for item in _load_json(ROOT / "registry/message_types.json")
        if isinstance(item, dict)
    }
    sessions: set[str] = set()
    contracts: set[str] = set()
    message_ids: list[str] = []
    for index, message in enumerate(messages):
        if not isinstance(message, dict):
            add("CT-SCHEMA-JSONL-01", f"message {index + 1} is not an object")
            continue
        if list(core_validator.iter_errors(message)):
            add("CT-SCHEMA-JSONL-01", f"message {index + 1} violates the Core envelope schema")
        message_type = message.get("message_type")
        if message_type not in registered_message_types:
            add("CT-MESSAGE-TYPE-REGISTRY-01", f"unregistered message type: {message_type}")
        if generated_payload_routes:
            if "EVIDENCE-GENERATED-PAYLOAD-SCHEMA-01" not in disabled_checks:
                try:
                    route = tier1_payload_routes().get(str(message_type))
                except ValueError as exc:
                    add(
                        "EVIDENCE-GENERATED-PAYLOAD-SCHEMA-01",
                        f"payload route registry is invalid: {exc}",
                    )
                    route = None
                if route is None:
                    add(
                        "EVIDENCE-GENERATED-PAYLOAD-SCHEMA-01",
                        f"{message_type} has no exact AICP v0.1 payload schema route",
                    )
                else:
                    schema_path = ROOT / route.schema_path
                    schema = _load_json(schema_path)
                    wrapper = {
                        "$schema": schema.get("$schema"),
                        "$id": schema.get("$id"),
                        "$defs": schema.get("$defs", {}),
                        "$ref": f"#{route.schema_pointer}",
                    }
                    validator = build_validator(wrapper, schema_path)
                    if validator is None:
                        add(
                            "EVIDENCE-GENERATED-PAYLOAD-SCHEMA-01",
                            "jsonschema unavailable for generated payload routing",
                        )
                    elif list(validator.iter_errors(message.get("payload"))):
                        add(
                            "EVIDENCE-GENERATED-PAYLOAD-SCHEMA-01",
                            f"{message_type} payload violates {route.owning_suite}/"
                            f"{route.check_id} at {route.schema_path}#{route.schema_pointer} "
                            f"for {route.surface_kind}:{route.surface_id}@{route.surface_version}",
                        )
        else:
            for selector, validator in payload_validators:
                expected_type, check_id = selector.split("\0", 1)
                if (
                    check_id not in disabled_checks
                    and message_type == expected_type
                    and list(validator.iter_errors(message.get("payload")))
                ):
                    add(check_id, f"{message_type} payload violates its selected schema")
        session_id = message.get("session_id")
        contract_id = message.get("contract_id")
        message_id = message.get("message_id")
        if isinstance(session_id, str):
            sessions.add(session_id)
        if isinstance(contract_id, str):
            contracts.add(contract_id)
        if not isinstance(contract_id, str) or not contract_id:
            add("CT-CONTRACT-ID-01", "contract_id must be a non-empty string")
        if isinstance(message_id, str):
            message_ids.append(message_id)
        try:
            computed = message_hash_from_body(_message_body(message))
        except Exception as exc:
            add("CT-MESSAGE-HASH-01", f"message hash recomputation failed: {exc}")
        else:
            if message.get("message_hash") != computed:
                add("CT-MESSAGE-HASH-01", "message_hash does not match canonical message body")
        if index:
            previous_hash = messages[index - 1].get("message_hash")
            if not isinstance(message.get("prev_msg_hash"), str) or not message.get(
                "prev_msg_hash"
            ):
                add("CT-PREV-MSG-REQUIRED-01", "non-first message lacks prev_msg_hash")
            elif message.get("prev_msg_hash") != previous_hash:
                add("CT-HASH-CHAIN-01", "prev_msg_hash does not match the previous message")
    if len(sessions) != 1 or len(contracts) != 1 or len(message_ids) != len(
        set(message_ids)
    ):
        add("CT-INVARIANTS-01", "session/contract must be constant and message IDs unique")

    if "CT-CONTRACT-SCHEMA-01" in enabled:
        contract_schema_path = ROOT / "schemas/core/aicp-core-contract.schema.json"
        contract_validator = build_validator(
            _load_json(contract_schema_path), contract_schema_path
        )
        if contract_validator is None:
            return TranscriptEvaluation(
                False,
                ({"code": "CT-CONTRACT-SCHEMA-01", "message": "jsonschema unavailable"},),
                True,
                ("jsonschema dependency unavailable",),
                ("CT-CONTRACT-SCHEMA-01",),
            )
        for message in messages:
            if message.get("message_type") != "CONTRACT_PROPOSE":
                continue
            payload = message.get("payload") if isinstance(message.get("payload"), dict) else {}
            contract = payload.get("contract")
            if not isinstance(contract, dict):
                add("CT-CONTRACT-SCHEMA-01", "payload.contract must be an object")
                continue
            if list(contract_validator.iter_errors(contract)):
                add("CT-CONTRACT-SCHEMA-01", "payload.contract violates the Core contract schema")
            if message.get("contract_id") != contract.get("contract_id"):
                add(
                    "CT-CONTRACT-SCHEMA-01",
                    "envelope.contract_id must equal payload.contract.contract_id",
                )

    if "CT-POLICY-CATEGORIES-01" in enabled:
        registered_categories = {
            str(item.get("id"))
            for item in _load_json(ROOT / "registry/policy_categories.json")
            if isinstance(item, dict)
        }
        for message in messages:
            if message.get("message_type") != "CONTRACT_PROPOSE":
                continue
            contract = ((message.get("payload") or {}).get("contract") or {})
            policies = contract.get("policies") if isinstance(contract, dict) else None
            if policies is None:
                continue
            if not isinstance(policies, list):
                add("CT-POLICY-CATEGORIES-01", "contract.policies must be an array")
                continue
            seen_policy_ids: set[str] = set()
            for policy in policies:
                if not isinstance(policy, dict):
                    add("CT-POLICY-CATEGORIES-01", "contract policy must be an object")
                    continue
                policy_id = policy.get("policy_id")
                category = policy.get("category")
                if not isinstance(policy_id, str) or not policy_id:
                    add("CT-POLICY-CATEGORIES-01", "policy_id must be a non-empty string")
                elif policy_id in seen_policy_ids:
                    add("CT-POLICY-CATEGORIES-01", f"duplicate policy_id: {policy_id}")
                else:
                    seen_policy_ids.add(policy_id)
                if (
                    not isinstance(category, str)
                    or not category
                    or (
                        category not in registered_categories
                        and not is_broad_namespaced_identifier(category)
                    )
                ):
                    add("CT-POLICY-CATEGORIES-01", f"unknown policy category: {category}")

    keyring = _baseline_keyring()
    revoked_kids: set[str] = set()
    crypto_available = signature_verifier_available() and not simulate_no_crypto
    signature_required_types = {"SUBJECT_BINDING_ISSUE", "SUBJECT_BINDING_REVOKE"}
    for message in messages:
        message_type = message.get("message_type")
        payload = message.get("payload") if isinstance(message.get("payload"), dict) else {}
        signatures = message.get("signatures")

        if message_type == "IDENTITY_ANNOUNCE":
            aid_ref = payload.get("aid_ref") if isinstance(payload, dict) else None
            aid_obj = aid_ref.get("object") if isinstance(aid_ref, dict) else None
            if "ID-AID-01" in enabled and isinstance(aid_ref, dict):
                if aid_ref.get("object_type") != "aid" or not isinstance(aid_obj, dict):
                    add("ID-AID-01", "aid_ref must bind an aid object")
                elif aid_ref.get("object_hash") != object_hash("aid", aid_obj):
                    add("ID-AID-01", "aid_ref.object_hash mismatch")
            if "ID-ANN-01" in enabled and isinstance(aid_ref, dict):
                if payload.get("aid_hash") != aid_ref.get("object_hash"):
                    add("ID-ANN-01", "aid_hash does not match aid_ref")
            if isinstance(aid_obj, dict):
                agent_id = aid_obj.get("agent_id")
                for key in aid_obj.get("keys", []) or []:
                    if not isinstance(key, dict) or key.get("status") == "revoked":
                        continue
                    kid = key.get("kid")
                    public_key = key.get("public_key_b64url")
                    if (
                        isinstance(agent_id, str)
                        and isinstance(kid, str)
                        and isinstance(public_key, str)
                    ):
                        keyring.setdefault(agent_id, {})[kid] = public_key

        if message_type == "KEY_ROTATION":
            sender = message.get("sender")
            old_kid = payload.get("old_kid")
            new_key = payload.get("new_key") if isinstance(payload.get("new_key"), dict) else {}
            cross = payload.get("cross_signatures") if isinstance(payload.get("cross_signatures"), dict) else {}
            old_signature = cross.get("old_signs_new") if isinstance(cross.get("old_signs_new"), dict) else {}
            new_signature = cross.get("new_signs_old") if isinstance(cross.get("new_signs_old"), dict) else {}
            new_material = {
                "kid": new_key.get("kid"),
                "alg": new_key.get("alg"),
                "public_key_b64url": new_key.get("public_key_b64url"),
            }
            expected_new_hash = object_hash("key", new_material)
            expected_old_hash = object_hash("kid", {"old_kid": old_kid})
            old_public = (
                keyring.get(str(sender), {}).get(str(old_kid))
                if isinstance(sender, str) and isinstance(old_kid, str)
                else None
            )
            new_public = new_key.get("public_key_b64url")
            hashes_ok = (
                old_signature.get("object_hash") == expected_new_hash
                and new_signature.get("object_hash") == expected_old_hash
            )
            signatures_ok = (
                crypto_available
                and isinstance(old_public, str)
                and isinstance(new_public, str)
                and verify_ed25519(
                    old_public,
                    str(old_signature.get("sig_b64url", "")),
                    str(old_signature.get("object_hash", "")),
                )
                and verify_ed25519(
                    new_public,
                    str(new_signature.get("sig_b64url", "")),
                    str(new_signature.get("object_hash", "")),
                )
            )
            if "ID-ROT-01" in enabled and (not hashes_ok or not signatures_ok):
                add("ID-ROT-01", "key rotation cross-signatures are invalid")
            if hashes_ok and signatures_ok and isinstance(sender, str):
                new_kid = new_key.get("kid")
                if isinstance(new_kid, str) and isinstance(new_public, str):
                    keyring.setdefault(sender, {})[new_kid] = new_public

        if message_type == "KEY_REVOKE":
            target_kid = payload.get("target_kid")
            if isinstance(target_kid, str):
                revoked_kids.add(target_kid)
        elif isinstance(signatures, list):
            if any(
                isinstance(signature, dict)
                and signature.get("kid") in revoked_kids
                for signature in signatures
            ):
                add("ID-REVOKE-01", "a revoked identity key was reused")

        if message_type in signature_required_types and (
            not isinstance(signatures, list) or not signatures
        ):
            add("DI-SIGNED-01", f"{message_type} requires a signature")
        if signatures:
            if not crypto_available:
                if "Ed25519 verifier unavailable" not in degraded_reasons:
                    degraded_reasons.append("Ed25519 verifier unavailable")
                if "CT-SIGNATURE-VERIFY-01" not in skipped_checks:
                    skipped_checks.append("CT-SIGNATURE-VERIFY-01")
            else:
                for issue in validate_message_signatures(
                    message,
                    keyring,
                    verify_crypto=True,
                ):
                    code = (
                        "CT-SIGNATURE-HASH-01"
                        if issue["code"] == "object_hash_mismatch"
                        else "CT-SIGNATURE-STRUCTURE-01"
                        if issue["code"] == "object_type_mismatch"
                        else "CT-SIGNATURE-VERIFY-01"
                    )
                    add(code, issue["message"])

    if "OR-OBJECT-HASH-01" in enabled:
        for message in messages:
            for object_type, value, digest in _collect_object_refs(message.get("payload")):
                if object_hash(object_type, value) != digest:
                    add("OR-OBJECT-HASH-01", "object reference hash mismatch")

    if "PE-REASON-CODES-01" in enabled or "PE-CONTEXT-HASH-01" in enabled:
        reason_codes = {
            str(item.get("id"))
            for item in _load_json(ROOT / "registry/policy_reason_codes.json")
            if isinstance(item, dict)
        }
        for message in messages:
            payload = message.get("payload") if isinstance(message.get("payload"), dict) else {}
            if (
                "PE-REASON-CODES-01" in enabled
                and message.get("message_type") == "POLICY_EVAL_RESULT"
            ):
                decision = payload.get("policy_decision") if isinstance(payload.get("policy_decision"), dict) else {}
                if any(
                    code not in reason_codes
                    and not is_vendor_or_org_namespaced_identifier(code)
                    for code in decision.get("reason_codes", []) or []
                ):
                    add("PE-REASON-CODES-01", "policy decision contains an unknown reason code")
            if (
                "PE-CONTEXT-HASH-01" in enabled
                and message.get("message_type") == "POLICY_EVAL_REQUEST"
            ):
                context = payload.get("evaluation_context") if isinstance(payload.get("evaluation_context"), dict) else {}
                if "context_hash" in context:
                    stored = context.get("context_hash")
                    raw = dict(context)
                    raw.pop("context_hash", None)
                    if stored != object_hash("evaluation_context", raw):
                        add("PE-CONTEXT-HASH-01", "policy evaluation context hash mismatch")

    _validate_capneg(messages, enabled, registered_profiles, add)
    _validate_resume(messages, enabled, add)
    _validate_enforcement(messages, enabled, add)
    _validate_delegated_identity(messages, enabled, add)

    degraded = bool(degraded_reasons or skipped_checks)
    return TranscriptEvaluation(
        accepted=not errors and not degraded,
        errors=tuple(errors),
        degraded=degraded,
        degraded_reasons=tuple(sorted(set(degraded_reasons))),
        skipped_checks=tuple(sorted(set(skipped_checks))),
    )


def _validate_capneg(
    messages: list[dict[str, Any]],
    enabled: set[str],
    registered_profiles: set[tuple[str, str]],
    add: Any,
) -> None:
    if not any(code.startswith("CN-") for code in enabled):
        return
    declares: dict[str, dict[str, Any]] = {}
    proposals: dict[str, dict[str, Any]] = {}
    accepted_extensions: dict[str, set[str]] = {}
    accepted_indices: list[int] = []
    proposed_result: dict[str, Any] | None = None
    proposed_hash: str | None = None
    profile_entries = {
        (str(item.get("profile_id")), str(item.get("profile_version"))): item
        for item in _load_json(ROOT / "registry/aicp_profiles.json")
        if isinstance(item, dict)
    }
    reason_codes = {
        str(item.get("id"))
        for item in _load_json(ROOT / "registry/capneg_reason_codes.json")
        if isinstance(item, dict)
    }
    privacy_modes = {
        str(item.get("id"))
        for item in _load_json(ROOT / "registry/privacy_modes.json")
        if isinstance(item, dict)
    }
    transport_bindings = {
        str(item.get("id")): item
        for item in _load_json(ROOT / "registry/transport_bindings.json")
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    deprecated_bindings = {
        binding_id: str(item.get("canonical_id"))
        for binding_id, item in transport_bindings.items()
        if item.get("status") == "deprecated" and isinstance(item.get("canonical_id"), str)
    }
    channel_property_ids = {
        str(item.get("id"))
        for item in _load_json(ROOT / "registry/channel_properties.json")
        if isinstance(item, dict)
    }

    def canonical_bindings(value: Any) -> set[str]:
        if not isinstance(value, list):
            return set()
        return {
            deprecated_bindings.get(item, item)
            for item in value
            if isinstance(item, str) and item
        }
    for index, message in enumerate(messages):
        payload = message.get("payload") if isinstance(message.get("payload"), dict) else {}
        message_type = message.get("message_type")
        if message_type == "CAPABILITIES_DECLARE":
            party = payload.get("party_id")
            if isinstance(party, str):
                declares[party] = payload
            if "CN-PRIVACY-MODES-01" in enabled:
                for mode in payload.get("supported_privacy_modes", []) or []:
                    if mode not in privacy_modes and not is_vendor_or_org_namespaced_identifier(mode):
                        add("CN-PRIVACY-MODES-01", "declaration contains an unknown privacy mode")
        elif message_type == "CAPABILITIES_PROPOSE":
            result = payload.get("negotiation_result") if isinstance(payload.get("negotiation_result"), dict) else {}
            negotiation_id = result.get("negotiation_id")
            if isinstance(negotiation_id, str):
                proposals[negotiation_id] = result
            if proposed_result is None and result:
                proposed_result = result
                proposed_hash = object_hash("capneg.negotiation_result", result)
            profile = (result.get("selected") or {}).get("aicp_profile")
            selected = result.get("selected") if isinstance(result.get("selected"), dict) else {}
            if "CN-PRIVACY-MODES-01" in enabled:
                selected_privacy = selected.get("privacy_mode")
                if (
                    selected_privacy is not None
                    and selected_privacy not in privacy_modes
                    and not is_vendor_or_org_namespaced_identifier(selected_privacy)
                ):
                    add("CN-PRIVACY-MODES-01", "selected privacy mode is not registered or namespaced")
            participants = result.get("participants") if isinstance(result.get("participants"), list) else []
            selected_binding = selected.get("binding")
            if "CN-BINDINGS-01" in enabled and selected_binding is not None:
                binding_entry = transport_bindings.get(str(selected_binding))
                if not isinstance(selected_binding, str) or not selected_binding:
                    add("CN-BINDINGS-01", "selected.binding must be a non-empty string")
                elif binding_entry is None:
                    add("CN-BINDINGS-01", "selected transport binding is unregistered")
                elif binding_entry.get("status") == "deprecated":
                    add("CN-BINDINGS-01", "selected transport binding is deprecated")
                participant_sets = [
                    canonical_bindings(declares[str(participant)].get("bindings"))
                    for participant in participants
                    if str(participant) in declares
                ]
                if participant_sets and selected_binding not in set.intersection(*participant_sets):
                    add("CN-BINDINGS-01", "selected binding is not mutually declared")
            selected_properties = selected.get("channel_properties")
            if "CN-CHANNEL-PROPERTIES-01" in enabled and selected_properties is not None:
                if not isinstance(selected_properties, dict):
                    add("CN-CHANNEL-PROPERTIES-01", "selected channel_properties must be an object")
                else:
                    for key in selected_properties:
                        if key not in channel_property_ids and not str(key).startswith("vendor:/"):
                            add("CN-CHANNEL-PROPERTIES-01", "selected channel property is unregistered")
                    for participant in participants:
                        declared = declares.get(str(participant))
                        if not isinstance(declared, dict):
                            continue
                        supported = declared.get("supported_channel_properties")
                        if not isinstance(supported, dict):
                            add("CN-CHANNEL-PROPERTIES-01", "participant lacks channel-property support")
                            continue
                        for key, value in selected_properties.items():
                            if str(key).startswith("vendor:/"):
                                continue
                            rule = supported.get(key)
                            if key == "CP-REPLAY-WINDOW-0.1":
                                if not isinstance(value, int) or value < 0 or not isinstance(rule, dict):
                                    add("CN-CHANNEL-PROPERTIES-01", "replay window selection/range is invalid")
                                    continue
                                minimum, maximum = rule.get("min"), rule.get("max")
                                if (
                                    not isinstance(minimum, int)
                                    or not isinstance(maximum, int)
                                    or minimum < 0
                                    or maximum < minimum
                                    or not minimum <= value <= maximum
                                ):
                                    add("CN-CHANNEL-PROPERTIES-01", "replay window violates participant range")
                            elif not isinstance(rule, list) or value not in rule:
                                add("CN-CHANNEL-PROPERTIES-01", "channel property is not supported by every participant")
            if isinstance(profile, dict):
                exact = (str(profile.get("profile_id")), str(profile.get("profile_version")))
                participants = result.get("participants") if isinstance(result.get("participants"), list) else []
                if exact not in registered_profiles:
                    add("CN-AICP-PROFILE-NEGOTIATION-01", "selected profile is not registered")
                for participant in participants:
                    declared = declares.get(str(participant))
                    if not isinstance(declared, dict):
                        continue
                    supported = {
                        (str(item.get("profile_id")), str(item.get("profile_version")))
                        for item in declared.get("supported_aicp_profiles", []) or []
                        if isinstance(item, dict)
                    }
                    required = {
                        (str(item.get("profile_id")), str(item.get("profile_version")))
                        for item in declared.get("required_aicp_profiles", []) or []
                        if isinstance(item, dict)
                    }
                    if (supported and exact not in supported) or (required and exact not in required):
                        add("CN-AICP-PROFILE-NEGOTIATION-01", "participant declarations do not permit selected profile")
                if "CN-AUTHENTICATED-CRYPTO-01" in enabled:
                    required_crypto = {
                        str(item)
                        for item in profile_entries.get(exact, {}).get(
                            "required_crypto_profiles", []
                        )
                        if isinstance(item, str)
                    }
                    selected_crypto = {
                        str(item)
                        for item in (result.get("selected") or {}).get(
                            "crypto_profile", []
                        )
                        if isinstance(item, str)
                    }
                    if required_crypto - selected_crypto:
                        add(
                            "CN-AUTHENTICATED-CRYPTO-01",
                            "selected crypto profile omits an exact profile requirement",
                        )
                    for participant in participants:
                        declared = declares.get(str(participant), {})
                        supported_crypto = {
                            str(item)
                            for item in declared.get("supported_profiles", []) or []
                            if isinstance(item, str)
                        }
                        if required_crypto - supported_crypto:
                            add(
                                "CN-AUTHENTICATED-CRYPTO-01",
                                "participant does not declare the profile-required crypto",
                            )
            negotiation_id = result.get("negotiation_id")
            required_extensions = (result.get("selected") or {}).get("required_extensions")
            if isinstance(negotiation_id, str) and isinstance(required_extensions, list):
                prior = accepted_extensions.get(negotiation_id)
                proposed = {str(item) for item in required_extensions if isinstance(item, str)}
                if prior is not None and not prior.issubset(proposed):
                    add("CN-DOWNGRADE-01", "proposal removes an accepted required extension")
        elif message_type == "CAPABILITIES_ACCEPT":
            accepted_indices.append(index)
            result = payload.get("negotiation_result") if isinstance(payload.get("negotiation_result"), dict) else {}
            negotiation_id = payload.get("negotiation_id") or result.get("negotiation_id")
            required_extensions = (result.get("selected") or {}).get("required_extensions")
            if isinstance(negotiation_id, str) and isinstance(required_extensions, list):
                accepted_extensions[negotiation_id] = {
                    str(item) for item in required_extensions if isinstance(item, str)
                }
            if proposed_hash and isinstance(payload.get("negotiation_result_hash"), str):
                if payload.get("negotiation_result_hash") != proposed_hash:
                    add("CN-NEGRESULT-HASH-01", "accepted negotiation hash mismatch")
            result_selected = result.get("selected") if isinstance(result.get("selected"), dict) else {}
            selected_privacy = result_selected.get("privacy_mode")
            if (
                "CN-PRIVACY-MODES-01" in enabled
                and selected_privacy is not None
                and selected_privacy not in privacy_modes
                and not is_vendor_or_org_namespaced_identifier(selected_privacy)
            ):
                add("CN-PRIVACY-MODES-01", "accepted privacy mode is not registered or namespaced")
        elif message_type == "CAPABILITIES_REJECT":
            negotiation_id = payload.get("negotiation_id")
            proposal = proposals.get(str(negotiation_id), {})
            if "CN-REASON-CODES-01" in enabled and payload.get("reason_code") not in reason_codes:
                add("CN-REASON-CODES-01", "CAPNEG rejection reason is unregistered")
            profile = (proposal.get("selected") or {}).get("aicp_profile")
            if isinstance(profile, dict):
                exact = (str(profile.get("profile_id")), str(profile.get("profile_version")))
                unsupported = False
                unacceptable = False
                for participant in proposal.get("participants", []) or []:
                    declared = declares.get(str(participant), {})
                    supported = {
                        (str(item.get("profile_id")), str(item.get("profile_version")))
                        for item in declared.get("supported_aicp_profiles", []) or []
                        if isinstance(item, dict)
                    }
                    required = {
                        (str(item.get("profile_id")), str(item.get("profile_version")))
                        for item in declared.get("required_aicp_profiles", []) or []
                        if isinstance(item, dict)
                    }
                    unsupported = unsupported or bool(supported and exact not in supported)
                    unacceptable = unacceptable or bool(required and exact not in required)
                reason = payload.get("reason_code")
                if unsupported and reason != "REQUIRED_PROFILE_UNSUPPORTED":
                    add("CN-PROFILE-REJECT-SEMANTICS-01", "unsupported profile rejection reason is incorrect")
                elif unacceptable and reason not in {"PROFILE_NOT_ACCEPTABLE", "DOWNGRADE_NOT_ALLOWED"}:
                    add("CN-PROFILE-REJECT-SEMANTICS-01", "unacceptable profile rejection reason is incorrect")

    if "CN-CONTRACT-BIND-01" in enabled and accepted_indices and proposed_hash:
        first_accept = accepted_indices[0]
        expected_selected = (proposed_result or {}).get("selected")
        for index, message in enumerate(messages):
            if index <= first_accept or message.get("message_type") != "CONTRACT_PROPOSE":
                continue
            contract = ((message.get("payload") or {}).get("contract") or {})
            capneg = ((contract.get("ext") or {}).get("capneg")) if isinstance(contract, dict) else None
            if not isinstance(capneg, dict):
                add("CN-CONTRACT-BIND-01", "contract lacks accepted CAPNEG binding")
            elif capneg.get("negotiation_result_hash") != proposed_hash or (
                "selected" in capneg and capneg.get("selected") != expected_selected
            ):
                add("CN-CONTRACT-BIND-01", "contract CAPNEG binding is stale or mismatched")


def _validate_resume(messages: list[dict[str, Any]], enabled: set[str], add: Any) -> None:
    if not ({"RS-RESUME-MATCH-01", "RS-ACTIONS-01", "RS-LOOP-01"} & enabled):
        return
    registered_actions = {
        str(item.get("id"))
        for item in _load_json(ROOT / "registry/alert_recommended_actions.json")
        if isinstance(item, dict)
    }
    pairs: list[tuple[dict[str, Any], dict[str, Any] | None]] = []
    for index, message in enumerate(messages):
        if message.get("message_type") != "RESUME_REQUEST":
            continue
        request = message.get("payload") if isinstance(message.get("payload"), dict) else {}
        response = next(
            (
                candidate.get("payload")
                for candidate in messages[index + 1 :]
                if candidate.get("message_type") == "RESUME_RESPONSE"
                and isinstance(candidate.get("payload"), dict)
            ),
            None,
        )
        pairs.append((request, response))
        if response is None:
            add("RS-RESUME-MATCH-01", "resume request has no response")
            continue
        if response.get("resume_id") != request.get("resume_id") or response.get(
            "session_id"
        ) != request.get("session_id"):
            add("RS-RESUME-MATCH-01", "resume response correlation mismatch")
        status = response.get("status")
        current = response.get("current_head_hash")
        last_seen = request.get("last_seen_message_hash")
        if status == "OK" and current != last_seen:
            add("RS-RESUME-MATCH-01", "IN_SYNC resume head mismatch")
        if status == "NEEDS_RESYNC" and current == last_seen:
            add("RS-RESUME-MATCH-01", "NEEDS_RESYNC did not advance the head")
        if "RS-ACTIONS-01" in enabled:
            for action in response.get("recommended_actions", []) or []:
                if action not in registered_actions:
                    add("RS-ACTIONS-01", "resume response contains an unknown recommended action")
    streak = 0
    anchor: tuple[Any, Any, Any] | None = None
    for request, response in pairs:
        if isinstance(response, dict) and response.get("status") == "NEEDS_RESYNC":
            triple = (
                request.get("session_id"),
                request.get("last_seen_message_hash"),
                response.get("current_head_hash"),
            )
            streak = streak + 1 if triple == anchor else 1
            anchor = triple
            if streak >= 3:
                add("RS-LOOP-01", "repeated NEEDS_RESYNC loop made no progress")
        else:
            streak = 0
            anchor = None


def _validate_enforcement(
    messages: list[dict[str, Any]], enabled: set[str], add: Any
) -> None:
    if not ({"ENF-GATE-01", "ENF-SANCTION-CODES-01", "ENF-AUTH-01"} & enabled):
        return
    sanction_codes = {
        str(item.get("id"))
        for item in _load_json(ROOT / "registry/enforcement_sanction_codes.json")
        if isinstance(item, dict)
    }
    contract = next(
        (
            (message.get("payload") or {}).get("contract")
            for message in messages
            if message.get("message_type") == "CONTRACT_PROPOSE"
        ),
        None,
    )
    configuration = None
    if isinstance(contract, dict):
        configuration = (contract.get("ext") or {}).get("enforcement")
        if configuration is None:
            configuration = (contract.get("extensions") or {}).get("EXT-ENFORCEMENT")
    verdicts = {
        str(message.get("message_id")): message
        for message in messages
        if message.get("message_type") == "ENFORCEMENT_VERDICT"
    }
    if "ENF-SANCTION-CODES-01" in enabled:
        for verdict in verdicts.values():
            payload = verdict.get("payload") if isinstance(verdict.get("payload"), dict) else {}
            for sanction in payload.get("sanctions", []) or []:
                code = sanction.get("code") if isinstance(sanction, dict) else None
                if (
                    not isinstance(code, str)
                    or (
                        code not in sanction_codes
                        and not is_broad_namespaced_identifier(code)
                    )
                ):
                    add("ENF-SANCTION-CODES-01", "enforcement sanction code is unregistered")
    if isinstance(configuration, dict):
        allowed = configuration.get("enforcers")
        if isinstance(allowed, list) and allowed:
            for verdict in verdicts.values():
                if verdict.get("sender") not in allowed:
                    add("ENF-AUTH-01", "enforcement verdict sender is unauthorized")
        if configuration.get("mode") == "blocking":
            gated = configuration.get("gated_message_types")
            for delivery in messages:
                if delivery.get("message_type") != "CONTENT_DELIVER":
                    continue
                payload = delivery.get("payload") if isinstance(delivery.get("payload"), dict) else {}
                verdict = verdicts.get(str(payload.get("verdict_message_id")))
                if not isinstance(verdict, dict):
                    add("ENF-GATE-01", "content delivery lacks a referenced verdict")
                    continue
                verdict_payload = verdict.get("payload") if isinstance(verdict.get("payload"), dict) else {}
                original = payload.get("original_message") if isinstance(payload.get("original_message"), dict) else {}
                original_hash = payload.get("original_message_hash")
                if (
                    verdict_payload.get("decision") != "ALLOW"
                    or verdict_payload.get("target_message_hash") != original_hash
                    or original.get("message_hash") != original_hash
                    or (
                        isinstance(gated, list)
                        and original.get("message_type") not in gated
                    )
                ):
                    add("ENF-GATE-01", "content delivery is not bound to an ALLOW verdict")


def _validate_delegated_identity(
    messages: list[dict[str, Any]], enabled: set[str], add: Any
) -> None:
    if not any(code.startswith("DI-") for code in enabled):
        return
    issued: dict[str, dict[str, Any]] = {}
    revoked: dict[str, datetime] = {}
    for message in messages:
        message_type = message.get("message_type")
        payload = message.get("payload") if isinstance(message.get("payload"), dict) else {}
        if message_type == "SUBJECT_BINDING_ISSUE":
            binding_hash = payload.get("binding_hash")
            binding_ref = payload.get("binding_ref") if isinstance(payload.get("binding_ref"), dict) else {}
            binding = binding_ref.get("object")
            if (
                binding_ref.get("object_type") != "subject_binding"
                or not isinstance(binding, dict)
                or binding_ref.get("object_hash") != object_hash("subject_binding", binding)
            ):
                add("DI-OBJ-01", "subject binding object reference is invalid")
            if payload.get("binding_hash") != binding_ref.get("object_hash") or (
                isinstance(binding, dict)
                and binding.get("issuer") != message.get("sender")
            ):
                add("DI-ISSUE-01", "binding hash or issuer is invalid")
            if isinstance(binding_hash, str):
                issued[binding_hash] = binding if isinstance(binding, dict) else {}
        elif message_type == "SUBJECT_BINDING_REVOKE":
            effective = _parse_datetime(payload.get("effective_at"))
            binding_hash = payload.get("binding_hash")
            if isinstance(binding_hash, str) and effective is not None:
                revoked[binding_hash] = effective

        extension = message.get("ext") if isinstance(message.get("ext"), dict) else {}
        binding_hash = extension.get("subject_binding_hash")
        if not isinstance(binding_hash, str):
            continue
        binding = issued.get(binding_hash)
        if not isinstance(binding, dict):
            add("DI-ACT-01", "acting message references no prior binding")
            continue
        if binding.get("agent_id") != message.get("sender"):
            add("DI-ACT-01", "acting agent differs from binding agent")
        message_time = _parse_datetime(message.get("timestamp"))
        expiry = _parse_datetime(binding.get("expires_at"))
        if message_time is None or expiry is None or message_time > expiry:
            add("DI-EXPIRY-01", "binding is expired or has invalid timestamps")
        effective = revoked.get(binding_hash)
        if effective is not None and message_time is not None and effective <= message_time:
            add("DI-REVOKE-01", "revoked binding was reused")
