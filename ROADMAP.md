## Roadmap and current status (repo-backed)

This roadmap reflects the **actual repository artifacts**, not only content embedded in the Suite index.
It separates: (A) Spec authoring (text), and (B) Productization (executable, enforceable deliverables).

**Repo snapshot:** AICP-main_v3  
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
  - `docs/core/AICP_Core_v0.1_Normative_0.1.0.docx`
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

### 🟡 Current milestone (M2): Standalone RFC docs + roadmap sync + release-check hardening
**Goal:** reduce monolith-spec risk and keep status/release gates repo-verifiable.
- Maintain Suite as umbrella index in `docs/suite/`.
- Keep standalone RFCs as canonical sources under `docs/rfc/`, `docs/extensions/`, `docs/bindings/`.
- Ensure release-check verifies canonical Core artifacts in addition to hygiene files.

### 🟡 Current milestone (M3): Machine-readable registries as first-class artifacts
**Goal:** prevent collisions and enable third-party ecosystems.
- Create `registry/*.json` per the Registry RFC (message types, profiles, bindings, codes, etc.).
- Add `scripts/validate_registry.py` and run it in `make validate` + CI.
**Acceptance:** registry validation runs in CI; changes are reviewed and collision-free.

### 🔜 Next milestone (M4): Conformance as a product (runner + reports)
**Goal:** “AICP-compatible” becomes measurable.
- Add `/conformance` suite catalogs (Core + opt-in EXT suites).
- Add a conformance runner CLI that outputs a **compatibility report** (machine-readable).
- Run conformance in CI.
**Acceptance:** one command produces pass/fail + report; CI runs Core suite.

### 🔜 Next milestone (M5): Reference implementations in-repo
**Goal:** provide minimal, correct reference implementations that are easy to adopt and test.
- Add `/reference/python` (minimum correct implementation).
- Optionally add `/reference/typescript` with parity notes.
**Acceptance:** reference implementation tests are runnable via the one-command standard.

### ⏳ Later milestones (productization hardening)
- ⏳ M6 Expand golden transcripts to cover real-world recovery and consent flows:
  - revoke, unknown-base+resync, invalid signature, duplicate message_id, etc.
- ⏳ M7 Plugfest kit + Interop report + Errata process:
  - `/interop/*` artifacts
- ⏳ M8 External security review artifacts and remediation log:
  - `/security_review/*`
- ⏳ M9 Release Candidate → v0.1.0:
  - feature freeze, registry snapshot, final compatibility marks, release packaging, checksums

---

## Immediate next step
**M2 (Standalone RFC docs + roadmap sync + release-check hardening)** is current.
