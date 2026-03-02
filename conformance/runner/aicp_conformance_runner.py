#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from jsonschema import Draft202012Validator
except Exception:  # pragma: no cover - environment dependent
    Draft202012Validator = None

try:
    from referencing import Registry, Resource
except Exception:  # pragma: no cover - environment dependent
    Registry = None
    Resource = None

ROOT = Path(__file__).resolve().parents[2]
REF_PY = ROOT / "reference/python"
if str(REF_PY) not in sys.path:
    sys.path.insert(0, str(REF_PY))

from aicp_ref.hashing import message_hash_from_body, object_hash  # noqa: E402
from aicp_ref.jcs import canonicalize_json  # noqa: E402
from aicp_ref.signatures import signature_verifier_available, verify_ed25519  # noqa: E402


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def add_failure(failures: list[dict[str, Any]], test_id: str, message: str, file: str, line: int | None = None) -> None:
    failures.append({"test_id": test_id, "message": message, "file": file, "line": line})

def _collect_refs(node: Any) -> list[str]:
    refs: list[str] = []
    if isinstance(node, dict):
        ref = node.get("$ref")
        if isinstance(ref, str):
            refs.append(ref)
        for v in node.values():
            refs.extend(_collect_refs(v))
    elif isinstance(node, list):
        for v in node:
            refs.extend(_collect_refs(v))
    return refs


def _schema_aliases(schema: dict[str, Any], schema_path: Path) -> set[str]:
    aliases = {schema_path.resolve().as_uri()}
    schema_id = schema.get("$id")
    if isinstance(schema_id, str) and schema_id:
        aliases.add(schema_id)
    for legacy in schema.get("x-legacy-ids", []):
        if isinstance(legacy, str) and legacy:
            aliases.add(legacy)
    return aliases


def _core_schema_resources() -> dict[str, Any]:
    if Resource is None:
        return {}
    core_path = ROOT / "schemas/core/aicp-core-message.schema.json"
    core_schema = load_json(core_path)
    resource = Resource.from_contents(core_schema)
    return {alias: resource for alias in _schema_aliases(core_schema, core_path)}


def _build_validator(schema: dict[str, Any], schema_path: Path) -> Any:
    if Draft202012Validator is None:
        return None

    remote_refs = {
        ref for ref in _collect_refs(schema)
        if ref.startswith("http://") or ref.startswith("https://")
    }

    if Registry is None or Resource is None:
        if remote_refs:
            raise ValueError("Remote schema retrieval is disabled; add local mapping or replace $ref with aicp:.")
        return Draft202012Validator(schema)

    resources = _core_schema_resources()
    schema_resource = Resource.from_contents(schema)
    for alias in _schema_aliases(schema, schema_path):
        resources[alias] = schema_resource

    allowed_remote = {u for u in resources if u.startswith("http://") or u.startswith("https://")}
    unresolved = sorted(remote_refs - allowed_remote)
    if unresolved:
        raise ValueError(
            "Remote schema retrieval is disabled; add local mapping or replace $ref with aicp:. "
            f"Unmapped refs: {', '.join(unresolved)}"
        )

    registry = Registry().with_resources(resources.items())
    return Draft202012Validator(schema, registry=registry)


def _normalize_pointer(pointer: str) -> str:
    if pointer.startswith("#"):
        pointer = pointer[1:]
    if pointer == "":
        return ""
    if not pointer.startswith("/"):
        raise ValueError(f"Invalid JSON pointer format: {pointer}")
    return pointer


def _resolve_json_pointer(doc: dict[str, Any], pointer: str) -> Any:
    pointer = _normalize_pointer(pointer)
    if pointer == "":
        return doc
    cur: Any = doc
    for raw in pointer.lstrip("/").split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(cur, dict):
            cur = cur[token]
        elif isinstance(cur, list):
            cur = cur[int(token)]
        else:
            raise KeyError(token)
    return cur


def _validate_payload_schema(
    msg: dict[str, Any],
    line_no: int,
    rel_file: str,
    t_failures: list[dict[str, Any]],
    payload_schema: dict[str, Any] | None,
    payload_schema_map: dict[str, str] | None,
    payload_schema_check_id: str,
    enabled_checks: set[str],
) -> None:
    if payload_schema is None or payload_schema_map is None or Draft202012Validator is None:
        return
    if payload_schema_check_id not in enabled_checks:
        return

    mtype = msg.get("message_type")
    schema_pointer = payload_schema_map.get(mtype)
    if not schema_pointer:
        return

    try:
        pointer = _normalize_pointer(schema_pointer)
        _resolve_json_pointer(payload_schema, pointer)
        wrapper = {
            "$schema": payload_schema.get("$schema"),
            "$id": payload_schema.get("$id"),
            "$ref": f"#{pointer}" if pointer else "#",
            "$defs": payload_schema.get("$defs", {}),
        }
        validator = Draft202012Validator(wrapper)
    except Exception as exc:
        add_failure(t_failures, payload_schema_check_id, f"invalid payload schema configuration for {mtype}: {exc}", rel_file, line_no)
        return

    payload = msg.get("payload")
    for err in sorted(validator.iter_errors(payload), key=lambda e: list(e.path)):
        add_failure(t_failures, payload_schema_check_id, err.message, rel_file, line_no)


def _collect_object_hash_triples(value: Any) -> list[tuple[str, Any, str]]:
    found: list[tuple[str, Any, str]] = []
    if isinstance(value, dict):
        if {"object_type", "object", "object_hash"}.issubset(value.keys()):
            if isinstance(value.get("object_type"), str) and isinstance(value.get("object_hash"), str):
                found.append((value["object_type"], value.get("object"), value["object_hash"]))
        for v in value.values():
            found.extend(_collect_object_hash_triples(v))
    elif isinstance(value, list):
        for v in value:
            found.extend(_collect_object_hash_triples(v))
    return found


def _message_body_without_hash_and_signatures(message: dict[str, Any]) -> dict[str, Any]:
    body = dict(message)
    body.pop("message_hash", None)
    body.pop("signatures", None)
    return body


def _baseline_keyring(key_map: dict[str, Any]) -> dict[str, dict[str, str]]:
    keyring: dict[str, dict[str, str]] = {}
    for signer, meta in key_map.items():
        if not isinstance(meta, dict):
            continue
        kid = meta.get("kid")
        public_key = meta.get("public_key_b64url")
        if isinstance(signer, str) and isinstance(kid, str) and isinstance(public_key, str):
            keyring.setdefault(signer, {})[kid] = public_key
    return keyring


def _is_namespaced_identifier(value: Any) -> bool:
    return isinstance(value, str) and (value.startswith("vendor:") or value.startswith("org:"))


def _has_resolvable_evidence_ref(evidence_refs: Any, prior_message_ids: set[str], prior_message_hashes: set[str], prior_payload_object_hashes: set[str]) -> bool:
    if not isinstance(evidence_refs, list):
        return False
    for ref in evidence_refs:
        if not isinstance(ref, str) or not ref:
            continue
        if ref.startswith("msgid:") and ref[len("msgid:"):] in prior_message_ids:
            return True
        if ref.startswith("msghash:") and ref[len("msghash:"):] in prior_message_hashes:
            return True
        if ref.startswith("objhash:") and ref[len("objhash:"):] in prior_payload_object_hashes:
            return True
    return False


def _parse_iso_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _evaluate_transcript_expectations(
    transcript: dict[str, Any], transcript_failures: list[dict[str, Any]], rel_file: str
) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    expect_pass = transcript.get("expect_pass", True)
    expected_failures = transcript.get("expected_failures", [])

    if expect_pass:
        errors.extend(transcript_failures)
        return errors

    expected_map = {e["test_id"]: int(e.get("min_count", 1)) for e in expected_failures}
    counts: dict[str, int] = {}
    for f in transcript_failures:
        counts[f["test_id"]] = counts.get(f["test_id"], 0) + 1
        if f["test_id"] not in expected_map:
            errors.append(f)

    for test_id, min_count in expected_map.items():
        if counts.get(test_id, 0) < min_count:
            add_failure(errors, test_id, f"expected failure missing or below min_count={min_count}", rel_file, None)

    return errors


