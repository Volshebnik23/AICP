# AICP UAT Release Pack

> **Purpose:** provide one concise, repo-backed package for pilot adopters evaluating the already-shipped AICP surface. The companion freeze/support policy for this pilot phase lives in `docs/release/AICP_UAT_Architecture_Freeze.md`.

## 1) What this pack is for

This release pack tells pilot adopters exactly:
- what AICP surface is in scope for **UAT** in this repository,
- what the recommended baseline is,
- which overlays are optional,
- which adjacent layers remain external,
- how to validate a pilot implementation,
- how to package evidence and report defects.

In this repo, **UAT** means:
- trialing already-shipped AICP artifacts in a real pilot or pre-production evaluation,
- validating claims against repo-backed schemas, conformance suites, profiles, and interop tooling,
- reporting practical gaps, docs friction, and interoperability defects back into the repository.

It does **not** mean that AICP is claiming universal production readiness for every deployment shape.

## 2) Explicit non-goals

This pack is **not**:
- a new protocol specification,
- a new profile catalog,
- a certification regime,
- a maintainer endorsement program,
- a claim that every shipped optional surface is required for pilot adoption,
- a replacement for the canonical profile/spec/conformance documents.

Use this pack as a release-facing entrypoint, not as a new source of protocol truth. During UAT, read it together with `docs/release/AICP_UAT_Architecture_Freeze.md` so the pilot baseline is understood as a frozen support envelope rather than a moving target.

## 3) UAT scope in this repository

The UAT scope is limited to **already-shipped repo truth**:
- Core transcript integrity requirements in `docs/core/AICP_Core_v0.1_Normative.md`, `schemas/core/`, and `conformance/core/`.
- Adoption framing in `docs/architecture/AICP_Adoption_Core_and_Tiers.md`.
- Shipped profile definitions in `docs/profiles/AICP_Profiles.md`.
- Shipped binding guidance and static binding-case conformance; live independent transport
  interoperability is not part of the current evidence.
- Public interop evidence packaging, review, and dry-run tooling under `docs/interop/` and `interop/`.
- Repo-backed validation, conformance, quickstart, template-smoke, and SDK checks in the Makefile/CI.

This pack does **not** expand protocol surface beyond those shipped artifacts.

## 4) Recommended pilot baseline

The conservative pilot baseline is intentionally small.

### 4.1 Core transcript integrity baseline

Every pilot should start by proving the Core baseline:
- schema-valid envelopes/payloads,
- deterministic hashing and transcript linkage,
- boundary validation,
- Core conformance.

Canonical baseline artifacts:
- narrative: `docs/core/AICP_Core_v0.1_Normative.md`
- schemas: `schemas/core/`
- core suite: `conformance/core/CT_CORE_0.1.json`

### 4.2 Baseline profile center

For pilot adoption, start with the smallest shipped profile that matches the deployment:
- **start here:** `AICP-BASE@0.1`
- **add when mediated governance is required:** `AICP-MEDIATED-BLOCKING@0.1`
- **add when continuity matters:** `AICP-RESUMABLE-SESSIONS@0.1`
- **add when acting-on-behalf-of identity binding matters:** `AICP-DELEGATED-IDENTITY@0.1`

This follows the existing Adoption Core / Tier 0–1 framing. It does **not** make every other shipped profile part of the default pilot baseline.

### 4.3 Static transport/binding case floor

AICP remains transport-independent. The current HTTP/WS/SSE binding surface is a static
case-validation floor for pilot implementation:
- binding guidance: `docs/bindings/RFC_BIND_HTTP_WS.md`
- binding suite: `conformance/bindings/TB_HTTP_WS_0.1.json`
- binding identifier: `BIND-HTTP-0.1`

Passing these fixtures does not prove that two independent live endpoints exchanged traffic.

### 4.4 Interop/review entrypoint

When a pilot is ready to package evidence, use the already-shipped interop path:
- public corpus guide: `docs/interop/AICP_Public_Interop_Corpus.md`
- claim language: `docs/interop/AICP_Compatibility_Claims_and_Evidence.md`
- submitter playbook: `docs/interop/AICP_Interop_Submission_Playbook.md`
- maintainer review workflow: `docs/interop/AICP_Interop_Review_Workflow.md`
- repo-owned rehearsal path: `docs/interop/AICP_Interop_Dry_Run_Workflow.md`

## 5) Optional overlays that are **not** required for a basic UAT

AICP ships more surface than a basic pilot needs. These remain optional unless the deployment requires them:
- policy semantic profiles,
- human approval,
- confidentiality / redaction / retention overlays,
- trust attestations / status / enterprise bindings / observability,
- execution interoperability,
- commerce-ready orchestration,
- bazaar, channel/media, and marketplace bundles,
- richer workflow orchestration bundles.

Use the existing tier model and profile-selection guide to add them only when needed:
- `docs/architecture/AICP_Adoption_Core_and_Tiers.md`
- `docs/profiles/Profile_Selection_Guide.md`

## 6) Adjacent layers that remain external

AICP is still the governed **content layer**, not the whole stack.

For UAT, the following remain external/adjacent unless your own product composes them separately:
- discovery/directory systems,
- calling/connectivity/session-establishment protocols,
- tool runtime execution protocols and tool catalogs,
- IAM provider internals,
- payment/checkout rails,
- universal trust fabric or hosted trust service.

