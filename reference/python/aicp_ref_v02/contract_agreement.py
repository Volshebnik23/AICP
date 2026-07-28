from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Sequence

from aicp_ref.hashing import object_hash
from aicp_ref.jcs import canonicalize_json


HASH_RE = re.compile(r"^sha256:[A-Za-z0-9_-]{43}$")

CONTRACT_SCHEMA = "CT2-CONTRACT-SCHEMA-01"
CONTRACT_ID = "CT2-CONTRACT-ID-01"
CONTRACT_HASH = "CT2-CONTRACT-HASH-01"
CONTRACT_REF = "CT2-CONTRACT-REF-01"
PROPOSAL_BINDING = "CT2-PROPOSAL-BINDING-01"
ACCEPT_BINDING = "CT2-ACCEPT-BINDING-01"
ACTIVE_HEAD = "CT2-ACTIVE-HEAD-01"
CONTEXT_BINDING = "CT2-CONTEXT-BINDING-01"
CONFLICT_BINDING = "CT2-CONFLICT-BINDING-01"
AGREEMENT_STATE = "CT2-AGREEMENT-STATE-01"

CHECK_IDS = (
    CONTRACT_SCHEMA,
    CONTRACT_ID,
    CONTRACT_HASH,
    CONTRACT_REF,
    PROPOSAL_BINDING,
    ACCEPT_BINDING,
    ACTIVE_HEAD,
    CONTEXT_BINDING,
    CONFLICT_BINDING,
    AGREEMENT_STATE,
)


@dataclass(frozen=True)
class AgreementIssue:
    code: str
    message: str
    index: int

    def as_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "index": self.index}


@dataclass(frozen=True)
class ProposalRecord:
    message_id: str
    message_hash: str
    contract_id: str
    contract: dict[str, Any]
    contract_hash: str
    contract_ref: dict[str, Any]
    index: int

    def binding(self) -> dict[str, Any]:
        return {
            "proposal_message_id": self.message_id,
            "proposal_message_hash": self.message_hash,
            "contract_hash": self.contract_hash,
            "contract_ref": copy.deepcopy(self.contract_ref),
        }


@dataclass
class AgreementState:
    state: str = "NO_ACTIVE_CONTRACT"
    session_id: str | None = None
    contract_id: str | None = None
    active_head: dict[str, Any] | None = None
    proposals: dict[str, ProposalRecord] = field(default_factory=dict)
    proposals_by_hash: dict[str, ProposalRecord] = field(default_factory=dict)
    acceptance_tuples: set[str] = field(default_factory=set)
    rejected_tuples: set[str] = field(default_factory=set)
    issues: list[AgreementIssue] = field(default_factory=list)
    selected_conflict_result: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "session_id": self.session_id,
            "contract_id": self.contract_id,
            "active_head": copy.deepcopy(self.active_head),
            "proposal_ids": sorted(self.proposals),
            "proposal_hashes": sorted(self.proposals_by_hash),
            "accepted_tuple_count": len(self.acceptance_tuples),
            "rejected_tuple_count": len(self.rejected_tuples),
            "selected_conflict_result": copy.deepcopy(self.selected_conflict_result),
            "issues": [issue.as_dict() for issue in self.issues],
        }


def compute_contract_hash(contract: dict[str, Any]) -> str:
    return object_hash("contract", contract)


def _version_hash_errors(value: Any, label: str) -> list[str]:
    if not isinstance(value, dict):
        return [f"{label} must be an object"]
    if set(value) != {"version", "contract_hash"}:
        return [f"{label} must contain only version and contract_hash"]
    version = value.get("version")
    contract_hash = value.get("contract_hash")
    errors: list[str] = []
    if not isinstance(version, str) or not version:
        errors.append(f"{label}.version must be a non-empty opaque identifier")
    if not isinstance(contract_hash, str) or HASH_RE.fullmatch(contract_hash) is None:
        errors.append(f"{label}.contract_hash must use AICP sha256 syntax")
    return errors


def validate_contract_reference(reference: Any) -> list[str]:
    if not isinstance(reference, dict):
        return ["contract_ref must be an object"]
    if not {"branch_id", "head"}.issubset(reference):
        return ["contract_ref requires branch_id and head"]
    if set(reference) - {"branch_id", "base", "head"}:
        return ["contract_ref contains unsupported properties"]

    errors: list[str] = []
    branch_id = reference.get("branch_id")
    if not isinstance(branch_id, str) or not branch_id:
        errors.append("contract_ref.branch_id must be a non-empty string")
    errors.extend(_version_hash_errors(reference.get("head"), "contract_ref.head"))
    if "base" in reference:
        errors.extend(_version_hash_errors(reference.get("base"), "contract_ref.base"))
        if not errors and reference["base"] == reference["head"]:
            errors.append("contract_ref transition base and head must differ")
    return errors


