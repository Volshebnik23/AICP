# AICP Public Interoperability Kit

AICP interoperability submissions let implementations package **profile-scoped, reviewable evidence** using a lightweight JSON manifest.

This directory now supports two shapes:
- the newer public interop corpus submission model based on `submission.json`, and
- the older implementation-manifest layout (`implementation.json` + `reports/`) for backward compatibility with early plugfest-style submissions.

## Start with the public corpus docs

- `docs/interop/AICP_Public_Interop_Corpus.md`
- `docs/interop/AICP_Compatibility_Claims_and_Evidence.md`
- `docs/interop/AICP_Interop_Submission_Playbook.md`

## Public submission package shape

A public interop submission package should live under `interop/submissions/<submission_folder>/` and include:
1. `submission.json`
2. referenced report/evidence files listed in `report_refs`
3. disclosures that keep the claim narrow and truthful

Examples and templates live under:
- `interop/submissions/examples/`
- `interop/submissions/templates/`

They are instructional artifacts only and must not be presented as external market evidence.

## Validate interop intake artifacts

Run:

```bash
python scripts/validate_interop_submission_examples.py
python scripts/validate_interop_submissions.py
make interop-validate
```

This intake path checks that:
- shipped examples/templates remain valid,
- real submission folders validate separately from instructional artifacts,
- shipped `profile_id` values and referenced files resolve correctly.

## Generate the interop matrix

Run:

```bash
make interop-matrix
```

This aggregates real submission folders under `interop/submissions/` into:
- `interop/interop_matrix.json`
- `interop/INTEROP_MATRIX.md`

Instructional example/template artifacts are rendered in a separate matrix section so they are not confused with real external submissions.
