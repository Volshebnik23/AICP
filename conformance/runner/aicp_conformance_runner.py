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
from aicp_ref.signatures import signature_verifier_available, verify_ed25519  # noqa: E402


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


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
    case_validator = _build_validator(schema, ROOT / suite["schema_ref"]) if schema is not None else None
    core_schema_path = ROOT / "schemas/core/aicp-core-message.schema.json"
    core_schema = load_json(core_schema_path)
    core_validator = _build_validator(core_schema, core_schema_path)
    can_verify_signatures = signature_verifier_available()
    key_map = load_json(ROOT / "fixtures/keys/GT_public_keys.json")

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

    failures: list[dict[str, Any]] = []

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

        if can_verify_signatures:
            for line_no, msg in rows:
                for sig in msg.get("signatures", []) or []:
                    signer = sig.get("signer")
                    key = key_map.get(signer)
                    if not key:
                        add_failure(t_failures, "CT-SIGNATURE-VERIFY-01", f"missing public key for signer {signer}", rel_file, line_no)
                        continue
                    if not verify_ed25519(key.get("public_key_b64url", ""), sig.get("sig_b64url", ""), sig.get("object_hash", "")):
                        add_failure(t_failures, "CT-SIGNATURE-VERIFY-01", "signature verification failed", rel_file, line_no)
        else:
            expected = {e.get("test_id") for e in transcript.get("expected_failures", [])}
            if "CT-SIGNATURE-VERIFY-01" in expected:
                add_failure(t_failures, "CT-SIGNATURE-VERIFY-01", "signature verification unavailable in environment", rel_file, None)

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
                            if code not in policy_reason_codes:
                                add_failure(t_failures, "PE-REASON-CODES-01", f"unknown reason_code '{code}'", rel_file, line_no)
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

        failures.extend(_evaluate_transcript_expectations(transcript, t_failures, rel_file))

    version = (ROOT / "VERSION").read_text(encoding="utf-8").strip()
    passed = not failures
    suite_mark = suite.get("compatibility_mark")
    marks = [suite_mark] if passed and isinstance(suite_mark, str) else []

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

    print(f"Conformance {'PASSED' if report['passed'] else 'FAILED'}: {report['suite_id']} -> {out_path.relative_to(ROOT)}")
    if report["failures"]:
        for f in report["failures"]:
            print(f" - [{f['test_id']}] {f['file']}:{f['line']} {f['message']}")

    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
