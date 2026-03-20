# AICP Interop Submission Playbook

## Purpose

This playbook helps external implementers prepare **truthful, reviewable interoperability submission packages** for the AICP public interop corpus.

It is an onboarding guide for packaging evidence that already exists. It is not a certification standard and it does not create any new protocol semantics.

## Scope

This playbook covers:
- who should submit,
- what a minimal real submission package contains,
- how to package single-implementation and pairwise claims,
- what disclosures to include,
- how the repo validators and matrix treat submission records and placeholder templates,
- how examples/templates differ from real external submissions.

## Explicit non-goals

This playbook is **not**:
- a certification regime,
- an endorsement program,
- a substitute for the AICP profile catalog or conformance suites,
- permission to publish vague “supports AICP” marketing claims,
- a place to invent external interoperability evidence that did not actually happen.

## Who should submit

Submit when you have a real implementation and want to publish **profile-scoped evidence** that another reviewer can inspect.

Typical submitters include:
- implementers of an AICP-capable agent, gateway, or platform component,
- teams that ran repo-backed conformance/profile tooling against their implementation,
- teams that completed a pairwise interop exercise with another named implementation and can package the resulting evidence truthfully.

If you only need an example of the package shape, use the shipped examples/templates instead of opening a real submission.

## Minimal real submission package

A minimal real submission package lives under:
- `interop/submissions/<submission-folder>/`

It should contain:
1. `submission.json` following `interop/submissions/submission.schema.json`.
2. Report/evidence files referenced by `report_refs`.
3. At least one disclosure explaining any limitations, assumptions, or scope boundaries.
4. Exact shipped `profile_ids` from `registry/aicp_profiles.json`.

## Claim / evidence status model

Use the small controlled vocabulary in `submission.json:evidence_status`.

- `example` — instructional artifact only; never market-facing evidence.
- `template` — starter package only; placeholders must be replaced before any real claim.
- `self_attested` — real submission published by one implementation with evidence scoped to the submitter's own package.
- `reproducible` — real submission where the package includes reproducible repo-style conformance/profile report evidence for the stated profile claim.
- `pairwise` — real submission about interoperability with a named peer implementation on a named profile; narrower than general compatibility.

This vocabulary is packaging-oriented. It does **not** imply maintainer endorsement.

## How to package a single-implementation claim

Use this path when you are making a claim such as:
- “implements AICP profile X”, or
- “compatible with AICP profile X”.

Recommended shape:
- `claim_type`: `implements_profile` or `compatible_with_profile`
- `claim_scope`: `self_attested`
- `evidence_status`: `self_attested` or `reproducible`
- no `peer_implementation_id`
- one or more report JSON files in `report_refs`

Prefer `reproducible` when the package includes actual conformance/profile report outputs generated from shipped repo tooling.

## How to package a pairwise claim

Use this only when the evidence is specifically about interoperability with a named peer implementation.

Required shape:
- `claim_type`: `pairwise_interop`
- `claim_scope`: `pairwise`
- `evidence_status`: `pairwise`
- `peer_implementation_id` present
- report/evidence references sufficient to inspect the pairwise claim

Do not translate a pairwise result into a broad ecosystem-wide compatibility statement.

## Required disclosures

Real submissions should include disclosures that help reviewers avoid over-reading the claim.

Common disclosures include:
- whether the submission is self-published by one side,
- whether the evidence package includes both sides' reports or only one side's package,
- whether any evidence files are summaries rather than raw runner output,
- whether the claim is limited to a single shipped profile/version.

## What evidence files are expected

Expected evidence files are usually JSON artifacts referenced by `report_refs`, for example:
- conformance report outputs,
- profile report outputs,
- pairwise summary/report JSON that explains how a joint exercise was packaged.

The validator expects referenced files to exist for real submissions and examples. Templates may intentionally keep placeholder `report_refs` until a real submitter replaces them; the matrix renders those as instructional warnings rather than as failed real-submission evidence.

## How to avoid overstating compatibility

Keep claims:
- profile-scoped,
- evidence-first,
- implementation/version-specific,
- explicit about whether the claim is self-attested, reproducible, or pairwise.

Do **not** publish:
- “supports AICP” without profile scope,
- pairwise claims that imply unnamed third-party compatibility,
- example/template artifacts as if they were real submissions,
- language that implies maintainer endorsement.

## Examples/templates vs real external submissions

The shipped examples and templates under `interop/submissions/examples/` and `interop/submissions/templates/` are instructional only.

They show:
- manifest shape,
- allowed controlled vocabularies,
- folder/reference conventions,
- validator expectations.

They do **not** prove real external interoperability. Real submissions must use non-placeholder package data and truthful disclosures.

## Build a package from existing evidence

Use `interop/tools/build_submission.py` when you already have report JSON files and want the repo to assemble a submission package layout for you.

### Single-implementation example

```bash
python interop/tools/build_submission.py \
  --out-root out/interop-submissions \
  --submission-id fictional-single-impl \
  --implementation-id fictional-impl-a \
  --implementation-version 1.2.3 \
  --profile-id AICP-BASE \
  --claim-type implements_profile \
  --claim-scope self_attested \
  --evidence-status reproducible \
  --report-path interop/submissions/examples/single_profile_claim/reports/report_profile_base.json \
  --report-path interop/submissions/examples/single_profile_claim/reports/report_core.json \
  --suite-ref PF_AICP_BASE_0.1 \
  --suite-ref CT_CORE_0.1 \
  --disclosure "Fictional example package only; not a market-facing claim." \
  --with-integrity \
  --validate
```

### Pairwise example

```bash
python interop/tools/build_submission.py \
  --out-root out/interop-submissions \
  --submission-id fictional-pairwise \
  --implementation-id fictional-impl-a \
  --peer-implementation-id fictional-impl-b \
  --implementation-version 2.0.0 \
  --profile-id AICP-MEDIATED-BLOCKING \
  --claim-type pairwise_interop \
  --claim-scope pairwise \
  --evidence-status pairwise \
  --report-path interop/submissions/examples/pairwise_profile_interop/reports/report_profile_mediated_blocking_a.json \
  --report-path interop/submissions/examples/pairwise_profile_interop/reports/report_profile_mediated_blocking_b.json \
  --suite-ref PF_AICP_MEDIATED_BLOCKING_0.1 \
  --suite-ref ENF_ENFORCEMENT_0.1 \
  --disclosure "Fictional pairwise example only; not a real interoperability claim." \
  --with-integrity \
  --validate
```

The builder copies the supplied report files into the package's `reports/` folder, writes predictable `report_refs`, and refuses incomplete pairwise inputs instead of guessing missing peer metadata.

After building a package, validate and inspect it with:

```bash
python scripts/validate_interop_submissions.py
make interop-matrix
```

## Optional bundle integrity manifest

When you are ready to package a submission for transport or review, prefer generating `bundle-integrity.json` alongside `submission.json`.

Use it to protect against:
- accidental file drift after packaging,
- mismatched copied reports,
- silent changes while moving a bundle between systems.

Do **not** treat it as:
- signer identity proof,
- an endorsement signal,
- a certification artifact,
- a replacement for the claim semantics already carried by `submission.json`.

The builder writes this file when you pass `--with-integrity`, and the validator verifies it when present.

## Validation and matrix entrypoints

Before opening a submission PR, run:

```bash
python scripts/validate_interop_submission_examples.py
python scripts/validate_interop_submissions.py
make interop-validate
make interop-matrix
```

Then run the broader repo verification commands required by the repo's one-command standard.
