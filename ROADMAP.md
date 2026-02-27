## AICP — Agent Interaction Content Protocol

“An open content-layer protocol for agent-to-agent interaction with enforceable policies.”

## Roadmap and current status (repo-backed)

This roadmap reflects the **actual repository artifacts**, not only content embedded in the Suite index.
It separates: (A) Spec authoring (text), and (B) Productization (executable, enforceable deliverables).

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
**Acceptance:** one command produces pass/fail + report; CI runs Core suite.

### ✅ Completed (M5): Reference implementations in-repo
**Goal:** provide minimal, correct reference implementations that are easy to adopt and test.
- Add `/reference/python` (minimum correct implementation).
- Optionally add `/reference/typescript` with parity notes.
**Acceptance:** reference implementation tests are runnable via the one-command standard.

### ✅ Completed (M6): Expanded golden transcripts + negative conformance
- Core golden coverage now includes revoke, unknown-base+resync, invalid signature, and duplicate message_id replay scenarios.
- Conformance supports expected-failure handling for controlled negative outcomes.

### ✅ Completed (M7.1): EXT-CAPNEG productization
- Add EXT-CAPNEG payload schemas under `schemas/extensions/`.
- Add CAPNEG extension fixtures under `fixtures/extensions/capneg/`.
- Add extension conformance suite under `conformance/extensions/`.

### ✅ Completed (M7.2): EXT-OBJECT-RESYNC productization
### ✅ Completed (M7.3): EXT-POLICY-EVAL productization + hardening
- Naming consistency enforcement in canonical Markdown sources (DOCX removed from PR-critical gates)
- Core taxonomy alignment on `CONTEXT_AMEND`
- Core payload schema enforcement in conformance/tests
### 🟡 Current milestone (M7.4): BINDINGS productization (starting with MCP)
**Goal:** make at least one transport binding adoptable with the same rigor as Core/EXT:
schemas + fixtures + binding conformance suite + tests + docs.
**Target (MCP first):**
- `schemas/bindings/` (binding schema for MCP tools/call wrappers)
- `fixtures/bindings/mcp/` (binding cases)
- `conformance/bindings/` (TB_MCP suite) + runner support
- tests (pytest) that execute the binding suite
- docs updates in `docs/bindings/RFC_BIND_MCP.md` and `conformance/README.md`

### ✅ Completed (M7.5): Developer Experience & Adoption Kit (DX)
**Goal:** reduce perceived ceremony for agent builders and enforcer platform builders.
**Shipped artifacts:**
- `docs/index.md` (landing page), `docs/branding.md` (canonical terms), `CITATION.cff`
- TS SDK starter: `sdk/typescript/` (TV-01 test)
- copy-paste template: `templates/ts-agent/`
- sandbox debug thread: `sandbox/`

(After M7.4, proceed to plugfest/security-review milestones.)

### ⏳ Later milestones (productization hardening)
- ⏳ M8 Plugfest kit + Interop report + Errata process:
  - `/interop/*` artifacts
- ⏳ M9 External security review artifacts and remediation log:
  - `/security_review/*`
- ⏳ M10 Release Candidate → v0.1.0:
  - feature freeze, registry snapshot, final compatibility marks, release packaging, checksums

---

## Immediate next step
**M7.4 (BINDINGS productization, starting with MCP)** is current.
