# AICP Public Interop Corpus

> **Status:** public repo packaging guidance for interoperability submissions against already-shipped AICP profiles. This document does **not** define new protocol semantics, profile IDs, or a certification regime.

## 1) Purpose

The AICP repo already ships the executable ingredients needed for interoperability work:
- profile definitions,
- conformance suites,
- profile runners and reports,
- compatibility/badge rules,
- adoption-core/tier framing.

This document defines the **public interoperability corpus** for external submission packages so independent implementations can submit reproducible evidence against those already-shipped artifacts.

The goal is practical preparation for interoperability work, not to claim that interoperability has already been proven across the ecosystem.

## 2) Scope

In scope:
- a repo-backed submission layout,
- the minimum machine-readable manifest for an interop submission,
- how profile IDs and report artifacts anchor the submission,
- how single-implementation and pairwise evidence packages should be organized,
- example submissions that demonstrate package shape only.

Out of scope:
- new protocol features,
- new profile IDs,
- vendor certification,
- endorsement or trust delegation,
- automatic acceptance of self-attested marketing claims,
- inventing fake third-party interoperability results.

## 3) Explicit non-goals

This corpus is **not**:
- a certification authority,
- a standards-body seal,
- a replacement for shipped conformance/profile artifacts,
- a substitute for legal/trademark policy,
- proof that an implementation is trustworthy or production-ready merely because it submitted files.

A submission is evidence packaging, not automatic approval.

## 4) What counts as an interoperability submission

An interoperability submission is a repo-packaged claim package that ties:
- one or more **shipped AICP profile IDs**,
- one or more **shipped suite/profile artifacts**,
- one or more **machine-readable report files**,
- implementation disclosures,
- and, when relevant, a peer implementation identifier,

into a single machine-readable manifest.

The submission format in this sprint is intentionally conservative: it is for profile-based compatibility evidence only.

## 5) Interop corpus layout

The public corpus layout is:

```text
interop/
  submissions/
    submission.schema.json
    README.md
    examples/
      single_profile_claim/
        README.md
        submission.json
      pairwise_profile_interop/
        README.md
        submission.json
    templates/
      submission.json
```

Rules:
- `examples/` contains **example-only** packages and MUST NOT be treated as real ecosystem submissions.
- `templates/` contains copy-starting points for future submitters.
- Real future submissions should live under `interop/submissions/<submission_id-or-implementation_id>/` using the same manifest shape.
- Report references in a manifest MUST point to concrete repo-relative artifacts.

## 6) Required evidence for a profile-based submission

A truthful profile-based submission package should include, at minimum:
1. a machine-readable `submission.json` manifest,
2. one or more shipped `profile_ids` using registry-backed profile identifiers such as `AICP-BASE@0.1`,
3. `suite_refs` pointing to the shipped conformance profile catalog and/or required suite artifacts,
4. `report_refs` pointing to concrete machine-readable reports,
5. implementation version/disclosure metadata,
6. a disclosure note explaining whether the package is example-only, self-run evidence, or pairwise evidence.

The profile ID anchors **what is being claimed**. The report and suite references anchor **how the claim was evidenced**.

## 7) Submission manifest model

The submission manifest is defined by:
- `interop/submissions/submission.schema.json`

The manifest includes:
- `submission_id`
- `implementation_id`
- `implementation_version`
- `profile_ids`
- `claim_type`
- `claim_scope`
- `evidence_types`
- `suite_refs`
- `report_refs`
- optional `peer_implementation_id`
- `generated_at`
- `notes`
- `disclosures`

This is deliberately lightweight. It is meant to make evidence packages easy to validate and compare, not to model every possible interoperability workflow.

## 8) Single-implementation vs pairwise packaging

### Single-implementation evidence package
Use this when the claim is:
- “implements AICP profile X”, or
- “compatible with AICP profile X”

The package should include:
- one implementation identifier,
- one or more shipped profile IDs,
- shipped suite/profile refs,
- report refs produced by the existing repo tooling,
- disclosures about the evidence source.

### Pairwise interoperability package
Use this when the claim is:
- “implementation A and implementation B were pairwise interoperable on profile X”

The package should include:
- an `implementation_id`,
- a `peer_implementation_id`,
- the shared shipped profile ID(s),
- concrete report refs used as evidence,
- explicit disclosures that explain the scope and limits of the pairwise claim.

A pairwise submission does **not** imply broader ecosystem compatibility by itself.

## 9) What remains outside scope

Outside the corpus format:
- vendor endorsement,
- ecosystem-wide compatibility guarantees from a single submission,
- certification marks,
- “trusted implementation” status,
- claims that are not backed by concrete shipped profile IDs and report evidence.

## 10) Example packages in this repo

This sprint ships two example packages:
- `interop/submissions/examples/single_profile_claim/`
- `interop/submissions/examples/pairwise_profile_interop/`

These are examples/templates only:
- they use clearly fictional identifiers such as `example-impl-a` and `example-impl-b`,
- they point at local repo artifacts for shape illustration,
- they MUST NOT be read as market-facing third-party claims.

## 11) Relationship to compatibility claim language

This corpus doc defines **how evidence is packaged**.

For the claim-language model itself, see:
- `docs/interop/AICP_Compatibility_Claims_and_Evidence.md`
- `docs/adoption/COMPATIBILITY_AND_BADGES.md`
- `docs/ops/COMPATIBILITY_POLICY.md`
- `docs/profiles/AICP_Profiles.md`

## 12) Minimal submitter workflow

1. Pick the exact shipped profile ID(s) being claimed.
2. Run the required repo conformance/profile commands.
3. Collect the resulting report artifacts.
4. Fill in `submission.json` using the submission schema.
5. Validate the package locally.
6. Submit the package as repo evidence.

That is the whole point of the public corpus: small, reproducible, profile-anchored interoperability evidence.
