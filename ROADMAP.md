## AICP — Agent Interaction Content Protocol

“An open content-layer protocol for agent-to-agent interaction with enforceable policies.”

## Roadmap and current status (repo-backed)

This roadmap reflects the **actual repository artifacts**, not only content embedded in the Suite index.
It separates: (A) Spec authoring (text), and (B) Productization (executable, enforceable deliverables).

AICP uses versions for technical evolution, but roadmap sequencing is **dependency-based** (technical prerequisites first), not product-release sequencing.
AICP is to content-layer agent interaction what HTTPS/TLS is to secure transport: a standard protocol, not an infrastructure provider (e.g., not a “CA” or a hosted enforcement platform).

**Suite document:** `docs/suite/AICP_Suite_Overview_and_Skeleton_v0.1.21_EN.md`  
**Core canonical paths:** `docs/core/`, `schemas/core/`, `fixtures/`

### Legend
- ✅ **Shipped**: exists in-repo as a standalone artifact and is runnable/usable.
- 🟡 **Current**: active milestone in progress.
- 🔜 **Next**: next milestone to execute.
- ⏳ **Later**: planned, but not in the immediate milestone.

---

## A) Spec authoring status (text completeness)

- ✅ Suite overview/index is present at `docs/suite/AICP_Suite_Overview_and_Skeleton_v0.1.21_EN.md`.
- ✅ Core normative spec is diff-friendly Markdown under `docs/core/`.
- ✅ Standalone RFC documents exist under:
  - `docs/rfc/`
  - `docs/extensions/`
  - `docs/bindings/`

---

## B) Productization status (implementable + enforceable)

### ✅ Completed: Canonical repo layout + registries + conformance + references
- ✅ Core schemas, registries, fixtures, conformance runner and reports
- ✅ Reference implementations and drop-ins
- ✅ Anti-drift gates (registry/schema/fixtures/conformance coverage) + snapshot discipline

### ✅ Completed: Extensions and “mediated blocking” contour
- ✅ CAPNEG, ENFORCEMENT, POLICY_EVAL, ALERTS, RESUME, OBJECT_RESYNC
- ✅ Participants, tool gating, identity lifecycle, delegation, workflow sync
- ✅ Disputes, security alerts, delegated identity (optional)

### ✅ Completed: TLS-like usability layer
- ✅ Profiles catalog + profile conformance runner
- ✅ Plugfest kit scaffolding + interop matrix tool + errata workflow note
- ✅ Implementer quickstarts

### ✅ Completed: Adoption “< 1 hour” onboarding baseline
- ✅ drop-ins, START_HERE_IMPLEMENTERS, sandbox validation, templates
- ✅ CI gates (validate + conformance-all + conformance-profiles + snapshot)

---

## ✅ Productization milestone shipped
- ✅ M14 Profile packaging shipped
  - Added profile conformance artifacts and wired them into `make conformance-profiles`.
  - Updated profile registry and profile catalog docs to move profiles to available status.

---

## ✅ Productization milestone shipped
- ✅ M13 Workflow Orchestration & Delegation Profile shipped
  - Profile: `AICP-WORKFLOW-ORCHESTRATION-DELEGATION@0.1`
  - Bundles: POLICY_EVAL, TOOL_GATING, DELEGATION, WORKFLOW_SYNC, RESUME/OBJECT_RESYNC, ALERTS, SECURITY_ALERTS (+ Core + CAPNEG)

---

## ⏳ Website & messaging (docs-only)
- ⏳ M15 Convert ecosystem user stories into website-ready marketing use cases
  - Source: `docs/marketing/ecosystem_use_cases.md`

---

# C) Next growth milestones (protocol maturity & ecosystem scale)

These milestones are driven by **real adoption constraints** observed in implementer onboarding and enterprise workflows. They remain protocol-scoped (RFC/registries/schemas/fixtures/conformance/profiles/bindings).

## 🟡 M16 Numeric canonicalization and safe number policy (RFC8785; closes OQ-0001)
- **Part 1 (shipped):** strict float rejection parity across reference + drop-ins + a numeric guardrail conformance suite (prevents float creep).
- **Part 2 (next):** define and implement RFC8785 numeric normalization + a safe integer/decimal policy, with cross-language parity fixtures and conformance.
- Outcome: avoid surprise float/bigint incompatibilities across languages.

## 🔜 M17.1 Protocol ID & compatibility mark alignment (anti-drift)
- Fix **SECURITY ALERT** naming drift across artifacts:
  - Keep registry extension id canonical as `EXT-SECURITY-ALERT` (singular)
  - Align suite filename/suite_id/compatibility_mark to singular (currently plural in SA suite)
  - Update all references (profiles, Makefile wiring, docs, snapshot)
