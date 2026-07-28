#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import copy
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


ROOT = Path(__file__).resolve().parents[1]
REF_PY = ROOT / "reference/python"
if str(REF_PY) not in sys.path:
    sys.path.insert(0, str(REF_PY))

from aicp_ref_v02.contract_agreement import (  # noqa: E402
    ACCEPT_BINDING,
    ACTIVE_HEAD,
    AGREEMENT_STATE,
    CHECK_IDS,
    CONFLICT_BINDING,
    CONTEXT_BINDING,
    CONTRACT_HASH,
    CONTRACT_ID,
    CONTRACT_REF,
    PROPOSAL_BINDING,
    build_acceptance_binding,
    build_proposal_binding,
    choose_resolution,
    compute_contract_hash,
    current_head_reference,
    proposal_candidate,
    reduce_transcript,
)
from aicp_ref.hashing import message_hash_from_body  # noqa: E402
from aicp_ref.jcs import canonicalize_json  # noqa: E402


FIXTURE_ROOT = ROOT / "fixtures/core_v0_2/exact_contract_agreement"
SUITE_PATH = ROOT / "conformance/core/CT_CORE_0.2.json"
FAKE_HASH = "sha256:" + ("A" * 43)
OTHER_HASH = "sha256:" + ("B" * 43)
SESSION_ID = "session-core-v02-exact-agreement"
CONTRACT_ID_VALUE = "contract-exact-agreement"
PRIVATE_KEYS = json.loads(
    (ROOT / "fixtures/keys/TEST_private_keys.json").read_text(encoding="utf-8")
)


def _b64url_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _b64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def signature(
    object_hash: str,
    *,
    signer: str = "agent:S",
    signing_key: str | None = None,
    kid: str | None = None,
) -> dict[str, str]:
    key_name = signing_key or signer
    meta = PRIVATE_KEYS[key_name]
    private_key = Ed25519PrivateKey.from_private_bytes(
        _b64url_decode(meta["private_key_b64url"])
    )
    signature_bytes = private_key.sign(
        f"AICP1\0SIG\0{object_hash}".encode("utf-8")
    )
    return {
        "signer": signer,
        "kid": kid or meta["kid"],
        "object_type": "message",
        "object_hash": object_hash,
        "sig_b64url": _b64url_encode(signature_bytes),
    }


def sign_message(
    message: dict[str, Any],
    *,
    signer: str = "agent:S",
    signing_key: str | None = None,
    kid: str | None = None,
) -> dict[str, str]:
    item = signature(
        message["message_hash"],
        signer=signer,
        signing_key=signing_key,
        kid=kid,
    )
    message.setdefault("signatures", []).append(item)
    return item


def contract(version: str, goal: str | None = None, contract_id: str = CONTRACT_ID_VALUE) -> dict[str, Any]:
    return {
        "contract_id": contract_id,
        "contract_version": version,
        "goal": goal or f"Exact agreement for {version}",
        "roles": ["proposer", "acceptor"],
    }


def _body_without_hash(message: dict[str, Any]) -> dict[str, Any]:
    body = copy.deepcopy(message)
    body.pop("message_hash", None)
    body.pop("signatures", None)
    return body


def rehash(messages: list[dict[str, Any]]) -> None:
    previous: str | None = None
    for message in messages:
        message.pop("message_hash", None)
        message.pop("prev_msg_hash", None)
        if previous is not None:
            message["prev_msg_hash"] = previous
        message["message_hash"] = message_hash_from_body(_body_without_hash(message))
        previous = message["message_hash"]


