# AICP v84 — Roadmap Items (repo-backed)

> Generated from the current repo `ROADMAP.md` + `AICP_Backlog`, plus newly identified protocol gaps (interop + security).
> This file lists **actionable roadmap milestones** (deliverables + exit criteria). It intentionally omits already-shipped items.

_Last updated: 2026-03-02_

## Current / Next

### ✅ M16b — RFC8785 float canonicalization
- **Progress:** Finite-float canonicalization landed with cross-language vector parity coverage and updated conformance/docs.

### ✅ M17 — Stability graduation baseline (first promotions)
- **Progress:** `EXT-ENFORCEMENT` and `EXT-POLICY-EVAL` promoted to stable with anchored spec refs and productization coverage.

### ✅ M18 — Release discipline (changelog + compatibility policy + errata cadence)
- **Progress:** Errata cadence documented and validator wired into `make validate`.

### ✅ M19 — Protocol Adapter / Gateway quickstart kit (CI-first onboarding)
- **Progress:** Adapter/gateway artifacts are present and roadmap state is now aligned to shipped repo reality.

### 🚧 M22 — Transport bindings and channel properties (started)
- **Step 1 complete:** channel properties registry + canonical schema landed, and CAPNEG now carries binding/channel-property negotiation fields.
- **Step 2 partial:** MCP-backed CAPNEG conformance evidence added (CN-09) with binding/channel-property negotiation invariant checks in runner.
- **Step 2 hardening:** binding ID normalization shipped for HTTP/BUS (`BIND-HTTP-0.1` / `BIND-BUS-0.1`) with deprecated alias mapping retained for compatibility.
- **Step 2 guardrails:** schema/registry alignment validator added to prevent channel-properties drift between canonical binding schema and CAPNEG embedded defs.
- **Step 2 evidence:** TB-HTTP-0.1 binding conformance suite + fixtures + report are now shipped for HTTP send/poll/head/overload semantics.
- **Next concrete step:** extend transport conformance to HTTP/WS WS streaming framing + chunking/backpressure semantics remain the next step (M22b part 2).

## Planned milestones (protocol maturity & ecosystem scale)

### ✅ M16a — Safe-integer policy + numeric guardrails (staged decision)
- **Progress:** Canonicalization enforces integers within ±(2^53−1), unsafe integer expected-fail fixtures are covered in conformance, and OQ-0001 was staged pending M16b.
- **Exit:** Safe-integer policy implemented across reference/SDK + conformance guardrails + docs.

### ✅ M17.1 — Protocol ID & compatibility mark alignment (anti-drift)
- **Progress:** Conformance reports emit protocol `aicp_version` from suite/profile inputs, and `make validate` includes anti-drift lint for extensions/profiles/bindings mark alignment + global mark uniqueness across `conformance/**`.
- **Exit:** Lint gates + aligned names/marks across repo.

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
