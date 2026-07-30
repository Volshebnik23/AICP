#!/usr/bin/env python3
"""Generate CAPNEG v0.2 conformance cases and shared language vectors."""

from __future__ import annotations

import argparse
import base64
import copy
import json
import sys
from pathlib import Path
from typing import Any, Callable

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


ROOT = Path(__file__).resolve().parents[1]
REF_PY = ROOT / "reference/python"
if str(REF_PY) not in sys.path:
    sys.path.insert(0, str(REF_PY))

from aicp_ref.hashing import message_hash_from_body, object_hash  # noqa: E402
from aicp_ref.validate import message_body_without_hash_and_signatures  # noqa: E402
from capneg_v02_fixture_model import (  # noqa: E402
    COMPOSITION_HASH_DOMAIN,
    COMPOSITION_VERSION,
    canonical_profile_ref_key,
)


OUT = ROOT / "fixtures/extensions/capneg_v0_2"
POSITIVE_OUT = OUT / "positive_cases.json"
NEGATIVE_OUT = OUT / "negative_cases.json"
VECTORS_OUT = OUT / "cross_language_vectors.json"
PROJECTION_OUT = (
    ROOT / "fixtures/extensions/object_resync/state_projection_v2"
)
PROJECTION_POSITIVE_OUT = PROJECTION_OUT / "positive_cases.json"
PROJECTION_NEGATIVE_OUT = PROJECTION_OUT / "negative_cases.json"
PRIVATE_KEYS = ROOT / "fixtures/keys/TEST_private_keys.json"
PUBLIC_KEYS = ROOT / "fixtures/keys/GT_public_keys.json"
REASON_CODES = ROOT / "registry/capneg_reason_codes.json"
ORACLE_EXPECTATIONS = OUT / "oracle_expectations.json"
COMPOSITION_ORACLE = OUT / "composition_oracle.json"
NEGOTIATION_HASH_DOMAIN = "capneg.negotiation_result"
PROJECTION_OBJECT_TYPE = "session_state_projection"
PROJECTION_VERSION = "aicp.session_state_projection.v2"


def ref(profile_id: str, version: str = "0.1") -> dict[str, str]:
    return {"profile_id": profile_id, "profile_version": version}


BASE = ref("AICP-BASE")
BASE_V02 = ref("AICP-BASE", "0.2")
AUTH = ref("AICP-AUTHENTICATED-BASE")
MEDIATED = ref("AICP-MEDIATED-BLOCKING")
MEDIATED_OPS = ref("AICP-MEDIATED-BLOCKING-OPS")
RESUMABLE = ref("AICP-RESUMABLE-SESSIONS")
EXECUTION = ref("AICP-EXECUTION-INTEROP")
DELEGATED = ref("AICP-DELEGATED-IDENTITY")
WORKFLOW = ref("AICP-WORKFLOW-ORCHESTRATION-DELEGATION")
AGENT_MEDIA = ref("AICP-AGENT-MEDIA")
BAZAAR = ref("AICP-BAZAAR-RECEPTION")
POLICY_ABAC = ref("AICP-POLICY-ABAC-RBAC")
POLICY_LLM = ref("AICP-POLICY-LLM-SAFETY")
PARTY_A = "agent:S"
PARTY_B = "agent:T"
PARTY_C = "agent:U"


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def configure_root(root: Path) -> None:
    """Point every fixture input/output at one explicit repository tree."""

    global ROOT, OUT, POSITIVE_OUT, NEGATIVE_OUT, VECTORS_OUT
    global PROJECTION_OUT, PROJECTION_POSITIVE_OUT, PROJECTION_NEGATIVE_OUT
    global PRIVATE_KEYS, PUBLIC_KEYS, REASON_CODES, ORACLE_EXPECTATIONS
    global COMPOSITION_ORACLE, PRIVATE_KEY_MAP, PUBLIC_KEY_MAP

    ROOT = root.resolve()
    OUT = ROOT / "fixtures/extensions/capneg_v0_2"
    POSITIVE_OUT = OUT / "positive_cases.json"
    NEGATIVE_OUT = OUT / "negative_cases.json"
    VECTORS_OUT = OUT / "cross_language_vectors.json"
    PROJECTION_OUT = ROOT / "fixtures/extensions/object_resync/state_projection_v2"
    PROJECTION_POSITIVE_OUT = PROJECTION_OUT / "positive_cases.json"
    PROJECTION_NEGATIVE_OUT = PROJECTION_OUT / "negative_cases.json"
    PRIVATE_KEYS = ROOT / "fixtures/keys/TEST_private_keys.json"
    PUBLIC_KEYS = ROOT / "fixtures/keys/GT_public_keys.json"
    REASON_CODES = ROOT / "registry/capneg_reason_codes.json"
    ORACLE_EXPECTATIONS = OUT / "oracle_expectations.json"
    COMPOSITION_ORACLE = OUT / "composition_oracle.json"
    PRIVATE_KEY_MAP = _load(PRIVATE_KEYS)
    PUBLIC_KEY_MAP = _load(PUBLIC_KEYS)


PRIVATE_KEY_MAP = _load(PRIVATE_KEYS)
PUBLIC_KEY_MAP = _load(PUBLIC_KEYS)


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _signature(hash_value: str, signer: str) -> dict[str, str]:
    metadata = PRIVATE_KEY_MAP[signer]
    private_key = Ed25519PrivateKey.from_private_bytes(
        _b64decode(metadata["private_key_b64url"])
    )
    signature = private_key.sign(
        f"AICP1\0SIG\0{hash_value}".encode("utf-8")
    )
    return {
        "signer": signer,
        "kid": metadata["kid"],
        "object_type": "message",
        "object_hash": hash_value,
        "sig_b64url": _b64encode(signature),
    }