class Builder:
    def __init__(self) -> None:
        self.messages: list[dict[str, Any]] = []

    def add(
        self,
        message_type: str,
        payload: dict[str, Any],
        *,
        message_id: str,
        contract_ref: dict[str, Any] | None = None,
        contract_id: str = CONTRACT_ID_VALUE,
        sender: str | None = None,
    ) -> dict[str, Any]:
        message: dict[str, Any] = {
            "session_id": SESSION_ID,
            "message_id": message_id,
            "timestamp": f"2026-01-01T00:00:{len(self.messages):02d}Z",
            "sender": sender or ("agent://alice" if len(self.messages) % 2 == 0 else "agent://bob"),
            "message_type": message_type,
            "contract_id": contract_id,
            "payload": copy.deepcopy(payload),
        }
        if contract_ref is not None:
            message["contract_ref"] = copy.deepcopy(contract_ref)
        self.messages.append(message)
        rehash(self.messages)
        return message

    def propose(
        self,
        value: dict[str, Any],
        *,
        message_id: str,
        base: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        binding = build_proposal_binding(value, base=base)
        return self.add(
            "CONTRACT_PROPOSE",
            {
                "contract": copy.deepcopy(value),
                "contract_hash": binding["contract_hash"],
            },
            message_id=message_id,
            contract_ref=binding["contract_ref"],
            contract_id=value["contract_id"],
        )

    def accept(
        self,
        proposal: dict[str, Any],
        *,
        accepted: bool,
        message_id: str,
        replay: bool = False,
        contract_id: str | None = None,
    ) -> dict[str, Any]:
        return self.add(
            "CONTRACT_ACCEPT",
            build_acceptance_binding(proposal, accepted=accepted, replay=replay),
            message_id=message_id,
            contract_ref=proposal["contract_ref"],
            contract_id=contract_id or proposal["contract_id"],
        )

    def context(
        self,
        reference: dict[str, Any],
        *,
        message_id: str,
        effect: str = "none",
    ) -> dict[str, Any]:
        return self.add(
            "CONTEXT_AMEND",
            {
                "amendment": {"topic": "context-only", "value": message_id},
                "contract_effect": effect,
            },
            message_id=message_id,
            contract_ref=reference,
        )

    def action(
        self,
        reference: dict[str, Any],
        *,
        message_id: str,
    ) -> dict[str, Any]:
        return self.add(
            "ATTEST_ACTION",
            {
                "action_id": f"action-{message_id}",
                "action_type": "TEST",
                "result_hash": FAKE_HASH,
            },
            message_id=message_id,
            contract_ref=reference,
        )

    def error(
        self,
        *,
        message_id: str,
        reference: dict[str, Any] | None = None,
        contract_id: str = CONTRACT_ID_VALUE,
    ) -> dict[str, Any]:
        return self.add(
            "ERROR",
            {
                "error_code": "TEST_ERROR",
                "error_class": "STATE",
                "severity": "low",
                "applies_to": {"message_id": "target-message"},
                "disposition": "REJECTED",
            },
            message_id=message_id,
            contract_ref=reference,
            contract_id=contract_id,
        )

    def resolve(
        self,
        proposals: list[dict[str, Any]],
        selected: dict[str, Any],
        *,
        message_id: str,
    ) -> dict[str, Any]:
        candidates = [proposal_candidate(item) for item in proposals]
        selected_candidate = proposal_candidate(selected)
        return self.add(
            "RESOLVE_CONFLICT",
            {
                "conflict_id": f"conflict-{message_id}",
                "conflict_class": "CONTRACT_HEAD",
                "candidates": candidates,
                "resolution": choose_resolution(selected_candidate),
            },
            message_id=message_id,
            contract_ref=selected["contract_ref"],
        )


@dataclass
class Fixture:
    fixture_id: str
    path: str
    messages: list[dict[str, Any]]
    expect_pass: bool
    expected_failures: list[str]
    expected_state: str | None = None
    expected_active_head: dict[str, Any] | None = None
    expected_proposal_ids: list[str] | None = None
    expected_selected_conflict_result: dict[str, Any] | None = None
    expected_accepted_tuple_count: int = 0
    expected_rejected_tuple_count: int = 0
    invalid_indices: list[int] | None = None
    expected_semantic_issue_ids: list[str] | None = None


def _attach_state_expectations(fixture: Fixture) -> Fixture:
    invalid_indices = fixture.invalid_indices or []
    state = reduce_transcript(fixture.messages, invalid_indices)
    if fixture.expected_state is not None:
        assert state.state == fixture.expected_state, fixture.fixture_id
    if fixture.expected_active_head is not None:
        assert state.active_head == fixture.expected_active_head, fixture.fixture_id
    fixture.expected_state = state.state
    fixture.expected_active_head = state.active_head
    fixture.expected_proposal_ids = sorted(state.proposals)
    fixture.expected_selected_conflict_result = state.selected_conflict_result
    fixture.expected_accepted_tuple_count = len(state.acceptance_tuples)
    fixture.expected_rejected_tuple_count = len(state.rejected_tuples)
    fixture.expected_semantic_issue_ids = sorted(
        {issue.code for issue in state.issues}
    )
    return fixture


def _positive(
    fixture_id: str,
    slug: str,
    builder: Builder,
    state: str,
    active_head: dict[str, Any] | None,
) -> Fixture:
    return _attach_state_expectations(Fixture(
        fixture_id,
        f"fixtures/core_v0_2/exact_contract_agreement/positive/{slug}.jsonl",
        builder.messages,
        True,
        [],
        state,
        active_head,
    ))


def _negative(
    fixture_id: str,
    slug: str,
    messages: list[dict[str, Any]],
    failures: list[str],
    *,
    invalid_indices: list[int] | None = None,
    rehash_messages: bool = True,
) -> Fixture:
    if rehash_messages:
        rehash(messages)
    return _attach_state_expectations(Fixture(
        fixture_id,
        f"fixtures/core_v0_2/exact_contract_agreement/negative/{slug}_expected_fail.jsonl",
        messages,
        False,
        failures,
        invalid_indices=invalid_indices or [],
    ))


def positive_fixtures() -> list[Fixture]:
    fixtures: list[Fixture] = []

    b = Builder()
    p1 = b.propose(contract("v1"), message_id="p01-propose-v1")
    b.accept(p1, accepted=True, message_id="p01-accept-v1")
    b.action(current_head_reference(p1["contract_ref"]), message_id="p01-action")
    fixtures.append(_positive("CT2-POS-01", "01_initial_accept_action", b, "ACTIVE_HEAD", current_head_reference(p1["contract_ref"])))

    b = Builder()
    p1 = b.propose(contract("v1"), message_id="p02-propose-v1")
    b.accept(p1, accepted=False, message_id="p02-reject-v1")
    fixtures.append(_positive("CT2-POS-02", "02_initial_reject", b, "NO_ACTIVE_CONTRACT", None))

    b = Builder()
    p1 = b.propose(contract("v1"), message_id="p03-propose-v1")
    b.accept(p1, accepted=True, message_id="p03-accept-v1")
    p2 = b.propose(contract("v2"), message_id="p03-propose-v2", base=current_head_reference(p1["contract_ref"]))
    b.accept(p2, accepted=True, message_id="p03-accept-v2")
    fixtures.append(_positive("CT2-POS-03", "03_revision_accept", b, "ACTIVE_HEAD", current_head_reference(p2["contract_ref"])))

    b = Builder()
    p1 = b.propose(contract("v1"), message_id="p04-propose-v1")
    b.accept(p1, accepted=True, message_id="p04-accept-v1")
    active = current_head_reference(p1["contract_ref"])
    b.context(active, message_id="p04-context")
    b.action(active, message_id="p04-action")
    fixtures.append(_positive("CT2-POS-04", "04_context_only_then_action", b, "ACTIVE_HEAD", active))

    b = Builder()
    p1 = b.propose(contract("v1"), message_id="p05-propose-v1")
    b.accept(p1, accepted=True, message_id="p05-accept-v1")
    active = current_head_reference(p1["contract_ref"])
    p2a = b.propose(contract("v2-a"), message_id="p05-propose-v2a", base=active)
    p2b = b.propose(contract("v2-b"), message_id="p05-propose-v2b", base=active)
    b.resolve([p2a, p2b], p2b, message_id="p05-resolve")
    fixtures.append(_positive("CT2-POS-05", "05_competing_choose", b, "CONFLICT_RESOLVED", current_head_reference(p2b["contract_ref"])))

    b = Builder()
    p1 = b.propose(contract("v1"), message_id="p06-propose-v1")
    b.accept(p1, accepted=True, message_id="p06-accept-v1")
    b.accept(p1, accepted=True, message_id="p06-replay-v1", replay=True)
    fixtures.append(_positive("CT2-POS-06", "06_exact_accept_replay", b, "ACTIVE_HEAD", current_head_reference(p1["contract_ref"])))

    b = Builder()
    b.error(message_id="p07-error-before")
    fixtures.append(_positive("CT2-POS-07", "07_error_before_agreement", b, "NO_ACTIVE_CONTRACT", None))

    b = Builder()
    p1 = b.propose(contract("v1"), message_id="p08-propose-v1")
    b.accept(p1, accepted=True, message_id="p08-accept-v1")
    active = current_head_reference(p1["contract_ref"])
    b.error(message_id="p08-error-after", reference=active)
    fixtures.append(_positive("CT2-POS-08", "08_error_after_agreement", b, "ACTIVE_HEAD", active))

    b = Builder()
    p1 = b.propose(contract("v1"), message_id="p09-propose-v1")
    b.accept(p1, accepted=True, message_id="p09-accept-v1")
    active = current_head_reference(p1["contract_ref"])
    signed_action = b.action(active, message_id="p09-signed-action")
    signed_action["sender"] = "agent:S"
    rehash(b.messages)
    sign_message(signed_action)
    fixtures.append(
        _positive(
            "CT2-POS-09",
            "09_valid_optional_signature",
            b,
            "ACTIVE_HEAD",
            active,
        )
    )
    return fixtures


def _base_initial(prefix: str = "n") -> tuple[Builder, dict[str, Any]]:
    b = Builder()
    p1 = b.propose(contract("v1"), message_id=f"{prefix}-propose-v1")
    return b, p1


def _accepted_initial(prefix: str) -> tuple[Builder, dict[str, Any], dict[str, Any]]:
    b, p1 = _base_initial(prefix)
    b.accept(p1, accepted=True, message_id=f"{prefix}-accept-v1")
    return b, p1, current_head_reference(p1["contract_ref"])


def negative_fixtures() -> list[Fixture]:
    out: list[Fixture] = []

    b, p = _base_initial("n01")
    p.pop("contract_ref")
    out.append(_negative("CT2-NEG-01", "01_missing_contract_ref", b.messages, [CONTRACT_REF]))

    b, p = _base_initial("n02")
    p["contract_ref"] = {"branch_id": "main", "head": {"version": "v1"}}
    out.append(_negative("CT2-NEG-02", "02_malformed_contract_ref", b.messages, [CONTRACT_REF]))

    b, p = _base_initial("n03")
    p["payload"]["contract_hash"] = FAKE_HASH
    p["contract_ref"]["head"]["contract_hash"] = FAKE_HASH
    out.append(_negative("CT2-NEG-03", "03_incorrect_contract_hash", b.messages, [CONTRACT_HASH]))

    b, p = _base_initial("n04")
    p["contract_ref"]["head"]["contract_hash"] = FAKE_HASH
    out.append(_negative("CT2-NEG-04", "04_head_hash_mismatch", b.messages, [PROPOSAL_BINDING]))

    b, p = _base_initial("n05")
    p["contract_ref"]["head"]["version"] = "substituted-version"
    out.append(_negative("CT2-NEG-05", "05_head_version_mismatch", b.messages, [PROPOSAL_BINDING]))

    b, p = _base_initial("n06")
    p["contract_id"] = "other-contract"
    out.append(_negative("CT2-NEG-06", "06_envelope_contract_id_mismatch", b.messages, [CONTRACT_ID]))

    b, _ = _base_initial("n07")
    b.error(message_id="n07-contract-change", contract_id="other-contract")
    out.append(_negative("CT2-NEG-07", "07_contract_id_changes", b.messages, [CONTRACT_ID]))

    b = Builder()
    fake_ref = {"branch_id": "main", "head": {"version": "v1", "contract_hash": FAKE_HASH}}
    b.add(
        "CONTRACT_ACCEPT",
        {
            "accepted": True,
            "proposal_message_id": "unknown-proposal",
            "proposal_message_hash": FAKE_HASH,
            "contract_hash": FAKE_HASH,
        },
        message_id="n08-accept-unknown",
        contract_ref=fake_ref,
    )
    out.append(_negative("CT2-NEG-08", "08_accept_unknown_proposal", b.messages, [ACCEPT_BINDING]))

    b = Builder()
    future_contract = contract("v1")
    future_binding = build_proposal_binding(future_contract)
    b.add(
        "CONTRACT_ACCEPT",
        {
            "accepted": True,
            "proposal_message_id": "n09-future-proposal",
            "proposal_message_hash": FAKE_HASH,
            "contract_hash": future_binding["contract_hash"],
        },
        message_id="n09-accept-future",
        contract_ref=future_binding["contract_ref"],
    )
    b.add(
        "CONTRACT_PROPOSE",
        {"contract": future_contract, "contract_hash": future_binding["contract_hash"]},
        message_id="n09-future-proposal",
        contract_ref=future_binding["contract_ref"],
    )
    out.append(_negative("CT2-NEG-09", "09_accept_future_proposal", b.messages, [ACCEPT_BINDING]))

    b, p = _base_initial("n10")
    a = b.accept(p, accepted=True, message_id="n10-accept")
    a["payload"]["proposal_message_hash"] = FAKE_HASH
    out.append(_negative("CT2-NEG-10", "10_accept_wrong_message_hash", b.messages, [ACCEPT_BINDING]))

    b, p = _base_initial("n11")
    a = b.accept(p, accepted=True, message_id="n11-accept")
    a["payload"]["contract_hash"] = FAKE_HASH
    out.append(_negative("CT2-NEG-11", "11_accept_wrong_contract_hash", b.messages, [ACCEPT_BINDING]))

    b, p = _base_initial("n12")
    a = b.accept(p, accepted=True, message_id="n12-accept")
    a["contract_ref"]["branch_id"] = "substituted-branch"
    out.append(_negative("CT2-NEG-12", "12_accept_substituted_ref", b.messages, [ACCEPT_BINDING]))

    b, p1, active = _accepted_initial("n13")
    p2a = b.propose(contract("v2-a"), message_id="n13-propose-v2a", base=active)
    p2b = b.propose(contract("v2-b"), message_id="n13-propose-v2b", base=active)
    b.accept(p2a, accepted=True, message_id="n13-accept-v2a")
    b.accept(p2b, accepted=True, message_id="n13-accept-stale-v2b")
    out.append(_negative("CT2-NEG-13", "13_accept_stale_proposal", b.messages, [ACCEPT_BINDING]))

    b, p = _base_initial("n14")
    b.accept(p, accepted=False, message_id="n14-reject")
    b.action(current_head_reference(p["contract_ref"]), message_id="n14-action")
    out.append(_negative("CT2-NEG-14", "14_rejection_does_not_activate", b.messages, [ACTIVE_HEAD]))

    b, p1, active = _accepted_initial("n15")
    p2a = b.propose(contract("v2-a"), message_id="n15-propose-v2a", base=active)
    p2b = b.propose(contract("v2-b"), message_id="n15-propose-v2b", base=active)
    b.accept(p2a, accepted=True, message_id="n15-accept-v2a")
    b.accept(p2b, accepted=True, message_id="n15-replay-retarget", replay=True)
    out.append(_negative("CT2-NEG-15", "15_replay_retargets", b.messages, [ACCEPT_BINDING]))

    b, p = _base_initial("n16")
    b.context(current_head_reference(p["contract_ref"]), message_id="n16-context")
    out.append(_negative("CT2-NEG-16", "16_context_before_agreement", b.messages, [CONTEXT_BINDING]))

    b, p1, active1 = _accepted_initial("n17")
    p2 = b.propose(contract("v2"), message_id="n17-propose-v2", base=active1)
    b.accept(p2, accepted=True, message_id="n17-accept-v2")
    b.context(active1, message_id="n17-context-stale")
    out.append(_negative("CT2-NEG-17", "17_context_stale_head", b.messages, [CONTEXT_BINDING]))

    b, _, active = _accepted_initial("n18")
    b.context(active, message_id="n18-context", effect="replace")
    out.append(_negative("CT2-NEG-18", "18_context_contract_effect", b.messages, [CONTEXT_BINDING]))

    b, p = _base_initial("n19")
    b.action(current_head_reference(p["contract_ref"]), message_id="n19-action")
    out.append(_negative("CT2-NEG-19", "19_action_before_agreement", b.messages, [ACTIVE_HEAD]))

    b, p1, active1 = _accepted_initial("n20")
    p2 = b.propose(contract("v2"), message_id="n20-propose-v2", base=active1)
    b.accept(p2, accepted=True, message_id="n20-accept-v2")
    b.action(active1, message_id="n20-action-stale")
    out.append(_negative("CT2-NEG-20", "20_action_stale_head", b.messages, [ACTIVE_HEAD]))

    b, _, active = _accepted_initial("n21")
    context_message = b.context(active, message_id="n21-context")
    p2 = b.propose(contract("v2"), message_id="n21-propose-v2", base=active)
    bad_candidate = {
        "proposal_message_id": context_message["message_id"],
        "proposal_message_hash": context_message["message_hash"],
        "contract_hash": p2["payload"]["contract_hash"],
        "contract_ref": p2["contract_ref"],
    }
    b.add(
        "RESOLVE_CONFLICT",
        {
            "conflict_id": "n21-conflict",
            "conflict_class": "CONTRACT_HEAD",
            "candidates": [bad_candidate, proposal_candidate(p2)],
            "resolution": choose_resolution(proposal_candidate(p2)),
        },
        message_id="n21-resolve",
        contract_ref=p2["contract_ref"],
    )
    out.append(_negative("CT2-NEG-21", "21_candidate_non_proposal", b.messages, [CONFLICT_BINDING]))

    b, _, active = _accepted_initial("n22")
    p2a = b.propose(contract("v2-a"), message_id="n22-propose-v2a", base=active)
    p2b = b.propose(contract("v2-b"), message_id="n22-propose-v2b", base=active)
    r = b.resolve([p2a, p2b], p2a, message_id="n22-resolve")
    r["payload"]["candidates"][0]["proposal_message_hash"] = FAKE_HASH
    out.append(_negative("CT2-NEG-22", "22_candidate_wrong_message_hash", b.messages, [CONFLICT_BINDING]))

    b, _, active = _accepted_initial("n23")
    p2a = b.propose(contract("v2-a"), message_id="n23-propose-v2a", base=active)
    p2b = b.propose(contract("v2-b"), message_id="n23-propose-v2b", base=active)
    r = b.resolve([p2a, p2b], p2a, message_id="n23-resolve")
    r["payload"]["candidates"][0]["contract_hash"] = FAKE_HASH
    out.append(_negative("CT2-NEG-23", "23_candidate_wrong_contract_hash", b.messages, [CONFLICT_BINDING]))

    b = Builder()
    p1 = b.propose(contract("v1"), message_id="n24-propose-v1")
    stale = b.propose(contract("v-stale"), message_id="n24-propose-stale")
    b.accept(p1, accepted=True, message_id="n24-accept-v1")
    active = current_head_reference(p1["contract_ref"])
    p2 = b.propose(contract("v2"), message_id="n24-propose-v2", base=active)
    b.resolve([stale, p2], p2, message_id="n24-resolve")
    out.append(_negative("CT2-NEG-24", "24_candidates_different_base", b.messages, [CONFLICT_BINDING]))

    b, _, active = _accepted_initial("n25")
    p2 = b.propose(contract("v2"), message_id="n25-propose-v2", base=active)
    r = b.resolve([p2, p2], p2, message_id="n25-resolve")
    out.append(_negative("CT2-NEG-25", "25_duplicate_candidate", b.messages, [CONFLICT_BINDING]))

    b, _, active = _accepted_initial("n26")
    p2a = b.propose(contract("v2-a"), message_id="n26-propose-v2a", base=active)
    p2b = b.propose(contract("v2-b"), message_id="n26-propose-v2b", base=active)
    p2c = b.propose(contract("v2-c"), message_id="n26-propose-v2c", base=active)
    r = b.resolve([p2a, p2b], p2a, message_id="n26-resolve")
    r["payload"]["resolution"] = choose_resolution(proposal_candidate(p2c))
    out.append(_negative("CT2-NEG-26", "26_selected_not_candidate", b.messages, [CONFLICT_BINDING]))

    b, _, active = _accepted_initial("n27")
    p2a = b.propose(contract("v2-a"), message_id="n27-propose-v2a", base=active)
    p2b = b.propose(contract("v2-b"), message_id="n27-propose-v2b", base=active)
    r = b.resolve([p2a, p2b], p2a, message_id="n27-resolve")
    r["payload"]["resolution"]["selected_contract_hash"] = FAKE_HASH
    out.append(_negative("CT2-NEG-27", "27_selected_fields_mismatch", b.messages, [CONFLICT_BINDING]))

    b, _, active = _accepted_initial("n28")
    p2a = b.propose(contract("v2-a"), message_id="n28-propose-v2a", base=active)
    p2b = b.propose(contract("v2-b"), message_id="n28-propose-v2b", base=active)
    r = b.resolve([p2a, p2b], p2a, message_id="n28-resolve")
    r["contract_ref"] = copy.deepcopy(p2b["contract_ref"])
    out.append(_negative("CT2-NEG-28", "28_resolution_substitutes_head", b.messages, [CONFLICT_BINDING]))

    b, p = _base_initial("n29")
    b.accept(p, accepted=True, message_id="n29-cross-contract-accept", contract_id="other-contract")
    out.append(_negative("CT2-NEG-29", "29_cross_contract_acceptance", b.messages, [CONTRACT_ID]))

    b, _, active = _accepted_initial("n30")
    wrong_base = {
        "branch_id": active["branch_id"],
        "head": {"version": "v0", "contract_hash": FAKE_HASH},
    }
    b.propose(contract("v2"), message_id="n30-propose-v2", base=wrong_base)
    out.append(_negative("CT2-NEG-30", "30_revision_wrong_base", b.messages, [PROPOSAL_BINDING]))

    b, p = _base_initial("n31")
    acceptance = b.accept(p, accepted=True, message_id="n31-changed-session")
    acceptance["session_id"] = "session-core-v02-substituted"
    out.append(
        _negative(
            "CT2-NEG-31",
            "31_acceptance_changed_session",
            b.messages,
            ["CT-INVARIANTS-01", AGREEMENT_STATE],
            invalid_indices=[1],
        )
    )

    b, p = _base_initial("n32")
    acceptance = b.accept(p, accepted=True, message_id="n32-invalid-message-hash")
    rehash(b.messages)
    acceptance["message_hash"] = OTHER_HASH
    out.append(
        _negative(
            "CT2-NEG-32",
            "32_acceptance_invalid_message_hash",
            b.messages,
            ["CT-MESSAGE-HASH-01"],
            invalid_indices=[1],
            rehash_messages=False,
        )
    )

    b, p = _base_initial("n33")
    acceptance = b.accept(p, accepted=True, message_id="n33-broken-prev")
    acceptance["prev_msg_hash"] = OTHER_HASH
    acceptance["message_hash"] = message_hash_from_body(
        _body_without_hash(acceptance)
    )
    out.append(
        _negative(
            "CT2-NEG-33",
            "33_acceptance_broken_prev_hash",
            b.messages,
            ["CT-HASH-CHAIN-01"],
            invalid_indices=[1],
            rehash_messages=False,
        )
    )

    b, _, active = _accepted_initial("n34")
    p2 = b.propose(contract("v2"), message_id="n34-propose-v2", base=active)
    acceptance = b.accept(
        p2, accepted=True, message_id="n34-invalid-signed-accept"
    )
    acceptance["sender"] = "agent:S"
    rehash(b.messages)
    sign_message(acceptance, signer="agent:S", signing_key="agent:T", kid="S1")
    out.append(
        _negative(
            "CT2-NEG-34",
            "34_revision_acceptance_invalid_signature",
            b.messages,
            ["CT-SIGNATURE-VERIFY-01"],
            invalid_indices=[3],
            rehash_messages=False,
        )
    )

    b, _, active = _accepted_initial("n35")
    proposal = b.propose(
        contract("v2"), message_id="n35-schema-invalid-proposal", base=active
    )
    proposal["unexpected_envelope_field"] = True
    out.append(
        _negative(
            "CT2-NEG-35",
            "35_revision_proposal_message_schema",
            b.messages,
            ["CT-SCHEMA-JSONL-01"],
            invalid_indices=[2],
        )
    )

    b, _, active = _accepted_initial("n36")
    p2a = b.propose(contract("v2-a"), message_id="n36-propose-v2a", base=active)
    p2b = b.propose(contract("v2-b"), message_id="n36-propose-v2b", base=active)
    resolution = b.resolve(
        [p2a, p2b], p2a, message_id="n36-invalid-hash-resolution"
    )
    rehash(b.messages)
    resolution["message_hash"] = OTHER_HASH
    out.append(
        _negative(
            "CT2-NEG-36",
            "36_conflict_resolution_invalid_message_hash",
            b.messages,
            ["CT-MESSAGE-HASH-01"],
            invalid_indices=[4],
            rehash_messages=False,
        )
    )

    b, p = _base_initial("n37")
    acceptance = b.accept(p, accepted=True, message_id="n37-unknown-signer")
    rehash(b.messages)
    acceptance["signatures"] = [
        signature(acceptance["message_hash"], signer="agent:unknown", signing_key="agent:S")
    ]
    out.append(
        _negative(
            "CT2-NEG-37",
            "37_signature_unknown_signer",
            b.messages,
            ["CT-SIGNATURE-VERIFY-01"],
            invalid_indices=[1],
            rehash_messages=False,
        )
    )

    b, p = _base_initial("n38")
    acceptance = b.accept(p, accepted=True, message_id="n38-kid-mismatch")
    rehash(b.messages)
    sign_message(acceptance, kid="WRONG-KID")
    out.append(
        _negative(
            "CT2-NEG-38",
            "38_signature_kid_mismatch",
            b.messages,
            ["CT-SIGNATURE-VERIFY-01"],
            invalid_indices=[1],
            rehash_messages=False,
        )
    )

    b, p = _base_initial("n39")
    acceptance = b.accept(p, accepted=True, message_id="n39-object-hash-mismatch")
    rehash(b.messages)
    acceptance["signatures"] = [signature(OTHER_HASH)]
    out.append(
        _negative(
            "CT2-NEG-39",
            "39_signature_object_hash_mismatch",
            b.messages,
            ["CT-SIGNATURE-HASH-01"],
            invalid_indices=[1],
            rehash_messages=False,
        )
    )

    b, p = _base_initial("n40")
    acceptance = b.accept(p, accepted=True, message_id="n40-copied-signature")
    rehash(b.messages)
    stale_signature = signature(p["message_hash"])
    stale_signature["object_hash"] = acceptance["message_hash"]
    acceptance["signatures"] = [stale_signature]
    out.append(
        _negative(
            "CT2-NEG-40",
            "40_copied_stale_signature",
            b.messages,
            ["CT-SIGNATURE-VERIFY-01"],
            invalid_indices=[1],
            rehash_messages=False,
        )
    )

    b, p = _base_initial("n41")
    acceptance = b.accept(p, accepted=True, message_id="n41-invalid-cosignature")
    rehash(b.messages)
    sign_message(acceptance)
    sign_message(
        acceptance,
        signer="agent:T",
        signing_key="agent:S",
        kid="T1",
    )
    out.append(
        _negative(
            "CT2-NEG-41",
            "41_one_invalid_signature_entry",
            b.messages,
            ["CT-SIGNATURE-VERIFY-01"],
            invalid_indices=[1],
            rehash_messages=False,
        )
    )
    return out


def _jsonl_text(messages: list[dict[str, Any]]) -> str:
    return "\n".join(
        json.dumps(message, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        for message in messages
    ) + "\n"


def _suite_entry(fixture: Fixture) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "id": fixture.fixture_id,
        "path": fixture.path,
        "expected_message_types": [
            message["message_type"] for message in fixture.messages
        ],
        "expected_agreement_state": fixture.expected_state,
        "expected_active_head": fixture.expected_active_head,
        "expected_proposal_ids": fixture.expected_proposal_ids,
        "expected_selected_conflict_result": (
            fixture.expected_selected_conflict_result
        ),
        "expected_accepted_tuple_count": fixture.expected_accepted_tuple_count,
        "expected_rejected_tuple_count": fixture.expected_rejected_tuple_count,
        "invalid_message_indices": fixture.invalid_indices or [],
    }
    if not fixture.expect_pass:
        entry["expect_pass"] = False
        entry["expected_failures"] = [
            {"test_id": test_id, "min_count": 1}
            for test_id in fixture.expected_failures
        ]
    return entry


def _check(test_id: str, description: str) -> dict[str, str]:
    return {"test_id": test_id, "description": description}


def build_suite(fixtures: list[Fixture]) -> dict[str, Any]:
    shared_checks = [
        _check("CT-SCHEMA-JSONL-01", "Validate each JSONL record against the Core v0.2 message schema"),
        _check("CT-MESSAGE-TYPE-REGISTRY-01", "Reuse only registered Core message type IDs"),
        _check("CT-PAYLOAD-SCHEMA-01", "Validate each lifecycle payload against Core v0.2 payload schemas"),
        _check("CT-HASH-CHAIN-01", "Require exact previous-message hash continuity"),
        _check("CT-PREV-MSG-REQUIRED-01", "Require prev_msg_hash after the first message"),
        _check("CT-INVARIANTS-01", "Require one session and unique message IDs"),
        _check("CT-SEQUENCE-01", "Match the declared deterministic fixture sequence"),
        _check("CT-SIGNATURE-HASH-01", "Bind optional signatures to the exact message hash"),
        _check("CT-SIGNATURE-STRUCTURE-01", "Retain optional Core signature structure validation"),
        _check("CT-SIGNATURE-VERIFY-01", "Cryptographically verify every present Ed25519 signature"),
        _check("CT-MESSAGE-HASH-01", "Recompute every message hash"),
    ]
    descriptions = {
        "CT2-CONTRACT-SCHEMA-01": "Validate the versioned contract object",
        "CT2-CONTRACT-ID-01": "Require one exact contract ID across envelope, object and transcript",
        "CT2-CONTRACT-HASH-01": "Recompute object_hash('contract', contract)",
        "CT2-CONTRACT-REF-01": "Validate exact branch/base/head version-hash references",
        "CT2-PROPOSAL-BINDING-01": "Bind proposal object, hash, version and active base",
        "CT2-ACCEPT-BINDING-01": "Bind acceptance to one prior exact proposal tuple",
        "CT2-ACTIVE-HEAD-01": "Require actions and targeted errors to bind the active head",
        "CT2-CONTEXT-BINDING-01": "Limit context amendments to active-head, no-contract-effect changes",
        "CT2-CONFLICT-BINDING-01": "Validate exact CHOOSE candidates and selected head",
        "CT2-AGREEMENT-STATE-01": "Derive and verify the final exact agreement state",
    }
    return {
        "suite_id": "CT-CORE-0.2",
        "suite_version": "0.2.0-experimental",
        "aicp_version": "0.2",
        "description": "Experimental post-UAT Core v0.2 exact contract artifact and active-head agreement.",
        "schema_ref": "schemas/core/aicp-core-message-v0.2.schema.json",
        "contract_schema_ref": "schemas/core/aicp-core-contract-v0.2.schema.json",
        "payload_schema_ref": "schemas/core/aicp-core-payloads-v0.2.schema.json",
        "payload_schema_map": {
            "CONTRACT_PROPOSE": "#/$defs/CONTRACT_PROPOSE",
            "CONTRACT_ACCEPT": "#/$defs/CONTRACT_ACCEPT",
            "CONTEXT_AMEND": "#/$defs/CONTEXT_AMEND",
            "ATTEST_ACTION": "#/$defs/ATTEST_ACTION",
            "RESOLVE_CONFLICT": "#/$defs/RESOLVE_CONFLICT",
            "ERROR": "#/$defs/ERROR",
        },
        "payload_schema_check_id": "CT-PAYLOAD-SCHEMA-01",
        "schema_failure_routes": {
            "CT-SCHEMA-JSONL-01": {
                "CONTRACT_PROPOSE": "CT2-CONTRACT-REF-01"
            },
            "CT-PAYLOAD-SCHEMA-01": {
                "CONTEXT_AMEND": "CT2-CONTEXT-BINDING-01"
            }
        },
        "canonical_payload_schema": False,
        "transcripts": [_suite_entry(fixture) for fixture in fixtures],
        "checks": shared_checks
        + [_check(check_id, descriptions[check_id]) for check_id in CHECK_IDS],
        "compatibility_mark": "AICP-Core-0.2",
    }


def build_cross_language_vectors(fixtures: list[Fixture]) -> dict[str, Any]:
    sample = contract("v-vector")
    binding = build_proposal_binding(sample)
    return {
        "vector_version": 1,
        "contract": sample,
        "canonical_json": canonicalize_json(sample),
        "contract_hash": compute_contract_hash(sample),
        "contract_ref": binding["contract_ref"],
        "positive": [
            {
                "path": fixture.path,
                "expected_state": fixture.expected_state,
                "expected_active_head": fixture.expected_active_head,
                "expected_proposal_ids": fixture.expected_proposal_ids,
                "expected_selected_conflict_result": (
                    fixture.expected_selected_conflict_result
                ),
                "expected_accepted_tuple_count": (
                    fixture.expected_accepted_tuple_count
                ),
                "expected_rejected_tuple_count": (
                    fixture.expected_rejected_tuple_count
                ),
                "invalid_message_indices": fixture.invalid_indices or [],
            }
            for fixture in fixtures
            if fixture.expect_pass
        ],
        "negative": [
            {
                "path": fixture.path,
                "expected_semantic_issue_ids": sorted(
                    fixture.expected_semantic_issue_ids or []
                ),
                "expected_runner_failure_ids": sorted(
                    fixture.expected_failures
                ),
                "expected_state": fixture.expected_state,
                "expected_active_head": fixture.expected_active_head,
                "expected_proposal_ids": fixture.expected_proposal_ids,
                "expected_selected_conflict_result": (
                    fixture.expected_selected_conflict_result
                ),
                "expected_accepted_tuple_count": (
                    fixture.expected_accepted_tuple_count
                ),
                "expected_rejected_tuple_count": (
                    fixture.expected_rejected_tuple_count
                ),
                "invalid_message_indices": fixture.invalid_indices or [],
            }
            for fixture in fixtures
            if not fixture.expect_pass
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if checked-in suite, fixtures, or vectors differ from generator output.",
    )
    args = parser.parse_args()
    fixtures = positive_fixtures() + negative_fixtures()
    outputs = {
        ROOT / fixture.path: _jsonl_text(fixture.messages)
        for fixture in fixtures
    }
    outputs[SUITE_PATH] = (
        json.dumps(build_suite(fixtures), indent=2, ensure_ascii=False) + "\n"
    )
    outputs[FIXTURE_ROOT / "cross_language_vectors.json"] = (
        json.dumps(build_cross_language_vectors(fixtures), indent=2, ensure_ascii=False)
        + "\n"
    )
    if args.check:
        stale = [
            path.relative_to(ROOT).as_posix()
            for path, expected in outputs.items()
            if not path.exists() or path.read_text(encoding="utf-8") != expected
        ]
        if stale:
            print("[FAIL] Core v0.2 generated artifacts are stale:")
            for relative in stale:
                print(f" - {relative}")
            return 1
        positive_count = sum(item.expect_pass for item in fixtures)
        negative_count = sum(not item.expect_pass for item in fixtures)
        print(
            "OK: Core v0.2 suite, "
            f"{positive_count} positive fixtures, {negative_count} negative "
            "fixtures, and vectors are current."
        )
        return 0

    for path, text in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print(
        "Generated Core v0.2 exact-agreement fixtures: "
        f"{sum(item.expect_pass for item in fixtures)} positive, "
        f"{sum(not item.expect_pass for item in fixtures)} negative."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