def current_head_reference(contract_reference: dict[str, Any]) -> dict[str, Any]:
    return {
        "branch_id": contract_reference["branch_id"],
        "head": copy.deepcopy(contract_reference["head"]),
    }


def build_proposal_binding(
    contract: dict[str, Any],
    *,
    branch_id: str = "main",
    base: dict[str, Any] | None = None,
) -> dict[str, Any]:
    contract_hash = compute_contract_hash(contract)
    reference: dict[str, Any] = {
        "branch_id": branch_id,
        "head": {
            "version": contract["contract_version"],
            "contract_hash": contract_hash,
        },
    }
    if base is not None:
        if set(base) == {"branch_id", "head"}:
            if base["branch_id"] != branch_id:
                raise ValueError("proposal branch_id must match the active branch")
            reference["base"] = copy.deepcopy(base["head"])
        else:
            reference["base"] = copy.deepcopy(base)
    errors = validate_contract_reference(reference)
    if errors:
        raise ValueError("; ".join(errors))
    return {"contract_hash": contract_hash, "contract_ref": reference}


def build_acceptance_binding(
    proposal_message: dict[str, Any],
    *,
    accepted: bool,
    replay: bool = False,
) -> dict[str, Any]:
    if proposal_message.get("message_type") != "CONTRACT_PROPOSE":
        raise ValueError("acceptance binding requires a CONTRACT_PROPOSE message")
    payload = proposal_message.get("payload")
    if not isinstance(payload, dict):
        raise ValueError("proposal payload must be an object")
    result = {
        "accepted": accepted,
        "proposal_message_id": proposal_message["message_id"],
        "proposal_message_hash": proposal_message["message_hash"],
        "contract_hash": payload["contract_hash"],
    }
    if replay:
        result["replay"] = True
    return result


def proposal_candidate(proposal_message: dict[str, Any]) -> dict[str, Any]:
    payload = proposal_message["payload"]
    return {
        "proposal_message_id": proposal_message["message_id"],
        "proposal_message_hash": proposal_message["message_hash"],
        "contract_hash": payload["contract_hash"],
        "contract_ref": copy.deepcopy(proposal_message["contract_ref"]),
    }


def choose_resolution(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "type": "CHOOSE",
        "selected_proposal_message_id": candidate["proposal_message_id"],
        "selected_proposal_message_hash": candidate["proposal_message_hash"],
        "selected_contract_hash": candidate["contract_hash"],
        "selected_contract_ref": copy.deepcopy(candidate["contract_ref"]),
    }


def _tuple_key(
    accepted: Any,
    proposal_message_id: Any,
    proposal_message_hash: Any,
    contract_hash: Any,
    contract_ref: Any,
) -> str:
    return canonicalize_json(
        {
            "accepted": accepted,
            "proposal_message_id": proposal_message_id,
            "proposal_message_hash": proposal_message_hash,
            "contract_hash": contract_hash,
            "contract_ref": contract_ref,
        }
    )


