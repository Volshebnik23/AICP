# AICP Adoption Core and Tiers

> **Purpose:** adoption framing for already-shipped AICP repo truth. This document packages the existing Core, profiles, bindings, and compatibility evidence model into a simpler public adoption model. It does **not** define new protocol semantics. For the pilot-facing UAT package built on top of this framing, see `docs/release/AICP_UAT_Release_Pack.md`.

## 1) What this document is for

If you need the shortest release-facing answer for pilot adopters, start with `docs/release/AICP_UAT_Release_Pack.md` and then return here for the canonical tier framing.


AICP already ships a large amount of executable protocol surface: Core narrative requirements, schemas, conformance suites, bindings, profiles, extension RFCs, and implementation guidance. This document defines the **AICP Adoption Core** and a practical **tier model** so architects and implementers can answer four questions quickly:

1. What is the smallest truthful thing to implement first?
2. Which shipped profiles make up the must-implement center for common adoption?
3. Which governance and ecosystem capabilities are optional overlays rather than prerequisites?
4. How should teams make compatibility claims without falling back to vague “supports AICP” language?

The profile catalog, registries, schemas, and conformance suites remain the canonical executable truth. This document is the packaging/framing layer for that shipped truth.

## 2) Explicit non-goals

This document is **not**:
- a new protocol spec,
- a new certification regime,
- a reduction of existing optional shipped surfaces,
- a transport, discovery, tool-runtime, payment, or IAM specification,
- a claim that every adopter must implement the full governance stack before adopting AICP.

The purpose is adoption clarity, not protocol expansion.

## 3) The AICP Adoption Core

The **AICP Adoption Core** is the smallest truthful center for initial AICP adoption. It has four parts.

### 3.1 Core transcript integrity baseline

Every serious AICP adoption starts with the shipped Core transcript model:
- envelope and payload semantics from Core,
- deterministic hashing and transcript linkage,
- schema validation at the boundary,
- conformance validation for transcript invariants and replayable evidence.

In practical terms, that means using the existing Core narrative/spec/schema/conformance stack as the baseline:
- Core narrative: `docs/core/AICP_Core_v0.1_Normative.md`
- Core schemas: `schemas/core/`
- Core conformance: `conformance/core/CT_CORE_0.1.json`

If this baseline is absent, higher-layer AICP claims are not meaningful.

### 3.2 Baseline profile center (small, conservative, already shipped)

For public adoption framing, the conservative baseline profile center is:
- `AICP-BASE@0.1` — minimum interoperable Core profile,
- `AICP-MEDIATED-BLOCKING@0.1` — baseline governed mediation / policy / enforcement profile,
- `AICP-RESUMABLE-SESSIONS@0.1` — continuity profile for reconnect/resume/resync needs,
- `AICP-DELEGATED-IDENTITY@0.1` — identity-sensitive acting-on-behalf-of profile when external identity authority matters.

Why these four:
- they are already shipped in repo truth,
- they cover the most common adoption center without expanding protocol breadth,
- they distinguish “Core only”, “governed mediation”, “continuity”, and “delegated authority” as separate adoption steps.

This is intentionally **not** the full profile catalog. More specialized bundles remain available and optional.

`AICP-AUTHENTICATED-BASE@0.1` is an experimental, post-UAT Tier-0 security
variant. It adds mandatory Ed25519 binding from every envelope sender to the message hash,
without changing the frozen baseline or adding identity, trust, witnessing, policy, or
transport-security claims. Existing profiles are not silently strengthened; deployments
may compose them only as separate, explicit targets.

### 3.3 Transport/binding floor

AICP is transport-independent. The repo-backed HTTP/WS/SSE binding surface currently
provides static, executable case validation:
- binding spec: `docs/bindings/RFC_BIND_HTTP_WS.md`
- conformance suite: `conformance/bindings/TB_HTTP_WS_0.1.json`
- canonical binding identifier: `BIND-HTTP-0.1`

This does **not** redefine AICP as a transport protocol, and the static case suite does not
demonstrate live independent HTTP, WebSocket, or SSE interoperability. A live binding harness
is planned under M64.

### 3.4 Compatibility story

AICP compatibility claims should be grounded in **profile conformance evidence**, not generic marketing language.

The truthful compatibility story is:
1. implement the Core transcript integrity baseline,
2. implement the smallest shipped profile that matches your need,
3. pass the required repository-owned suite/profile conformance runs for that profile,
4. use a full external-IUT target when one exists before making an external product claim.

