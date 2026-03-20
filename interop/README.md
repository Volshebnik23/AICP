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

## Build a submission package from existing evidence

Use the builder to create a real-submission package skeleton from explicit metadata plus existing report JSON files:

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

For a pairwise package, supply two or more `--report-path` values plus an explicit peer ID:

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

The builder copies the supplied reports into `<out-root>/<submission-id>/reports/`, writes `submission.json`, and fails clearly instead of inventing missing pairwise metadata. Pass `--with-integrity` to also write `bundle-integrity.json` for the packaged files the builder actually emitted.

`bundle-integrity.json` helps reviewers detect accidental drift or tampering after packaging. It does **not** prove signer identity, endorsement, or certification, and validators treat it as optional-but-strict: missing is allowed, present-and-invalid fails.

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
- shipped `profile_id` values and referenced files resolve correctly,
- template placeholder references stay clearly instructional instead of being mistaken for failed real submissions.

## Generate the interop matrix

Run:

```bash
make interop-matrix
```

This aggregates real submission folders under `interop/submissions/` into:
- `interop/interop_matrix.json`
- `interop/INTEROP_MATRIX.md`

Instructional example/template artifacts are rendered in a separate matrix section so they are not confused with real external submissions. Template placeholder references appear as instructional warnings, while real missing evidence still renders as invalid.
