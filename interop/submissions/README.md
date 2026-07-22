# Interop submissions folder contract

The public interop corpus uses a lightweight manifest model for real submissions:

- `interop/submissions/<submission-folder>/submission.json`
- additional evidence files referenced by `report_refs`

Instructional artifacts live in:
- `interop/submissions/examples/`
- `interop/submissions/templates/`

## Required fields

`submission.json` must follow `interop/submissions/submission.schema.json` and include at minimum:
- `submission_id`
- `implementation_id`
- `implementation_version`
- `profile_ids`
- `evidence_types`
- `evidence_status`
- `report_refs`
- `suite_refs`
- `claim_type`
- `claim_scope`
- `generated_at`

`peer_implementation_id` and `peer_implementation_version` are required for pairwise
interoperability claims.

Real public submissions must add `profile_refs` with exact `profile_id` and
`profile_version` values. Reproducible implementation/compatibility claims must include an
eligible, passed, non-degraded external-IUT report whose execution subject matches the
manifest. Pairwise claims require eligible subjects for both parties and an explicit shared
profile/participant summary. Legacy real packages receive migration errors; examples,
templates, and repo-owned dry runs remain instructional and cannot substantiate an external
claim.

## Evidence-status vocabulary

- `example`
- `template`
- `self_attested`
- `reproducible`
- `pairwise`

Use `example` and `template` only for the shipped instructional artifacts. Real submission folders should use `self_attested`, `reproducible`, or `pairwise`. Template placeholder `report_refs` are allowed for instructional starter packs, but real submissions and examples must resolve their referenced files.

## Validation entrypoints

Run:

```bash
python scripts/validate_interop_submission_examples.py
python scripts/validate_interop_submissions.py
make interop-validate
```

The matrix generator continues to understand the new `submission.json` format and keeps backward-compatible display support for legacy `implementation.json` folders.
