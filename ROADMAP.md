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

## Adoption-ready track (public standard readiness)
This track turns AICP from “strong repo” into an **adoption-ready standard**: clear positioning, guides, productized profiles, market-grade conformance, governance, and legal packaging.

### 🔜 Adoption Pack 1 — “30-second understanding” + first hello session (docs-first, high ROI)
**Goal:** A developer does NOT ask 10 clarifying questions before trying. Two audiences reach a first “hello session” in 10–20 minutes.

- 🔜 AP1.1 Standard Overview (what it is / isn’t)
  - A single short “standard overview” entry that explains:
    - AICP = content-layer agent-to-agent protocol
    - roles: Mediator/Host and Enforcer
    - profiles as product feature (what you can claim/require)
    - what AICP does NOT replace (transport, tool protocols like MCP, domain ontologies, IAM systems)
  - Linked from README + docs/index.

- 🔜 AP1.2 Implementer’s Guide — Platform Builders (Mediators/Enforcers)
  - How to build a gateway/enforcer: what to store, how to log, how to apply strikes/sanctions, how to gate side-effects.
  - How to compute compatibility claims and what “degraded mode” means.

- 🔜 AP1.3 Implementer’s Guide — Agent Developers
  - How to add support (SDK/drop-in), how to run quickstart, how conformance and profile badges work, what minimal session looks like.

- 🔜 AP1.4 Error & Recovery — deterministic operational playbook
  - One canonical doc that unifies:
    - alerts vs fatal
    - what to do on hash/signature/chain mismatch
    - resync/resume behavior
    - retry vs disconnect guidance

### ⏳ Adoption Pack 2 — Profiles as product (negotiation, downgrade protection, naming)
**Goal:** A platform can credibly say: “We support AICP-Profile-XYZ” and mean it.

- ⏳ AP2.1 Profile declaration & negotiation
  - Specify how profiles are declared and negotiated (via CAPNEG or equivalent),
  - and how a party can REQUIRE a profile.

- ⏳ AP2.2 Profile downgrade protection (profile-level)
  - Make downgrade attempts detectable/invalid when a profile is required (tie to CAPNEG checks).
  - Provide “required profile” invariants and example fixtures.

- ⏳ AP2.3 Profile capability taxonomy
  - Explicitly define what a profile constrains:
    - required extensions
    - required message types (where relevant)
    - crypto requirements (“crypto profile”)
    - required policy categories (shape-level, not policy engine semantics)

### ⏳ Adoption Pack 3 — Conformance as marketing contract + governance + legal packaging
**Goal:** Companies integrate without fear of unstable changes or legal surprises.

- ⏳ AP3.1 Compatibility scale and “AICP-compatible” story
  - Document a clear compatibility ladder:
    - Core-only
    - Core+Crypto (badge-eligible, non-degraded)
    - Mediated blocking (ENF + Alerts + Resume)
    - Ops hardening
  - Provide a GitHub Action or workflow snippet to publish conformance/profile badges.

- ⏳ AP3.2 Governance & change control
  - Versioning policy (SemVer-like)
  - Deprecation policy (support window)
  - Registry change-control RFC (who/how changes registries)
  - Extension acceptance workflow (RFC lifecycle)

- ⏳ AP3.3 Legal/standard packaging
  - Code license + spec license (explicit)
  - Trademark/name usage note for “AICP”
  - Security policy (already present) and disclosure workflow clarity

---

## Additional technical adoption enablers
These are strongly recommended for platform adoption but can be staged.

- ⏳ HTTP/Webhook transport binding (pragmatic platform binding)
  - A binding doc + minimal example of AICP envelope over HTTP requests/responses.
  - (Optional) WS/SSE binding later.

---

## Immediate next step
Start **Adoption Pack 1 (AP1.1–AP1.4)**.