See:
- `docs/architecture/AICP_in_the_Ecosystem.md`
- `docs/adjacent/A2A_Integration_Pattern.md`
- `TRADEMARKS.md`

## 7) Validation path for pilot adopters

A concise, truthful pilot validation path is:

1. Read the front-door docs:
   - `START_HERE_IMPLEMENTERS.md`
   - `docs/architecture/AICP_Adoption_Core_and_Tiers.md`
   - `docs/profiles/Profile_Selection_Guide.md`
2. Run the repo validation/conformance gates:
   - `make validate`
   - `make conformance`
   - `make conformance-ext`
   - `make conformance-bindings`
   - `make conformance-profiles`
   - `make test`
3. Run onboarding smoke checks as applicable:
   - `make quickstart-py`
   - `make quickstart-ts`
   - `make template-smoke`
4. Run the full shipped verification bundle before publishing claims:
   - `make prepr`
5. Treat pilot findings under the UAT freeze/support envelope:
   - `docs/release/AICP_UAT_Architecture_Freeze.md`

For interop evidence packaging/review:
- `python scripts/validate_interop_submission_examples.py`
- `python scripts/validate_interop_submissions.py`
- `python scripts/review_interop_submission.py interop/submissions/<submission_id>`
- `make interop-dryrun` for repo-owned rehearsal

Internal profile runs cover all 15 registered profiles. External product claims require an
eligible full-profile IUT target, which currently exists only for Base and experimental
Authenticated Base; only Base can currently reach an ordinary external mark.

## 8) Trial entrypoints for pilot adopters

Use one of these small truthful entrypoints:
- **Core-only pilot:** start with `AICP-BASE@0.1`, `make quickstart-py` or `make quickstart-ts`, then `make conformance`.
- **Governed hosted pilot:** add `AICP-MEDIATED-BLOCKING@0.1`, then run `make conformance-ext` and `make conformance-profiles`.
- **Continuity-sensitive pilot:** add `AICP-RESUMABLE-SESSIONS@0.1` when reconnect/resume/resync behavior matters.
- **Identity-sensitive pilot:** add `AICP-DELEGATED-IDENTITY@0.1` only when externally rooted delegated identity matters.

## 9) Reporting defects, friction, or evidence gaps

Pilot adopters should report findings back into the repository as repo-backed evidence, not prose-only claims.

Recommended paths:
- open a GitHub issue for defects, gaps, ambiguity, or onboarding friction,
- open a PR for doc clarifications or fixes,
- use the interop submission path when the finding is evidence-backed compatibility or interoperability packaging,
- include exact commands, outputs, profile IDs, and reproduction notes.

Good reports should say:
- which shipped profile/binding/suite was targeted,
- which command failed or produced confusing output,
- whether the issue is Core, profile, interop packaging, docs, or tooling,
- what evidence/transcript/report JSON is attached or reproducible.

If resolving the finding would widen the baseline or redefine semantics, record it for explicit post-UAT review instead of treating it as an automatic in-UAT scope change.

## 10) What UAT does **not** mean

AICP UAT in this repo does **not** mean:
- certification,
- maintainer endorsement,
- universal interoperability with unnamed third parties,
- approval to say “supports AICP” without profile scope,
- a guarantee that every optional overlay is mature for every use case,
- a promise that discovery, IAM internals, tool runtimes, or payment rails are standardized by AICP.

Keep public-facing language aligned with:
- `docs/interop/AICP_Compatibility_Claims_and_Evidence.md`
- `docs/interop/AICP_Public_Interop_Corpus.md`
- `TRADEMARKS.md`

## 11) Fast path summary

If you need a one-screen answer for a pilot:
- start with `AICP-BASE@0.1`,
- use the Core transcript integrity stack,
- use the static `BIND-HTTP-0.1` cases as the current binding-validation floor,
- add mediated blocking / resumable sessions / delegated identity only when needed,
- run the shipped validation + conformance + quickstart checks,
- package any compatibility claim through the shipped interop evidence path,
- do not describe static binding cases as live transport interoperability,
- do not over-claim UAT as certification or universal production readiness.

## 12) Companion checklist

Use `docs/release/AICP_UAT_Checklist.md` as the concise operator checklist that goes with this pack.

## 13) Post-UAT experiments excluded from this pack

The repository also contains experimental `AICP-AUTHENTICATED-BASE@0.1` and strict
`aicp.session_state_projection.v1` artifacts. They are post-UAT, opt-in targets with their
own conformance evidence. They are not additions to this pack's frozen baseline, and pilot
implementers are not required to implement them unless a future versioned pilot decision
explicitly says so.

The new provenance-rich report formats are additive as well. The UAT commands keep emitting
the legacy report shape by default. Maintainers and tool authors can explicitly request
conformance/profile v1 reports with `--report-format v1`; external-IUT evidence is governed
separately by `conformance/iut/iut_report_v1.schema.json`. Neither opt-in path changes the
frozen UAT baseline, and a future default-format migration requires an explicit maintainer
decision.

External full-profile IUT reports cover one exact product profile and cannot include the
strict state-projection capability overlay. Emit that capability evidence separately; this
restriction keeps post-UAT report provenance unambiguous without changing the frozen UAT
baseline.