def _rehash(
    messages: list[dict[str, Any]],
    *,
    signed_message_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    signed_message_ids = signed_message_ids or set()
    previous: str | None = None
    for message in messages:
        body = message_body_without_hash_and_signatures(message)
        body.pop("prev_msg_hash", None)
        if previous is not None:
            body["prev_msg_hash"] = previous
        digest = message_hash_from_body(body)
        message.clear()
        message.update(body)
        message["message_hash"] = digest
        if message["message_id"] in signed_message_ids:
            message["signatures"] = [_signature(digest, message["sender"])]
        previous = digest
    return messages


def _new_message(
    *,
    session_id: str,
    contract_id: str,
    index: int,
    sender: str,
    message_type: str,
    payload: dict[str, Any],
    contract_ref: dict[str, str] | None = None,
) -> dict[str, Any]:
    message: dict[str, Any] = {
        "session_id": session_id,
        "message_id": f"m{index}",
        "timestamp": f"2026-07-01T00:00:{index:02d}Z",
        "sender": sender,
        "message_type": message_type,
        "contract_id": contract_id,
        "payload": payload,
    }
    if contract_ref is not None:
        message["contract_ref"] = contract_ref
    return message


def _canonical_composition(profiles: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "composition_version": COMPOSITION_VERSION,
        "profiles": sorted(copy.deepcopy(profiles), key=canonical_profile_ref_key),
    }


def _reviewed_composition_expectation(
    composition: dict[str, Any],
) -> dict[str, Any]:
    oracle = _load(COMPOSITION_ORACLE)
    matches = [
        entry.get("expected")
        for entry in oracle.get("cases", {}).values()
        if isinstance(entry, dict) and entry.get("input") == composition
    ]
    if len(matches) != 1 or not isinstance(matches[0], dict):
        raise ValueError(
            "composition must resolve exactly once in the reviewed composition oracle: "
            f"{composition}"
        )
    return copy.deepcopy(matches[0])


def _proposal_index(messages: list[dict[str, Any]], revision: int = 1) -> int:
    return next(
        index
        for index, message in enumerate(messages)
        if message["message_type"] == "CAPABILITIES_PROPOSE"
        and message["payload"]["proposal_revision"] == revision
    )


def _declaration_indices(messages: list[dict[str, Any]]) -> list[int]:
    return [
        index
        for index, message in enumerate(messages)
        if message["message_type"] == "CAPABILITIES_DECLARE"
    ]


def _accept_indices(messages: list[dict[str, Any]]) -> list[int]:
    return [
        index
        for index, message in enumerate(messages)
        if message["message_type"] == "CAPABILITIES_ACCEPT"
    ]


def _refresh_proposal_after_declarations(
    messages: list[dict[str, Any]], proposal_index: int
) -> None:
    _rehash(messages)
    latest: dict[str, dict[str, Any]] = {}
    for message in messages[:proposal_index]:
        if message["message_type"] == "CAPABILITIES_DECLARE":
            latest[message["payload"]["party_id"]] = message
    result = messages[proposal_index]["payload"]["negotiation_result"]
    result["declaration_bindings"] = [
        {
            "party_id": party,
            "capabilities_id": latest[party]["payload"]["capabilities_id"],
            "declaration_message_id": latest[party]["message_id"],
            "declaration_message_hash": latest[party]["message_hash"],
        }
        for party in result["participants"]
        if party in latest
    ]
    messages[proposal_index]["payload"]["negotiation_result_hash"] = object_hash(
        NEGOTIATION_HASH_DOMAIN, result
    )
    _rehash(messages)


def build_negotiation(
    profiles: list[dict[str, str]],
    *,
    case_id: str,
    include_acceptances: bool = True,
    signed_acceptances: bool | None = None,
    duplicate_acceptance: bool = False,
    include_contract: bool = False,
    include_projection: bool = False,
    required_by_party: dict[str, list[dict[str, str]]] | None = None,
) -> list[dict[str, Any]]:
    session_id = f"session-{case_id.lower()}"
    contract_id = f"contract-{case_id.lower()}"
    composition = _canonical_composition(profiles)
    resolved = _reviewed_composition_expectation(composition)
    if resolved["errors"]:
        raise ValueError(f"{case_id}: invalid base composition {resolved['errors']}")
    signed_acceptances = (
        AUTH in composition["profiles"]
        if signed_acceptances is None
        else signed_acceptances
    )
    selected_crypto = resolved["required_crypto_profiles"]
    selected_extensions = resolved["required_extensions"]
    selected_policies = resolved["required_policy_categories"]
    required_by_party = required_by_party or {}
    participants = [PARTY_A, PARTY_B]
    messages: list[dict[str, Any]] = []
    for party in participants:
        messages.append(
            _new_message(
                session_id=session_id,
                contract_id=contract_id,
                index=len(messages) + 1,
                sender=party,
                message_type="CAPABILITIES_DECLARE",
                payload={
                    "capneg_version": "0.2",
                    "capabilities_id": f"cap-{case_id.lower()}-{party[-1].lower()}-1",
                    "party_id": party,
                    "supported_crypto_profiles": selected_crypto,
                    "supported_privacy_modes": ["standard"],
                    "supported_aicp_profiles": copy.deepcopy(
                        composition["profiles"]
                    ),
                    "required_crypto_profiles": selected_crypto,
                    "required_aicp_profiles": sorted(
                        required_by_party.get(party, []),
                        key=canonical_profile_ref_key,
                    ),
                    "supported_extensions": selected_extensions,
                    "supported_policy_categories": selected_policies,
                    "bindings": ["BIND-HTTP-0.1"],
                    "limits": {"max_message_bytes": 1048576},
                },
            )
        )
    _rehash(messages)
    bindings = [
        {
            "party_id": message["payload"]["party_id"],
            "capabilities_id": message["payload"]["capabilities_id"],
            "declaration_message_id": message["message_id"],
            "declaration_message_hash": message["message_hash"],
        }
        for message in messages
    ]
    result = {
        "negotiation_id": f"neg-{case_id.lower()}-1",
        "proposal_revision": 1,
        "session_id": session_id,
        "contract_id": contract_id,
        "participants": participants,
        "declaration_bindings": bindings,
        "selected": {
            "crypto_profiles": selected_crypto,
            "privacy_mode": "standard",
            "profile_composition": composition,
            "profile_composition_hash": resolved["composition_hash"],
            "required_extensions": selected_extensions,
            "required_policy_categories": selected_policies,
            "binding": "BIND-HTTP-0.1",
            "limits": {"max_message_bytes": 1048576},
        },
    }
    proposal = _new_message(
        session_id=session_id,
        contract_id=contract_id,
        index=len(messages) + 1,
        sender=PARTY_A,
        message_type="CAPABILITIES_PROPOSE",
        payload={
            "capneg_version": "0.2",
            "proposal_revision": 1,
            "negotiation_result": result,
            "negotiation_result_hash": object_hash(
                NEGOTIATION_HASH_DOMAIN, result
            ),
        },
    )
    messages.append(proposal)
    _rehash(messages)
    if include_acceptances:
        acceptance_senders = (
            [PARTY_A, PARTY_A, PARTY_B]
            if duplicate_acceptance
            else participants
        )
        for party in acceptance_senders:
            messages.append(
                _new_message(
                    session_id=session_id,
                    contract_id=contract_id,
                    index=len(messages) + 1,
                    sender=party,
                    message_type="CAPABILITIES_ACCEPT",
                    payload={
                        "capneg_version": "0.2",
                        "negotiation_id": result["negotiation_id"],
                        "proposal_revision": 1,
                        "proposal_message_id": proposal["message_id"],
                        "proposal_message_hash": proposal["message_hash"],
                        "negotiation_result_hash": proposal["payload"][
                            "negotiation_result_hash"
                        ],
                        "accepted": True,
                    },
                )
            )
        signed_ids = (
            {message["message_id"] for message in messages if message["message_type"] == "CAPABILITIES_ACCEPT"}
            if signed_acceptances
            else set()
        )
        _rehash(messages, signed_message_ids=signed_ids)
    if include_contract:
        binding = {
            "capneg_version": "0.2",
            "negotiation_id": result["negotiation_id"],
            "negotiation_result_hash": proposal["payload"][
                "negotiation_result_hash"
            ],
            "profile_composition": composition,
            "profile_composition_hash": resolved["composition_hash"],
        }
        messages.append(
            _new_message(
                session_id=session_id,
                contract_id=contract_id,
                index=len(messages) + 1,
                sender=PARTY_A,
                message_type="CONTRACT_PROPOSE",
                contract_ref={
                    "branch_id": "main",
                    "base_version": "v1",
                    "head_version": "v1",
                },
                payload={
                    "contract": {
                        "contract_id": contract_id,
                        "goal": "activate accepted CAPNEG v0.2 composition",
                        "roles": participants,
                        "ext": {"capneg_v2": binding},
                    }
                },
            )
        )
        messages.append(
            _new_message(
                session_id=session_id,
                contract_id=contract_id,
                index=len(messages) + 1,
                sender=PARTY_B,
                message_type="CONTRACT_ACCEPT",
                contract_ref={
                    "branch_id": "main",
                    "base_version": "v1",
                    "head_version": "v1",
                },
                payload={"accepted": True},
            )
        )
        signed_ids = {
            message["message_id"]
            for message in messages
            if signed_acceptances
            and message["message_type"] == "CAPABILITIES_ACCEPT"
        }
        _rehash(messages, signed_message_ids=signed_ids)
    if include_projection:
        as_of = messages[-1]["message_hash"]
        active_extensions = sorted(
            set(selected_extensions) | {"EXT-OBJECT-RESYNC"}
        )
        state = {
            "projection_version": PROJECTION_VERSION,
            "session_id": session_id,
            "contract_id": contract_id,
            "as_of_message_hash": as_of,
            "session_status": "OPEN",
            "selected_aicp_profiles": composition["profiles"],
            "profile_composition_hash": resolved["composition_hash"],
            "accepted_negotiation_result_hash": proposal["payload"][
                "negotiation_result_hash"
            ],
            "active_contract_ref": {
                "branch_id": "main",
                "base_version": "v1",
                "head_version": "v1",
            },
            "active_extensions": active_extensions,
            "participant_refs": participants,
        }
        messages.append(
            _new_message(
                session_id=session_id,
                contract_id=contract_id,
                index=len(messages) + 1,
                sender=PARTY_B,
                message_type="STATE_SYNC_RESPONSE",
                payload={
                    "request_id": f"sync-{case_id.lower()}",
                    "session_state": state,
                    "session_state_hash": object_hash(
                        PROJECTION_OBJECT_TYPE, state
                    ),
                    "branch_heads": [
                        {
                            "branch_id": "main",
                            "head_version": "v1",
                            "message_hash": as_of,
                        }
                    ],
                    "active_head_version": "v1",
                },
            )
        )
        signed_ids = {
            message["message_id"]
            for message in messages
            if signed_acceptances
            and message["message_type"] == "CAPABILITIES_ACCEPT"
        }
        _rehash(messages, signed_message_ids=signed_ids)
    return messages


def append_rejection_and_revision(
    messages: list[dict[str, Any]],
    *,
    accept_revision: bool,
    revision: int = 2,
    wrong_supersession: bool = False,
) -> list[dict[str, Any]]:
    first_proposal = messages[_proposal_index(messages)]
    result = first_proposal["payload"]["negotiation_result"]
    messages.append(
        _new_message(
            session_id=result["session_id"],
            contract_id=result["contract_id"],
            index=len(messages) + 1,
            sender=PARTY_B,
            message_type="CAPABILITIES_REJECT",
            payload={
                "capneg_version": "0.2",
                "negotiation_id": result["negotiation_id"],
                "proposal_revision": 1,
                "proposal_message_id": first_proposal["message_id"],
                "proposal_message_hash": first_proposal["message_hash"],
                "negotiation_result_hash": first_proposal["payload"][
                    "negotiation_result_hash"
                ],
                "reason_code": "PROFILE_SET_UNSUPPORTED",
            },
        )
    )
    _rehash(messages)
    revised_result = copy.deepcopy(result)
    revised_result["proposal_revision"] = revision
    revision_message = _new_message(
        session_id=result["session_id"],
        contract_id=result["contract_id"],
        index=len(messages) + 1,
        sender=PARTY_A,
        message_type="CAPABILITIES_PROPOSE",
        payload={
            "capneg_version": "0.2",
            "proposal_revision": revision,
            "negotiation_result": revised_result,
            "negotiation_result_hash": object_hash(
                NEGOTIATION_HASH_DOMAIN, revised_result
            ),
            "supersedes_proposal_message_id": first_proposal["message_id"],
            "supersedes_proposal_message_hash": (
                "sha256:" + "A" * 43
                if wrong_supersession
                else first_proposal["message_hash"]
            ),
        },
    )
    messages.append(revision_message)
    _rehash(messages)
    if accept_revision:
        for party in (PARTY_A, PARTY_B):
            messages.append(
                _new_message(
                    session_id=result["session_id"],
                    contract_id=result["contract_id"],
                    index=len(messages) + 1,
                    sender=party,
                    message_type="CAPABILITIES_ACCEPT",
                    payload={
                        "capneg_version": "0.2",
                        "negotiation_id": result["negotiation_id"],
                        "proposal_revision": revision,
                        "proposal_message_id": revision_message["message_id"],
                        "proposal_message_hash": revision_message["message_hash"],
                        "negotiation_result_hash": revision_message["payload"][
                            "negotiation_result_hash"
                        ],
                        "accepted": True,
                    },
                )
            )
        _rehash(messages)
    return messages


def append_superseding_negotiation(
    messages: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    first = messages[_proposal_index(messages)]
    old_result = first["payload"]["negotiation_result"]
    new_result = copy.deepcopy(old_result)
    new_result["negotiation_id"] = old_result["negotiation_id"] + "-next"
    new_result["supersedes_negotiation_id"] = old_result["negotiation_id"]
    new_result["proposal_revision"] = 1
    proposal = _new_message(
        session_id=old_result["session_id"],
        contract_id=old_result["contract_id"],
        index=len(messages) + 1,
        sender=PARTY_B,
        message_type="CAPABILITIES_PROPOSE",
        payload={
            "capneg_version": "0.2",
            "proposal_revision": 1,
            "negotiation_result": new_result,
            "negotiation_result_hash": object_hash(
                NEGOTIATION_HASH_DOMAIN, new_result
            ),
        },
    )
    messages.append(proposal)
    _rehash(messages)
    for party in (PARTY_A, PARTY_B):
        messages.append(
            _new_message(
                session_id=old_result["session_id"],
                contract_id=old_result["contract_id"],
                index=len(messages) + 1,
                sender=party,
                message_type="CAPABILITIES_ACCEPT",
                payload={
                    "capneg_version": "0.2",
                    "negotiation_id": new_result["negotiation_id"],
                    "proposal_revision": 1,
                    "proposal_message_id": proposal["message_id"],
                    "proposal_message_hash": proposal["message_hash"],
                    "negotiation_result_hash": proposal["payload"][
                        "negotiation_result_hash"
                    ],
                    "accepted": True,
                },
            )
        )
    _rehash(messages)
    return messages


def append_new_negotiation(
    messages: list[dict[str, Any]],
    *,
    suffix: str,
    supersedes_negotiation_id: str | None,
    profiles: list[dict[str, str]] | None = None,
    acceptance_senders: tuple[str, ...] = (),
) -> dict[str, Any]:
    first = messages[_proposal_index(messages)]
    old_result = first["payload"]["negotiation_result"]
    new_result = copy.deepcopy(old_result)
    new_result["negotiation_id"] = old_result["negotiation_id"] + f"-{suffix}"
    new_result["proposal_revision"] = 1
    if supersedes_negotiation_id is None:
        new_result.pop("supersedes_negotiation_id", None)
    else:
        new_result["supersedes_negotiation_id"] = supersedes_negotiation_id
    if profiles is not None:
        composition = _canonical_composition(profiles)
        resolved = _reviewed_composition_expectation(composition)
        new_result["selected"].update(
            {
                "crypto_profiles": resolved["required_crypto_profiles"],
                "profile_composition": composition,
                "profile_composition_hash": resolved["composition_hash"],
                "required_extensions": resolved["required_extensions"],
                "required_policy_categories": resolved[
                    "required_policy_categories"
                ],
            }
        )
    proposal = _new_message(
        session_id=old_result["session_id"],
        contract_id=old_result["contract_id"],
        index=len(messages) + 1,
        sender=PARTY_B,
        message_type="CAPABILITIES_PROPOSE",
        payload={
            "capneg_version": "0.2",
            "proposal_revision": 1,
            "negotiation_result": new_result,
            "negotiation_result_hash": object_hash(
                NEGOTIATION_HASH_DOMAIN, new_result
            ),
        },
    )
    messages.append(proposal)
    _rehash_preserving_signatures(messages)
    for sender in acceptance_senders:
        append_decision(messages, sender=sender, proposal=proposal)
    return proposal


def _rehash_preserving_signatures(messages: list[dict[str, Any]]) -> None:
    signed_ids = {
        message["message_id"]
        for message in messages
        if isinstance(message.get("signatures"), list) and message["signatures"]
    }
    _rehash(messages, signed_message_ids=signed_ids)


def append_decision(
    messages: list[dict[str, Any]],
    *,
    sender: str,
    message_type: str = "CAPABILITIES_ACCEPT",
    proposal: dict[str, Any] | None = None,
    payload_updates: dict[str, Any] | None = None,
) -> dict[str, Any]:
    proposal = proposal or next(
        message
        for message in reversed(messages)
        if message["message_type"] == "CAPABILITIES_PROPOSE"
    )
    result = proposal["payload"]["negotiation_result"]
    payload: dict[str, Any] = {
        "capneg_version": "0.2",
        "negotiation_id": result["negotiation_id"],
        "proposal_revision": proposal["payload"]["proposal_revision"],
        "proposal_message_id": proposal["message_id"],
        "proposal_message_hash": proposal["message_hash"],
        "negotiation_result_hash": proposal["payload"]["negotiation_result_hash"],
    }
    if message_type == "CAPABILITIES_ACCEPT":
        payload["accepted"] = True
    else:
        payload["reason_code"] = "PROFILE_SET_UNSUPPORTED"
    payload.update(payload_updates or {})
    message = _new_message(
        session_id=proposal["session_id"],
        contract_id=proposal["contract_id"],
        index=len(messages) + 1,
        sender=sender,
        message_type=message_type,
        payload=payload,
    )
    messages.append(message)
    _rehash_preserving_signatures(messages)
    return messages[-1]


def append_declaration_supersession(
    messages: list[dict[str, Any]], party: str
) -> dict[str, Any]:
    latest = next(
        message
        for message in reversed(messages)
        if message.get("message_type") == "CAPABILITIES_DECLARE"
        and message.get("payload", {}).get("party_id") == party
    )
    declaration = copy.deepcopy(latest)
    declaration["message_id"] = f"m{len(messages) + 1}"
    declaration["timestamp"] = f"2026-07-01T00:00:{len(messages) + 1:02d}Z"
    declaration["payload"]["capabilities_id"] = (
        latest["payload"]["capabilities_id"] + "-next"
    )
    declaration["payload"]["supersedes_capabilities_id"] = latest["payload"][
        "capabilities_id"
    ]
    messages.append(declaration)
    _rehash_preserving_signatures(messages)
    return messages[-1]


def append_projection(
    messages: list[dict[str, Any]],
    *,
    as_of_message_hash: str,
    result: dict[str, Any],
    case_id: str,
    branch_head_hash: str | None = None,
) -> dict[str, Any]:
    selected = result["selected"]
    state = {
        "projection_version": PROJECTION_VERSION,
        "session_id": messages[0]["session_id"],
        "contract_id": messages[0]["contract_id"],
        "as_of_message_hash": as_of_message_hash,
        "session_status": "OPEN",
        "selected_aicp_profiles": copy.deepcopy(
            selected["profile_composition"]["profiles"]
        ),
        "profile_composition_hash": selected["profile_composition_hash"],
        "accepted_negotiation_result_hash": object_hash(
            NEGOTIATION_HASH_DOMAIN, result
        ),
        "active_extensions": sorted(
            set(selected["required_extensions"]) | {"EXT-OBJECT-RESYNC"}
        ),
        "participant_refs": copy.deepcopy(result["participants"]),
    }
    message = _new_message(
        session_id=messages[0]["session_id"],
        contract_id=messages[0]["contract_id"],
        index=len(messages) + 1,
        sender=PARTY_B,
        message_type="STATE_SYNC_RESPONSE",
        payload={
            "request_id": f"sync-{case_id.lower()}",
            "session_state": state,
            "session_state_hash": object_hash(PROJECTION_OBJECT_TYPE, state),
            "branch_heads": [
                {
                    "branch_id": "main",
                    "head_version": "v1",
                    "message_hash": branch_head_hash or as_of_message_hash,
                }
            ],
            "active_head_version": "v1",
        },
    )
    messages.append(message)
    _rehash_preserving_signatures(messages)
    return messages[-1]


def finalize_case(
    case_id: str,
    description: str,
    messages: list[dict[str, Any]],
    *,
    expect_pass: bool,
    required_error: str | None = None,
    invalid_messages: dict[int, str] | None = None,
    require_accepted: bool = False,
    execution_metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    invalid_messages = invalid_messages or {}
    oracle = _load(ORACLE_EXPECTATIONS)
    expectation = oracle.get("cases", {}).get(case_id)
    if not isinstance(expectation, dict):
        raise ValueError(
            f"{case_id}: missing reviewed expectation in "
            f"{ORACLE_EXPECTATIONS.relative_to(ROOT)}"
        )
    observations = copy.deepcopy(expectation["expected_error_observations"])
    final_state = copy.deepcopy(expectation["expected_final_state"])
    observed_codes = {item["code"] for item in observations}
    if expect_pass and observations:
        raise ValueError(f"{case_id}: positive case has oracle errors {observations}")
    if not expect_pass and not observations:
        raise ValueError(f"{case_id}: negative case has no oracle error")
    if required_error is not None and required_error not in observed_codes:
        raise ValueError(
            f"{case_id}: required error {required_error} absent from reviewed oracle"
        )
    result = {
        "id": case_id,
        "description": description,
        "expect_pass": expect_pass,
        "messages": messages,
        "invalid_message_indices": sorted(invalid_messages),
        "requires_jsonschema": bool(expectation.get("requires_jsonschema", False)),
        "require_accepted": require_accepted,
        "oracle_case_id": case_id,
    }
    if execution_metadata:
        result["execution_metadata"] = copy.deepcopy(execution_metadata)
    return result


def _semantic_mutation_case(
    case_id: str,
    description: str,
    profiles: list[dict[str, str]],
    mutate: Callable[[list[dict[str, Any]]], None],
    required_error: str,
    *,
    invalid_messages: dict[int, str] | None = None,
    preserve_result_hash: bool = False,
) -> dict[str, Any]:
    messages = build_negotiation(
        profiles, case_id=case_id, include_acceptances=False
    )
    mutate(messages)
    if not preserve_result_hash:
        proposal = messages[_proposal_index(messages)]["payload"]
        proposal["negotiation_result_hash"] = object_hash(
            NEGOTIATION_HASH_DOMAIN, proposal["negotiation_result"]
        )
    _rehash(messages)
    return finalize_case(
        case_id,
        description,
        messages,
        expect_pass=False,
        required_error=required_error,
        invalid_messages=invalid_messages,
    )


def positive_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []
    definitions = [
        ("P01", "singleton AICP-BASE@0.1", [BASE], {}),
        (
            "P02",
            "Mediated Blocking plus Resumable Sessions",
            [MEDIATED, RESUMABLE],
            {},
        ),
        (
            "P03",
            "Authenticated Base plus Mediated Blocking with signed accepts",
            [AUTH, MEDIATED],
            {},
        ),
        (
            "P04",
            "Delegated Identity plus Workflow Orchestration Delegation",
            [DELEGATED, WORKFLOW],
            {},
        ),
        (
            "P05",
            "Agent Media plus Bazaar Reception",
            [AGENT_MEDIA, BAZAAR],
            {},
        ),
        (
            "P07",
            "exact duplicate acceptance replay",
            [MEDIATED, RESUMABLE],
            {"duplicate_acceptance": True},
        ),
        (
            "P08",
            "contract binding to accepted composition",
            [MEDIATED, RESUMABLE],
            {"include_contract": True},
        ),
        (
            "P09",
            "session-state projection v2",
            [MEDIATED, RESUMABLE],
            {"include_contract": True, "include_projection": True},
        ),
        (
            "P10",
            "optional valid signatures for non-authenticated composition",
            [MEDIATED, RESUMABLE],
            {"signed_acceptances": True},
        ),
    ]
    for case_id, description, profiles, options in definitions:
        messages = build_negotiation(
            profiles, case_id=case_id, **options
        )
        cases.append(
            finalize_case(
                case_id, description, messages, expect_pass=True
            )
        )

    revision_messages = build_negotiation(
        [MEDIATED, RESUMABLE],
        case_id="P06",
        include_acceptances=False,
    )
    append_rejection_and_revision(
        revision_messages, accept_revision=True
    )
    cases.append(
        finalize_case(
            "P06",
            "reject first proposal then accept exact revision",
            revision_messages,
            expect_pass=True,
        )
    )
    superseding = build_negotiation(
        [MEDIATED, RESUMABLE], case_id="P11"
    )
    append_superseding_negotiation(superseding)
    cases.append(
        finalize_case(
            "P11",
            "new negotiation explicitly supersedes accepted negotiation",
            superseding,
            expect_pass=True,
        )
    )

    participant_crypto = build_negotiation(
        [BASE], case_id="P12", include_acceptances=False
    )
    for index, declaration in enumerate(participant_crypto[:2]):
        declaration["payload"]["supported_crypto_profiles"] = [
            "aicp.crypto.ed25519.v1"
        ]
        declaration["payload"]["required_crypto_profiles"] = (
            ["aicp.crypto.ed25519.v1"] if index == 0 else []
        )
    participant_crypto[2]["payload"]["negotiation_result"]["selected"][
        "crypto_profiles"
    ] = ["aicp.crypto.ed25519.v1"]
    _refresh_proposal_after_declarations(participant_crypto, 2)
    append_decision(participant_crypto, sender=PARTY_A)
    append_decision(participant_crypto, sender=PARTY_B)
    cases.append(
        finalize_case(
            "P12",
            "participant-required crypto is selected without product-profile requirement",
            participant_crypto,
            expect_pass=True,
        )
    )

    unrelated = build_negotiation(
        [BASE], case_id="P13", include_acceptances=False
    )
    unrelated.append(
        _new_message(
            session_id=unrelated[0]["session_id"],
            contract_id=unrelated[0]["contract_id"],
            index=4,
            sender=PARTY_C,
            message_type="CAPABILITIES_DECLARE",
            payload={
                **copy.deepcopy(unrelated[0]["payload"]),
                "capabilities_id": "cap-p13-u-1",
                "party_id": PARTY_C,
            },
        )
    )
    _rehash(unrelated)
    append_decision(unrelated, sender=PARTY_A, proposal=unrelated[2])
    append_decision(unrelated, sender=PARTY_B, proposal=unrelated[2])
    cases.append(
        finalize_case(
            "P13",
            "unrelated participant declaration does not stale a proposal",
            unrelated,
            expect_pass=True,
        )
    )

    duplicate_reject = build_negotiation(
        [BASE], case_id="P14", include_acceptances=False
    )
    append_decision(
        duplicate_reject,
        sender=PARTY_B,
        message_type="CAPABILITIES_REJECT",
    )
    append_decision(
        duplicate_reject,
        sender=PARTY_B,
        message_type="CAPABILITIES_REJECT",
    )
    cases.append(
        finalize_case(
            "P14",
            "exact duplicate rejection replay is idempotent",
            duplicate_reject,
            expect_pass=True,
        )
    )

    projection_at_accept = build_negotiation(
        [MEDIATED, RESUMABLE],
        case_id="P15",
        include_projection=True,
    )
    cases.append(
        finalize_case(
            "P15",
            "projection binds the exact final acceptance",
            projection_at_accept,
            expect_pass=True,
        )
    )

    projection_before_supersession = build_negotiation(
        [MEDIATED, RESUMABLE], case_id="P16"
    )
    old_proposal = projection_before_supersession[_proposal_index(
        projection_before_supersession
    )]
    old_as_of = projection_before_supersession[-1]["message_hash"]
    append_superseding_negotiation(projection_before_supersession)
    append_projection(
        projection_before_supersession,
        as_of_message_hash=old_as_of,
        result=old_proposal["payload"]["negotiation_result"],
        case_id="P16",
    )
    cases.append(
        finalize_case(
            "P16",
            "projection before later supersession uses the old accepted prefix",
            projection_before_supersession,
            expect_pass=True,
        )
    )

    projection_after_supersession = build_negotiation(
        [MEDIATED, RESUMABLE], case_id="P17"
    )
    append_superseding_negotiation(projection_after_supersession)
    new_proposal = next(
        message
        for message in reversed(projection_after_supersession)
        if message["message_type"] == "CAPABILITIES_PROPOSE"
    )
    append_projection(
        projection_after_supersession,
        as_of_message_hash=projection_after_supersession[-1]["message_hash"],
        result=new_proposal["payload"]["negotiation_result"],
        case_id="P17",
    )
    cases.append(
        finalize_case(
            "P17",
            "projection after accepted supersession uses the successor prefix",
            projection_after_supersession,
            expect_pass=True,
        )
    )

    successor_proposed = build_negotiation(
        [MEDIATED, RESUMABLE], case_id="P18"
    )
    root_id = successor_proposed[2]["payload"]["negotiation_result"][
        "negotiation_id"
    ]
    append_new_negotiation(
        successor_proposed,
        suffix="successor",
        supersedes_negotiation_id=root_id,
    )
    cases.append(
        finalize_case(
            "P18",
            "explicit successor proposal leaves the accepted predecessor current",
            successor_proposed,
            expect_pass=True,
        )
    )

    rejected_successor = build_negotiation(
        [MEDIATED, RESUMABLE], case_id="P19"
    )
    root_id = rejected_successor[2]["payload"]["negotiation_result"][
        "negotiation_id"
    ]
    successor = append_new_negotiation(
        rejected_successor,
        suffix="successor",
        supersedes_negotiation_id=root_id,
    )
    append_decision(
        rejected_successor,
        sender=PARTY_B,
        message_type="CAPABILITIES_REJECT",
        proposal=successor,
    )
    cases.append(
        finalize_case(
            "P19",
            "rejected successor leaves the predecessor accepted",
            rejected_successor,
            expect_pass=True,
        )
    )

    replayed_successor = build_negotiation(
        [MEDIATED, RESUMABLE], case_id="P20"
    )
    root_id = replayed_successor[2]["payload"]["negotiation_result"][
        "negotiation_id"
    ]
    successor = append_new_negotiation(
        replayed_successor,
        suffix="successor",
        supersedes_negotiation_id=root_id,
        acceptance_senders=(PARTY_A, PARTY_B),
    )
    append_decision(replayed_successor, sender=PARTY_B, proposal=successor)
    append_decision(replayed_successor, sender=PARTY_A, proposal=successor)
    cases.append(
        finalize_case(
            "P20",
            "accepted successor decisions replay idempotently in reverse order",
            replayed_successor,
            expect_pass=True,
        )
    )
    return sorted(cases, key=lambda case: int(case["id"][1:]))


def negative_cases() -> list[dict[str, Any]]:
    cases: list[dict[str, Any]] = []

    def proposal(messages: list[dict[str, Any]]) -> dict[str, Any]:
        return messages[_proposal_index(messages)]["payload"]

    cases.append(
        _semantic_mutation_case(
            "N01",
            "empty profile set",
            [BASE],
            lambda messages: proposal(messages)["negotiation_result"]["selected"][
                "profile_composition"
            ].update(profiles=[]),
            "PROFILE_COMPOSITION_EMPTY",
            invalid_messages={2: "PROFILE_COMPOSITION_EMPTY"},
        )
    )
    cases.append(
        _semantic_mutation_case(
            "N02",
            "duplicate profile",
            [MEDIATED, RESUMABLE],
            lambda messages: proposal(messages)["negotiation_result"]["selected"][
                "profile_composition"
            ]["profiles"].append(copy.deepcopy(MEDIATED)),
            "PROFILE_DUPLICATE",
            invalid_messages={2: "PROFILE_DUPLICATE"},
        )
    )
    cases.append(
        _semantic_mutation_case(
            "N03",
            "non-canonical profile order",
            [MEDIATED, RESUMABLE],
            lambda messages: proposal(messages)["negotiation_result"]["selected"][
                "profile_composition"
            ]["profiles"].reverse(),
            "PROFILE_ORDER_NON_CANONICAL",
        )
    )
    cases.append(
        _semantic_mutation_case(
            "N04",
            "unknown profile",
            [BASE],
            lambda messages: proposal(messages)["negotiation_result"]["selected"][
                "profile_composition"
            ].update(profiles=[ref("AICP-UNKNOWN")]),
            "PROFILE_UNKNOWN",
        )
    )

    def replace_composition(
        messages: list[dict[str, Any]], profiles: list[dict[str, str]]
    ) -> None:
        proposal(messages)["negotiation_result"]["selected"][
            "profile_composition"
        ] = {
            "composition_version": COMPOSITION_VERSION,
            "profiles": sorted(copy.deepcopy(profiles), key=canonical_profile_ref_key),
        }

    cases.append(
        _semantic_mutation_case(
            "N05",
            "same profile ID with multiple versions",
            [BASE],
            lambda messages: replace_composition(messages, [BASE, BASE_V02]),
            "PROFILE_FAMILY_VERSION_CONFLICT",
        )
    )
    cases.append(
        _semantic_mutation_case(
            "N06",
            "Core 0.1 profile plus Base 0.2",
            [MEDIATED],
            lambda messages: replace_composition(messages, [BASE_V02, MEDIATED]),
            "PROFILE_CORE_VERSION_CONFLICT",
        )
    )
    cases.append(
        _semantic_mutation_case(
            "N07",
            "Base 0.2 singleton unsupported by CAPNEG v0.2",
            [BASE],
            lambda messages: replace_composition(messages, [BASE_V02]),
            "CAPNEG_CORE_FAMILY_UNSUPPORTED",
        )
    )
    for case_id, description, base_profiles, replacement in (
        (
            "N08",
            "Base plus stricter Core 0.1 profile redundancy",
            [MEDIATED],
            [BASE, MEDIATED],
        ),
        (
            "N09",
            "Mediated Blocking plus Mediated Blocking Ops redundancy",
            [MEDIATED_OPS],
            [MEDIATED, MEDIATED_OPS],
        ),
        (
            "N10",
            "Resumable Sessions plus Execution Interop redundancy",
            [EXECUTION],
            [EXECUTION, RESUMABLE],
        ),
    ):
        cases.append(
            _semantic_mutation_case(
                case_id,
                description,
                base_profiles,
                lambda messages, replacement=replacement: replace_composition(
                    messages, replacement
                ),
                "PROFILE_COMPOSITION_REDUNDANT",
            )
        )
    cases.append(
        _semantic_mutation_case(
            "N11",
            "multiple exclusive policy-semantic profiles",
            [POLICY_ABAC],
            lambda messages: replace_composition(
                messages, [POLICY_ABAC, POLICY_LLM]
            ),
            "PROFILE_COMPOSITION_EXCLUSIVE_CONFLICT",
        )
    )

    unsupported = build_negotiation(
        [MEDIATED, RESUMABLE],
        case_id="N12",
        include_acceptances=False,
    )
    unsupported[1]["payload"]["supported_aicp_profiles"] = [MEDIATED]
    _refresh_proposal_after_declarations(unsupported, 2)
    cases.append(
        finalize_case(
            "N12",
            "selected profile unsupported by one participant",
            unsupported,
            expect_pass=False,
            required_error="PROFILE_SET_UNSUPPORTED",
        )
    )
    required_missing = build_negotiation(
        [MEDIATED], case_id="N13", include_acceptances=False
    )
    required_missing[1]["payload"]["supported_aicp_profiles"] = sorted(
        [MEDIATED, RESUMABLE], key=canonical_profile_ref_key
    )
    required_missing[1]["payload"]["required_aicp_profiles"] = [RESUMABLE]
    _refresh_proposal_after_declarations(required_missing, 2)
    cases.append(
        finalize_case(
            "N13",
            "required participant profile omitted",
            required_missing,
            expect_pass=False,
            required_error="REQUIRED_PROFILE_MISSING",
        )
    )
    cases.append(
        _semantic_mutation_case(
            "N14",
            "required extension omitted",
            [MEDIATED],
            lambda messages: proposal(messages)["negotiation_result"]["selected"].update(
                required_extensions=[]
            ),
            "PROFILE_REQUIREMENTS_MISMATCH",
        )
    )
    for case_id, description in (
        ("N15", "required crypto profile omitted"),
        ("N17", "Authenticated Base without Ed25519 selection"),
    ):
        cases.append(
            _semantic_mutation_case(
                case_id,
                description,
                [AUTH],
                lambda messages: proposal(messages)["negotiation_result"]["selected"].update(
                    crypto_profiles=[]
                ),
                "PROFILE_REQUIREMENTS_MISMATCH",
            )
        )
    cases.append(
        _semantic_mutation_case(
            "N16",
            "required policy category omitted",
            [BAZAAR],
            lambda messages: proposal(messages)["negotiation_result"]["selected"].update(
                required_policy_categories=[]
            ),
            "PROFILE_REQUIREMENTS_MISMATCH",
        )
    )
    crypto_unsupported = build_negotiation(
        [AUTH], case_id="N18", include_acceptances=False
    )
    crypto_unsupported[1]["payload"]["supported_crypto_profiles"] = []
    crypto_unsupported[1]["payload"]["required_crypto_profiles"] = []
    _refresh_proposal_after_declarations(crypto_unsupported, 2)
    cases.append(
        finalize_case(
            "N18",
            "Authenticated Base unsupported by participant crypto declaration",
            crypto_unsupported,
            expect_pass=False,
            required_error="PROFILE_REQUIREMENTS_MISMATCH",
        )
    )

    unsigned_auth = build_negotiation([AUTH], case_id="N19")
    unsigned_auth[-1].pop("signatures", None)
    cases.append(
        finalize_case(
            "N19",
            "unsigned Authenticated Base acceptance",
            unsigned_auth,
            expect_pass=False,
            required_error="AUTHENTICATED_ACCEPTANCE_SIGNATURE_REQUIRED",
        )
    )
    invalid_auth = build_negotiation([AUTH], case_id="N20")
    invalid_auth[-1]["signatures"][0]["sig_b64url"] = "A" * 86
    cases.append(
        finalize_case(
            "N20",
            "invalid Authenticated Base acceptance signature",
            invalid_auth,
            expect_pass=False,
            required_error="ACCEPTANCE_SIGNATURE_INVALID",
        )
    )
    cases.append(
        _semantic_mutation_case(
            "N21",
            "composition hash mismatch",
            [MEDIATED, RESUMABLE],
            lambda messages: proposal(messages)["negotiation_result"]["selected"].update(
                profile_composition_hash="sha256:" + "A" * 43
            ),
            "PROFILE_COMPOSITION_HASH_MISMATCH",
        )
    )
    cases.append(
        _semantic_mutation_case(
            "N22",
            "negotiation-result hash mismatch",
            [MEDIATED, RESUMABLE],
            lambda messages: proposal(messages).update(
                negotiation_result_hash="sha256:" + "A" * 43
            ),
            "NEGOTIATION_RESULT_HASH_MISMATCH",
            preserve_result_hash=True,
        )
    )

    party_mismatch = build_negotiation(
        [BASE], case_id="N23", include_acceptances=False
    )[:1]
    party_mismatch[0]["payload"]["party_id"] = PARTY_B
    _rehash(party_mismatch)
    cases.append(
        finalize_case(
            "N23",
            "declaration party differs from sender",
            party_mismatch,
            expect_pass=False,
            required_error="DECLARATION_PARTY_SENDER_MISMATCH",
        )
    )
    duplicate_decl = build_negotiation(
        [BASE], case_id="N24", include_acceptances=False
    )[:1]
    duplicate = copy.deepcopy(duplicate_decl[0])
    duplicate["message_id"] = "m2"
    duplicate["timestamp"] = "2026-07-01T00:00:02Z"
    duplicate["payload"]["capabilities_id"] = "cap-n24-a-2"
    duplicate_decl.append(duplicate)
    _rehash(duplicate_decl)
    cases.append(
        finalize_case(
            "N24",
            "duplicate party declaration",
            duplicate_decl,
            expect_pass=False,
            required_error="DUPLICATE_PARTY_DECLARATION",
        )
    )

    stale = build_negotiation(
        [BASE], case_id="N25", include_acceptances=False
    )
    superseding = copy.deepcopy(stale[0])
    superseding["message_id"] = "m3"
    superseding["timestamp"] = "2026-07-01T00:00:03Z"
    superseding["payload"]["capabilities_id"] = "cap-n25-a-2"
    superseding["payload"]["supersedes_capabilities_id"] = stale[0]["payload"][
        "capabilities_id"
    ]
    stale.insert(2, superseding)
    stale[3]["message_id"] = "m4"
    stale[3]["timestamp"] = "2026-07-01T00:00:04Z"
    _rehash(stale)
    stale[3]["payload"]["negotiation_result"]["declaration_bindings"][1][
        "declaration_message_hash"
    ] = stale[1]["message_hash"]
    stale[3]["payload"]["negotiation_result_hash"] = object_hash(
        NEGOTIATION_HASH_DOMAIN,
        stale[3]["payload"]["negotiation_result"],
    )
    _rehash(stale)
    cases.append(
        finalize_case(
            "N25",
            "stale declaration used by proposal",
            stale,
            expect_pass=False,
            required_error="STALE_CAPABILITIES_DECLARATION",
        )
    )
    invalid_supersession = copy.deepcopy(duplicate_decl)
    invalid_supersession[1]["payload"][
        "supersedes_capabilities_id"
    ] = "cap-not-latest"
    _rehash(invalid_supersession)
    cases.append(
        finalize_case(
            "N26",
            "invalid declaration supersession",
            invalid_supersession,
            expect_pass=False,
            required_error="INVALID_DECLARATION_SUPERSESSION",
        )
    )
    cases.append(
        _semantic_mutation_case(
            "N27",
            "missing declaration binding",
            [BASE],
            lambda messages: proposal(messages)["negotiation_result"][
                "declaration_bindings"
            ].pop(),
            "MISSING_DECLARATION_BINDING",
            invalid_messages={2: "MISSING_DECLARATION_BINDING"},
        )
    )
    cases.append(
        _semantic_mutation_case(
            "N28",
            "declaration binding hash mismatch",
            [BASE],
            lambda messages: proposal(messages)["negotiation_result"][
                "declaration_bindings"
            ][0].update(declaration_message_hash="sha256:" + "A" * 43),
            "STALE_CAPABILITIES_DECLARATION",
        )
    )
    cases.append(
        _semantic_mutation_case(
            "N29",
            "proposal participant set differs from bindings",
            [BASE],
            lambda messages: proposal(messages)["negotiation_result"].update(
                participants=[PARTY_A, PARTY_B, PARTY_C]
            ),
            "DECLARATION_BINDING_SET_MISMATCH",
        )
    )

    skipped_revision = build_negotiation(
        [BASE], case_id="N30", include_acceptances=False
    )
    append_rejection_and_revision(
        skipped_revision, accept_revision=False, revision=3
    )
    cases.append(
        finalize_case(
            "N30",
            "proposal revision skips a number",
            skipped_revision,
            expect_pass=False,
            required_error="PROPOSAL_REVISION_INVALID",
        )
    )
    wrong_revision_binding = build_negotiation(
        [BASE], case_id="N31", include_acceptances=False
    )
    append_rejection_and_revision(
        wrong_revision_binding,
        accept_revision=False,
        wrong_supersession=True,
    )
    cases.append(
        finalize_case(
            "N31",
            "revision does not bind prior proposal",
            wrong_revision_binding,
            expect_pass=False,
            required_error="PROPOSAL_SUPERSESSION_INVALID",
        )
    )

    unknown_accept = build_negotiation(
        [BASE], case_id="N32", include_acceptances=False
    )[:2]
    unknown_accept.append(
        _new_message(
            session_id=unknown_accept[0]["session_id"],
            contract_id=unknown_accept[0]["contract_id"],
            index=3,
            sender=PARTY_A,
            message_type="CAPABILITIES_ACCEPT",
            payload={
                "capneg_version": "0.2",
                "negotiation_id": "neg-unknown",
                "proposal_revision": 1,
                "proposal_message_id": "missing",
                "proposal_message_hash": "sha256:" + "A" * 43,
                "negotiation_result_hash": "sha256:" + "B" * 43,
                "accepted": True,
            },
        )
    )
    _rehash(unknown_accept)
    cases.append(
        finalize_case(
            "N32",
            "accept unknown proposal",
            unknown_accept,
            expect_pass=False,
            required_error="UNKNOWN_PROPOSAL",
        )
    )
    future_accept = build_negotiation(
        [BASE], case_id="N33", include_acceptances=True
    )
    future_accept = future_accept[:4]
    future_accept[-1]["payload"]["proposal_revision"] = 2
    _rehash(future_accept)
    cases.append(
        finalize_case(
            "N33",
            "accept future proposal",
            future_accept,
            expect_pass=False,
            required_error="FUTURE_PROPOSAL",
        )
    )
    old_revision = build_negotiation(
        [BASE], case_id="N34", include_acceptances=False
    )
    append_rejection_and_revision(old_revision, accept_revision=False)
    first = old_revision[_proposal_index(old_revision, 1)]
    old_revision.append(
        _new_message(
            session_id=first["session_id"],
            contract_id=first["contract_id"],
            index=len(old_revision) + 1,
            sender=PARTY_A,
            message_type="CAPABILITIES_ACCEPT",
            payload={
                "capneg_version": "0.2",
                "negotiation_id": first["payload"]["negotiation_result"][
                    "negotiation_id"
                ],
                "proposal_revision": 1,
                "proposal_message_id": first["message_id"],
                "proposal_message_hash": first["message_hash"],
                "negotiation_result_hash": first["payload"][
                    "negotiation_result_hash"
                ],
                "accepted": True,
            },
        )
    )
    _rehash(old_revision)
    cases.append(
        finalize_case(
            "N34",
            "accept superseded proposal revision",
            old_revision,
            expect_pass=False,
            required_error="SUPERSEDED_PROPOSAL",
        )
    )
    acceptance_hash = build_negotiation(
        [BASE], case_id="N35"
    )[:4]
    acceptance_hash[-1]["payload"][
        "negotiation_result_hash"
    ] = "sha256:" + "A" * 43
    _rehash(acceptance_hash)
    cases.append(
        finalize_case(
            "N35",
            "acceptance result hash mismatch",
            acceptance_hash,
            expect_pass=False,
            required_error="ACCEPTANCE_RESULT_HASH_MISMATCH",
        )
    )

    duplicate_count = build_negotiation(
        [BASE],
        case_id="N36",
        duplicate_acceptance=True,
    )[:-1]
    cases.append(
        finalize_case(
            "N36",
            "duplicate participant acceptance must not count twice",
            duplicate_count,
            expect_pass=False,
            required_error="PARTICIPANT_ACCEPTANCE_INCOMPLETE",
            require_accepted=True,
        )
    )
    partial = build_negotiation(
        [BASE],
        case_id="N37",
        include_contract=True,
    )
    del partial[4]
    for index, message in enumerate(partial, 1):
        message["message_id"] = f"m{index}"
        message["timestamp"] = f"2026-07-01T00:00:{index:02d}Z"
    _rehash(partial)
    cases.append(
        finalize_case(
            "N37",
            "partial participant acceptance presented as accepted",
            partial,
            expect_pass=False,
            required_error="CONTRACT_BINDING_ACCEPTANCE_INCOMPLETE",
        )
    )
    conflict = build_negotiation(
        [BASE], case_id="N38", include_acceptances=False
    )
    first = conflict[_proposal_index(conflict)]
    conflict.append(
        _new_message(
            session_id=first["session_id"],
            contract_id=first["contract_id"],
            index=4,
            sender=PARTY_B,
            message_type="CAPABILITIES_REJECT",
            payload={
                "capneg_version": "0.2",
                "negotiation_id": first["payload"]["negotiation_result"][
                    "negotiation_id"
                ],
                "proposal_revision": 1,
                "proposal_message_id": first["message_id"],
                "proposal_message_hash": first["message_hash"],
                "negotiation_result_hash": first["payload"][
                    "negotiation_result_hash"
                ],
                "reason_code": "PROFILE_SET_UNSUPPORTED",
            },
        )
    )
    _rehash(conflict)
    conflict.append(
        _new_message(
            session_id=first["session_id"],
            contract_id=first["contract_id"],
            index=5,
            sender=PARTY_B,
            message_type="CAPABILITIES_ACCEPT",
            payload={
                "capneg_version": "0.2",
                "negotiation_id": first["payload"]["negotiation_result"][
                    "negotiation_id"
                ],
                "proposal_revision": 1,
                "proposal_message_id": first["message_id"],
                "proposal_message_hash": first["message_hash"],
                "negotiation_result_hash": first["payload"][
                    "negotiation_result_hash"
                ],
                "accepted": True,
            },
        )
    )
    _rehash(conflict)
    cases.append(
        finalize_case(
            "N38",
            "same participant both rejects and accepts",
            conflict,
            expect_pass=False,
            required_error="PARTICIPANT_DECISION_CONFLICT",
        )
    )

    immutable = build_negotiation([BASE], case_id="N39")
    first = immutable[_proposal_index(immutable)]
    revised_result = copy.deepcopy(first["payload"]["negotiation_result"])
    revised_result["proposal_revision"] = 2
    immutable.append(
        _new_message(
            session_id=first["session_id"],
            contract_id=first["contract_id"],
            index=len(immutable) + 1,
            sender=PARTY_A,
            message_type="CAPABILITIES_PROPOSE",
            payload={
                "capneg_version": "0.2",
                "proposal_revision": 2,
                "negotiation_result": revised_result,
                "negotiation_result_hash": object_hash(
                    NEGOTIATION_HASH_DOMAIN, revised_result
                ),
                "supersedes_proposal_message_id": first["message_id"],
                "supersedes_proposal_message_hash": first["message_hash"],
            },
        )
    )
    _rehash(immutable)
    cases.append(
        finalize_case(
            "N39",
            "revision proposed after full acceptance under same negotiation ID",
            immutable,
            expect_pass=False,
            required_error="ACCEPTED_NEGOTIATION_IMMUTABLE",
        )
    )
    mutation = copy.deepcopy(immutable)
    mutation[-1]["payload"]["negotiation_result"]["selected"][
        "profile_composition"
    ] = _canonical_composition([MEDIATED])
    mutation[-1]["payload"]["negotiation_result"]["selected"][
        "profile_composition_hash"
    ] = object_hash(
        COMPOSITION_HASH_DOMAIN, _canonical_composition([MEDIATED])
    )
    mutation[-1]["payload"]["negotiation_result_hash"] = object_hash(
        NEGOTIATION_HASH_DOMAIN,
        mutation[-1]["payload"]["negotiation_result"],
    )
    _rehash(mutation)
    cases.append(
        finalize_case(
            "N40",
            "silent mutation of accepted composition",
            mutation,
            expect_pass=False,
            required_error="ACCEPTED_NEGOTIATION_IMMUTABLE",
        )
    )

    before_accept = build_negotiation(
        [MEDIATED, RESUMABLE], case_id="N41", include_contract=True
    )
    del before_accept[4]
    for index, message in enumerate(before_accept, 1):
        message["message_id"] = f"m{index}"
        message["timestamp"] = f"2026-07-01T00:00:{index:02d}Z"
    _rehash(before_accept)
    cases.append(
        finalize_case(
            "N41",
            "contract binding before all accepts",
            before_accept,
            expect_pass=False,
            required_error="CONTRACT_BINDING_ACCEPTANCE_INCOMPLETE",
        )
    )
    superseded_binding = build_negotiation(
        [BASE], case_id="N42", include_contract=False
    )
    first = superseded_binding[_proposal_index(superseded_binding)]
    append_superseding_negotiation(superseded_binding)
    superseded_binding.append(
        _new_message(
            session_id=first["session_id"],
            contract_id=first["contract_id"],
            index=len(superseded_binding) + 1,
            sender=PARTY_A,
            message_type="CONTRACT_PROPOSE",
            contract_ref={
                "branch_id": "main",
                "base_version": "v1",
                "head_version": "v1",
            },
            payload={
                "contract": {
                    "contract_id": first["contract_id"],
                    "goal": "invalid superseded binding",
                    "roles": [PARTY_A, PARTY_B],
                    "ext": {
                        "capneg_v2": {
                            "capneg_version": "0.2",
                            "negotiation_id": first["payload"][
                                "negotiation_result"
                            ]["negotiation_id"],
                            "negotiation_result_hash": first["payload"][
                                "negotiation_result_hash"
                            ],
                            "profile_composition": first["payload"][
                                "negotiation_result"
                            ]["selected"]["profile_composition"],
                            "profile_composition_hash": first["payload"][
                                "negotiation_result"
                            ]["selected"]["profile_composition_hash"],
                        }
                    },
                }
            },
        )
    )
    _rehash(superseded_binding)
    cases.append(
        finalize_case(
            "N42",
            "contract binding to superseded result",
            superseded_binding,
            expect_pass=False,
            required_error="CONTRACT_BINDING_SUPERSEDED",
        )
    )
    substitution = build_negotiation(
        [MEDIATED, RESUMABLE],
        case_id="N43",
        include_contract=True,
    )
    contract_message = next(
        message
        for message in substitution
        if message["message_type"] == "CONTRACT_PROPOSE"
    )
    substituted_composition = _canonical_composition([MEDIATED])
    contract_message["payload"]["contract"]["ext"]["capneg_v2"].update(
        profile_composition=substituted_composition,
        profile_composition_hash=object_hash(
            COMPOSITION_HASH_DOMAIN, substituted_composition
        ),
    )
    _rehash(substitution)
    cases.append(
        finalize_case(
            "N43",
            "contract composition substitution",
            substitution,
            expect_pass=False,
            required_error="CONTRACT_BINDING_SUBSTITUTION",
        )
    )

    def projection_case(
        case_id: str,
        description: str,
        mutate: Callable[[dict[str, Any]], None],
        error: str,
    ) -> dict[str, Any]:
        messages = build_negotiation(
            [MEDIATED, RESUMABLE],
            case_id=case_id,
            include_contract=True,
            include_projection=True,
        )
        projection_message = messages[-1]
        mutate(projection_message["payload"]["session_state"])
        projection_message["payload"]["session_state_hash"] = object_hash(
            PROJECTION_OBJECT_TYPE,
            projection_message["payload"]["session_state"],
        )
        _rehash(messages)
        return finalize_case(
            case_id,
            description,
            messages,
            expect_pass=False,
            required_error=error,
        )

    cases.append(
        projection_case(
            "N44",
            "projection profile-set mismatch",
            lambda state: state.update(
                selected_aicp_profiles=[MEDIATED],
                profile_composition_hash=object_hash(
                    COMPOSITION_HASH_DOMAIN,
                    _canonical_composition([MEDIATED]),
                ),
            ),
            "PROJECTION_PROFILE_SET_MISMATCH",
        )
    )
    cases.append(
        projection_case(
            "N45",
            "projection composition-hash mismatch",
            lambda state: state.update(
                profile_composition_hash="sha256:" + "A" * 43
            ),
            "PROJECTION_COMPOSITION_HASH_MISMATCH",
        )
    )
    cases.append(
        projection_case(
            "N46",
            "projection accepted-result-hash mismatch",
            lambda state: state.update(
                accepted_negotiation_result_hash="sha256:" + "A" * 43
            ),
            "PROJECTION_ACCEPTED_RESULT_HASH_MISMATCH",
        )
    )
    cases.append(
        projection_case(
            "N47",
            "projection active-extension inconsistency",
            lambda state: state.update(active_extensions=["EXT-OBJECT-RESYNC"]),
            "PROJECTION_ACTIVE_EXTENSION_INCONSISTENT",
        )
    )

    schema_invalid = build_negotiation(
        [BASE], case_id="N48", include_acceptances=False
    )[:1]
    schema_invalid[0]["payload"].pop("capneg_version")
    _rehash(schema_invalid)
    cases.append(
        finalize_case(
            "N48",
            "schema-invalid message attempts state transition",
            schema_invalid,
            expect_pass=False,
            required_error="CAPNEG_PAYLOAD_SCHEMA_INVALID",
            invalid_messages={0: "CAPNEG_PAYLOAD_SCHEMA_INVALID"},
        )
    )
    broken_chain = build_negotiation([BASE], case_id="N49")[:4]
    broken_chain[-1]["prev_msg_hash"] = "sha256:" + "A" * 43
    broken_chain[-1]["message_hash"] = message_hash_from_body(
        message_body_without_hash_and_signatures(broken_chain[-1])
    )
    cases.append(
        finalize_case(
            "N49",
            "broken chain attempts state transition",
            broken_chain,
            expect_pass=False,
            required_error="CAPNEG_CHAIN_INVALID",
            invalid_messages={3: "CAPNEG_CHAIN_INVALID"},
        )
    )
    invalid_hash = build_negotiation([BASE], case_id="N50")[:4]
    invalid_hash[-1]["message_hash"] = "sha256:" + "A" * 43
    cases.append(
        finalize_case(
            "N50",
            "invalid message hash attempts acceptance",
            invalid_hash,
            expect_pass=False,
            required_error="CAPNEG_MESSAGE_HASH_INVALID",
            invalid_messages={3: "CAPNEG_MESSAGE_HASH_INVALID"},
        )
    )
    invalid_optional = build_negotiation([BASE], case_id="N51")[:4]
    acceptance = invalid_optional[-1]
    acceptance["signatures"] = [
        {
            "signer": acceptance["sender"],
            "kid": PUBLIC_KEY_MAP[acceptance["sender"]]["kid"],
            "object_type": "message",
            "object_hash": acceptance["message_hash"],
            "sig_b64url": "A" * 86,
        }
    ]
    cases.append(
        finalize_case(
            "N51",
            "present invalid optional signature in non-authenticated set",
            invalid_optional,
            expect_pass=False,
            required_error="ACCEPTANCE_SIGNATURE_INVALID",
        )
    )

    def context_mismatch(
        case_id: str,
        *,
        message_type: str,
        field: str,
    ) -> None:
        messages = build_negotiation(
            [BASE],
            case_id=case_id,
            include_acceptances=message_type == "CAPABILITIES_ACCEPT",
        )
        if message_type == "CAPABILITIES_ACCEPT":
            target = messages[-1]
        else:
            target = append_decision(
                messages,
                sender=PARTY_B,
                message_type="CAPABILITIES_REJECT",
            )
        target[field] = f"other-{field}-{case_id.lower()}"
        _rehash_preserving_signatures(messages)
        error = (
            "DECISION_SESSION_MISMATCH"
            if field == "session_id"
            else "DECISION_CONTRACT_MISMATCH"
        )
        cases.append(
            finalize_case(
                case_id,
                f"{message_type.lower()} envelope {field} mismatch",
                messages,
                expect_pass=False,
                required_error=error,
            )
        )

    context_mismatch("N52", message_type="CAPABILITIES_ACCEPT", field="session_id")
    context_mismatch("N53", message_type="CAPABILITIES_ACCEPT", field="contract_id")
    context_mismatch("N54", message_type="CAPABILITIES_REJECT", field="session_id")
    context_mismatch("N55", message_type="CAPABILITIES_REJECT", field="contract_id")

    wrong_signer = build_negotiation([AUTH], case_id="N56")
    wrong_signer[-1]["signatures"] = [
        _signature(wrong_signer[-1]["message_hash"], PARTY_A)
    ]
    cases.append(
        finalize_case(
            "N56",
            "valid other-party signature does not satisfy sender signature",
            wrong_signer,
            expect_pass=False,
            required_error="AUTHENTICATED_ACCEPTANCE_SIGNATURE_REQUIRED",
        )
    )

    replay_missing_signature = build_negotiation(
        [AUTH], case_id="N57", duplicate_acceptance=True
    )
    replay_missing_signature[4].pop("signatures", None)
    cases.append(
        finalize_case(
            "N57",
            "duplicate Authenticated Base acceptance has no signature",
            replay_missing_signature,
            expect_pass=False,
            required_error="AUTHENTICATED_ACCEPTANCE_SIGNATURE_REQUIRED",
        )
    )
    replay_invalid_signature = build_negotiation(
        [AUTH], case_id="N58", duplicate_acceptance=True
    )
    replay_invalid_signature[4]["signatures"][0]["sig_b64url"] = "A" * 86
    cases.append(
        finalize_case(
            "N58",
            "duplicate acceptance has an invalid current signature",
            replay_invalid_signature,
            expect_pass=False,
            required_error="ACCEPTANCE_SIGNATURE_INVALID",
        )
    )

    for case_id, message_offset, description in (
        ("N59", 0, "invalid signed declaration"),
        ("N60", 2, "invalid signed proposal"),
    ):
        messages = build_negotiation(
            [BASE], case_id=case_id, include_acceptances=False
        )
        target = messages[message_offset]
        target["signatures"] = [
            {
                **_signature(target["message_hash"], target["sender"]),
                "sig_b64url": "A" * 86,
            }
        ]
        cases.append(
            finalize_case(
                case_id,
                description,
                messages,
                expect_pass=False,
                required_error="CAPNEG_SIGNATURE_INVALID",
            )
        )

    invalid_signed_reject = build_negotiation(
        [BASE], case_id="N61", include_acceptances=False
    )
    invalid_reject = append_decision(
        invalid_signed_reject,
        sender=PARTY_B,
        message_type="CAPABILITIES_REJECT",
    )
    invalid_reject["signatures"] = [
        {
            **_signature(invalid_reject["message_hash"], PARTY_B),
            "sig_b64url": "A" * 86,
        }
    ]
    cases.append(
        finalize_case(
            "N61",
            "invalid signed rejection",
            invalid_signed_reject,
            expect_pass=False,
            required_error="CAPNEG_SIGNATURE_INVALID",
        )
    )

    unknown_signer = build_negotiation([AUTH], case_id="N62")
    unknown_signer[-1]["signatures"][0].update(
        signer="agent:unknown", kid="unknown-key"
    )
    cases.append(
        finalize_case(
            "N62",
            "Authenticated Base acceptance signature has unknown signer",
            unknown_signer,
            expect_pass=False,
            required_error="ACCEPTANCE_SIGNATURE_INVALID",
        )
    )
    kid_mismatch = build_negotiation([AUTH], case_id="N63")
    kid_mismatch[-1]["signatures"][0]["kid"] = "wrong-kid"
    cases.append(
        finalize_case(
            "N63",
            "Authenticated Base acceptance signature has mismatched kid",
            kid_mismatch,
            expect_pass=False,
            required_error="ACCEPTANCE_SIGNATURE_INVALID",
        )
    )
    copied_signature = build_negotiation([AUTH], case_id="N64")
    copied_signature[-1]["signatures"] = copy.deepcopy(
        copied_signature[-2]["signatures"]
    )
    cases.append(
        finalize_case(
            "N64",
            "Authenticated Base acceptance reuses a stale copied signature",
            copied_signature,
            expect_pass=False,
            required_error="ACCEPTANCE_SIGNATURE_INVALID",
        )
    )
    mixed_signatures = build_negotiation([AUTH], case_id="N65")
    mixed_signatures[-1]["signatures"].append(
        {
            **_signature(mixed_signatures[-1]["message_hash"], PARTY_A),
            "sig_b64url": "A" * 86,
        }
    )
    cases.append(
        finalize_case(
            "N65",
            "valid sender signature plus another invalid entry",
            mixed_signatures,
            expect_pass=False,
            required_error="ACCEPTANCE_SIGNATURE_INVALID",
        )
    )

    for case_id, field in (("N66", "session_id"), ("N67", "contract_id")):
        messages = build_negotiation(
            [AUTH], case_id=case_id, duplicate_acceptance=True
        )
        replay = messages[4]
        replay[field] = f"replay-other-{field}"
        _rehash_preserving_signatures(messages)
        cases.append(
            finalize_case(
                case_id,
                f"exact acceptance replay moved to another {field}",
                messages,
                expect_pass=False,
                required_error=(
                    "DECISION_SESSION_MISMATCH"
                    if field == "session_id"
                    else "DECISION_CONTRACT_MISMATCH"
                ),
            )
        )

    changed_sender = build_negotiation(
        [BASE], case_id="N68", duplicate_acceptance=True
    )
    changed_sender[4]["sender"] = PARTY_C
    _rehash(changed_sender)
    cases.append(
        finalize_case(
            "N68",
            "duplicate acceptance replay changes to a nonparticipant sender",
            changed_sender,
            expect_pass=False,
            required_error="ACCEPTOR_NOT_PARTICIPANT",
        )
    )

    stale_accept = build_negotiation(
        [BASE], case_id="N69", include_acceptances=False
    )
    append_declaration_supersession(stale_accept, PARTY_A)
    append_decision(stale_accept, sender=PARTY_B, proposal=stale_accept[2])
    cases.append(
        finalize_case(
            "N69",
            "declaration superseded after proposal then old proposal accepted",
            stale_accept,
            expect_pass=False,
            required_error="STALE_CAPABILITIES_DECLARATION",
        )
    )
    stale_reject = build_negotiation(
        [BASE], case_id="N70", include_acceptances=False
    )
    append_declaration_supersession(stale_reject, PARTY_A)
    append_decision(
        stale_reject,
        sender=PARTY_B,
        message_type="CAPABILITIES_REJECT",
        proposal=stale_reject[2],
    )
    cases.append(
        finalize_case(
            "N70",
            "declaration superseded after proposal then old proposal rejected",
            stale_reject,
            expect_pass=False,
            required_error="STALE_CAPABILITIES_DECLARATION",
        )
    )

    revised_after_stale = build_negotiation(
        [BASE], case_id="N71", include_acceptances=False
    )
    first_proposal = revised_after_stale[2]
    append_declaration_supersession(revised_after_stale, PARTY_A)
    append_decision(
        revised_after_stale, sender=PARTY_B, proposal=first_proposal
    )
    revised_result = copy.deepcopy(
        first_proposal["payload"]["negotiation_result"]
    )
    revised_result["proposal_revision"] = 2
    revised_result["declaration_bindings"] = [
        {
            "party_id": party,
            "capabilities_id": declaration["payload"]["capabilities_id"],
            "declaration_message_id": declaration["message_id"],
            "declaration_message_hash": declaration["message_hash"],
        }
        for party in (PARTY_A, PARTY_B)
        for declaration in [
            next(
                message
                for message in reversed(revised_after_stale)
                if message.get("message_type") == "CAPABILITIES_DECLARE"
                and message["payload"]["party_id"] == party
            )
        ]
    ]
    revised_after_stale.append(
        _new_message(
            session_id=first_proposal["session_id"],
            contract_id=first_proposal["contract_id"],
            index=len(revised_after_stale) + 1,
            sender=PARTY_A,
            message_type="CAPABILITIES_PROPOSE",
            payload={
                "capneg_version": "0.2",
                "proposal_revision": 2,
                "negotiation_result": revised_result,
                "negotiation_result_hash": object_hash(
                    NEGOTIATION_HASH_DOMAIN, revised_result
                ),
                "supersedes_proposal_message_id": first_proposal["message_id"],
                "supersedes_proposal_message_hash": first_proposal["message_hash"],
            },
        )
    )
    _rehash(revised_after_stale)
    cases.append(
        finalize_case(
            "N71",
            "stale decision fails but correct revised proposal binds latest declarations",
            revised_after_stale,
            expect_pass=False,
            required_error="STALE_CAPABILITIES_DECLARATION",
        )
    )

    declaration_fork = build_negotiation(
        [BASE], case_id="N72", include_acceptances=False
    )
    original = declaration_fork[0]
    append_declaration_supersession(declaration_fork, PARTY_A)
    fork = copy.deepcopy(original)
    fork["message_id"] = "m5"
    fork["timestamp"] = "2026-07-01T00:00:05Z"
    fork["payload"]["capabilities_id"] = "cap-n72-s-fork"
    fork["payload"]["supersedes_capabilities_id"] = original["payload"][
        "capabilities_id"
    ]
    declaration_fork.append(fork)
    _rehash(declaration_fork)
    cases.append(
        finalize_case(
            "N72",
            "declaration supersession fork after proposal",
            declaration_fork,
            expect_pass=False,
            required_error="INVALID_DECLARATION_SUPERSESSION",
        )
    )

    rejected_then_accept = build_negotiation(
        [BASE], case_id="N73", include_acceptances=False
    )
    append_decision(
        rejected_then_accept,
        sender=PARTY_B,
        message_type="CAPABILITIES_REJECT",
    )
    append_decision(rejected_then_accept, sender=PARTY_A)
    cases.append(
        finalize_case(
            "N73",
            "acceptance after another participant rejected the revision",
            rejected_then_accept,
            expect_pass=False,
            required_error="REVISION_REJECTED",
        )
    )
    accepted_then_rejected = build_negotiation(
        [BASE], case_id="N74", include_acceptances=False
    )
    append_decision(accepted_then_rejected, sender=PARTY_A)
    append_decision(
        accepted_then_rejected,
        sender=PARTY_B,
        message_type="CAPABILITIES_REJECT",
    )
    append_decision(accepted_then_rejected, sender=PARTY_A)
    cases.append(
        finalize_case(
            "N74",
            "previous accepter cannot advance a rejected revision",
            accepted_then_rejected,
            expect_pass=False,
            required_error="REVISION_REJECTED",
        )
    )
    retargeted_reject = build_negotiation(
        [BASE], case_id="N75", include_acceptances=False
    )
    append_decision(
        retargeted_reject,
        sender=PARTY_B,
        message_type="CAPABILITIES_REJECT",
    )
    append_decision(
        retargeted_reject,
        sender=PARTY_B,
        message_type="CAPABILITIES_REJECT",
        payload_updates={"reason_code": "PROFILE_REQUIREMENTS_MISMATCH"},
    )
    cases.append(
        finalize_case(
            "N75",
            "duplicate rejection changes reason code",
            retargeted_reject,
            expect_pass=False,
            required_error="REJECTION_REPLAY_RETARGETED",
        )
    )

    participant_crypto_missing = build_negotiation(
        [BASE], case_id="N76", include_acceptances=False
    )
    participant_crypto_missing[0]["payload"]["supported_crypto_profiles"] = [
        "aicp.crypto.ed25519.v1"
    ]
    participant_crypto_missing[0]["payload"]["required_crypto_profiles"] = [
        "aicp.crypto.ed25519.v1"
    ]
    _refresh_proposal_after_declarations(participant_crypto_missing, 2)
    cases.append(
        finalize_case(
            "N76",
            "participant-required crypto omitted by selected result",
            participant_crypto_missing,
            expect_pass=False,
            required_error="PARTICIPANT_REQUIRED_CRYPTO_MISSING",
        )
    )

    channel_mismatch = build_negotiation(
        [BASE], case_id="N77", include_acceptances=False
    )
    channel_mismatch[0]["payload"]["supported_channel_properties"] = {
        "CP-ORDERING-0.1": ["ordered"]
    }
    channel_mismatch[1]["payload"]["supported_channel_properties"] = {
        "CP-ORDERING-0.1": ["unordered"]
    }
    channel_mismatch[2]["payload"]["negotiation_result"]["selected"][
        "channel_properties"
    ] = {"CP-ORDERING-0.1": "ordered"}
    _refresh_proposal_after_declarations(channel_mismatch, 2)
    cases.append(
        finalize_case(
            "N77",
            "selected channel property is outside one declaration",
            channel_mismatch,
            expect_pass=False,
            required_error="SELECTION_OUTSIDE_DECLARATION",
        )
    )
    limit_mismatch = build_negotiation(
        [BASE], case_id="N78", include_acceptances=False
    )
    limit_mismatch[2]["payload"]["negotiation_result"]["selected"]["limits"] = {
        "max_message_bytes": 1048577
    }
    _refresh_proposal_after_declarations(limit_mismatch, 2)
    cases.append(
        finalize_case(
            "N78",
            "selected limit exceeds a participant declaration",
            limit_mismatch,
            expect_pass=False,
            required_error="SELECTION_OUTSIDE_DECLARATION",
        )
    )

    def supersession_mutation(
        case_id: str,
        mutate: Callable[[dict[str, Any]], None],
        required_error: str,
    ) -> None:
        messages = build_negotiation([BASE], case_id=case_id)
        append_superseding_negotiation(messages)
        new_proposal = next(
            message
            for message in reversed(messages)
            if message["message_type"] == "CAPABILITIES_PROPOSE"
        )
        mutate(new_proposal["payload"]["negotiation_result"])
        new_proposal["payload"]["negotiation_result_hash"] = object_hash(
            NEGOTIATION_HASH_DOMAIN,
            new_proposal["payload"]["negotiation_result"],
        )
        del messages[messages.index(new_proposal) + 1 :]
        _rehash(messages)
        cases.append(
            finalize_case(
                case_id,
                "invalid same-context negotiation supersession",
                messages,
                expect_pass=False,
                required_error=required_error,
            )
        )

    supersession_mutation(
        "N79",
        lambda result: result.update(session_id="other-supersession-session"),
        "NEGOTIATION_SUPERSESSION_CONTEXT_MISMATCH",
    )
    supersession_mutation(
        "N80",
        lambda result: result.update(contract_id="other-supersession-contract"),
        "NEGOTIATION_SUPERSESSION_CONTEXT_MISMATCH",
    )
    supersession_mutation(
        "N81",
        lambda result: result.update(participants=[PARTY_A, PARTY_C]),
        "NEGOTIATION_SUPERSESSION_CONTEXT_MISMATCH",
    )

    double_fork = build_negotiation([BASE], case_id="N82")
    old_negotiation_id = double_fork[2]["payload"]["negotiation_result"][
        "negotiation_id"
    ]
    append_superseding_negotiation(double_fork)
    accepted_successor = next(
        message
        for message in reversed(double_fork)
        if message["message_type"] == "CAPABILITIES_PROPOSE"
    )
    fork_result = copy.deepcopy(accepted_successor["payload"]["negotiation_result"])
    fork_result["negotiation_id"] += "-fork"
    fork_result["supersedes_negotiation_id"] = old_negotiation_id
    double_fork.append(
        _new_message(
            session_id=double_fork[0]["session_id"],
            contract_id=double_fork[0]["contract_id"],
            index=len(double_fork) + 1,
            sender=PARTY_A,
            message_type="CAPABILITIES_PROPOSE",
            payload={
                "capneg_version": "0.2",
                "proposal_revision": 1,
                "negotiation_result": fork_result,
                "negotiation_result_hash": object_hash(
                    NEGOTIATION_HASH_DOMAIN, fork_result
                ),
            },
        )
    )
    _rehash(double_fork)
    cases.append(
        finalize_case(
            "N82",
            "double supersession fork from an already superseded negotiation",
            double_fork,
            expect_pass=False,
            required_error="NEGOTIATION_SUPERSESSION_INVALID",
        )
    )

    def temporal_projection_case(
        case_id: str,
        as_of_index: int | None,
        *,
        branch_only: bool = False,
    ) -> None:
        messages = build_negotiation([BASE], case_id=case_id)
        proposal_message = messages[2]
        if as_of_index is None:
            as_of = "sha256:" + "Z" * 43
        else:
            as_of = messages[as_of_index]["message_hash"]
        known_head = messages[-1]["message_hash"]
        append_projection(
            messages,
            as_of_message_hash=as_of,
            result=proposal_message["payload"]["negotiation_result"],
            case_id=case_id,
            branch_head_hash=as_of if branch_only else known_head,
        )
        cases.append(
            finalize_case(
                case_id,
                "projection uses a non-accepted or unproved as-of point",
                messages,
                expect_pass=False,
                required_error=(
                    "PROJECTION_AS_OF_STALE"
                    if as_of_index is None
                    else "PROJECTION_ACCEPTANCE_NOT_ESTABLISHED"
                ),
            )
        )

    temporal_projection_case("N83", 0)
    temporal_projection_case("N84", 2)
    temporal_projection_case("N85", 3)
    temporal_projection_case("N86", None)
    temporal_projection_case("N87", None, branch_only=True)

    def invalid_contract_case(
        case_id: str,
        mutate: Callable[[dict[str, Any], dict[str, Any]], None],
        error: str,
    ) -> None:
        messages = build_negotiation(
            [BASE], case_id=case_id, include_contract=True
        )
        contract_message = next(
            message
            for message in messages
            if message["message_type"] == "CONTRACT_PROPOSE"
        )
        mutate(contract_message, contract_message["payload"]["contract"])
        _rehash(messages)
        cases.append(
            finalize_case(
                case_id,
                "structurally invalid Core contract with valid CAPNEG binding",
                messages,
                expect_pass=False,
                required_error=error,
            )
        )

    invalid_contract_case(
        "N88",
        lambda _message, contract: contract.pop("contract_id"),
        "CORE_CONTRACT_SCHEMA_INVALID",
    )
    invalid_contract_case(
        "N89",
        lambda _message, contract: contract.update(contract_id="other-contract"),
        "CONTRACT_ID_MISMATCH",
    )
    invalid_contract_case(
        "N90",
        lambda _message, contract: contract.pop("goal"),
        "CORE_CONTRACT_SCHEMA_INVALID",
    )
    invalid_contract_case(
        "N91",
        lambda _message, contract: contract.update(
            policies=[{"policy_id": "p1", "category": "privacy"}]
        ),
        "CORE_CONTRACT_SCHEMA_INVALID",
    )

    strict_constraints = build_negotiation(
        [BASE], case_id="N92", include_acceptances=False
    )
    strict_reject = append_decision(
        strict_constraints,
        sender=PARTY_B,
        message_type="CAPABILITIES_REJECT",
        payload_updates={
            "alternative_constraints": {
                "constraints_version": "aicp.capneg.alternative_constraints.v1",
                "unknown_constraint": True,
            }
        },
    )
    cases.append(
        finalize_case(
            "N92",
            "alternative constraints reject undocumented fields",
            strict_constraints,
            expect_pass=False,
            required_error="CAPNEG_PAYLOAD_SCHEMA_INVALID",
            invalid_messages={
                strict_constraints.index(strict_reject): "CAPNEG_PAYLOAD_SCHEMA_INVALID"
            },
        )
    )

    alternative_requirements = build_negotiation(
        [MEDIATED, RESUMABLE],
        case_id="N93",
        include_acceptances=False,
        required_by_party={PARTY_B: [RESUMABLE]},
    )
    append_decision(
        alternative_requirements,
        sender=PARTY_B,
        message_type="CAPABILITIES_REJECT",
        payload_updates={
            "alternative_profile_compositions": [
                _canonical_composition([MEDIATED])
            ]
        },
    )
    cases.append(
        finalize_case(
            "N93",
            "rejection alternative omits participant profile minimum",
            alternative_requirements,
            expect_pass=False,
            required_error="REJECTION_ALTERNATIVE_REQUIREMENTS_UNMET",
        )
    )

    retargeted_alternative = build_negotiation(
        [BASE], case_id="N94", include_acceptances=False
    )
    append_decision(
        retargeted_alternative,
        sender=PARTY_B,
        message_type="CAPABILITIES_REJECT",
    )
    append_decision(
        retargeted_alternative,
        sender=PARTY_B,
        message_type="CAPABILITIES_REJECT",
        payload_updates={
            "alternative_profile_compositions": [_canonical_composition([BASE])]
        },
    )
    cases.append(
        finalize_case(
            "N94",
            "duplicate rejection changes alternatives",
            retargeted_alternative,
            expect_pass=False,
            required_error="REJECTION_REPLAY_RETARGETED",
        )
    )

    duplicate_message_id = build_negotiation([BASE], case_id="N95")[:4]
    duplicate_message_id[-1]["message_id"] = duplicate_message_id[0]["message_id"]
    _rehash(duplicate_message_id)
    cases.append(
        finalize_case(
            "N95",
            "duplicate raw message ID is blocked before reduction",
            duplicate_message_id,
            expect_pass=False,
            required_error="CAPNEG_MESSAGE_ID_DUPLICATE",
        )
    )
    invalid_message_id = build_negotiation([BASE], case_id="N96")[:1]
    invalid_message_id[0]["message_id"] = 7
    _rehash(invalid_message_id)
    cases.append(
        finalize_case(
            "N96",
            "non-string raw message ID is blocked before reduction",
            invalid_message_id,
            expect_pass=False,
            required_error="CAPNEG_MESSAGE_ID_INVALID",
        )
    )

    invalid_projection_signature = build_negotiation(
        [BASE], case_id="N97", include_projection=True
    )
    projection_message = invalid_projection_signature[-1]
    projection_message["signatures"] = [
        {
            **_signature(projection_message["message_hash"], PARTY_B),
            "sig_b64url": "A" * 86,
        }
    ]
    cases.append(
        finalize_case(
            "N97",
            "invalid present signature on projection message",
            invalid_projection_signature,
            expect_pass=False,
            required_error="CAPNEG_SIGNATURE_INVALID",
        )
    )
    invalid_contract_signature = build_negotiation(
        [BASE], case_id="N98", include_contract=True
    )
    signed_contract = next(
        message
        for message in invalid_contract_signature
        if message["message_type"] == "CONTRACT_PROPOSE"
    )
    signed_contract["signatures"] = [
        {
            **_signature(signed_contract["message_hash"], PARTY_A),
            "sig_b64url": "A" * 86,
        }
    ]
    cases.append(
        finalize_case(
            "N98",
            "invalid present signature on CAPNEG-bound contract",
            invalid_contract_signature,
            expect_pass=False,
            required_error="CAPNEG_SIGNATURE_INVALID",
        )
    )

    unlinked_same = build_negotiation([BASE], case_id="N99")
    append_new_negotiation(
        unlinked_same,
        suffix="unlinked",
        supersedes_negotiation_id=None,
    )
    cases.append(
        finalize_case(
            "N99",
            "same-composition second root omits required supersession",
            unlinked_same,
            expect_pass=False,
            required_error="NEGOTIATION_SUPERSESSION_REQUIRED",
        )
    )

    unlinked_different = build_negotiation(
        [MEDIATED, RESUMABLE], case_id="N100"
    )
    append_new_negotiation(
        unlinked_different,
        suffix="unlinked",
        supersedes_negotiation_id=None,
        profiles=[MEDIATED],
    )
    cases.append(
        finalize_case(
            "N100",
            "different-composition second root omits required supersession",
            unlinked_different,
            expect_pass=False,
            required_error="NEGOTIATION_SUPERSESSION_REQUIRED",
        )
    )

    accept_unlinked = build_negotiation([BASE], case_id="N101")
    append_new_negotiation(
        accept_unlinked,
        suffix="unlinked",
        supersedes_negotiation_id=None,
        acceptance_senders=(PARTY_A, PARTY_B),
    )
    cases.append(
        finalize_case(
            "N101",
            "attempt to fully accept an unlinked second root",
            accept_unlinked,
            expect_pass=False,
            required_error="NEGOTIATION_SUPERSESSION_REQUIRED",
        )
    )

    forked_successors = build_negotiation([BASE], case_id="N102")
    root_id = forked_successors[2]["payload"]["negotiation_result"][
        "negotiation_id"
    ]
    first_successor = append_new_negotiation(
        forked_successors,
        suffix="successor-a",
        supersedes_negotiation_id=root_id,
    )
    other_successor = append_new_negotiation(
        forked_successors,
        suffix="successor-b",
        supersedes_negotiation_id=root_id,
    )
    append_decision(
        forked_successors, sender=PARTY_A, proposal=first_successor
    )
    append_decision(
        forked_successors, sender=PARTY_B, proposal=first_successor
    )
    append_decision(
        forked_successors, sender=PARTY_A, proposal=other_successor
    )
    append_decision(
        forked_successors, sender=PARTY_B, proposal=other_successor
    )
    cases.append(
        finalize_case(
            "N102",
            "successor decisions cannot replay through a predecessor superseded by another successor",
            forked_successors,
            expect_pass=False,
            required_error="NEGOTIATION_SUPERSESSION_INVALID",
        )
    )

    unsigned_without_crypto = build_negotiation([AUTH], case_id="N103")[:4]
    unsigned_without_crypto[-1].pop("signatures", None)
    _rehash(unsigned_without_crypto)
    cases.append(
        finalize_case(
            "N103",
            "direct Authenticated Base acceptance requires a signature without crypto",
            unsigned_without_crypto,
            expect_pass=False,
            required_error="AUTHENTICATED_ACCEPTANCE_SIGNATURE_REQUIRED",
            execution_metadata={"crypto_available": False},
        )
    )

    signed_without_crypto = build_negotiation([AUTH], case_id="N104")[:4]
    cases.append(
        finalize_case(
            "N104",
            "signed Authenticated Base acceptance cannot advance without verification",
            signed_without_crypto,
            expect_pass=False,
            required_error="CRYPTO_VERIFICATION_UNAVAILABLE",
            execution_metadata={"crypto_available": False},
        )
    )

    if len(cases) != 104:
        raise ValueError(f"expected 104 negative families, generated {len(cases)}")
    return sorted(cases, key=lambda case: int(case["id"][1:]))


def composition_vectors() -> list[dict[str, str]]:
    return [
        {"id": vector_id, "oracle_case_id": vector_id}
        for vector_id in (
            "singleton-base",
            "mediated-resumable",
            "authenticated-mediated",
            "delegated-workflow",
            "agent-media-bazaar",
            "redundant-base-mediated",
            "exclusive-policy-dialects",
            "core-family-conflict",
        )
    ]


def render_payload(
    positive: list[dict[str, Any]],
    negative: list[dict[str, Any]],
) -> tuple[str, str, str, str, str]:
    metadata = {
        "fixture_version": "aicp.capneg_v0_2.fixtures.v3",
        "generator": "scripts/generate_capneg_v02_fixtures.py",
    }
    positive_payload = {
        **metadata,
        "expectation": "pass",
        "case_count": len(positive),
        "cases": positive,
    }
    negative_payload = {
        **metadata,
        "expectation": "fail",
        "case_count": len(negative),
        "cases": negative,
    }
    vectors_payload = {
        "vector_version": "aicp.capneg_v0_2.cross_language.v3",
        "generator": "scripts/generate_capneg_v02_fixtures.py",
        "composition_oracle_ref": (
            "fixtures/extensions/capneg_v0_2/composition_oracle.json"
        ),
        "negotiation_oracle_ref": (
            "fixtures/extensions/capneg_v0_2/oracle_expectations.json"
        ),
        "composition_vectors": composition_vectors(),
        "negotiation_vectors": [
            {
                "id": case["id"],
                "source_catalog": (
                    "fixtures/extensions/capneg_v0_2/positive_cases.json"
                    if case["expect_pass"]
                    else "fixtures/extensions/capneg_v0_2/negative_cases.json"
                ),
                "case_id": case["id"],
                "oracle_case_id": case["oracle_case_id"],
            }
            for case in positive + negative
            if case["id"]
            in {
                "P02",
                "P03",
                "P06",
                "P07",
                "P08",
                "P09",
                "P11",
                "P12",
                "P14",
                "P15",
                "P16",
                "P17",
                "P18",
                "P19",
                "P20",
                "N06",
                "N11",
                "N25",
                "N30",
                "N36",
                "N38",
                "N43",
                "N44",
                "N51",
                "N52",
                "N53",
                "N54",
                "N55",
                "N56",
                "N57",
                "N58",
                "N59",
                "N60",
                "N61",
                "N62",
                "N63",
                "N64",
                "N65",
                "N66",
                "N67",
                "N68",
                "N69",
                "N70",
                "N71",
                "N72",
                "N73",
                "N74",
                "N75",
                "N76",
                "N77",
                "N78",
                "N79",
                "N80",
                "N81",
                "N82",
                "N83",
                "N84",
                "N85",
                "N86",
                "N87",
                "N88",
                "N89",
                "N90",
                "N91",
                "N93",
                "N94",
                "N97",
                "N98",
                "N99",
                "N100",
                "N101",
                "N102",
                "N103",
                "N104",
            }
        ],
    }
    projection_positive = {
        **metadata,
        "capability": PROJECTION_VERSION,
        "expectation": "pass",
        "case_count": 4,
        "cases": [
            {
                "id": case["id"],
                "source_catalog": (
                    "fixtures/extensions/capneg_v0_2/positive_cases.json"
                ),
                "case_id": case["id"],
                "oracle_case_id": case["oracle_case_id"],
            }
            for case in positive
            if case["id"] in {"P09", "P15", "P16", "P17"}
        ],
    }
    projection_negative_cases = [
        case
        for case in negative
        if case["id"]
        in {"N44", "N45", "N46", "N47", "N83", "N84", "N85", "N86", "N87"}
    ]
    projection_negative = {
        **metadata,
        "capability": PROJECTION_VERSION,
        "expectation": "fail",
        "case_count": len(projection_negative_cases),
        "cases": [
            {
                "id": case["id"],
                "source_catalog": (
                    "fixtures/extensions/capneg_v0_2/negative_cases.json"
                ),
                "case_id": case["id"],
                "oracle_case_id": case["oracle_case_id"],
            }
            for case in projection_negative_cases
        ],
    }
    render = lambda payload: json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    return (
        render(positive_payload),
        render(negative_payload),
        render(vectors_payload),
        render(projection_positive),
        render(projection_negative),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--write", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--root", type=Path, default=ROOT)
    args = parser.parse_args()
    configure_root(args.root)

    positive = positive_cases()
    negative = negative_cases()
    rendered = render_payload(positive, negative)
    paths = (
        POSITIVE_OUT,
        NEGATIVE_OUT,
        VECTORS_OUT,
        PROJECTION_POSITIVE_OUT,
        PROJECTION_NEGATIVE_OUT,
    )
    if args.check:
        stale = [
            path.relative_to(ROOT).as_posix()
            for path, expected in zip(paths, rendered)
            if not path.is_file() or path.read_text(encoding="utf-8") != expected
        ]
        if stale:
            print("[FAIL] stale CAPNEG v0.2 generated artifacts: " + ", ".join(stale))
            return 1
        print(
            f"OK: CAPNEG v0.2 generated artifacts match "
            f"{len(positive)} positive and {len(negative)} negative cases."
        )
        return 0

    OUT.mkdir(parents=True, exist_ok=True)
    PROJECTION_OUT.mkdir(parents=True, exist_ok=True)
    for path, content in zip(paths, rendered):
        path.write_text(content, encoding="utf-8")
    print(
        f"Generated CAPNEG v0.2 fixtures: "
        f"{len(positive)} positive, {len(negative)} negative."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
