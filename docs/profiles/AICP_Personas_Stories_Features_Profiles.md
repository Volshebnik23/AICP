# AICP Personas → Stories → Features → Profiles Mapping

## Purpose
This document defines the source-of-truth justification layer for AICP profile design. Profiles are derived from concrete persona needs, user stories, and feature sets, not invented ad hoc.

## Personas

### P0 — Platform/Mediator Developer
User stories:
- As a platform/mediator developer, I need deterministic blocking gates so policy decisions are applied before content delivery.
- As a platform/mediator developer, I need standardized sanction and reason semantics so enforcement behavior is interoperable.
- As a platform/mediator developer, I need operational alerting and recovery hooks to handle enforcement outages safely.

Feature sets:
- Blocking gate flow (`CONTENT_MESSAGE` → `ENFORCEMENT_VERDICT` → `CONTENT_DELIVER`).
- Standardized policy-evaluation/enforcement payload semantics and registry-backed reason/sanction codes.
- Alert/recovery semantics for mediated operations (planned ops profile).

### P1 — Agent Developer
User stories:
- As an agent developer, I need a minimal baseline profile that works across implementations without extension lock-in.
- As an agent developer, I need capability/profile negotiation signals to fail fast on incompatibilities.
- As an agent developer, I need predictable, testable canonical flows for core session lifecycle behavior.

Feature sets:
- Core-only interoperable baseline (contract lifecycle, invariants, signatures/hash-chain checks).
- Negotiation-aligned profile selection.
- Canonical conformance suites that can be run locally and in CI.

### P2 — Enterprise AI Orchestrator
User stories:
- As an orchestrator, I need workflow and delegation semantics to coordinate multi-agent tasks with policy boundaries.
- As an orchestrator, I need resumable sessions so long-running workflows survive interruptions.
- As an orchestrator, I need profile badges to gate deployment based on objective conformance evidence.

Feature sets:
- Workflow orchestration primitives (planned).
- Session resumption/resync semantics (planned).
- Profile-level conformance badges computed from required suite results.

### P3 — Auth/Identity Provider
User stories:
- As an identity provider, I need delegated identity/claims containers so trust assertions are portable across parties.
- As an identity provider, I need explicit dependencies between identity semantics and policy/evidence artifacts.

Feature sets:
- Delegated identity claims container and references to issuer artifacts (planned).
- Binding between identity assertions and policy/evidence verification paths (planned).

### P4 — Vibe-coder / Multi-agent Builder
User stories:
- As a builder, I need a simple reception/chat-oriented profile to bootstrap quickly before adopting advanced controls.
- As a builder, I need clear profile progression so I can start with baseline and incrementally add mediation/orchestration.

Feature sets:
- Reception/chat usability profile for quick-start integration (planned).
- Incremental profile ladder from base interoperability to advanced mediated/orchestrated behavior.

## Initial Profile Set and Persona/Story Mapping

| Profile ID | Status | Description | Personas/Stories served |
|---|---|---|---|
| `AICP-BASE` | Available now | Core-only baseline interoperability profile. | P1 baseline interoperability and canonical flow stories; P4 incremental adoption starting point. |
| `AICP-MEDIATED-BLOCKING` | Available now | Core + mediated blocking enforcement flow for deterministic gate-before-deliver behavior. | P0 blocking and standardized sanctions stories; P2 deployment gating via conformance evidence. |
| `AICP-MEDIATED-BLOCKING-OPS` | Planned | Operations add-on for alerts/recovery around mediated blocking environments. | P0 operational alerting/recovery story. |
| `AICP-RECEPTION-CHAT` | Planned | Reception/chat-oriented profile for rapid builder onboarding and common interaction flows. | P4 quick-start reception/chat story. |
| `AICP-DELEGATED-IDENTITY` | Planned | Delegated identity/claims container profile aligned to external identity providers. | P3 delegated identity and trust portability stories. |
| `AICP-WORKFLOW-ORCHESTRATION` | Planned | Multi-agent workflow orchestration semantics and guardrails for enterprise coordination. | P2 orchestration governance story. |
| `AICP-RESUMABLE-SESSIONS` | Planned | Session continuity/resumption semantics for interruption-tolerant operations. | P2 long-running workflow resumption story. |

## Rationale
This mapping anchors profile evolution in user needs and implementable feature bundles. Any new profile SHOULD identify:
1. target persona(s),
2. user stories it satisfies,
3. concrete required suites/extensions,
4. objective conformance evidence path.


## New personas and stories (v88)
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
