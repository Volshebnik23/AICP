# AICP Roadmap Items (repo-backed)

> Source of truth for shipped/current/next milestone status.
> `AICP_Backlog` is planning-only for remaining deliverables and should not duplicate shipped-history detail.

_Last updated: 2026-03-09_

## Current / Next

### ✅ M16b — RFC8785 float canonicalization
- **Progress:** Finite-float canonicalization landed with cross-language vector parity coverage and updated conformance/docs.

### ✅ M17 — Stability graduation (first promotions)
- **Progress:** `EXT-ENFORCEMENT` and `EXT-POLICY-EVAL` promoted to stable with anchored spec refs and productization coverage.

### ✅ M18 — Release discipline (changelog + compatibility policy + errata cadence)
- **Progress:** Errata cadence documented and validator wired into `make validate`.

### ✅ M19 — Protocol Adapter / Gateway quickstart kit (CI-first onboarding)
- **Progress:** Adapter/gateway artifacts are present and roadmap state is now aligned to shipped repo reality.

### ✅ M42–M46 — Developer-facing documentation architecture pass
- **Progress:** Canonical docs front door (`docs/INDEX.md`) shipped with role/goal navigation and cross-links across overview, profiles, architecture, playbooks, and flows.
- **Progress:** Ecosystem positioning, profile selection guide, session topology cookbook, and enforcement models docs shipped with explicit protocol-vs-adjacent-layer boundaries.
- **Progress:** Solution playbooks for reception/support, enterprise orchestration, personal-agent coordination, agent media feeds, and commerce-assisted purchase shipped with profile and dependency guidance.
- **Next concrete step:** gather implementer feedback from first integration cohorts and tighten examples/diagrams without changing protocol semantics.

### ✅ M39 — Productization hygiene: Core/template/reference/CI alignment
- **Progress:** Core narrative now explicitly matches shipped `ERROR` message set and clarifies narrative/spec/schema/conformance/reference boundaries.
- **Progress:** Python reference validator now enforces non-first `prev_msg_hash`, signature `object_hash == message_hash`, and consistent signer/`kid` key selection checks.
- **Progress:** TS agent + protocol-adapter templates are aligned to actual commands/output and now preserve onboarding-safe audit metadata.
- **Progress:** CI/test coverage now includes deterministic smoke checks for shipped onboarding templates.
- **Next concrete step:** expand template smoke checks into profile-specific onboarding packs without increasing default CI runtime significantly.

### ✅ M22 — Transport bindings and channel properties (completed)
- **Shipped:** replay-window hardening now includes additional deterministic replay evidence (`TB-HTTP-18`) plus session-scoped replay checks in runner enforcement.
- **Shipped:** multi-session interoperability is now conformance-backed with secondary-session create/send/replay coverage (`TB-HTTP-19`/`20`/`21`) and session-scope coherence checks across path/body/top-level references.
- **Shipped:** reconnect/churn coverage now includes multi-step SSE reconnect evidence (`TB-HTTP-22` chaining from `TB-HTTP-17`) with deterministic cursor continuity checks.
- **Shipped:** HTTP/WS binding RFC guidance now maps replay/idempotency/session-scope/reconnect behavior directly to shipped conformance cases.
- **Next concrete step:** begin M30 (Tool/Resource/Prompt supply-chain security) after shipping trust + status baseline.

### ✅ M20 — Trust anchors & issuer attestations (completed)
- **Shipped:** normative M20 RFC defines canonical `trust_anchor_list` and `issuer_attestation` objects with baseline verification model and explicit M21 deferrals.
- **Shipped:** trust-signal and attestation-type registries are now in-repo and validator-enforced (`registry/trust_signal_types.json`, `registry/attestation_types.json`).
- **Shipped:** M20 schemas + deterministic fixtures + conformance suite (`TA-TRUST-ATTESTATIONS-0.1`) verify hash integrity, registry linkage, signature binding, and trust-chain resolution including untrusted-signer negative case.
- **Next concrete step:** begin M21 (Revocation/status channel) to layer revocation/status freshness onto this baseline trust model.


