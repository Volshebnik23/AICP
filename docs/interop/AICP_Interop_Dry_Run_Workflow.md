# AICP Interop Dry-Run Workflow

## Purpose

This document defines the **repo-owned rehearsal path** for the interop submission lifecycle.

It exists so maintainers can rehearse, end to end:
- package creation,
- submission validation,
- reviewer summary output,
- matrix regeneration,
without fabricating real external ecosystem proof.

## Scope

This dry-run workflow covers:
- the checked-in rehearsal package at `interop/submissions/dryrun-reviewed-base/`,
- the commands used to validate and review it,
- how matrix generation behaves for rehearsal artifacts,
- how the dry-run differs from examples/templates and from real external submissions.

## Explicit non-goals

This workflow is **not**:
- a certification program,
- a plugfest roster,
- a real external vendor claim,
- proof of ecosystem adoption,
- a new protocol surface.

## Dry-run package layout

The repo-owned rehearsal package lives at:
- `interop/submissions/dryrun-reviewed-base/`

It uses the normal public submission package shape:
- `submission.json`
- `reports/`
- `bundle-integrity.json`

The IDs and disclosures are explicitly fictional/rehearsal-only (`dryrun-*`).

## How the rehearsal package is created

The checked-in package was generated with the shipped submission builder using fictional IDs, copied example report artifacts, and `--with-integrity` so the rehearsal exercises the same packaging path that a future real submitter would use.

That means the dry-run proves the repo can rehearse package creation with the current builder and validation rules, without claiming any real external implementation result.

## End-to-end rehearsal path

Run:

```bash
make interop-dryrun
```

That convenience path rehearses the lifecycle by:
1. validating real-submission folders,
2. running the reviewer-summary helper on the dry-run package,
3. regenerating the interop matrix.

You can also rehearse the whole submissions tree with:

```bash
python scripts/review_interop_submission.py interop/submissions/
```

## How dry-run artifacts differ from other artifacts

### Versus examples/templates

- examples/templates are instructional artifacts under `interop/submissions/examples/` or `interop/submissions/templates/`,
- the dry-run package uses a real-submission folder shape under `interop/submissions/`,
- but it is still explicitly rehearsal-only and repo-owned.

### Versus real external submissions

- real external submissions are expected to come from outside implementers and can be matrix-eligible after review,
- the dry-run package is authored by the repo for rehearsal and stays separate from real external rows,
- dry-run matrix output is descriptive rehearsal evidence only, not external ecosystem proof.

## Matrix behavior in rehearsal mode

The matrix keeps dry-run artifacts in their own bucket with a descriptive rehearsal status so they are not confused with:
- real external submissions, or
- instructional examples/templates.

A successful matrix update in rehearsal mode proves the tooling can classify and render the repo-owned dry-run package separately.

## What a successful rehearsal proves

A successful dry run proves that the repo can exercise the current workflow end to end using fictional artifacts:
- package shape is valid,
- validators pass,
- reviewer summaries are readable,
- matrix generation can classify rehearsal artifacts correctly.

## What it does NOT prove

A successful dry run does **not** prove:
- any real external interoperability claim,
- maintainer endorsement of an external implementation,
- certification,
- ecosystem maturity beyond repo-owned rehearsal readiness.
