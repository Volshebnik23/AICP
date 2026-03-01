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
- 🔜 M10 Snapshot discipline (optional, when needed):
  - feature freeze rules, registry snapshot, compatibility marks, packaging/checksums
- 🔜 M11 Multi-party sessions + tool/action gating (protocol foundations)
  - M11.0 Productize `ERROR` message type (payload schema + fixtures + conformance).
  - M11.1 EXT-PARTICIPANTS (membership + roles) with **two contract models**:
    - `shared_contract`: single contract governs the whole session; participant must be accepted against it.
    - `per_participant_acceptance`: each participant is accepted against a specific contract_ref/hash; messages must be compatible with sender acceptance.
  - M11.2 EXT-TOOL-GATING with **two enforcement modes**:
    - `blocking`: `TOOL_CALL_RESULT` requires a prior `ALLOW` verdict bound to the request hash.
    - `audit`: results must be post-attested/bound (no pre-blocking), per contract.
  - M11.3 Governance gate: registry ↔ schemas ↔ fixtures ↔ conformance anti-drift
    - Any `stable` message type (or any type required by a `shipped` profile) MUST have payload schema + at least one fixture + conformance coverage.
    - Experimental types may exist without full productization, but MUST NOT be required by shipped profiles.

- ⏳ M12 Enterprise chaining foundations (identity + delegation + workflow)
  - M12.1 Productize EXT-IDENTITY-LC (schemas + fixtures + conformance; verify signatures via announced/rotated keys at least session-local).
  - M12.2 Productize EXT-DELEGATION (grant/accept/revoke/result attest) with depth/expiry/scope-binding checks.
  - M12.3 Productize EXT-WORKFLOW-SYNC (declare/update/step attest) with step monotonicity + result-hash binding.
  - (Optional) EXT-SUBJECT-BINDING (acting-on-behalf-of): platform-controlled; if enabled by profile/contract, MUST be machine-checkable.

- ⏳ M13 Ops/security interop hygiene
  - M13.1 Productize EXT-DISPUTES and EXT-SECURITY-ALERTS (payload schemas + fixtures + conformance).
  - M13.2 CAPNEG hardening: registry `privacy_modes` + conformance that negotiation results are bound into contract/context when required by profile.
  - M13.3 Expand `policy_reason_codes` baseline + enforce namespacing rules (`vendor:*` / `org:*`) for non-baseline codes.

- ⏳ M14 Market-facing profile packaging
  - M14.1 `AICP-RECEPTION-CHAT` profile = MEDIATED-BLOCKING + ENFORCEMENT + POLICY_EVAL + PARTICIPANTS (with contract model selection).
  - M14.2 `AICP-ENTERPRISE-CHAINING` profile = IDENTITY-LC + DELEGATION + WORKFLOW-SYNC + TOOL-GATING + POLICY_EVAL (with tool mode selection).

- ⏳ HTTP/Webhook transport binding (pragmatic platform binding)
  - A binding doc + minimal example of AICP envelope over HTTP requests/responses.
  - (Optional) WS/SSE binding later.

---

## Immediate next steps
1) Finish **M8.6 Plugfest kit + interop report + errata workflow** (remaining in-progress items).
2) Execute **M10 Snapshot discipline** when a compatibility freeze/packaging moment is needed.
3) Start **M11 Multi-party sessions and tool/action gating** (P0 backlog below).

