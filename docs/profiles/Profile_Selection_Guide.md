# Profile Selection Guide

This guide helps solution and platform teams select practical AICP profile targets. Use [AICP Adoption Core and Tiers](../architecture/AICP_Adoption_Core_and_Tiers.md) as the packaging/framing layer, and treat [AICP_Profiles.md](AICP_Profiles.md) as the canonical executable profile truth.

## 1) Why profiles exist

Profiles convert optional extension space into concrete implementation targets with measurable conformance outcomes. They reduce ambiguity about what must be implemented for a given deployment pattern.

For adjacent-layer placement (discovery/calling vs content governance), see [docs/adjacent/A2A_Integration_Pattern.md](../adjacent/A2A_Integration_Pattern.md) and [docs/architecture/AICP_in_the_Ecosystem.md](../architecture/AICP_in_the_Ecosystem.md).

## 2) How to choose a minimum viable profile

1. Define your session ownership model (hosted, foreign, relay, mixed).
2. Define enforcement strictness (advisory, blocking, audited).
3. Define continuity needs (resume/resync required or not).
4. Decide whether Core-optional signatures are enough or every sender message must be authenticated.
5. Pick the smallest profile that covers those needs.
6. Prefer the smallest repository-present profile that satisfies your need before adding
   optional governance overlays; repository availability does not imply stable maturity.
7. Add extensions only where your use case requires them.

If the requirement is exact contract-byte and active-head agreement, select experimental
post-UAT `AICP-BASE@0.2` explicitly. Do not treat it as an automatic upgrade of Base 0.1:
its lifecycle schemas differ, it has no external-IUT target, and it does not authenticate
senders.

## 3) When to upgrade to stricter profiles

Upgrade profile strictness when you need:
- stronger moderated/blocking behavior,
- resumable sessions and durable continuity,
- delegated identity or workflow-governed orchestration,
- broader bazaar/agent-media ecosystem capabilities.

Adoption framing reminder:
- **Adoption Core / Tier 0** starts with `AICP-BASE@0.1`.
- **Post-UAT Tier-0 security variant:** select `AICP-AUTHENTICATED-BASE@0.1` when every
  message must be Ed25519-bound to its declared envelope sender. This is post-UAT and does
  not add identity/delegation/trust semantics.
- **Tier 1** adds baseline mediation, continuity, or delegated identity only when needed.
- **Tier 2+** overlays (policy semantics, approval, privacy, trust, enterprise, observability, commerce, execution interop) remain optional unless your deployment requires them.

## 4) Selection matrix

| Scenario / environment | Recommended profile(s) | Required suites/extensions (see profile defs) | Optional extensions | Adjacent infrastructure assumptions |
|---|---|---|---|---|
| Basic governed bilateral exchange | `AICP-BASE@0.1` | Base profile-required set | CAPNEG, RESUME | Existing transport + simple identity |
| Bilateral exact contract artifact/head agreement (post-UAT experiment) | `AICP-BASE@0.2` | `CT_CORE_0.2` | None standardized in M60 | Explicit version selection; no projection-v1 or external-IUT claim |
| Bilateral exchange requiring authenticated senders | `AICP-AUTHENTICATED-BASE@0.1` | Core + authenticated-message security suite | CAPNEG, identity/trust/witness profiles as separately needed | Supplied Ed25519 verification material; key discovery/custody remains external |
| Hosted moderated reception | `AICP-MEDIATED-BLOCKING@0.1` | Blocking-oriented profile set | ALERTS, SECURITY-ALERT | Mediator/host + enforcement operator |
| Hosted moderated ops-heavy environment | `AICP-MEDIATED-BLOCKING-OPS@0.1` | Blocking+ops profile set | DISPUTES, POLICY-EVAL | Monitoring/ops pipelines |
| Long-running sessions with reconnect/resume | `AICP-RESUMABLE-SESSIONS@0.1` | Resume-oriented profile set | OBJECT-RESYNC | Durable state + recovery tooling |
| Cross-platform run/thread/store metadata portability | `AICP-EXECUTION-INTEROP@0.1` | Execution lifecycle + resume + object-resync profile set | TOOL-GATING (recommended for side effects) | Durable state references + deterministic recovery evidence |
| Commerce-assisted purchase orchestration with external checkout rails | `AICP-COMMERCE-ACP@0.1` | CAPNEG + POLICY-EVAL + ENFORCEMENT + EXTERNAL-TRANSACTION + HUMAN-APPROVAL + REDACTION + cross-extension commerce semantics suite | WORKFLOW-ORCHESTRATION-DELEGATION (if multi-party approvals/workflows) | External commerce/payment rails remain out-of-protocol; transcript anchors evidence only |
| Cross-vendor policy semantic interoperability (OPA/Rego, ABAC/RBAC, LLM-safety) | `AICP-POLICY-OPA-REGO@0.1`, `AICP-POLICY-ABAC-RBAC@0.1`, or `AICP-POLICY-LLM-SAFETY@0.1` | Policy semantic profile suite + EXT-POLICY-EVAL | CAPNEG (recommended) | Registry-governed policy bundle + binding pipeline |
| Delegated/enterprise workflow environment | `AICP-WORKFLOW-ORCHESTRATION-DELEGATION@0.1` | Workflow/delegation profile set | TOOL-GATING, POLICY-EVAL | IAM bridge + approval controls |
| Delegated identity sensitive interactions | `AICP-DELEGATED-IDENTITY@0.1` | Delegated identity profile set | SECURITY-ALERT, DISPUTES | Identity lifecycle and revocation infra |
| Bazaar/agent-media channels | `AICP-BAZAAR-RECEPTION@0.1`, `AICP-AGENT-MEDIA@0.1` | Bazaar/media profile sets | Subscriptions/publications/inbox combinations | Channel infra, moderation, distribution controls |

