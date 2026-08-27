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
eligible, full-profile, passed, non-degraded external-IUT v1 report whose execution subject,
complete mandatory case set, and registered TCK digests match the manifest. Smoke and legacy
reports are migration errors for this strong claim. Real `pairwise_interop` publication
requires exact Base and MCP side reports for two distinct builds plus one eligible
`AICP-PAIRWISE-TCK-1.2.0` joint report; TCK 1.0 and 1.1 are historical/strong-ineligible, and two independent IUT reports or a summary are not
joint proof. Missing or invalid joint evidence returns
`PAIRWISE_JOINT_EVIDENCE_REQUIRED`. Examples,
templates, and repo-owned dry runs remain instructional and cannot substantiate an external
claim.

`implements_profile` and `compatible_with_profile` are strong claims: real packages using
either must set `evidence_status=reproducible`. `self_attested` remains in the schema for
migration/informational packaging but cannot receive an ordinary profile mark. The matrix
reuses this same independent eligibility check and does not promote raw report marks.

## Evidence-status vocabulary

- `example`
- `template`
- `self_attested`
- `reproducible`
- `pairwise`

Use `example` and `template` only for the shipped instructional artifacts. Real strong
profile claims must use `reproducible`; `self_attested` is retained only for migration or
informational packaging, and `pairwise` remains fail-closed. Template placeholder
`report_refs` are allowed for instructional starter packs, but real submissions and
examples must resolve their referenced files.

## Validation entrypoints

Run:

```bash
python scripts/validate_interop_submission_examples.py
python scripts/validate_interop_submissions.py
make interop-validate
```

The matrix generator continues to understand the new `submission.json` format and keeps backward-compatible display support for legacy `implementation.json` folders.
