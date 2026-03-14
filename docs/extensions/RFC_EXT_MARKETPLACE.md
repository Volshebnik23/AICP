# RFC_EXT_MARKETPLACE (EXT-MARKETPLACE)

Status: Experimental  
AICP Version: 0.1

## 1. Purpose

`EXT-MARKETPLACE` defines transcript-native request-for-work, bidding, award, auction-mode, blackboard, and subchat orchestration artifacts for bazaar/reception coordination.

## 2. Scope boundaries (normative)

This extension is **not**:
- a hosted marketplace backend,
- a payment rail,
- a bidding/auction runtime engine,
- a provenance/responsibility-transfer layer (M37),
- a spam-detection system.

This extension standardizes content-layer evidence objects/messages only.

## 3. Message types (normative)

- `RFW_POST`
- `BID_SUBMIT`
- `BID_UPDATE`
- `BID_WITHDRAW`
- `AWARD_ISSUE`
- `AWARD_ACCEPT`
- `AWARD_DECLINE`
- `AUCTION_OPEN`
- `AUCTION_CLOSE`
- `BLACKBOARD_DECLARE`
- `BLACKBOARD_POST`
- `BLACKBOARD_UPDATE`
- `BLACKBOARD_REMOVE`
- `SUBCHAT_CREATE`
- `SUBCHAT_INVITE`
- `SUBCHAT_JOIN`
- `ROUTING_DECISION_ATTEST` (recommended)

## 4. RFW / bid / award lifecycle (normative)

### 4.1 RFW_POST
`payload` MUST include:
- `rfw_id`
- `work_spec_ref`
- `policy_ref`
- `deadline`

`payload` MAY include:
- `budget_hint`
- `sla_hint`
- `required_attestation_refs`

### 4.2 BID_SUBMIT / BID_UPDATE / BID_WITHDRAW
`BID_SUBMIT` MUST include:
- `bid_id`
- `rfw_id`
- `offer_terms`

`BID_UPDATE` MUST include:
- `bid_id`
- `rfw_id`
- `offer_terms`

`BID_WITHDRAW` MUST include:
- `bid_id`
- `rfw_id`
- `reason_code`

### 4.3 AWARD_ISSUE / AWARD_ACCEPT / AWARD_DECLINE
`AWARD_ISSUE` MUST include:
- `award_id`
- `rfw_id`
- `bid_id`
- `work_order` (contains `work_order_id` and `workflow_ref`)

`AWARD_ACCEPT` / `AWARD_DECLINE` MUST include:
- `award_id`
- `rfw_id`

`AWARD_DECLINE` SHOULD include `reason_code`.

## 5. Auction mode semantics (normative)

### 5.1 AUCTION_OPEN
`payload` MUST include:
- `auction_id`
- `rfw_id`
- `auction_mode`
- `deadline`

Valid `auction_mode` identifiers are registry-defined by `registry/auction_modes.json`.

### 5.2 AUCTION_CLOSE
`payload` MUST include:
- `auction_id`
- `rfw_id`
- `result_ref`

## 6. Blackboard semantics (normative)

### 6.1 BLACKBOARD_DECLARE
MUST include:
- `workspace_id`
- `policy_ref`

### 6.2 BLACKBOARD_POST / UPDATE / REMOVE
All MUST include:
- `workspace_id`
- `entry_id`

`BLACKBOARD_POST` and `BLACKBOARD_UPDATE` MUST include `content_ref`.

## 7. Subchat semantics (normative)

### 7.1 SUBCHAT_CREATE
MUST include:
- `subchat_id`
- `parent_chat_id`
- `topic_tag`

### 7.2 SUBCHAT_INVITE
MUST include:
- `subchat_id`
- `invitee_id`

### 7.3 SUBCHAT_JOIN
MUST include:
- `subchat_id`
- `participant_id`

If session policy requires admission/role constraints, `SUBCHAT_JOIN` participation MUST be gated by prior admission evidence.

## 8. Routing-decision attestation semantics (normative)

`ROUTING_DECISION_ATTEST` is used when policy requires explicit award/routing evidence.

MUST include:
- `decision_id`
- `award_id`
- `policy_ref`
- `evidence_ref`

## 9. Conformance expectations

Conformance MUST cover:
- RFW shape/deadline/policy references,
- bid linkage to prior RFW,
- award linkage to prior bid/RFW/work-order binding,
- auction mode/open-close coherence,
- blackboard lifecycle consistency,
- subchat parent/invite/join consistency,
- admission-linked gating for participation,
- observability correlation for at least one marketplace flow,
- routing attestation presence when policy requires it.

## 10. Security considerations

- Awards and routing decisions should be signed/hash-bound to prevent winner substitution.
- Admission-gated subchat joins should fail closed when admission evidence is missing.
- Example: when `routing_attestation_required=true`, issuing an award without `ROUTING_DECISION_ATTEST` should fail policy conformance.

## 11. Privacy considerations

- Avoid embedding sensitive commercial details directly in market payloads when references suffice.
- Use abstract budget/SLA hints rather than raw private contracts where possible.
- Limit subchat invitation payloads to required participant and topic context.

## 12. Relationship to adjacent milestones

- M26 (`EXT-HUMAN-APPROVAL`): high-impact award/routing paths may require approval evidence.
- M27 (`EXT-OBSERVABILITY`): marketplace events should correlate with `OBS_SIGNAL` evidence.
- M28 (`EXT-IAM-BRIDGE`): identity/role assertions can inform participation controls.
- M35 (`EXT-ADMISSION`, `EXT-QUEUE-LEASES`): admission and load-management semantics gate participation and throughput.

## 13. Registry entry

- `EXT-MARKETPLACE` in `registry/extension_ids.json`.
