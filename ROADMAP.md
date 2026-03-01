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
- ✅ Core v0.1 normative artifacts are present at canonical paths:
  - `docs/core/AICP_Core_v0.1_Normative.md`
  - `schemas/core/`
  - `fixtures/`
- ✅ Standalone RFC documents for registries/error model/extensions/bindings/governance/interop are present under:
  - `docs/rfc/`
  - `docs/extensions/`
  - `docs/bindings/`

---

## B) Productization status (implementable + enforceable)

### ✅ Completed (M1): Canonical repo layout
- Core artifacts are in canonical repository locations:
  - `docs/core/` (normative Core docs)
  - `schemas/core/` (Core schemas)
  - `fixtures/` (TV + golden transcripts + keys)
- Validation and release hygiene commands are available in `Makefile`:
  - `make validate`
  - `make test`
  - `make release-check`

### ✅ Completed (M2): Standalone RFC docs + roadmap sync + release-check hardening
- Suite maintained as umbrella index in `docs/suite/`.
- Standalone RFCs maintained under `docs/rfc/`, `docs/extensions/`, `docs/bindings/`.
- `release-check` verifies canonical Core artifacts in addition to hygiene files.

### ✅ Completed (M3): Machine-readable registries as first-class artifacts
- Registry artifacts are available under `registry/*.json`.
- Registry validation is enforced via `scripts/validate_registry.py` in `make validate` and CI.

### ✅ Completed (M4): Conformance as a product (runner + reports)
**Goal:** “AICP-compatible” becomes measurable.
- Add `/conformance` suite catalogs (Core + opt-in EXT suites).
- Add a conformance runner CLI that outputs a **compatibility report** (machine-readable).
- Run conformance in CI.

### ✅ Completed (M5): Reference implementations in-repo
- `/reference/python` (minimum correct implementation).
- `/sdk/typescript` (validator/hash utilities) + templates.

### ✅ Completed (M6): Expanded golden transcripts + negative conformance
- Golden coverage includes revoke, unknown-base+resync, invalid signature, duplicate message_id replay scenarios.
- Expected-fail support in conformance.

### ✅ Completed (M7.x): Extension & binding productization line
- ✅ M7.1: EXT-CAPNEG productization
- ✅ M7.2: EXT-OBJECT-RESYNC productization
- ✅ M7.3: EXT-POLICY-EVAL productization + hardening
- ✅ M7.4: BINDINGS productization (starting with MCP)
- ✅ M7.5: Developer Experience & Adoption Kit (DX)
- ✅ M7.6: EXT-ENFORCEMENT productization (blocking enforcement contour)
- ✅ M7.7: Roadmap sync discipline (process hardening)

---

## ✅ Completed: Interop readiness package (TLS-like usability & interoperability)
- ✅ M8.1 Personas → user stories → feature sets → profile mapping
- ✅ M8.2 AICP Profiles (normative doc) + conformance badges
- ✅ M8.3 EXT-ALERTS (“TLS alerts”-like) + recovery semantics
- ✅ M8.4 Canonical state machines and flow diagrams
- ✅ M8.5 EXT-RESUME (session resumption / reconnect)
- ✅ M8.6 Plugfest kit scaffolding + interop matrix tool + errata workflow note
- ✅ M8.6.1 Interop community-ready hardening:
  - interop matrix CI staleness checks
  - submission validation (implementation_id matches folder name)
  - schema validation for changed manifests in CI

- 🔜 M8.1 Personas → user stories → feature sets → profile mapping (source-of-truth)
  - Create a canonical mapping doc that justifies profiles by real personas and use cases.

- 🔜 M8.2 AICP Profiles (normative document) + conformance badges (profile-level compatibility)
  - Define profiles as named bundles of required extensions + canonical flows.
  - Provide machine-readable profile definitions and a profile conformance runner that aggregates suite results into a profile badge.

- ✅ M8.3 EXT-ALERTS alert/error registry + recovery semantics (“TLS alerts”-like)
  - Registered extension artifacts shipped: RFC, registries, schema, conformance suite, and fixtures.
  - Standard categories/codes + recommended actions (retry / remediate / disconnect / escalate) are now repo-validated.

- ✅ M8.4 Canonical state machines and flow diagrams (“handshake diagrams”-like)
  - Core + key extensions (ENFORCEMENT, POLICY_EVAL, OBJECT_RESYNC, CAPNEG, MCP binding).

