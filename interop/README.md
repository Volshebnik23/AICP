# AICP Public Interoperability Kit

AICP interoperability submissions let implementations package **profile-scoped, reviewable evidence** using a lightweight JSON manifest.

This directory now supports two shapes:
- the newer public interop corpus submission model based on `submission.json`, and
- the older implementation-manifest layout (`implementation.json` + `reports/`) for backward compatibility with early plugfest-style submissions.

## Start with the public corpus docs

- `docs/interop/AICP_Public_Interop_Corpus.md`
- `docs/interop/AICP_Compatibility_Claims_and_Evidence.md`

## Public submission package shape

A public interop submission package should live under `interop/submissions/<submission_folder>/` and include:
1. `submission.json`
2. referenced report/evidence files listed in `report_refs`
3. disclosures that keep the claim narrow and truthful

Examples and templates live under:
- `interop/submissions/examples/`
- `interop/submissions/templates/`

They are instructional artifacts only and must not be presented as external market evidence.

## Validate shipped examples/templates

Run:

```bash
python scripts/validate_interop_submission_examples.py
```

This checks that shipped examples/templates:
- conform to `interop/submissions/submission.schema.json`,
- use shipped `profile_id` values from `registry/aicp_profiles.json`,
- reference files correctly for example packages.

## Generate the interop matrix

Run:

```bash
make interop-matrix
```

This aggregates real submission folders under `interop/submissions/` into:
- `interop/interop_matrix.json`
- `interop/INTEROP_MATRIX.md`

Reserved instructional directories such as `examples/` and `templates/` are ignored by the matrix generator.
