from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from aicp_ref.hashing import object_hash
from aicp_ref.validate import validate_message_signatures

from .profile_composition import (
    COMPOSITION_HASH_DOMAIN,
    canonical_profile_ref_key,
    load_composition_rules,
    resolve_profile_composition,
)


NEGOTIATION_HASH_DOMAIN = "capneg.negotiation_result"
AUTHENTICATED_PROFILE = ("AICP-AUTHENTICATED-BASE", "0.1")
ED25519_PROFILE = "aicp.crypto.ed25519.v1"


def _issue(code: str, detail: str, message: dict[str, Any] | None = None) -> dict[str, Any]:
    issue: dict[str, Any] = {"code": code, "detail": detail}
    if message is not None:
        issue["message_id"] = message.get("message_id")
    return issue


def _is_sorted_unique_strings(values: Any) -> bool:
    return (
        isinstance(values, list)
        and all(isinstance(value, str) and value for value in values)
        and values == sorted(set(values))
    )


def _is_sorted_unique_profiles(values: Any) -> bool:
    return (
        isinstance(values, list)
        and all(
            isinstance(value, dict)
            and set(value) == {"profile_id", "profile_version"}
            and all(isinstance(item, str) and item for item in value.values())
            for value in values
        )
        and values == sorted(values, key=canonical_profile_ref_key)
        and len({canonical_profile_ref_key(value) for value in values}) == len(values)
    )


def _profile_keys(values: Any) -> set[tuple[str, str]]:
    if not isinstance(values, list):
        return set()
    return {canonical_profile_ref_key(value) for value in values}


def _message_binding(message: dict[str, Any]) -> dict[str, Any]:
    payload = message["payload"]
    return {
        "party_id": payload["party_id"],
        "capabilities_id": payload["capabilities_id"],
        "declaration_message_id": message["message_id"],
        "declaration_message_hash": message["message_hash"],
    }


def _negotiation_context_key(
    result: dict[str, Any],
) -> tuple[Any, Any, tuple[str, ...]]:
    participants = result.get("participants")
    canonical_participants = (
        tuple(sorted(participants))
        if isinstance(participants, list)
        and all(isinstance(party, str) for party in participants)
        else ()
    )
    return (
        result.get("session_id"),
        result.get("contract_id"),
        canonical_participants,
    )


def _check_selection_support(
    result: dict[str, Any],
    selected_records: dict[str, dict[str, Any]],
    resolved: dict[str, Any],
) -> list[dict[str, Any]]:
    issues: list[dict[str, Any]] = []
    selected = result.get("selected", {})
    participants = result.get("participants", [])
    selected_profiles = _profile_keys(
        selected.get("profile_composition", {}).get("profiles")
    )
    selected_crypto = set(selected.get("crypto_profiles", []))
    selected_extensions = set(selected.get("required_extensions", []))
    selected_policies = set(selected.get("required_policy_categories", []))

    expected_extensions = set(resolved["required_extensions"])
    expected_policies = set(resolved["required_policy_categories"])
    expected_crypto = set(resolved["required_crypto_profiles"])
    if selected_extensions != expected_extensions:
        issues.append(
            _issue(
                "PROFILE_REQUIREMENTS_MISMATCH",
                "selected.required_extensions must equal the resolved profile requirement union",
            )
        )
    if selected_policies != expected_policies:
        issues.append(
            _issue(
                "PROFILE_REQUIREMENTS_MISMATCH",
                "selected.required_policy_categories must equal the resolved profile requirement union",
            )
        )
    if not expected_crypto <= selected_crypto:
        issues.append(
            _issue(
                "PROFILE_REQUIREMENTS_MISMATCH",
                "selected.crypto_profiles omits a resolved profile requirement",
            )
        )

    for party in participants if isinstance(participants, list) else []:
        declaration = selected_records.get(party, {}).get("payload", {})
        supported_profiles = _profile_keys(
            declaration.get("supported_aicp_profiles")
        )
        required_profiles = _profile_keys(
            declaration.get("required_aicp_profiles", [])
        )
        if not selected_profiles <= supported_profiles:
            issues.append(
                _issue(
                    "PROFILE_SET_UNSUPPORTED",
                    f"{party} does not support every selected exact profile",
                )
            )
        if not required_profiles <= selected_profiles:
            issues.append(
                _issue(
                    "REQUIRED_PROFILE_MISSING",
                    f"composition omits a profile required by {party}",
                )
            )

        if not selected_crypto <= set(
            declaration.get("supported_crypto_profiles", [])
        ):
            issues.append(
                _issue(
                    "PROFILE_REQUIREMENTS_MISMATCH",
                    f"{party} does not support the complete selected crypto set",
                )
            )
        if not set(declaration.get("required_crypto_profiles", [])) <= selected_crypto:
            issues.append(
                _issue(
                    "PARTICIPANT_REQUIRED_CRYPTO_MISSING",
                    f"selected.crypto_profiles omits a crypto profile required by {party}",
                )
            )
        if not selected_extensions <= set(
            declaration.get("supported_extensions", [])
        ):
            issues.append(
                _issue(
                    "PROFILE_REQUIREMENTS_MISMATCH",
                    f"{party} does not support the complete resolved extension set",
                )
            )
        if not selected_policies <= set(
            declaration.get("supported_policy_categories", [])
        ):
            issues.append(
                _issue(
                    "PROFILE_REQUIREMENTS_MISMATCH",
                    f"{party} does not support the complete resolved policy set",
                )
            )
        if selected.get("privacy_mode") not in declaration.get(
            "supported_privacy_modes", []
        ):
            issues.append(
                _issue(
                    "SELECTION_OUTSIDE_DECLARATION",
                    f"{party} does not support selected privacy_mode",
                )
            )
        binding = selected.get("binding")
        if binding is not None and binding not in declaration.get("bindings", []):
            issues.append(
                _issue(
                    "SELECTION_OUTSIDE_DECLARATION",
                    f"{party} does not support selected binding",
                )
            )
        channel_properties = selected.get("channel_properties", {})
        supported_channel = declaration.get("supported_channel_properties", {})
        if isinstance(channel_properties, dict):
            for property_id, selected_value in channel_properties.items():
                supported_value = supported_channel.get(property_id)
                if isinstance(supported_value, list):
                    supported = selected_value in supported_value
                elif isinstance(supported_value, dict) and isinstance(
                    selected_value, int
                ):
                    supported = (
                        supported_value.get("min", selected_value) <= selected_value
                        <= supported_value.get("max", selected_value)
                    )
                else:
                    supported = False
                if not supported:
                    issues.append(
                        _issue(
                            "SELECTION_OUTSIDE_DECLARATION",
                            f"{party} does not support selected channel property {property_id}",
                        )
                    )
        limits = selected.get("limits", {})
        declared_limits = declaration.get("limits", {})
        if isinstance(limits, dict):
            for limit_id, selected_value in limits.items():
                declared_value = declared_limits.get(limit_id)
                if (
                    not isinstance(selected_value, int)
                    or not isinstance(declared_value, int)
                    or selected_value > declared_value
                ):
                    issues.append(
                        _issue(
                            "SELECTION_OUTSIDE_DECLARATION",
                            f"{party} does not support selected limit {limit_id}",
                        )
                    )
    return issues


