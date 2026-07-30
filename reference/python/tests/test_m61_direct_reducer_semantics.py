from __future__ import annotations

import base64
import copy
import json
import sys
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


ROOT = Path(__file__).resolve().parents[3]
RUNNER_DIR = ROOT / "conformance/capneg_v02_runner"
if str(RUNNER_DIR) not in sys.path:
    sys.path.insert(0, str(RUNNER_DIR))

from aicp_ref.hashing import message_hash_from_body, object_hash  # noqa: E402
from aicp_ref.validate import (  # noqa: E402
    message_body_without_hash_and_signatures,
)
from aicp_ref_capneg_v02.session_state_v2 import (  # noqa: E402
    PROJECTION_VERSION,
    validate_session_state_projection_v2,
)
from aicp_ref_capneg_v02.state_machine import (  # noqa: E402
    CapnegV02Reducer,
    NEGOTIATION_HASH_DOMAIN,
    reduce_capneg_v02,
)
from validation import validate_messages  # noqa: E402


def load(relative: str) -> Any:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


RULES = load("registry/aicp_profile_composition_rules.json")
REASONS = {entry["id"] for entry in load("registry/capneg_reason_codes.json")}
KEYS = load("fixtures/keys/GT_public_keys.json")
PRIVATE_KEYS = load("fixtures/keys/TEST_private_keys.json")
EXTENSIONS = {entry["id"] for entry in load("registry/extension_ids.json")}
MESSAGES = {entry["id"] for entry in load("registry/message_types.json")}
BASE = {"profile_id": "AICP-BASE", "profile_version": "0.1"}
AUTH = {
    "profile_id": "AICP-AUTHENTICATED-BASE",
    "profile_version": "0.1",
}
PARTIES = ["agent:S", "agent:T"]


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _signature(message_hash: str, signer: str) -> dict[str, str]:
    metadata = PRIVATE_KEYS[signer]
    key = Ed25519PrivateKey.from_private_bytes(
        _decode(metadata["private_key_b64url"])
    )
    return {
        "signer": signer,
        "kid": metadata["kid"],
        "object_type": "message",
        "object_hash": message_hash,
        "sig_b64url": _encode(
            key.sign(f"AICP1\0SIG\0{message_hash}".encode())
        ),
    }


def _rehash(
    messages: list[dict[str, Any]],
    signers: dict[str, str] | None = None,
) -> None:
    previous = None
    signers = signers or {}
    for message in messages:
        body = message_body_without_hash_and_signatures(message)
        body.pop("prev_msg_hash", None)
        if previous is not None:
            body["prev_msg_hash"] = previous
        digest = message_hash_from_body(body)
        message.clear()
        message.update(body)
        message["message_hash"] = digest
        signer = signers.get(message["message_id"])
        if signer is not None:
            message["signatures"] = [_signature(digest, signer)]
        previous = digest


