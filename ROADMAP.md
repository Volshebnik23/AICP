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

- ✅ M13.1 EXT-DISPUTES + EXT-SECURITY-ALERT productized (message-type registry coverage, payload schemas, deterministic fixtures, conformance suites, and runner checks).
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

## ✅ Productization milestone shipped
- ✅ M14 Profile packaging shipped
  - Added profile conformance artifacts for `AICP-MEDIATED-BLOCKING-OPS@0.1`, `AICP-RESUMABLE-SESSIONS@0.1`, and `AICP-RECEPTION-CHAT@0.1`.
  - Wired profile execution and cleanup into `make conformance-profiles` and `make clean`.
  - Updated profile registry and profile catalog docs to move these profiles to available status.
  - ✅ Reception chat semantics hardening shipped with cross-suite suite `conformance/extensions/RC_RECEPTION_CHAT_SEMANTICS_0.1.json`, required by `AICP-RECEPTION-CHAT` profile.

## 🔜 M17.1 Protocol ID & compatibility mark alignment (anti-drift)
- Fix **SECURITY ALERT** naming drift across artifacts:
  - Keep registry extension id canonical as `EXT-SECURITY-ALERT` (singular)
  - Align suite filename/suite_id/compatibility_mark to singular (currently plural in SA suite)
  - Update all references (profiles, Makefile wiring, docs, snapshot)
- Fix **Reception Chat semantics** classification:
  - `RC_RECEPTION_CHAT_SEMANTICS` is a cross-suite semantics suite, not an extension; update its compatibility mark to a non-extension prefix (e.g., `AICP-SUITE-*`) **or** register a matching extension id + RFC (choose one path, but be consistent).
- Add an **anti-drift lint**: if a suite compatibility mark starts with `AICP-EXT-...`, the corresponding `EXT-...` must exist in `registry/extension_ids.json`.

## ⏳ Website & messaging (docs-only)
- ⏳ M15 Convert ecosystem user stories into website-ready marketing use cases
  - Source: `docs/marketing/ecosystem_use_cases.md`

---


## ✅ M16 Numeric canonicalization & safe number policy shipped
- ✅ Part 1 shipped (historical): float rejection parity across reference/dropins.
- ✅ Part 2 shipped: finite float support with deterministic RFC8785-style normalization in Python reference/dropin and TypeScript SDK/dropin, safe-integer enforcement (`abs(n) <= 9007199254740991`), and numeric guardrail fixtures/suite updates (`fixtures/core/numeric/NUM-01_float_payload_pass.jsonl`, `fixtures/core/numeric/NUM-02_unsafe_integer_expected_fail.jsonl`, `conformance/core/CT_NUMERIC_GUARDRAILS_0.1.json`).

---


## ✅ D1–D4 protocol consistency fixes shipped
- ✅ D1 SECURITY-ALERT naming alignment shipped (suite renamed to `conformance/extensions/SA_SECURITY_ALERT_0.1.json` with singular suite id/compatibility mark to match `EXT-SECURITY-ALERT`).
- ✅ D2 Reception-chat semantics suite mark reclassified to non-extension (`AICP-SUITE-RECEPTION-CHAT-SEMANTICS-0.1`) to avoid unregistered EXT claims.
- ✅ D3/D4 Error & recovery docs canonicalized: ops guide now uses EXT-ALERTS action IDs only and references RFC as normative source; RFC links back to ops guide.
- ✅ Added compatibility-mark anti-drift gate (`scripts/validate_compatibility_marks.py`) and wired it into `make validate`.

---

## Immediate next step
**M15 Website & messaging conversion** is next (docs-focused milestone).