### ✅ M21 — Revocation/status channel (completed)
- **Shipped:** normative M21 RFC defines canonical `status_query` and `status_assertion` objects with baseline status-as-of/cache semantics and revocation-as-of checks.
- **Shipped:** minimal status and revocation-reason registries are in-repo and validator-enforced (`registry/status_assertion_codes.json`, `registry/revocation_reason_codes.json`).
- **Shipped:** M21 schema + deterministic fixtures + conformance suite (`SC-STATUS-CHANNEL-0.1`) verify hash integrity, registry linkage, trust-chain signature checks, target binding consistency, and temporal/cache validity for GOOD/REVOKED assertions.
- **Next concrete step:** begin M30 (Tool/Resource/Prompt supply-chain security).

## Planned milestones (protocol maturity & ecosystem scale)





### ⏳ M23 — Confidentiality & selective disclosure modes (enterprise/on-prem)
- **Exit:** Full/redacted/metadata-only/classification-only modes + conformance.

### ⏳ M24 — Redaction standard + retention/deletion policies
- **Exit:** Redaction objects + retention/deletion contract fields + fixtures + conformance.

### ⏳ M26 — Human-in-the-loop primitive (approval / step-up)
- **Exit:** EXT-HUMAN-APPROVAL with challenge/signer/TTL bindings + conformance.

### ⏳ M28 — IAM bridge (OAuth/OIDC mapping for delegation/tool gating/human approval)
- **Exit:** Normative mapping guidance + examples + security notes.

### ⏳ M31 — Anti-equivocation & transparency witnessing (optional, internet-scale)
- **Exit:** Witness checkpoints + gossip + inclusion proofs + conformance for required-witness deployments.

### ⏳ M32 — Agent execution interoperability profile (optional): Runs / Threads / Stores
- **Exit:** Optional extension + profile + fixtures/conformance.

### ⏳ M27 — Production attributes: tracing, SLA signals, metering
- **Exit:** Minimal event taxonomy for tracing/latency/errors + standard SLA signals.

### ⏳ M29 — Enterprise domain bindings (OpenAPI/OData/OPA/ABAC)
- **Exit:** Binding notes + minimal profiles for common enterprise integration styles.

### ⏳ M34 — Security & implementer playbooks (MCP-level doc completeness)
- **Progress:** Implementer-facing security best-practices doc is shipped at `docs/security/SECURITY_BEST_PRACTICES.md`.
- **Next concrete step:** add production cookbook depth (mediated blocking/OAuth bridge/tool pinning) and finish security-considerations completion across extension docs.
- **Exit:** Security best practices + deployment cookbooks + security-considerations completion.

### ⏳ M35 — Bazaar admission & congestion control (leases, queues, anti-spam hooks)
- **Exit:** EXT-ADMISSION + EXT-QUEUE-LEASES + overload reason codes + conformance for crowded-room stability.

### ⏳ M36 — Multi-agent marketplace & coordination (RFW/Bids/Auction + blackboard + subchats)
- **Exit:** EXT-MARKETPLACE + EXT-BLACKBOARD + subchat semantics, with fixtures showing RFW→bid→award→workflow→close at scale.

### ⏳ M37 — Service-chaining accountability (provenance graph + responsibility transfer + escrowed actions)
- **Exit:** EXT-PROVENANCE-GRAPH + EXT-RESPONSIBILITY + escrowed action flow binding to TOOL_GATING/M26, with audit-ready conformance.

### ⏳ M38 — Agent media & brand reception feeds (channels/topics, subscriptions, content-level CDN, group policies)
- **Exit:** EXT-CHANNELS + EXT-SUBSCRIPTIONS + EXT-FEEDS + CDN/inbox primitives + profiles for brand receptions and agent-media distribution.

## Suggested dependency order (high level)
1) M16 → M17.1 → M17 → M18 → M33
2) Interop hardening: M22 + M19
3) Trust & tooling: M20 + M21
4) Enterprise controls: M23 + M24 + M26 + M28
5) Crowd-ready bazaars: M35
6) Coordination & service chaining: M36 + M37
7) Internet-scale audit (recommended before large public feeds): M31
8) Agent media & brand reception feeds: M38
9) Optional platform interop: M32
10) Ops + docs completeness: M27 + M34 + M29
