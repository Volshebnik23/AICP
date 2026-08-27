# AICP Public Interoperability Kit

AICP interoperability submissions let implementations package **profile-scoped, reviewable evidence** using a lightweight JSON manifest.

Current generated status: zero real external submissions, one dry run, three instructional
artifacts, and no eligible external/pairwise mark. The canonical evidence summary is
`docs/process/AICP_Repo_Truth_Baseline.md`; `interop/interop_matrix.json` is the generated
corpus view.

This directory now supports two shapes:
- the newer public interop corpus submission model based on `submission.json`, and
- the older implementation-manifest layout (`implementation.json` + `reports/`) for backward compatibility with early plugfest-style submissions.

## Start with the public corpus docs

- `docs/interop/AICP_Public_Interop_Corpus.md`
- `docs/interop/AICP_Compatibility_Claims_and_Evidence.md`
- `docs/interop/AICP_Interop_Submission_Playbook.md`
- `docs/interop/AICP_Interop_Review_Workflow.md`
- `docs/interop/AICP_Interop_Dry_Run_Workflow.md`
- `docs/release/AICP_UAT_Release_Pack.md`
- `docs/release/AICP_UAT_Architecture_Freeze.md`
- `docs/release/AICP_UAT_Checklist.md`

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

The checked-in pairwise example below remains instructional and cannot pass the M66
publication path: it targets the wrong profile, has no exact build digests, no MCP side
reports, and no eligible joint report. Use the five-file pairwise template and
`interop/pairwise/README.md` for a real package:

```bash
python interop/tools/build_submission.py \
  --out-root out/interop-submissions \
  --submission-id fictional-pairwise \
  --implementation-id fictional-impl-a \
  --peer-implementation-id fictional-impl-b \
  --peer-implementation-version 2.0.0 \
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

For single-implementation claims, the builder copies supplied reports into
`<out-root>/<submission-id>/reports/`, writes `submission.json`, and can produce
`bundle-integrity.json`. For the old pairwise example, deterministic validation failure is
intentional: two independent reports do not establish a shared bidirectional run. A real
M66 package requires four eligible side reports plus one `AICP-PAIRWISE-TCK-1.2.0` joint
report and never receives a pairwise compatibility mark.

The command above demonstrates package assembly with fictional instructional reports; it
does not create publication-eligible profile evidence. A real `implements_profile` or
`compatible_with_profile` package must use `evidence_status=reproducible` and include an
eligible full-profile external-IUT v1 report. `self_attested`, legacy, instructional, or
hand-shaped raw marks are never promoted into matrix `computed_marks`.

`bundle-integrity.json` helps reviewers detect accidental drift or tampering after packaging. It does **not** prove signer identity, endorsement, or certification, and validators treat it as optional-but-strict: missing is allowed, present-and-invalid fails.

## Validate and review interop intake artifacts

Real external submissions should normally arrive as a PR that adds or updates `interop/submissions/<submission_id>/`. If a submitter needs preflight help before the PR, they can open the dedicated interop submission issue template first. Pilot adopters using the repo-backed UAT path should start with `docs/release/AICP_UAT_Release_Pack.md` and `docs/release/AICP_UAT_Architecture_Freeze.md` so the interop workflow stays grounded in the conservative pilot baseline and its frozen support envelope instead of implying every optional surface is required.

Run:

```bash
python scripts/validate_interop_submission_examples.py
python scripts/validate_interop_submissions.py
python scripts/review_interop_submission.py interop/submissions/<submission_id>
make interop-validate
```

This intake path checks that:
- shipped examples/templates remain valid,
- real submission folders validate separately from instructional artifacts,
- shipped `profile_id` values and referenced files resolve correctly,
- optional integrity manifests are verified when present,
- reviewer summaries can call out whether a package is matrix-eligible,
- template placeholder references stay clearly instructional instead of being mistaken for failed real submissions.

Maintainer workflow details live in `docs/interop/AICP_Interop_Review_Workflow.md`.

For repo-owned rehearsal of the full path, use the dry-run package at `interop/submissions/dryrun-reviewed-base/` together with `make interop-dryrun`. That path is intentionally fictional and stays separate from both examples/templates and real external submissions.

## Generate the interop matrix

Run:

```bash
make interop-matrix
```

This aggregates real submission folders under `interop/submissions/` into:
- `interop/interop_matrix.json`
- `interop/INTEROP_MATRIX.md`

Instructional example/template artifacts are rendered in a separate matrix section so they are not confused with real external submissions. Template placeholder references appear as instructional warnings, while real missing evidence still renders as invalid.

Regenerate the matrix after a real submission is reviewable and acceptable for publication. Do not publish invalid real submissions in the matrix, and do not treat examples/templates as external interoperability rows.

Dry-run artifacts appear in a separate rehearsal section so maintainers can rehearse the flow without implying real external ecosystem proof.
