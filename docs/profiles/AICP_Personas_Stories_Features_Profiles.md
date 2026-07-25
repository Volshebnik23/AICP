# AICP Personas → Stories → Features → Profiles Mapping

## Purpose
This document records the justification layer for AICP profile design. Current status is
owned by `docs/process/AICP_Repo_Truth_Baseline.md` and registry/catalog artifacts; this
persona map must not override them.

## Personas

### P0 — Platform/Mediator Developer
User stories:
- As a platform/mediator developer, I need deterministic blocking gates so policy decisions are applied before content delivery.
- As a platform/mediator developer, I need standardized sanction and reason semantics so
  enforcement behavior has a shared protocol conformance target.
- As a platform/mediator developer, I need operational alerting and recovery hooks to handle enforcement outages safely.

Feature sets:
- Blocking gate flow (`CONTENT_MESSAGE` → `ENFORCEMENT_VERDICT` → `CONTENT_DELIVER`).
- Standardized policy-evaluation/enforcement payload semantics and registry-backed reason/sanction codes.
- Alert/recovery semantics for mediated operations (available in the registered ops profile).

### P1 — Agent Developer
User stories:
- As an agent developer, I need a minimal baseline profile that works across implementations without extension lock-in.
- As an agent developer, I need capability/profile negotiation signals to fail fast on incompatibilities.
- As an agent developer, I need predictable, testable canonical flows for core session lifecycle behavior.

Feature sets:
- Core-only protocol conformance baseline (contract lifecycle, invariants,
  signatures/hash-chain checks).
- Negotiation-aligned profile selection.
- Canonical conformance suites that can be run locally and in CI.

### P2 — Enterprise AI Orchestrator
User stories:
- As an orchestrator, I need workflow and delegation semantics to coordinate multi-agent tasks with policy boundaries.
- As an orchestrator, I need resumable sessions so long-running workflows survive interruptions.
- As an orchestrator, I need profile badges to gate deployment based on objective conformance evidence.

Feature sets:
- Workflow orchestration primitives (available in the registered workflow/delegation profile).
- Session resumption/resync semantics (available in the registered resumable-sessions profile).
- Profile-level conformance badges computed from required suite results.

### P3 — Auth/Identity Provider
User stories:
- As an identity provider, I need delegated identity/claims containers so trust assertions are portable across parties.
- As an identity provider, I need explicit dependencies between identity semantics and policy/evidence artifacts.

Feature sets:
- Delegated identity claims container and issuer-artifact references are shipped as
  experimental protocol semantics with repository-owned internal suites.
- Identity assertion bindings to scope, expiry, revocation, and evidence paths are shipped
  and internally verified; an external-IUT target and independent external evidence are
  absent.
- Real external adoption and any broader identity-provider integration remain future
  deployment/evidence work, not missing delegated-identity protocol semantics.

### P4 — Vibe-coder / Multi-agent Builder
User stories:
- As a builder, I need a simple reception/chat-oriented profile to bootstrap quickly before adopting advanced controls.
- As a builder, I need clear profile progression so I can start with baseline and incrementally add mediation/orchestration.

Feature sets:
- Reception/chat usability profile for quick-start integration (available in the registry).
- Incremental profile ladder from base interoperability to advanced mediated/orchestrated behavior.

## Initial Profile Set and Persona/Story Mapping

This justification table intentionally does not duplicate current registry maturity. Exact
repository availability, stable/experimental maturity, internal evidence, external-IUT
reachability, and independent evidence are generated in
[`AICP_Profiles.md`](AICP_Profiles.md#2-profile-catalog-and-status).

| Profile ID | Protocol role | Personas/Stories served |
|---|---|---|
| `AICP-BASE` | Core-only protocol conformance target. | P1 baseline conformance and canonical flow stories; P4 incremental adoption starting point. |
| `AICP-MEDIATED-BLOCKING` | Core + mediated blocking enforcement flow for deterministic gate-before-deliver behavior. | P0 blocking and standardized sanctions stories; P2 deployment gating via conformance evidence. |
| `AICP-MEDIATED-BLOCKING-OPS` | Operations add-on for alerts/recovery around mediated blocking environments. | P0 operational alerting/recovery story. |
| `AICP-RECEPTION-CHAT` | Reception/chat-oriented profile for rapid builder onboarding and common interaction flows. | P4 quick-start reception/chat story. |
| `AICP-DELEGATED-IDENTITY` | Delegated identity/claims container profile aligned to external identity providers. | P3 delegated identity and trust portability stories. |
| `AICP-WORKFLOW-ORCHESTRATION-DELEGATION` | Multi-agent workflow orchestration semantics and guardrails for enterprise coordination. | P2 orchestration governance story. |
| `AICP-RESUMABLE-SESSIONS` | Session continuity/resumption semantics for interruption-tolerant operations. | P2 long-running workflow resumption story. |

## Rationale
This mapping anchors profile evolution in user needs and implementable feature bundles. Any new profile SHOULD identify:
1. target persona(s),
2. user stories it satisfies,
3. concrete required suites/extensions,
4. objective conformance evidence path.


## Additional personas and stories
- **Brand Reception Operator**: uses ADMISSION + QUEUE-LEASES + INBOX to control spikes.
- **Bazaar Enforcer Operator**: uses FACILITATION and overload signaling to reduce storm traffic.
- **Agent Media Publisher/Editor**: uses CHANNELS/SUBSCRIPTIONS/PUBLICATIONS for corrections and targeted distribution.
- **Marketplace Operator**: uses MARKETPLACE + PROVENANCE + ACTION-ESCROW for award and accountable execution.
- **Client Agent**: uses SUBSCRIPTIONS + ECONOMICS budgets + backoff hints.

## Scenario → Persona → Story → Features → Profile → Dependencies map

| Scenario | Persona | Story | Feature set | Suggested profile | Adjacent dependencies |
|---|---|---|---|---|---|
| Hosted brand support reception | Product architect / mediator developer | Host moderated external support conversations with policy-gated escalation | Mediated delivery, enforcement signaling, alerts | `AICP-MEDIATED-BLOCKING@0.1` | Transport, IAM, support APIs |
| Enterprise workflow chaining | Platform architect / enterprise orchestrator | Coordinate multiple agents with delegated authority and auditable tool use | Delegation, workflow sync, tool gating, policy eval | `AICP-WORKFLOW-ORCHESTRATION-DELEGATION@0.1` | IAM bridge, policy engine, workflow runtime |
| Delegated identity actions | Security architect / enforcer developer | Validate acting-on-behalf-of operations across trust boundaries | Delegated identity lifecycle + evidence compatibility | `AICP-DELEGATED-IDENTITY@0.1` | Identity lifecycle, revocation/status infra |
| Personal agent external coordination | Agent developer | Keep user-governed context while interacting with foreign receptions | Base governance + resumable continuity where needed | `AICP-BASE@0.1` then `AICP-RESUMABLE-SESSIONS@0.1` | Connectivity, personal IAM, optional relay |
| Agent media/feed distribution | Product architect | Publish governed channel updates to subscriber agents | Channels/subscriptions/publications/inbox | `AICP-AGENT-MEDIA@0.1` | Distribution infra, moderation controls |
| Bazaar-style multi-party intake | Solution architect | Run high-volume moderated intake with admission/congestion controls | Admission + queue leases + facilitation + participants/enforcement | `AICP-BAZAAR-RECEPTION@0.1` | Channel ops, anti-abuse controls |

Use this table with:
- `docs/profiles/Profile_Selection_Guide.md`
- `docs/playbooks/`
- `docs/architecture/AICP_in_the_Ecosystem.md`
