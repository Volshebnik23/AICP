#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone, timedelta
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




def _validator_for_schema_pointer(schema: dict[str, Any], pointer: str) -> Any:
    if Draft202012Validator is None:
        return None
    norm_pointer = _normalize_pointer(pointer)
    _resolve_json_pointer(schema, norm_pointer)
    wrapper = {
        "$schema": schema.get("$schema"),
        "$id": schema.get("$id"),
        "$ref": f"#{norm_pointer}" if norm_pointer else "#",
        "$defs": schema.get("$defs", {}),
    }
    return Draft202012Validator(wrapper)


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


def _contract_ext_object(contract: Any, ext_key: str, extension_id: str) -> dict[str, Any] | None:
    if not isinstance(contract, dict):
        return None
    ext = contract.get("ext")
    if isinstance(ext, dict) and isinstance(ext.get(ext_key), dict):
        return ext.get(ext_key)
    extensions = contract.get("extensions")
    if isinstance(extensions, dict) and isinstance(extensions.get(extension_id), dict):
        return extensions.get(extension_id)
    return None


def _flatten_authority_subset(value: Any) -> set[str]:
    out: set[str] = set()
    if not isinstance(value, dict):
        return out
    for key, entries in value.items():
        if not isinstance(key, str):
            continue
        if isinstance(entries, list):
            for entry in entries:
                if isinstance(entry, str) and entry:
                    out.add(f"{key}.{entry}")
        elif isinstance(entries, str) and entries:
            out.add(f"{key}.{entries}")
    return out


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
    seen_cases_by_id: dict[str, dict[str, Any]] = {}
    loaded_cases: list[tuple[str, dict[str, Any]]] = []

    trust_signal_ids: set[str] = set()
    attestation_type_ids: set[str] = set()
    status_codes: set[str] = set()
    revocation_reason_codes: set[str] = set()
    if any(check in enabled_checks for check in {"TR-REGISTRY-01", "TR-CHAIN-01"}):
        trust_signal_ids = {
            e.get("id") for e in load_json(ROOT / "registry/trust_signal_types.json") if isinstance(e, dict)
        }
        attestation_type_ids = {
            e.get("id") for e in load_json(ROOT / "registry/attestation_types.json") if isinstance(e, dict)
        }
    if any(check in enabled_checks for check in {"SR-REGISTRY-01", "SR-CHAIN-01"}):
        status_codes = {
            e.get("id") for e in load_json(ROOT / "registry/status_assertion_codes.json") if isinstance(e, dict)
        }
        revocation_reason_codes = {
            e.get("id") for e in load_json(ROOT / "registry/revocation_reason_codes.json") if isinstance(e, dict)
        }

    def _session_id_from_path(path: str) -> str | None:
        if not isinstance(path, str) or '/sessions/' not in path:
            return None
        tail = path.split('/sessions/', 1)[1]
        if not tail:
            return None
        segment = tail.split('/', 1)[0]
        return segment or None

    for rel_case in suite.get("cases", []):
        case_path = ROOT / rel_case
        try:
            case_obj = load_json(case_path)
        except Exception as exc:
            add_failure(failures, "TB-CASE-JSON-01", f"invalid JSON case file: {exc}", rel_case, None)
            continue

        loaded_cases.append((rel_case, case_obj))

        if case_validator is not None:
            for err in sorted(case_validator.iter_errors(case_obj), key=lambda e: list(e.path)):
                add_failure(failures, "TB-SCHEMA-01", err.message, rel_case, None)

        extracted_messages: list[dict[str, Any]] = []
        embedded_messages = case_obj.get("embedded_messages")
        if isinstance(embedded_messages, list):
            extracted_messages = [m for m in embedded_messages if isinstance(m, dict)]
        elif isinstance(case_obj.get("embedded_message"), dict):
            extracted_messages = [case_obj.get("embedded_message")]
        else:
            mcp_msg = (
                (case_obj.get("mcp_request") or {})
                .get("params", {})
                .get("arguments", {})
                .get("message")
            )
            if isinstance(mcp_msg, dict):
                extracted_messages = [mcp_msg]


        channel_properties = case_obj.get("channel_properties")

        if "TB-CP-ORDERING-01" in enabled_checks:
            ordered = isinstance(channel_properties, dict) and channel_properties.get("CP-ORDERING-0.1") == "ordered"
            if ordered and len(extracted_messages) >= 2:
                for idx in range(1, len(extracted_messages)):
                    prev = extracted_messages[idx - 1]
                    current = extracted_messages[idx]
                    prev_hash = prev.get("message_hash")
                    current_prev_hash = current.get("prev_msg_hash")
                    if not isinstance(prev_hash, str) or not prev_hash:
                        add_failure(
                            failures,
                            "TB-CP-ORDERING-01",
                            f"ordered mode requires message_hash on embedded_messages[{idx - 1}]",
                            rel_case,
                            None,
                        )
                        break
                    if not isinstance(current_prev_hash, str) or not current_prev_hash:
                        add_failure(
                            failures,
                            "TB-CP-ORDERING-01",
                            f"ordered mode requires prev_msg_hash on embedded_messages[{idx}]",
                            rel_case,
                            None,
                        )
                        break
                    if current_prev_hash != prev_hash:
                        add_failure(
                            failures,
                            "TB-CP-ORDERING-01",
                            f"embedded_messages[{idx}].prev_msg_hash must equal embedded_messages[{idx - 1}].message_hash",
                            rel_case,
                            None,
                        )
                        break

        if "TB-CP-RELIABILITY-01" in enabled_checks:
            at_most_once = isinstance(channel_properties, dict) and channel_properties.get("CP-RELIABILITY-0.1") == "at_most_once"
            if at_most_once:
                seen_ids: set[str] = set()
                duplicate_ids: set[str] = set()
                for msg in extracted_messages:
                    mid = msg.get("message_id")
                    if isinstance(mid, str):
                        if mid in seen_ids:
                            duplicate_ids.add(mid)
                        else:
                            seen_ids.add(mid)
                if duplicate_ids:
                    add_failure(
                        failures,
                        "TB-CP-RELIABILITY-01",
                        f"at_most_once forbids duplicate message_id values: {sorted(duplicate_ids)}",
                        rel_case,
                        None,
                    )

        if "TB-CP-RELIABILITY-02" in enabled_checks:
            at_least_once = isinstance(channel_properties, dict) and channel_properties.get("CP-RELIABILITY-0.1") == "at_least_once"
            if at_least_once:
                seen_hashes: dict[str, str] = {}
                for msg in extracted_messages:
                    mid = msg.get("message_id")
                    mhash = msg.get("message_hash")
                    if not isinstance(mid, str) or not isinstance(mhash, str):
                        continue
                    prior_hash = seen_hashes.get(mid)
                    if prior_hash is None:
                        seen_hashes[mid] = mhash
                    elif prior_hash != mhash:
                        add_failure(
                            failures,
                            "TB-CP-RELIABILITY-02",
                            f"at_least_once duplicate message_id '{mid}' has inconsistent message_hash values",
                            rel_case,
                            None,
                        )
                        break

        ws_frames_out = case_obj.get("ws_frames_out")
        ws_frames_in = case_obj.get("ws_frames_in")

        if "TB-WS-PULL-01" in enabled_checks and case_obj.get("operation") == "wsPullMessages":
            if not isinstance(ws_frames_in, list) or not ws_frames_in:
                add_failure(failures, "TB-WS-PULL-01", "wsPullMessages requires ws_frames_in with at least one frame", rel_case, None)
            elif not isinstance(ws_frames_in[0], dict) or ws_frames_in[0].get("type") != "pull":
                add_failure(failures, "TB-WS-PULL-01", "wsPullMessages requires first inbound frame to be type='pull'", rel_case, None)
            else:
                limit = ws_frames_in[0].get("limit")
                if not isinstance(limit, int):
                    add_failure(failures, "TB-WS-PULL-01", "wsPullMessages pull frame must include integer limit", rel_case, None)
                elif not isinstance(ws_frames_out, list) or not ws_frames_out:
                    add_failure(failures, "TB-WS-PULL-01", "wsPullMessages requires ws_frames_out frames", rel_case, None)
                else:
                    message_frames = [f for f in ws_frames_out if isinstance(f, dict) and f.get("type") == "messages"]
                    overload_present = any(isinstance(f, dict) and f.get("type") == "overload" for f in ws_frames_out)
                    if not message_frames and not overload_present:
                        add_failure(
                            failures,
                            "TB-WS-PULL-01",
                            "wsPullMessages requires at least one messages frame unless overload-only",
                            rel_case,
                            None,
                        )
                    if message_frames:
                        for idx, frame in enumerate(message_frames):
                            more = frame.get("more")
                            if idx < len(message_frames) - 1 and more is not True:
                                add_failure(
                                    failures,
                                    "TB-WS-PULL-01",
                                    "all non-final messages frames must set more=true",
                                    rel_case,
                                    None,
                                )
                                break
                            if idx == len(message_frames) - 1 and more is not False:
                                add_failure(
                                    failures,
                                    "TB-WS-PULL-01",
                                    "last messages frame must set more=false",
                                    rel_case,
                                    None,
                                )
                                break
                        if isinstance(limit, int):
                            delivered = 0
                            for frame in message_frames:
                                msgs = frame.get("messages")
                                if isinstance(msgs, list):
                                    delivered += len(msgs)
                            if delivered > limit:
                                add_failure(
                                    failures,
                                    "TB-WS-PULL-01",
                                    f"delivered messages ({delivered}) exceed pull limit ({limit})",
                                    rel_case,
                                    None,
                                )

        if "TB-WS-FRAME-MIRROR-01" in enabled_checks and isinstance(ws_frames_out, list):
            frame_pairs: set[tuple[str, str]] = set()
            malformed = False
            for frame in ws_frames_out:
                if not isinstance(frame, dict) or frame.get("type") != "messages":
                    continue
                messages = frame.get("messages")
                if not isinstance(messages, list):
                    continue
                for idx, msg in enumerate(messages):
                    if not isinstance(msg, dict):
                        continue
                    mid = msg.get("message_id")
                    mhash = msg.get("message_hash")
                    if not isinstance(mid, str) or not mid or not isinstance(mhash, str) or not mhash:
                        add_failure(
                            failures,
                            "TB-WS-FRAME-MIRROR-01",
                            f"messages frame entry {idx} must include message_id and message_hash",
                            rel_case,
                            None,
                        )
                        malformed = True
                        break
                    frame_pairs.add((mid, mhash))
                if malformed:
                    break
            if not malformed and frame_pairs:
                embedded_pairs = {
                    (msg.get("message_id"), msg.get("message_hash"))
                    for msg in extracted_messages
                    if isinstance(msg.get("message_id"), str) and isinstance(msg.get("message_hash"), str)
                }
                missing_pairs = sorted(frame_pairs - embedded_pairs)
                if missing_pairs:
                    add_failure(
                        failures,
                        "TB-WS-FRAME-MIRROR-01",
                        f"ws messages frame pairs missing in embedded_messages: {missing_pairs}",
                        rel_case,
                        None,
                    )

        if "TB-SSE-PULL-01" in enabled_checks and case_obj.get("operation") in {"ssePullMessages", "sseOverloadEvent"}:
            http_request = case_obj.get("http_request")
            sse_events_out = case_obj.get("sse_events_out")
            if not isinstance(http_request, dict):
                add_failure(failures, "TB-SSE-PULL-01", "SSE pull requires http_request object", rel_case, None)
            else:
                limit_raw = (http_request.get("query") or {}).get("limit") if isinstance(http_request.get("query"), dict) else None
                try:
                    limit = int(limit_raw)
                except Exception:
                    limit = None
                if limit is None:
                    add_failure(failures, "TB-SSE-PULL-01", "SSE pull query.limit must be parseable integer", rel_case, None)
                if not isinstance(sse_events_out, list) or not sse_events_out:
                    add_failure(failures, "TB-SSE-PULL-01", "SSE pull requires non-empty sse_events_out", rel_case, None)
                else:
                    message_events = [e for e in sse_events_out if isinstance(e, dict) and e.get("event") == "messages"]
                    overload_present = any(isinstance(e, dict) and e.get("event") == "overload" for e in sse_events_out)
                    if not message_events and not overload_present:
                        add_failure(failures, "TB-SSE-PULL-01", "SSE pull requires messages events unless overload-only", rel_case, None)
                    if message_events:
                        for idx, event in enumerate(message_events):
                            data = event.get("data") if isinstance(event.get("data"), dict) else {}
                            more = data.get("more")
                            if idx < len(message_events) - 1 and more is not True:
                                add_failure(failures, "TB-SSE-PULL-01", "all non-final SSE messages events must set more=true", rel_case, None)
                                break
                            if idx == len(message_events) - 1 and more is not False:
                                add_failure(failures, "TB-SSE-PULL-01", "last SSE messages event must set more=false", rel_case, None)
                                break
                        if isinstance(limit, int):
                            delivered = 0
                            for event in message_events:
                                data = event.get("data") if isinstance(event.get("data"), dict) else {}
                                msgs = data.get("messages")
                                if isinstance(msgs, list):
                                    delivered += len(msgs)
                            if delivered > limit:
                                add_failure(failures, "TB-SSE-PULL-01", f"SSE delivered messages ({delivered}) exceed limit ({limit})", rel_case, None)

        if "TB-SSE-EVENT-MIRROR-01" in enabled_checks:
            sse_events_out = case_obj.get("sse_events_out")
            if isinstance(sse_events_out, list):
                frame_pairs: set[tuple[str, str]] = set()
                malformed = False
                for event in sse_events_out:
                    if not isinstance(event, dict) or event.get("event") != "messages":
                        continue
                    data = event.get("data")
                    if not isinstance(data, dict):
                        continue
                    messages = data.get("messages")
                    if not isinstance(messages, list):
                        continue
                    for idx, msg in enumerate(messages):
                        if not isinstance(msg, dict):
                            continue
                        mid = msg.get("message_id")
                        mhash = msg.get("message_hash")
                        if not isinstance(mid, str) or not mid or not isinstance(mhash, str) or not mhash:
                            add_failure(failures, "TB-SSE-EVENT-MIRROR-01", f"SSE messages event entry {idx} must include message_id and message_hash", rel_case, None)
                            malformed = True
                            break
                        frame_pairs.add((mid, mhash))
                    if malformed:
                        break
                if not malformed and frame_pairs:
                    embedded_pairs = {
                        (msg.get("message_id"), msg.get("message_hash"))
                        for msg in extracted_messages
                        if isinstance(msg.get("message_id"), str) and isinstance(msg.get("message_hash"), str)
                    }
                    missing_pairs = sorted(frame_pairs - embedded_pairs)
                    if missing_pairs:
                        add_failure(failures, "TB-SSE-EVENT-MIRROR-01", f"SSE messages pairs missing in embedded_messages: {missing_pairs}", rel_case, None)

        if "TB-HTTP-IDEMPOTENCY-01" in enabled_checks and case_obj.get("operation") == "sendMessage":
            http_request = case_obj.get("http_request")
            headers = (http_request.get("headers") if isinstance(http_request, dict) else None)
            idem = headers.get("Idempotency-Key") if isinstance(headers, dict) else None
            embedded_mid = None
            if extracted_messages and isinstance(extracted_messages[0], dict):
                embedded_mid = extracted_messages[0].get("message_id")
            if not isinstance(idem, str) or not idem:
                add_failure(failures, "TB-HTTP-IDEMPOTENCY-01", "sendMessage requires Idempotency-Key header", rel_case, None)
            elif not isinstance(embedded_mid, str) or not embedded_mid:
                add_failure(failures, "TB-HTTP-IDEMPOTENCY-01", "sendMessage requires embedded message_id evidence", rel_case, None)
            elif idem != embedded_mid:
                if not idem.endswith(embedded_mid):
                    add_failure(failures, "TB-HTTP-IDEMPOTENCY-01", "Idempotency-Key must equal message_id or end with it using delimiter -:/", rel_case, None)
                else:
                    prefix = idem[: -len(embedded_mid)]
                    if not prefix or prefix[-1] not in "-:/":
                        add_failure(failures, "TB-HTTP-IDEMPOTENCY-01", "Idempotency-Key suffix delimiter must be one of -:/", rel_case, None)

        if "TB-HTTP-REPLAY-01" in enabled_checks:
            replay_of = case_obj.get("replay_of")
            if isinstance(replay_of, str):
                base_case = seen_cases_by_id.get(replay_of)
                if base_case is None:
                    add_failure(failures, "TB-HTTP-REPLAY-01", f"replay_of references unknown or later case_id '{replay_of}'", rel_case, None)
                else:
                    base_msgs = base_case.get("embedded_messages") if isinstance(base_case.get("embedded_messages"), list) else []
                    cur_msgs = extracted_messages
                    base_msg = base_msgs[0] if base_msgs and isinstance(base_msgs[0], dict) else None
                    cur_msg = cur_msgs[0] if cur_msgs and isinstance(cur_msgs[0], dict) else None
                    if not isinstance(base_msg, dict) or not isinstance(cur_msg, dict):
                        add_failure(failures, "TB-HTTP-REPLAY-01", "replay evidence requires embedded message in both referenced and replay cases", rel_case, None)
                    else:
                        if base_msg.get("message_id") != cur_msg.get("message_id") or base_msg.get("message_hash") != cur_msg.get("message_hash"):
                            add_failure(failures, "TB-HTTP-REPLAY-01", "replay case embedded message_id/message_hash must match referenced case", rel_case, None)
                    base_req = base_case.get("http_request") if isinstance(base_case.get("http_request"), dict) else {}
                    cur_req = case_obj.get("http_request") if isinstance(case_obj.get("http_request"), dict) else {}
                    base_body = base_req.get("body") if isinstance(base_req.get("body"), dict) else {}
                    cur_body = cur_req.get("body") if isinstance(cur_req.get("body"), dict) else {}
                    base_scope = base_body.get("session_id") if isinstance(base_body.get("session_id"), str) else _session_id_from_path(base_req.get("path", ""))
                    cur_scope = cur_body.get("session_id") if isinstance(cur_body.get("session_id"), str) else _session_id_from_path(cur_req.get("path", ""))
                    if isinstance(base_scope, str) and isinstance(cur_scope, str) and base_scope != cur_scope:
                        add_failure(failures, "TB-HTTP-REPLAY-01", "replay_of case must remain in the same session scope as referenced case", rel_case, None)
                    response = case_obj.get("http_response")
                    if not isinstance(response, dict):
                        add_failure(failures, "TB-HTTP-REPLAY-01", "replay case requires http_response object", rel_case, None)
                    else:
                        status = response.get("status")
                        headers = response.get("headers")
                        if status not in {200, 208}:
                            add_failure(failures, "TB-HTTP-REPLAY-01", "replay case status must be 200 or 208", rel_case, None)
                        replay_hdr = headers.get("AICP-Replay") if isinstance(headers, dict) else None
                        if replay_hdr != "true":
                            add_failure(failures, "TB-HTTP-REPLAY-01", "replay case must set response header AICP-Replay: true", rel_case, None)

        if "TB-HTTP-RATELIMIT-01" in enabled_checks and case_obj.get("operation") == "overload":
            response = case_obj.get("http_response")
            if isinstance(response, dict) and response.get("status") == 429:
                headers = response.get("headers") if isinstance(response.get("headers"), dict) else {}
                if not isinstance(headers.get("Retry-After"), str) or not headers.get("Retry-After"):
                    add_failure(failures, "TB-HTTP-RATELIMIT-01", "429 overload responses must include Retry-After header", rel_case, None)
                rate_hints = ["RateLimit-Limit", "RateLimit-Remaining", "RateLimit-Reset"]
                if not any(isinstance(headers.get(name), str) and headers.get(name) for name in rate_hints):
                    add_failure(failures, "TB-HTTP-RATELIMIT-01", "429 overload responses must include at least one RateLimit-* hint header", rel_case, None)

        if "TB-HTTP-AUTH-01" in enabled_checks and isinstance(case_obj.get("auth"), dict):
            auth = case_obj.get("auth")
            http_request = case_obj.get("http_request")
            headers = http_request.get("headers") if isinstance(http_request, dict) and isinstance(http_request.get("headers"), dict) else {}
            expected = None
            if auth.get("scheme") == "bearer" and isinstance(auth.get("token"), str):
                expected = f"Bearer {auth.get('token')}"
            actual = headers.get("Authorization") if isinstance(headers, dict) else None
            if expected is None or actual != expected:
                add_failure(failures, "TB-HTTP-AUTH-01", "auth evidence requires request header Authorization: Bearer <token>", rel_case, None)

        if "TB-SSE-RECONNECT-01" in enabled_checks:
            reconnect_of = case_obj.get("reconnect_of")
            if isinstance(reconnect_of, str):
                referenced_case = seen_cases_by_id.get(reconnect_of)
                if referenced_case is None:
                    add_failure(failures, "TB-SSE-RECONNECT-01", f"reconnect_of references unknown or later case_id '{reconnect_of}'", rel_case, None)
                elif referenced_case.get("operation") != "ssePullMessages":
                    add_failure(failures, "TB-SSE-RECONNECT-01", "reconnect_of must reference an ssePullMessages case", rel_case, None)
                else:
                    ref_events = referenced_case.get("sse_events_out") if isinstance(referenced_case.get("sse_events_out"), list) else []
                    msg_events = [e for e in ref_events if isinstance(e, dict) and e.get("event") == "messages"]
                    if not msg_events:
                        add_failure(failures, "TB-SSE-RECONNECT-01", "referenced ssePullMessages case must include at least one messages event", rel_case, None)
                    else:
                        last_event = msg_events[-1]
                        data = last_event.get("data") if isinstance(last_event.get("data"), dict) else {}
                        expected_cursor = last_event.get("id") if isinstance(last_event.get("id"), str) and last_event.get("id") else data.get("cursor_after_last")
                        request = case_obj.get("http_request")
                        headers = request.get("headers") if isinstance(request, dict) and isinstance(request.get("headers"), dict) else {}
                        query = request.get("query") if isinstance(request, dict) and isinstance(request.get("query"), dict) else {}
                        if not isinstance(expected_cursor, str) or not expected_cursor:
                            add_failure(failures, "TB-SSE-RECONNECT-01", "referenced case must provide reconnect cursor via event id or data.cursor_after_last", rel_case, None)
                        else:
                            if headers.get("Last-Event-ID") != expected_cursor:
                                add_failure(failures, "TB-SSE-RECONNECT-01", f"Last-Event-ID must match reconnect cursor '{expected_cursor}'", rel_case, None)
                            if query.get("after") != expected_cursor:
                                add_failure(failures, "TB-SSE-RECONNECT-01", f"query.after must match reconnect cursor '{expected_cursor}'", rel_case, None)

        trust_anchor_list = case_obj.get("trust_anchor_list") if isinstance(case_obj.get("trust_anchor_list"), dict) else None
        trust_anchor_list_hash = case_obj.get("trust_anchor_list_hash") if isinstance(case_obj.get("trust_anchor_list_hash"), str) else None
        issuer_attestation = case_obj.get("issuer_attestation") if isinstance(case_obj.get("issuer_attestation"), dict) else None
        issuer_attestation_hash = case_obj.get("issuer_attestation_hash") if isinstance(case_obj.get("issuer_attestation_hash"), str) else None
        attestation_signature = case_obj.get("attestation_signature") if isinstance(case_obj.get("attestation_signature"), dict) else None
        expect_trust_valid = bool(case_obj.get("expect_trust_valid"))

        if "TR-ANCHOR-OBJ-01" in enabled_checks and trust_anchor_list is not None:
            try:
                computed_anchor_hash = object_hash("trust_anchor_list", trust_anchor_list)
            except Exception as exc:
                add_failure(failures, "TR-ANCHOR-OBJ-01", f"trust_anchor_list hash recompute error: {exc}", rel_case, None)
            else:
                if computed_anchor_hash != trust_anchor_list_hash:
                    add_failure(failures, "TR-ANCHOR-OBJ-01", "trust_anchor_list_hash must equal object_hash('trust_anchor_list', trust_anchor_list)", rel_case, None)
            anchor_issued = _parse_iso_datetime(trust_anchor_list.get("issued_at"))
            anchor_expires = _parse_iso_datetime(trust_anchor_list.get("expires_at"))
            if anchor_issued is None or anchor_expires is None:
                add_failure(failures, "TR-ANCHOR-OBJ-01", "trust_anchor_list issued_at/expires_at must be valid date-time", rel_case, None)
            elif anchor_issued >= anchor_expires:
                add_failure(failures, "TR-ANCHOR-OBJ-01", "trust_anchor_list issued_at must be earlier than expires_at", rel_case, None)

        trust_chain_valid = False
        if issuer_attestation is not None:
            if "TR-ATTEST-OBJ-01" in enabled_checks:
                try:
                    computed_attestation_hash = object_hash("issuer_attestation", issuer_attestation)
                except Exception as exc:
                    add_failure(failures, "TR-ATTEST-OBJ-01", f"issuer_attestation hash recompute error: {exc}", rel_case, None)
                else:
                    if computed_attestation_hash != issuer_attestation_hash:
                        add_failure(failures, "TR-ATTEST-OBJ-01", "issuer_attestation_hash must equal object_hash('issuer_attestation', issuer_attestation)", rel_case, None)
                if not isinstance(attestation_signature, dict):
                    add_failure(failures, "TR-ATTEST-OBJ-01", "issuer_attestation requires attestation_signature object", rel_case, None)
                else:
                    if attestation_signature.get("object_type") != "issuer_attestation":
                        add_failure(failures, "TR-ATTEST-OBJ-01", "attestation_signature.object_type must be 'issuer_attestation'", rel_case, None)
                    if attestation_signature.get("object_hash") != issuer_attestation_hash:
                        add_failure(failures, "TR-ATTEST-OBJ-01", "attestation_signature.object_hash must equal issuer_attestation_hash", rel_case, None)

            if "TR-REGISTRY-01" in enabled_checks:
                if issuer_attestation.get("attestation_type") not in attestation_type_ids:
                    add_failure(failures, "TR-REGISTRY-01", "issuer_attestation.attestation_type must be registered in registry/attestation_types.json", rel_case, None)
                if issuer_attestation.get("trust_signal") not in trust_signal_ids:
                    add_failure(failures, "TR-REGISTRY-01", "issuer_attestation.trust_signal must be registered in registry/trust_signal_types.json", rel_case, None)

            if "TR-CHAIN-01" in enabled_checks and trust_anchor_list is not None and isinstance(attestation_signature, dict):
                anchors = trust_anchor_list.get("anchors") if isinstance(trust_anchor_list.get("anchors"), list) else []
                signer = attestation_signature.get("signer")
                kid = attestation_signature.get("kid")
                issuer_id = issuer_attestation.get("issuer_id")
                matched_anchor = None
                for anchor in anchors:
                    if not isinstance(anchor, dict):
                        continue
                    if anchor.get("issuer_id") == issuer_id and anchor.get("signer") == signer and anchor.get("kid") == kid:
                        matched_anchor = anchor
                        break
                if matched_anchor is not None and isinstance(matched_anchor.get("public_key_b64url"), str):
                    trust_chain_valid = verify_ed25519(
                        matched_anchor.get("public_key_b64url", ""),
                        str(attestation_signature.get("sig_b64url", "")),
                        str(attestation_signature.get("object_hash", "")),
                    )

                att_issued = _parse_iso_datetime(issuer_attestation.get("issued_at"))
                att_expires = _parse_iso_datetime(issuer_attestation.get("expires_at"))
                anchor_issued = _parse_iso_datetime(trust_anchor_list.get("issued_at"))
                anchor_expires = _parse_iso_datetime(trust_anchor_list.get("expires_at"))
                temporal_valid = (
                    att_issued is not None
                    and att_expires is not None
                    and anchor_issued is not None
                    and anchor_expires is not None
                    and att_issued < att_expires
                    and anchor_issued <= att_issued
                    and att_expires <= anchor_expires
                )
                list_match = issuer_attestation.get("anchor_list_id") == trust_anchor_list.get("anchor_list_id")
                trust_chain_valid = trust_chain_valid and temporal_valid and list_match and matched_anchor is not None

                if expect_trust_valid and not trust_chain_valid:
                    add_failure(failures, "TR-CHAIN-01", "expected valid attestation did not resolve under provided trust_anchor_list", rel_case, None)
                if (not expect_trust_valid) and trust_chain_valid:
                    add_failure(failures, "TR-CHAIN-01", "case marked expect_trust_valid=false but attestation resolved as trusted", rel_case, None)

        status_query = case_obj.get("status_query") if isinstance(case_obj.get("status_query"), dict) else None
        status_query_hash = case_obj.get("status_query_hash") if isinstance(case_obj.get("status_query_hash"), str) else None
        status_assertion = case_obj.get("status_assertion") if isinstance(case_obj.get("status_assertion"), dict) else None
        status_assertion_hash = case_obj.get("status_assertion_hash") if isinstance(case_obj.get("status_assertion_hash"), str) else None
        status_signature = case_obj.get("status_signature") if isinstance(case_obj.get("status_signature"), dict) else None
        observed_at = _parse_iso_datetime(case_obj.get("observed_at"))
        expect_status_valid = bool(case_obj.get("expect_status_valid"))

        if "SR-QUERY-OBJ-01" in enabled_checks and status_query is not None:
            try:
                computed_query_hash = object_hash("status_query", status_query)
            except Exception as exc:
                add_failure(failures, "SR-QUERY-OBJ-01", f"status_query hash recompute error: {exc}", rel_case, None)
            else:
                if computed_query_hash != status_query_hash:
                    add_failure(failures, "SR-QUERY-OBJ-01", "status_query_hash must equal object_hash('status_query', status_query)", rel_case, None)
            if _parse_iso_datetime(status_query.get("status_as_of")) is None:
                add_failure(failures, "SR-QUERY-OBJ-01", "status_query.status_as_of must be valid date-time", rel_case, None)

        status_valid = False
        if status_assertion is not None:
            if "SR-ASSERT-OBJ-01" in enabled_checks:
                try:
                    computed_status_hash = object_hash("status_assertion", status_assertion)
                except Exception as exc:
                    add_failure(failures, "SR-ASSERT-OBJ-01", f"status_assertion hash recompute error: {exc}", rel_case, None)
                else:
                    if computed_status_hash != status_assertion_hash:
                        add_failure(failures, "SR-ASSERT-OBJ-01", "status_assertion_hash must equal object_hash('status_assertion', status_assertion)", rel_case, None)
                if not isinstance(status_signature, dict):
                    add_failure(failures, "SR-ASSERT-OBJ-01", "status_assertion requires status_signature object", rel_case, None)
                else:
                    if status_signature.get("object_type") != "status_assertion":
                        add_failure(failures, "SR-ASSERT-OBJ-01", "status_signature.object_type must be 'status_assertion'", rel_case, None)
                    if status_signature.get("object_hash") != status_assertion_hash:
                        add_failure(failures, "SR-ASSERT-OBJ-01", "status_signature.object_hash must equal status_assertion_hash", rel_case, None)

            if "SR-REGISTRY-01" in enabled_checks:
                if status_assertion.get("status") not in status_codes:
                    add_failure(failures, "SR-REGISTRY-01", "status_assertion.status must be registered in registry/status_assertion_codes.json", rel_case, None)
                if status_assertion.get("status") == "REVOKED" and status_assertion.get("revocation_reason") not in revocation_reason_codes:
                    add_failure(failures, "SR-REGISTRY-01", "REVOKED status_assertion.revocation_reason must be registered in registry/revocation_reason_codes.json", rel_case, None)

            if "SR-CHAIN-01" in enabled_checks and isinstance(status_signature, dict) and trust_anchor_list is not None and status_query is not None:
                anchors = trust_anchor_list.get("anchors") if isinstance(trust_anchor_list.get("anchors"), list) else []
                signer = status_signature.get("signer")
                kid = status_signature.get("kid")
                issuer_id = status_assertion.get("issuer_id")
                matched_anchor = None
                for anchor in anchors:
                    if not isinstance(anchor, dict):
                        continue
                    if anchor.get("issuer_id") == issuer_id and anchor.get("signer") == signer and anchor.get("kid") == kid:
                        matched_anchor = anchor
                        break

                sig_ok = False
                if matched_anchor is not None and isinstance(matched_anchor.get("public_key_b64url"), str):
                    sig_ok = verify_ed25519(
                        matched_anchor.get("public_key_b64url", ""),
                        str(status_signature.get("sig_b64url", "")),
                        str(status_signature.get("object_hash", "")),
                    )

                query_as_of = _parse_iso_datetime(status_query.get("status_as_of"))
                assertion_as_of = _parse_iso_datetime(status_assertion.get("status_as_of"))
                issued_at = _parse_iso_datetime(status_assertion.get("issued_at"))
                expires_at = _parse_iso_datetime(status_assertion.get("expires_at"))
                anchor_issued = _parse_iso_datetime(trust_anchor_list.get("issued_at"))
                anchor_expires = _parse_iso_datetime(trust_anchor_list.get("expires_at"))
                max_age = status_assertion.get("max_age_seconds")
                cache_ok = (
                    isinstance(max_age, int)
                    and issued_at is not None
                    and observed_at is not None
                    and observed_at <= issued_at + timedelta(seconds=max_age)
                )
                binding_ok = (
                    status_assertion.get("query_id") == status_query.get("query_id")
                    and status_assertion.get("target_type") == status_query.get("target_type")
                    and status_assertion.get("target_ref") == status_query.get("target_ref")
                    and status_assertion.get("anchor_list_id") == trust_anchor_list.get("anchor_list_id")
                    and query_as_of is not None
                    and assertion_as_of is not None
                    and query_as_of == assertion_as_of
                )
                temporal_ok = (
                    issued_at is not None
                    and expires_at is not None
                    and anchor_issued is not None
                    and anchor_expires is not None
                    and assertion_as_of is not None
                    and issued_at < expires_at
                    and anchor_issued <= issued_at
                    and expires_at <= anchor_expires
                    and assertion_as_of <= issued_at <= expires_at
                )
                status_value = status_assertion.get("status")
                revoked_at = _parse_iso_datetime(status_assertion.get("revoked_at"))
                revoked_semantics_ok = True
                if status_value == "REVOKED":
                    revoked_semantics_ok = revoked_at is not None and assertion_as_of is not None and revoked_at <= assertion_as_of
                elif status_value == "GOOD":
                    revoked_semantics_ok = status_assertion.get("revoked_at") is None

                status_valid = sig_ok and binding_ok and temporal_ok and cache_ok and revoked_semantics_ok and matched_anchor is not None

                if expect_status_valid and not status_valid:
                    add_failure(failures, "SR-CHAIN-01", "expected valid status assertion did not resolve under provided trust anchors and temporal/cache semantics", rel_case, None)
                if (not expect_status_valid) and status_valid:
                    add_failure(failures, "SR-CHAIN-01", "case marked expect_status_valid=false but status assertion resolved as valid", rel_case, None)

        case_id = case_obj.get("case_id")
        if isinstance(case_id, str) and case_id:
            seen_cases_by_id[case_id] = case_obj

        for msg in extracted_messages:
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

    if "TB-HTTP-SESSION-01" in enabled_checks:
        known_sessions: set[str] = set()
        for rel_case, case_obj in loaded_cases:
            if case_obj.get("operation") != "createSession":
                continue
            response = case_obj.get("http_response")
            body = response.get("body") if isinstance(response, dict) and isinstance(response.get("body"), dict) else {}
            response_sid = body.get("session_id") if isinstance(body.get("session_id"), str) and body.get("session_id") else None
            if response_sid:
                known_sessions.add(response_sid)
            top_sid = case_obj.get("session_id") if isinstance(case_obj.get("session_id"), str) and case_obj.get("session_id") else None
            if top_sid:
                known_sessions.add(top_sid)

        mismatches: list[str] = []
        for rel_case, case_obj in loaded_cases:
            if case_obj.get("operation") == "createSession":
                continue
            cid = case_obj.get("case_id") if isinstance(case_obj.get("case_id"), str) else rel_case
            request = case_obj.get("http_request")
            path = request.get("path") if isinstance(request, dict) and isinstance(request.get("path"), str) else ""
            body = request.get("body") if isinstance(request, dict) and isinstance(request.get("body"), dict) else {}
            top_session = case_obj.get("session_id") if isinstance(case_obj.get("session_id"), str) and case_obj.get("session_id") else None
            body_session = body.get("session_id") if isinstance(body.get("session_id"), str) and body.get("session_id") else None
            path_session = _session_id_from_path(path)

            case_sessions = [sid for sid in [path_session, top_session, body_session] if isinstance(sid, str) and sid]
            unique_sessions = sorted(set(case_sessions))
            if len(unique_sessions) > 1:
                mismatches.append(f"{cid} inconsistent session scope across path/body/top-level: {unique_sessions}")
                continue
            if unique_sessions and known_sessions and unique_sessions[0] not in known_sessions:
                mismatches.append(f"{cid} session_id '{unique_sessions[0]}' was not created by createSession evidence")

        if mismatches:
            add_failure(failures, "TB-HTTP-SESSION-01", f"session-scope mismatches: {mismatches}", "conformance/bindings/TB_HTTP_WS_0.1.json", None)

    protocol_version = suite["aicp_version"]
    passed = not failures
    suite_mark = suite.get("compatibility_mark")
    marks = [suite_mark] if passed and isinstance(suite_mark, str) else (["AICP-BIND-MCP-0.1"] if passed else [])
    return {
        "aicp_version": protocol_version,
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
    auction_modes_registry = {e.get("id") for e in load_json(ROOT / "registry/auction_modes.json")} if (ROOT / "registry/auction_modes.json").exists() else {"sealed-bid", "english", "dutch", "fixed-price", "priority-routing"}
    retention_policy_category_id = "retention_deletion"
    capneg_reason_codes = {e.get("id") for e in load_json(ROOT / "registry/capneg_reason_codes.json")}
    privacy_modes_registry = {e.get("id") for e in load_json(ROOT / "registry/privacy_modes.json")}
    transport_bindings_registry = {
        e.get("id"): e for e in load_json(ROOT / "registry/transport_bindings.json") if isinstance(e, dict)
    }
    deprecated_binding_aliases = {
        binding_id: str(entry.get("canonical_id"))
        for binding_id, entry in transport_bindings_registry.items()
        if isinstance(binding_id, str)
        and isinstance(entry.get("canonical_id"), str)
        and entry.get("status") == "deprecated"
    }
    channel_property_ids = {e.get("id") for e in load_json(ROOT / "registry/channel_properties.json") if isinstance(e, dict)}
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
    confidentiality_schema_path = ROOT / "schemas/extensions/ext-confidentiality-artifacts.schema.json"
    confidentiality_schema = load_json(confidentiality_schema_path)
    confidentiality_validator = _build_validator(confidentiality_schema, confidentiality_schema_path) if Draft202012Validator is not None else None
    redaction_schema_path = ROOT / "schemas/extensions/ext-redaction-payloads.schema.json"
    redaction_schema = load_json(redaction_schema_path)
    redaction_payload_validator = _validator_for_schema_pointer(redaction_schema, "/$defs/CONTENT_REDACTED") if Draft202012Validator is not None else None
    redaction_proof_validator = _validator_for_schema_pointer(redaction_schema, "/$defs/RedactionProof") if Draft202012Validator is not None else None
    pii_ref_validator = _validator_for_schema_pointer(redaction_schema, "/$defs/PiiRef") if Draft202012Validator is not None else None
    retention_policy_validator = _validator_for_schema_pointer(redaction_schema, "/$defs/RetentionPolicy") if Draft202012Validator is not None else None
    human_approval_schema_path = ROOT / "schemas/extensions/ext-human-approval-payloads.schema.json"
    human_approval_schema = load_json(human_approval_schema_path)
    approval_challenge_validator = _validator_for_schema_pointer(human_approval_schema, "/$defs/APPROVAL_CHALLENGE") if Draft202012Validator is not None else None
    approval_grant_validator = _validator_for_schema_pointer(human_approval_schema, "/$defs/APPROVAL_GRANT") if Draft202012Validator is not None else None
    approval_deny_validator = _validator_for_schema_pointer(human_approval_schema, "/$defs/APPROVAL_DENY") if Draft202012Validator is not None else None
    intervention_required_validator = _validator_for_schema_pointer(human_approval_schema, "/$defs/INTERVENTION_REQUIRED") if Draft202012Validator is not None else None
    intervention_complete_validator = _validator_for_schema_pointer(human_approval_schema, "/$defs/INTERVENTION_COMPLETE") if Draft202012Validator is not None else None
    iam_bridge_schema_path = ROOT / "schemas/extensions/ext-iam-bridge-payloads.schema.json"
    iam_bridge_schema = load_json(iam_bridge_schema_path)
    iam_bridge_claims_validator = _validator_for_schema_pointer(iam_bridge_schema, "/$defs/NormalizedClaimsSnapshot") if Draft202012Validator is not None else None
    iam_bridge_contract_validator = _validator_for_schema_pointer(iam_bridge_schema, "/$defs/ContractIamBridge") if Draft202012Validator is not None else None
    iam_bridge_message_validator = _validator_for_schema_pointer(iam_bridge_schema, "/$defs/MessageIamBridge") if Draft202012Validator is not None else None


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

        if "CN-BINDINGS-01" in enabled_checks or "CN-CHANNEL-PROPERTIES-01" in enabled_checks:
            declares_by_party: dict[str, dict[str, Any]] = {}
            for _, msg in rows:
                if msg.get("message_type") != "CAPABILITIES_DECLARE":
                    continue
                payload = msg.get("payload") or {}
                party_id = payload.get("party_id")
                if isinstance(party_id, str) and party_id:
                    declares_by_party[party_id] = payload

            def _canonical_declared_bindings(bindings: list[Any]) -> set[str]:
                out: set[str] = set()
                for binding in bindings:
                    if not isinstance(binding, str) or not binding:
                        continue
                    out.add(deprecated_binding_aliases.get(binding, binding))
                return out

            for line_no, msg in rows:
                if msg.get("message_type") != "CAPABILITIES_PROPOSE":
                    continue
                payload = msg.get("payload") or {}
                negotiation_result = payload.get("negotiation_result") or {}
                if not isinstance(negotiation_result, dict):
                    continue
                selected = negotiation_result.get("selected") or {}
                if not isinstance(selected, dict):
                    continue
                participants = negotiation_result.get("participants")
                participants = participants if isinstance(participants, list) else []

                selected_binding = selected.get("binding")
                if "CN-BINDINGS-01" in enabled_checks and selected_binding is not None:
                    if not isinstance(selected_binding, str) or not selected_binding:
                        add_failure(t_failures, "CN-BINDINGS-01", "selected.binding must be a non-empty string", rel_file, line_no)
                    else:
                        binding_entry = transport_bindings_registry.get(selected_binding)
                        if binding_entry is None:
                            add_failure(t_failures, "CN-BINDINGS-01", f"selected.binding '{selected_binding}' is not in registry/transport_bindings.json", rel_file, line_no)
                        elif binding_entry.get("status") == "deprecated":
                            add_failure(t_failures, "CN-BINDINGS-01", f"selected.binding '{selected_binding}' is deprecated; use canonical ID", rel_file, line_no)

                        participant_sets: list[set[str]] = []
                        for participant in participants:
                            if not isinstance(participant, str):
                                continue
                            declared = declares_by_party.get(participant)
                            if not isinstance(declared, dict):
                                continue
                            declared_bindings = declared.get("bindings")
                            declared_list = declared_bindings if isinstance(declared_bindings, list) else []
                            participant_sets.append(_canonical_declared_bindings(declared_list))
                        if participant_sets:
                            intersection = set.intersection(*participant_sets)
                            if selected_binding not in intersection:
                                add_failure(t_failures, "CN-BINDINGS-01", f"selected.binding '{selected_binding}' is not in participant binding intersection", rel_file, line_no)

                selected_props = selected.get("channel_properties")
                if "CN-CHANNEL-PROPERTIES-01" in enabled_checks and selected_props is not None:
                    if not isinstance(selected_props, dict):
                        add_failure(t_failures, "CN-CHANNEL-PROPERTIES-01", "selected.channel_properties must be an object", rel_file, line_no)
                        continue
                    for key in selected_props.keys():
                        if isinstance(key, str) and key.startswith("vendor:/"):
                            continue
                        if key not in channel_property_ids:
                            add_failure(t_failures, "CN-CHANNEL-PROPERTIES-01", f"unknown channel property key '{key}'", rel_file, line_no)
                    for participant in participants:
                        if not isinstance(participant, str):
                            continue
                        declared = declares_by_party.get(participant)
                        if not isinstance(declared, dict):
                            continue
                        support = declared.get("supported_channel_properties")
                        if not isinstance(support, dict):
                            add_failure(t_failures, "CN-CHANNEL-PROPERTIES-01", f"participant '{participant}' missing supported_channel_properties", rel_file, line_no)
                            continue
                        for key, value in selected_props.items():
                            if isinstance(key, str) and key.startswith("vendor:/"):
                                continue
                            rule = support.get(key)
                            if key == "CP-REPLAY-WINDOW-0.1":
                                if not isinstance(value, int) or value < 0:
                                    add_failure(t_failures, "CN-CHANNEL-PROPERTIES-01", f"selected {key} must be integer >= 0", rel_file, line_no)
                                    continue
                                if not isinstance(rule, dict):
                                    add_failure(t_failures, "CN-CHANNEL-PROPERTIES-01", f"participant '{participant}' missing range for {key}", rel_file, line_no)
                                    continue
                                mn = rule.get("min")
                                mx = rule.get("max")
                                if not isinstance(mn, int) or not isinstance(mx, int) or mn < 0 or mx < 0 or mn > mx:
                                    add_failure(t_failures, "CN-CHANNEL-PROPERTIES-01", f"participant '{participant}' has invalid {key} range", rel_file, line_no)
                                    continue
                                if value < mn or value > mx:
                                    add_failure(t_failures, "CN-CHANNEL-PROPERTIES-01", f"selected {key}={value} outside participant '{participant}' range [{mn},{mx}]", rel_file, line_no)
                            else:
                                if not isinstance(rule, list) or value not in rule:
                                    add_failure(t_failures, "CN-CHANNEL-PROPERTIES-01", f"selected {key}='{value}' not supported by participant '{participant}'", rel_file, line_no)

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

        if any(check in enabled_checks for check in {"CF-CONTRACT-CONFIDENTIALITY-01", "CF-MODE-REGISTRY-01", "CF-CAPNEG-BIND-01", "CF-NEGRESULT-HASH-BIND-01", "CF-REDACTION-ARTIFACTS-01", "CF-METADATA-PROJECTION-01", "CF-CLASSIFICATION-ARTIFACTS-01"}):
            proposed_negotiation_result = None
            proposed_negotiation_result_hash = None
            accepted_negotiation_result_hash = None
            accepted_mode = None
            accepted_indices: list[int] = []

            for idx, (line_no, msg) in enumerate(rows):
                mtype = msg.get("message_type")
                payload = msg.get("payload") if isinstance(msg.get("payload"), dict) else {}

                if mtype == "CAPABILITIES_PROPOSE":
                    nr = payload.get("negotiation_result")
                    if isinstance(nr, dict):
                        proposed_negotiation_result = nr
                        proposed_negotiation_result_hash = object_hash("capneg.negotiation_result", nr)
                        selected = nr.get("selected") if isinstance(nr.get("selected"), dict) else {}
                        accepted_mode = selected.get("privacy_mode") if isinstance(selected.get("privacy_mode"), str) else accepted_mode

                elif mtype == "CAPABILITIES_ACCEPT" and payload.get("accepted") is True:
                    accepted_indices.append(idx)
                    nr = payload.get("negotiation_result")
                    nr_hash = payload.get("negotiation_result_hash")
                    if isinstance(nr, dict):
                        accepted_negotiation_result_hash = object_hash("capneg.negotiation_result", nr)
                        selected = nr.get("selected") if isinstance(nr.get("selected"), dict) else {}
                        if isinstance(selected.get("privacy_mode"), str):
                            accepted_mode = selected.get("privacy_mode")
                    if isinstance(nr_hash, str) and nr_hash:
                        accepted_negotiation_result_hash = nr_hash

            if not accepted_indices:
                pass
            else:
                expected_hash = accepted_negotiation_result_hash or proposed_negotiation_result_hash
                for idx, (line_no, msg) in enumerate(rows):
                    if idx <= accepted_indices[0] or msg.get("message_type") != "CONTRACT_PROPOSE":
                        continue
                    contract = ((msg.get("payload") or {}).get("contract") or {})
                    confidentiality = _contract_ext_object(contract, "confidentiality", "EXT-CONFIDENTIALITY")

                    if confidentiality is None:
                        if "CF-CONTRACT-CONFIDENTIALITY-01" in enabled_checks:
                            add_failure(t_failures, "CF-CONTRACT-CONFIDENTIALITY-01", "CONTRACT_PROPOSE payload.contract.ext.confidentiality is required after CAPABILITIES_ACCEPT", rel_file, line_no)
                        continue

                    if confidentiality_validator is not None:
                        for err in sorted(confidentiality_validator.iter_errors(confidentiality), key=lambda e: list(e.path)):
                            add_failure(t_failures, "CF-CONTRACT-CONFIDENTIALITY-01", f"confidentiality object schema error: {err.message}", rel_file, line_no)

                    mode_id = confidentiality.get("mode_id")
                    if "CF-MODE-REGISTRY-01" in enabled_checks:
                        if mode_id not in privacy_modes_registry and not _is_namespaced_identifier(mode_id):
                            add_failure(t_failures, "CF-MODE-REGISTRY-01", f"unregistered confidentiality mode_id '{mode_id}'", rel_file, line_no)

                    if "CF-CAPNEG-BIND-01" in enabled_checks and isinstance(accepted_mode, str):
                        if mode_id != accepted_mode:
                            add_failure(t_failures, "CF-CAPNEG-BIND-01", "contract.ext.confidentiality.mode_id must match accepted CAPNEG selected.privacy_mode", rel_file, line_no)

                    if "CF-NEGRESULT-HASH-BIND-01" in enabled_checks and isinstance(expected_hash, str):
                        n_hash = confidentiality.get("negotiation_result_hash")
                        if not isinstance(n_hash, str) or n_hash != expected_hash:
                            add_failure(t_failures, "CF-NEGRESULT-HASH-BIND-01", "contract.ext.confidentiality.negotiation_result_hash must match accepted CAPNEG result hash", rel_file, line_no)

                    if "CF-REDACTION-ARTIFACTS-01" in enabled_checks and mode_id == "redacted":
                        refs = confidentiality.get("redaction_artifact_refs")
                        if not isinstance(refs, list) or len([r for r in refs if isinstance(r, str) and r]) == 0:
                            add_failure(t_failures, "CF-REDACTION-ARTIFACTS-01", "redacted mode requires non-empty redaction_artifact_refs", rel_file, line_no)

                    if "CF-METADATA-PROJECTION-01" in enabled_checks and mode_id == "metadata-only":
                        projection = confidentiality.get("metadata_projection")
                        if not isinstance(projection, dict) or len(projection) == 0:
                            add_failure(t_failures, "CF-METADATA-PROJECTION-01", "metadata-only mode requires non-empty metadata_projection", rel_file, line_no)

                    if "CF-CLASSIFICATION-ARTIFACTS-01" in enabled_checks and mode_id == "classification-only":
                        labels = confidentiality.get("classification_labels")
                        evidence_refs = confidentiality.get("classification_evidence_refs")
                        labels_ok = isinstance(labels, list) and len([v for v in labels if isinstance(v, str) and v]) > 0
                        evidence_ok = isinstance(evidence_refs, list) and len([v for v in evidence_refs if isinstance(v, str) and v]) > 0
                        if not labels_ok or not evidence_ok:
                            add_failure(t_failures, "CF-CLASSIFICATION-ARTIFACTS-01", "classification-only mode requires non-empty classification_labels and classification_evidence_refs", rel_file, line_no)

        if any(check in enabled_checks for check in {"RD-ORIGINAL-BIND-01", "RD-POLICY-REF-01", "RD-PROOF-01", "RD-PII-REF-01", "RD-RETENTION-CONTRACT-01", "RD-POLICY-CATEGORY-01", "RD-DELETE-SEMANTICS-01", "RD-CHAIN-INTEGRITY-01"}):
            prior_message_hashes: set[str] = set()
            forbidden_pii_keys = {"value", "raw_value", "plaintext", "email", "phone", "address", "ssn", "passport_number", "national_id"}

            for line_no, msg in rows:
                mtype = msg.get("message_type")
                payload = msg.get("payload") if isinstance(msg.get("payload"), dict) else {}

                if mtype == "CONTRACT_PROPOSE" and "RD-RETENTION-CONTRACT-01" in enabled_checks:
                    contract = payload.get("contract") if isinstance(payload.get("contract"), dict) else {}
                    redaction_cfg = _contract_ext_object(contract, "redaction", "EXT-REDACTION")
                    if redaction_cfg is not None:
                        retention = redaction_cfg.get("retention_policy") if isinstance(redaction_cfg.get("retention_policy"), dict) else None
                        if retention is None:
                            add_failure(t_failures, "RD-RETENTION-CONTRACT-01", "contract.ext.redaction.retention_policy must be present when EXT-REDACTION contract config is declared", rel_file, line_no)
                        else:
                            ttl = retention.get("ttl_seconds")
                            delete_semantics = retention.get("delete_semantics")
                            audit_ttl = retention.get("audit_retention_seconds")
                            if not isinstance(ttl, int) or ttl < 1:
                                add_failure(t_failures, "RD-RETENTION-CONTRACT-01", "retention_policy.ttl_seconds must be an integer >= 1", rel_file, line_no)
                            policy_category = retention.get("policy_category")
                            policy_ref = retention.get("policy_ref")
                            if not isinstance(delete_semantics, str) or delete_semantics not in {"hard-delete", "soft-delete", "tombstone"}:
                                add_failure(t_failures, "RD-DELETE-SEMANTICS-01", "retention_policy.delete_semantics must be one of: hard-delete, soft-delete, tombstone", rel_file, line_no)
                            if not isinstance(audit_ttl, int) or audit_ttl < 1:
                                add_failure(t_failures, "RD-RETENTION-CONTRACT-01", "retention_policy.audit_retention_seconds must be an integer >= 1", rel_file, line_no)
                            if not isinstance(policy_category, str) or not policy_category:
                                add_failure(t_failures, "RD-POLICY-CATEGORY-01", "retention_policy.policy_category must be present and non-empty", rel_file, line_no)
                            elif policy_category != retention_policy_category_id:
                                add_failure(t_failures, "RD-POLICY-CATEGORY-01", f"retention_policy.policy_category must be '{retention_policy_category_id}'", rel_file, line_no)
                            elif policy_category not in policy_categories_registry:
                                add_failure(t_failures, "RD-POLICY-CATEGORY-01", f"retention_policy.policy_category '{policy_category}' must be registered", rel_file, line_no)
                            if not isinstance(policy_ref, str) or not policy_ref:
                                add_failure(t_failures, "RD-RETENTION-CONTRACT-01", "retention_policy.policy_ref must be a non-empty string", rel_file, line_no)
                            if retention_policy_validator is not None:
                                for err in sorted(retention_policy_validator.iter_errors(retention), key=lambda e: list(e.path)):
                                    test_id = "RD-POLICY-CATEGORY-01" if "policy_category" in err.message else ("RD-DELETE-SEMANTICS-01" if "delete_semantics" in err.message else "RD-RETENTION-CONTRACT-01")
                                    add_failure(t_failures, test_id, f"invalid retention_policy: {err.message}", rel_file, line_no)
                            if isinstance(ttl, int) and isinstance(audit_ttl, int) and audit_ttl < ttl:
                                add_failure(t_failures, "RD-RETENTION-CONTRACT-01", "retention_policy.audit_retention_seconds should be >= ttl_seconds", rel_file, line_no)

                if mtype == "CONTENT_REDACTED":
                    if redaction_payload_validator is not None:
                        for err in sorted(redaction_payload_validator.iter_errors(payload), key=lambda e: list(e.path)):
                            if list(err.path)[:1] == ["redaction_proof"] or "redaction_proof" in err.message:
                                add_failure(t_failures, "RD-PROOF-01", f"invalid redaction payload proof shape: {err.message}", rel_file, line_no)
                            elif list(err.path)[:1] == ["pii_refs"] or "pii_refs" in err.message:
                                add_failure(t_failures, "RD-PII-REF-01", f"invalid pii_refs shape: {err.message}", rel_file, line_no)

                    original_hash = payload.get("original_message_hash")
                    if "RD-ORIGINAL-BIND-01" in enabled_checks:
                        if not isinstance(original_hash, str) or not original_hash or original_hash not in prior_message_hashes:
                            add_failure(t_failures, "RD-ORIGINAL-BIND-01", "CONTENT_REDACTED.original_message_hash must reference an earlier message_hash", rel_file, line_no)

                    if "RD-POLICY-REF-01" in enabled_checks:
                        policy_ref = payload.get("redaction_policy_ref")
                        if not isinstance(policy_ref, str) or not policy_ref:
                            add_failure(t_failures, "RD-POLICY-REF-01", "CONTENT_REDACTED.redaction_policy_ref must be a non-empty string", rel_file, line_no)

                    if "RD-PROOF-01" in enabled_checks:
                        proof = payload.get("redaction_proof")
                        if not isinstance(proof, dict):
                            add_failure(t_failures, "RD-PROOF-01", "CONTENT_REDACTED.redaction_proof must be an object", rel_file, line_no)
                        else:
                            for field in ("proof_type", "proof_ref", "generated_at"):
                                if not isinstance(proof.get(field), str) or not proof.get(field):
                                    add_failure(t_failures, "RD-PROOF-01", f"redaction_proof.{field} must be a non-empty string", rel_file, line_no)
                            if redaction_proof_validator is not None:
                                for err in sorted(redaction_proof_validator.iter_errors(proof), key=lambda e: list(e.path)):
                                    add_failure(t_failures, "RD-PROOF-01", f"invalid redaction_proof: {err.message}", rel_file, line_no)

                    if "RD-PII-REF-01" in enabled_checks:
                        pii_refs = payload.get("pii_refs")
                        if pii_refs is not None:
                            if not isinstance(pii_refs, list):
                                add_failure(t_failures, "RD-PII-REF-01", "CONTENT_REDACTED.pii_refs must be an array when present", rel_file, line_no)
                            else:
                                for idx, pii_ref in enumerate(pii_refs):
                                    if not isinstance(pii_ref, dict):
                                        add_failure(t_failures, "RD-PII-REF-01", f"pii_refs[{idx}] must be an object", rel_file, line_no)
                                        continue
                                    for bad_key in forbidden_pii_keys:
                                        if bad_key in pii_ref:
                                            add_failure(t_failures, "RD-PII-REF-01", f"pii_refs[{idx}] contains forbidden inline sensitive key '{bad_key}'", rel_file, line_no)
                                    for field in ("ref_id", "class", "controller", "access_policy_ref"):
                                        if not isinstance(pii_ref.get(field), str) or not pii_ref.get(field):
                                            add_failure(t_failures, "RD-PII-REF-01", f"pii_refs[{idx}].{field} must be a non-empty string", rel_file, line_no)
                                    if pii_ref_validator is not None:
                                        for err in sorted(pii_ref_validator.iter_errors(pii_ref), key=lambda e: list(e.path)):
                                            add_failure(t_failures, "RD-PII-REF-01", f"invalid pii_ref: {err.message}", rel_file, line_no)

                    if "RD-CHAIN-INTEGRITY-01" in enabled_checks and isinstance(original_hash, str) and isinstance(msg.get("message_hash"), str):
                        if msg.get("message_hash") == original_hash:
                            add_failure(t_failures, "RD-CHAIN-INTEGRITY-01", "CONTENT_REDACTED message_hash must be distinct from original_message_hash", rel_file, line_no)

                message_hash = msg.get("message_hash")
                if isinstance(message_hash, str) and message_hash:
                    prior_message_hashes.add(message_hash)

        if any(check in enabled_checks for check in {"HA-CHALLENGE-TARGET-01", "HA-CHALLENGE-APPROVER-01", "HA-CHALLENGE-EXPIRY-01", "HA-DECISION-BIND-01", "HA-SIGNER-01", "HA-TARGET-REUSE-01", "HA-EXPIRY-01", "HA-INTERVENTION-REQUIRED-01", "HA-INTERVENTION-LINK-01", "HA-ENFORCER-BIND-01"}):
            challenges_by_hash: dict[str, tuple[dict[str, Any], int]] = {}
            grants_by_target: dict[tuple[Any, ...], list[tuple[dict[str, Any], int]]] = {}
            interventions_by_hash: dict[str, tuple[dict[str, Any], int, bool]] = {}

            def _target_tuple(binding: Any) -> tuple[Any, ...] | None:
                if not isinstance(binding, dict):
                    return None
                return tuple(sorted((k, v) for k, v in binding.items() if isinstance(k, str)))

            for line_no, msg in rows:
                mtype = msg.get("message_type")
                payload = msg.get("payload") or {}
                msg_hash = msg.get("message_hash")
                msg_ts = _parse_iso_datetime(msg.get("timestamp"))

                if mtype == "APPROVAL_CHALLENGE":
                    target = payload.get("target_binding")
                    approver_id = payload.get("approver_id")
                    scope = payload.get("scope")
                    expires_at = _parse_iso_datetime(payload.get("expires_at"))

                    if "HA-CHALLENGE-TARGET-01" in enabled_checks:
                        if not isinstance(target, dict):
                            add_failure(t_failures, "HA-CHALLENGE-TARGET-01", "APPROVAL_CHALLENGE.target_binding must be an object", rel_file, line_no)
                        else:
                            present = [k for k in ("tool_call_id", "tool_call_hash", "message_hash") if isinstance(target.get(k), str) and target.get(k)]
                            if len(present) != 1:
                                add_failure(t_failures, "HA-CHALLENGE-TARGET-01", "APPROVAL_CHALLENGE.target_binding must contain exactly one of tool_call_id/tool_call_hash/message_hash", rel_file, line_no)
                        if approval_challenge_validator is not None:
                            for err in sorted(approval_challenge_validator.iter_errors(payload), key=lambda e: list(e.path)):
                                add_failure(t_failures, "HA-CHALLENGE-TARGET-01", f"invalid approval challenge payload: {err.message}", rel_file, line_no)

                    if "HA-CHALLENGE-APPROVER-01" in enabled_checks:
                        if not isinstance(approver_id, str) or not approver_id:
                            add_failure(t_failures, "HA-CHALLENGE-APPROVER-01", "APPROVAL_CHALLENGE.approver_id must be a non-empty string", rel_file, line_no)
                        if not isinstance(scope, dict) or not isinstance(scope.get("action"), str) or not scope.get("action"):
                            add_failure(t_failures, "HA-CHALLENGE-APPROVER-01", "APPROVAL_CHALLENGE.scope.action must be present", rel_file, line_no)

                    if "HA-CHALLENGE-EXPIRY-01" in enabled_checks:
                        if expires_at is None:
                            add_failure(t_failures, "HA-CHALLENGE-EXPIRY-01", "APPROVAL_CHALLENGE.expires_at must be valid RFC3339 date-time", rel_file, line_no)

                    if isinstance(msg_hash, str) and msg_hash:
                        challenges_by_hash[msg_hash] = (msg, line_no)

                elif mtype in {"APPROVAL_GRANT", "APPROVAL_DENY"}:
                    challenge_hash = payload.get("challenge_message_hash")
                    challenge_entry = challenges_by_hash.get(challenge_hash) if isinstance(challenge_hash, str) else None
                    decision_target = payload.get("target_binding")

                    if mtype == "APPROVAL_GRANT" and approval_grant_validator is not None:
                        for err in sorted(approval_grant_validator.iter_errors(payload), key=lambda e: list(e.path)):
                            add_failure(t_failures, "HA-DECISION-BIND-01", f"invalid approval grant payload: {err.message}", rel_file, line_no)
                    if mtype == "APPROVAL_DENY" and approval_deny_validator is not None:
                        for err in sorted(approval_deny_validator.iter_errors(payload), key=lambda e: list(e.path)):
                            add_failure(t_failures, "HA-DECISION-BIND-01", f"invalid approval deny payload: {err.message}", rel_file, line_no)

                    if "HA-DECISION-BIND-01" in enabled_checks and challenge_entry is None:
                        add_failure(t_failures, "HA-DECISION-BIND-01", f"{mtype} must reference a prior APPROVAL_CHALLENGE via challenge_message_hash", rel_file, line_no)

                    if challenge_entry is not None:
                        challenge_msg = challenge_entry[0]
                        challenge_payload = challenge_msg.get("payload") or {}
                        expected_approver = challenge_payload.get("approver_id")
                        expected_target = challenge_payload.get("target_binding")
                        expected_scope = challenge_payload.get("scope")
                        expected_expires = challenge_payload.get("expires_at")
                        expires_at = _parse_iso_datetime(expected_expires)

                        if "HA-SIGNER-01" in enabled_checks:
                            if msg.get("sender") != expected_approver or payload.get("approver_id") != expected_approver:
                                add_failure(t_failures, "HA-SIGNER-01", f"{mtype} sender and approver_id must match challenge approver_id", rel_file, line_no)

                        if "HA-TARGET-REUSE-01" in enabled_checks:
                            if not isinstance(expected_target, dict) or not isinstance(expected_scope, dict) or not isinstance(expected_expires, str) or not expected_expires:
                                pass
                            elif decision_target != expected_target or payload.get("scope") != expected_scope or payload.get("expires_at") != expected_expires:
                                add_failure(t_failures, "HA-TARGET-REUSE-01", f"{mtype} target_binding/scope/expires_at must match challenged values exactly", rel_file, line_no)

                        if "HA-EXPIRY-01" in enabled_checks:
                            if expires_at is None or msg_ts is None:
                                add_failure(t_failures, "HA-EXPIRY-01", f"{mtype} and challenge must have valid timestamps for expiry checks", rel_file, line_no)
                            elif msg_ts > expires_at:
                                add_failure(t_failures, "HA-EXPIRY-01", f"{mtype} occurs after challenge expiry", rel_file, line_no)

                        if mtype == "APPROVAL_GRANT":
                            tkey = _target_tuple(expected_target)
                            if tkey is not None:
                                grants_by_target.setdefault(tkey, []).append((msg, line_no))

                elif mtype == "INTERVENTION_REQUIRED":
                    handle = payload.get("intervention_handle")
                    handle_valid = isinstance(handle, str) and bool(handle)
                    if "HA-INTERVENTION-REQUIRED-01" in enabled_checks:
                        if intervention_required_validator is not None:
                            for err in sorted(intervention_required_validator.iter_errors(payload), key=lambda e: list(e.path)):
                                add_failure(t_failures, "HA-INTERVENTION-REQUIRED-01", f"invalid intervention-required payload: {err.message}", rel_file, line_no)
                        if _parse_iso_datetime(payload.get("expires_at")) is None:
                            add_failure(t_failures, "HA-INTERVENTION-REQUIRED-01", "INTERVENTION_REQUIRED.expires_at must be valid RFC3339 date-time", rel_file, line_no)
                        if not handle_valid:
                            add_failure(t_failures, "HA-INTERVENTION-REQUIRED-01", "INTERVENTION_REQUIRED.intervention_handle must be a non-empty string", rel_file, line_no)

                    if isinstance(msg_hash, str) and msg_hash:
                        interventions_by_hash[msg_hash] = (msg, line_no, handle_valid)

                elif mtype == "INTERVENTION_COMPLETE":
                    req_hash = payload.get("required_message_hash")
                    req_entry = interventions_by_hash.get(req_hash) if isinstance(req_hash, str) else None

                    if "HA-INTERVENTION-LINK-01" in enabled_checks:
                        if intervention_complete_validator is not None:
                            for err in sorted(intervention_complete_validator.iter_errors(payload), key=lambda e: list(e.path)):
                                add_failure(t_failures, "HA-INTERVENTION-LINK-01", f"invalid intervention-complete payload: {err.message}", rel_file, line_no)
                        if req_entry is None:
                            add_failure(t_failures, "HA-INTERVENTION-LINK-01", "INTERVENTION_COMPLETE.required_message_hash must reference prior INTERVENTION_REQUIRED", rel_file, line_no)
                        else:
                            req_payload = req_entry[0].get("payload") or {}
                            req_handle_valid = bool(req_entry[2])
                            if req_handle_valid and payload.get("intervention_handle") != req_payload.get("intervention_handle"):
                                add_failure(t_failures, "HA-INTERVENTION-LINK-01", "INTERVENTION_COMPLETE.intervention_handle must match required intervention_handle", rel_file, line_no)

                elif mtype == "TOOL_CALL_REQUEST" and "HA-ENFORCER-BIND-01" in enabled_checks:
                    ext = payload.get("ext") if isinstance(payload.get("ext"), dict) else {}
                    ha_ext = ext.get("human_approval") if isinstance(ext.get("human_approval"), dict) else None
                    if not isinstance(ha_ext, dict) or not ha_ext.get("required"):
                        continue
                    target: dict[str, Any] = {}
                    if isinstance(payload.get("tool_call_id"), str) and payload.get("tool_call_id"):
                        target["tool_call_id"] = payload.get("tool_call_id")
                    if isinstance(payload.get("tool_call_hash"), str) and payload.get("tool_call_hash"):
                        target["tool_call_hash"] = payload.get("tool_call_hash")
                    if not target:
                        add_failure(t_failures, "HA-ENFORCER-BIND-01", "TOOL_CALL_REQUEST requiring approval must include tool_call_id or tool_call_hash", rel_file, line_no)
                        continue
                    tkey = _target_tuple(target)
                    grants = grants_by_target.get(tkey, []) if tkey is not None else []
                    if not grants:
                        add_failure(t_failures, "HA-ENFORCER-BIND-01", "TOOL_CALL_REQUEST requiring approval lacks prior matching APPROVAL_GRANT", rel_file, line_no)
                    elif "HA-EXPIRY-01" in enabled_checks and msg_ts is not None:
                        valid = False
                        for grant_msg, _ in grants:
                            expires_at = _parse_iso_datetime((grant_msg.get("payload") or {}).get("expires_at"))
                            if expires_at is not None and msg_ts <= expires_at:
                                valid = True
                                break
                        if not valid:
                            add_failure(t_failures, "HA-EXPIRY-01", "TOOL_CALL_REQUEST requiring approval has only expired grants", rel_file, line_no)

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

        if any(check in enabled_checks for check in {"IB-ISSUER-01", "IB-SCOPE-MAP-01", "IB-ROLE-MAP-01", "IB-GROUP-MAP-01", "IB-BINDING-LINK-01", "IB-STEPUP-ACR-01", "IB-STEPUP-AMR-01", "IB-APPROVAL-MAP-01"}):
            first_contract = None
            for _, msg in rows:
                if msg.get("message_type") == "CONTRACT_PROPOSE":
                    first_contract = ((msg.get("payload") or {}).get("contract") or {})
                    break

            iam_bridge_cfg = _contract_ext_object(first_contract, "iam_bridge", "EXT-IAM-BRIDGE") if isinstance(first_contract, dict) else None
            if iam_bridge_cfg is None:
                iam_bridge_cfg = {}
            if iam_bridge_contract_validator is not None and isinstance(iam_bridge_cfg, dict) and len(iam_bridge_cfg) > 0:
                for err in sorted(iam_bridge_contract_validator.iter_errors(iam_bridge_cfg), key=lambda e: list(e.path)):
                    add_failure(t_failures, "IB-ISSUER-01", f"invalid contract.ext.iam_bridge: {err.message}", rel_file, rows[0][0] if rows else None)

            issued_bindings: dict[str, dict[str, Any]] = {}
            approvals: list[dict[str, Any]] = []

            for idx, (line_no, msg) in enumerate(rows):
                mtype = msg.get("message_type")
                payload = msg.get("payload") or {}

                if mtype == "SUBJECT_BINDING_ISSUE":
                    binding_hash = payload.get("binding_hash")
                    binding_ref = payload.get("binding_ref") if isinstance(payload.get("binding_ref"), dict) else None
                    binding_obj = binding_ref.get("object") if isinstance(binding_ref, dict) and isinstance(binding_ref.get("object"), dict) else None
                    claims = None
                    claims_hash = None
                    if isinstance(binding_obj, dict):
                        ext_obj = binding_obj.get("ext") if isinstance(binding_obj.get("ext"), dict) else None
                        if isinstance(ext_obj, dict):
                            claims = ext_obj.get("iam_bridge_claims")
                            claims_hash = ext_obj.get("iam_bridge_claims_hash")
                    if isinstance(binding_hash, str) and binding_hash:
                        issued_bindings[binding_hash] = {
                            "idx": idx,
                            "line_no": line_no,
                            "binding_obj": binding_obj,
                            "claims": claims if isinstance(claims, dict) else None,
                            "claims_hash": claims_hash,
                        }

                if mtype == "APPROVAL_GRANT":
                    approvals.append({"idx": idx, "line_no": line_no, "msg": msg})

            issuer_allowlist = iam_bridge_cfg.get("issuer_allowlist") if isinstance(iam_bridge_cfg.get("issuer_allowlist"), list) else []
            scope_to_auth = iam_bridge_cfg.get("scope_to_authority") if isinstance(iam_bridge_cfg.get("scope_to_authority"), dict) else {}
            role_to_auth = iam_bridge_cfg.get("role_to_authority") if isinstance(iam_bridge_cfg.get("role_to_authority"), dict) else {}
            group_to_auth = iam_bridge_cfg.get("group_to_authority") if isinstance(iam_bridge_cfg.get("group_to_authority"), dict) else {}
            actions_cfg = iam_bridge_cfg.get("actions") if isinstance(iam_bridge_cfg.get("actions"), dict) else {}

            def _req_list(action_cfg: dict[str, Any], key: str, ext_iam: dict[str, Any] | None, ext_key: str) -> list[str]:
                if isinstance(ext_iam, dict) and isinstance(ext_iam.get(ext_key), list):
                    return [v for v in ext_iam.get(ext_key) if isinstance(v, str) and v]
                if isinstance(action_cfg.get(key), list):
                    return [v for v in action_cfg.get(key) if isinstance(v, str) and v]
                return []

            for idx, (line_no, msg) in enumerate(rows):
                ext = msg.get("ext") if isinstance(msg.get("ext"), dict) else {}
                binding_hash = ext.get("subject_binding_hash") if isinstance(ext.get("subject_binding_hash"), str) else None
                iam_ext = ext.get("iam_bridge") if isinstance(ext.get("iam_bridge"), dict) else None
                action = iam_ext.get("action") if isinstance(iam_ext, dict) and isinstance(iam_ext.get("action"), str) else None
                if binding_hash is None or action is None:
                    continue

                if iam_bridge_message_validator is not None and isinstance(iam_ext, dict):
                    for err in sorted(iam_bridge_message_validator.iter_errors(iam_ext), key=lambda e: list(e.path)):
                        add_failure(t_failures, "IB-BINDING-LINK-01", f"invalid ext.iam_bridge: {err.message}", rel_file, line_no)

                binding = issued_bindings.get(binding_hash)
                if binding is None or binding.get("idx", -1) >= idx:
                    if "IB-BINDING-LINK-01" in enabled_checks:
                        add_failure(t_failures, "IB-BINDING-LINK-01", "acting message must reference an earlier SUBJECT_BINDING_ISSUE via ext.subject_binding_hash", rel_file, line_no)
                    continue

                claims = binding.get("claims")
                claims_hash = binding.get("claims_hash")
                if not isinstance(claims, dict):
                    if "IB-BINDING-LINK-01" in enabled_checks:
                        add_failure(t_failures, "IB-BINDING-LINK-01", "subject binding must include ext.iam_bridge_claims for IAM bridge evaluation", rel_file, line_no)
                    continue

                if iam_bridge_claims_validator is not None:
                    for err in sorted(iam_bridge_claims_validator.iter_errors(claims), key=lambda e: list(e.path)):
                        add_failure(t_failures, "IB-BINDING-LINK-01", f"invalid normalized claims snapshot: {err.message}", rel_file, line_no)

                try:
                    computed_claims_hash = object_hash("iam_claims_snapshot", claims)
                    if isinstance(claims_hash, str) and claims_hash != computed_claims_hash:
                        add_failure(t_failures, "IB-BINDING-LINK-01", "iam_bridge_claims_hash must equal object_hash('iam_claims_snapshot', iam_bridge_claims)", rel_file, line_no)
                except Exception as exc:
                    add_failure(t_failures, "IB-BINDING-LINK-01", f"claims hash recompute error: {exc}", rel_file, line_no)

                issuer = claims.get("issuer")
                if "IB-ISSUER-01" in enabled_checks and isinstance(issuer_allowlist, list) and issuer_allowlist and issuer not in issuer_allowlist:
                    add_failure(t_failures, "IB-ISSUER-01", f"claims issuer '{issuer}' is not allowed by contract.ext.iam_bridge.issuer_allowlist", rel_file, line_no)

                action_cfg = actions_cfg.get(action) if isinstance(actions_cfg.get(action), dict) else {}
                scopes = set(v for v in claims.get("scopes", []) if isinstance(v, str))
                roles = set(v for v in claims.get("roles", []) if isinstance(v, str))
                groups = set(v for v in claims.get("groups", []) if isinstance(v, str))
                amr = set(v for v in claims.get("amr", []) if isinstance(v, str))
                mapped_authority: set[str] = set()
                for s in scopes:
                    mapped_authority.update(v for v in scope_to_auth.get(s, []) if isinstance(v, str))
                for r in roles:
                    mapped_authority.update(v for v in role_to_auth.get(r, []) if isinstance(v, str))
                for g in groups:
                    mapped_authority.update(v for v in group_to_auth.get(g, []) if isinstance(v, str))

                if msg.get("message_type") == "DELEGATION_GRANT":
                    mapped_authority.update(_flatten_authority_subset(payload.get("authority_subset")))

                req_scopes_all = _req_list(action_cfg, "required_scopes_all", iam_ext, "required_scopes")
                req_roles_all = _req_list(action_cfg, "required_roles_all", iam_ext, "required_roles")
                req_groups_all = _req_list(action_cfg, "required_groups_all", iam_ext, "required_groups")
                req_scopes_any = [v for v in action_cfg.get("required_scopes_any", []) if isinstance(v, str)] if isinstance(action_cfg.get("required_scopes_any"), list) else []
                req_roles_any = [v for v in action_cfg.get("required_roles_any", []) if isinstance(v, str)] if isinstance(action_cfg.get("required_roles_any"), list) else []
                req_groups_any = [v for v in action_cfg.get("required_groups_any", []) if isinstance(v, str)] if isinstance(action_cfg.get("required_groups_any"), list) else []
                req_auth_any = [v for v in action_cfg.get("required_authority_any", []) if isinstance(v, str)] if isinstance(action_cfg.get("required_authority_any"), list) else []

                if "IB-SCOPE-MAP-01" in enabled_checks:
                    if any(v not in scopes for v in req_scopes_all):
                        add_failure(t_failures, "IB-SCOPE-MAP-01", "required_scopes_all not satisfied by normalized claims snapshot", rel_file, line_no)
                    if req_scopes_any and not any(v in scopes for v in req_scopes_any):
                        add_failure(t_failures, "IB-SCOPE-MAP-01", "required_scopes_any not satisfied by normalized claims snapshot", rel_file, line_no)
                if "IB-ROLE-MAP-01" in enabled_checks:
                    if any(v not in roles for v in req_roles_all):
                        add_failure(t_failures, "IB-ROLE-MAP-01", "required_roles_all not satisfied by normalized claims snapshot", rel_file, line_no)
                    if req_roles_any and not any(v in roles for v in req_roles_any):
                        add_failure(t_failures, "IB-ROLE-MAP-01", "required_roles_any not satisfied by normalized claims snapshot", rel_file, line_no)
                if "IB-GROUP-MAP-01" in enabled_checks:
                    if any(v not in groups for v in req_groups_all):
                        add_failure(t_failures, "IB-GROUP-MAP-01", "required_groups_all not satisfied by normalized claims snapshot", rel_file, line_no)
                    if req_groups_any and not any(v in groups for v in req_groups_any):
                        add_failure(t_failures, "IB-GROUP-MAP-01", "required_groups_any not satisfied by normalized claims snapshot", rel_file, line_no)
                if "IB-SCOPE-MAP-01" in enabled_checks and req_auth_any and not any(v in mapped_authority for v in req_auth_any):
                    add_failure(t_failures, "IB-SCOPE-MAP-01", "required_authority_any not satisfied by scope/role/group mapping", rel_file, line_no)

                required_acr = action_cfg.get("required_acr") if isinstance(action_cfg.get("required_acr"), str) else None
                if "IB-STEPUP-ACR-01" in enabled_checks and required_acr is not None and claims.get("acr") != required_acr:
                    add_failure(t_failures, "IB-STEPUP-ACR-01", f"required_acr '{required_acr}' not satisfied", rel_file, line_no)

                required_amr_any = [v for v in action_cfg.get("required_amr_any", []) if isinstance(v, str)] if isinstance(action_cfg.get("required_amr_any"), list) else []
                required_amr_all = [v for v in action_cfg.get("required_amr_all", []) if isinstance(v, str)] if isinstance(action_cfg.get("required_amr_all"), list) else []
                if "IB-STEPUP-AMR-01" in enabled_checks:
                    if required_amr_any and not any(v in amr for v in required_amr_any):
                        add_failure(t_failures, "IB-STEPUP-AMR-01", "required_amr_any not satisfied", rel_file, line_no)
                    if any(v not in amr for v in required_amr_all):
                        add_failure(t_failures, "IB-STEPUP-AMR-01", "required_amr_all not satisfied", rel_file, line_no)

                if "IB-APPROVAL-MAP-01" in enabled_checks and action_cfg.get("requires_human_approval") is True:
                    approval_action = action_cfg.get("approval_scope_action") if isinstance(action_cfg.get("approval_scope_action"), str) else action
                    target_tool_call_id = payload.get("tool_call_id") if isinstance(payload.get("tool_call_id"), str) else None
                    has_valid_approval = False
                    for appr in approvals:
                        if appr.get("idx", -1) >= idx:
                            continue
                        appr_payload = (appr.get("msg") or {}).get("payload") or {}
                        scope_action = ((appr_payload.get("scope") or {}).get("action") if isinstance(appr_payload.get("scope"), dict) else None)
                        target_binding = appr_payload.get("target_binding") if isinstance(appr_payload.get("target_binding"), dict) else {}
                        if scope_action == approval_action and ((target_tool_call_id is not None and target_binding.get("tool_call_id") == target_tool_call_id) or (target_tool_call_id is None)):
                            has_valid_approval = True
                            break
                    if not has_valid_approval:
                        add_failure(t_failures, "IB-APPROVAL-MAP-01", "protected action requires approval evidence but no matching prior APPROVAL_GRANT was found", rel_file, line_no)

        if any(check in enabled_checks for check in {"OB-TRACE-CORRELATION-01", "OB-TRACE-CONTEXT-01", "OB-SLA-SIGNAL-01", "OB-REASON-CODE-01", "OB-METERING-01", "OB-CORRELATION-LINK-01", "OB-APPROVAL-CORRELATION-01", "OB-IAM-STEPUP-CORRELATION-01"}):
            valid_signal_types = {"drop", "throttle", "deny", "degraded", "timeout"}
            trace_id_re = re.compile(r"^[0-9a-f]{32}$")
            span_id_re = re.compile(r"^[0-9a-f]{16}$")
            known_message_hashes = {m.get("message_hash") for _, m in rows if isinstance(m.get("message_hash"), str)}
            known_tool_call_ids: set[str] = set()
            known_tool_call_hashes: set[str] = set()
            known_workflow_step_refs: set[str] = set()
            approval_tool_call_ids: set[str] = set()
            iam_tool_call_ids: set[str] = set()

            for _, msg in rows:
                payload = msg.get("payload") if isinstance(msg.get("payload"), dict) else {}
                tool_call_id = payload.get("tool_call_id")
                if isinstance(tool_call_id, str) and tool_call_id:
                    known_tool_call_ids.add(tool_call_id)
                    ext = payload.get("ext") if isinstance(payload.get("ext"), dict) else {}
                    if isinstance(ext.get("human_approval"), dict) and ext.get("human_approval", {}).get("required") is True:
                        approval_tool_call_ids.add(tool_call_id)
                    if isinstance(ext.get("iam_bridge"), dict):
                        iam_tool_call_ids.add(tool_call_id)

                step_ref = payload.get("workflow_step_ref")
                if isinstance(step_ref, str) and step_ref:
                    known_workflow_step_refs.add(step_ref)

                tool_call_hash = payload.get("tool_call_hash")
                if isinstance(tool_call_hash, str) and tool_call_hash:
                    known_tool_call_hashes.add(tool_call_hash)

            def _extract_corr(obj: Any) -> tuple[str | None, str | None]:
                if not isinstance(obj, dict):
                    return (None, None)
                corr = obj.get("correlation_ref")
                if not isinstance(corr, dict):
                    return (None, None)
                keys = [k for k in ("message_hash", "tool_call_id", "tool_call_hash", "workflow_step_ref") if isinstance(corr.get(k), str) and corr.get(k)]
                if len(keys) != 1:
                    return (None, None)
                key = keys[0]
                return (key, str(corr.get(key)))

            def _corr_valid(kind: str | None, value: str | None) -> bool:
                if kind is None or value is None:
                    return False
                if kind == "message_hash":
                    return value in known_message_hashes
                if kind == "tool_call_id":
                    return value in known_tool_call_ids
                if kind == "tool_call_hash":
                    return value in known_tool_call_hashes
                if kind == "workflow_step_ref":
                    return value in known_workflow_step_refs
                return False

            found_approval_corr = False
            found_iam_corr = False
            for idx, (line_no, msg) in enumerate(rows):
                if msg.get("message_type") != "OBS_SIGNAL":
                    continue
                payload = msg.get("payload") if isinstance(msg.get("payload"), dict) else {}
                trace_obj = payload.get("trace") if isinstance(payload.get("trace"), dict) else None
                sla_obj = payload.get("sla") if isinstance(payload.get("sla"), dict) else None
                metering_obj = payload.get("metering") if isinstance(payload.get("metering"), dict) else None

                obs_objects = [obj for obj in (trace_obj, sla_obj, metering_obj) if isinstance(obj, dict)]
                for obj in obs_objects:
                    corr_kind, corr_value = _extract_corr(obj)
                    if corr_kind == "tool_call_id" and corr_value in approval_tool_call_ids:
                        found_approval_corr = True
                    if corr_kind == "tool_call_id" and corr_value in iam_tool_call_ids:
                        found_iam_corr = True

                if trace_obj is not None:
                    corr_kind, corr_value = _extract_corr(trace_obj)
                    if "OB-TRACE-CORRELATION-01" in enabled_checks and not _corr_valid(corr_kind, corr_value):
                        add_failure(t_failures, "OB-TRACE-CORRELATION-01", "trace.correlation_ref must bind to exactly one valid transcript target", rel_file, line_no)

                    if "OB-TRACE-CONTEXT-01" in enabled_checks:
                        trace_id = trace_obj.get("trace_id")
                        span_id = trace_obj.get("span_id")
                        parent_span_id = trace_obj.get("parent_span_id")
                        if not isinstance(trace_id, str) or not trace_id_re.fullmatch(trace_id):
                            add_failure(t_failures, "OB-TRACE-CONTEXT-01", "trace.trace_id must be 32 lowercase hex chars", rel_file, line_no)
                        if not isinstance(span_id, str) or not span_id_re.fullmatch(span_id):
                            add_failure(t_failures, "OB-TRACE-CONTEXT-01", "trace.span_id must be 16 lowercase hex chars", rel_file, line_no)
                        if parent_span_id is not None:
                            if not isinstance(parent_span_id, str) or not span_id_re.fullmatch(parent_span_id):
                                add_failure(t_failures, "OB-TRACE-CONTEXT-01", "trace.parent_span_id must be 16 lowercase hex chars when present", rel_file, line_no)
                            if isinstance(parent_span_id, str) and isinstance(span_id, str) and parent_span_id == span_id:
                                add_failure(t_failures, "OB-TRACE-CONTEXT-01", "trace.parent_span_id must differ from trace.span_id", rel_file, line_no)

                if sla_obj is not None:
                    corr_kind, corr_value = _extract_corr(sla_obj)
                    if "OB-CORRELATION-LINK-01" in enabled_checks and not _corr_valid(corr_kind, corr_value):
                        add_failure(t_failures, "OB-CORRELATION-LINK-01", "sla.correlation_ref must bind to exactly one valid transcript target", rel_file, line_no)
                    if "OB-SLA-SIGNAL-01" in enabled_checks:
                        sig = sla_obj.get("signal_type")
                        if not isinstance(sig, str) or sig not in valid_signal_types:
                            add_failure(t_failures, "OB-SLA-SIGNAL-01", "sla.signal_type must be one of drop/throttle/deny/degraded/timeout", rel_file, line_no)
                    if "OB-REASON-CODE-01" in enabled_checks:
                        code = sla_obj.get("reason_code")
                        if not isinstance(code, str) or not code:
                            add_failure(t_failures, "OB-REASON-CODE-01", "sla.reason_code must be a non-empty string", rel_file, line_no)
                        elif code not in policy_reason_codes and not _is_namespaced_identifier(code):
                            add_failure(t_failures, "OB-REASON-CODE-01", f"unknown reason_code '{code}' (must be registered or namespaced vendor:/org:)", rel_file, line_no)

                if metering_obj is not None:
                    corr_kind, corr_value = _extract_corr(metering_obj)
                    if "OB-CORRELATION-LINK-01" in enabled_checks and not _corr_valid(corr_kind, corr_value):
                        add_failure(t_failures, "OB-CORRELATION-LINK-01", "metering.correlation_ref must bind to exactly one valid transcript target", rel_file, line_no)
                    if "OB-METERING-01" in enabled_checks:
                        quantity = metering_obj.get("quantity")
                        unit = metering_obj.get("unit")
                        if not isinstance(quantity, (int, float)) or isinstance(quantity, bool):
                            add_failure(t_failures, "OB-METERING-01", "metering.quantity must be numeric", rel_file, line_no)
                        elif quantity < 0:
                            add_failure(t_failures, "OB-METERING-01", "metering.quantity must be non-negative", rel_file, line_no)
                        if not isinstance(unit, str) or not unit:
                            add_failure(t_failures, "OB-METERING-01", "metering.unit must be a non-empty string", rel_file, line_no)

            if "OB-APPROVAL-CORRELATION-01" in enabled_checks and approval_tool_call_ids and not found_approval_corr:
                add_failure(t_failures, "OB-APPROVAL-CORRELATION-01", "no OBS_SIGNAL correlated to a tool_call_id with M26 human_approval.required=true evidence", rel_file, rows[-1][0] if rows else None)

            if "OB-IAM-STEPUP-CORRELATION-01" in enabled_checks and iam_tool_call_ids and not found_iam_corr:
                add_failure(t_failures, "OB-IAM-STEPUP-CORRELATION-01", "no OBS_SIGNAL correlated to a tool_call_id with M28 iam_bridge action evidence", rel_file, rows[-1][0] if rows else None)

        if any(check in enabled_checks for check in {"EB-OPENAPI-BIND-01", "EB-ODATA-BIND-01", "EB-POLICY-XREF-01", "EB-POLICY-KIND-01", "EB-IAM-LINK-01", "EB-APPROVAL-LINK-01", "EB-OBS-CORRELATION-01", "EB-REFERENCE-INTEGRITY-01"}):
            first_contract = None
            first_contract_line_no = rows[0][0] if rows else None
            for line_no, msg in rows:
                if msg.get("message_type") == "CONTRACT_PROPOSE":
                    first_contract = ((msg.get("payload") or {}).get("contract") or {})
                    first_contract_line_no = line_no
                    break

            eb_cfg: dict[str, Any] = {}
            if isinstance(first_contract, dict):
                ext = first_contract.get("ext") or {}
                if isinstance(ext, dict) and isinstance(ext.get("enterprise_bindings"), dict):
                    eb_cfg = ext.get("enterprise_bindings")
                else:
                    extensions = first_contract.get("extensions") or {}
                    if isinstance(extensions, dict) and isinstance(extensions.get("EXT-ENTERPRISE-BINDINGS"), dict):
                        eb_cfg = extensions.get("EXT-ENTERPRISE-BINDINGS")

            openapi_bindings = eb_cfg.get("openapi_bindings") if isinstance(eb_cfg.get("openapi_bindings"), list) else []
            odata_bindings = eb_cfg.get("odata_bindings") if isinstance(eb_cfg.get("odata_bindings"), list) else []
            policy_xrefs = eb_cfg.get("policy_xrefs") if isinstance(eb_cfg.get("policy_xrefs"), list) else []

            openapi_ids = {b.get("binding_id") for b in openapi_bindings if isinstance(b, dict) and isinstance(b.get("binding_id"), str)}
            odata_ids = {b.get("binding_id") for b in odata_bindings if isinstance(b, dict) and isinstance(b.get("binding_id"), str)}
            all_binding_ids = {b for b in (openapi_ids | odata_ids) if isinstance(b, str) and b}

            if "EB-OPENAPI-BIND-01" in enabled_checks:
                if not openapi_bindings:
                    add_failure(t_failures, "EB-OPENAPI-BIND-01", "contract.ext.enterprise_bindings.openapi_bindings must contain at least one binding", rel_file, first_contract_line_no)
                for b in openapi_bindings:
                    if not isinstance(b, dict):
                        add_failure(t_failures, "EB-OPENAPI-BIND-01", "openapi binding entry must be an object", rel_file, first_contract_line_no)
                        continue
                    if not isinstance(b.get("spec_ref"), str) or not b.get("spec_ref"):
                        add_failure(t_failures, "EB-OPENAPI-BIND-01", "openapi binding spec_ref must be a non-empty string", rel_file, first_contract_line_no)
                    if not isinstance(b.get("tool_id"), str) or not b.get("tool_id"):
                        add_failure(t_failures, "EB-OPENAPI-BIND-01", "openapi binding tool_id must be a non-empty string", rel_file, first_contract_line_no)
                    if not isinstance(b.get("operation_id"), str) or not b.get("operation_id"):
                        add_failure(t_failures, "EB-OPENAPI-BIND-01", "openapi binding operation_id must be present for operation linkage", rel_file, first_contract_line_no)

            if "EB-ODATA-BIND-01" in enabled_checks:
                if not odata_bindings:
                    add_failure(t_failures, "EB-ODATA-BIND-01", "contract.ext.enterprise_bindings.odata_bindings must contain at least one binding", rel_file, first_contract_line_no)
                for b in odata_bindings:
                    if not isinstance(b, dict):
                        add_failure(t_failures, "EB-ODATA-BIND-01", "odata binding entry must be an object", rel_file, first_contract_line_no)
                        continue
                    if not isinstance(b.get("service_ref"), str) or not b.get("service_ref"):
                        add_failure(t_failures, "EB-ODATA-BIND-01", "odata binding service_ref must be a non-empty string", rel_file, first_contract_line_no)
                    target = b.get("target_ref")
                    if not isinstance(target, str) or not target:
                        add_failure(t_failures, "EB-ODATA-BIND-01", "odata binding target_ref must be a non-empty string", rel_file, first_contract_line_no)

            if "EB-POLICY-XREF-01" in enabled_checks:
                if not policy_xrefs:
                    add_failure(t_failures, "EB-POLICY-XREF-01", "contract.ext.enterprise_bindings.policy_xrefs must contain at least one xref", rel_file, first_contract_line_no)
                for x in policy_xrefs:
                    if not isinstance(x, dict):
                        add_failure(t_failures, "EB-POLICY-XREF-01", "policy_xref entry must be an object", rel_file, first_contract_line_no)
                        continue
                    if not isinstance(x.get("policy_ref"), str) or not x.get("policy_ref"):
                        add_failure(t_failures, "EB-POLICY-XREF-01", "policy_xref.policy_ref must be a non-empty string", rel_file, first_contract_line_no)
                    if not isinstance(x.get("xref_id"), str) or not x.get("xref_id"):
                        add_failure(t_failures, "EB-POLICY-XREF-01", "policy_xref.xref_id must be a non-empty string", rel_file, first_contract_line_no)

            if "EB-POLICY-KIND-01" in enabled_checks:
                allowed_kinds = {"abac", "rbac", "opa"}
                for x in policy_xrefs:
                    if not isinstance(x, dict):
                        continue
                    kind = x.get("policy_kind")
                    if not isinstance(kind, str) or kind not in allowed_kinds:
                        add_failure(t_failures, "EB-POLICY-KIND-01", f"unsupported policy_kind '{kind}' (must be one of abac/rbac/opa)", rel_file, first_contract_line_no)

            tool_rows: list[tuple[int, dict[str, Any]]] = []
            approvals: list[tuple[int, dict[str, Any]]] = []
            obs_tool_corr: set[str] = set()
            iam_link_found = False
            has_iam_activity = False
            approval_link_found = False
            requires_obs_correlation = eb_cfg.get("requires_obs_correlation") is True

            for idx, (line_no, msg) in enumerate(rows):
                mtype = msg.get("message_type")
                payload = msg.get("payload") if isinstance(msg.get("payload"), dict) else {}

                if mtype == "APPROVAL_GRANT":
                    approvals.append((idx, msg))

                if mtype == "OBS_SIGNAL":
                    for key in ("trace", "sla", "metering"):
                        obj = payload.get(key)
                        if not isinstance(obj, dict):
                            continue
                        corr = obj.get("correlation_ref") if isinstance(obj.get("correlation_ref"), dict) else {}
                        tool_call_id = corr.get("tool_call_id") if isinstance(corr.get("tool_call_id"), str) else None
                        if tool_call_id:
                            obs_tool_corr.add(tool_call_id)

                if mtype == "TOOL_CALL_REQUEST":
                    tool_rows.append((line_no, msg))
                    tool_call_id = payload.get("tool_call_id") if isinstance(payload.get("tool_call_id"), str) else None
                    ext = payload.get("ext") if isinstance(payload.get("ext"), dict) else {}
                    eb_ref = None
                    if isinstance(ext.get("enterprise_bindings"), dict):
                        eb_ref = ext.get("enterprise_bindings", {}).get("binding_ref_id")
                    if "EB-REFERENCE-INTEGRITY-01" in enabled_checks:
                        if not isinstance(eb_ref, str) or not eb_ref:
                            add_failure(t_failures, "EB-REFERENCE-INTEGRITY-01", "TOOL_CALL_REQUEST.ext.enterprise_bindings.binding_ref_id must be present", rel_file, line_no)
                        elif eb_ref not in all_binding_ids:
                            add_failure(t_failures, "EB-REFERENCE-INTEGRITY-01", f"binding_ref_id '{eb_ref}' does not resolve to declared openapi/odata binding_id", rel_file, line_no)

                    if "EB-IAM-LINK-01" in enabled_checks and isinstance(ext.get("iam_bridge"), dict):
                        has_iam_activity = True
                        action = ext.get("iam_bridge", {}).get("action")
                        if isinstance(action, str) and any(isinstance(x, dict) and x.get("action_ref") == action for x in policy_xrefs):
                            iam_link_found = True

                    if "EB-APPROVAL-LINK-01" in enabled_checks and isinstance(ext.get("human_approval"), dict) and ext.get("human_approval", {}).get("required") is True and isinstance(tool_call_id, str):
                        for appr_idx, appr_msg in approvals:
                            if appr_idx >= idx:
                                continue
                            appr_payload = appr_msg.get("payload") if isinstance(appr_msg.get("payload"), dict) else {}
                            target = appr_payload.get("target_binding") if isinstance(appr_payload.get("target_binding"), dict) else {}
                            if target.get("tool_call_id") == tool_call_id:
                                approval_link_found = True
                                break

                    if "EB-ODATA-BIND-01" in enabled_checks and isinstance(eb_ref, str) and eb_ref in odata_ids:
                        args = payload.get("arguments") if isinstance(payload.get("arguments"), dict) else {}
                        target = args.get("target_ref") if isinstance(args.get("target_ref"), str) else None
                        bound_target = None
                        for binding in odata_bindings:
                            if isinstance(binding, dict) and binding.get("binding_id") == eb_ref:
                                bound_target = binding.get("target_ref")
                                break
                        if isinstance(target, str) and isinstance(bound_target, str) and target != bound_target:
                            add_failure(t_failures, "EB-ODATA-BIND-01", f"odata binding target_ref '{bound_target}' does not match tool arguments target_ref '{target}'", rel_file, line_no)

            if "EB-IAM-LINK-01" in enabled_checks and has_iam_activity and not iam_link_found:
                add_failure(t_failures, "EB-IAM-LINK-01", "no enterprise-bound TOOL_CALL_REQUEST linked to iam_bridge action + policy_xref.action_ref", rel_file, tool_rows[-1][0] if tool_rows else first_contract_line_no)
            if "EB-APPROVAL-LINK-01" in enabled_checks and any(isinstance((m.get("payload") or {}).get("ext"), dict) and ((m.get("payload") or {}).get("ext", {}).get("human_approval", {}).get("required") is True) for _, m in tool_rows) and not approval_link_found:
                add_failure(t_failures, "EB-APPROVAL-LINK-01", "no required human_approval TOOL_CALL_REQUEST had prior matching APPROVAL_GRANT evidence", rel_file, tool_rows[-1][0] if tool_rows else first_contract_line_no)
            if "EB-OBS-CORRELATION-01" in enabled_checks and requires_obs_correlation:
                bound_tool_ids = {((m.get("payload") or {}).get("tool_call_id")) for _, m in tool_rows if isinstance((m.get("payload") or {}).get("tool_call_id"), str)}
                if bound_tool_ids and obs_tool_corr.isdisjoint(bound_tool_ids):
                    add_failure(t_failures, "EB-OBS-CORRELATION-01", "no OBS_SIGNAL correlation_ref.tool_call_id matches enterprise-bound TOOL_CALL_REQUEST", rel_file, tool_rows[-1][0] if tool_rows else first_contract_line_no)

        if any(check in enabled_checks for check in {"AD-REQUEST-01", "AD-OFFER-01", "AD-REASON-01", "AD-ATTEST-01", "AD-RENEW-01", "AD-NO-SILENT-DROP-01"}):
            requests: dict[str, tuple[int, dict[str, Any]]] = {}
            offers_by_request: dict[str, list[dict[str, Any]]] = {}
            terminal_by_request: dict[str, set[str]] = {}
            accepted_request_ids: set[str] = set()

            def _mark_terminal(req_id: str, kind: str) -> None:
                terminal_by_request.setdefault(req_id, set()).add(kind)

            all_message_ids = {m.get("message_id") for _, m in rows if isinstance(m.get("message_id"), str)}
            all_message_hashes = {m.get("message_hash") for _, m in rows if isinstance(m.get("message_hash"), str)}
            all_objhashes: set[str] = set()
            for _, m in rows:
                payload = m.get("payload") if isinstance(m.get("payload"), dict) else None
                if payload is None:
                    continue
                for _, _, oh in _collect_object_hash_triples(payload):
                    if isinstance(oh, str) and oh:
                        all_objhashes.add(oh)

            def _valid_ref(value: Any) -> bool:
                if not isinstance(value, str) or not value:
                    return False
                if value.startswith("msgid:"):
                    return value[len("msgid:"):] in all_message_ids
                if value.startswith("msghash:"):
                    return value[len("msghash:"):] in all_message_hashes
                if value.startswith("objhash:"):
                    return value[len("objhash:"):] in all_objhashes
                if value.startswith("att:") or value.startswith("stake:"):
                    return True
                return False

            for line_no, msg in rows:
                mtype = msg.get("message_type")
                payload = msg.get("payload") if isinstance(msg.get("payload"), dict) else {}
                req_id = payload.get("request_id") if isinstance(payload.get("request_id"), str) else None

                if mtype == "ADMISSION_REQUEST":
                    if "AD-REQUEST-01" in enabled_checks:
                        roles = payload.get("requested_roles")
                        scopes = payload.get("requested_scopes")
                        risk = payload.get("risk_tier")
                        if not isinstance(req_id, str) or not req_id:
                            add_failure(t_failures, "AD-REQUEST-01", "ADMISSION_REQUEST.request_id must be a non-empty string", rel_file, line_no)
                        if not isinstance(roles, list) or not roles or not all(isinstance(x, str) and x for x in roles):
                            add_failure(t_failures, "AD-REQUEST-01", "ADMISSION_REQUEST.requested_roles must be a non-empty string array", rel_file, line_no)
                        if not isinstance(scopes, list) or not scopes or not all(isinstance(x, str) and x for x in scopes):
                            add_failure(t_failures, "AD-REQUEST-01", "ADMISSION_REQUEST.requested_scopes must be a non-empty string array", rel_file, line_no)
                        if not isinstance(risk, str) or not risk:
                            add_failure(t_failures, "AD-REQUEST-01", "ADMISSION_REQUEST.risk_tier must be a non-empty string", rel_file, line_no)
                    if isinstance(req_id, str) and req_id:
                        requests[req_id] = (line_no, payload)

                    if "AD-ATTEST-01" in enabled_checks:
                        attestation_refs = payload.get("attestation_refs")
                        if attestation_refs is not None:
                            if not isinstance(attestation_refs, list) or not attestation_refs:
                                add_failure(t_failures, "AD-ATTEST-01", "ADMISSION_REQUEST.attestation_refs must be a non-empty array when present", rel_file, line_no)
                            else:
                                for ref in attestation_refs:
                                    if not _valid_ref(ref):
                                        add_failure(t_failures, "AD-ATTEST-01", f"invalid attestation_ref '{ref}'", rel_file, line_no)
                        stake_ref = payload.get("stake_ref")
                        if stake_ref is not None and (not isinstance(stake_ref, str) or not stake_ref):
                            add_failure(t_failures, "AD-ATTEST-01", "ADMISSION_REQUEST.stake_ref must be a non-empty string when present", rel_file, line_no)

                elif mtype == "ADMISSION_OFFER":
                    if "AD-OFFER-01" in enabled_checks:
                        offer_id = payload.get("offer_id")
                        granted_roles = payload.get("granted_roles")
                        granted_scopes = payload.get("granted_scopes")
                        quota_class = payload.get("quota_class")
                        lease_profile = payload.get("lease_profile")
                        if not isinstance(req_id, str) or not req_id:
                            add_failure(t_failures, "AD-OFFER-01", "ADMISSION_OFFER.request_id must be a non-empty string", rel_file, line_no)
                        if not isinstance(offer_id, str) or not offer_id:
                            add_failure(t_failures, "AD-OFFER-01", "ADMISSION_OFFER.offer_id must be a non-empty string", rel_file, line_no)
                        if not isinstance(granted_roles, list) or not granted_roles or not all(isinstance(x, str) and x for x in granted_roles):
                            add_failure(t_failures, "AD-OFFER-01", "ADMISSION_OFFER.granted_roles must be a non-empty string array", rel_file, line_no)
                        if not isinstance(granted_scopes, list) or not granted_scopes or not all(isinstance(x, str) and x for x in granted_scopes):
                            add_failure(t_failures, "AD-OFFER-01", "ADMISSION_OFFER.granted_scopes must be a non-empty string array", rel_file, line_no)
                        if not isinstance(quota_class, str) or not quota_class:
                            add_failure(t_failures, "AD-OFFER-01", "ADMISSION_OFFER.quota_class must be a non-empty string", rel_file, line_no)
                        if not isinstance(lease_profile, str) or not lease_profile:
                            add_failure(t_failures, "AD-OFFER-01", "ADMISSION_OFFER.lease_profile must be a non-empty string", rel_file, line_no)

                        if isinstance(req_id, str) and req_id in requests:
                            req_payload = requests[req_id][1]
                            req_roles = set(req_payload.get("requested_roles") or []) if isinstance(req_payload.get("requested_roles"), list) else set()
                            req_scopes = set(req_payload.get("requested_scopes") or []) if isinstance(req_payload.get("requested_scopes"), list) else set()
                            off_roles = set(granted_roles or []) if isinstance(granted_roles, list) else set()
                            off_scopes = set(granted_scopes or []) if isinstance(granted_scopes, list) else set()
                            if req_roles and not off_roles.issubset(req_roles):
                                add_failure(t_failures, "AD-OFFER-01", "ADMISSION_OFFER.granted_roles must be subset of requested_roles", rel_file, line_no)
                            if req_scopes and not off_scopes.issubset(req_scopes):
                                add_failure(t_failures, "AD-OFFER-01", "ADMISSION_OFFER.granted_scopes must be subset of requested_scopes", rel_file, line_no)
                        elif isinstance(req_id, str):
                            add_failure(t_failures, "AD-OFFER-01", f"ADMISSION_OFFER references unknown request_id '{req_id}'", rel_file, line_no)

                    if isinstance(req_id, str) and req_id:
                        offers_by_request.setdefault(req_id, []).append(payload)

                elif mtype == "ADMISSION_ACCEPT":
                    offer_id = payload.get("offer_id")
                    if "AD-OFFER-01" in enabled_checks:
                        if not isinstance(req_id, str) or req_id not in offers_by_request:
                            add_failure(t_failures, "AD-OFFER-01", "ADMISSION_ACCEPT.request_id must reference an existing ADMISSION_OFFER", rel_file, line_no)
                        elif isinstance(offer_id, str) and not any(isinstance(o.get("offer_id"), str) and o.get("offer_id") == offer_id for o in offers_by_request.get(req_id, [])):
                            add_failure(t_failures, "AD-OFFER-01", f"ADMISSION_ACCEPT.offer_id '{offer_id}' not found for request_id '{req_id}'", rel_file, line_no)
                    if isinstance(req_id, str) and req_id:
                        _mark_terminal(req_id, "accept")
                        accepted_request_ids.add(req_id)

                elif mtype in {"ADMISSION_REJECT", "ADMISSION_REVOKE", "ADMISSION_RENEW"}:
                    reason_code = payload.get("reason_code")
                    if "AD-REASON-01" in enabled_checks:
                        if not isinstance(reason_code, str) or not reason_code:
                            add_failure(t_failures, "AD-REASON-01", f"{mtype}.reason_code must be a non-empty string", rel_file, line_no)
                        elif reason_code not in policy_reason_codes and not _is_namespaced_identifier(reason_code):
                            add_failure(t_failures, "AD-REASON-01", f"unknown reason_code '{reason_code}' (must be registered or namespaced vendor:/org:)", rel_file, line_no)

                    if mtype == "ADMISSION_RENEW" and "AD-RENEW-01" in enabled_checks:
                        prior_request_id = payload.get("prior_request_id")
                        if not isinstance(prior_request_id, str) or not prior_request_id:
                            add_failure(t_failures, "AD-RENEW-01", "ADMISSION_RENEW.prior_request_id must be a non-empty string", rel_file, line_no)
                        elif prior_request_id not in accepted_request_ids:
                            add_failure(t_failures, "AD-RENEW-01", f"ADMISSION_RENEW.prior_request_id '{prior_request_id}' must reference a previously accepted admission", rel_file, line_no)
                        if isinstance(req_id, str) and req_id and req_id not in requests:
                            requests[req_id] = (line_no, payload)

                    if mtype in {"ADMISSION_REJECT", "ADMISSION_REVOKE"} and isinstance(req_id, str) and req_id:
                        _mark_terminal(req_id, mtype.lower())

                    if mtype == "ADMISSION_RENEW" and "AD-ATTEST-01" in enabled_checks:
                        attestation_refs = payload.get("attestation_refs")
                        if attestation_refs is not None:
                            if not isinstance(attestation_refs, list) or not attestation_refs:
                                add_failure(t_failures, "AD-ATTEST-01", "ADMISSION_RENEW.attestation_refs must be a non-empty array when present", rel_file, line_no)
                            else:
                                for ref in attestation_refs:
                                    if not _valid_ref(ref):
                                        add_failure(t_failures, "AD-ATTEST-01", f"invalid attestation_ref '{ref}'", rel_file, line_no)

                    if mtype in {"ADMISSION_REQUEST", "ADMISSION_RENEW"} and "AD-ATTEST-01" in enabled_checks:
                        stake_ref = payload.get("stake_ref")
                        if stake_ref is not None and not _valid_ref(stake_ref):
                            add_failure(t_failures, "AD-ATTEST-01", f"invalid stake_ref '{stake_ref}'", rel_file, line_no)

            if "AD-NO-SILENT-DROP-01" in enabled_checks:
                for req_id, (line_no, _) in requests.items():
                    if req_id not in terminal_by_request:
                        add_failure(t_failures, "AD-NO-SILENT-DROP-01", f"admission request '{req_id}' has no explicit accept/reject/revoke outcome", rel_file, line_no)

        if any(check in enabled_checks for check in {"QL-LEASE-01", "QL-BOUND-01", "QL-OVERRUN-01", "QL-NACK-01", "QL-OVERLOAD-01", "QL-RELEASE-01"}):
            ql_cfg: dict[str, Any] = {}
            first_contract_line_no = rows[0][0] if rows else None
            for line_no, msg in rows:
                if msg.get("message_type") == "CONTRACT_PROPOSE":
                    contract = ((msg.get("payload") or {}).get("contract") or {})
                    if isinstance(contract, dict):
                        ext = contract.get("ext") if isinstance(contract.get("ext"), dict) else {}
                        ql_cfg = ext.get("queue_leases") if isinstance(ext.get("queue_leases"), dict) else {}
                        first_contract_line_no = line_no
                    break

            lease_required = ql_cfg.get("lease_required") is True
            leases: dict[str, dict[str, Any]] = {}
            lease_use_msgs: dict[str, int] = {}
            lease_use_tools: dict[str, int] = {}
            released: set[str] = set()
            lease_message_hashes: set[str] = set()
            valid_overload_severity = {"low", "medium", "high", "critical"}

            for line_no, msg in rows:
                mtype = msg.get("message_type")
                payload = msg.get("payload") if isinstance(msg.get("payload"), dict) else {}

                if mtype == "QUEUE_LEASE_GRANT":
                    lease_id = payload.get("lease_id") if isinstance(payload.get("lease_id"), str) else None
                    if "QL-LEASE-01" in enabled_checks:
                        ttl = payload.get("ttl_seconds")
                        max_msgs = payload.get("max_msgs")
                        max_tool_calls = payload.get("max_tool_calls")
                        if not isinstance(lease_id, str) or not lease_id:
                            add_failure(t_failures, "QL-LEASE-01", "QUEUE_LEASE_GRANT.lease_id must be a non-empty string", rel_file, line_no)
                        if not isinstance(ttl, int) or ttl < 1:
                            add_failure(t_failures, "QL-LEASE-01", "QUEUE_LEASE_GRANT.ttl_seconds must be a positive integer", rel_file, line_no)
                        if not isinstance(max_msgs, int) or max_msgs < 1:
                            add_failure(t_failures, "QL-LEASE-01", "QUEUE_LEASE_GRANT.max_msgs must be a positive integer", rel_file, line_no)
                        if not isinstance(max_tool_calls, int) or max_tool_calls < 0:
                            add_failure(t_failures, "QL-LEASE-01", "QUEUE_LEASE_GRANT.max_tool_calls must be a non-negative integer", rel_file, line_no)
                    if isinstance(lease_id, str) and lease_id:
                        leases[lease_id] = payload
                        lease_use_msgs.setdefault(lease_id, 0)
                        lease_use_tools.setdefault(lease_id, 0)
                        mhash = msg.get("message_hash")
                        if isinstance(mhash, str) and mhash:
                            lease_message_hashes.add(mhash)

                elif mtype == "QUEUE_NACK":
                    if "QL-NACK-01" in enabled_checks:
                        reason_code = payload.get("reason_code")
                        retry_after = payload.get("retry_after_seconds")
                        if not isinstance(reason_code, str) or not reason_code:
                            add_failure(t_failures, "QL-NACK-01", "QUEUE_NACK.reason_code must be a non-empty string", rel_file, line_no)
                        elif reason_code not in policy_reason_codes and not _is_namespaced_identifier(reason_code):
                            add_failure(t_failures, "QL-NACK-01", f"unknown reason_code '{reason_code}' (must be registered or namespaced vendor:/org:)", rel_file, line_no)
                        if not isinstance(retry_after, int) or retry_after < 1:
                            add_failure(t_failures, "QL-NACK-01", "QUEUE_NACK.retry_after_seconds must be a positive integer", rel_file, line_no)

                elif mtype == "OVERLOAD_SIGNAL":
                    if "QL-OVERLOAD-01" in enabled_checks:
                        severity = payload.get("severity")
                        reason_code = payload.get("reason_code")
                        retry_after = payload.get("retry_after_seconds")
                        if not isinstance(severity, str) or severity not in valid_overload_severity:
                            add_failure(t_failures, "QL-OVERLOAD-01", "OVERLOAD_SIGNAL.severity must be one of low/medium/high/critical", rel_file, line_no)
                        if not isinstance(reason_code, str) or not reason_code:
                            add_failure(t_failures, "QL-OVERLOAD-01", "OVERLOAD_SIGNAL.reason_code must be a non-empty string", rel_file, line_no)
                        elif reason_code not in policy_reason_codes and not _is_namespaced_identifier(reason_code):
                            add_failure(t_failures, "QL-OVERLOAD-01", f"unknown reason_code '{reason_code}' (must be registered or namespaced vendor:/org:)", rel_file, line_no)
                        if not isinstance(retry_after, int) or retry_after < 1:
                            add_failure(t_failures, "QL-OVERLOAD-01", "OVERLOAD_SIGNAL.retry_after_seconds must be a positive integer", rel_file, line_no)

                elif mtype == "QUEUE_RELEASE":
                    lease_id = payload.get("lease_id") if isinstance(payload.get("lease_id"), str) else None
                    if "QL-RELEASE-01" in enabled_checks:
                        if not isinstance(lease_id, str) or not lease_id:
                            add_failure(t_failures, "QL-RELEASE-01", "QUEUE_RELEASE.lease_id must be a non-empty string", rel_file, line_no)
                        elif lease_id not in leases:
                            add_failure(t_failures, "QL-RELEASE-01", f"QUEUE_RELEASE references unknown lease_id '{lease_id}'", rel_file, line_no)
                    if isinstance(lease_id, str) and lease_id:
                        released.add(lease_id)

                elif mtype in {"CONTENT_MESSAGE", "TOOL_CALL_REQUEST"}:
                    lease_id = None
                    if isinstance(payload.get("lease_id"), str):
                        lease_id = payload.get("lease_id")
                    ext = payload.get("ext") if isinstance(payload.get("ext"), dict) else {}
                    if lease_id is None and isinstance(ext.get("queue_leases"), dict):
                        cand = ext.get("queue_leases", {}).get("lease_id")
                        lease_id = cand if isinstance(cand, str) else None

                    if "QL-BOUND-01" in enabled_checks and lease_required:
                        if not isinstance(lease_id, str) or not lease_id:
                            add_failure(t_failures, "QL-BOUND-01", f"{mtype} must include lease_id when lease_required=true", rel_file, line_no)
                        elif lease_id not in leases:
                            add_failure(t_failures, "QL-BOUND-01", f"{mtype} references unknown lease_id '{lease_id}'", rel_file, line_no)
                        elif lease_id in released:
                            add_failure(t_failures, "QL-BOUND-01", f"{mtype} uses lease_id '{lease_id}' after release", rel_file, line_no)

                    if isinstance(lease_id, str) and lease_id in leases:
                        lease_use_msgs[lease_id] = lease_use_msgs.get(lease_id, 0) + 1
                        if mtype == "TOOL_CALL_REQUEST":
                            lease_use_tools[lease_id] = lease_use_tools.get(lease_id, 0) + 1

            if "QL-OVERRUN-01" in enabled_checks:
                for lease_id, lease_obj in leases.items():
                    max_msgs = lease_obj.get("max_msgs") if isinstance(lease_obj.get("max_msgs"), int) else None
                    max_tool_calls = lease_obj.get("max_tool_calls") if isinstance(lease_obj.get("max_tool_calls"), int) else None
                    used_msgs = lease_use_msgs.get(lease_id, 0)
                    used_tools = lease_use_tools.get(lease_id, 0)
                    if isinstance(max_msgs, int) and used_msgs > max_msgs:
                        add_failure(t_failures, "QL-OVERRUN-01", f"lease_id '{lease_id}' exceeded max_msgs ({used_msgs}>{max_msgs})", rel_file, first_contract_line_no)
                    if isinstance(max_tool_calls, int) and used_tools > max_tool_calls:
                        add_failure(t_failures, "QL-OVERRUN-01", f"lease_id '{lease_id}' exceeded max_tool_calls ({used_tools}>{max_tool_calls})", rel_file, first_contract_line_no)

            if ql_cfg.get("requires_obs_correlation") is True and "QL-OVERLOAD-01" in enabled_checks:
                found_obs = False
                for line_no, msg in rows:
                    if msg.get("message_type") != "OBS_SIGNAL":
                        continue
                    payload = msg.get("payload") if isinstance(msg.get("payload"), dict) else {}
                    for key in ("trace", "sla", "metering"):
                        obj = payload.get(key)
                        if not isinstance(obj, dict):
                            continue
                        corr = obj.get("correlation_ref") if isinstance(obj.get("correlation_ref"), dict) else {}
                        mh = corr.get("message_hash")
                        if isinstance(mh, str) and mh in lease_message_hashes:
                            found_obs = True
                if not found_obs:
                    add_failure(t_failures, "QL-OVERLOAD-01", "requires_obs_correlation=true but no OBS_SIGNAL correlation_ref.message_hash targets a QUEUE_LEASE_GRANT", rel_file, first_contract_line_no)

        # Marketplace extension semantic-enforcement path (M36):
        # This block intentionally handles RFW/BID/AWARD/AUCTION/BLACKBOARD/SUBCHAT
        # linkage checks separately from schema validation to preserve schema-vs-semantic layering.
        if any(check in enabled_checks for check in {"MP-RFW-01", "MP-BID-01", "MP-AWARD-01", "MP-AUCTION-01", "MP-BLACKBOARD-01", "MP-SUBCHAT-01", "MP-ADMISSION-LINK-01", "MP-OBS-CORRELATION-01", "MP-ROUTING-ATTEST-01"}):
            mp_cfg: dict[str, Any] = {}
            for _, msg in rows:
                if msg.get("message_type") == "CONTRACT_PROPOSE":
                    contract = ((msg.get("payload") or {}).get("contract") or {})
                    if isinstance(contract, dict):
                        ext = contract.get("ext") if isinstance(contract.get("ext"), dict) else {}
                        mp_cfg = ext.get("marketplace") if isinstance(ext.get("marketplace"), dict) else {}
                    break

            rfws: dict[str, tuple[int, dict[str, Any]]] = {}
            bids: dict[str, tuple[int, dict[str, Any]]] = {}
            awards: dict[str, tuple[int, dict[str, Any]]] = {}
            auctions: dict[str, tuple[int, dict[str, Any]]] = {}
            blackboards: set[str] = set()
            subchats: set[str] = set()
            invited_subchat_participants: set[tuple[str, str]] = set()
            accepted_present = False
            routing_attested_awards: set[str] = set()
            marketplace_message_hashes: set[str] = set()

            for line_no, msg in rows:
                mtype = msg.get("message_type")
                payload = msg.get("payload") if isinstance(msg.get("payload"), dict) else {}
                mhash = msg.get("message_hash")
                if isinstance(mhash, str) and mhash and mtype in {"RFW_POST", "BID_SUBMIT", "BID_UPDATE", "BID_WITHDRAW", "AWARD_ISSUE", "AUCTION_OPEN", "AUCTION_CLOSE", "SUBCHAT_CREATE", "SUBCHAT_JOIN"}:
                    marketplace_message_hashes.add(mhash)

                if mtype == "ADMISSION_ACCEPT":
                    accepted_present = True

                if mtype == "RFW_POST":
                    rfw_id = payload.get("rfw_id")
                    if "MP-RFW-01" in enabled_checks:
                        if not isinstance(rfw_id, str) or not rfw_id:
                            add_failure(t_failures, "MP-RFW-01", "RFW_POST.rfw_id must be a non-empty string", rel_file, line_no)
                        if not isinstance(payload.get("work_spec_ref"), str) or not payload.get("work_spec_ref"):
                            add_failure(t_failures, "MP-RFW-01", "RFW_POST.work_spec_ref must be a non-empty string", rel_file, line_no)
                        if not isinstance(payload.get("policy_ref"), str) or not payload.get("policy_ref"):
                            add_failure(t_failures, "MP-RFW-01", "RFW_POST.policy_ref must be a non-empty string", rel_file, line_no)
                        if not isinstance(payload.get("deadline"), str) or not payload.get("deadline"):
                            add_failure(t_failures, "MP-RFW-01", "RFW_POST.deadline must be a non-empty date-time string", rel_file, line_no)
                    if isinstance(rfw_id, str) and rfw_id:
                        rfws[rfw_id] = (line_no, payload)

                elif mtype in {"BID_SUBMIT", "BID_UPDATE", "BID_WITHDRAW"}:
                    bid_id = payload.get("bid_id")
                    rfw_id = payload.get("rfw_id")
                    if "MP-BID-01" in enabled_checks:
                        if not isinstance(bid_id, str) or not bid_id:
                            add_failure(t_failures, "MP-BID-01", f"{mtype}.bid_id must be a non-empty string", rel_file, line_no)
                        if not isinstance(rfw_id, str) or not rfw_id:
                            add_failure(t_failures, "MP-BID-01", f"{mtype}.rfw_id must be a non-empty string", rel_file, line_no)
                        elif rfw_id not in rfws:
                            add_failure(t_failures, "MP-BID-01", f"{mtype}.rfw_id '{rfw_id}' must reference a prior RFW_POST", rel_file, line_no)
                        if mtype in {"BID_SUBMIT", "BID_UPDATE"}:
                            terms = payload.get("offer_terms")
                            if not isinstance(terms, dict):
                                add_failure(t_failures, "MP-BID-01", f"{mtype}.offer_terms must be an object", rel_file, line_no)
                            else:
                                if not isinstance(terms.get("price_hint"), str) or not terms.get("price_hint"):
                                    add_failure(t_failures, "MP-BID-01", f"{mtype}.offer_terms.price_hint must be a non-empty string", rel_file, line_no)
                                if not isinstance(terms.get("sla_hint"), str) or not terms.get("sla_hint"):
                                    add_failure(t_failures, "MP-BID-01", f"{mtype}.offer_terms.sla_hint must be a non-empty string", rel_file, line_no)
                    if isinstance(bid_id, str) and bid_id:
                        bids[bid_id] = (line_no, payload)

                elif mtype in {"AWARD_ISSUE", "AWARD_ACCEPT", "AWARD_DECLINE"}:
                    award_id = payload.get("award_id")
                    rfw_id = payload.get("rfw_id")
                    if "MP-AWARD-01" in enabled_checks:
                        if not isinstance(award_id, str) or not award_id:
                            add_failure(t_failures, "MP-AWARD-01", f"{mtype}.award_id must be a non-empty string", rel_file, line_no)
                        if not isinstance(rfw_id, str) or not rfw_id:
                            add_failure(t_failures, "MP-AWARD-01", f"{mtype}.rfw_id must be a non-empty string", rel_file, line_no)
                        elif rfw_id not in rfws:
                            add_failure(t_failures, "MP-AWARD-01", f"{mtype}.rfw_id '{rfw_id}' must reference a prior RFW_POST", rel_file, line_no)
                        if mtype == "AWARD_ISSUE":
                            bid_id = payload.get("bid_id")
                            if not isinstance(bid_id, str) or not bid_id:
                                add_failure(t_failures, "MP-AWARD-01", "AWARD_ISSUE.bid_id must be a non-empty string", rel_file, line_no)
                            elif bid_id not in bids:
                                add_failure(t_failures, "MP-AWARD-01", f"AWARD_ISSUE.bid_id '{bid_id}' must reference a prior bid", rel_file, line_no)
                            elif isinstance(rfw_id, str):
                                prior_rfw = bids[bid_id][1].get("rfw_id")
                                if isinstance(prior_rfw, str) and prior_rfw != rfw_id:
                                    add_failure(t_failures, "MP-AWARD-01", f"AWARD_ISSUE bid/rfw mismatch ({bid_id} -> {prior_rfw} != {rfw_id})", rel_file, line_no)
                            wo = payload.get("work_order")
                            if not isinstance(wo, dict):
                                add_failure(t_failures, "MP-AWARD-01", "AWARD_ISSUE.work_order must be an object", rel_file, line_no)
                            else:
                                if not isinstance(wo.get("work_order_id"), str) or not wo.get("work_order_id"):
                                    add_failure(t_failures, "MP-AWARD-01", "AWARD_ISSUE.work_order.work_order_id must be a non-empty string", rel_file, line_no)
                                if not isinstance(wo.get("workflow_ref"), str) or not wo.get("workflow_ref"):
                                    add_failure(t_failures, "MP-AWARD-01", "AWARD_ISSUE.work_order.workflow_ref must be a non-empty string", rel_file, line_no)
                        else:
                            if isinstance(award_id, str) and award_id not in awards:
                                add_failure(t_failures, "MP-AWARD-01", f"{mtype}.award_id '{award_id}' must reference prior AWARD_ISSUE", rel_file, line_no)
                            elif isinstance(award_id, str) and isinstance(rfw_id, str):
                                issue_rfw_id = awards[award_id][1].get("rfw_id")
                                if isinstance(issue_rfw_id, str) and issue_rfw_id != rfw_id:
                                    add_failure(t_failures, "MP-AWARD-01", f"{mtype}.rfw_id '{rfw_id}' must match AWARD_ISSUE.rfw_id '{issue_rfw_id}'", rel_file, line_no)
                    if isinstance(award_id, str) and award_id and mtype == "AWARD_ISSUE":
                        awards[award_id] = (line_no, payload)

                elif mtype in {"AUCTION_OPEN", "AUCTION_CLOSE"}:
                    auction_id = payload.get("auction_id")
                    rfw_id = payload.get("rfw_id")
                    if "MP-AUCTION-01" in enabled_checks:
                        if not isinstance(auction_id, str) or not auction_id:
                            add_failure(t_failures, "MP-AUCTION-01", f"{mtype}.auction_id must be a non-empty string", rel_file, line_no)
                        if not isinstance(rfw_id, str) or not rfw_id:
                            add_failure(t_failures, "MP-AUCTION-01", f"{mtype}.rfw_id must be a non-empty string", rel_file, line_no)
                        elif rfw_id not in rfws:
                            add_failure(t_failures, "MP-AUCTION-01", f"{mtype}.rfw_id '{rfw_id}' must reference a prior RFW_POST", rel_file, line_no)
                        if mtype == "AUCTION_OPEN":
                            mode = payload.get("auction_mode")
                            if not isinstance(mode, str) or not mode:
                                add_failure(t_failures, "MP-AUCTION-01", "AUCTION_OPEN.auction_mode must be a non-empty string", rel_file, line_no)
                            elif mode not in auction_modes_registry and not _is_namespaced_identifier(mode):
                                add_failure(t_failures, "MP-AUCTION-01", f"invalid auction_mode '{mode}'", rel_file, line_no)
                        else:
                            if not isinstance(payload.get("result_ref"), str) or not payload.get("result_ref"):
                                add_failure(t_failures, "MP-AUCTION-01", "AUCTION_CLOSE.result_ref must be a non-empty string", rel_file, line_no)
                            if isinstance(auction_id, str) and auction_id not in auctions:
                                add_failure(t_failures, "MP-AUCTION-01", f"AUCTION_CLOSE.auction_id '{auction_id}' must reference prior AUCTION_OPEN", rel_file, line_no)
                    if mtype == "AUCTION_OPEN" and isinstance(auction_id, str) and auction_id:
                        auctions[auction_id] = (line_no, payload)

                elif mtype in {"BLACKBOARD_DECLARE", "BLACKBOARD_POST", "BLACKBOARD_UPDATE", "BLACKBOARD_REMOVE"}:
                    ws = payload.get("workspace_id")
                    if "MP-BLACKBOARD-01" in enabled_checks:
                        if not isinstance(ws, str) or not ws:
                            add_failure(t_failures, "MP-BLACKBOARD-01", f"{mtype}.workspace_id must be a non-empty string", rel_file, line_no)
                        if mtype == "BLACKBOARD_DECLARE":
                            if not isinstance(payload.get("policy_ref"), str) or not payload.get("policy_ref"):
                                add_failure(t_failures, "MP-BLACKBOARD-01", "BLACKBOARD_DECLARE.policy_ref must be a non-empty string", rel_file, line_no)
                        else:
                            if isinstance(ws, str) and ws not in blackboards:
                                add_failure(t_failures, "MP-BLACKBOARD-01", f"{mtype}.workspace_id '{ws}' must reference prior BLACKBOARD_DECLARE", rel_file, line_no)
                            if not isinstance(payload.get("entry_id"), str) or not payload.get("entry_id"):
                                add_failure(t_failures, "MP-BLACKBOARD-01", f"{mtype}.entry_id must be a non-empty string", rel_file, line_no)
                            if mtype in {"BLACKBOARD_POST", "BLACKBOARD_UPDATE"} and (not isinstance(payload.get("content_ref"), str) or not payload.get("content_ref")):
                                add_failure(t_failures, "MP-BLACKBOARD-01", f"{mtype}.content_ref must be a non-empty string", rel_file, line_no)
                    if mtype == "BLACKBOARD_DECLARE" and isinstance(ws, str) and ws:
                        blackboards.add(ws)

                elif mtype in {"SUBCHAT_CREATE", "SUBCHAT_INVITE", "SUBCHAT_JOIN"}:
                    subchat_id = payload.get("subchat_id")
                    if "MP-SUBCHAT-01" in enabled_checks:
                        if not isinstance(subchat_id, str) or not subchat_id:
                            add_failure(t_failures, "MP-SUBCHAT-01", f"{mtype}.subchat_id must be a non-empty string", rel_file, line_no)
                        if mtype == "SUBCHAT_CREATE":
                            if not isinstance(payload.get("parent_chat_id"), str) or not payload.get("parent_chat_id"):
                                add_failure(t_failures, "MP-SUBCHAT-01", "SUBCHAT_CREATE.parent_chat_id must be a non-empty string", rel_file, line_no)
                            if not isinstance(payload.get("topic_tag"), str) or not payload.get("topic_tag"):
                                add_failure(t_failures, "MP-SUBCHAT-01", "SUBCHAT_CREATE.topic_tag must be a non-empty string", rel_file, line_no)
                        elif isinstance(subchat_id, str) and subchat_id not in subchats:
                            add_failure(t_failures, "MP-SUBCHAT-01", f"{mtype}.subchat_id '{subchat_id}' must reference prior SUBCHAT_CREATE", rel_file, line_no)
                    if mtype == "SUBCHAT_CREATE" and isinstance(subchat_id, str) and subchat_id:
                        subchats.add(subchat_id)
                    elif mtype == "SUBCHAT_INVITE":
                        invitee = payload.get("invitee_id") if isinstance(payload.get("invitee_id"), str) else None
                        if isinstance(subchat_id, str) and subchat_id and isinstance(invitee, str) and invitee:
                            invited_subchat_participants.add((subchat_id, invitee))
                    elif mtype == "SUBCHAT_JOIN":
                        participant = payload.get("participant_id") if isinstance(payload.get("participant_id"), str) else None
                        if "MP-ADMISSION-LINK-01" in enabled_checks and mp_cfg.get("subchat_requires_admission") is True:
                            if not accepted_present:
                                add_failure(t_failures, "MP-ADMISSION-LINK-01", "SUBCHAT_JOIN requires prior ADMISSION_ACCEPT when subchat_requires_admission=true", rel_file, line_no)
                            if isinstance(subchat_id, str) and isinstance(participant, str) and (subchat_id, participant) not in invited_subchat_participants:
                                add_failure(t_failures, "MP-ADMISSION-LINK-01", "SUBCHAT_JOIN participant must be invited to the subchat", rel_file, line_no)

                elif mtype == "ROUTING_DECISION_ATTEST":
                    award_id = payload.get("award_id") if isinstance(payload.get("award_id"), str) else None
                    if "MP-ROUTING-ATTEST-01" in enabled_checks:
                        if not isinstance(award_id, str) or not award_id:
                            add_failure(t_failures, "MP-ROUTING-ATTEST-01", "ROUTING_DECISION_ATTEST.award_id must be a non-empty string", rel_file, line_no)
                        elif award_id not in awards:
                            add_failure(t_failures, "MP-ROUTING-ATTEST-01", f"ROUTING_DECISION_ATTEST.award_id '{award_id}' must reference prior AWARD_ISSUE", rel_file, line_no)
                        if not isinstance(payload.get("policy_ref"), str) or not payload.get("policy_ref"):
                            add_failure(t_failures, "MP-ROUTING-ATTEST-01", "ROUTING_DECISION_ATTEST.policy_ref must be a non-empty string", rel_file, line_no)
                        if not isinstance(payload.get("evidence_ref"), str) or not payload.get("evidence_ref"):
                            add_failure(t_failures, "MP-ROUTING-ATTEST-01", "ROUTING_DECISION_ATTEST.evidence_ref must be a non-empty string", rel_file, line_no)
                    if isinstance(award_id, str) and award_id:
                        routing_attested_awards.add(award_id)

            if "MP-ROUTING-ATTEST-01" in enabled_checks and mp_cfg.get("routing_attestation_required") is True:
                for award_id, (line_no, _) in awards.items():
                    if award_id not in routing_attested_awards:
                        add_failure(t_failures, "MP-ROUTING-ATTEST-01", f"AWARD_ISSUE '{award_id}' missing ROUTING_DECISION_ATTEST while routing_attestation_required=true", rel_file, line_no)

            if "MP-OBS-CORRELATION-01" in enabled_checks and mp_cfg.get("requires_obs_correlation") is True:
                found_obs = False
                for line_no, msg in rows:
                    if msg.get("message_type") != "OBS_SIGNAL":
                        continue
                    payload = msg.get("payload") if isinstance(msg.get("payload"), dict) else {}
                    for key in ("trace", "sla", "metering"):
                        obj = payload.get(key)
                        if not isinstance(obj, dict):
                            continue
                        corr = obj.get("correlation_ref") if isinstance(obj.get("correlation_ref"), dict) else {}
                        mh = corr.get("message_hash")
                        if isinstance(mh, str) and mh in marketplace_message_hashes:
                            found_obs = True
                if not found_obs:
                    add_failure(t_failures, "MP-OBS-CORRELATION-01", "requires_obs_correlation=true but no OBS_SIGNAL correlation_ref.message_hash targets marketplace activity", rel_file, rows[0][0] if rows else None)

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

            capneg_cfg = _contract_ext_object(first_contract, "capneg", "EXT-CAPNEG")
            enforcement_cfg = _contract_ext_object(first_contract, "enforcement", "EXT-ENFORCEMENT")
            participants_cfg = _contract_ext_object(first_contract, "participants", "EXT-PARTICIPANTS")

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


        if any(check in enabled_checks for check in {"AM-MANIFEST-SCHEMA-01", "AM-PIN-01", "AM-SHADOW-01", "AM-RENEG-01"}):
            manifest_schema = load_json(ROOT / "schemas/extensions/ext-artifact-manifests-pinning.schema.json")
            manifest_validator = None
            if Draft202012Validator is not None:
                manifest_wrapper = {
                    "$schema": manifest_schema.get("$schema"),
                    "$id": manifest_schema.get("$id"),
                    "$ref": "#/$defs/contract_artifact_pinning",
                    "$defs": manifest_schema.get("$defs", {}),
                }
                manifest_validator = Draft202012Validator(manifest_wrapper)

            active_pins: list[dict[str, Any]] = []
            initial_pins: list[dict[str, Any]] = []

            def _extract_pinning_from_contract(contract_obj: dict[str, Any]) -> dict[str, Any] | None:
                ext = contract_obj.get("ext") if isinstance(contract_obj.get("ext"), dict) else {}
                pin = ext.get("artifact_pinning") if isinstance(ext, dict) else None
                if pin is None:
                    extensions = contract_obj.get("extensions") if isinstance(contract_obj.get("extensions"), dict) else {}
                    pin = extensions.get("EXT-ARTIFACT-PINNING") if isinstance(extensions, dict) else None
                return pin if isinstance(pin, dict) else None

            for line_no, msg in rows:
                mtype = msg.get("message_type")
                payload = msg.get("payload") if isinstance(msg.get("payload"), dict) else {}

                if mtype == "CONTRACT_PROPOSE":
                    contract_obj = payload.get("contract") if isinstance(payload.get("contract"), dict) else {}
                    pin_obj = _extract_pinning_from_contract(contract_obj)
                    if isinstance(pin_obj, dict):
                        initial_pins = list(pin_obj.get("pinned_artifacts") or [])
                        active_pins = list(initial_pins)
                        if "AM-MANIFEST-SCHEMA-01" in enabled_checks and manifest_validator is not None:
                            for err in sorted(manifest_validator.iter_errors(pin_obj), key=lambda e: list(e.path)):
                                add_failure(t_failures, "AM-MANIFEST-SCHEMA-01", err.message, rel_file, line_no)

                if mtype == "CONTEXT_AMEND":
                    ext = payload.get("ext") if isinstance(payload.get("ext"), dict) else {}
                    pin_obj = ext.get("artifact_pinning") if isinstance(ext.get("artifact_pinning"), dict) else None
                    if isinstance(pin_obj, dict):
                        if "AM-MANIFEST-SCHEMA-01" in enabled_checks and manifest_validator is not None:
                            for err in sorted(manifest_validator.iter_errors(pin_obj), key=lambda e: list(e.path)):
                                add_failure(t_failures, "AM-MANIFEST-SCHEMA-01", err.message, rel_file, line_no)
                        new_pins = list(pin_obj.get("pinned_artifacts") or [])
                        if "AM-RENEG-01" in enabled_checks and initial_pins and new_pins and new_pins != active_pins:
                            active_pins = new_pins

                if mtype == "TOOL_CALL_REQUEST":
                    if "AM-PIN-01" in enabled_checks:
                        manifest_ref = payload.get("manifest_ref") if isinstance(payload.get("manifest_ref"), dict) else None
                        if manifest_ref is None:
                            add_failure(t_failures, "AM-PIN-01", "TOOL_CALL_REQUEST must include payload.manifest_ref when artifact pinning is active", rel_file, line_no)
                        else:
                            matched = False
                            for pin in active_pins:
                                if not isinstance(pin, dict):
                                    continue
                                if all(manifest_ref.get(k) == pin.get(k) for k in ["manifest_id", "issuer_id", "issuer_scoped_id", "version", "content_hash"]):
                                    matched = True
                                    break
                            if not matched:
                                add_failure(t_failures, "AM-PIN-01", "TOOL_CALL_REQUEST manifest_ref does not match active pinned artifact", rel_file, line_no)

                    if "AM-SHADOW-01" in enabled_checks:
                        manifest_ref = payload.get("manifest_ref") if isinstance(payload.get("manifest_ref"), dict) else None
                        if manifest_ref is not None:
                            for pin in active_pins:
                                if not isinstance(pin, dict):
                                    continue
                                if manifest_ref.get("manifest_id") == pin.get("manifest_id") and manifest_ref.get("issuer_id") != pin.get("issuer_id"):
                                    add_failure(t_failures, "AM-SHADOW-01", "manifest_id collision with different issuer_id detected (shadowing)", rel_file, line_no)
                                    break

            if "AM-RENEG-01" in enabled_checks and initial_pins:
                saw_amend = any((msg.get("message_type") == "CONTEXT_AMEND" and isinstance((msg.get("payload") or {}).get("ext"), dict) and isinstance(((msg.get("payload") or {}).get("ext") or {}).get("artifact_pinning"), dict)) for _, msg in rows)
                for line_no, msg in rows:
                    if msg.get("message_type") != "TOOL_CALL_REQUEST":
                        continue
                    payload = msg.get("payload") if isinstance(msg.get("payload"), dict) else {}
                    manifest_ref = payload.get("manifest_ref") if isinstance(payload.get("manifest_ref"), dict) else {}
                    issuer = manifest_ref.get("issuer_id")
                    manifest_id = manifest_ref.get("manifest_id")
                    version = manifest_ref.get("version")
                    same_artifact_initial = [
                        pin for pin in initial_pins
                        if isinstance(pin, dict)
                        and pin.get("issuer_id") == issuer
                        and pin.get("manifest_id") == manifest_id
                    ]
                    if same_artifact_initial and all(pin.get("version") != version for pin in same_artifact_initial) and not saw_amend:
                        add_failure(t_failures, "AM-RENEG-01", "pinned artifact version changed without explicit CONTEXT_AMEND", rel_file, line_no)

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

    protocol_version = suite["aicp_version"]
    passed = not failures
    suite_mark = suite.get("compatibility_mark")
    marks = [suite_mark] if (passed and not degraded and isinstance(suite_mark, str)) else []

    return {
        "aicp_version": protocol_version,
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
