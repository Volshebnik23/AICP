#!/usr/bin/env python3
"""M65 lifecycle checks kept outside the frozen product-IUT v1 runner bundle."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RUNNER_DIR = ROOT / "conformance/runner"
if str(RUNNER_DIR) not in sys.path:
    sys.path.insert(0, str(RUNNER_DIR))

from aicp_conformance_runner import run_suite as run_frozen_suite  # noqa: E402


M65_SUITE_PATHS = (
    "conformance/extensions/ID_IDENTITY_LC_0.1.json",
    "conformance/extensions/DS_DISPUTES_0.1.json",
    "conformance/extensions/DL_DELEGATION_0.1.json",
    "conformance/extensions/MP_MARKETPLACE_0.1.json",
    "conformance/extensions/PA_PARTICIPANTS_0.1.json",
    "conformance/extensions/PE_POLICY_EVAL_0.1.json",
    "conformance/extensions/DI_DELEGATED_IDENTITY_0.1.json",
)


def _resolve(path_like: str | Path) -> Path:
    path = Path(path_like)
    return path if path.is_absolute() else ROOT / path


def _rows(path_like: str | Path) -> list[tuple[int, dict[str, Any]]]:
    path = _resolve(path_like)
    return [
        (line_no, json.loads(line))
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if line.strip()
    ]


def _failure(test_id: str, message: str, file: str, line: int | None) -> dict[str, Any]:
    return {"test_id": test_id, "message": message, "file": file, "line": line}


def _object_hashes(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        object_hash = value.get("object_hash")
        if isinstance(object_hash, str) and object_hash:
            found.add(object_hash)
        for child in value.values():
            found.update(_object_hashes(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_object_hashes(child))
    return found


def _resolves(
    refs: Any,
    message_ids: set[str],
    message_hashes: set[str],
    object_hashes: set[str],
) -> bool:
    if not isinstance(refs, list):
        return False
    namespaces = {
        "msgid:": message_ids,
        "msghash:": message_hashes,
        "objhash:": object_hashes,
    }
    return any(
        isinstance(ref, str)
        and any(ref.startswith(prefix) and ref[len(prefix) :] in values for prefix, values in namespaces.items())
        for ref in refs
    )


def _identity_failures(rows: list[tuple[int, dict[str, Any]]], file: str, checks: set[str]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    announced_aids: set[str] = set()
    announced_kids: set[str] = set()
    for line_no, message in rows:
        message_type = message.get("message_type")
        payload = message.get("payload") or {}
        if message_type == "IDENTITY_ANNOUNCE":
            aid_hash = payload.get("aid_hash")
            if isinstance(aid_hash, str) and aid_hash:
                announced_aids.add(aid_hash)
            keys = (((payload.get("aid_ref") or {}).get("object") or {}).get("keys") or [])
            announced_kids.update(
                key["kid"]
                for key in keys
                if isinstance(key, dict)
                and isinstance(key.get("kid"), str)
                and key.get("status") != "revoked"
            )
        elif message_type == "AGENT_MIGRATION" and "ID-MIGRATE-01" in checks:
            aid_hash = payload.get("aid_hash")
            if aid_hash not in announced_aids:
                failures.append(_failure("ID-MIGRATE-01", "AGENT_MIGRATION.aid_hash must reference a prior IDENTITY_ANNOUNCE", file, line_no))
        elif message_type == "KEY_REVOKE" and "ID-REVOKE-01" in checks:
            target_kid = payload.get("target_kid")
            target_aid = payload.get("target_aid_hash")
            if target_kid not in announced_kids and target_aid not in announced_aids:
                failures.append(_failure("ID-REVOKE-01", "KEY_REVOKE must target a key or AID announced earlier in the transcript", file, line_no))
    return failures


def _dispute_failures(rows: list[tuple[int, dict[str, Any]]], file: str, checks: set[str]) -> list[dict[str, Any]]:
    failures: list[dict[str, Any]] = []
    prior_ids: set[str] = set()
    prior_hashes: set[str] = set()
    prior_objects: set[str] = set()
    challenge_ids: set[str] = set()
    arbitration_ids: set[str] = set()
    dispute_types = {"CLAIM_BREACH", "ARBITRATION_REQUEST", "ARBITRATION_RESULT"}
    for line_no, message in rows:
        message_type = message.get("message_type")
        payload = message.get("payload") or {}
        if message_type == "CHALLENGE_ASSERTION":
            challenge_id = payload.get("challenge_id")
            if isinstance(challenge_id, str) and challenge_id:
                challenge_ids.add(challenge_id)
        if message_type in dispute_types:
            refs = payload.get("evidence_refs")
            if "DS-EVIDENCE-01" in checks and not (
                isinstance(refs, list) and refs and all(isinstance(ref, str) and ref for ref in refs)
            ):
                failures.append(_failure("DS-EVIDENCE-01", f"{message_type} requires non-empty evidence_refs", file, line_no))
            if "DS-EVIDENCE-RESOLVE-01" in checks and not _resolves(refs, prior_ids, prior_hashes, prior_objects):
                failures.append(_failure("DS-EVIDENCE-RESOLVE-01", f"{message_type} evidence_refs must resolve to prior transcript evidence", file, line_no))
            if message_type == "ARBITRATION_REQUEST":
                related = payload.get("related_challenge_id")
                if "DS-ARBITRATION-01" in checks and related not in challenge_ids:
                    failures.append(_failure("DS-ARBITRATION-01", "ARBITRATION_REQUEST must reference a prior challenge", file, line_no))
                arbitration_id = payload.get("arbitration_id")
                if isinstance(arbitration_id, str) and arbitration_id:
                    arbitration_ids.add(arbitration_id)
            elif message_type == "ARBITRATION_RESULT" and "DS-ARBITRATION-01" in checks:
                if payload.get("arbitration_id") not in arbitration_ids:
                    failures.append(_failure("DS-ARBITRATION-01", "ARBITRATION_RESULT must reference a prior arbitration request", file, line_no))
        message_id = message.get("message_id")
        message_hash = message.get("message_hash")
        if isinstance(message_id, str) and message_id:
            prior_ids.add(message_id)
        if isinstance(message_hash, str) and message_hash:
            prior_hashes.add(message_hash)
        prior_objects.update(_object_hashes(payload))
    return failures


def _delegation_failures(rows: list[tuple[int, dict[str, Any]]], file: str, checks: set[str]) -> list[dict[str, Any]]:
    if "DL-REVOKE-01" not in checks:
        return []
    failures: list[dict[str, Any]] = []
    active: set[str] = set()
    for line_no, message in rows:
        payload = message.get("payload") or {}
        if message.get("message_type") == "DELEGATION_GRANT":
            delegation_id = payload.get("delegation_id")
            if isinstance(delegation_id, str) and delegation_id:
                active.add(delegation_id)
        elif message.get("message_type") == "DELEGATION_REVOKE":
            delegation_id = payload.get("delegation_id")
            if delegation_id not in active:
                failures.append(_failure("DL-REVOKE-01", "DELEGATION_REVOKE must reference a prior active delegation", file, line_no))
            else:
                active.remove(delegation_id)
    return failures


def _marketplace_failures(rows: list[tuple[int, dict[str, Any]]], file: str, checks: set[str]) -> list[dict[str, Any]]:
    if "MP-BID-01" not in checks:
        return []
    failures: list[dict[str, Any]] = []
    rfws: set[str] = set()
    bids: dict[str, str] = {}
    withdrawn: set[str] = set()
    for line_no, message in rows:
        message_type = message.get("message_type")
        payload = message.get("payload") or {}
        if message_type == "RFW_POST":
            rfw_id = payload.get("rfw_id")
            if isinstance(rfw_id, str) and rfw_id:
                rfws.add(rfw_id)
        elif message_type in {"BID_SUBMIT", "BID_UPDATE", "BID_WITHDRAW"}:
            bid_id = payload.get("bid_id")
            rfw_id = payload.get("rfw_id")
            if message_type in {"BID_UPDATE", "BID_WITHDRAW"}:
                if bid_id not in bids:
                    failures.append(_failure("MP-BID-01", f"{message_type} must reference a prior bid", file, line_no))
                elif bids[bid_id] != rfw_id:
                    failures.append(_failure("MP-BID-01", f"{message_type} must preserve the original bid RFW", file, line_no))
                if bid_id in withdrawn:
                    failures.append(_failure("MP-BID-01", f"{message_type} cannot reuse a withdrawn bid", file, line_no))
            if message_type in {"BID_SUBMIT", "BID_UPDATE"} and isinstance(bid_id, str) and bid_id and rfw_id in rfws:
                bids[bid_id] = rfw_id
            elif message_type == "BID_WITHDRAW" and isinstance(bid_id, str):
                withdrawn.add(bid_id)
    return failures


def _participant_failures(rows: list[tuple[int, dict[str, Any]]], file: str, checks: set[str]) -> list[dict[str, Any]]:
    if "PA-MEM-01" not in checks:
        return []
    failures: list[dict[str, Any]] = []
    joined: set[str] = set()
    for line_no, message in rows:
        payload = message.get("payload") or {}
        if message.get("message_type") == "PARTICIPANT_JOIN":
            participant_id = payload.get("participant_id")
            if isinstance(participant_id, str) and participant_id:
                joined.add(participant_id)
        elif message.get("message_type") == "PARTICIPANT_LEAVE":
            participant_id = payload.get("participant_id")
            if participant_id not in joined:
                failures.append(_failure("PA-MEM-01", "PARTICIPANT_LEAVE must reference a prior join", file, line_no))
            if participant_id != message.get("sender"):
                failures.append(_failure("PA-MEM-01", "PARTICIPANT_LEAVE participant_id must equal sender", file, line_no))
    return failures


def _policy_failures(rows: list[tuple[int, dict[str, Any]]], file: str, checks: set[str]) -> list[dict[str, Any]]:
    if "PE-ATTEST-01" not in checks:
        return []
    failures: list[dict[str, Any]] = []
    results: dict[str, str] = {}
    actions: set[str] = set()
    prior_ids: set[str] = set()
    prior_hashes: set[str] = set()
    for line_no, message in rows:
        message_type = message.get("message_type")
        payload = message.get("payload") or {}
        if message_type == "POLICY_EVAL_RESULT":
            eval_id = payload.get("eval_id")
            message_hash = message.get("message_hash")
            if isinstance(eval_id, str) and isinstance(message_hash, str):
                results[eval_id] = message_hash
        elif message_type == "ATTEST_ACTION":
            action_id = payload.get("action_id")
            if isinstance(action_id, str) and action_id:
                actions.add(action_id)
        elif message_type == "POLICY_DECISION_ATTEST":
            expected_ref = results.get(payload.get("eval_id"))
            if expected_ref is None or payload.get("policy_decision_ref") != expected_ref:
                failures.append(_failure("PE-ATTEST-01", "POLICY_DECISION_ATTEST must bind the prior evaluation result hash", file, line_no))
            attestation_ref = payload.get("attestation_ref")
            ref_bound = isinstance(attestation_ref, str) and (
                attestation_ref in prior_ids
                or attestation_ref in prior_hashes
                or (attestation_ref.startswith("msgid:") and attestation_ref[6:] in prior_ids)
                or (attestation_ref.startswith("msghash:") and attestation_ref[8:] in prior_hashes)
            )
            if payload.get("related_action_id") not in actions and not ref_bound:
                failures.append(_failure("PE-ATTEST-01", "POLICY_DECISION_ATTEST must bind prior action evidence", file, line_no))
        message_id = message.get("message_id")
        message_hash = message.get("message_hash")
        if isinstance(message_id, str):
            prior_ids.add(message_id)
        if isinstance(message_hash, str):
            prior_hashes.add(message_hash)
    return failures


def _delegated_identity_failures(rows: list[tuple[int, dict[str, Any]]], file: str, checks: set[str]) -> list[dict[str, Any]]:
    if "DI-REVOKE-01" not in checks:
        return []
    failures: list[dict[str, Any]] = []
    issued: set[str] = set()
    for line_no, message in rows:
        payload = message.get("payload") or {}
        if message.get("message_type") == "SUBJECT_BINDING_ISSUE":
            binding_hash = payload.get("binding_hash")
            if isinstance(binding_hash, str) and binding_hash:
                issued.add(binding_hash)
        elif message.get("message_type") == "SUBJECT_BINDING_REVOKE" and payload.get("binding_hash") not in issued:
            failures.append(_failure("DI-REVOKE-01", "SUBJECT_BINDING_REVOKE must reference a prior issued binding", file, line_no))
    return failures


VALIDATORS = {
    "ID-IDENTITY-LC-0.1": _identity_failures,
    "DS-DISPUTES-0.1": _dispute_failures,
    "DL-DELEGATION-0.1": _delegation_failures,
    "MP-MARKETPLACE-0.1": _marketplace_failures,
    "PA-PARTICIPANTS-0.1": _participant_failures,
    "PE-POLICY-EVAL-0.1": _policy_failures,
    "DI-DELEGATED-IDENTITY-0.1": _delegated_identity_failures,
}

VALIDATOR_CHECKS = {
    _identity_failures: {"ID-MIGRATE-01", "ID-REVOKE-01"},
    _dispute_failures: {"DS-ARBITRATION-01"},
    _delegation_failures: {"DL-REVOKE-01"},
    _marketplace_failures: {"MP-BID-01"},
    _participant_failures: {"PA-MEM-01"},
    _policy_failures: {"PE-ATTEST-01"},
    _delegated_identity_failures: {"DI-REVOKE-01"},
}


def extension_semantic_failures(suite_path: str | Path) -> list[dict[str, Any]]:
    suite = json.loads(_resolve(suite_path).read_text(encoding="utf-8"))
    checks = {
        check.get("test_id")
        for check in suite.get("checks", [])
        if isinstance(check, dict) and isinstance(check.get("test_id"), str)
    }
    validator = VALIDATORS.get(suite.get("suite_id"))
    if validator is None:
        matches = [
            candidate
            for candidate, candidate_checks in VALIDATOR_CHECKS.items()
            if checks & candidate_checks
        ]
        if len(matches) != 1:
            return []
        validator = matches[0]
    failures: list[dict[str, Any]] = []
    for transcript in suite.get("transcripts", []):
        if not isinstance(transcript, dict) or transcript.get("expect_pass", True) is False:
            continue
        path = transcript.get("path")
        if not isinstance(path, str):
            continue
        failures.extend(validator(_rows(path), path, checks))
    return failures


def run_suite(suite_path: str | Path, *, report_format: str = "legacy") -> dict[str, Any]:
    """Run the frozen product-IUT suite engine plus additive M65 extension semantics."""
    report = run_frozen_suite(_resolve(suite_path), report_format=report_format)
    failures = extension_semantic_failures(suite_path)
    if failures:
        report["failures"].extend(failures)
        report["passed"] = False
        report["compatibility_marks"] = []
    return report
