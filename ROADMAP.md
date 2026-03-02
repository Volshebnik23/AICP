# AICP v74 — Roadmap Items (repo-backed)

> Generated from the current repo `ROADMAP.md` + `AICP_Backlog`, plus newly identified protocol gaps (interop + security).
> This file lists **actionable roadmap milestones** (deliverables + exit criteria). It intentionally omits already-shipped items.

_Last updated: 2026-03-02_

## Current / Next

### 🟡 M16 — Numeric canonicalization & safe number policy (Part 2)
- **Why:** Cross-language numeric interop (RFC8785 canonicalization; safe-integer policy).
- **Source:** Already marked current in `ROADMAP.md`.
- **Exit:** RFC8785 numeric canonicalization + safe number policy + fixtures + conformance.

### ✅ M17.1 — Protocol ID & compatibility mark alignment (anti-drift)
- **Why:** Prevent drift between registries/suites/profile marks.
- **Progress:** Conformance reports now emit protocol `aicp_version` from suite/profile inputs, and `make validate` includes a single anti-drift lint gate for extensions/profiles/bindings mark alignment + global mark uniqueness across `conformance/**`.
- **Source:** Implemented in this sprint.
- **Exit:** Lint gates + aligned names/marks across repo.

### 🔜 Next milestone — M17 Stability graduation program
- **Next concrete step:** Define the first stable baseline set and add validator rules for promotion eligibility metadata in registries.

## Planned milestones (protocol maturity & ecosystem scale)

### ⏳ M17 — Stability graduation program (reduce experimental sprawl safely)
- **Exit:** “Stable baseline set” defined + validator rules enforce stable metadata + first promotions.

### ⏳ M18 — Release discipline (changelog + compatibility policy + errata cadence)
- **Exit:** RELEASE_NOTES filled; compatibility policy; release checklist; errata cadence.

### ⏳ M33 — Legal readiness pack (licenses, patents, governance) for vendor adoption
- **Exit:** Clear LICENSE+PATENTS+contribution policy+trademark policy enabling commercial distribution.

### ⏳ M19 — Protocol Adapter / Gateway quickstart kit (CI-first onboarding)
- **Exit:** Template adapter skeleton + CI snippets + “<1 hour” onboarding for a new platform.

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

## Suggested dependency order (high level)
1) M16 → M17.1 → M17 → M18 → M33  
2) Interop hardening: M22 + M19  
3) Trust & tooling: M20 + M21 + M30  
4) Enterprise controls: M23 + M24 + M26 + M28  
5) Internet-scale audit: M31  
6) Optional platform interop: M32  
7) Ops + docs completeness: M27 + M34 + M29

