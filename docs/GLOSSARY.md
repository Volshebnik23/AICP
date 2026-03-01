# AICP Glossary (Canonical)

## Agent
An AI-capable protocol participant that sends/receives AICP messages and may act on delegated authority.

## Mediator / Host
A platform-controlled channel endpoint that can enforce gating, delivery, and session lifecycle behavior for mediated interactions.

## Enforcer / Moderator
An entity that evaluates policy/evidence and emits enforcement-relevant artifacts (e.g., EXT-ENFORCEMENT verdicts, EXT-ALERTS alerts).

## Observer / Auditor
A passive or independent participant that verifies transcript integrity, signatures, and policy evidence without changing contract state.

## Session
A protocol interaction context identified by `session_id`.

## Contract
The machine-readable context contract (`contract_id`) defining goal, roles, and policies.

## Contract Ref
A message-level reference (`contract_ref`) that binds processing to branch/version state.

## Amendment
A contract state change represented by `CONTEXT_AMEND` and resolved via branch/version semantics.

## Conflict / Resolve
Conflict is divergent contract head state; `RESOLVE_CONFLICT` selects/merges heads to restore a canonical head.

## Policy (structured object)
A contract policy entry with `policy_id`, `category`, and `parameters`, plus optional metadata (version/status/uri/notes).

## Policy Category
A registered id from `registry/policy_categories.json` or a namespaced extension category (`x-...` or `vendor:...`).

## Enforcement (EXT-ENFORCEMENT)
Extension semantics for blocking-gate delivery with auditable `ENFORCEMENT_VERDICT` and sanctions.

## Verdict
An `ENFORCEMENT_VERDICT` decision (`ALLOW`/`DENY`/`INCONCLUSIVE`) bound to a target message.

## Sanction
A codified enforcement consequence (e.g., WARN/KICK/BAN), validated against sanction registry semantics.

## Alert (EXT-ALERTS)
Operational warning/fatal signal (`ALERT`) carrying code + recommended actions for deterministic recovery handling.

## Security Alert (EXT-SECURITY-ALERTS)
Security incident/event signaling extension distinct from operational EXT-ALERTS taxonomy.

## Resume (EXT-RESUME)
Reconnect handshake using `RESUME_REQUEST` / `RESUME_RESPONSE` with explicit status and recovery actions.

## Resync (EXT-OBJECT-RESYNC)
Object/state resynchronization flows used when peers are out of sync.

## Conformance Suite
A machine-readable catalog of checks + fixtures executed by the conformance runner.

## Compatibility Mark
A suite/profile capability mark awarded only when required checks run and pass without degraded-mode disqualification.

## Profile
A composition of required suites representing a practical implementation target.

## Badge eligibility vs Degraded mode
A report may be `passed=true` yet `degraded=true` when critical checks are unavailable (e.g., signature backend missing); degraded reports are not badge-eligible and MUST NOT emit compatibility marks.

## Coexistence with non-AICP chats
AICP is optional: agents may operate in channels that do not use AICP. Enforcement semantics apply only where a mediated channel actually uses AICP artifacts.


## Standard Overview
A short orientation document that explains what AICP is and is not, and points implementers to first-run commands and core references.

## Degraded mode
A report state where checks pass but critical capabilities are unavailable (for example, signature verification backend missing), so compatibility marks are withheld.

## Badge eligibility
Condition where required checks both pass and are fully enforceable (non-degraded), allowing compatibility mark issuance.