def _run_binding_suite(suite: dict[str, Any], schema: dict[str, Any] | None) -> dict[str, Any]:
    enabled_checks = {c.get("test_id") for c in suite.get("checks", [])}
    case_validator = _build_validator(schema, ROOT / suite["schema_ref"]) if schema is not None else None
    core_schema_path = ROOT / "schemas/core/aicp-core-message.schema.json"
    core_schema = load_json(core_schema_path)
    core_validator = _build_validator(core_schema, core_schema_path)
    can_verify_signatures = signature_verifier_available()
    key_map = load_json(ROOT / "fixtures/keys/GT_public_keys.json")
    registered_message_types = {e.get("id") for e in load_json(ROOT / "registry/message_types.json")}

    failures: list[dict[str, Any]] = []

    for rel_case in suite.get("cases", []):
        case_path = ROOT / rel_case
        try:
            case_obj = load_json(case_path)
        except Exception as exc:
            add_failure(failures, "TB-CASE-JSON-01", f"invalid JSON case file: {exc}", rel_case, None)
            continue

        if case_validator is not None:
            for err in sorted(case_validator.iter_errors(case_obj), key=lambda e: list(e.path)):
                add_failure(failures, "TB-SCHEMA-01", err.message, rel_case, None)

        msg = (
            (case_obj.get("mcp_request") or {})
            .get("params", {})
            .get("arguments", {})
            .get("message")
        )
        if not isinstance(msg, dict):
            continue

        if core_validator is not None:
            for err in sorted(core_validator.iter_errors(msg), key=lambda e: list(e.path)):
                add_failure(failures, "TB-EMBEDDED-MESSAGE-SCHEMA-01", err.message, rel_case, None)

        if "CT-MESSAGE-TYPE-REGISTRY-01" in enabled_checks:
            mtype = msg.get("message_type")
            if mtype not in registered_message_types:
                add_failure(failures, "CT-MESSAGE-TYPE-REGISTRY-01", f"unregistered message_type '{mtype}'", rel_case, None)

        stored_hash = msg.get("message_hash")
        if stored_hash is not None:
            try:
                computed_hash = message_hash_from_body(_message_body_without_hash_and_signatures(msg))
            except Exception as exc:
                add_failure(failures, "TB-EMBEDDED-MESSAGE-HASH-01", f"hash recompute error: {exc}", rel_case, None)
            else:
                if computed_hash != stored_hash:
                    add_failure(
                        failures,
                        "TB-EMBEDDED-MESSAGE-HASH-01",
                        f"embedded message_hash mismatch (expected {stored_hash}, got {computed_hash})",
                        rel_case,
                        None,
                    )

        if can_verify_signatures:
            for sig in msg.get("signatures", []) or []:
                signer = sig.get("signer")
                key = key_map.get(signer)
                if not key:
                    add_failure(failures, "TB-EMBEDDED-SIGNATURE-VERIFY-01", f"missing public key for signer {signer}", rel_case, None)
                    continue
                if not verify_ed25519(key.get("public_key_b64url", ""), sig.get("sig_b64url", ""), sig.get("object_hash", "")):
                    add_failure(failures, "TB-EMBEDDED-SIGNATURE-VERIFY-01", "embedded signature verification failed", rel_case, None)

    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    passed = not failures
    suite_mark = suite.get("compatibility_mark")
    marks = [suite_mark] if passed and isinstance(suite_mark, str) else (["AICP-BIND-MCP-0.1"] if passed else [])
    return {
        "aicp_version": version,
        "suite_id": suite["suite_id"],
        "suite_version": suite["suite_version"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "failures": failures,
        "compatibility_marks": marks,
        "degraded": False,
        "degraded_reasons": [],
        "skipped_checks": [],
    }


def run_suite(suite_path: Path) -> dict[str, Any]:
    suite = load_json(suite_path)
    enabled_checks = {c.get("test_id") for c in suite.get("checks", [])}
    schema_path = ROOT / suite["schema_ref"]
    schema = load_json(schema_path)

    if "cases" in suite:
        return _run_binding_suite(suite, schema)

    validator = _build_validator(schema, schema_path)

    key_map = load_json(ROOT / "fixtures/keys/GT_public_keys.json")
    can_verify_signatures = signature_verifier_available()
    payload_schema_ref = suite.get("payload_schema_ref")
    payload_schema = load_json(ROOT / payload_schema_ref) if payload_schema_ref else None
    payload_schema_map = suite.get("payload_schema_map")
    payload_schema_check_id = suite.get("payload_schema_check_id", "CN-PAYLOAD-SCHEMA-01")
    policy_reason_codes = {e.get("id") for e in load_json(ROOT / "registry/policy_reason_codes.json")}
    enforcement_sanction_codes = {e.get("id") for e in load_json(ROOT / "registry/enforcement_sanction_codes.json")}
    alert_codes_registry = {e.get("id"): e for e in load_json(ROOT / "registry/alert_codes.json")}
    alert_recommended_actions = {e.get("id") for e in load_json(ROOT / "registry/alert_recommended_actions.json")}
    registered_message_types = {e.get("id") for e in load_json(ROOT / "registry/message_types.json")}
    policy_categories_registry = {e.get("id") for e in load_json(ROOT / "registry/policy_categories.json")}
    capneg_reason_codes = {e.get("id") for e in load_json(ROOT / "registry/capneg_reason_codes.json")}
    privacy_modes_registry = {e.get("id") for e in load_json(ROOT / "registry/privacy_modes.json")}
    dispute_claim_types = {e.get("id") for e in load_json(ROOT / "registry/dispute_claim_types.json")}
    security_alert_categories = {e.get("id") for e in load_json(ROOT / "registry/security_alert_categories.json")}
    aicp_profiles_registry = {
        (e.get("profile_id"), e.get("profile_version"))
        for e in load_json(ROOT / "registry/aicp_profiles.json")
        if isinstance(e, dict)
    }
    contract_schema_path = ROOT / "schemas/core/aicp-core-contract.schema.json"
    contract_schema = load_json(contract_schema_path)
    contract_validator = _build_validator(contract_schema, contract_schema_path) if Draft202012Validator is not None else None

    failures: list[dict[str, Any]] = []
    degraded = False
    degraded_reasons: list[str] = []
    skipped_checks: list[str] = []

    for transcript in suite["transcripts"]:
        rel_file = transcript["path"]
        file_path = ROOT / rel_file
        t_failures: list[dict[str, Any]] = []

        rows = []
        for i, line in enumerate(file_path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except Exception as exc:
                add_failure(t_failures, "CT-SCHEMA-JSONL-01", f"Invalid JSON line: {exc}", rel_file, i)
                continue
            rows.append((i, obj))
            if validator is not None:
                for err in sorted(validator.iter_errors(obj), key=lambda e: list(e.path)):
                    add_failure(t_failures, "CT-SCHEMA-JSONL-01", err.message, rel_file, i)
            _validate_payload_schema(
                obj,
                i,
                rel_file,
                t_failures,
                payload_schema,
                payload_schema_map,
                payload_schema_check_id,
                enabled_checks,
            )

        if not rows:
            add_failure(t_failures, "CT-INVARIANTS-01", "Transcript has no JSONL records", rel_file, None)
            failures.extend(_evaluate_transcript_expectations(transcript, t_failures, rel_file))
            continue

        if "CT-MESSAGE-TYPE-REGISTRY-01" in enabled_checks:
            for line_no, msg in rows:
                mtype = msg.get("message_type")
                if mtype not in registered_message_types:
                    add_failure(t_failures, "CT-MESSAGE-TYPE-REGISTRY-01", f"unregistered message_type '{mtype}'", rel_file, line_no)

        session_id = rows[0][1].get("session_id")
        seen_ids: set[str] = set()
        for line_no, msg in rows:
            if msg.get("session_id") != session_id:
                add_failure(t_failures, "CT-INVARIANTS-01", "session_id changed within transcript", rel_file, line_no)

            mid = msg.get("message_id")
            if mid in seen_ids:
                add_failure(t_failures, "CT-INVARIANTS-01", f"duplicate message_id '{mid}'", rel_file, line_no)
            else:
                seen_ids.add(mid)

        if "CT-PREV-MSG-REQUIRED-01" in enabled_checks:
            for idx, (line_no, msg) in enumerate(rows):
                if idx == 0:
                    continue
                prev_msg_hash = msg.get("prev_msg_hash")
                if not isinstance(prev_msg_hash, str) or not prev_msg_hash:
                    add_failure(
                        t_failures,
                        "CT-PREV-MSG-REQUIRED-01",
                        "prev_msg_hash is required and must be a non-empty string for non-first messages",
                        rel_file,
                        line_no,
                    )

        prev_hash = None
        for line_no, msg in rows:
            if prev_hash is not None and "prev_msg_hash" in msg and msg.get("prev_msg_hash") != prev_hash:
                add_failure(
                    t_failures,
                    "CT-HASH-CHAIN-01",
                    f"prev_msg_hash mismatch (expected {prev_hash}, got {msg.get('prev_msg_hash')})",
                    rel_file,
                    line_no,
                )
            prev_hash = msg.get("message_hash")

        actual_types = [m.get("message_type") for _, m in rows]
        expected_types = transcript.get("expected_message_types", [])
        if actual_types != expected_types:
            add_failure(
                t_failures,
                "CT-SEQUENCE-01",
                f"message_type sequence mismatch (expected {expected_types}, got {actual_types})",
                rel_file,
                None,
            )

        for line_no, msg in rows:
            mhash = msg.get("message_hash")
            for sig in msg.get("signatures", []) or []:
                obj_hash = sig.get("object_hash")
                if obj_hash is not None and obj_hash != mhash:
                    add_failure(
                        t_failures,
                        "CT-SIGNATURE-HASH-01",
                        f"signatures.object_hash mismatch (expected {mhash}, got {obj_hash})",
                        rel_file,
                        line_no,
                    )

        for line_no, msg in rows:
            stored = msg.get("message_hash")
            try:
                computed = message_hash_from_body(_message_body_without_hash_and_signatures(msg))
            except Exception as exc:
                add_failure(t_failures, "CT-MESSAGE-HASH-01", f"hash recompute error: {exc}", rel_file, line_no)
                continue
            if computed != stored:
                add_failure(
                    t_failures,
                    "CT-MESSAGE-HASH-01",
                    f"message_hash mismatch (expected {stored}, got {computed})",
                    rel_file,
                    line_no,
                )

        if "CT-SIGNATURE-VERIFY-01" in enabled_checks:
            if can_verify_signatures:
                keyring = _baseline_keyring(key_map)
                for line_no, msg in rows:
                    mtype = msg.get("message_type")
                    payload = msg.get("payload") or {}

                    if mtype == "IDENTITY_ANNOUNCE":
                        aid_ref = payload.get("aid_ref")
                        if isinstance(aid_ref, dict) and aid_ref.get("object_type") == "aid":
                            aid_obj = aid_ref.get("object")
                            if isinstance(aid_obj, dict):
                                agent_id = aid_obj.get("agent_id")
                                keys = aid_obj.get("keys")
                                if isinstance(agent_id, str) and isinstance(keys, list):
                                    for item in keys:
                                        if not isinstance(item, dict):
                                            continue
                                        kid = item.get("kid")
                                        public_key = item.get("public_key_b64url")
                                        status = item.get("status")
                                        if isinstance(kid, str) and isinstance(public_key, str) and status != "revoked":
                                            keyring.setdefault(agent_id, {})[kid] = public_key

                    if mtype == "KEY_ROTATION":
                        sender = msg.get("sender")
                        if isinstance(sender, str):
                            old_kid = payload.get("old_kid")
                            new_key = payload.get("new_key") or {}
                            cross = payload.get("cross_signatures") or {}
                            old_sig = cross.get("old_signs_new") or {}
                            new_sig = cross.get("new_signs_old") or {}
                            old_public = keyring.get(sender, {}).get(old_kid) if isinstance(old_kid, str) else None
                            new_public = new_key.get("public_key_b64url") if isinstance(new_key, dict) else None
                            new_kid = new_key.get("kid") if isinstance(new_key, dict) else None
                            old_ok = isinstance(old_public, str) and verify_ed25519(old_public, str(old_sig.get("sig_b64url", "")), str(old_sig.get("object_hash", "")))
                            new_ok = isinstance(new_public, str) and verify_ed25519(str(new_public), str(new_sig.get("sig_b64url", "")), str(new_sig.get("object_hash", "")))
                            if old_ok and new_ok and isinstance(new_kid, str) and isinstance(new_public, str):
                                keyring.setdefault(sender, {})[new_kid] = new_public

                    for sig in msg.get("signatures", []) or []:
                        signer = sig.get("signer")
                        kid = sig.get("kid")
                        key = keyring.get(signer, {}).get(kid) if isinstance(signer, str) and isinstance(kid, str) else None
                        if not key:
                            add_failure(t_failures, "CT-SIGNATURE-VERIFY-01", f"missing public key for signer {signer} kid {kid}", rel_file, line_no)
                            continue
                        if not verify_ed25519(key, sig.get("sig_b64url", ""), sig.get("object_hash", "")):
                            add_failure(t_failures, "CT-SIGNATURE-VERIFY-01", "signature verification failed", rel_file, line_no)
            else:
                degraded = True
                reason = "signature verification unavailable"
                if reason not in degraded_reasons:
                    degraded_reasons.append(reason)
                if "CT-SIGNATURE-VERIFY-01" not in skipped_checks:
                    skipped_checks.append("CT-SIGNATURE-VERIFY-01")
                expected = {e.get("test_id") for e in transcript.get("expected_failures", [])}
                if "CT-SIGNATURE-VERIFY-01" in expected:
                    add_failure(t_failures, "CT-SIGNATURE-VERIFY-01", "signature verification unavailable in environment", rel_file, None)

        if "CT-CONTRACT-SCHEMA-01" in enabled_checks:
            for line_no, msg in rows:
                if msg.get("message_type") != "CONTRACT_PROPOSE":
                    continue
                payload = msg.get("payload") or {}
                contract_obj = payload.get("contract")
                if not isinstance(contract_obj, dict):
                    add_failure(t_failures, "CT-CONTRACT-SCHEMA-01", "payload.contract must be an object", rel_file, line_no)
                    continue
                if Draft202012Validator is None or contract_validator is None:
                    if not isinstance(contract_obj.get("contract_id"), str) or not contract_obj.get("contract_id"):
                        add_failure(t_failures, "CT-CONTRACT-SCHEMA-01", "contract.contract_id must be a non-empty string", rel_file, line_no)
                    if not isinstance(contract_obj.get("goal"), str) or not contract_obj.get("goal"):
                        add_failure(t_failures, "CT-CONTRACT-SCHEMA-01", "contract.goal must be a non-empty string", rel_file, line_no)
                    roles = contract_obj.get("roles")
                    if not isinstance(roles, list) or not roles or not all(isinstance(r, str) and r for r in roles):
                        add_failure(t_failures, "CT-CONTRACT-SCHEMA-01", "contract.roles must be a non-empty array of strings", rel_file, line_no)
                else:
                    for err in sorted(contract_validator.iter_errors(contract_obj), key=lambda e: list(e.path)):
                        add_failure(t_failures, "CT-CONTRACT-SCHEMA-01", err.message, rel_file, line_no)
                if msg.get("contract_id") != contract_obj.get("contract_id"):
                    add_failure(t_failures, "CT-CONTRACT-SCHEMA-01", "envelope.contract_id must equal payload.contract.contract_id", rel_file, line_no)

        if "CT-POLICY-CATEGORIES-01" in enabled_checks:
            namespaced_dash = re.compile(r"^x-[a-z0-9]+[a-z0-9._-]*$")
            namespaced_colon = re.compile(r"^[a-z0-9]+:[a-z0-9][a-z0-9._-]*$")
            for line_no, msg in rows:
                if msg.get("message_type") != "CONTRACT_PROPOSE":
                    continue
                contract_obj = ((msg.get("payload") or {}).get("contract") or {})
                policies = contract_obj.get("policies")
                if policies is None:
                    continue
                if not isinstance(policies, list):
                    add_failure(t_failures, "CT-POLICY-CATEGORIES-01", "contract.policies must be an array", rel_file, line_no)
                    continue
                seen_policy_ids: set[str] = set()
                for ix, policy in enumerate(policies):
                    if not isinstance(policy, dict):
                        add_failure(t_failures, "CT-POLICY-CATEGORIES-01", f"contract.policies[{ix}] must be an object", rel_file, line_no)
                        continue
                    policy_id = policy.get("policy_id")
                    category = policy.get("category")
                    if not isinstance(policy_id, str) or not policy_id:
                        add_failure(t_failures, "CT-POLICY-CATEGORIES-01", f"contract.policies[{ix}].policy_id must be a non-empty string", rel_file, line_no)
                    elif policy_id in seen_policy_ids:
                        add_failure(t_failures, "CT-POLICY-CATEGORIES-01", f"duplicate policy_id '{policy_id}'", rel_file, line_no)
                    else:
                        seen_policy_ids.add(policy_id)
                    if not isinstance(category, str) or not category:
                        add_failure(t_failures, "CT-POLICY-CATEGORIES-01", f"contract.policies[{ix}].category must be a non-empty string", rel_file, line_no)
                    elif category not in policy_categories_registry and not namespaced_dash.match(category) and not namespaced_colon.match(category):
                        add_failure(t_failures, "CT-POLICY-CATEGORIES-01", f"unknown policy category '{category}'", rel_file, line_no)

        # Extension-specific object hash checks (OR-OBJECT-HASH-01)
        if "OR-OBJECT-HASH-01" in enabled_checks:
            for line_no, msg in rows:
                for otype, obj, stored_hash in _collect_object_hash_triples(msg.get("payload")):
                    try:
                        computed_hash = object_hash(otype, obj)
                    except Exception as exc:
                        add_failure(t_failures, "OR-OBJECT-HASH-01", f"object_hash recompute error: {exc}", rel_file, line_no)
                        continue
                    if computed_hash != stored_hash:
                        add_failure(
                            t_failures,
                            "OR-OBJECT-HASH-01",
                            f"object_hash mismatch (expected {stored_hash}, got {computed_hash})",
                            rel_file,
                            line_no,
                        )


        # PE-REASON-CODES-01 + PE-CONTEXT-HASH-01
        if "PE-REASON-CODES-01" in enabled_checks or "PE-CONTEXT-HASH-01" in enabled_checks:
            for line_no, msg in rows:
                payload = msg.get("payload") or {}
                if msg.get("message_type") == "POLICY_EVAL_RESULT":
                    decision = payload.get("policy_decision") or {}
                    if "PE-REASON-CODES-01" in enabled_checks:
                        for code in decision.get("reason_codes", []) or []:
                            if code not in policy_reason_codes and not _is_namespaced_identifier(code):
                                add_failure(t_failures, "PE-REASON-CODES-01", f"unknown reason_code '{code}' (must be registered or namespaced vendor:/org:)", rel_file, line_no)
                if msg.get("message_type") == "POLICY_EVAL_REQUEST" and "PE-CONTEXT-HASH-01" in enabled_checks:
                    ctx = (payload.get("evaluation_context") or {})
                    if "context_hash" in ctx:
                        stored_ctx_hash = ctx.get("context_hash")
                        context_obj = dict(ctx)
                        context_obj.pop("context_hash", None)
                        try:
                            computed_ctx_hash = object_hash("evaluation_context", context_obj)
                        except Exception as exc:
                            add_failure(t_failures, "PE-CONTEXT-HASH-01", f"context_hash recompute error: {exc}", rel_file, line_no)
                            continue
                        if computed_ctx_hash != stored_ctx_hash:
                            add_failure(t_failures, "PE-CONTEXT-HASH-01", f"context_hash mismatch (expected {stored_ctx_hash}, got {computed_ctx_hash})", rel_file, line_no)


        if "CN-AICP-PROFILE-NEGOTIATION-01" in enabled_checks:
            declares_by_party: dict[str, dict[str, Any]] = {}
            for _, msg in rows:
                if msg.get("message_type") != "CAPABILITIES_DECLARE":
                    continue
                payload = msg.get("payload") or {}
                party_id = payload.get("party_id")
                if isinstance(party_id, str):
                    declares_by_party[party_id] = payload

            for line_no, msg in rows:
                if msg.get("message_type") != "CAPABILITIES_PROPOSE":
                    continue
                result = ((msg.get("payload") or {}).get("negotiation_result") or {})
                participants = result.get("participants") or []
                selected = result.get("selected") or {}
                aicp_profile = selected.get("aicp_profile")
                if not isinstance(aicp_profile, dict):
                    continue
                profile_id = aicp_profile.get("profile_id")
                profile_version = aicp_profile.get("profile_version")
                profile_tuple = (profile_id, profile_version)
                if profile_tuple not in aicp_profiles_registry:
                    add_failure(
                        t_failures,
                        "CN-AICP-PROFILE-NEGOTIATION-01",
                        f"selected.aicp_profile '{profile_id}@{profile_version}' is not registered",
                        rel_file,
                        line_no,
                    )

                for participant in participants:
                    if not isinstance(participant, str):
                        continue
                    declared = declares_by_party.get(participant)
                    if not isinstance(declared, dict):
                        continue

                    supported_profiles = {
                        (p.get("profile_id"), p.get("profile_version"))
                        for p in (declared.get("supported_aicp_profiles") or [])
                        if isinstance(p, dict)
                    }
                    if supported_profiles and profile_tuple not in supported_profiles:
                        add_failure(
                            t_failures,
                            "CN-AICP-PROFILE-NEGOTIATION-01",
                            f"participant '{participant}' does not support selected.aicp_profile '{profile_id}@{profile_version}'",
                            rel_file,
                            line_no,
                        )

                    required_profiles = {
                        (p.get("profile_id"), p.get("profile_version"))
                        for p in (declared.get("required_aicp_profiles") or [])
                        if isinstance(p, dict)
                    }
                    if required_profiles and profile_tuple not in required_profiles:
                        add_failure(
                            t_failures,
                            "CN-AICP-PROFILE-NEGOTIATION-01",
                            f"participant '{participant}' required_aicp_profiles does not include selected.aicp_profile '{profile_id}@{profile_version}'",
                            rel_file,
                            line_no,
                        )

        if "CN-REASON-CODES-01" in enabled_checks:
            for line_no, msg in rows:
                if msg.get("message_type") != "CAPABILITIES_REJECT":
                    continue
                payload = msg.get("payload") or {}
                reason_code = payload.get("reason_code")
                if reason_code not in capneg_reason_codes:
                    add_failure(t_failures, "CN-REASON-CODES-01", f"unknown CAPNEG reason_code '{reason_code}'", rel_file, line_no)

        if "CN-PRIVACY-MODES-01" in enabled_checks:
            for line_no, msg in rows:
                mtype = msg.get("message_type")
                payload = msg.get("payload") or {}
                if mtype == "CAPABILITIES_DECLARE":
                    for mode in payload.get("supported_privacy_modes") or []:
                        if mode not in privacy_modes_registry and not _is_namespaced_identifier(mode):
                            add_failure(t_failures, "CN-PRIVACY-MODES-01", f"unsupported supported_privacy_modes entry '{mode}'", rel_file, line_no)
                elif mtype in {"CAPABILITIES_PROPOSE", "CAPABILITIES_ACCEPT"}:
                    selected = ((payload.get("negotiation_result") or {}).get("selected") or {})
                    mode = selected.get("privacy_mode")
                    if mode is None:
                        continue
                    if mode not in privacy_modes_registry and not _is_namespaced_identifier(mode):
                        add_failure(t_failures, "CN-PRIVACY-MODES-01", f"selected privacy_mode '{mode}' is not registered", rel_file, line_no)

        if "CN-NEGRESULT-HASH-01" in enabled_checks or "CN-CONTRACT-BIND-01" in enabled_checks:
            proposed_negotiation_result: dict[str, Any] | None = None
            proposed_negotiation_result_hash: str | None = None
            accepted_indices: list[int] = []

            for idx, (line_no, msg) in enumerate(rows):
                mtype = msg.get("message_type")
                payload = msg.get("payload") or {}
                if mtype == "CAPABILITIES_PROPOSE" and proposed_negotiation_result is None:
                    nr = payload.get("negotiation_result")
                    if isinstance(nr, dict):
                        proposed_negotiation_result = nr
                        try:
                            proposed_negotiation_result_hash = object_hash("capneg.negotiation_result", nr)
                        except Exception as exc:
                            add_failure(t_failures, "CN-NEGRESULT-HASH-01", f"negotiation_result hash recompute error: {exc}", rel_file, line_no)
                if mtype == "CAPABILITIES_ACCEPT":
                    accepted_indices.append(idx)
                    if "CN-NEGRESULT-HASH-01" in enabled_checks:
                        if not proposed_negotiation_result_hash:
                            add_failure(t_failures, "CN-NEGRESULT-HASH-01", "CAPABILITIES_ACCEPT seen before valid CAPABILITIES_PROPOSE negotiation_result", rel_file, line_no)
                            continue
                        nr = payload.get("negotiation_result")
                        if isinstance(nr, dict):
                            try:
                                accept_hash = object_hash("capneg.negotiation_result", nr)
                            except Exception as exc:
                                add_failure(t_failures, "CN-NEGRESULT-HASH-01", f"accept negotiation_result hash recompute error: {exc}", rel_file, line_no)
                            else:
                                if accept_hash != proposed_negotiation_result_hash:
                                    add_failure(t_failures, "CN-NEGRESULT-HASH-01", "CAPABILITIES_ACCEPT negotiation_result hash mismatch vs CAPABILITIES_PROPOSE", rel_file, line_no)
                        nr_hash = payload.get("negotiation_result_hash")
                        if isinstance(nr_hash, str) and nr_hash and nr_hash != proposed_negotiation_result_hash:
                            add_failure(t_failures, "CN-NEGRESULT-HASH-01", "CAPABILITIES_ACCEPT negotiation_result_hash mismatch vs CAPABILITIES_PROPOSE", rel_file, line_no)

            if "CN-CONTRACT-BIND-01" in enabled_checks and accepted_indices:
                if not proposed_negotiation_result_hash:
                    add_failure(t_failures, "CN-CONTRACT-BIND-01", "cannot verify contract CAPNEG binding without CAPABILITIES_PROPOSE negotiation_result", rel_file, None)
                else:
                    first_accept_idx = accepted_indices[0]
                    expected_selected = (proposed_negotiation_result or {}).get("selected")
                    for idx, (line_no, msg) in enumerate(rows):
                        if idx <= first_accept_idx or msg.get("message_type") != "CONTRACT_PROPOSE":
                            continue
                        contract = ((msg.get("payload") or {}).get("contract") or {})
                        capneg_binding = (((contract.get("ext") or {}).get("capneg")) if isinstance(contract, dict) else None)
                        if not isinstance(capneg_binding, dict):
                            add_failure(t_failures, "CN-CONTRACT-BIND-01", "CONTRACT_PROPOSE payload.contract.ext.capneg is required after CAPABILITIES_ACCEPT", rel_file, line_no)
                            continue
                        binding_hash = capneg_binding.get("negotiation_result_hash")
                        if not isinstance(binding_hash, str) or binding_hash != proposed_negotiation_result_hash:
                            add_failure(t_failures, "CN-CONTRACT-BIND-01", "contract.ext.capneg.negotiation_result_hash must match accepted negotiation_result hash", rel_file, line_no)
                        if "selected" in capneg_binding and capneg_binding.get("selected") != expected_selected:
                            add_failure(t_failures, "CN-CONTRACT-BIND-01", "contract.ext.capneg.selected must exactly match negotiation_result.selected", rel_file, line_no)

        if "CN-DOWNGRADE-01" in enabled_checks:
            accepted_extensions: dict[str, set[str]] = {}
            for line_no, msg in rows:
                mtype = msg.get("message_type")
                payload = msg.get("payload") or {}

                if mtype == "CAPABILITIES_ACCEPT":
                    result = payload.get("negotiation_result") or {}
                    neg_id = payload.get("negotiation_id") or result.get("negotiation_id")
                    selected = result.get("selected") or {}
                    required_ext = selected.get("required_extensions")
                    if isinstance(neg_id, str) and isinstance(required_ext, list):
                        accepted_extensions[neg_id] = {e for e in required_ext if isinstance(e, str)}

                elif mtype == "CAPABILITIES_PROPOSE":
                    result = payload.get("negotiation_result") or {}
                    neg_id = result.get("negotiation_id")
                    selected = result.get("selected") or {}
                    required_ext = selected.get("required_extensions")
                    if not (isinstance(neg_id, str) and isinstance(required_ext, list)):
                        continue
                    proposed_set = {e for e in required_ext if isinstance(e, str)}
                    prior_set = accepted_extensions.get(neg_id)
                    if prior_set is not None and not prior_set.issubset(proposed_set):
                        add_failure(
                            t_failures,
                            "CN-DOWNGRADE-01",
                            f"negotiation_id '{neg_id}' removes previously accepted required_extensions (accepted={sorted(prior_set)}, proposed={sorted(proposed_set)})",
                            rel_file,
                            line_no,
                        )

        if any(check in enabled_checks for check in {"DS-TARGET-01", "DS-CLAIMTYPE-01", "DS-EVIDENCE-01", "DS-EVIDENCE-RESOLVE-01", "SA-CAT-01", "SA-EVIDENCE-01", "SA-EVIDENCE-RESOLVE-01"}):
            prior_message_ids: set[str] = set()
            prior_message_hashes: set[str] = set()
            prior_payload_object_hashes: set[str] = set()
            for line_no, msg in rows:
                payload = msg.get("payload") or {}
                mtype = msg.get("message_type")

                if mtype == "CHALLENGE_ASSERTION":
                    target_ref = payload.get("target_ref") if isinstance(payload.get("target_ref"), dict) else {}
                    if "DS-TARGET-01" in enabled_checks:
                        message_id = target_ref.get("message_id")
                        object_hash_ref = target_ref.get("object_hash")
                        if isinstance(message_id, str) and message_id and message_id not in prior_message_ids:
                            add_failure(t_failures, "DS-TARGET-01", f"target_ref.message_id '{message_id}' must reference an earlier message_id", rel_file, line_no)
                        if isinstance(object_hash_ref, str) and object_hash_ref and object_hash_ref not in prior_payload_object_hashes:
                            add_failure(t_failures, "DS-TARGET-01", f"target_ref.object_hash '{object_hash_ref}' must reference an earlier payload object_hash", rel_file, line_no)

                    if "DS-CLAIMTYPE-01" in enabled_checks:
                        challenge_type = payload.get("challenge_type")
                        if challenge_type not in dispute_claim_types and not _is_namespaced_identifier(challenge_type):
                            add_failure(t_failures, "DS-CLAIMTYPE-01", f"unknown challenge_type '{challenge_type}'", rel_file, line_no)

                    evidence_refs = payload.get("evidence_refs")
                    if "DS-EVIDENCE-01" in enabled_checks:
                        valid_evidence = isinstance(evidence_refs, list) and len(evidence_refs) > 0 and all(isinstance(ref, str) and ref for ref in evidence_refs)
                        if not valid_evidence:
                            add_failure(t_failures, "DS-EVIDENCE-01", "CHALLENGE_ASSERTION requires non-empty evidence_refs", rel_file, line_no)
                    if "DS-EVIDENCE-RESOLVE-01" in enabled_checks and not _has_resolvable_evidence_ref(evidence_refs, prior_message_ids, prior_message_hashes, prior_payload_object_hashes):
                        add_failure(t_failures, "DS-EVIDENCE-RESOLVE-01", "CHALLENGE_ASSERTION evidence_refs must include a resolvable msgid:/msghash:/objhash: reference", rel_file, line_no)

                elif mtype == "CLAIM_BREACH" and "DS-CLAIMTYPE-01" in enabled_checks:
                    breach_type = payload.get("breach_type")
                    if breach_type not in dispute_claim_types and not _is_namespaced_identifier(breach_type):
                        add_failure(t_failures, "DS-CLAIMTYPE-01", f"unknown breach_type '{breach_type}'", rel_file, line_no)

                elif mtype == "SECURITY_ALERT":
                    if "SA-CAT-01" in enabled_checks:
                        category = payload.get("category")
                        if category not in security_alert_categories and not _is_namespaced_identifier(category):
                            add_failure(t_failures, "SA-CAT-01", f"unknown category '{category}'", rel_file, line_no)
                    evidence_refs = payload.get("evidence_refs")
                    if "SA-EVIDENCE-01" in enabled_checks:
                        valid_evidence = isinstance(evidence_refs, list) and len(evidence_refs) > 0 and all(isinstance(ref, str) and ref for ref in evidence_refs)
                        if not valid_evidence:
                            add_failure(t_failures, "SA-EVIDENCE-01", "SECURITY_ALERT requires non-empty evidence_refs", rel_file, line_no)
                    if "SA-EVIDENCE-RESOLVE-01" in enabled_checks and not _has_resolvable_evidence_ref(evidence_refs, prior_message_ids, prior_message_hashes, prior_payload_object_hashes):
                        add_failure(t_failures, "SA-EVIDENCE-RESOLVE-01", "SECURITY_ALERT evidence_refs must include a resolvable msgid:/msghash:/objhash: reference", rel_file, line_no)

                msg_id = msg.get("message_id")
                if isinstance(msg_id, str) and msg_id:
                    prior_message_ids.add(msg_id)
                msg_hash = msg.get("message_hash")
                if isinstance(msg_hash, str) and msg_hash:
                    prior_message_hashes.add(msg_hash)
                if isinstance(payload, dict):
                    for value in payload.values():
                        if isinstance(value, dict):
                            o_hash = value.get("object_hash")
                            if isinstance(o_hash, str) and o_hash:
                                prior_payload_object_hashes.add(o_hash)

        if any(check in enabled_checks for check in {"DL-EXPIRY-01", "DL-DEPTH-01", "DL-BIND-01", "DL-SCOPE-01"}):
            grants_by_id: dict[str, tuple[int, int, dict[str, Any], dict[str, Any]]] = {}
            for idx, (line_no, msg) in enumerate(rows):
                if msg.get("message_type") != "DELEGATION_GRANT":
                    continue
                payload = msg.get("payload") or {}
                delegation_id = payload.get("delegation_id")
                if isinstance(delegation_id, str) and delegation_id not in grants_by_id:
                    grants_by_id[delegation_id] = (idx, line_no, msg, payload)

            if "DL-DEPTH-01" in enabled_checks:
                for idx, line_no, _, payload in grants_by_id.values():
                    parent_id = payload.get("parent_delegation_id")
                    if not isinstance(parent_id, str):
                        continue
                    parent = grants_by_id.get(parent_id)
                    if parent is None:
                        add_failure(t_failures, "DL-DEPTH-01", f"parent_delegation_id '{parent_id}' does not reference a prior DELEGATION_GRANT", rel_file, line_no)
                        continue
                    parent_idx, _, _, parent_payload = parent
                    if parent_idx >= idx:
                        add_failure(t_failures, "DL-DEPTH-01", f"parent_delegation_id '{parent_id}' must reference an earlier DELEGATION_GRANT", rel_file, line_no)
                        continue
                    parent_max = parent_payload.get("max_depth") if isinstance(parent_payload.get("max_depth"), int) else 0
                    child_max = payload.get("max_depth") if isinstance(payload.get("max_depth"), int) else 0
                    if parent_max <= 0:
                        add_failure(t_failures, "DL-DEPTH-01", f"parent delegation '{parent_id}' max_depth={parent_max} cannot delegate further", rel_file, line_no)
                        continue
                    if child_max > parent_max - 1:
                        add_failure(t_failures, "DL-DEPTH-01", f"child delegation max_depth={child_max} exceeds allowed remaining depth {parent_max - 1}", rel_file, line_no)

            if "DL-SCOPE-01" in enabled_checks:
                for idx, line_no, _, payload in grants_by_id.values():
                    parent_id = payload.get("parent_delegation_id")
                    if not isinstance(parent_id, str):
                        continue
                    parent = grants_by_id.get(parent_id)
                    if parent is None:
                        continue
                    parent_idx, _, _, parent_payload = parent
                    if parent_idx >= idx:
                        continue
                    parent_scope = parent_payload.get("scope") if isinstance(parent_payload.get("scope"), list) else []
                    child_scope = payload.get("scope") if isinstance(payload.get("scope"), list) else []
                    parent_set = {s for s in parent_scope if isinstance(s, str)}
                    child_set = {s for s in child_scope if isinstance(s, str)}
                    extra = sorted(child_set - parent_set)
                    if extra:
                        add_failure(t_failures, "DL-SCOPE-01", f"child delegation scope is not subset of parent scope; extra={extra}", rel_file, line_no)

            for idx, (line_no, msg) in enumerate(rows):
                if msg.get("message_type") != "DELEGATION_RESULT_ATTEST":
                    continue
                payload = msg.get("payload") or {}
                delegation_id = payload.get("delegation_id")
                grant = grants_by_id.get(delegation_id) if isinstance(delegation_id, str) else None

                if "DL-BIND-01" in enabled_checks:
                    if grant is None:
                        add_failure(t_failures, "DL-BIND-01", f"DELEGATION_RESULT_ATTEST delegation_id '{delegation_id}' must reference a prior DELEGATION_GRANT", rel_file, line_no)
                    else:
                        grant_idx = grant[0]
                        if grant_idx >= idx:
                            add_failure(t_failures, "DL-BIND-01", f"DELEGATION_RESULT_ATTEST delegation_id '{delegation_id}' must reference an earlier DELEGATION_GRANT", rel_file, line_no)
                    contract_ref = msg.get("contract_ref") or {}
                    if payload.get("contract_head_version") != contract_ref.get("head_version"):
                        add_failure(t_failures, "DL-BIND-01", "payload.contract_head_version must equal envelope contract_ref.head_version", rel_file, line_no)

                if "DL-EXPIRY-01" in enabled_checks and grant is not None and grant[0] < idx:
                    expiry = _parse_iso_datetime((grant[3] or {}).get("expiry"))
                    attest_ts = _parse_iso_datetime(msg.get("timestamp"))
                    if expiry is None:
                        add_failure(t_failures, "DL-EXPIRY-01", "referenced DELEGATION_GRANT payload.expiry must be valid date-time", rel_file, line_no)
                    elif attest_ts is None:
                        add_failure(t_failures, "DL-EXPIRY-01", "DELEGATION_RESULT_ATTEST timestamp must be valid date-time", rel_file, line_no)
                    elif attest_ts > expiry:
                        add_failure(t_failures, "DL-EXPIRY-01", f"DELEGATION_RESULT_ATTEST occurs after grant expiry ({attest_ts.isoformat()} > {expiry.isoformat()})", rel_file, line_no)

        if any(check in enabled_checks for check in {"WF-DECL-01", "WF-UPD-01", "WF-REF-01", "WF-MONO-01", "WF-BIND-01"}):
            workflow_state: dict[str, dict[str, Any]] = {}
            last_step_index: dict[str, int] = {}

            def _parse_version_number(value: Any) -> int | None:
                if not isinstance(value, str) or not value:
                    return None
                if value.startswith("v") and value[1:].isdigit():
                    return int(value[1:])
                if value.isdigit():
                    return int(value)
                return None

            for idx, (line_no, msg) in enumerate(rows):
                mtype = msg.get("message_type")
                payload = msg.get("payload") or {}

                if mtype == "WORKFLOW_DECLARE":
                    workflow_id = payload.get("workflow_id")
                    artifact_ref = payload.get("workflow_artifact_ref") or {}
                    artifact_hash = artifact_ref.get("object_hash") if isinstance(artifact_ref, dict) else None
                    if isinstance(workflow_id, str):
                        workflow_state[workflow_id] = {"hash": artifact_hash, "version": payload.get("version"), "index": idx}

                    if "WF-DECL-01" in enabled_checks:
                        contract_ref = msg.get("contract_ref") or {}
                        if payload.get("contract_head_version") != contract_ref.get("head_version"):
                            add_failure(t_failures, "WF-DECL-01", "WORKFLOW_DECLARE payload.contract_head_version must equal envelope contract_ref.head_version", rel_file, line_no)
                        if artifact_ref.get("object_type") != "workflow":
                            add_failure(t_failures, "WF-DECL-01", "workflow_artifact_ref.object_type must be 'workflow'", rel_file, line_no)
                        try:
                            computed = object_hash("workflow", artifact_ref.get("object"))
                        except Exception as exc:
                            add_failure(t_failures, "WF-DECL-01", f"workflow_artifact_ref object_hash recompute error: {exc}", rel_file, line_no)
                        else:
                            if computed != artifact_ref.get("object_hash"):
                                add_failure(t_failures, "WF-DECL-01", f"workflow_artifact_ref.object_hash mismatch (expected {artifact_ref.get('object_hash')}, got {computed})", rel_file, line_no)
                            wf_hash = payload.get("workflow_hash")
                            if wf_hash is not None and wf_hash != artifact_ref.get("object_hash"):
                                add_failure(t_failures, "WF-DECL-01", "payload.workflow_hash must equal workflow_artifact_ref.object_hash when present", rel_file, line_no)

                elif mtype == "WORKFLOW_UPDATE":
                    workflow_id = payload.get("workflow_id")
                    previous = workflow_state.get(workflow_id) if isinstance(workflow_id, str) else None
                    artifact_ref = payload.get("workflow_artifact_ref") or {}
                    artifact_hash = artifact_ref.get("object_hash") if isinstance(artifact_ref, dict) else None
                    if isinstance(workflow_id, str):
                        workflow_state[workflow_id] = {"hash": artifact_hash, "version": payload.get("version"), "index": idx}

                    if "WF-UPD-01" in enabled_checks:
                        if previous is None or previous.get("index", -1) >= idx:
                            add_failure(t_failures, "WF-UPD-01", f"WORKFLOW_UPDATE workflow_id '{workflow_id}' must reference an earlier workflow declaration/update", rel_file, line_no)
                        else:
                            if payload.get("base_workflow_hash") != previous.get("hash"):
                                add_failure(t_failures, "WF-UPD-01", "payload.base_workflow_hash must equal previous workflow hash", rel_file, line_no)
                            prev_v = _parse_version_number(previous.get("version"))
                            cur_v = _parse_version_number(payload.get("version"))
                            if prev_v is None or cur_v is None:
                                add_failure(t_failures, "WF-UPD-01", "workflow versions must be parseable as vN or integer string", rel_file, line_no)
                            elif cur_v <= prev_v:
                                add_failure(t_failures, "WF-UPD-01", f"workflow version must increase (previous={previous.get('version')}, current={payload.get('version')})", rel_file, line_no)

                elif mtype == "WORKFLOW_STEP_ATTEST":
                    workflow_id = payload.get("workflow_id")
                    known = workflow_state.get(workflow_id) if isinstance(workflow_id, str) else None

                    if "WF-REF-01" in enabled_checks:
                        if known is None or known.get("index", -1) >= idx:
                            add_failure(t_failures, "WF-REF-01", f"WORKFLOW_STEP_ATTEST workflow_id '{workflow_id}' must reference a previously declared workflow", rel_file, line_no)

                    if "WF-MONO-01" in enabled_checks:
                        step_index = payload.get("step_index")
                        if isinstance(step_index, int):
                            prev = last_step_index.get(str(workflow_id))
                            if prev is not None and step_index < prev:
                                add_failure(t_failures, "WF-MONO-01", f"workflow_id '{workflow_id}' step_index decreased from {prev} to {step_index}", rel_file, line_no)
                            last_step_index[str(workflow_id)] = step_index

                    if "WF-BIND-01" in enabled_checks:
                        contract_ref = msg.get("contract_ref") or {}
                        if payload.get("contract_head_version") != contract_ref.get("head_version"):
                            add_failure(t_failures, "WF-BIND-01", "WORKFLOW_STEP_ATTEST payload.contract_head_version must equal envelope contract_ref.head_version", rel_file, line_no)
                        output_hash = payload.get("output_hash")
                        output_refs = payload.get("output_refs")
                        has_output_hash = isinstance(output_hash, str) and bool(output_hash)
                        has_output_refs = isinstance(output_refs, list) and any(isinstance(x, str) and x for x in output_refs)
                        if not (has_output_hash or has_output_refs):
                            add_failure(t_failures, "WF-BIND-01", "WORKFLOW_STEP_ATTEST requires output_hash or non-empty output_refs", rel_file, line_no)

        if any(check in enabled_checks for check in {"ID-AID-01", "ID-ANN-01", "ID-ROT-01", "ID-REVOKE-01"}):
            keyring = _baseline_keyring(key_map)
            revoked_after_index: dict[str, int] = {}
            contract_changing_types = {"CONTRACT_PROPOSE", "CONTRACT_ACCEPT", "CONTEXT_AMEND", "RESOLVE_CONFLICT"}

            for idx, (line_no, msg) in enumerate(rows):
                mtype = msg.get("message_type")
                payload = msg.get("payload") or {}

                if mtype == "IDENTITY_ANNOUNCE":
                    aid_ref = payload.get("aid_ref")
                    if isinstance(aid_ref, dict):
                        if "ID-AID-01" in enabled_checks:
                            if aid_ref.get("object_type") != "aid" or not isinstance(aid_ref.get("object"), dict) or not isinstance(aid_ref.get("object_hash"), str):
                                add_failure(t_failures, "ID-AID-01", "aid_ref must include object_type='aid', object, and object_hash", rel_file, line_no)
                            else:
                                try:
                                    computed_aid_hash = object_hash("aid", aid_ref.get("object"))
                                except Exception as exc:
                                    add_failure(t_failures, "ID-AID-01", f"aid_ref object_hash recompute error: {exc}", rel_file, line_no)
                                else:
                                    if computed_aid_hash != aid_ref.get("object_hash"):
                                        add_failure(t_failures, "ID-AID-01", f"aid_ref.object_hash mismatch (expected {aid_ref.get('object_hash')}, got {computed_aid_hash})", rel_file, line_no)
                        if "ID-ANN-01" in enabled_checks and isinstance(aid_ref.get("object_hash"), str):
                            if payload.get("aid_hash") != aid_ref.get("object_hash"):
                                add_failure(t_failures, "ID-ANN-01", "IDENTITY_ANNOUNCE payload.aid_hash must equal aid_ref.object_hash", rel_file, line_no)

                        aid_obj = aid_ref.get("object")
                        if isinstance(aid_obj, dict):
                            agent_id = aid_obj.get("agent_id")
                            keys = aid_obj.get("keys")
                            if isinstance(agent_id, str) and isinstance(keys, list):
                                for item in keys:
                                    if not isinstance(item, dict):
                                        continue
                                    kid = item.get("kid")
                                    pub = item.get("public_key_b64url")
                                    status = item.get("status")
                                    if isinstance(kid, str) and isinstance(pub, str) and status != "revoked":
                                        keyring.setdefault(agent_id, {})[kid] = pub

                if mtype == "KEY_ROTATION":
                    sender = msg.get("sender")
                    old_kid = payload.get("old_kid")
                    new_key = payload.get("new_key") or {}
                    cross = payload.get("cross_signatures") or {}
                    old_sig = cross.get("old_signs_new") or {}
                    new_sig = cross.get("new_signs_old") or {}

                    new_key_material = {
                        "kid": new_key.get("kid"),
                        "alg": new_key.get("alg"),
                        "public_key_b64url": new_key.get("public_key_b64url"),
                    }
                    old_kid_binding = {"old_kid": old_kid}
                    try:
                        new_key_hash = object_hash("key", new_key_material)
                        old_kid_hash = object_hash("kid", old_kid_binding)
                    except Exception as exc:
                        if "ID-ROT-01" in enabled_checks:
                            add_failure(t_failures, "ID-ROT-01", f"rotation object_hash computation failed: {exc}", rel_file, line_no)
                        continue

                    old_public = keyring.get(sender, {}).get(old_kid) if isinstance(sender, str) and isinstance(old_kid, str) else None
                    new_public = new_key.get("public_key_b64url") if isinstance(new_key, dict) else None
                    new_kid = new_key.get("kid") if isinstance(new_key, dict) else None

                    hash_ok = old_sig.get("object_hash") == new_key_hash and new_sig.get("object_hash") == old_kid_hash
                    sig_old_ok = isinstance(old_public, str) and verify_ed25519(old_public, str(old_sig.get("sig_b64url", "")), str(old_sig.get("object_hash", "")))
                    sig_new_ok = isinstance(new_public, str) and verify_ed25519(str(new_public), str(new_sig.get("sig_b64url", "")), str(new_sig.get("object_hash", "")))

                    if "ID-ROT-01" in enabled_checks:
                        if not hash_ok:
                            add_failure(t_failures, "ID-ROT-01", "KEY_ROTATION cross_signatures object_hash values do not match required key/kid object hashes", rel_file, line_no)
                        if not sig_old_ok:
                            add_failure(t_failures, "ID-ROT-01", "KEY_ROTATION old_signs_new signature verification failed", rel_file, line_no)
                        if not sig_new_ok:
                            add_failure(t_failures, "ID-ROT-01", "KEY_ROTATION new_signs_old signature verification failed", rel_file, line_no)

                    if hash_ok and sig_old_ok and sig_new_ok and isinstance(sender, str) and isinstance(new_kid, str) and isinstance(new_public, str):
                        keyring.setdefault(sender, {})[new_kid] = new_public

                if mtype == "KEY_REVOKE":
                    target_kid = payload.get("target_kid")
                    if isinstance(target_kid, str) and target_kid not in revoked_after_index:
                        revoked_after_index[target_kid] = idx

                if "ID-REVOKE-01" in enabled_checks and mtype in contract_changing_types:
                    for sig in msg.get("signatures", []) or []:
                        kid = sig.get("kid")
                        if isinstance(kid, str):
                            revoke_idx = revoked_after_index.get(kid)
                            if revoke_idx is not None and idx > revoke_idx:
                                add_failure(t_failures, "ID-REVOKE-01", f"contract-changing message signed with revoked kid '{kid}'", rel_file, line_no)

        if any(check in enabled_checks for check in {"DI-OBJ-01", "DI-ISSUE-01", "DI-SIGNED-01", "DI-ACT-01", "DI-EXPIRY-01", "DI-REVOKE-01"}):
            issued_bindings: dict[str, dict[str, Any]] = {}
            revoked_effective_at: dict[str, datetime] = {}

            for line_no, msg in rows:
                mtype = msg.get("message_type")
                payload = msg.get("payload") or {}
                sender = msg.get("sender")

                if mtype == "SUBJECT_BINDING_ISSUE":
                    signatures = msg.get("signatures") or []
                    if "DI-SIGNED-01" in enabled_checks and (not isinstance(signatures, list) or len(signatures) == 0):
                        add_failure(t_failures, "DI-SIGNED-01", "SUBJECT_BINDING_ISSUE must include non-empty signatures", rel_file, line_no)

                    binding_hash = payload.get("binding_hash")
                    binding_ref = payload.get("binding_ref")
                    binding_obj = None
                    if isinstance(binding_ref, dict):
                        binding_obj = binding_ref.get("object")
                        if "DI-OBJ-01" in enabled_checks:
                            if binding_ref.get("object_type") != "subject_binding":
                                add_failure(t_failures, "DI-OBJ-01", "binding_ref.object_type must be 'subject_binding'", rel_file, line_no)
                            elif isinstance(binding_obj, dict):
                                computed = object_hash("subject_binding", binding_obj)
                                if binding_ref.get("object_hash") != computed:
                                    add_failure(t_failures, "DI-OBJ-01", "binding_ref.object_hash must equal object_hash('subject_binding', binding_ref.object)", rel_file, line_no)
                            else:
                                add_failure(t_failures, "DI-OBJ-01", "binding_ref.object must be an object", rel_file, line_no)

                        if "DI-ISSUE-01" in enabled_checks:
                            ref_hash = binding_ref.get("object_hash")
                            if isinstance(ref_hash, str) and isinstance(binding_hash, str) and binding_hash != ref_hash:
                                add_failure(t_failures, "DI-ISSUE-01", "payload.binding_hash must equal binding_ref.object_hash", rel_file, line_no)
                            issuer = binding_obj.get("issuer") if isinstance(binding_obj, dict) else None
                            if isinstance(issuer, str) and issuer != sender:
                                add_failure(t_failures, "DI-ISSUE-01", "SUBJECT_BINDING_ISSUE sender must equal binding_ref.object.issuer", rel_file, line_no)

                    if isinstance(binding_hash, str) and binding_hash:
                        issued_bindings[binding_hash] = {
                            "object": binding_obj if isinstance(binding_obj, dict) else None,
                            "line_no": line_no,
                        }

                if mtype == "SUBJECT_BINDING_REVOKE":
                    signatures = msg.get("signatures") or []
                    if "DI-SIGNED-01" in enabled_checks and (not isinstance(signatures, list) or len(signatures) == 0):
                        add_failure(t_failures, "DI-SIGNED-01", "SUBJECT_BINDING_REVOKE must include non-empty signatures", rel_file, line_no)

                    binding_hash = payload.get("binding_hash")
                    eff = _parse_iso_datetime(payload.get("effective_at"))
                    if isinstance(binding_hash, str) and binding_hash and eff is not None:
                        prev = revoked_effective_at.get(binding_hash)
                        if prev is None or eff < prev:
                            revoked_effective_at[binding_hash] = eff

                ext = msg.get("ext") or {}
                if "DI-ACT-01" in enabled_checks and isinstance(ext, dict):
                    binding_hash = ext.get("subject_binding_hash")
                    if isinstance(binding_hash, str) and binding_hash:
                        issued = issued_bindings.get(binding_hash)
                        if issued is None:
                            add_failure(t_failures, "DI-ACT-01", "ext.subject_binding_hash must reference a prior SUBJECT_BINDING_ISSUE", rel_file, line_no)
                            continue

                        binding_obj = issued.get("object")
                        if not isinstance(binding_obj, dict):
                            add_failure(t_failures, "DI-ACT-01", "issued binding_ref.object must be present for acting-on-behalf-of validation", rel_file, line_no)
                            continue

                        agent_id = binding_obj.get("agent_id")
                        if not isinstance(agent_id, str) or agent_id != sender:
                            add_failure(t_failures, "DI-ACT-01", "message sender must equal binding agent_id", rel_file, line_no)

                        msg_ts = _parse_iso_datetime(msg.get("timestamp"))
                        exp_ts = _parse_iso_datetime(binding_obj.get("expires_at"))
                        if msg_ts is None or exp_ts is None:
                            add_failure(t_failures, "DI-EXPIRY-01", "binding/message timestamps must be valid date-time", rel_file, line_no)
                        elif msg_ts > exp_ts:
                            add_failure(t_failures, "DI-EXPIRY-01", "ext.subject_binding_hash used after binding expires", rel_file, line_no)

                        revoked_at = revoked_effective_at.get(binding_hash)
                        if revoked_at is not None and msg_ts is not None and revoked_at <= msg_ts:
                            add_failure(t_failures, "DI-REVOKE-01", "ext.subject_binding_hash used at/after effective revocation", rel_file, line_no)

        if any(check in enabled_checks for check in {"PA-JOIN-01", "PA-ACCEPT-01", "PA-MEM-01", "PA-AUTH-01", "PA-MODEL-01"}):
            first_contract = None
            for _, msg in rows:
                if msg.get("message_type") == "CONTRACT_PROPOSE":
                    first_contract = ((msg.get("payload") or {}).get("contract") or {})
                    break

            participants_cfg: dict[str, Any] | None = None
            if isinstance(first_contract, dict):
                ext = first_contract.get("ext") or {}
                if isinstance(ext, dict):
                    participants_cfg = ext.get("participants")
                if participants_cfg is None:
                    extensions = first_contract.get("extensions") or {}
                    if isinstance(extensions, dict):
                        participants_cfg = extensions.get("EXT-PARTICIPANTS")

            participants_cfg = participants_cfg if isinstance(participants_cfg, dict) else {}
            configured_acceptors = participants_cfg.get("acceptors") if isinstance(participants_cfg.get("acceptors"), list) else None
            model = participants_cfg.get("model") if isinstance(participants_cfg.get("model"), str) else None

            joined_at: dict[str, int] = {}
            accepted_at: dict[str, int] = {}
            left_at: dict[str, int] = {}
            accepted_contract_ref_by_participant: dict[str, dict[str, str]] = {}

            for idx, (line_no, msg) in enumerate(rows):
                mtype = msg.get("message_type")
                sender = msg.get("sender")
                payload = msg.get("payload") or {}

                if mtype == "PARTICIPANT_JOIN":
                    participant_id = payload.get("participant_id")
                    if "PA-JOIN-01" in enabled_checks:
                        if not isinstance(participant_id, str) or not participant_id:
                            add_failure(t_failures, "PA-JOIN-01", "PARTICIPANT_JOIN payload.participant_id must be a non-empty string", rel_file, line_no)
                        if not isinstance(sender, str) or participant_id != sender:
                            add_failure(t_failures, "PA-JOIN-01", "PARTICIPANT_JOIN payload.participant_id must equal sender", rel_file, line_no)
                    if isinstance(participant_id, str) and participant_id and participant_id not in joined_at:
                        joined_at[participant_id] = idx

                elif mtype == "PARTICIPANT_ACCEPT":
                    participant_id = payload.get("participant_id")
                    if "PA-ACCEPT-01" in enabled_checks:
                        if not isinstance(participant_id, str) or not participant_id or participant_id not in joined_at:
                            add_failure(t_failures, "PA-ACCEPT-01", "PARTICIPANT_ACCEPT must reference a participant_id with prior PARTICIPANT_JOIN", rel_file, line_no)
                    if "PA-AUTH-01" in enabled_checks and configured_acceptors:
                        if sender not in configured_acceptors:
                            add_failure(t_failures, "PA-AUTH-01", f"PARTICIPANT_ACCEPT sender '{sender}' not in configured acceptors", rel_file, line_no)

                    if isinstance(participant_id, str) and participant_id and participant_id not in accepted_at:
                        accepted_at[participant_id] = idx
                        if "PA-MODEL-01" in enabled_checks and model == "per_participant_acceptance":
                            accepted_contract_ref = payload.get("accepted_contract_ref")
                            if not isinstance(accepted_contract_ref, dict):
                                add_failure(t_failures, "PA-MODEL-01", "per_participant_acceptance requires payload.accepted_contract_ref object", rel_file, line_no)
                            else:
                                required_keys = ("branch_id", "base_version", "head_version")
                                if any(not isinstance(accepted_contract_ref.get(k), str) or not accepted_contract_ref.get(k) for k in required_keys):
                                    add_failure(t_failures, "PA-MODEL-01", "accepted_contract_ref must include non-empty branch_id/base_version/head_version", rel_file, line_no)
                                else:
                                    accepted_contract_ref_by_participant[participant_id] = {
                                        "branch_id": str(accepted_contract_ref.get("branch_id")),
                                        "base_version": str(accepted_contract_ref.get("base_version")),
                                        "head_version": str(accepted_contract_ref.get("head_version")),
                                    }

                elif mtype == "PARTICIPANT_LEAVE":
                    participant_id = payload.get("participant_id")
                    if isinstance(participant_id, str) and participant_id and participant_id not in left_at:
                        left_at[participant_id] = idx

                if "PA-MEM-01" in enabled_checks and isinstance(sender, str) and sender in joined_at:
                    if mtype not in {"PARTICIPANT_JOIN", "PARTICIPANT_ACCEPT", "PARTICIPANT_LEAVE"}:
                        accept_idx = accepted_at.get(sender)
                        if accept_idx is None or idx < accept_idx:
                            add_failure(t_failures, "PA-MEM-01", f"sender '{sender}' emitted {mtype} before PARTICIPANT_ACCEPT", rel_file, line_no)
                        leave_idx = left_at.get(sender)
                        if leave_idx is not None and idx > leave_idx:
                            add_failure(t_failures, "PA-MEM-01", f"sender '{sender}' emitted {mtype} after PARTICIPANT_LEAVE", rel_file, line_no)

                if "PA-MODEL-01" in enabled_checks and model == "per_participant_acceptance" and isinstance(sender, str):
                    if mtype in {"PARTICIPANT_JOIN", "PARTICIPANT_ACCEPT", "PARTICIPANT_LEAVE"}:
                        continue
                    accept_idx = accepted_at.get(sender)
                    if accept_idx is None or idx <= accept_idx:
                        continue
                    expected_contract_ref = accepted_contract_ref_by_participant.get(sender)
                    if expected_contract_ref is None:
                        continue
                    if msg.get("contract_ref") != expected_contract_ref:
                        add_failure(t_failures, "PA-MODEL-01", f"sender '{sender}' message contract_ref must match accepted_contract_ref", rel_file, line_no)

        if any(check in enabled_checks for check in {"RC-CONTRACT-01", "RC-DELIVER-01"}):
            first_contract = None
            first_contract_line_no = 1
            for line_no, msg in rows:
                if msg.get("message_type") == "CONTRACT_PROPOSE":
                    first_contract = ((msg.get("payload") or {}).get("contract") or {})
                    first_contract_line_no = line_no
                    break

            capneg_cfg: dict[str, Any] | None = None
            enforcement_cfg: dict[str, Any] | None = None
            participants_cfg: dict[str, Any] | None = None
            if isinstance(first_contract, dict):
                ext = first_contract.get("ext") or {}
                if isinstance(ext, dict):
                    capneg_cfg = ext.get("capneg")
                    enforcement_cfg = ext.get("enforcement")
                    participants_cfg = ext.get("participants")
                if enforcement_cfg is None or participants_cfg is None:
                    extensions = first_contract.get("extensions") or {}
                    if isinstance(extensions, dict):
                        if enforcement_cfg is None:
                            enforcement_cfg = extensions.get("EXT-ENFORCEMENT")
                        if participants_cfg is None:
                            participants_cfg = extensions.get("EXT-PARTICIPANTS")

            capneg_cfg = capneg_cfg if isinstance(capneg_cfg, dict) else None
            enforcement_cfg = enforcement_cfg if isinstance(enforcement_cfg, dict) else None
            participants_cfg = participants_cfg if isinstance(participants_cfg, dict) else None

            mediators: list[str] = []
            if isinstance(enforcement_cfg, dict):
                raw_mediators = enforcement_cfg.get("mediators")
                if isinstance(raw_mediators, list):
                    mediators = [v for v in raw_mediators if isinstance(v, str) and v]

            if "RC-CONTRACT-01" in enabled_checks:
                if capneg_cfg is None:
                    add_failure(t_failures, "RC-CONTRACT-01", "contract.ext.capneg must be present", rel_file, first_contract_line_no)
                else:
                    negotiation_result_hash = capneg_cfg.get("negotiation_result_hash")
                    selected = capneg_cfg.get("selected")
                    if not isinstance(negotiation_result_hash, str) or not negotiation_result_hash:
                        add_failure(t_failures, "RC-CONTRACT-01", "contract.ext.capneg.negotiation_result_hash must be a non-empty string", rel_file, first_contract_line_no)
                    if not isinstance(selected, dict):
                        add_failure(t_failures, "RC-CONTRACT-01", "contract.ext.capneg.selected must be an object", rel_file, first_contract_line_no)

                    expected_negotiation_result = None
                    for _, candidate in rows:
                        if candidate.get("message_type") == "CAPABILITIES_PROPOSE":
                            nr = (candidate.get("payload") or {}).get("negotiation_result")
                            if isinstance(nr, dict):
                                expected_negotiation_result = nr
                                break

                    expected_hash = None
                    if isinstance(expected_negotiation_result, dict):
                        expected_hash = object_hash("capneg.negotiation_result", expected_negotiation_result)
                        if isinstance(negotiation_result_hash, str) and negotiation_result_hash != expected_hash:
                            add_failure(t_failures, "RC-CONTRACT-01", "contract.ext.capneg.negotiation_result_hash must match CAPABILITIES_PROPOSE negotiation_result hash", rel_file, first_contract_line_no)
                        expected_selected = expected_negotiation_result.get("selected")
                        if isinstance(selected, dict) and isinstance(expected_selected, dict) and selected != expected_selected:
                            add_failure(t_failures, "RC-CONTRACT-01", "contract.ext.capneg.selected must match CAPABILITIES_PROPOSE negotiation_result.selected", rel_file, first_contract_line_no)

                    for line_no, candidate in rows:
                        if candidate.get("message_type") != "CAPABILITIES_ACCEPT":
                            continue
                        cap_payload = candidate.get("payload") or {}
                        if cap_payload.get("accepted") is not True:
                            continue
                        accept_nr = cap_payload.get("negotiation_result")
                        accept_hash = cap_payload.get("negotiation_result_hash")
                        if isinstance(expected_hash, str):
                            if isinstance(accept_nr, dict):
                                computed_accept = object_hash("capneg.negotiation_result", accept_nr)
                                if computed_accept != expected_hash:
                                    add_failure(t_failures, "RC-CONTRACT-01", "CAPABILITIES_ACCEPT negotiation_result must match CAPABILITIES_PROPOSE negotiation_result hash", rel_file, line_no)
                            if isinstance(accept_hash, str) and accept_hash != expected_hash:
                                add_failure(t_failures, "RC-CONTRACT-01", "CAPABILITIES_ACCEPT negotiation_result_hash must match CAPABILITIES_PROPOSE negotiation_result hash", rel_file, line_no)

                if enforcement_cfg is None:
                    add_failure(t_failures, "RC-CONTRACT-01", "contract.ext.enforcement (or contract.extensions['EXT-ENFORCEMENT']) must be present", rel_file, first_contract_line_no)
                else:
                    if enforcement_cfg.get("mode") != "blocking":
                        add_failure(t_failures, "RC-CONTRACT-01", "enforcement mode must be 'blocking'", rel_file, first_contract_line_no)
                    if not mediators:
                        add_failure(t_failures, "RC-CONTRACT-01", "enforcement mediators must be a non-empty array", rel_file, first_contract_line_no)

                if participants_cfg is None:
                    add_failure(t_failures, "RC-CONTRACT-01", "contract.ext.participants (or contract.extensions['EXT-PARTICIPANTS']) must be present", rel_file, first_contract_line_no)

            if "RC-DELIVER-01" in enabled_checks and mediators:
                allowed_senders = set(mediators)
                for line_no, msg in rows:
                    if msg.get("message_type") != "CONTENT_DELIVER":
                        continue
                    sender = msg.get("sender")
                    if sender not in allowed_senders:
                        add_failure(
                            t_failures,
                            "RC-DELIVER-01",
                            f"CONTENT_DELIVER sender '{sender}' is not listed in contract mediators",
                            rel_file,
                            line_no,
                        )


        if any(check in enabled_checks for check in {"TG-REQ-01", "TG-BIND-01", "TG-AUTH-01", "TG-MODE-01"}):
            first_contract = None
            for _, msg in rows:
                if msg.get("message_type") == "CONTRACT_PROPOSE":
                    first_contract = ((msg.get("payload") or {}).get("contract") or {})
                    break

            tool_gating_cfg: dict[str, Any] | None = None
            if isinstance(first_contract, dict):
                ext = first_contract.get("ext") or {}
                if isinstance(ext, dict):
                    tool_gating_cfg = ext.get("tool_gating")
                if tool_gating_cfg is None:
                    extensions = first_contract.get("extensions") or {}
                    if isinstance(extensions, dict):
                        tool_gating_cfg = extensions.get("EXT-TOOL-GATING")

            tool_gating_cfg = tool_gating_cfg if isinstance(tool_gating_cfg, dict) else {}
            mode = tool_gating_cfg.get("mode") if isinstance(tool_gating_cfg.get("mode"), str) else None
            acceptors = tool_gating_cfg.get("acceptors") if isinstance(tool_gating_cfg.get("acceptors"), list) else None

            request_hash_by_line: dict[int, str] = {}
            prior_request_hashes: set[str] = set()
            verdict_by_id: dict[str, dict[str, Any]] = {}
            attest_rows: list[tuple[int, int, dict[str, Any], dict[str, Any]]] = []
            result_rows: list[tuple[int, int, dict[str, Any], dict[str, Any], str | None]] = []

            for idx, (line_no, msg) in enumerate(rows):
                mtype = msg.get("message_type")
                payload = msg.get("payload") or {}
                sender = msg.get("sender")

                if mtype == "TOOL_CALL_REQUEST":
                    if "TG-REQ-01" in enabled_checks:
                        tool_id = payload.get("tool_id")
                        operation = payload.get("operation")
                        if not isinstance(tool_id, str) or not tool_id:
                            add_failure(t_failures, "TG-REQ-01", "TOOL_CALL_REQUEST payload.tool_id must be a non-empty string", rel_file, line_no)
                        if not isinstance(operation, str) or not operation:
                            add_failure(t_failures, "TG-REQ-01", "TOOL_CALL_REQUEST payload.operation must be a non-empty string", rel_file, line_no)
                    mh = msg.get("message_hash")
                    if isinstance(mh, str):
                        prior_request_hashes.add(mh)
                        request_hash_by_line[idx] = mh

                if mtype == "TOOL_CALL_VERDICT":
                    if "TG-AUTH-01" in enabled_checks and acceptors:
                        if sender not in acceptors:
                            add_failure(t_failures, "TG-AUTH-01", f"TOOL_CALL_VERDICT sender '{sender}' not in configured acceptors", rel_file, line_no)
                    verdict_id = msg.get("message_id")
                    if isinstance(verdict_id, str):
                        verdict_by_id[verdict_id] = msg

                if mtype == "TOOL_CALL_ATTEST":
                    if "TG-AUTH-01" in enabled_checks and acceptors:
                        if sender not in acceptors:
                            add_failure(t_failures, "TG-AUTH-01", f"TOOL_CALL_ATTEST sender '{sender}' not in configured acceptors", rel_file, line_no)
                    attest_rows.append((idx, line_no, msg, payload))

                if mtype in {"TOOL_CALL_VERDICT", "TOOL_CALL_RESULT", "TOOL_CALL_ATTEST"}:
                    if "TG-BIND-01" in enabled_checks:
                        target_request_hash = payload.get("target_request_hash")
                        if not isinstance(target_request_hash, str) or target_request_hash not in prior_request_hashes:
                            add_failure(t_failures, "TG-BIND-01", f"{mtype} payload.target_request_hash must reference an earlier TOOL_CALL_REQUEST.message_hash", rel_file, line_no)

                if mtype == "TOOL_CALL_RESULT":
                    result_rows.append((idx, line_no, msg, payload, msg.get("message_hash") if isinstance(msg.get("message_hash"), str) else None))

            if "TG-MODE-01" in enabled_checks and mode == "blocking":
                for _, line_no, _, payload, _ in result_rows:
                    verdict_ref = payload.get("verdict_ref")
                    target_request_hash = payload.get("target_request_hash")
                    if not isinstance(verdict_ref, str) or not verdict_ref:
                        add_failure(t_failures, "TG-MODE-01", "blocking mode requires TOOL_CALL_RESULT payload.verdict_ref", rel_file, line_no)
                        continue
                    verdict_msg = verdict_by_id.get(verdict_ref)
                    if verdict_msg is None:
                        add_failure(t_failures, "TG-MODE-01", f"blocking mode verdict_ref '{verdict_ref}' not found", rel_file, line_no)
                        continue
                    vp = verdict_msg.get("payload") or {}
                    if vp.get("decision") != "ALLOW" or vp.get("target_request_hash") != target_request_hash:
                        add_failure(t_failures, "TG-MODE-01", "blocking mode requires verdict_ref to point to prior ALLOW verdict for same target_request_hash", rel_file, line_no)

            if "TG-MODE-01" in enabled_checks and mode == "audit":
                for result_idx, line_no, _, payload, result_hash in result_rows:
                    target_request_hash = payload.get("target_request_hash")
                    matched = False
                    for attest_idx, _, _, attest_payload in attest_rows:
                        if attest_idx <= result_idx:
                            continue
                        if attest_payload.get("target_request_hash") == target_request_hash and attest_payload.get("target_result_hash") == result_hash:
                            matched = True
                            break
                    if not matched:
                        add_failure(t_failures, "TG-MODE-01", "audit mode requires later TOOL_CALL_ATTEST bound to TOOL_CALL_RESULT.message_hash and target_request_hash", rel_file, line_no)


        if "AL-ALERT-CODES-01" in enabled_checks or "AL-ALERT-ACTIONS-01" in enabled_checks:
            for line_no, msg in rows:
                if msg.get("message_type") != "ALERT":
                    continue
                payload = msg.get("payload") or {}
                if "AL-ALERT-CODES-01" in enabled_checks:
                    code = payload.get("code")
                    if code not in alert_codes_registry:
                        add_failure(t_failures, "AL-ALERT-CODES-01", f"unknown alert code '{code}'", rel_file, line_no)
                if "AL-ALERT-ACTIONS-01" in enabled_checks:
                    for action in payload.get("recommended_actions", []) or []:
                        if action not in alert_recommended_actions:
                            add_failure(t_failures, "AL-ALERT-ACTIONS-01", f"unknown recommended_action '{action}'", rel_file, line_no)

        if "AL-VERBOSITY-01" in enabled_checks:
            for line_no, msg in rows:
                if msg.get("message_type") != "ALERT":
                    continue
                payload = msg.get("payload") or {}
                message = payload.get("message")
                if isinstance(message, str) and len(message) > 256:
                    add_failure(t_failures, "AL-VERBOSITY-01", f"ALERT payload.message exceeds 256 characters (got {len(message)})", rel_file, line_no)
                if "details" in payload:
                    try:
                        details_size = len(canonicalize_json(payload.get("details")))
                    except Exception as exc:
                        add_failure(t_failures, "AL-VERBOSITY-01", f"ALERT payload.details canonicalization failed: {exc}", rel_file, line_no)
                        continue
                    if details_size > 4096:
                        add_failure(
                            t_failures,
                            "AL-VERBOSITY-01",
                            f"ALERT payload.details canonical JSON exceeds 4096 bytes (got {details_size})",
                            rel_file,
                            line_no,
                        )

        if any(check in enabled_checks for check in {"RS-ACTIONS-01", "RS-RESUME-MATCH-01", "RS-LOOP-01", "RS-PROBING-01"}):
            request_rows: list[tuple[int, dict[str, Any]]] = []
            response_rows: dict[tuple[str, str], list[tuple[int, dict[str, Any]]]] = {}

            for line_no, msg in rows:
                if msg.get("message_type") == "RESUME_REQUEST":
                    payload = msg.get("payload") or {}
                    request_rows.append((line_no, payload))
                elif msg.get("message_type") == "RESUME_RESPONSE":
                    payload = msg.get("payload") or {}
                    key = (str(payload.get("resume_id")), str(payload.get("session_id")))
                    response_rows.setdefault(key, []).append((line_no, payload))

                    if "RS-ACTIONS-01" in enabled_checks:
                        for action in payload.get("recommended_actions", []) or []:
                            if action not in alert_recommended_actions:
                                add_failure(t_failures, "RS-ACTIONS-01", f"unknown recommended_action '{action}'", rel_file, line_no)

            if "RS-RESUME-MATCH-01" in enabled_checks:
                for line_no, req_payload in request_rows:
                    req_resume_id = req_payload.get("resume_id")
                    req_session_id = req_payload.get("session_id")
                    req_last_seen = req_payload.get("last_seen_message_hash")
                    key = (str(req_resume_id), str(req_session_id))
                    candidates = response_rows.get(key, [])
                    if not candidates:
                        add_failure(
                            t_failures,
                            "RS-RESUME-MATCH-01",
                            f"missing RESUME_RESPONSE for resume_id='{req_resume_id}' session_id='{req_session_id}'",
                            rel_file,
                            line_no,
                        )
                        continue

                    matching = [c for c in candidates if c[0] > line_no]
                    resp_line_no, resp_payload = matching[0] if matching else candidates[0]

                    if resp_payload.get("resume_id") != req_resume_id:
                        add_failure(t_failures, "RS-RESUME-MATCH-01", "response.resume_id does not match request.resume_id", rel_file, resp_line_no)
                    if resp_payload.get("session_id") != req_session_id:
                        add_failure(t_failures, "RS-RESUME-MATCH-01", "response.session_id does not match request.session_id", rel_file, resp_line_no)

                    current_head_hash = resp_payload.get("current_head_hash")
                    if not isinstance(current_head_hash, str):
                        add_failure(t_failures, "RS-RESUME-MATCH-01", "response.current_head_hash must be a string", rel_file, resp_line_no)
                        continue

                    status = resp_payload.get("status")
                    if status == "OK":
                        if current_head_hash != req_last_seen:
                            add_failure(t_failures, "RS-RESUME-MATCH-01", "OK response.current_head_hash must equal request.last_seen_message_hash", rel_file, resp_line_no)
                    elif status == "NEEDS_RESYNC":
                        if current_head_hash == req_last_seen:
                            add_failure(t_failures, "RS-RESUME-MATCH-01", "NEEDS_RESYNC response.current_head_hash must differ from request.last_seen_message_hash", rel_file, resp_line_no)

            if "RS-LOOP-01" in enabled_checks:
                streak = 0
                anchor: tuple[str, str, str] | None = None
                idx = 0
                while idx < len(rows):
                    line_no, msg = rows[idx]
                    if msg.get("message_type") != "RESUME_REQUEST":
                        streak = 0
                        anchor = None
                        idx += 1
                        continue

                    req_payload = msg.get("payload") or {}
                    if idx + 1 >= len(rows) or rows[idx + 1][1].get("message_type") != "RESUME_RESPONSE":
                        streak = 0
                        anchor = None
                        idx += 1
                        continue

                    resp_line_no, resp_msg = rows[idx + 1]
                    resp_payload = resp_msg.get("payload") or {}
                    triple = (
                        str(req_payload.get("session_id")),
                        str(req_payload.get("last_seen_message_hash")),
                        str(resp_payload.get("current_head_hash")),
                    )
                    same_session = str(resp_payload.get("session_id")) == triple[0]
                    needs_resync = resp_payload.get("status") == "NEEDS_RESYNC"
                    if same_session and needs_resync:
                        if anchor == triple:
                            streak += 1
                        else:
                            anchor = triple
                            streak = 1
                        if streak >= 3:
                            add_failure(
                                t_failures,
                                "RS-LOOP-01",
                                "detected repeated NEEDS_RESYNC loop without head progress (>=3 consecutive request/response cycles)",
                                rel_file,
                                resp_line_no,
                            )
                            break
                    else:
                        streak = 0
                        anchor = None

                    idx += 2

            if "RS-PROBING-01" in enabled_checks:
                probing_sessions_by_sender: dict[str, set[str]] = {}
                successful_resume_by_sender: dict[str, bool] = {}

                for idx, (_, msg) in enumerate(rows):
                    if msg.get("message_type") != "RESUME_REQUEST":
                        continue

                    sender = msg.get("sender")
                    req_payload = msg.get("payload") or {}
                    session_id = req_payload.get("session_id")
                    if not isinstance(sender, str) or not isinstance(session_id, str):
                        continue

                    matched_response = None
                    for _, candidate in rows[idx + 1:]:
                        if candidate.get("message_type") != "RESUME_RESPONSE":
                            continue
                        cand_payload = candidate.get("payload") or {}
                        if cand_payload.get("resume_id") == req_payload.get("resume_id") and cand_payload.get("session_id") == session_id:
                            matched_response = cand_payload
                            break

                    if matched_response is None:
                        continue

                    status = matched_response.get("status")
                    if status in {"OK", "NEEDS_RESYNC"}:
                        successful_resume_by_sender[sender] = True
                    elif status == "UNKNOWN_SESSION":
                        probing_sessions_by_sender.setdefault(sender, set()).add(session_id)

                for sender, probed in probing_sessions_by_sender.items():
                    if successful_resume_by_sender.get(sender):
                        continue
                    if len(probed) >= 5:
                        add_failure(
                            t_failures,
                            "RS-PROBING-01",
                            f"detected RESUME_REQUEST probing by sender '{sender}': UNKNOWN_SESSION across {len(probed)} distinct session_id values",
                            rel_file,
                            None,
                        )

        if "ENF-SANCTION-CODES-01" in enabled_checks:
            namespaced_dash = re.compile(r"^x-[a-z0-9]+[a-z0-9._-]*$")
            namespaced_colon = re.compile(r"^[a-z0-9]+:[a-z0-9][a-z0-9._-]*$")
            for line_no, msg in rows:
                if msg.get("message_type") != "ENFORCEMENT_VERDICT":
                    continue
                sanctions = (msg.get("payload") or {}).get("sanctions", []) or []
                for sanction in sanctions:
                    code = sanction.get("code") if isinstance(sanction, dict) else None
                    if not isinstance(code, str):
                        add_failure(t_failures, "ENF-SANCTION-CODES-01", "sanctions[].code must be a string", rel_file, line_no)
                        continue
                    if code in enforcement_sanction_codes:
                        continue
                    if namespaced_dash.match(code) or namespaced_colon.match(code):
                        continue
                    add_failure(t_failures, "ENF-SANCTION-CODES-01", f"unknown sanction code '{code}'", rel_file, line_no)

        if "ENF-AUTH-01" in enabled_checks:
            first_contract = None
            for _, msg in rows:
                if msg.get("message_type") == "CONTRACT_PROPOSE":
                    first_contract = ((msg.get("payload") or {}).get("contract") or {})
                    break

            enforcement_cfg = None
            if isinstance(first_contract, dict):
                ext = first_contract.get("ext") or {}
                if isinstance(ext, dict):
                    enforcement_cfg = ext.get("enforcement")
                if enforcement_cfg is None:
                    extensions = first_contract.get("extensions") or {}
                    if isinstance(extensions, dict):
                        enforcement_cfg = extensions.get("EXT-ENFORCEMENT")

            if isinstance(enforcement_cfg, dict):
                allowed = enforcement_cfg.get("enforcers")
                if isinstance(allowed, list) and allowed:
                    allowed_senders = {v for v in allowed if isinstance(v, str)}
                    for line_no, msg in rows:
                        if msg.get("message_type") != "ENFORCEMENT_VERDICT":
                            continue
                        sender = msg.get("sender")
                        if sender not in allowed_senders:
                            add_failure(
                                t_failures,
                                "ENF-AUTH-01",
                                f"ENFORCEMENT_VERDICT sender '{sender}' is not listed in contract enforcers",
                                rel_file,
                                line_no,
                            )

        if "ENF-GATE-01" in enabled_checks:
            first_contract = None
            for _, msg in rows:
                if msg.get("message_type") == "CONTRACT_PROPOSE":
                    first_contract = ((msg.get("payload") or {}).get("contract") or {})
                    break

            enforcement_cfg = None
            if isinstance(first_contract, dict):
                ext = first_contract.get("ext") or {}
                if isinstance(ext, dict):
                    enforcement_cfg = ext.get("enforcement")
                if enforcement_cfg is None:
                    extensions = first_contract.get("extensions") or {}
                    if isinstance(extensions, dict):
                        enforcement_cfg = extensions.get("EXT-ENFORCEMENT")

            if isinstance(enforcement_cfg, dict) and enforcement_cfg.get("mode") == "blocking":
                verdicts_by_id = {
                    msg.get("message_id"): msg
                    for _, msg in rows
                    if msg.get("message_type") == "ENFORCEMENT_VERDICT"
                }
                gated_types = enforcement_cfg.get("gated_message_types")
                for line_no, msg in rows:
                    if msg.get("message_type") != "CONTENT_DELIVER":
                        continue
                    payload = msg.get("payload") or {}
                    verdict_message_id = payload.get("verdict_message_id")
                    verdict_msg = verdicts_by_id.get(verdict_message_id)
                    if verdict_msg is None:
                        add_failure(t_failures, "ENF-GATE-01", f"missing ENFORCEMENT_VERDICT for verdict_message_id '{verdict_message_id}'", rel_file, line_no)
                        continue

                    verdict_payload = verdict_msg.get("payload") or {}
                    if verdict_payload.get("decision") != "ALLOW":
                        add_failure(t_failures, "ENF-GATE-01", "CONTENT_DELIVER references non-ALLOW verdict", rel_file, line_no)

                    original_hash = payload.get("original_message_hash")
                    if verdict_payload.get("target_message_hash") != original_hash:
                        add_failure(t_failures, "ENF-GATE-01", "verdict target_message_hash does not match delivery original_message_hash", rel_file, line_no)

                    original_message = payload.get("original_message") or {}
                    if original_message.get("message_hash") != original_hash:
                        add_failure(t_failures, "ENF-GATE-01", "embedded original_message.message_hash does not match original_message_hash", rel_file, line_no)

                    if gated_types is not None and original_message.get("message_type") not in gated_types:
                        add_failure(t_failures, "ENF-GATE-01", "embedded original_message.message_type is not listed in gated_message_types", rel_file, line_no)

        if "ENF-VERDICT-STORM-01" in enabled_checks:
            verdict_counts: dict[str, int] = {}
            for line_no, msg in rows:
                if msg.get("message_type") != "ENFORCEMENT_VERDICT":
                    continue
                payload = msg.get("payload") or {}
                target_hash = payload.get("target_message_hash")
                if not isinstance(target_hash, str):
                    continue
                verdict_counts[target_hash] = verdict_counts.get(target_hash, 0) + 1
                if verdict_counts[target_hash] > 1:
                    add_failure(
                        t_failures,
                        "ENF-VERDICT-STORM-01",
                        f"multiple ENFORCEMENT_VERDICT messages reference target_message_hash '{target_hash}'",
                        rel_file,
                        line_no,
                    )

        failures.extend(_evaluate_transcript_expectations(transcript, t_failures, rel_file))

    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    passed = not failures
    suite_mark = suite.get("compatibility_mark")
    marks = [suite_mark] if (passed and not degraded and isinstance(suite_mark, str)) else []

    return {
        "aicp_version": version,
        "suite_id": suite["suite_id"],
        "suite_version": suite["suite_version"],
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "passed": passed,
        "failures": failures,
        "compatibility_marks": marks,
        "degraded": degraded,
        "degraded_reasons": degraded_reasons,
        "skipped_checks": skipped_checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run AICP conformance suite")
    parser.add_argument("--suite", required=True, help="Path to suite catalog JSON")
    parser.add_argument("--out", required=True, help="Path to output report JSON")
    args = parser.parse_args()

    suite_path = (ROOT / args.suite).resolve() if not Path(args.suite).is_absolute() else Path(args.suite)
    out_path = (ROOT / args.out).resolve() if not Path(args.out).is_absolute() else Path(args.out)

    try:
        report = run_suite(suite_path)
    except Exception as exc:
        print(f"[FAIL] {exc}")
        return 1

    if Draft202012Validator is None:
        print("[WARN] jsonschema is not installed. Skipping message/schema payload validation checks.")
    if not signature_verifier_available():
        print("[WARN] cryptography is not installed. Signature verification checks are limited.")

    if Draft202012Validator is not None:
        report_schema_path = ROOT / "conformance/conformance_report_schema.json"
        report_schema = load_json(report_schema_path)
        _build_validator(report_schema, report_schema_path).validate(report)
    else:
        print("[WARN] jsonschema is not installed. Skipping conformance report schema validation.")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    status = 'PASSED' if report['passed'] else 'FAILED'
    if report.get('degraded'):
        status = f"{status} (DEGRADED)"
    print(f"Conformance {status}: {report['suite_id']} -> {_display_path(out_path)}")
    if report["failures"]:
        for f in report["failures"]:
            print(f" - [{f['test_id']}] {f['file']}:{f['line']} {f['message']}")

    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
