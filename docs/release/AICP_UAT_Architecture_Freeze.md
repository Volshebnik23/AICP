# AICP UAT Architecture and Support Freeze

> **Purpose:** define the explicit freeze/support envelope for the AICP pilot phase without expanding protocol surface.

## 1) What this document is for

This document explains what is **frozen for UAT** in the repository, what may still change during the pilot phase, and what must wait for explicit post-UAT review.

It exists so pilot adopters and maintainers have one shared answer to these questions:
- what baseline is stable enough to target during UAT,
- what counts as acceptable bugfix/errata scope,
- how pilot defects and interop findings should be recorded,
- what should **not** churn during the pilot phase.

In repo terms, this is a **support discipline / architecture freeze** document, not a new protocol artifact.

## 2) Explicit non-goals

This freeze policy is **not**:
- a new protocol specification,
- a certification or endorsement program,
- a promise that every optional shipped surface is equally mature for every deployment,
- permission to redefine baseline semantics casually during UAT,
- a replacement for the canonical Core/profile/interop docs.

The purpose is pilot stability and release discipline, not protocol expansion.

## 3) What “frozen for UAT” means in this repo

For this repository, **frozen for UAT** means:
- the pilot baseline is the already-shipped repo truth described in the UAT pack and Adoption Core docs,
- maintainers should prefer bugfix/errata/support-discipline updates over baseline churn,
- pilot findings are welcome, but they do not automatically justify changing the supported baseline mid-UAT,
- anything that would widen or redefine semantics should be recorded and reviewed explicitly after UAT instead of being silently folded into the pilot target.

This freeze is about the **support envelope** around shipped AICP artifacts, not about stopping all repository activity.

## 4) Frozen baseline for the UAT phase

The frozen UAT baseline includes the already-shipped adoption and interop packaging layer:

### 4.1 Adoption Core baseline

The pilot baseline continues to anchor on the shipped Adoption Core:
- Core transcript integrity baseline,
- conservative baseline profile center,
- static HTTP/WS/SSE binding-case floor,
- profile-scoped internal conformance and, where a full external-IUT target exists,
  externally eligible evidence.

This frozen support envelope does not claim live independent binding interoperability.

Canonical references:
- `docs/architecture/AICP_Adoption_Core_and_Tiers.md`
- `docs/core/AICP_Core_v0.1_Normative.md`
- `docs/profiles/AICP_Profiles.md`
- `docs/profiles/Profile_Selection_Guide.md`

### 4.2 UAT release pack baseline

The current UAT release pack remains the release-facing definition of:
- what is in scope for pilot adopters,
- what the conservative pilot baseline is,
- what overlays are optional,
- what remains external/adjacent.

Canonical references:
- `docs/release/AICP_UAT_Release_Pack.md`
- `docs/release/AICP_UAT_Checklist.md`

### 4.3 Interop/review workflow baseline

The current interop evidence path is also part of the frozen UAT support envelope:
- public interop corpus guidance,
- claim-language limits,
- submission playbook,
- maintainer review workflow,
- repo-owned dry-run rehearsal path.

Canonical references:
- `docs/interop/AICP_Public_Interop_Corpus.md`
- `docs/interop/AICP_Compatibility_Claims_and_Evidence.md`
- `docs/interop/AICP_Interop_Submission_Playbook.md`
- `docs/interop/AICP_Interop_Review_Workflow.md`
- `docs/interop/AICP_Interop_Dry_Run_Workflow.md`
- `interop/README.md`

## 5) What remains external / out of scope

The freeze does **not** change AICP’s existing architecture boundaries.

The following remain external or adjacent during UAT:
- discovery/directory systems,
- calling/connectivity/session-establishment protocols,
- tool runtime execution protocols and tool catalogs,
- IAM provider internals,
- payment/checkout rails,
- universal trust services or trust fabric.

This freeze also does not turn optional shipped overlays into mandatory UAT prerequisites.

## 6) What is allowed during UAT

The following changes are allowed during UAT when they are genuinely bugfix/errata-grade:
- **bugfixes** that correct broken behavior in already-shipped tooling or docs,
- **errata** that clarify or fix incorrect statements without changing intended semantics,
- **docs clarification** that improves pilot usability without widening scope,
- **non-semantic validator/test fixes** when they correct an implementation bug, false failure, false success, or obvious repo-truth mismatch.

Allowed changes should preserve the same intended baseline and claim boundaries.

## 7) What counts as bugfix/errata-only change

