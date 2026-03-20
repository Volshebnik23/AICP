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

`peer_implementation_id` is required for pairwise interoperability claims.

## Evidence-status vocabulary

- `example`
- `template`
- `self_attested`
- `reproducible`
- `pairwise`

Use `example` and `template` only for the shipped instructional artifacts. Real submission folders should use `self_attested`, `reproducible`, or `pairwise`.

## Validation entrypoints

Run:

```bash
python scripts/validate_interop_submission_examples.py
python scripts/validate_interop_submissions.py
make interop-validate
```

The matrix generator continues to understand the new `submission.json` format and keeps backward-compatible display support for legacy `implementation.json` folders.
