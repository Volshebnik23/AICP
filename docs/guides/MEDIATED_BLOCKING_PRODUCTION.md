# Mediated Blocking in Production (Implementer Playbook)

This playbook maps already-shipped AICP artifacts to a practical production path for mediated blocking deployments.
It does not introduce new protocol semantics.

## When to use this playbook

Use this guide when your deployment needs deterministic host/mediator gating before delivery or side effects, with conformance-backed evidence and operational auditability.

## Required protocol artifacts / suites

### Profile target
- `AICP-MEDIATED-BLOCKING@0.1`
- Optional hardening target: `AICP-MEDIATED-BLOCKING-OPS@0.1`

### Core and extension suites
- `conformance/core/CT_CORE_0.1.json`
- `conformance/extensions/CN_CAPNEG_0.1.json`
- `conformance/extensions/PE_POLICY_EVAL_0.1.json`
- `conformance/extensions/ENF_ENFORCEMENT_0.1.json`
- Optional ops hardening: `conformance/extensions/AL_ALERTS_0.1.json`, `conformance/extensions/RS_RESUME_0.1.json`

## Ingress validation and signature posture

At ingress, apply a strict sequence:
1. envelope/schema boundary validation,
2. transcript/hash-chain checks,
3. signature/hash consistency and signer key checks,
4. profile/extension capability checks (CAPNEG where applicable),
5. policy evaluation and enforcement decision.

Recommended command path for local/CI posture:
- `make validate`
- `make conformance`
- `make conformance-ext`
- `make conformance-profiles`

## Storage / audit expectations

Persist:
- full source envelopes (immutable append-only log),
- message hash/prev-hash linkage,
- signatures and key identifiers,
- policy/verdict/evidence references used for gating decisions.

Do not rely only on projected internal events for audit/dispute handling.

## Enforcement decision flow

A safe operational flow:
1. receive message,
2. validate + verify,
3. evaluate policy context,
4. produce allow/deny/escalate artifact,
5. deliver or block deterministically,
6. persist decision + evidence references.

Use explicit artifacts rather than silent drops for reject/escalation paths.

## Degraded mode handling

If signature verification or required policy dependencies are unavailable:
- mark run/deployment mode degraded,
- avoid compatibility-mark claims for affected runs,
- keep explicit operational alerts/evidence of degraded posture,
- require recovery before re-entering badge-eligible operation.

## Operational risks and links

- **Replay/session hijack:** test replay windows and resume paths with binding/core suites.
- **Confused deputy:** bind authority/scope checks to policy artifacts before side effects.
- **Tool-side SSRF or unsafe execution:** enforce allowlists and tool-gating policies.
- **Mediator equivocation:** preserve immutable logs and portable evidence references.

See:
- `docs/security/SECURITY_BEST_PRACTICES.md`
- `docs/architecture/Enforcement_Models.md`
- `docs/profiles/AICP_Profiles.md`
- `docs/profiles/Profile_Selection_Guide.md`