A change fits the UAT freeze envelope when it does one or more of the following without redefining the target baseline:
- fixes an incorrect cross-reference,
- clarifies wording that was misleading or ambiguous relative to already-shipped repo truth,
- fixes validator/test behavior that was incorrectly rejecting valid artifacts or accepting invalid ones,
- corrects packaging/support guidance so it matches the already-shipped Core/profile/interop truth,
- repairs implementation-facing docs for existing shipped commands and workflows.

If the practical effect is “the repo now means something broader or different than before,” it is **not** bugfix/errata-only.

## 8) What is not allowed during UAT without explicit post-UAT review

The following are outside the freeze envelope unless maintainers intentionally decide to reopen them after UAT:
- new capability families,
- new protocol semantics,
- widening the pilot baseline,
- silently changing which profiles/bindings count as the UAT center,
- moving goalposts for compatibility claims or interop evidence expectations,
- turning optional overlays into implied pilot prerequisites,
- using pilot churn as a reason to reopen shipped milestones casually.

Those items should be recorded, not smuggled into the UAT baseline.

## 9) How pilot findings should be recorded

Pilot findings are welcome during UAT. The freeze policy changes **how they are handled**, not whether they are accepted.

Recommended recording path:
- open a GitHub issue for a defect, ambiguity, or support gap,
- open a PR for a concrete bugfix/errata/docs correction,
- use the interop submission/review path when the finding is evidence-backed compatibility or packaging-related.

A useful pilot finding should include:
- the targeted profile/binding/suite,
- exact commands and outputs,
- whether the problem is docs, validation, conformance, interop packaging, or support guidance,
- reproduction notes and attached evidence where possible.

### 9.1 Immediate UAT bugfix vs deferred post-UAT review

Treat a finding as an **immediate UAT bugfix/errata candidate** when:
- it corrects broken repo behavior,
- it fixes a false/misleading statement,
- it does not widen or redefine the pilot baseline.

Treat a finding as **deferred for post-UAT review** when:
- fixing it would add or widen semantics,
- it would materially change the compatibility/support target,
- it would shift what pilot adopters are expected to implement,
- it implies a new milestone rather than an erratum.

## 10) Relationship to the UAT pack and checklist

The UAT release pack tells adopters **what to target**.

This freeze document tells adopters and maintainers **how stable that target is during UAT**.

Read together:
- `docs/release/AICP_UAT_Release_Pack.md` defines the conservative pilot baseline,
- `docs/release/AICP_UAT_Checklist.md` defines the practical operator steps,
- this document defines the support/freeze discipline that prevents casual mid-UAT goalpost movement.

## 11) Bottom line

During UAT, AICP is in a **bugfix/errata/support-discipline** mode for the shipped pilot baseline.

That means:
- pilot adopters should target the already-documented baseline,
- maintainers should fix bugs and clarify truth,
- findings that would expand or redefine the baseline should be recorded for explicit post-UAT review instead of being folded into UAT by default.

### Post-UAT experimental additions

`AICP-AUTHENTICATED-BASE@0.1` and strict
`aicp.session_state_projection.v1` support are experimental post-UAT additions.
`AICP-BASE@0.2` is also a separately versioned post-UAT experiment for exact contract
artifact/head agreement. These surfaces are
version-selected, separately tested surfaces and are explicitly excluded from this frozen
pilot center. Their presence does not alter the meaning of `AICP-BASE@0.1`,
`AICP-RESUMABLE-SESSIONS@0.1`, or any other existing `@0.1` profile. A later pilot may
adopt them only through an explicit maintainer decision and versioned baseline update.

Core v0.2 does not alter any frozen Core v0.1 schema, golden fixture, suite, report shape,
or UAT mark. A Base 0.1 report cannot substantiate Base 0.2.

The evidence/report migration follows the same rule. Existing conformance commands retain
their legacy report shape by default, including the frozen
`conformance/conformance_report_schema.json` contract. Provenance-rich conformance/profile
v1 reports are opt-in through `--report-format v1`, while IUT evidence uses the separate
`conformance/iut/iut_report_v1.schema.json` contract. These additive artifacts do not alter
the frozen UAT protocol or profile semantics. Changing the default report format or making
the new experimental profile part of a pilot requires an explicit, versioned maintainer
decision after UAT.

Post-UAT IUT product-profile reports cover one exact profile target. They cannot currently
compose `aicp.session_state_projection.v1` as a full-profile overlay; strict projection
evidence is emitted separately until a versioned overlay-provenance model exists.
