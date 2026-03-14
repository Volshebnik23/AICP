# Mediated Blocking in Production (M26 + M27)

This playbook shows a conservative production pattern for mediated blocking where sensitive tool execution is gated by approval evidence and operator-visible telemetry.

## What this playbook covers

- M26 approval/intervention evidence (`APPROVAL_CHALLENGE` / `APPROVAL_GRANT` / `INTERVENTION_*`)
- M27 observability evidence (`OBS_SIGNAL`) for operational debugging
- Failure handling and safe degradation behavior

## Architecture sketch (prose)

A typical deployment has four roles:
1. **Requester agent** emits `TOOL_CALL_REQUEST` with `ext.human_approval.required=true` for protected actions.
2. **Mediator/enforcer** checks transcript evidence before allowing progression.
3. **Approver** emits grant/deny artifacts bound to exact target/scope.
4. **Observability producer** emits `OBS_SIGNAL` linked to the gated tool call (`correlation_ref.tool_call_id`).

AICP standardizes transcript evidence and linkage. External ticketing, paging, and SIEM systems remain deployment-specific.

## Step-by-step flow (happy path)

1. Contract enables tool gating + human approval policy.
2. Requester emits `TOOL_CALL_REQUEST` for sensitive action.
3. Mediator emits `APPROVAL_CHALLENGE` bound to that request.
4. Approver emits `APPROVAL_GRANT` bound to the challenge.
5. Mediator allows execution and records decision/result chain.
6. Observability emitter posts `OBS_SIGNAL` correlated to the same `tool_call_id`.
7. Operators can audit a single hash-chain showing request → challenge → grant → execution → telemetry.

## Failure walkthrough: grant missing or expired

**Symptom**
- Request appears valid, but no matching active grant exists.

**Expected safe behavior**
- Do not execute protected tool action.
- Emit explicit deny/degraded event path (policy-eval/enforcement as applicable).
- Emit `OBS_SIGNAL` with correlation to blocked `tool_call_id` and reason-code mapping.

**Operator debugging checklist**
- Verify challenge/grant target binding equality (`tool_call_id`/hash).
- Verify challenge expiry and grant issuance timing.
- Verify approver identity match.
- Verify no replayed grant reused across a different target.

## Transcript evidence required for incident review

At minimum, retain and correlate:
- contract policy declaration for approval requirement,
- protected `TOOL_CALL_REQUEST` payload ext object,
- `APPROVAL_CHALLENGE` / `APPROVAL_GRANT` linkage,
- execution verdict/result artifacts,
- one or more correlated `OBS_SIGNAL` events.

## Safe degradation guidance

If external approval or identity systems are degraded:
- default to deny for protected actions,
- allow only explicitly pre-authorized low-risk operations,
- annotate degraded mode in transcript-visible telemetry,
- require explicit operator override paths with strong audit trails.

## What remains outside AICP

- human approver UX implementation,
- org-specific escalation trees and paging workflows,
- SIEM dashboards and ticket integrations,
- legal/compliance retention controls beyond transcript evidence primitives.