Only Base and experimental Authenticated Base currently have full external-IUT targets, and
only Base can reach an ordinary external profile mark. See
`docs/process/AICP_Repo_Truth_Baseline.md`.

## 4) Optional governance stack (important, but not prerequisite to all adoption)

AICP already ships many governance-oriented capabilities. They are important, but they are **optional overlays**, not universal adoption prerequisites.

Optional overlays include:
- **policy**: `EXT-POLICY-EVAL` and the optional policy semantic profiles,
- **approval / intervention**: `EXT-HUMAN-APPROVAL`,
- **privacy / redaction / retention**: confidentiality and redaction surfaces,
- **external transaction / commerce**: `EXT-EXTERNAL-TRANSACTION` and `AICP-COMMERCE-ACP@0.1`,
- **trust / enterprise / observability**: trust attestations, status/revocation, enterprise bindings, observability,
- **bazaar / publication / distribution families** where high-volume mediated ecosystems are needed,
- **execution metadata interoperability** where runs/threads/stores portability is a goal.

An adopter should add these when the deployment actually requires them, not because they are part of the protocol universe.

## 5) Adoption tier model

The tier model below is **adoption framing only**. It introduces no new protocol semantics.

### Tier 0 — Core transcript integrity

**What it is:** the minimum truthful AICP starting point.

**Center:**
- Core narrative + schema + conformance baseline,
- `AICP-BASE@0.1`,
- transport-independent by design, with `BIND-HTTP-0.1` as the practical executable floor when a concrete interoperable transport binding is needed.

**Who needs it:**
- teams that need portable, verifiable governed transcripts before they need advanced governance overlays,
- implementers embedding AICP into an existing app or adapter/gateway.

**Still optional at Tier 0:**
- the experimental `AICP-AUTHENTICATED-BASE@0.1` sender-authentication variant,
- policy engines,
- approval workflows,
- privacy/redaction overlays,
- delegated identity,
- marketplace/media/commerce/execution interop bundles.

### Tier 1 — Baseline mediated adoption

**What it is:** the smallest widely useful governance step beyond Core-only exchange.

**Typical profiles and surfaces:**
- `AICP-MEDIATED-BLOCKING@0.1`,
- `AICP-RESUMABLE-SESSIONS@0.1` when continuity matters,
- `AICP-DELEGATED-IDENTITY@0.1` when acting-on-behalf-of identity binding matters.

**Who needs it:**
- hosted receptions,
- moderated sessions,
- durable cross-session conversations,
- systems that need externally rooted identity/delegation evidence.

**What remains optional:**
- semantic policy profile variants,
- human approval,
- confidentiality/redaction overlays,
- enterprise/trust overlays,
- commerce and execution interoperability bundles.

### Tier 2 — Governance, trust, and privacy overlays

**What it is:** optional overlays for deployments with higher governance, assurance, or compliance needs.

**Typical shipped families:**
- policy semantic profiles (`AICP-POLICY-OPA-REGO@0.1`, `AICP-POLICY-ABAC-RBAC@0.1`, `AICP-POLICY-LLM-SAFETY@0.1`),
- `EXT-HUMAN-APPROVAL`,
- confidentiality / redaction / retention surfaces,
- trust attestations and status/revocation,
- enterprise bindings,
- observability.

**Who needs it:**
- enterprise control planes,
- regulated or privacy-sensitive deployments,
- systems that require externally checkable approval, trust, status, or audit overlays.

**What remains optional:**
- marketplace/reception specialization,
- publication/media ecosystems,
- execution interop portability,
- commerce-ready orchestration.

### Tier 3 — Adjacent composition and specialized ecosystem bundles

**What it is:** specialized optional bundles for ecosystems, platforms, and adjacent-system composition.

**Typical shipped profiles:**
- `AICP-EXECUTION-INTEROP@0.1`,
- `AICP-COMMERCE-ACP@0.1`,
- `AICP-BAZAAR-RECEPTION@0.1`,
- `AICP-AGENT-MEDIA@0.1`,
- `AICP-WORKFLOW-ORCHESTRATION-DELEGATION@0.1`,
- `AICP-RECEPTION-CHAT@0.1` where the richer reception/chat bundle is needed.

**Who needs it:**
- platforms composing AICP with execution runtimes, marketplaces, channelized media, external commerce rails, or larger multi-party workflow systems.

