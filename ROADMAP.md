# AICP v77 — Roadmap Items (repo-backed)

> Generated from the current repo `ROADMAP.md` + `AICP_Backlog`, plus newly identified protocol gaps (interop + security).
> This file lists **actionable roadmap milestones** (deliverables + exit criteria). It intentionally omits already-shipped items.

_Last updated: 2026-03-02_

## Current / Next

### ✅ M16a — Safe-integer policy + numeric guardrails (staged decision)
- **Progress:** Implemented across reference, SDK, and dropins with unsafe-integer expected-fail conformance coverage.

### ✅ M16b — RFC8785 float canonicalization
- **Progress:** Finite float canonicalization is implemented with shared float64 vectors (`conformance/vectors/rfc8785_float64_vectors.json`) and cross-language parity tests.
- **Guardrails retained:** non-finite numbers are rejected; unsafe integers remain disallowed.

### ✅ M17.1 — Protocol ID & compatibility mark alignment (anti-drift)
- **Progress:** Conformance reports emit protocol `aicp_version` from suite/profile inputs; anti-drift mark lint gate is active.

### ✅ M18 — Release discipline (changelog + compatibility policy + errata cadence)
- **Progress:** Compatibility policy, release checklist, and errata cadence are documented and validated (`scripts/validate_errata.py`).

### ✅ M19 — Protocol Adapter / Gateway quickstart kit (CI-first onboarding)
- **Progress:** Shipped guide + template in `docs/guides/Protocol_Adapter_Gateway.md` and `templates/protocol-adapter/` with CI snippet.

### 🔜 Next milestone — M22 Transport bindings and channel properties
- **Why now:** Core numeric/version drift and baseline release discipline are now landed; next highest interop risk is transport semantic divergence.
- **Next concrete step:** Define canonical HTTP/WS/SSE replay/idempotency/overload semantics with conformance cases.

### 🔜 Next milestone — M17 Stability graduation program
- **Next concrete step:** Define the first stable baseline set and add validator rules for promotion eligibility metadata in registries.

## Planned milestones (protocol maturity & ecosystem scale)

### ✅ M17 — Stability graduation baseline (first promotions)
- **Progress:** Stable baseline set includes `EXT-CAPNEG`, `EXT-ENFORCEMENT`, `EXT-POLICY-EVAL`, and profile `AICP-BASE@0.1`; validators enforce stable/deprecated metadata and stable extension productization coverage.
- **Next promotion candidates:** `EXT-ALERTS`, `EXT-DELEGATION`.
- **Exit:** “Stable baseline set” defined + validator rules enforce stable metadata + first promotions.

### ⏳ M33 — Legal readiness pack (licenses, patents, governance) for vendor adoption
- **Exit:** Clear LICENSE+PATENTS+contribution policy+trademark policy enabling commercial distribution.

### ⏳ M20 — Trust anchors & issuer attestations (internet-scale trust signals)
- **Exit:** RFC + registries + fixtures + conformance for trust anchors/attestations.

### ⏳ M21 — Revocation/status channel (OCSP/CRL analog, protocol-level)
- **Exit:** Status request/response or status object format + cache/staleness rules + conformance.

### ⏳ M30 — Tool/Resource/Prompt supply-chain security (immutable manifests + pinning + anti-shadowing)
- **Exit:** Signed manifests + contract pinning + tool-gating integration + conformance.

### ⏳ M22 — Transport bindings and channel properties (HTTP/WS + anti-replay + quotas + streaming)
- **Exit:** Canonical HTTP/SSE + WS semantics incl. anti-replay, idempotency, overload, chunking + conformance.

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
3) Trust & tooling: M20 + M21 + M30  
4) Enterprise controls: M23 + M24 + M26 + M28  
5) Crowd-ready bazaars: M35  
6) Coordination & service chaining: M36 + M37  
7) Internet-scale audit (recommended before large public feeds): M31  
8) Agent media & brand reception feeds: M38  
9) Optional platform interop: M32  
10) Ops + docs completeness: M27 + M34 + M29