- ✅ M8.5 Session resumption / reconnect pattern (fast re-onboarding)
  - “Resume contract/thread” pattern leveraging hashes and (optionally) OBJECT_RESYNC.

- 🟡 M8.6 Plugfest kit + interop report + errata workflow
  - `/interop/*` artifacts, test vectors, interop report format.
  - Interop matrix regeneration + staleness checks are enforced for submission-related PR changes.
  - Changed-manifest schema validation is enforced for `interop/submissions/*/implementation.json` in interop CI.

- ✅ M8.7 Start Here implementer entrypoint shipped (`START_HERE_IMPLEMENTERS.md`).
- ✅ M8.8 Self-contained Core drop-ins shipped (`dropins/aicp-core/{typescript,python}/`).
- ✅ M8.9 TS template Core-envelope validity hardening shipped (`templates/ts-agent/agent.js`).
- ✅ M8.10 TypeScript SDK README minimal-envelope corrections shipped (`sdk/typescript/README.md`).
- ✅ M8.11 Sandbox validator usability hardening shipped (`sandbox/run.py`, `sandbox/README.md`).
- ✅ M8.12 contract_id envelope consistency shipped (Core schema + docs + conformance alignment).
- ✅ M8.13 quickstart anti-rot gate shipped (`.github/workflows/ci.yml` quickstart-smoke job).
- ✅ AP1.1–AP1.4 adoption docs pack shipped (`docs/overview/AICP_STANDARD_OVERVIEW.md`, `docs/guides/*`, `docs/ops/ERROR_AND_RECOVERY.md`).
- ✅ AP2.1–AP2.3 profile negotiation hardening shipped (`registry/aicp_profiles.json`, CAPNEG profile negotiation checks/fixtures, profile downgrade protection).

---

## ⏳ Later milestones (hardening)
- 🟡 M9 External security review artifacts and remediation log:
  - `/security_review/*`
  - M9 security review package scaffolding is now available in-repo.
  - ✅ M9.1 Internal dry-run security self-review completed (`security_review/SELF_REVIEW.md`).
  - ✅ M9.2 Behavioral enforcement simulation demo added (`demos/enforcement_behavioral/`).
  - ✅ M9.2 threat-driven demo conformance expansion shipped (`conformance/demos/DEMO_ENFORCEMENT_BEHAVIORAL_0.1.json`, `ENF-AUTH-01`).
  - ✅ M9.3 threat-to-tests coverage map + CAPNEG/RESUME negative checks shipped (`security_review/COVERAGE_MAP.md`, `CN-DOWNGRADE-01`, `RS-LOOP-01`).
  - ✅ M9.3 anti-drift + Policy Core formalization + strict badge semantics + glossary update shipped.
  - ✅ M9.4 canonicalization edge-case vectors + drop-in asset anti-drift checks shipped.
  - ✅ M9.5 ordering model clarity + linear prev_msg_hash requirement + expanded drop-in asset parity checks shipped.
  - ✅ M9.6 DoS/amplification/abuse hardening guidance + deterministic ops checks shipped (`security_review/OPS_HARDENING_GUIDE.md`, `conformance/ops/OPS_HARDENING_0.1.json`, `fixtures/ops/`).
  - ✅ M9.7 Signed-path security evidence shipped for mediated blocking (`conformance/security/SIG_SIGNED_PATHS_0.1.json`, `fixtures/security/signed_paths/`, deterministic TEST-only keys).
- 🔜 M10 Snapshot discipline (optional, when needed):
  - feature freeze rules, registry snapshot, compatibility marks, packaging/checksums

---

## ⏳ Ecosystem-facing protocol profiles (platform-optional; protocol-only work)
- ⏳ M11 Reception Chat Profile (rules + onboarding semantics)
- ⏳ M12 Delegated Identity & Acting-on-behalf-of Binding (Auth/IAM friendly)
- ⏳ M13 Workflow Orchestration & Delegation Profile (platform may enforce)

---

## ⏳ Website & messaging (docs-only)
- ⏳ M14 Convert ecosystem user stories into website-ready marketing use cases
  - Source: `docs/marketing/ecosystem_use_cases.md`

---

## Immediate next step
**M10 (snapshot discipline + compatibility packaging hardening)** is next.
