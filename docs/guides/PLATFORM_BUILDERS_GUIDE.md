# Implementer Guide: Platform Builders (Mediators / Enforcers)

This guide is for teams building mediated AICP channels. For canonical term definitions, see [docs/GLOSSARY.md](../GLOSSARY.md).

## Architecture pattern (minimum viable)

- Mediator/host serializes transcript order into one deterministic chain.
- Mediator enforces hard gates before delivery or external side-effects.
- Enforcer/moderator emits protocol artifacts (`ENFORCEMENT_VERDICT`, `ALERT`) that can be audited later.

## Protocol-visible records to retain

- `contract_id`
- current head `message_hash`
- participant and role references used by emitted protocol artifacts
- verdict and evidence references bound to each `target_message_hash`

This is retention guidance for externally checkable protocol evidence, not a mandatory
internal storage schema. A platform may use any database, reducer, cache, or event model.
Internal moderation counters, queue state, model state, and host configuration are not
AICP session-state fields.

## What to log (audit events)

- verdict decision records (`ALLOW` / `DENY` / `INCONCLUSIVE`)
- sanctions applied (WARN/KICK/BAN or namespaced variants)
- alerts emitted and recommended actions
- disconnect/kick events
- resume/resync outcomes (`OK`, `NEEDS_RESYNC`, `UNKNOWN_SESSION`)
- links/ids for conformance reports used as release evidence

## Forbid effects deterministically

- Gate `CONTENT_DELIVER` behind `ENFORCEMENT_VERDICT(decision=ALLOW)`.
- If using MCP/tool paths, gate tool-call execution the same way: no ALLOW verdict, no effect.

## Simple strike policy (deterministic baseline)

Example policy:

1. strike 1 → `WARN`
2. strike 2 → `KICK`
3. strike 3+ → `BAN`

Keep thresholds explicit in policy/config and emit sanctions as protocol artifacts.

The strike example is deployment policy only. AICP does not standardize the counter,
storage mechanism, or threshold algorithm.

## Operational recovery

- Use ALERT `recommended_actions` taxonomy (`RETRY`, `REMEDIATE`, `DISCONNECT`, `ESCALATE`, `ACK_REQUIRED`, `NO_ACTION`).
- Resume flow:
  - `RESUME_REQUEST` with last seen head
  - `RESUME_RESPONSE(OK)` when in sync
  - `RESUME_RESPONSE(NEEDS_RESYNC)` + remediation path when out of sync
- Escalate to object/state resync only when required and authorized.
- When advertising strict portable state, use
  `aicp.session_state_projection.v1` and its separate `session_state_hash`; do not serialize
  the platform's internal state into `session_state`.

## Badge semantics and degraded mode

A suite/profile can be `passed=true` but still `degraded=true` when critical checks are unavailable (for example, signature verification backend unavailable). Degraded reports are not badge-eligible and must not emit compatibility marks.

## Pointers

- EXT-ENFORCEMENT: [docs/extensions/RFC_EXT_ENFORCEMENT.md](../extensions/RFC_EXT_ENFORCEMENT.md)
- EXT-ALERTS: [docs/extensions/RFC_EXT_ALERTS.md](../extensions/RFC_EXT_ALERTS.md)
- EXT-RESUME: [docs/extensions/RFC_EXT_RESUME.md](../extensions/RFC_EXT_RESUME.md)
- Behavioral demo suite: [conformance/demos/DEMO_ENFORCEMENT_BEHAVIORAL_0.1.json](../../conformance/demos/DEMO_ENFORCEMENT_BEHAVIORAL_0.1.json)
- Ops hardening suite: [conformance/ops/OPS_HARDENING_0.1.json](../../conformance/ops/OPS_HARDENING_0.1.json)
