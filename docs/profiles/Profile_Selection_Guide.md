# Profile Selection Guide

This guide helps solution and platform teams select practical AICP profile targets.

## 1) Why profiles exist

Profiles convert optional extension space into concrete implementation targets with measurable conformance outcomes. They reduce ambiguity about what must be implemented for a given deployment pattern.

## 2) How to choose a minimum viable profile

1. Define your session ownership model (hosted, foreign, relay, mixed).
2. Define enforcement strictness (advisory, blocking, audited).
3. Define continuity needs (resume/resync required or not).
4. Pick the smallest profile that covers those needs.
5. Add extensions only where your use case requires them.

## 3) When to upgrade to stricter profiles

Upgrade profile strictness when you need:
- stronger moderated/blocking behavior,
- resumable sessions and durable continuity,
- delegated identity or workflow-governed orchestration,
- broader bazaar/agent-media ecosystem capabilities.

## 4) Selection matrix

| Scenario / environment | Recommended profile(s) | Required suites/extensions (see profile defs) | Optional extensions | Adjacent infrastructure assumptions |
|---|---|---|---|---|
| Basic governed bilateral exchange | `AICP-BASE@0.1` | Base profile-required set | CAPNEG, RESUME | Existing transport + simple identity |
| Hosted moderated reception | `AICP-MEDIATED-BLOCKING@0.1` | Blocking-oriented profile set | ALERTS, SECURITY-ALERT | Mediator/host + enforcement operator |
| Hosted moderated ops-heavy environment | `AICP-MEDIATED-BLOCKING-OPS@0.1` | Blocking+ops profile set | DISPUTES, POLICY-EVAL | Monitoring/ops pipelines |
| Long-running sessions with reconnect/resume | `AICP-RESUMABLE-SESSIONS@0.1` | Resume-oriented profile set | OBJECT-RESYNC | Durable state + recovery tooling |
| Cross-platform run/thread/store metadata portability | `AICP-EXECUTION-INTEROP@0.1` | Execution lifecycle + resume + object-resync profile set | TOOL-GATING (recommended for side effects) | Durable state references + deterministic recovery evidence |
| Cross-vendor policy semantic interoperability (OPA/Rego, ABAC/RBAC, LLM-safety) | `AICP-POLICY-OPA-REGO@0.1`, `AICP-POLICY-ABAC-RBAC@0.1`, or `AICP-POLICY-LLM-SAFETY@0.1` | Policy semantic profile suite + EXT-POLICY-EVAL | CAPNEG (recommended) | Registry-governed policy bundle + binding pipeline |
| Delegated/enterprise workflow environment | `AICP-WORKFLOW-ORCHESTRATION-DELEGATION@0.1` | Workflow/delegation profile set | TOOL-GATING, POLICY-EVAL | IAM bridge + approval controls |
| Delegated identity sensitive interactions | `AICP-DELEGATED-IDENTITY@0.1` | Delegated identity profile set | SECURITY-ALERT, DISPUTES | Identity lifecycle and revocation infra |
| Bazaar/agent-media channels | `AICP-BAZAAR-RECEPTION@0.1`, `AICP-AGENT-MEDIA@0.1` | Bazaar/media profile sets | Subscriptions/publications/inbox combinations | Channel infra, moderation, distribution controls |

> Use [docs/profiles/AICP_Profiles.md](AICP_Profiles.md) as the canonical profile definition source.

## 5) Common profile combinations

- **Reception + continuity:** `AICP-MEDIATED-BLOCKING@0.1` + `AICP-RESUMABLE-SESSIONS@0.1`
- **Execution metadata interop:** `AICP-EXECUTION-INTEROP@0.1` (+ `EXT-TOOL-GATING` when side effects/approvals are required)
- **Policy semantic interop:** one of `AICP-POLICY-OPA-REGO@0.1`, `AICP-POLICY-ABAC-RBAC@0.1`, or `AICP-POLICY-LLM-SAFETY@0.1` depending on policy surface and determinism boundary.
- **Enterprise delegation:** `AICP-DELEGATED-IDENTITY@0.1` + `AICP-WORKFLOW-ORCHESTRATION-DELEGATION@0.1`
- **Media with moderated intake:** `AICP-AGENT-MEDIA@0.1` + `AICP-BAZAAR-RECEPTION@0.1`

## 6) If you are building X, start with Y

- **Brand support reception:** start with `AICP-MEDIATED-BLOCKING@0.1`.
- **Enterprise orchestration hub:** start with `AICP-WORKFLOW-ORCHESTRATION-DELEGATION@0.1`.
- **Personal-agent gateway into external services:** start with `AICP-BASE@0.1`, then add `AICP-RESUMABLE-SESSIONS@0.1` if continuity is critical.
- **Run/thread interoperability across platforms:** start with `AICP-EXECUTION-INTEROP@0.1` and add `EXT-TOOL-GATING` when execution can trigger side effects.
- **Agent media distribution channel:** start with `AICP-AGENT-MEDIA@0.1`.
- **Marketplace-like multi-party intake:** start with `AICP-BAZAAR-RECEPTION@0.1`.

## See also

- [Profiles catalog](AICP_Profiles.md)
- [Policy semantic profiles](AICP_Policy_Semantic_Profiles.md)
- [Personas/stories/features/profiles map](AICP_Personas_Stories_Features_Profiles.md)
- [Playbooks](../playbooks/)
- [Session topology cookbook](../playbooks/Session_Topologies.md)
- [Enforcement models](../architecture/Enforcement_Models.md)