class CapnegV02Reducer:
    def __init__(
        self,
        *,
        rules: dict[str, Any] | None = None,
        registered_reason_codes: set[str] | None = None,
        key_map: dict[str, Any] | None = None,
        crypto_available: bool = True,
    ) -> None:
        self.rules = rules or load_composition_rules()
        self.registered_reason_codes = registered_reason_codes or set()
        self.key_map = key_map or {}
        self.crypto_available = crypto_available
        self.latest_declarations: dict[str, dict[str, Any]] = {}
        self.capabilities_ids: dict[str, str] = {}
        self.negotiations: dict[str, dict[str, Any]] = {}
        self.active_negotiation_id: str | None = None
        self.issues: list[dict[str, Any]] = []
        self.bound_contracts: list[str] = []
        self.current_message_index: int | None = None

    def _current_accepted_roots(
        self, result: dict[str, Any]
    ) -> list[tuple[str, dict[str, Any]]]:
        context_key = _negotiation_context_key(result)
        return [
            (negotiation_id, negotiation)
            for negotiation_id, negotiation in sorted(self.negotiations.items())
            if negotiation.get("state") == "ACCEPTED"
            and negotiation.get("superseded_by") is None
            and _negotiation_context_key(negotiation.get("result", {}))
            == context_key
        ]

    def _accepted_root_issues(
        self,
        result: dict[str, Any],
        *,
        negotiation_id: str,
        message: dict[str, Any],
    ) -> list[dict[str, Any]]:
        roots = self._current_accepted_roots(result)
        if len(roots) > 1:
            return [
                _issue(
                    "NEGOTIATION_ACCEPTED_ROOT_AMBIGUOUS",
                    "the negotiation context contains more than one current accepted root",
                    message,
                )
            ]
        if not roots or roots[0][0] == negotiation_id:
            return []
        supersedes = result.get("supersedes_negotiation_id")
        if supersedes is None:
            return [
                _issue(
                    "NEGOTIATION_SUPERSESSION_REQUIRED",
                    "a new negotiation in a context with an accepted root must explicitly supersede that exact root",
                    message,
                )
            ]
        if supersedes != roots[0][0]:
            return []
        return []

    def add_issue(
        self, code: str, detail: str, message: dict[str, Any] | None = None
    ) -> None:
        self.issues.append(_issue(code, detail, message))

    def _validate_declaration(
        self, message: dict[str, Any]
    ) -> list[dict[str, Any]]:
        payload = message.get("payload", {})
        issues: list[dict[str, Any]] = []
        party = payload.get("party_id")
        if party != message.get("sender"):
            issues.append(
                _issue(
                    "DECLARATION_PARTY_SENDER_MISMATCH",
                    "declaration party_id must equal envelope sender",
                    message,
                )
            )
        for field in (
            "supported_crypto_profiles",
            "supported_privacy_modes",
            "supported_extensions",
            "supported_policy_categories",
            "required_crypto_profiles",
            "bindings",
            "languages",
        ):
            if field in payload and not _is_sorted_unique_strings(payload[field]):
                issues.append(
                    _issue(
                        "DECLARATION_ARRAY_NON_CANONICAL",
                        f"{field} must be unique and canonically sorted",
                        message,
                    )
                )
        for field in ("supported_aicp_profiles", "required_aicp_profiles"):
            if field in payload and not _is_sorted_unique_profiles(payload[field]):
                issues.append(
                    _issue(
                        "DECLARATION_ARRAY_NON_CANONICAL",
                        f"{field} must be unique and canonically sorted",
                        message,
                    )
                )

        supported_profiles = _profile_keys(
            payload.get("supported_aicp_profiles", [])
        )
        known_profiles = {
            canonical_profile_ref_key(record["profile"])
            for record in self.rules.get("profiles", [])
        }
        if not supported_profiles <= known_profiles:
            issues.append(
                _issue(
                    "PROFILE_UNKNOWN",
                    "declaration contains an unknown exact profile",
                    message,
                )
            )
        if not _profile_keys(payload.get("required_aicp_profiles", [])) <= supported_profiles:
            issues.append(
                _issue(
                    "DECLARATION_REQUIRED_NOT_SUPPORTED",
                    "required_aicp_profiles must be a subset of supported_aicp_profiles",
                    message,
                )
            )
        if not set(payload.get("required_crypto_profiles", [])) <= set(
            payload.get("supported_crypto_profiles", [])
        ):
            issues.append(
                _issue(
                    "DECLARATION_REQUIRED_NOT_SUPPORTED",
                    "required_crypto_profiles must be a subset of supported_crypto_profiles",
                    message,
                )
            )

        capabilities_id = payload.get("capabilities_id")
        prior_party = self.capabilities_ids.get(str(capabilities_id))
        if prior_party is not None:
            issues.append(
                _issue(
                    "DUPLICATE_CAPABILITIES_ID",
                    f"capabilities_id was already declared by {prior_party}",
                    message,
                )
            )
        latest = self.latest_declarations.get(str(party))
        supersedes = payload.get("supersedes_capabilities_id")
        if latest is None and supersedes is not None:
            issues.append(
                _issue(
                    "INVALID_DECLARATION_SUPERSESSION",
                    "first declaration cannot supersede an unknown declaration",
                    message,
                )
            )
        elif latest is not None:
            expected = latest["payload"]["capabilities_id"]
            if supersedes is None:
                issues.append(
                    _issue(
                        "DUPLICATE_PARTY_DECLARATION",
                        "a later declaration must explicitly supersede the latest declaration",
                        message,
                    )
                )
            elif supersedes != expected:
                issues.append(
                    _issue(
                        "INVALID_DECLARATION_SUPERSESSION",
                        f"supersedes_capabilities_id must equal latest {expected}",
                        message,
                    )
                )
        return issues

    def _apply_declaration(self, message: dict[str, Any]) -> None:
        issues = self._validate_declaration(message)
        if issues:
            self.issues.extend(issues)
            return
        payload = message["payload"]
        party = payload["party_id"]
        self.latest_declarations[party] = copy.deepcopy(message)
        self.capabilities_ids[payload["capabilities_id"]] = party

    def _validate_proposal(
        self, message: dict[str, Any]
    ) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
        payload = message.get("payload", {})
        result = payload.get("negotiation_result", {})
        issues: list[dict[str, Any]] = []
        negotiation_id = result.get("negotiation_id")
        revision = payload.get("proposal_revision")

        if revision != result.get("proposal_revision"):
            issues.append(
                _issue(
                    "PROPOSAL_REVISION_RESULT_MISMATCH",
                    "proposal_revision must equal negotiation_result.proposal_revision",
                    message,
                )
            )
        if result.get("session_id") != message.get("session_id"):
            issues.append(
                _issue(
                    "NEGOTIATION_SESSION_MISMATCH",
                    "negotiation_result.session_id must equal envelope session_id",
                    message,
                )
            )
        if result.get("contract_id") != message.get("contract_id"):
            issues.append(
                _issue(
                    "NEGOTIATION_CONTRACT_MISMATCH",
                    "negotiation_result.contract_id must equal envelope contract_id",
                    message,
                )
            )

        participants = result.get("participants")
        if not _is_sorted_unique_strings(participants) or len(participants) < 2:
            issues.append(
                _issue(
                    "PARTICIPANTS_NON_CANONICAL",
                    "participants must be unique, sorted, and contain at least two parties",
                    message,
                )
            )
            participants = participants if isinstance(participants, list) else []
        if message.get("sender") not in participants:
            issues.append(
                _issue(
                    "PROPOSER_NOT_PARTICIPANT",
                    "proposal sender must be a declared participant",
                    message,
                )
            )

        bindings = result.get("declaration_bindings")
        binding_parties = [
            binding.get("party_id")
            for binding in bindings
            if isinstance(binding, dict)
        ] if isinstance(bindings, list) else []
        if (
            not isinstance(bindings, list)
            or binding_parties != sorted(binding_parties)
            or len(set(binding_parties)) != len(binding_parties)
            or set(binding_parties) != set(participants)
        ):
            issues.append(
                _issue(
                    "DECLARATION_BINDING_SET_MISMATCH",
                    "declaration bindings must be canonical and exactly match participants",
                    message,
                )
            )

        selected_declarations: dict[str, dict[str, Any]] = {}
        for binding in bindings if isinstance(bindings, list) else []:
            if not isinstance(binding, dict):
                continue
            party = binding.get("party_id")
            declaration = self.latest_declarations.get(str(party))
            if declaration is None:
                issues.append(
                    _issue(
                        "MISSING_DECLARATION_BINDING",
                        f"no latest valid declaration exists for {party}",
                        message,
                    )
                )
                continue
            expected = _message_binding(declaration)
            if binding != expected:
                issues.append(
                    _issue(
                        "STALE_CAPABILITIES_DECLARATION",
                        f"binding for {party} does not identify its latest valid declaration",
                        message,
                    )
                )
            else:
                selected_declarations[str(party)] = declaration

        composition = result.get("selected", {}).get("profile_composition")
        resolved = resolve_profile_composition(composition, self.rules)
        for error in resolved["errors"]:
            issues.append(_issue(error["code"], error["detail"], message))
        if (
            resolved["composition_hash"] is not None
            and result.get("selected", {}).get("profile_composition_hash")
            != resolved["composition_hash"]
        ):
            issues.append(
                _issue(
                    "PROFILE_COMPOSITION_HASH_MISMATCH",
                    "profile_composition_hash does not match the canonical composition",
                    message,
                )
            )

        try:
            result_hash = object_hash(NEGOTIATION_HASH_DOMAIN, result)
        except Exception as exc:
            issues.append(
                _issue(
                    "NEGOTIATION_RESULT_HASH_MISMATCH",
                    f"negotiation result cannot be hashed: {exc}",
                    message,
                )
            )
            result_hash = None
        if payload.get("negotiation_result_hash") != result_hash:
            issues.append(
                _issue(
                    "NEGOTIATION_RESULT_HASH_MISMATCH",
                    "negotiation_result_hash does not match the exact result",
                    message,
                )
            )

        if not resolved["errors"]:
            issues.extend(
                _check_selection_support(
                    result, selected_declarations, resolved
                )
            )

        existing = self.negotiations.get(str(negotiation_id))
        if existing is None:
            if revision != 1:
                issues.append(
                    _issue(
                        "PROPOSAL_REVISION_INVALID",
                        "a new negotiation must start at proposal revision 1",
                        message,
                    )
                )
            if payload.get("supersedes_proposal_message_id") is not None or payload.get(
                "supersedes_proposal_message_hash"
            ) is not None:
                issues.append(
                    _issue(
                        "PROPOSAL_SUPERSESSION_INVALID",
                        "revision 1 must not bind a prior proposal message",
                        message,
                    )
                )
            supersedes_negotiation_id = result.get("supersedes_negotiation_id")
            issues.extend(
                self._accepted_root_issues(
                    result,
                    negotiation_id=str(negotiation_id),
                    message=message,
                )
            )
            if supersedes_negotiation_id is not None:
                prior_negotiation = self.negotiations.get(supersedes_negotiation_id)
                if (
                    prior_negotiation is None
                    or prior_negotiation.get("state") != "ACCEPTED"
                ):
                    issues.append(
                        _issue(
                            "NEGOTIATION_SUPERSESSION_INVALID",
                            "supersedes_negotiation_id must identify a fully accepted negotiation",
                            message,
                        )
                    )
                else:
                    prior_result = prior_negotiation.get("result", {})
                    if (
                        prior_result.get("session_id") != result.get("session_id")
                        or prior_result.get("contract_id") != result.get("contract_id")
                        or prior_result.get("participants") != result.get("participants")
                    ):
                        issues.append(
                            _issue(
                                "NEGOTIATION_SUPERSESSION_CONTEXT_MISMATCH",
                                "superseding negotiation must preserve session, contract, and exact participants",
                                message,
                            )
                        )
                    if prior_negotiation.get("superseded_by") is not None:
                        issues.append(
                            _issue(
                                "NEGOTIATION_SUPERSESSION_FORK",
                                "an accepted negotiation may be superseded by only one accepted successor",
                                message,
                            )
                        )
        else:
            if existing.get("state") == "ACCEPTED":
                issues.append(
                    _issue(
                        "ACCEPTED_NEGOTIATION_IMMUTABLE",
                        "a fully accepted negotiation cannot be revised under the same ID",
                        message,
                    )
                )
            expected_revision = int(existing.get("current_revision", 0)) + 1
            if revision != expected_revision:
                issues.append(
                    _issue(
                        "PROPOSAL_REVISION_INVALID",
                        f"proposal revision must increase exactly to {expected_revision}",
                        message,
                    )
                )
            if (
                payload.get("supersedes_proposal_message_id")
                != existing.get("proposal_message_id")
                or payload.get("supersedes_proposal_message_hash")
                != existing.get("proposal_message_hash")
            ):
                issues.append(
                    _issue(
                        "PROPOSAL_SUPERSESSION_INVALID",
                        "revision must bind the exact immediately prior proposal",
                        message,
                    )
                )

        context = {
            "negotiation_id": negotiation_id,
            "revision": revision,
            "result": copy.deepcopy(result),
            "result_hash": result_hash,
            "resolved": resolved,
        }
        return issues, context

    def _apply_proposal(self, message: dict[str, Any]) -> None:
        issues, context = self._validate_proposal(message)
        if issues:
            self.issues.extend(issues)
            return
        assert context is not None
        negotiation_id = str(context["negotiation_id"])
        revision = int(context["revision"])
        existing = self.negotiations.get(negotiation_id, {})
        self.negotiations[negotiation_id] = {
            **existing,
            "state": "PROPOSED" if revision == 1 else "REVISION_PROPOSED",
            "current_revision": revision,
            "proposal_message_id": message["message_id"],
            "proposal_message_hash": message["message_hash"],
            "result": context["result"],
            "result_hash": context["result_hash"],
            "resolved": context["resolved"],
            "acceptances": {},
            "rejections": {},
            "accepted_composition": existing.get("accepted_composition"),
            "accepted_result_hash": existing.get("accepted_result_hash"),
            "superseded_by": existing.get("superseded_by"),
        }
        self.active_negotiation_id = negotiation_id

    def _current_negotiation(
        self, message: dict[str, Any]
    ) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
        payload = message.get("payload", {})
        negotiation_id = str(payload.get("negotiation_id"))
        negotiation = self.negotiations.get(negotiation_id)
        issues: list[dict[str, Any]] = []
        if negotiation is None:
            issues.append(
                _issue(
                    "UNKNOWN_PROPOSAL",
                    "acceptance/rejection identifies an unknown negotiation",
                    message,
                )
            )
            return None, issues
        revision = payload.get("proposal_revision")
        current_revision = negotiation.get("current_revision")
        if revision != current_revision:
            issues.append(
                _issue(
                    (
                        "FUTURE_PROPOSAL"
                        if isinstance(revision, int)
                        and isinstance(current_revision, int)
                        and revision > current_revision
                        else "SUPERSEDED_PROPOSAL"
                    ),
                    "acceptance/rejection does not bind the current proposal revision",
                    message,
                )
            )
        if (
            payload.get("proposal_message_id")
            != negotiation.get("proposal_message_id")
            or payload.get("proposal_message_hash")
            != negotiation.get("proposal_message_hash")
        ):
            issues.append(
                _issue(
                    "PROPOSAL_BINDING_MISMATCH",
                    "acceptance/rejection must bind the exact current proposal message",
                    message,
                )
            )
        if payload.get("negotiation_result_hash") != negotiation.get("result_hash"):
            issues.append(
                _issue(
                    "ACCEPTANCE_RESULT_HASH_MISMATCH",
                    "acceptance/rejection result hash must equal the current proposal result hash",
                    message,
                )
            )
        sender = message.get("sender")
        if sender not in negotiation.get("result", {}).get("participants", []):
            issues.append(
                _issue(
                    "ACCEPTOR_NOT_PARTICIPANT",
                    "acceptance/rejection sender must be a participant",
                    message,
                )
            )
        result = negotiation.get("result", {})
        if message.get("session_id") != result.get("session_id"):
            issues.append(
                _issue(
                    "DECISION_SESSION_MISMATCH",
                    "decision envelope session_id must equal the negotiated session_id",
                    message,
                )
            )
        if message.get("contract_id") != result.get("contract_id"):
            issues.append(
                _issue(
                    "DECISION_CONTRACT_MISMATCH",
                    "decision envelope contract_id must equal the negotiated contract_id",
                    message,
                )
            )
        bindings = {
            binding.get("party_id"): binding
            for binding in result.get("declaration_bindings", [])
            if isinstance(binding, dict)
        }
        for party in result.get("participants", []):
            declaration = self.latest_declarations.get(str(party))
            if declaration is None or bindings.get(party) != _message_binding(declaration):
                issues.append(
                    _issue(
                        "STALE_CAPABILITIES_DECLARATION",
                        f"decision binding for {party} is not the latest valid declaration",
                        message,
                    )
                )
        supersedes = result.get("supersedes_negotiation_id")
        issues.extend(
            self._accepted_root_issues(
                result,
                negotiation_id=str(payload.get("negotiation_id")),
                message=message,
            )
        )
        if supersedes is not None:
            prior = self.negotiations.get(str(supersedes))
            prior_is_current_root = (
                prior is not None
                and prior.get("state") == "ACCEPTED"
                and prior.get("superseded_by") is None
            )
            prior_is_replay_safe = (
                prior is not None
                and prior.get("state") == "SUPERSEDED"
                and prior.get("superseded_by")
                == result.get("negotiation_id")
            )
            if not (prior_is_current_root or prior_is_replay_safe):
                issues.append(
                    _issue(
                        "NEGOTIATION_SUPERSESSION_INVALID",
                        "the predecessor must be the current accepted root or be superseded by this exact successor",
                        message,
                    )
                )
            elif _negotiation_context_key(prior.get("result", {})) != (
                _negotiation_context_key(result)
            ):
                issues.append(
                    _issue(
                        "NEGOTIATION_SUPERSESSION_CONTEXT_MISMATCH",
                        "successor replay must preserve session, contract, and exact participants",
                        message,
                    )
                )
        return negotiation, issues

    def _signature_issues(
        self,
        message: dict[str, Any],
        *,
        required: bool,
    ) -> list[dict[str, Any]]:
        signatures = message.get("signatures")
        if not self.crypto_available:
            if required and (not isinstance(signatures, list) or not signatures):
                return [
                    _issue(
                        "AUTHENTICATED_ACCEPTANCE_SIGNATURE_REQUIRED",
                        "Authenticated Base acceptance requires a sender signature",
                        message,
                    )
                ]
            if not isinstance(signatures, list) or not signatures:
                return []
            return [
                _issue(
                    "CRYPTO_VERIFICATION_UNAVAILABLE",
                    "Ed25519 signature verification is unavailable",
                    message,
                )
            ]
        issues: list[dict[str, Any]] = []
        for signature_issue in validate_message_signatures(
            message,
            self.key_map,
            verify_crypto=True,
            require_signatures=required,
            require_sender_signature=required,
        ):
            code = (
                "AUTHENTICATED_ACCEPTANCE_SIGNATURE_REQUIRED"
                if signature_issue["code"]
                in {"signatures_required", "sender_signature_required"}
                else "ACCEPTANCE_SIGNATURE_INVALID"
            )
            issues.append(
                _issue(
                    code,
                    signature_issue["message"],
                    message,
                )
            )
        return issues

    def _apply_accept(self, message: dict[str, Any]) -> None:
        negotiation, issues = self._current_negotiation(message)
        if negotiation is None:
            self.issues.extend(issues)
            return
        selected_profiles = _profile_keys(
            negotiation["result"]["selected"]["profile_composition"]["profiles"]
        )
        issues.extend(
            self._signature_issues(
                message, required=AUTHENTICATED_PROFILE in selected_profiles
            )
        )
        sender = str(message.get("sender"))
        if negotiation.get("state") == "REJECTED":
            issues.append(
                _issue(
                    "REVISION_REJECTED",
                    "a rejected proposal revision cannot accept further decisions",
                    message,
                )
            )
        if sender in negotiation.get("rejections", {}):
            issues.append(
                _issue(
                    "PARTICIPANT_DECISION_CONFLICT",
                    "a participant cannot accept a revision it already rejected",
                    message,
                )
            )
        prior = negotiation.get("acceptances", {}).get(sender)
        if prior is not None:
            current_payload = message.get("payload", {})
            if prior.get("payload") == current_payload and not issues:
                return
            if prior.get("payload") != current_payload:
                issues.append(
                    _issue(
                        "ACCEPTANCE_REPLAY_RETARGETED",
                        "participant acceptance replay changed its exact proposal binding",
                        message,
                    )
                )
        if issues:
            self.issues.extend(issues)
            return

        negotiation["acceptances"][sender] = copy.deepcopy(message)
        participants = set(negotiation["result"]["participants"])
        accepted_participants = set(negotiation["acceptances"])
        if accepted_participants == participants:
            negotiation["state"] = "ACCEPTED"
            negotiation["accepted_composition"] = copy.deepcopy(
                negotiation["result"]["selected"]["profile_composition"]
            )
            negotiation["accepted_result_hash"] = negotiation["result_hash"]
            supersedes = negotiation["result"].get("supersedes_negotiation_id")
            if supersedes is not None and supersedes in self.negotiations:
                self.negotiations[supersedes]["state"] = "SUPERSEDED"
                self.negotiations[supersedes]["superseded_by"] = negotiation[
                    "result"
                ]["negotiation_id"]
        else:
            negotiation["state"] = "PARTIALLY_ACCEPTED"

    def _apply_reject(self, message: dict[str, Any]) -> None:
        negotiation, issues = self._current_negotiation(message)
        if negotiation is None:
            self.issues.extend(issues)
            return
        sender = str(message.get("sender"))
        reason = message.get("payload", {}).get("reason_code")
        if (
            reason not in self.registered_reason_codes
            and not (
                isinstance(reason, str)
                and (
                    reason.startswith("vendor:")
                    or reason.startswith("org:")
                    or reason.startswith("x-")
                )
            )
        ):
            issues.append(
                _issue(
                    "REJECTION_REASON_UNREGISTERED",
                    "reason_code must be registered or explicitly namespaced",
                    message,
                )
            )
        if sender in negotiation.get("acceptances", {}):
            issues.append(
                _issue(
                    "PARTICIPANT_DECISION_CONFLICT",
                    "a participant cannot reject a revision it already accepted",
                    message,
                )
            )
        constraints = message.get("payload", {}).get(
            "alternative_constraints"
        )
        if isinstance(constraints, dict):
            for field in (
                "required_crypto_profiles",
                "required_extensions",
                "required_policy_categories",
                "acceptable_bindings",
            ):
                if field in constraints and not _is_sorted_unique_strings(
                    constraints[field]
                ):
                    issues.append(
                        _issue(
                            "REJECTION_ALTERNATIVE_CONSTRAINTS_INVALID",
                            f"{field} must be unique and canonically sorted",
                            message,
                        )
                    )
            if (
                "required_aicp_profiles" in constraints
                and not _is_sorted_unique_profiles(
                    constraints["required_aicp_profiles"]
                )
            ):
                issues.append(
                    _issue(
                        "REJECTION_ALTERNATIVE_CONSTRAINTS_INVALID",
                        "required_aicp_profiles must be unique and canonically sorted",
                        message,
                    )
                )
        prior = negotiation.get("rejections", {}).get(sender)
        if prior is not None:
            if prior.get("payload") == message.get("payload"):
                if issues:
                    self.issues.extend(issues)
                return
            issues.append(
                _issue(
                    "REJECTION_REPLAY_RETARGETED",
                    "duplicate rejection changed its exact decision identity",
                    message,
                )
            )
        for alternative in message.get("payload", {}).get(
            "alternative_profile_compositions", []
        ):
            resolved = resolve_profile_composition(alternative, self.rules)
            if resolved["errors"]:
                issues.append(
                    _issue(
                        "REJECTION_ALTERNATIVE_INVALID",
                        "alternative profile composition is not canonical and valid",
                        message,
                    )
                )
            supported = _profile_keys(
                self.latest_declarations.get(sender, {})
                .get("payload", {})
                .get("supported_aicp_profiles", [])
            )
            declaration = (
                self.latest_declarations.get(sender, {}).get("payload", {})
            )
            if not _profile_keys(alternative.get("profiles", [])) <= supported:
                issues.append(
                    _issue(
                        "REJECTION_ALTERNATIVE_UNSUPPORTED",
                        "rejecting participant does not support its alternative composition",
                        message,
                    )
                )
            required_profiles = _profile_keys(
                declaration.get("required_aicp_profiles", [])
            )
            constraints = message.get("payload", {}).get(
                "alternative_constraints", {}
            )
            constraint_crypto = (
                set(constraints.get("required_crypto_profiles", []))
                if isinstance(constraints, dict)
                else set()
            )
            available_crypto = set(resolved.get("required_crypto_profiles", []))
            available_crypto.update(constraint_crypto)
            if (
                not required_profiles
                <= _profile_keys(alternative.get("profiles", []))
                or not set(declaration.get("required_crypto_profiles", []))
                <= available_crypto
            ):
                issues.append(
                    _issue(
                        "REJECTION_ALTERNATIVE_REQUIREMENTS_UNMET",
                        "alternative must preserve the rejecting participant's profile and crypto minimums",
                        message,
                    )
                )
        if issues:
            self.issues.extend(issues)
            return
        negotiation["rejections"][sender] = copy.deepcopy(message)
        negotiation["state"] = "REJECTED"

    def apply(
        self,
        message: dict[str, Any],
        *,
        message_index: int | None = None,
        message_valid: bool = True,
        invalid_issues: list[dict[str, Any]] | None = None,
    ) -> None:
        before = len(self.issues)
        self.current_message_index = message_index
        if not message_valid:
            if invalid_issues:
                self.issues.extend(copy.deepcopy(invalid_issues))
            else:
                self.add_issue(
                    "MESSAGE_VALIDITY_BARRIER",
                    "invalid message did not mutate CAPNEG v0.2 state",
                    message,
                )
            self._annotate_new_issues(before, message, message_index)
            return
        message_type = message.get("message_type")
        if message_type == "CONTRACT_PROPOSE":
            self.issues.extend(self.validate_contract_binding(message))
            self._annotate_new_issues(before, message, message_index)
            return
        if message_type not in {
            "CAPABILITIES_DECLARE",
            "CAPABILITIES_PROPOSE",
            "CAPABILITIES_ACCEPT",
            "CAPABILITIES_REJECT",
        }:
            self._annotate_new_issues(before, message, message_index)
            return
        if message.get("payload", {}).get("capneg_version") != "0.2":
            self.add_issue(
                "CAPNEG_VERSION_MISMATCH",
                "CAPNEG v0.2 reducer accepts only capneg_version 0.2",
                message,
            )
            self._annotate_new_issues(before, message, message_index)
            return
        if message_type == "CAPABILITIES_DECLARE":
            self._apply_declaration(message)
        elif message_type == "CAPABILITIES_PROPOSE":
            self._apply_proposal(message)
        elif message_type == "CAPABILITIES_ACCEPT":
            self._apply_accept(message)
        else:
            self._apply_reject(message)
        self._annotate_new_issues(before, message, message_index)

    def _annotate_new_issues(
        self,
        start: int,
        message: dict[str, Any],
        message_index: int | None,
    ) -> None:
        for item in self.issues[start:]:
            item.setdefault("message_index", message_index)
            item.setdefault(
                "message_id",
                message.get("message_id")
                if isinstance(message.get("message_id"), str)
                else None,
            )

    def validate_contract_binding(
        self, message: dict[str, Any]
    ) -> list[dict[str, Any]]:
        payload = message.get("payload", {})
        contract = payload.get("contract", {})
        binding = contract.get("ext", {}).get("capneg_v2")
        issues: list[dict[str, Any]] = []
        if not isinstance(binding, dict):
            return [
                _issue(
                    "CONTRACT_BINDING_MISSING",
                    "contract.ext.capneg_v2 is required",
                    message,
                )
            ]
        negotiation_id = binding.get("negotiation_id")
        negotiation = self.negotiations.get(str(negotiation_id))
        if negotiation is not None and negotiation.get("state") == "SUPERSEDED":
            issues.append(
                _issue(
                    "CONTRACT_BINDING_SUPERSEDED",
                    "a superseded negotiation result cannot activate a contract",
                    message,
                )
            )
            return issues
        if negotiation is not None:
            roots = self._current_accepted_roots(negotiation.get("result", {}))
            if len(roots) > 1:
                issues.append(
                    _issue(
                        "NEGOTIATION_ACCEPTED_ROOT_AMBIGUOUS",
                        "contract binding cannot resolve an ambiguous accepted root",
                        message,
                    )
                )
                return issues
            if len(roots) == 1 and roots[0][0] != str(negotiation_id):
                issues.append(
                    _issue(
                        "CONTRACT_BINDING_ACCEPTANCE_INCOMPLETE",
                        "contract binding must identify the exact current accepted root",
                        message,
                    )
                )
                return issues
        if negotiation is None or negotiation.get("state") != "ACCEPTED":
            issues.append(
                _issue(
                    "CONTRACT_BINDING_ACCEPTANCE_INCOMPLETE",
                    "contract binding requires a fully accepted current negotiation",
                    message,
                )
            )
            return issues
        result = negotiation["result"]
        if result.get("session_id") != message.get("session_id") or result.get(
            "contract_id"
        ) != message.get("contract_id"):
            issues.append(
                _issue(
                    "CONTRACT_BINDING_CONTEXT_MISMATCH",
                    "contract binding session and contract must match the accepted result",
                    message,
                )
            )
        expected_composition = negotiation["accepted_composition"]
        if binding.get("capneg_version") != "0.2":
            issues.append(
                _issue(
                    "CONTRACT_BINDING_SUBSTITUTION",
                    "contract binding capneg_version must equal 0.2",
                    message,
                )
            )
        if binding.get("negotiation_result_hash") != negotiation.get(
            "accepted_result_hash"
        ):
            issues.append(
                _issue(
                    "CONTRACT_BINDING_SUBSTITUTION",
                    "contract negotiation_result_hash does not match the accepted result",
                    message,
                )
            )
        if binding.get("profile_composition") != expected_composition:
            issues.append(
                _issue(
                    "CONTRACT_BINDING_SUBSTITUTION",
                    "contract profile composition does not equal the accepted composition",
                    message,
                )
            )
        try:
            expected_hash = object_hash(
                COMPOSITION_HASH_DOMAIN, binding.get("profile_composition")
            )
        except Exception:
            expected_hash = None
        if (
            binding.get("profile_composition_hash") != expected_hash
            or binding.get("profile_composition_hash")
            != negotiation["result"]["selected"]["profile_composition_hash"]
        ):
            issues.append(
                _issue(
                    "CONTRACT_BINDING_SUBSTITUTION",
                    "contract profile_composition_hash does not match the accepted composition",
                    message,
                )
            )
        if not issues:
            self.bound_contracts.append(str(message.get("contract_id")))
        return issues

    def snapshot(self, *, include_internal: bool = False) -> dict[str, Any]:
        active = (
            self.negotiations.get(self.active_negotiation_id)
            if self.active_negotiation_id is not None
            else None
        )
        snapshot = {
            "state": active.get("state") if active else "COLLECTING_DECLARATIONS",
            "latest_declarations": [
                _message_binding(self.latest_declarations[party])
                for party in sorted(self.latest_declarations)
            ],
            "negotiation_id": self.active_negotiation_id,
            "current_revision": active.get("current_revision") if active else None,
            "proposal_message_id": active.get("proposal_message_id") if active else None,
            "acceptances": sorted(active.get("acceptances", {})) if active else [],
            "rejections": sorted(active.get("rejections", {})) if active else [],
            "accepted_profile_composition": (
                copy.deepcopy(active.get("accepted_composition"))
                if active
                else None
            ),
            "accepted_result_hash": (
                active.get("accepted_result_hash") if active else None
            ),
            "superseded_negotiations": sorted(
                negotiation_id
                for negotiation_id, negotiation in self.negotiations.items()
                if negotiation.get("state") == "SUPERSEDED"
            ),
            "bound_contracts": sorted(set(self.bound_contracts)),
            "negotiations": [
                {
                    "negotiation_id": negotiation_id,
                    "state": negotiation.get("state"),
                    "current_revision": negotiation.get("current_revision"),
                    "proposal_message_id": negotiation.get("proposal_message_id"),
                    "acceptances": sorted(negotiation.get("acceptances", {})),
                    "rejections": sorted(negotiation.get("rejections", {})),
                    "accepted_profile_composition": copy.deepcopy(
                        negotiation.get("accepted_composition")
                    ),
                    "accepted_result_hash": negotiation.get("accepted_result_hash"),
                    "superseded_by": negotiation.get("superseded_by"),
                }
                for negotiation_id, negotiation in sorted(self.negotiations.items())
            ],
            "issues": copy.deepcopy(self.issues),
            "errors": [issue["code"] for issue in self.issues],
        }
        if include_internal:
            snapshot["_negotiation_contexts"] = {
                negotiation_id: {
                    "session_id": negotiation.get("result", {}).get("session_id"),
                    "contract_id": negotiation.get("result", {}).get("contract_id"),
                    "participants": copy.deepcopy(
                        negotiation.get("result", {}).get("participants", [])
                    ),
                }
                for negotiation_id, negotiation in self.negotiations.items()
            }
        return snapshot


def reduce_capneg_v02(
    messages: list[dict[str, Any]],
    *,
    rules: dict[str, Any] | None = None,
    registered_reason_codes: set[str] | None = None,
    key_map: dict[str, Any] | None = None,
    crypto_available: bool = True,
    invalid_messages: dict[int, list[dict[str, Any]]] | None = None,
    include_internal: bool = False,
) -> dict[str, Any]:
    reducer = CapnegV02Reducer(
        rules=rules,
        registered_reason_codes=registered_reason_codes,
        key_map=key_map,
        crypto_available=crypto_available,
    )
    invalid_messages = invalid_messages or {}
    for index, message in enumerate(messages):
        reducer.apply(
            message,
            message_index=index,
            message_valid=index not in invalid_messages,
            invalid_issues=invalid_messages.get(index),
        )
    return reducer.snapshot(include_internal=include_internal)