class ExactAgreementMachine:
    def __init__(self, messages: Sequence[dict[str, Any]]):
        self.messages = messages
        self.state = AgreementState()
        self._message_index = {
            message.get("message_id"): index
            for index, message in enumerate(messages)
            if isinstance(message.get("message_id"), str)
        }
        self._message_types = {
            message.get("message_id"): message.get("message_type")
            for message in messages
            if isinstance(message.get("message_id"), str)
        }

    def _issue(self, code: str, message: str, index: int) -> None:
        if any(
            issue.code == code and issue.index == index and issue.message == message
            for issue in self.state.issues
        ):
            return
        self.state.issues.append(AgreementIssue(code, message, index))

    def _check_transcript_identity(self, message: dict[str, Any], index: int) -> None:
        session_id = message.get("session_id")
        contract_id = message.get("contract_id")
        if index == 0:
            self.state.session_id = session_id if isinstance(session_id, str) else None
            self.state.contract_id = contract_id if isinstance(contract_id, str) else None
            return
        if session_id != self.state.session_id:
            self._issue(AGREEMENT_STATE, "session_id changed within Core v0.2 transcript", index)
        if contract_id != self.state.contract_id:
            self._issue(CONTRACT_ID, "contract_id changed within Core v0.2 transcript", index)

    def _valid_reference(self, reference: Any, index: int, code: str = CONTRACT_REF) -> bool:
        errors = validate_contract_reference(reference)
        if errors:
            self._issue(code, "; ".join(errors), index)
            return False
        return True

    def _process_proposal(self, message: dict[str, Any], index: int) -> None:
        before = len(self.state.issues)
        payload = message.get("payload")
        if not isinstance(payload, dict):
            self._issue(CONTRACT_SCHEMA, "proposal payload must be an object", index)
            return
        contract = payload.get("contract")
        if not isinstance(contract, dict):
            self._issue(CONTRACT_SCHEMA, "payload.contract must be an object", index)
            return

        envelope_contract_id = message.get("contract_id")
        if contract.get("contract_id") != envelope_contract_id:
            self._issue(CONTRACT_ID, "envelope contract_id must equal contract.contract_id", index)

        stored_hash = payload.get("contract_hash")
        try:
            computed_hash = compute_contract_hash(contract)
        except Exception as exc:
            self._issue(CONTRACT_HASH, f"contract hash recomputation failed: {exc}", index)
            return
        if stored_hash != computed_hash:
            self._issue(
                CONTRACT_HASH,
                f"contract_hash mismatch (expected {computed_hash}, got {stored_hash})",
                index,
            )

        reference = message.get("contract_ref")
        if not self._valid_reference(reference, index):
            return
        assert isinstance(reference, dict)
        head = reference["head"]
        if head.get("version") != contract.get("contract_version"):
            self._issue(
                PROPOSAL_BINDING,
                "proposal head version must equal contract.contract_version",
                index,
            )
        if head.get("contract_hash") != stored_hash:
            self._issue(
                PROPOSAL_BINDING,
                "proposal head hash must equal payload.contract_hash",
                index,
            )

        active = self.state.active_head
        if active is None:
            if "base" in reference:
                self._issue(
                    PROPOSAL_BINDING,
                    "initial proposal must omit contract_ref.base",
                    index,
                )
        else:
            if (
                reference.get("branch_id") != active.get("branch_id")
                or reference.get("base") != active.get("head")
            ):
                self._issue(
                    PROPOSAL_BINDING,
                    "revision proposal base must equal the exact active head",
                    index,
                )

        if len(self.state.issues) != before:
            return
        message_id = message.get("message_id")
        message_hash = message.get("message_hash")
        if not isinstance(message_id, str) or not isinstance(message_hash, str):
            self._issue(PROPOSAL_BINDING, "proposal message ID/hash must be present", index)
            return
        proposal = ProposalRecord(
            message_id=message_id,
            message_hash=message_hash,
            contract_id=str(envelope_contract_id),
            contract=copy.deepcopy(contract),
            contract_hash=str(stored_hash),
            contract_ref=copy.deepcopy(reference),
            index=index,
        )
        self.state.proposals[message_id] = proposal
        self.state.proposals_by_hash[message_hash] = proposal
        same_base = [
            proposal
            for proposal in self.state.proposals.values()
            if proposal.contract_ref.get("branch_id") == reference.get("branch_id")
            and proposal.contract_ref.get("base") == reference.get("base")
            and proposal.index <= index
        ]
        self.state.state = (
            "COMPETING_CANDIDATES"
            if len(same_base) > 1
            else "CANDIDATE_PROPOSED"
        )

    def _proposal_for_acceptance(
        self, proposal_id: Any, index: int
    ) -> ProposalRecord | None:
        proposal = self.state.proposals.get(proposal_id)
        if proposal is not None:
            return proposal
        position = self._message_index.get(proposal_id)
        if position is not None and position > index:
            self._issue(ACCEPT_BINDING, "acceptance references a future proposal", index)
        elif position is not None and self._message_types.get(proposal_id) != "CONTRACT_PROPOSE":
            self._issue(ACCEPT_BINDING, "acceptance target is not a proposal", index)
        else:
            self._issue(ACCEPT_BINDING, "acceptance references an unknown proposal", index)
        return None

    def _process_acceptance(self, message: dict[str, Any], index: int) -> None:
        payload = message.get("payload")
        if not isinstance(payload, dict):
            self._issue(ACCEPT_BINDING, "acceptance payload must be an object", index)
            return
        reference = message.get("contract_ref")
        if not self._valid_reference(reference, index, ACCEPT_BINDING):
            return
        proposal = self._proposal_for_acceptance(
            payload.get("proposal_message_id"), index
        )
        if proposal is None:
            return

        mismatches: list[str] = []
        if payload.get("proposal_message_hash") != proposal.message_hash:
            mismatches.append("proposal_message_hash")
        if payload.get("contract_hash") != proposal.contract_hash:
            mismatches.append("contract_hash")
        if reference != proposal.contract_ref:
            mismatches.append("contract_ref")
        if message.get("contract_id") != proposal.contract_id:
            mismatches.append("contract_id")
        if mismatches:
            self._issue(
                ACCEPT_BINDING,
                "acceptance does not match proposal fields: " + ", ".join(mismatches),
                index,
            )
            return

        accepted = payload.get("accepted")
        tuple_key = _tuple_key(
            accepted,
            proposal.message_id,
            proposal.message_hash,
            proposal.contract_hash,
            proposal.contract_ref,
        )
        if payload.get("replay") is True:
            known = (
                tuple_key in self.state.acceptance_tuples
                or tuple_key in self.state.rejected_tuples
            )
            if not known:
                self._issue(
                    ACCEPT_BINDING,
                    "replay must repeat one exact prior acceptance tuple",
                    index,
                )
            return

        if accepted is True:
            active = self.state.active_head
            proposal_base = proposal.contract_ref.get("base")
            if active is None:
                if proposal_base is not None:
                    self._issue(
                        ACCEPT_BINDING,
                        "initial accepted proposal must omit base",
                        index,
                    )
                    return
            elif (
                proposal.contract_ref.get("branch_id") != active.get("branch_id")
                or proposal_base != active.get("head")
            ):
                self._issue(
                    ACCEPT_BINDING,
                    "stale proposal base does not equal the current active head",
                    index,
                )
                return
            self.state.active_head = current_head_reference(proposal.contract_ref)
            self.state.acceptance_tuples.add(tuple_key)
            self.state.state = "ACTIVE_HEAD"
        elif accepted is False:
            self.state.rejected_tuples.add(tuple_key)
            self.state.state = (
                "ACTIVE_HEAD"
                if self.state.active_head is not None
                else "NO_ACTIVE_CONTRACT"
            )
        else:
            self._issue(ACCEPT_BINDING, "accepted must be boolean", index)

    def _require_current_head(
        self,
        message: dict[str, Any],
        index: int,
        code: str,
        purpose: str,
    ) -> bool:
        reference = message.get("contract_ref")
        if not self._valid_reference(reference, index, code):
            return False
        if self.state.active_head is None:
            self._issue(code, f"{purpose} requires an active contract head", index)
            return False
        if reference != self.state.active_head:
            self._issue(code, f"{purpose} must bind the exact active head", index)
            return False
        return True

    def _process_context(self, message: dict[str, Any], index: int) -> None:
        payload = message.get("payload")
        if not isinstance(payload, dict) or payload.get("contract_effect") != "none":
            self._issue(
                CONTEXT_BINDING,
                "CONTEXT_AMEND contract_effect must equal 'none'",
                index,
            )
        self._require_current_head(
            message,
            index,
            CONTEXT_BINDING,
            "CONTEXT_AMEND",
        )

    def _process_action(self, message: dict[str, Any], index: int) -> None:
        self._require_current_head(
            message,
            index,
            ACTIVE_HEAD,
            "ATTEST_ACTION",
        )

    def _proposal_for_candidate(
        self, candidate: dict[str, Any], index: int
    ) -> ProposalRecord | None:
        proposal_id = candidate.get("proposal_message_id")
        proposal = self.state.proposals.get(proposal_id)
        if proposal is not None:
            return proposal
        position = self._message_index.get(proposal_id)
        if position is not None and position > index:
            reason = "future"
        elif position is not None and self._message_types.get(proposal_id) != "CONTRACT_PROPOSE":
            reason = "non-proposal"
        else:
            reason = "unknown"
        self._issue(
            CONFLICT_BINDING,
            f"conflict candidate references a {reason} proposal",
            index,
        )
        return None

    def _process_conflict(self, message: dict[str, Any], index: int) -> None:
        before = len(self.state.issues)
        if self.state.active_head is None:
            self._issue(
                CONFLICT_BINDING,
                "conflict resolution requires an active contract head",
                index,
            )
            return
        payload = message.get("payload")
        if not isinstance(payload, dict):
            self._issue(CONFLICT_BINDING, "conflict payload must be an object", index)
            return
        candidates = payload.get("candidates")
        resolution = payload.get("resolution")
        if not isinstance(candidates, list) or not isinstance(resolution, dict):
            self._issue(
                CONFLICT_BINDING,
                "conflict candidates and resolution must be structured",
                index,
            )
            return

        resolved: dict[str, ProposalRecord] = {}
        candidate_by_id: dict[str, dict[str, Any]] = {}
        for candidate in candidates:
            if not isinstance(candidate, dict):
                self._issue(CONFLICT_BINDING, "candidate must be an object", index)
                continue
            proposal_id = candidate.get("proposal_message_id")
            if proposal_id in candidate_by_id:
                self._issue(CONFLICT_BINDING, "duplicate conflict candidate", index)
                continue
            candidate_by_id[str(proposal_id)] = candidate
            proposal = self._proposal_for_candidate(candidate, index)
            if proposal is None:
                continue
            if candidate != proposal.binding():
                self._issue(
                    CONFLICT_BINDING,
                    f"candidate {proposal_id} does not exactly match its proposal",
                    index,
                )
                continue
            if proposal.contract_id != self.state.contract_id:
                self._issue(
                    CONFLICT_BINDING,
                    "cross-contract conflict candidate is forbidden",
                    index,
                )
                continue
            if (
                proposal.contract_ref.get("branch_id")
                != self.state.active_head.get("branch_id")
                or proposal.contract_ref.get("base")
                != self.state.active_head.get("head")
            ):
                self._issue(
                    CONFLICT_BINDING,
                    "all conflict candidates must derive from the exact active base",
                    index,
                )
                continue
            resolved[str(proposal_id)] = proposal

        if resolution.get("type") != "CHOOSE":
            self._issue(CONFLICT_BINDING, "only CHOOSE resolution is supported", index)
            return
        selected_id = resolution.get("selected_proposal_message_id")
        selected = resolved.get(str(selected_id))
        if selected is None:
            self._issue(
                CONFLICT_BINDING,
                "selected proposal is not an exact declared candidate",
                index,
            )
            return
        expected_resolution = choose_resolution(selected.binding())
        if resolution != expected_resolution:
            self._issue(
                CONFLICT_BINDING,
                "selected result fields do not exactly match the candidate",
                index,
            )
            return
        if message.get("contract_ref") != selected.contract_ref:
            self._issue(
                CONFLICT_BINDING,
                "resolution envelope must equal the selected contract reference",
                index,
            )
            return
        if len(self.state.issues) != before:
            return

        self.state.active_head = current_head_reference(selected.contract_ref)
        self.state.selected_conflict_result = copy.deepcopy(expected_resolution)
        self.state.state = "CONFLICT_RESOLVED"

    def _process_error(self, message: dict[str, Any], index: int) -> None:
        reference = message.get("contract_ref")
        if reference is None:
            return
        if not self._valid_reference(reference, index):
            return
        known_targets = [proposal.contract_ref for proposal in self.state.proposals.values()]
        if reference != self.state.active_head and reference not in known_targets:
            self._issue(
                ACTIVE_HEAD,
                "ERROR contract_ref must bind the current or an explicitly known head",
                index,
            )

    def process(self) -> AgreementState:
        handlers = {
            "CONTRACT_PROPOSE": self._process_proposal,
            "CONTRACT_ACCEPT": self._process_acceptance,
            "CONTEXT_AMEND": self._process_context,
            "ATTEST_ACTION": self._process_action,
            "RESOLVE_CONFLICT": self._process_conflict,
            "ERROR": self._process_error,
        }
        for index, message in enumerate(self.messages):
            self._check_transcript_identity(message, index)
            handler = handlers.get(message.get("message_type"))
            if handler is not None:
                handler(message, index)
        return self.state


def reduce_transcript(
    messages: Sequence[dict[str, Any]] | Iterable[dict[str, Any]],
) -> AgreementState:
    rows = list(messages)
    return ExactAgreementMachine(rows).process()


def semantic_issue_ids(messages: Sequence[dict[str, Any]]) -> list[str]:
    return sorted({issue.code for issue in reduce_transcript(messages).issues})


def load_jsonl(text: str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in text.splitlines() if line.strip()]


__all__ = [
    "ACCEPT_BINDING",
    "ACTIVE_HEAD",
    "AGREEMENT_STATE",
    "CHECK_IDS",
    "CONFLICT_BINDING",
    "CONTEXT_BINDING",
    "CONTRACT_HASH",
    "CONTRACT_ID",
    "CONTRACT_REF",
    "CONTRACT_SCHEMA",
    "ExactAgreementMachine",
    "PROPOSAL_BINDING",
    "AgreementIssue",
    "AgreementState",
    "build_acceptance_binding",
    "build_proposal_binding",
    "choose_resolution",
    "compute_contract_hash",
    "current_head_reference",
    "load_jsonl",
    "proposal_candidate",
    "reduce_transcript",
    "semantic_issue_ids",
    "validate_contract_reference",
]