> Use [docs/profiles/AICP_Profiles.md](AICP_Profiles.md) as the canonical profile definition source, and [AICP Adoption Core and Tiers](../architecture/AICP_Adoption_Core_and_Tiers.md) for the required-vs-optional packaging model.

The selection matrix does not duplicate registry maturity. Consult the generated canonical
profile-status table for stable/experimental state, external-IUT targets, and independent
evidence before publishing a claim.

When you need to publish compatibility evidence for the selected profile, package it using the public interop corpus guidance in [docs/interop/AICP_Public_Interop_Corpus.md](../interop/AICP_Public_Interop_Corpus.md) and the claim-language rules in [docs/interop/AICP_Compatibility_Claims_and_Evidence.md](../interop/AICP_Compatibility_Claims_and_Evidence.md).

## 5) Common profile combinations

These are deployment composition recommendations, not one negotiated multi-profile target.
Current EXT-CAPNEG proposes one selected `aicp_profile`; it does not negotiate the
combinations below as an atomic profile set. Versioned multi-profile composition is planned
under M61.

- **Reception + continuity:** `AICP-MEDIATED-BLOCKING@0.1` + `AICP-RESUMABLE-SESSIONS@0.1`
- **Authenticated Core:** `AICP-AUTHENTICATED-BASE@0.1`; compose with delegated identity,
  trust/status, witness, or mediation profiles only for the distinct semantics they add.
- **Execution metadata interop:** `AICP-EXECUTION-INTEROP@0.1` (+ `EXT-TOOL-GATING` when side effects/approvals are required)
- **Policy semantic interop:** one of `AICP-POLICY-OPA-REGO@0.1`, `AICP-POLICY-ABAC-RBAC@0.1`, or `AICP-POLICY-LLM-SAFETY@0.1` depending on policy surface and determinism boundary.
- **Enterprise delegation:** `AICP-DELEGATED-IDENTITY@0.1` + `AICP-WORKFLOW-ORCHESTRATION-DELEGATION@0.1`
- **Media with moderated intake:** `AICP-AGENT-MEDIA@0.1` + `AICP-BAZAAR-RECEPTION@0.1`
- **Commerce-assisted purchase orchestration:** `AICP-COMMERCE-ACP@0.1` (checkout/payment rails remain external)

## 6) If you are building X, start with Y

- **Brand support reception:** start with `AICP-MEDIATED-BLOCKING@0.1`.
- **Enterprise orchestration hub:** start with `AICP-WORKFLOW-ORCHESTRATION-DELEGATION@0.1`.
- **Personal-agent gateway into external services:** start with `AICP-BASE@0.1`, then add `AICP-RESUMABLE-SESSIONS@0.1` if continuity is critical.
- **Cryptographically sender-authenticated gateway:** use the post-UAT
  `AICP-AUTHENTICATED-BASE@0.1`; do not describe that result as real-world identity or
  universal trust.
- **Run/thread interoperability across platforms:** start with `AICP-EXECUTION-INTEROP@0.1` and add `EXT-TOOL-GATING` when execution can trigger side effects.
- **Agent media distribution channel:** start with `AICP-AGENT-MEDIA@0.1`.
- **Commerce-assisted purchase orchestration:** start with `AICP-COMMERCE-ACP@0.1`; keep payment rails external and anchor receipts/policy/approval evidence in transcript.
- **Marketplace-like multi-party intake:** start with `AICP-BAZAAR-RECEPTION@0.1`.

## See also

- [Profiles catalog](AICP_Profiles.md)
- [Policy semantic profiles](AICP_Policy_Semantic_Profiles.md)
- [Personas/stories/features/profiles map](AICP_Personas_Stories_Features_Profiles.md)
- [Playbooks](../playbooks/)
- [Session topology cookbook](../playbooks/Session_Topologies.md)
- [Enforcement models](../architecture/Enforcement_Models.md)
