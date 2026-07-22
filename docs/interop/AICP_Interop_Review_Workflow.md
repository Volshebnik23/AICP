# AICP Interop Review Workflow

## Purpose

This document explains the **maintainer workflow for reviewing real external interoperability submissions** in the repository.

Its goal is operational clarity:
- how a real submission should arrive,
- what maintainers verify,
- when matrix publication happens,
- how instructional examples/templates stay separate from real external evidence.

## Scope

This workflow covers:
- real external submission packages under `interop/submissions/<submission_id>/`,
- maintainer review of `submission.json`, referenced evidence, disclosures, and optional `bundle-integrity.json`,
- required repo validation commands,
- when `interop/INTEROP_MATRIX.md` and `interop/interop_matrix.json` should be regenerated.

## Explicit non-goals

This workflow is **not**:
- a certification program,
- an endorsement process,
- a trust or approval authority,
- a replacement for shipped schema/validator checks,
- permission to overstate compatibility beyond the evidence actually provided.

A merged submission remains a repo-backed evidence package only. It does **not** imply sponsorship, certification, or automatic trust.

## How a real external submission should arrive

### Preferred path: pull request

A real external submission should normally arrive as a PR that adds or updates a single submission folder under:
- `interop/submissions/<submission_id>/`

The PR should include:
- the submission package files,
- truthful disclosures,
- the submitter's validation commands/results,
- whether optional `bundle-integrity.json` is present,
- whether the submitter expects matrix publication after review.

The repo PR template includes an interop submission section for this path.

### Optional preflight path: issue

If a submitter needs help before opening the PR, they may open the dedicated interop submission issue template first.

That issue is a preflight/intake aid only. It does **not** publish evidence and it does **not** place the submission into the matrix.

For a repo-owned rehearsal of this same lifecycle, see `docs/interop/AICP_Interop_Dry_Run_Workflow.md`. The dry-run path is for operational practice only, not external evidence publication.

## Maintainer review workflow

1. **Confirm this is a real submission path.**
   - Real submissions belong under `interop/submissions/<submission_id>/`.
   - Example/template artifacts remain under `interop/submissions/examples/` or `interop/submissions/templates/` and are not reviewed as external claims.

2. **Run the shipped intake validators.**
   - `python scripts/validate_interop_submissions.py`
   - `python scripts/review_interop_submission.py interop/submissions/<submission_id>`

3. **Verify claim truthfulness and scope.**
   - `profile_ids` are shipped profile IDs already in repo truth.
   - `claim_type`, `claim_scope`, and `evidence_status` match the package contents.
   - disclosures keep the claim narrow and do not imply endorsement or certification.
   - language stays aligned with `docs/interop/AICP_Compatibility_Claims_and_Evidence.md` and `TRADEMARKS.md`.

4. **Verify evidence packaging.**
   - referenced files actually exist inside the package,
   - exact `profile_refs` match the claim,
   - reports are schema-valid full-profile external-IUT v1 artifacts matching the manifest,
     registered TCK release, exact mandatory case set, and all required digests,
   - passed reports are non-degraded, have no mandatory skips, and carry exactly the
     independently recomputed mark list,
   - optional `bundle-integrity.json` validates when present.

5. **Decide matrix publication readiness.**
   - only valid real submissions are eligible,
   - examples/templates remain instructional and separate,
   - invalid or incomplete real submissions stay out of the public matrix until fixed.

## Review checks by evidence status

### `self_attested`

Maintainers should verify:
- the claim is clearly self-published,
- disclosures explain any evidence limitations,
- the package does not imply third-party confirmation.
- `claim_type` is not `implements_profile` or `compatible_with_profile`, and no ordinary
  profile mark is computed or published from the package.

### `reproducible`

Maintainers should verify:
- the package includes an eligible external-IUT report supporting the exact profile claim,
- the reports are present inside the bundle,
- optional integrity data, if present, matches the bundled files.

### `pairwise`

Real pairwise submissions are not publication-eligible in this release. The validator must
return `PAIRWISE_JOINT_EVIDENCE_REQUIRED`; maintainers must not waive this using two
single-IUT reports, co-conformance, or a summary. Examples/templates remain instructional.
A future review path requires a dedicated joint run binding both builds and exchanged
artifacts in every required direction.

## Required maintainer checklist

Before accepting a real external submission, maintainers should confirm all of the following:
- `submission.json` validates,
- required referenced evidence files exist,
- `profile_ids` are shipped repo profile IDs,
- disclosures are present and truthful,
- optional `bundle-integrity.json` is valid when present,
- the review-summary helper reports the package as a real submission and matrix-eligible,
- examples/templates are not being presented as external evidence.

## Reviewer-summary helper

Use:

```bash
python scripts/review_interop_submission.py interop/submissions/<submission_id>
```

The helper prints a concise summary including:
- submission ID,
- implementation ID,
- profile IDs,
- claim type/scope,
- evidence status,
- integrity present/valid/invalid,
- required reference-file presence,
- whether matrix publication is possible.

This helper is for reviewer clarity only. It does not create new semantics.

## Matrix publication / update guidance

Matrix publication should happen **after** the real submission is reviewable and valid.

### Regenerate the matrix when:
- a real submission is merged or materially updated,
- a previously invalid submission becomes valid,
- a maintainer intentionally wants the published matrix to reflect the current accepted real-submission set.

### Do not publish matrix rows when:
- the submission is still an example/template,
- required files or disclosures are missing,
- the optional integrity manifest is present but invalid,
- the claim wording still overstates what the evidence supports.

### Public matrix behavior
- real valid submissions can appear in the public matrix,
- examples/templates remain clearly instructional and separate from real external rows,
- `evidence_status` is shown as package-strength/scope metadata only and does not imply endorsement.
- computed marks come only from the shared full-profile eligibility validator; raw legacy,
  instructional, or hand-shaped report marks are never promoted.

## What does not happen during review

Maintainer review does **not**:
- certify a product,
- guarantee interoperability beyond the submitted evidence,
- grant trademark rights beyond project policy,
- convert a self-attested claim into independent endorsement,
- automatically trust a package because it carries `bundle-integrity.json`.