**What remains true:**
- these are optional adoption targets,
- they do not replace the Tier 0 Core baseline,
- they do not redefine AICP as discovery, calling, tool runtime, IAM, payment, or trust infrastructure.

## 6) Core vs optional, in one table

| Category | Core adoption center? | Repo-backed examples |
|---|---|---|
| Core transcript integrity | **Yes** | Core narrative + schemas + `CT_CORE_0.1` |
| Baseline profile claim | **Yes** | `AICP-BASE@0.1` |
| Authenticated Core variant | Optional, experimental/post-UAT | `AICP-AUTHENTICATED-BASE@0.1` |
| Baseline mediated adoption | Usually yes for hosted/governed deployments | `AICP-MEDIATED-BLOCKING@0.1` |
| Continuity | Optional unless reconnect/resume matters | `AICP-RESUMABLE-SESSIONS@0.1` |
| Delegated identity | Optional unless acting-on-behalf-of matters | `AICP-DELEGATED-IDENTITY@0.1` |
| Policy semantics variants | Optional overlay | OPA/Rego, ABAC/RBAC, LLM-safety profiles |
| Approval/intervention | Optional overlay | `EXT-HUMAN-APPROVAL` |
| Privacy/redaction | Optional overlay | confidentiality + redaction surfaces |
| Trust / status / enterprise / observability | Optional overlay | trust/status, enterprise bindings, observability |
| Execution / commerce / marketplace / media | Optional specialized bundle | execution interop, commerce ACP, bazaar reception, agent media |

## 7) Compatibility claims: how to be truthful

Implementers should avoid blanket claims such as “supports AICP” without narrowing the actual interoperability target.

Prefer claims in this form:
- **Implements `AICP-BASE@0.1`**
- **Compatible with `AICP-MEDIATED-BLOCKING@0.1`**
- **Passes the static `BIND-HTTP-0.1` binding case suite**

Those claims should map to:
- shipped profile and binding identifiers,
- required conformance suites,
- reproducible, non-degraded external-IUT report evidence bound to the implementation,
  runner revision, suite/profile digest, and input artifacts. Repository corpus self-tests
  remain `reference_corpus` evidence and do not prove an unnamed external product.

The stronger external-IUT requirement is currently implementable only for the two registered
IUT targets. Other profile suites support internal verification, not an ordinary external
product-profile claim.

For compatibility-mark and badge policy, see:
- `docs/adoption/COMPATIBILITY_AND_BADGES.md`
- `docs/ops/COMPATIBILITY_POLICY.md`
- `docs/rfc/RFC_Governance_and_IPR.md`

## 8) Use AICP when / do not use AICP when

### Use AICP when
- you need governed multi-party transcripts with verifiable linkage,
- you need contract/policy/approval/evidence semantics that survive vendor boundaries,
- you need profile-based compatibility claims backed by executable conformance evidence,
- you need a governed content layer that composes with external transports, IAM, trust, policy, and commerce systems.

### Do not use AICP as your primary answer when
- the problem is only discovery or directory lookup,
- the problem is only calling/connectivity/transport,
- the problem is only tool runtime execution,
- the problem is only IAM/provider internals,
- the problem is only payment-rail behavior.

### Use both when
- an adjacent protocol handles discovery/calling/runtime/payment/IAM,
- and AICP carries the governed transcript, policy, approval, attestation, and compatibility evidence layer.

For the ecosystem boundary model, see:
- `docs/architecture/AICP_in_the_Ecosystem.md`
- `docs/adjacent/A2A_Integration_Pattern.md`
- `docs/guides/Protocol_Adapter_Gateway.md`

## 9) Practical adoption sequence

A small, truthful adoption sequence is:
1. Start with Tier 0 (`AICP-BASE@0.1` + Core conformance).
2. Add Tier 1 only where mediation, continuity, or delegated identity are real requirements.
3. Add Tier 2 overlays only where policy, approval, privacy, trust, enterprise, or observability needs are concrete.
4. Add Tier 3 bundles only for specialized ecosystems or adjacent-system composition.

In all cases, pick the **smallest shipped profile** that satisfies the deployment need.

## 10) Canonical cross-links

- Profile catalog: `docs/profiles/AICP_Profiles.md`
- Profile selection guide: `docs/profiles/Profile_Selection_Guide.md`
- Ecosystem boundaries: `docs/architecture/AICP_in_the_Ecosystem.md`
- Adjacent composition: `docs/adjacent/A2A_Integration_Pattern.md`
- Implementer quickstart: `START_HERE_IMPLEMENTERS.md`