def _message(
    messages: list[dict[str, Any]],
    message_type: str,
    sender: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    index = len(messages) + 1
    return {
        "session_id": messages[0]["session_id"] if messages else "direct-session",
        "message_id": f"m{index}",
        "timestamp": f"2026-07-30T00:00:{index:02d}Z",
        "sender": sender,
        "message_type": message_type,
        "contract_id": (
            messages[0]["contract_id"] if messages else "direct-contract"
        ),
        "payload": payload,
    }


def direct_transcript(
    *,
    authenticated: bool = False,
    accept_senders: tuple[str, ...] = (),
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    profile = AUTH if authenticated else BASE
    crypto = ["aicp.crypto.ed25519.v1"] if authenticated else []
    composition = {
        "composition_version": "aicp.profile_composition.v1",
        "profiles": [copy.deepcopy(profile)],
    }
    selected = {
        "crypto_profiles": crypto,
        "privacy_mode": "standard",
        "profile_composition": composition,
        "profile_composition_hash": object_hash(
            "capneg.profile_composition", composition
        ),
        "required_extensions": [],
        "required_policy_categories": [],
        "binding": "BIND-HTTP-0.1",
        "limits": {"max_message_bytes": 1024},
    }
    messages: list[dict[str, Any]] = []
    for party in PARTIES:
        messages.append(
            _message(
                messages,
                "CAPABILITIES_DECLARE",
                party,
                {
                    "capneg_version": "0.2",
                    "capabilities_id": f"direct-{party[-1]}",
                    "party_id": party,
                    "supported_crypto_profiles": crypto,
                    "required_crypto_profiles": crypto,
                    "supported_privacy_modes": ["standard"],
                    "supported_aicp_profiles": [copy.deepcopy(profile)],
                    "required_aicp_profiles": [],
                    "supported_extensions": [],
                    "supported_policy_categories": [],
                    "bindings": ["BIND-HTTP-0.1"],
                    "limits": {"max_message_bytes": 1024},
                },
            )
        )
    _rehash(messages)
    result = {
        "negotiation_id": "direct-root",
        "proposal_revision": 1,
        "session_id": "direct-session",
        "contract_id": "direct-contract",
        "participants": PARTIES,
        "declaration_bindings": [
            {
                "party_id": message["payload"]["party_id"],
                "capabilities_id": message["payload"]["capabilities_id"],
                "declaration_message_id": message["message_id"],
                "declaration_message_hash": message["message_hash"],
            }
            for message in messages
        ],
        "selected": selected,
    }
    proposal = _message(
        messages,
        "CAPABILITIES_PROPOSE",
        PARTIES[0],
        {
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
    signers: dict[str, str] = {}
    for sender in accept_senders:
        decision = append_decision(messages, proposal, sender)
        if authenticated:
            signers[decision["message_id"]] = sender
        _rehash(messages, signers)
    return messages, signers


def append_decision(
    messages: list[dict[str, Any]],
    proposal: dict[str, Any],
    sender: str,
    *,
    accepted: bool = True,
) -> dict[str, Any]:
    result = proposal["payload"]["negotiation_result"]
    payload = {
        "capneg_version": "0.2",
        "negotiation_id": result["negotiation_id"],
        "proposal_revision": proposal["payload"]["proposal_revision"],
        "proposal_message_id": proposal["message_id"],
        "proposal_message_hash": proposal["message_hash"],
        "negotiation_result_hash": proposal["payload"][
            "negotiation_result_hash"
        ],
    }
    if accepted:
        payload["accepted"] = True
        message_type = "CAPABILITIES_ACCEPT"
    else:
        payload["reason_code"] = "PROFILE_SET_UNSUPPORTED"
        message_type = "CAPABILITIES_REJECT"
    decision = _message(messages, message_type, sender, payload)
    messages.append(decision)
    _rehash(messages)
    return decision


def append_successor(
    messages: list[dict[str, Any]],
    *,
    negotiation_id: str,
    supersedes: str | None,
    accept_senders: tuple[str, ...] = (),
) -> dict[str, Any]:
    prior = messages[2]["payload"]["negotiation_result"]
    result = copy.deepcopy(prior)
    result["negotiation_id"] = negotiation_id
    if supersedes is None:
        result.pop("supersedes_negotiation_id", None)
    else:
        result["supersedes_negotiation_id"] = supersedes
    proposal = _message(
        messages,
        "CAPABILITIES_PROPOSE",
        PARTIES[1],
        {
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
    for sender in accept_senders:
        append_decision(messages, proposal, sender)
    return proposal


def errors(messages: list[dict[str, Any]], **kwargs: Any) -> list[str]:
    return reduce_capneg_v02(
        messages,
        rules=RULES,
        registered_reason_codes=REASONS,
        key_map=KEYS,
        **kwargs,
    )["errors"]


def test_hand_authored_decision_context_sender_rejection_and_declaration() -> None:
    messages, _ = direct_transcript(accept_senders=(PARTIES[0],))
    wrong_session = copy.deepcopy(messages)
    wrong_session[-1]["session_id"] = "other-session"
    assert errors(wrong_session) == ["DECISION_SESSION_MISMATCH"]

    wrong_contract = copy.deepcopy(messages)
    wrong_contract[-1]["contract_id"] = "other-contract"
    assert errors(wrong_contract) == ["DECISION_CONTRACT_MISMATCH"]

    authenticated, signers = direct_transcript(
        authenticated=True, accept_senders=(PARTIES[0],)
    )
    other_signature = copy.deepcopy(authenticated)
    other_signature[-1]["signatures"] = [
        _signature(other_signature[-1]["message_hash"], PARTIES[1])
    ]
    assert errors(other_signature) == [
        "AUTHENTICATED_ACCEPTANCE_SIGNATURE_REQUIRED"
    ]

    rejected, _ = direct_transcript()
    proposal = rejected[2]
    append_decision(rejected, proposal, PARTIES[0], accepted=False)
    append_decision(rejected, proposal, PARTIES[1])
    snapshot = reduce_capneg_v02(
        rejected, rules=RULES, registered_reason_codes=REASONS, key_map=KEYS
    )
    assert snapshot["state"] == "REJECTED"
    assert snapshot["errors"] == ["REVISION_REJECTED"]

    stale, _ = direct_transcript()
    stale_declaration = copy.deepcopy(stale[0])
    stale_declaration["message_id"] = "m4"
    stale_declaration["payload"]["capabilities_id"] = "direct-S-next"
    stale_declaration["payload"]["supersedes_capabilities_id"] = "direct-S"
    stale.append(stale_declaration)
    _rehash(stale)
    append_decision(stale, stale[2], PARTIES[0])
    assert errors(stale) == ["STALE_CAPABILITIES_DECLARATION"]


def test_hand_authored_crypto_projection_contract_and_unlinked_root() -> None:
    missing_crypto, _ = direct_transcript()
    missing_crypto[0]["payload"]["supported_crypto_profiles"] = [
        "aicp.crypto.ed25519.v1"
    ]
    missing_crypto[0]["payload"]["required_crypto_profiles"] = [
        "aicp.crypto.ed25519.v1"
    ]
    _rehash(missing_crypto)
    result = missing_crypto[2]["payload"]["negotiation_result"]
    result["declaration_bindings"] = [
        {
            "party_id": message["payload"]["party_id"],
            "capabilities_id": message["payload"]["capabilities_id"],
            "declaration_message_id": message["message_id"],
            "declaration_message_hash": message["message_hash"],
        }
        for message in missing_crypto[:2]
    ]
    missing_crypto[2]["payload"]["negotiation_result_hash"] = object_hash(
        NEGOTIATION_HASH_DOMAIN, result
    )
    _rehash(missing_crypto)
    assert errors(missing_crypto) == ["PARTICIPANT_REQUIRED_CRYPTO_MISSING"]

    partial, _ = direct_transcript(accept_senders=(PARTIES[0],))
    proposal = partial[2]
    projection = {
        "projection_version": PROJECTION_VERSION,
        "session_id": "direct-session",
        "contract_id": "direct-contract",
        "as_of_message_hash": partial[-1]["message_hash"],
        "session_status": "OPEN",
        "selected_aicp_profiles": [BASE],
        "profile_composition_hash": proposal["payload"][
            "negotiation_result"
        ]["selected"]["profile_composition_hash"],
        "accepted_negotiation_result_hash": proposal["payload"][
            "negotiation_result_hash"
        ],
        "participant_refs": PARTIES,
        "active_extensions": [],
    }
    projection_message = _message(
        partial,
        "STATE_SYNC_RESPONSE",
        PARTIES[1],
        {
            "request_id": "direct-projection",
            "session_state": projection,
            "session_state_hash": object_hash(
                "session_state_projection", projection
            ),
            "branch_heads": [],
        },
    )
    partial.append(projection_message)
    _rehash(partial)
    projection_codes = validate_session_state_projection_v2(
        partial[-1],
        partial,
        len(partial) - 1,
        registered_extensions=EXTENSIONS,
        rules=RULES,
        registered_reason_codes=REASONS,
        key_map=KEYS,
    )
    assert [item["code"] for item in projection_codes] == [
        "PROJECTION_ACCEPTANCE_NOT_ESTABLISHED",
        "PROJECTION_PROFILE_SET_MISMATCH",
        "PROJECTION_ACCEPTED_RESULT_HASH_MISMATCH",
    ]

    invalid_contract, _ = direct_transcript(
        accept_senders=(PARTIES[0], PARTIES[1])
    )
    invalid_contract.append(
        _message(
            invalid_contract,
            "CONTRACT_PROPOSE",
            PARTIES[0],
            {
                "contract": {
                    "contract_id": "direct-contract",
                    "ext": {
                        "capneg_v2": {
                            "capneg_version": "0.2",
                            "negotiation_id": "direct-root",
                            "negotiation_result_hash": invalid_contract[2][
                                "payload"
                            ]["negotiation_result_hash"],
                            "profile_composition": {
                                "composition_version": "aicp.profile_composition.v1",
                                "profiles": [BASE],
                            },
                            "profile_composition_hash": invalid_contract[2][
                                "payload"
                            ]["negotiation_result"]["selected"][
                                "profile_composition_hash"
                            ],
                        }
                    },
                }
            },
        )
    )
    _rehash(invalid_contract)
    invalid, _ = validate_messages(
        invalid_contract,
        message_schema=load("schemas/core/aicp-core-message.schema.json"),
        capneg_schema=load(
            "schemas/extensions/ext-capneg-v0.2-payloads.schema.json"
        ),
        projection_schema=load(
            "schemas/extensions/session-state-projection-v2.schema.json"
        ),
        core_payload_schema=load("schemas/core/aicp-core-payloads.schema.json"),
        core_contract_schema=load(
            "schemas/core/aicp-core-contract.schema.json"
        ),
        registered_messages=MESSAGES,
        key_map=KEYS,
        jsonschema_available=True,
        crypto_available=True,
    )
    assert [item["code"] for item in invalid[len(invalid_contract) - 1]] == [
        "CORE_CONTRACT_SCHEMA_INVALID"
    ]

    unlinked, _ = direct_transcript(
        accept_senders=(PARTIES[0], PARTIES[1])
    )
    append_successor(
        unlinked,
        negotiation_id="direct-unlinked",
        supersedes=None,
    )
    assert errors(unlinked) == ["NEGOTIATION_SUPERSESSION_REQUIRED"]


def test_successor_replay_is_exact_and_safe_after_supersession() -> None:
    messages, _ = direct_transcript(
        accept_senders=(PARTIES[0], PARTIES[1])
    )
    successor = append_successor(
        messages,
        negotiation_id="direct-successor",
        supersedes="direct-root",
        accept_senders=(PARTIES[0], PARTIES[1]),
    )
    append_decision(messages, successor, PARTIES[1])
    append_decision(messages, successor, PARTIES[0])
    snapshot = reduce_capneg_v02(
        messages, rules=RULES, registered_reason_codes=REASONS, key_map=KEYS
    )
    assert snapshot["errors"] == []
    assert snapshot["superseded_negotiations"] == ["direct-root"]
    assert snapshot["acceptances"] == PARTIES

    for field, value, code in (
        ("session_id", "other-session", "DECISION_SESSION_MISMATCH"),
        ("contract_id", "other-contract", "DECISION_CONTRACT_MISMATCH"),
    ):
        mutated = copy.deepcopy(messages[:-2])
        replay = append_decision(mutated, successor, PARTIES[1])
        replay[field] = value
        assert code in errors(mutated)

    changed_hash = copy.deepcopy(messages[:-2])
    replay = append_decision(changed_hash, successor, PARTIES[1])
    replay["payload"]["negotiation_result_hash"] = "sha256:" + "A" * 43
    assert "ACCEPTANCE_RESULT_HASH_MISMATCH" in errors(changed_hash)

    invalid_signature = copy.deepcopy(messages[:-2])
    replay = append_decision(invalid_signature, successor, PARTIES[1])
    replay["signatures"] = [
        {
            **_signature(replay["message_hash"], PARTIES[1]),
            "sig_b64url": "A" * 86,
        }
    ]
    assert "ACCEPTANCE_SIGNATURE_INVALID" in errors(invalid_signature)


def test_predecessor_superseded_by_another_successor_rejects_decisions() -> None:
    messages, _ = direct_transcript(
        accept_senders=(PARTIES[0], PARTIES[1])
    )
    successor_a = append_successor(
        messages,
        negotiation_id="successor-a",
        supersedes="direct-root",
    )
    successor_b = append_successor(
        messages,
        negotiation_id="successor-b",
        supersedes="direct-root",
    )
    append_decision(messages, successor_a, PARTIES[0])
    append_decision(messages, successor_a, PARTIES[1])
    append_decision(messages, successor_b, PARTIES[0])
    assert errors(messages)[-1] == "NEGOTIATION_SUPERSESSION_INVALID"


def test_direct_reducer_crypto_unavailable_is_fail_closed() -> None:
    unsigned_auth, _ = direct_transcript(authenticated=True)
    append_decision(unsigned_auth, unsigned_auth[2], PARTIES[0])
    snapshot = reduce_capneg_v02(
        unsigned_auth,
        rules=RULES,
        registered_reason_codes=REASONS,
        key_map=KEYS,
        crypto_available=False,
    )
    assert snapshot["state"] == "PROPOSED"
    assert snapshot["errors"] == [
        "AUTHENTICATED_ACCEPTANCE_SIGNATURE_REQUIRED"
    ]

    signed_auth, signers = direct_transcript(authenticated=True)
    decision = append_decision(signed_auth, signed_auth[2], PARTIES[0])
    signers[decision["message_id"]] = PARTIES[0]
    _rehash(signed_auth, signers)
    snapshot = reduce_capneg_v02(
        signed_auth,
        rules=RULES,
        registered_reason_codes=REASONS,
        key_map=KEYS,
        crypto_available=False,
    )
    assert snapshot["state"] == "PROPOSED"
    assert snapshot["errors"] == ["CRYPTO_VERIFICATION_UNAVAILABLE"]

    unsigned_base, _ = direct_transcript()
    append_decision(unsigned_base, unsigned_base[2], PARTIES[0])
    snapshot = reduce_capneg_v02(
        unsigned_base,
        rules=RULES,
        registered_reason_codes=REASONS,
        key_map=KEYS,
        crypto_available=False,
    )
    assert snapshot["state"] == "PARTIALLY_ACCEPTED"
    assert snapshot["errors"] == []

    signed_base, signers = direct_transcript()
    decision = append_decision(signed_base, signed_base[2], PARTIES[0])
    signers[decision["message_id"]] = PARTIES[0]
    _rehash(signed_base, signers)
    snapshot = reduce_capneg_v02(
        signed_base,
        rules=RULES,
        registered_reason_codes=REASONS,
        key_map=KEYS,
        crypto_available=False,
    )
    assert snapshot["state"] == "PROPOSED"
    assert snapshot["errors"] == ["CRYPTO_VERIFICATION_UNAVAILABLE"]


def test_ambiguous_accepted_roots_block_contract_and_projection(
    monkeypatch: Any,
) -> None:
    messages, _ = direct_transcript(
        accept_senders=(PARTIES[0], PARTIES[1])
    )
    reducer = CapnegV02Reducer(
        rules=RULES, registered_reason_codes=REASONS, key_map=KEYS
    )
    for index, message in enumerate(messages):
        reducer.apply(message, message_index=index)
    duplicate = copy.deepcopy(reducer.negotiations["direct-root"])
    duplicate["result"]["negotiation_id"] = "corrupt-root"
    reducer.negotiations["corrupt-root"] = duplicate
    contract = {
        "session_id": "direct-session",
        "contract_id": "direct-contract",
        "message_id": "contract",
        "payload": {
            "contract": {
                "ext": {"capneg_v2": {"negotiation_id": "direct-root"}}
            }
        },
    }
    assert [
        item["code"] for item in reducer.validate_contract_binding(contract)
    ] == ["NEGOTIATION_ACCEPTED_ROOT_AMBIGUOUS"]

    import aicp_ref_capneg_v02.state_machine as state_machine

    snapshot = reducer.snapshot(include_internal=True)
    monkeypatch.setattr(
        state_machine, "reduce_capneg_v02", lambda *args, **kwargs: snapshot
    )
    projection = {
        "projection_version": PROJECTION_VERSION,
        "session_id": "direct-session",
        "contract_id": "direct-contract",
        "as_of_message_hash": messages[-1]["message_hash"],
        "session_status": "OPEN",
        "selected_aicp_profiles": [BASE],
        "profile_composition_hash": messages[2]["payload"][
            "negotiation_result"
        ]["selected"]["profile_composition_hash"],
        "accepted_negotiation_result_hash": messages[2]["payload"][
            "negotiation_result_hash"
        ],
        "participant_refs": PARTIES,
        "active_extensions": [],
    }
    projection_message = {
        "session_id": "direct-session",
        "contract_id": "direct-contract",
        "message_id": "projection",
        "payload": {
            "session_state": projection,
            "session_state_hash": object_hash(
                "session_state_projection", projection
            ),
        },
    }
    codes = [
        item["code"]
        for item in validate_session_state_projection_v2(
            projection_message,
            [*messages, projection_message],
            len(messages),
            registered_extensions=EXTENSIONS,
            rules=RULES,
            registered_reason_codes=REASONS,
            key_map=KEYS,
        )
    ]
    assert "NEGOTIATION_ACCEPTED_ROOT_AMBIGUOUS" in codes