- Fix **Reception Chat semantics** classification:
  - `RC_RECEPTION_CHAT_SEMANTICS` is a cross-suite semantics suite, not an extension; update its compatibility mark to a non-extension prefix (e.g., `AICP-SUITE-*`) **or** register a matching extension id + RFC (choose one path, but be consistent).
- Add an **anti-drift lint**: if a suite compatibility mark starts with `AICP-EXT-...`, the corresponding `EXT-...` must exist in `registry/extension_ids.json`.


## ⏳ M17 Stability graduation program (reduce “experimental sprawl” responsibly)
- Goal: define and enforce criteria for promoting entries from experimental → stable.
- Deliverables: compatibility/stability policy + registry validation rules + first stable baseline set.

## ⏳ M18 Release discipline (changelog + compatibility policy + release checklist)
- Goal: make protocol adoption safe for mass deployment.
- Deliverables: filled RELEASE_NOTES, compatibility policy doc, release checklist, deprecation rules.

## 🔜 M18.1 Error & Recovery canonicalization
- Fix adoption-ready docs drift:
  - In `docs/ops/ERROR_AND_RECOVERY.md`, remove `DENY` as if it were an `EXT-ALERTS` action id; keep only the EXT-ALERTS action taxonomy (`RETRY/REMEDIATE/DISCONNECT/ESCALATE/ACK_REQUIRED/NO_ACTION`), and describe deny as platform behavior in plain language.
- Declare **one source of truth**:
  - RFC `docs/rfc/RFC_Error_Model_and_Recovery.md` is normative; `docs/ops/ERROR_AND_RECOVERY.md` is a non-normative implementer guide (add reciprocal links).

## ⏳ M19 Protocol Adapter / Gateway quickstart kit (CI-first onboarding)
- Goal: standardized “adapter-first” integration path (parse/validate AICP, map to internal events, run conformance in CI, CAPNEG as filter).
- Deliverables: adapter guide + minimal deployable skeleton + CI templates + implementer docs update.

## ⏳ M20 Trust anchors and issuer attestations (internet-scale trust)
- Goal: standardize trust anchors, issuer attestations, and minimal trust signals.
- Deliverables: RFC + registries + schemas + conformance for attestations.

## ⏳ M21 Revocation/status channel (OCSP/CRL analog)
- Goal: real-time or near-real-time revocation/status verification for keys and bindings.
- Deliverables: RFC/extension + fixtures + conformance.

## ⏳ M22 Transport bindings and channel properties
- Goal: practical interop across vendors via standard bindings.
- Deliverables: HTTP/WS binding RFCs + anti-replay/session binding + quotas/backpressure patterns.

## ⏳ M23 Confidentiality & selective disclosure modes
- Goal: enterprise-ready enforcement visibility modes tied to contract/CAPNEG.
- Deliverables: RFC + conformance checks for selective disclosure behavior.

## ⏳ M24 Redaction standard + retention/deletion policy
- Goal: allow verifiable transcripts under redaction and contractual retention.
- Deliverables: EXT-REDACTION + retention policy conventions + conformance.

## ⏳ M25 Policy semantic interoperability profiles
- Goal: semantic convergence (not only packaging) via stable policy profiles.
- Deliverables: OPA/Rego profile, ABAC/RBAC profile, LLM-safety profile; stabilize key registries.

## ⏳ M26 Human-in-the-loop primitive (approval / step-up)
- Goal: explicit, machine-checkable approval steps bound to tool calls/content.
- Deliverables: extension + fixtures + conformance + profile integration.

## ⏳ M27 Production attributes: tracing, SLA signals, metering
- Goal: production-grade operations across vendor boundaries.
- Deliverables: observability extension + SLA/overload signals + optional metering objects.

## ⏳ M28 IAM bridge (OAuth/OIDC mapping)
- Goal: standard mapping between AICP delegation/tool gating and enterprise IAM.
- Deliverables: binding RFCs + conformance-guided examples.

## ⏳ M29 Enterprise domain bindings (OpenAPI/OData/OPA/ABAC)
- Goal: ensure AICP isn’t “content protocol in a vacuum”.
- Deliverables: bindings to common enterprise models and tool descriptions.

---

## Immediate next step
- **Next technical milestone:** M17.1 Protocol ID & compatibility mark alignment (anti-drift) + M18.1 Error & Recovery canonicalization.
- After that: M16 Part 2 (RFC8785 numeric handling + safe number policy).
- Docs-only track: M15 Website & messaging conversion.
