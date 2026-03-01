# RFC EXT-PARTICIPANTS

## 1. Purpose (normative)
`EXT-PARTICIPANTS` defines deterministic membership and role-handling semantics for multi-party AICP sessions.
It standardizes how participants request to join, how authorized actors accept them, and how membership state gates subsequent message validity.

## 2. Contract configuration (normative)
Implementations MUST read participants configuration from the first `CONTRACT_PROPOSE` payload contract using:

1. `contract.ext.participants`, OR
2. fallback `contract.extensions["EXT-PARTICIPANTS"]`.

Configuration object:
- `model` (REQUIRED): `"shared_contract"` or `"per_participant_acceptance"`.
- `acceptors` (OPTIONAL): array of sender IDs allowed to emit `PARTICIPANT_ACCEPT`.
- `roles_catalog` (OPTIONAL): array of role strings (namespaced values allowed). This is informational/documentation-oriented and not required for enforcement.

## 3. Message types (normative)
- `PARTICIPANT_JOIN`
- `PARTICIPANT_ACCEPT`
- `PARTICIPANT_LEAVE`

### 3.1 `PARTICIPANT_JOIN` semantics (normative)
`PARTICIPANT_JOIN` payload MUST include:
- `participant_id`
- `requested_roles`

### 3.2 `PARTICIPANT_ACCEPT` semantics (normative)
`PARTICIPANT_ACCEPT` payload MUST include:
- `participant_id`
- `granted_roles`

If configuration `acceptors` is present and non-empty, `PARTICIPANT_ACCEPT.sender` MUST be in that allowlist.

### 3.3 `PARTICIPANT_LEAVE` semantics (normative)
`PARTICIPANT_LEAVE` payload MUST include:
- `participant_id`

## 4. Membership gating rules (normative)
For a `participant_id` that appears in `PARTICIPANT_JOIN`:

1. Any subsequent message from `sender == participant_id`, other than `PARTICIPANT_JOIN` / `PARTICIPANT_ACCEPT` / `PARTICIPANT_LEAVE`, MUST NOT appear before `PARTICIPANT_ACCEPT` for that participant.
2. After `PARTICIPANT_LEAVE` for that participant, that sender MUST NOT emit further messages in the transcript.
3. `PARTICIPANT_ACCEPT` MUST refer to a participant that has already joined.

## 5. Contract models (normative)

### 5.1 `shared_contract`
Acceptance is against the session contract as a whole. `accepted_contract_ref` in `PARTICIPANT_ACCEPT` MAY be omitted.

### 5.2 `per_participant_acceptance`
`PARTICIPANT_ACCEPT` MUST include `accepted_contract_ref` with `branch_id`, `base_version`, and `head_version`.
For each subsequent message from that accepted participant (excluding `PARTICIPANT_JOIN` / `PARTICIPANT_ACCEPT` / `PARTICIPANT_LEAVE`), envelope `contract_ref` MUST be present and MUST equal `accepted_contract_ref` exactly.

## 6. Security considerations
- Membership spoofing: bind participant identity to sender and authenticated channel identity.
- Role escalation: only trusted acceptors should grant roles.
- Join spam: implementations SHOULD rate-limit repeated/abusive joins.
