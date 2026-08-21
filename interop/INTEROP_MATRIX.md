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
- Only independently validated reproducible external full-profile IUT evidence produces computed marks.
- Capability marks are computed separately from product-profile marks and never prove a profile.
- Only independently validated full-capability report v2 evidence produces computed capability marks.
- Binding marks are computed separately from profile and capability marks and never prove either family.
- Only independently validated two-role full-binding live report v2.2 evidence produces computed binding marks.

## Real submissions

No real submission folders are currently present.

## Dry-run artifacts

| Folder | Implementation | Artifact kind | Peer | Evidence status | Claim type | Claim scope | Profiles | Capabilities | Bindings | Reported marks | Eligible profile marks | Eligible capability marks | Eligible binding marks | Eligible targets | Matrix status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| dryrun-reviewed-base | dryrun-impl-a | dry_run | — | reproducible | implements_profile | self_attested | AICP-BASE | — | — | AICP-Core-0.1, AICP-Profile-BASE-0.1 | — | — | — | — | REHEARSAL |

## Instructional artifacts

| Folder | Implementation | Artifact kind | Evidence status | Claim type | Claim scope | Profiles | Capabilities | Bindings | Reported marks | Eligible profile marks | Eligible capability marks | Eligible binding marks | Eligible targets | Matrix status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| capability_claim | example-projection-v1-implementation | example | example | implements_capability | self_attested | — | aicp.session_state_projection@v1 | — | AICP-Evidence-SESSION-STATE-PROJECTION-v1 | — | — | — | — | INSTRUCTIONAL |
| pairwise_profile_interop | example-impl-a | example | example | pairwise_interop | pairwise | AICP-MEDIATED-BLOCKING | — | — | AICP-EXT-ENFORCEMENT-0.1, AICP-Profile-MEDIATED-BLOCKING-0.1 | — | — | — | — | INSTRUCTIONAL |
| single_profile_claim | example-impl-a | example | example | implements_profile | self_attested | AICP-BASE | — | — | AICP-Core-0.1, AICP-Profile-BASE-0.1 | — | — | — | — | INSTRUCTIONAL |
| basic_submission | replace-with-implementation-id | template | template | compatible_with_profile | self_attested | AICP-BASE | — | — | — | — | — | — | — | INSTRUCTIONAL |
| binding_submission | replace-implementation-id | template | template | implements_binding | self_attested | — | — | BIND-HTTP@0.1 | — | — | — | — | — | INSTRUCTIONAL |
| capability_submission | replace-implementation-id | template | template | implements_capability | self_attested | — | aicp.session_state_projection@v1 | — | — | — | — | — | — | INSTRUCTIONAL |

## Parsing notes

- real submissions: no entries.
- `dryrun-reviewed-base`: NON_PUBLICATION_MARKS_NOT_PROMOTED: reported marks remain visible for audit but are not promoted outside a real eligible submission
- `example-capability-claim`: NON_PUBLICATION_MARKS_NOT_PROMOTED: reported marks remain visible for audit but are not promoted outside a real eligible submission
- `example-pairwise-profile-interop`: NON_PUBLICATION_MARKS_NOT_PROMOTED: reported marks remain visible for audit but are not promoted outside a real eligible submission
- `example-single-profile-claim`: NON_PUBLICATION_MARKS_NOT_PROMOTED: reported marks remain visible for audit but are not promoted outside a real eligible submission
- `replace-with-submission-id`: TEMPLATE_PLACEHOLDER_REF: template placeholder report_refs target not yet replaced: reports/replace-with-profile-report.json
- `replace-binding-submission-id`: TEMPLATE_PLACEHOLDER_REF: template placeholder report_refs target not yet replaced: reports/replace-with-full-binding-report-v2.2.json
- `replace-capability-submission-id`: TEMPLATE_PLACEHOLDER_REF: template placeholder report_refs target not yet replaced: reports/replace-with-full-capability-report.json
