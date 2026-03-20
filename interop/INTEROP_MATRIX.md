# AICP Interop Matrix

Generated from `interop/submissions/` using `interop/tools/interop_matrix.py`.

> No real external submissions are currently present; only rehearsal/instructional artifacts were found.

| Implementation | Status | Evidence status | AICP-Profile-BASE-0.1 | AICP-Profile-MEDIATED-BLOCKING-0.1 | AICP-Core-0.1 | AICP-EXT-ENFORCEMENT-0.1 | AICP-EXT-ALERTS-0.1 | AICP-EXT-RESUME-0.1 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |

## Interpretation notes

- Dry-run artifacts are listed separately from real external submissions and from instructional examples/templates.
- Instructional artifacts are listed separately from real submissions.
- evidence_status describes package strength/scope and does not imply maintainer endorsement.
- Template placeholder refs are surfaced as instructional warnings, not as real-submission compatibility evidence.
- Legacy implementation.json folders are shown as self_attested by default for backward-compatible display only.

## Real submissions

No real submission folders are currently present.

## Dry-run artifacts

| Folder | Implementation | Artifact kind | Peer | Evidence status | Claim type | Claim scope | Profiles | Marks | Matrix status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dryrun-reviewed-base | dryrun-impl-a | dry_run | — | reproducible | implements_profile | self_attested | AICP-BASE | AICP-Core-0.1, AICP-Profile-BASE-0.1 | REHEARSAL |

## Instructional artifacts

| Folder | Implementation | Artifact kind | Evidence status | Claim type | Claim scope | Profiles | Marks | Matrix status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pairwise_profile_interop | example-impl-a | example | example | pairwise_interop | pairwise | AICP-MEDIATED-BLOCKING | AICP-EXT-ENFORCEMENT-0.1, AICP-Profile-MEDIATED-BLOCKING-0.1 | VALID |
| single_profile_claim | example-impl-a | example | example | implements_profile | self_attested | AICP-BASE | AICP-Core-0.1, AICP-Profile-BASE-0.1 | VALID |
| basic_submission | replace-with-implementation-id | template | template | compatible_with_profile | self_attested | AICP-BASE | — | INSTRUCTIONAL |

## Parsing notes

- real submissions: no entries.
- `dryrun-reviewed-base`: no parsing errors or instructional warnings
- `example-pairwise-profile-interop`: no parsing errors or instructional warnings
- `example-single-profile-claim`: no parsing errors or instructional warnings
- `replace-with-submission-id`: TEMPLATE_PLACEHOLDER_REF: template placeholder report_refs target not yet replaced: reports/replace-with-profile-report.json
