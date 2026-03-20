# Interop submissions folder contract

The public interop corpus uses a lightweight manifest model:

- `interop/submissions/<submission_folder>/submission.json`
- additional evidence files referenced by `report_refs`

Instructional artifacts live in:
- `interop/submissions/examples/`
- `interop/submissions/templates/`

## Submission manifest requirements

`submission.json` must follow:
- `interop/submissions/submission.schema.json`

At minimum it identifies:
- `submission_id`
- `implementation_id`
- `implementation_version`
- `profile_ids`
- `evidence_types`
- `report_refs`
- `suite_refs`
- `claim_type`
- `claim_scope`
- `generated_at`

`peer_implementation_id` is optional except for pairwise interoperability claims.

## Truthfulness rules

Use fictional IDs such as `example-impl-a` and `example-impl-b` only for examples/templates.

Real submissions should follow the claim-language and trademark boundaries in:
- `docs/interop/AICP_Public_Interop_Corpus.md`
- `docs/interop/AICP_Compatibility_Claims_and_Evidence.md`
- `TRADEMARKS.md`

## Local validation

Run:

```bash
python scripts/validate_interop_submission_examples.py
```

The interop matrix tool also understands the new `submission.json` format while continuing to tolerate the older `implementation.json` layout for backward compatibility.
