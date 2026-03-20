# AICP Public Interop Corpus

## Purpose

The AICP public interop corpus is the repo-backed place for packaging **checkable interoperability evidence**.

Its purpose is to let implementers publish narrowly-scoped, machine-readable claims such as:
- an implementation **implements** a shipped AICP profile,
- an implementation is **compatible with** a shipped AICP profile based on conformance evidence,
- two implementations were **pairwise interoperable** for a specific shipped profile and evidence set.

The corpus is intentionally conservative. It is for evidence packaging and transparent review, not for marketing shorthand or protocol expansion.

## Scope

The public interop corpus covers:
- submission manifests under `interop/submissions/`,
- example and template packages that show valid submission structure,
- report references and related evidence files carried with a submission package,
- aggregation tooling such as `interop/tools/interop_matrix.py`,
- validation tooling that checks submission shape against repo truth.

The corpus is grounded in already-shipped repo artifacts such as:
- `registry/aicp_profiles.json`,
- conformance/profile report JSON emitted by repo runners,
- repo documentation for compatibility claims and trademark boundaries.

## Explicit non-goals

This corpus is **not**:
- a new certification program,
- a new profile or protocol feature surface,
- a place to publish unverifiable vendor marketing claims,
- a replacement for schemas, registries, conformance suites, or profile definitions,
- a guarantee that every submitted claim has been independently reproduced by AICP maintainers.

## What counts as an interoperability submission

An interoperability submission is a directory-scoped package whose primary manifest is `submission.json` and that includes enough evidence for a third party to inspect the claim.

At minimum, a submission should identify:
- the submitting implementation,
- the implementation version,
- the shipped `profile_id` values the claim is about,
- the type of claim being made,
- the evidence types included,
- the report references and suite references that support the claim,
- the generation timestamp,
- any notes or disclosures needed to keep the claim truthful.

## Required evidence shape

The public submission manifest schema is `interop/submissions/submission.schema.json`.

A valid submission package should include:
1. `submission.json` manifest.
2. Referenced report files under paths listed in `report_refs` when the package is an example or a real submission.
3. `suite_refs` that identify the suite/profile evidence set the claim depends on.
4. `profile_ids` that match profile identifiers already shipped in `registry/aicp_profiles.json`.
5. Notes/disclosures when the evidence is limited, synthetic, or example-only.

The evidence model is intentionally JSON-based and lightweight. The package should point to concrete repo-backed evidence rather than relying on prose-only claims.

## Example/template artifacts vs real external submissions

The repository ships **examples** and **templates** to show packaging shape.

- **Examples** are synthetic, fictional, and non-market-facing. They demonstrate what a valid package looks like and include local example evidence files.
- **Templates** are starter artifacts for future submitters. They may contain placeholder references and disclosure text that must be replaced before any real claim is made.
- **Real external submissions** are expected to replace placeholders with actual report outputs and truthful disclosures grounded in the submitter's implementation and test run.

Example and template artifacts must never be presented as proof of external vendor compatibility.

## Pairwise vs self-attested evidence packaging

The corpus supports two common packaging shapes.

### Self-attested / single-implementation claim package

Use this when one implementation is claiming profile implementation or compatibility based on its own reproducible conformance/profile evidence.

Typical shape:
- one `implementation_id`,
- no `peer_implementation_id`,
- one or more profile/conformance reports in `report_refs`,
- `claim_scope` of `self_attested`.

### Pairwise interoperability claim package

Use this when the claim is specifically about two implementations interoperating for a named profile.

Typical shape:
- one submitting `implementation_id`,
- one `peer_implementation_id`,
- `claim_type` of `pairwise_interop`,
- `claim_scope` of `pairwise`,
- evidence package containing reports and/or transcript-linked artifacts that show the pairwise result,
- disclosures explaining whether the package contains both sides' evidence directly or references a shared joint report.

Pairwise claims should be narrower than generic product claims. They should identify the exact peer and profile instead of implying broad ecosystem endorsement.

## Truthfulness expectations

Submission packages should use the claim language defined in:
- `docs/interop/AICP_Compatibility_Claims_and_Evidence.md`, and
- `TRADEMARKS.md`.

Do not submit vague claims such as “supports AICP.” Instead, publish the smallest truthful statement the evidence can actually support.
