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

---

## 🔜 Implementer onboarding (< 1 hour) & copy-paste integration kit
**Goal:** a developer can copy/paste or drop-in AICP Core support in under an hour with a deterministic smoke test.

- 🔜 M8.7 “Start Here” single entrypoint for implementers
  - Add `START_HERE_IMPLEMENTERS.md` (or `INTEGRATE.md`) and link it at the top of `README.md`.
  - Include a role × language table: what to copy, what to run, and the smoke check.
- 🔜 M8.8 Self-contained drop-ins (copy folder)
  - Add `dropins/aicp-core/typescript/` and `dropins/aicp-core/python/` as the ONLY recommended “copy this folder” artifacts.
  - Include `assets/` (schemas + minimal registries or an aggregate) and a minimal README + “10 lines” example.
- 🔜 M8.9 Fix TS template to generate valid Core messages
  - `templates/ts-agent/agent.js` must include required Core fields (`timestamp`, `sender`, …) and stop using repo-relative imports.
- 🔜 M8.10 Fix misleading TypeScript SDK docs example
  - `sdk/typescript/README.md` examples must show a valid minimal envelope body (incl. required fields).
- 🔜 M8.11 Sandbox validator usability for external paths + custom keys
  - `sandbox/run.py`: do not crash on non-repo paths; add `--keys` and `--no-signature-verify`.
  - Evolve towards an installable `aicp-validate` style CLI if feasible.
- 🔜 M8.12 Clarify `contract_id` requirement consistently (Suite vs schema)
  - Decide and document: “MUST for contract-scoped messages; MAY for pre-contract flows”, OR make it MUST everywhere and update everything accordingly.
- 🔜 M8.13 Add onboarding smoke tests in Makefile/CI
  - `make quickstart-ts` / `make quickstart-py`: generate minimal JSONL and validate it.
  - Add a CI gate so quickstart cannot silently rot.

---

## ✅ Security review package
- ✅ M9: Security review scaffolding (`security_review/*`)
- ✅ M9.1: Internal self-review dry-run (`security_review/SELF_REVIEW.md`)
- ✅ M9.2: Behavioral enforcement demo as a conformance-backed demo suite + threat-driven negatives (malicious mediator, spoofed verdict, replay)
- 🟡 M9.3: Threat→Tests coverage map + targeted threat-driven negatives
  - CAPNEG downgrade/spoof negative evidence
  - RESUME forced-loop negative evidence

---

## ⏳ Additional hardening (remaining items to fully “prove” interoperability & security posture)
These items are not “new features”, but close important proof/interop gaps.

- ⏳ M9.4 Canonicalization edge cases (unicode/number/confusables)
  - Add dedicated fixtures and checks to prevent hash mismatches across implementations.
- ⏳ M9.5 Concurrency / ordering model clarity
  - Document that mediated channels assume mediator serialization.
  - If p2p concurrency is a goal, define an explicit algorithm/profile (not “hints”).
- ⏳ M9.6 DoS / amplification / abuse hardening guidance (+ optional lint checks)
  - RESYNC/RESUME cadence guidance, response size guidance, loop detection patterns.
- ⏳ M9.7 Signed-path evidence (crypto “reality”, not just format)
  - Add at least one canonical signed transcript path (verdict/alert signed) and ensure badges are only awarded when signature verification is actually performed.

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
Finish **M9.3** (coverage map + CAPNEG/RESUME threat negatives), then proceed with **M8.7–M8.13** (implementer onboarding <1 hour).
