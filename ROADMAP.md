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
- Canonical paths: `docs/`, `schemas/`, `registry/`, `fixtures/`, `conformance/`, `reference/`
- `make validate`, `make conformance-all`, and repo-local tests exist.
- Reference implementation (Python) + TS/JS SDK and templates exist.

### ✅ Completed: Extensions and “mediated blocking” contour
- CAPNEG, OBJECT_RESYNC, POLICY_EVAL, ENFORCEMENT, ALERTS, RESUME, MCP binding are productized with:
  - registries
  - schemas
  - fixtures
  - conformance suites

### ✅ Completed: TLS-like usability layer
- Profiles + profile runner + badges
- Canonical flows & state machines
- Plugfest kit + interop matrix tooling + CI enforcement
- Security review package, self-review, threat-driven negatives
- Canonicalization edge-case TVs (executable evidence)
- Ordering model clarified + linear-chain required (prev_msg_hash)

### ✅ Completed: Adoption “< 1 hour” onboarding baseline
- Start Here entrypoint + drop-ins (copy folder artifacts)
- Quickstart targets + CI quickstart gate
- Sandbox validator usability (external paths, keys, no-signature-verify)
- Anti-drift for drop-in assets and canonical schema selection

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

- ✅ M8.3 EXT-ALERTS alert/error registry + recovery semantics (“TLS alerts”-like)
  - Registered extension artifacts shipped: RFC, registries, schema, conformance suite, and fixtures.
  - Standard categories/codes + recommended actions (retry / remediate / disconnect / escalate) are now repo-validated.

- ✅ M8.4 Canonical state machines and flow diagrams (“handshake diagrams”-like)
  - Core + key extensions (ENFORCEMENT, POLICY_EVAL, OBJECT_RESYNC, CAPNEG, MCP binding).

- ✅ M8.5 Session resumption / reconnect pattern (fast re-onboarding)
  - “Resume contract/thread” pattern leveraging hashes and (optionally) OBJECT_RESYNC.

- ✅ M8.7 Start Here implementer entrypoint shipped (`START_HERE_IMPLEMENTERS.md`).
- ✅ M8.8 Self-contained Core drop-ins shipped (`dropins/aicp-core/{typescript,python}/`).
- ✅ M8.9 TS template Core-envelope validity hardening shipped (`templates/ts-agent/agent.js`).
- ✅ M8.10 TypeScript SDK README minimal-envelope corrections shipped (`sdk/typescript/README.md`).
- ✅ M8.11 Sandbox validator usability hardening shipped (`sandbox/run.py`, `sandbox/README.md`).
- ✅ M8.12 contract_id envelope consistency shipped (Core schema + docs + conformance alignment).
- ✅ M8.13 quickstart anti-rot gate shipped (`.github/workflows/ci.yml` quickstart-smoke job).
- ✅ AP1.1–AP1.4 adoption docs pack shipped (`docs/overview/AICP_STANDARD_OVERVIEW.md`, `docs/guides/*`, `docs/ops/ERROR_AND_RECOVERY.md`).
- ✅ AP2.1–AP2.3 profile negotiation hardening shipped (`registry/aicp_profiles.json`, CAPNEG profile negotiation checks/fixtures, profile downgrade protection).
- ✅ AP3.1 compatibility ladder + badge contract docs + reusable CI workflow snippet shipped (`docs/adoption/COMPATIBILITY_AND_BADGES.md`, `docs/snippets/github-actions/aicp-conformance.yml`).

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
- ✅ M10 Snapshot discipline shipped (deterministic manifest at `dist/releases/snapshots/AICP_SNAPSHOT_0.1.0-dev.json`, generator/validator scripts, and `make validate` integration).

---

- ✅ M11.0 Core `ERROR` message type productized end-to-end (Core payload schema + golden fixture + Core conformance coverage).
- ✅ M11.3 Stable message-type anti-drift governance gate shipped (`scripts/validate_productization_coverage.py`, wired into `make validate`).

- ✅ M11.1 EXT-PARTICIPANTS shipped (RFC + registry IDs + payload schema + fixtures + conformance suite + runner enforcement).
- ✅ M11.2 EXT-TOOL-GATING shipped (RFC + registry IDs + payload schema + fixtures + conformance suite + runner enforcement).

- ✅ M12.1 EXT-IDENTITY-LC productized (payload schema + deterministic fixtures + conformance suite + session-local key verification support).
- ✅ M12.2 EXT-DELEGATION productized (registry message types + payload schema + fixtures + conformance suite + depth/expiry/binding checks).
- ✅ M12.3 EXT-WORKFLOW-SYNC productized (registry message types + payload schema + fixtures + conformance suite + workflow checks).

- ✅ M13.1 EXT-DISPUTES + EXT-SECURITY-ALERTS productized (message-type registry coverage, payload schemas, deterministic fixtures, conformance suites, and runner checks).
- ✅ M13.2 CAPNEG binding refinements shipped (accepted negotiation_result hash/selected bound into contract context with RFC + fixtures + conformance checks).
- ✅ M13.3 policy_reason_codes baseline expansion + namespaced reason-code acceptance shipped.

## ⏳ Ecosystem-facing protocol profiles (platform-optional; protocol-only work)
- ✅ M11 Reception Chat Profile shipped (`AICP-RECEPTION-CHAT@0.1`, plus `RC-RECEPTION-CHAT-SEMANTICS-0.1` conformance suite).
- ✅ M12 Delegated Identity & Acting-on-behalf-of Binding shipped (`EXT-DELEGATED-IDENTITY`, `DI-DELEGATED-IDENTITY-0.1`, `AICP-DELEGATED-IDENTITY@0.1`).
- ✅ M13 Workflow Orchestration & Delegation Profile shipped (`conformance/profiles/PF_AICP_WORKFLOW_ORCHESTRATION_DELEGATION_0.1.json`, `Makefile` conformance-profiles wiring, `registry/aicp_profiles.json`, and `docs/profiles/AICP_Profiles.md`).

---

## ✅ Productization milestone shipped
- ✅ M14 Profile packaging shipped
  - Added profile conformance artifacts for `AICP-MEDIATED-BLOCKING-OPS@0.1`, `AICP-RESUMABLE-SESSIONS@0.1`, and `AICP-RECEPTION-CHAT@0.1`.
  - Wired profile execution and cleanup into `make conformance-profiles` and `make clean`.
  - Updated profile registry and profile catalog docs to move these profiles to available status.
  - ✅ Reception chat semantics hardening shipped with cross-suite suite `conformance/extensions/RC_RECEPTION_CHAT_SEMANTICS_0.1.json`, required by `AICP-RECEPTION-CHAT` profile.

---

## ⏳ Website & messaging (docs-only)
- ⏳ M15 Convert ecosystem user stories into website-ready marketing use cases
  - Source: `docs/marketing/ecosystem_use_cases.md`

---

## Immediate next step
**M15 Website & messaging conversion** is next (docs-only milestone).
