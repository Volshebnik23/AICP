# AICP Interop Submission Playbook

## Purpose

This playbook helps external implementers prepare **truthful, reviewable interoperability submission packages** for the AICP public interop corpus.

It is an onboarding guide for packaging evidence that already exists. It is not a certification standard and it does not create any new protocol semantics.

## Scope

This playbook covers:
- who should submit,
- what a minimal real submission package contains,
- how to package single-implementation claims and interpret the reserved pairwise vocabulary,
- what disclosures to include,
- how the repo validators and matrix treat submission records and placeholder templates,
- how examples/templates differ from real external submissions.

## Explicit non-goals

This playbook is **not**:
- a certification regime,
- an endorsement program,
- a substitute for the AICP profile catalog or conformance suites,
- permission to publish vague “supports AICP” marketing claims,
- a place to invent external interoperability evidence that did not actually happen.

## Who should submit

Submit when you have a real implementation and want to publish exact profile- or
capability-scoped evidence that another reviewer can inspect.

Typical submitters include:
- implementers of an AICP-capable agent, gateway, or platform component,
- teams that ran repo-backed conformance/profile tooling against their implementation,
- teams that completed repo-backed full-profile IUT evaluation for their own implementation.

If you only need an example of the package shape, use the shipped examples/templates instead of opening a real submission.

## Minimal real submission package

A minimal real submission package lives under:
- `interop/submissions/<submission-folder>/`

It should contain:
1. `submission.json` following `interop/submissions/submission.schema.json`.
2. Report/evidence files referenced by `report_refs`.
3. At least one disclosure explaining any limitations, assumptions, or scope boundaries.
4. Exact shipped `profile_ids` from `registry/aicp_profiles.json`.
5. Exact `profile_refs` containing each claimed `profile_id` and `profile_version`.

For a capability claim, replace items 4 and 5 with exact `capability_refs`. M62 supports
only `aicp.session_state_projection@v1`, and one manifest must use only one claim family.

## Claim / evidence status model

Use the small controlled vocabulary in `submission.json:evidence_status`.

- `example` — instructional artifact only; never market-facing evidence.
- `template` — starter package only; placeholders must be replaced before any real claim.
- `self_attested` — migration/informational packaging status for submitter-published
  material; it cannot support an ordinary profile mark or a strong profile claim.
- `reproducible` — real submission where the package includes reproducible repo-style conformance/profile report evidence for the stated profile claim.
- `pairwise` — reserved vocabulary for a future joint-execution evidence format. Real
  submissions using it currently fail closed with `PAIRWISE_JOINT_EVIDENCE_REQUIRED`.

This vocabulary is packaging-oriented. It does **not** imply maintainer endorsement.

## How to package a single-implementation claim

Use this path when you are making a claim such as:
- “implements AICP profile X”, or
- “compatible with AICP profile X”.

Recommended shape:
- `claim_type`: `implements_profile` or `compatible_with_profile`
- `claim_scope`: `self_attested`
- `evidence_status`: exactly `reproducible`
- no `peer_implementation_id`
- one or more report JSON files in `report_refs`, including an eligible `full-profile`
  external-IUT v1 report for a real reproducible claim. Smoke and legacy reports are
  diagnostic/migration artifacts and are not eligible for this claim.

Prefer `reproducible` when the package includes actual conformance/profile report outputs generated from shipped repo tooling.

The validator rejects `implements_profile` or `compatible_with_profile` paired with
`self_attested` using `STRONG_PROFILE_CLAIM_REQUIRES_REPRODUCIBLE_IUT`. Retaining that enum
does not create a weaker certification tier.

### Capability claim

For strict session-state projection v1 use:

- `claim_type`: `implements_capability`
- `claim_scope`: `self_attested`
- `evidence_status`: exactly `reproducible`
- `capability_refs`: `[{"capability_id":"aicp.session_state_projection",
  "capability_version":"v1"}]`
- `evidence_types`: include `capability_report`
- `report_refs`: include an eligible target-oriented report v2 produced in
  `full-capability` mode

The validator independently evaluates the current target registry and
`AICP-EVIDENCE-TCK-1.1.0` bindings. It does not trust `passed` or
`compatibility_marks` alone. Smoke, `reference_corpus`, self-attested, degraded, skipped,
incomplete, wrong-version, or subject-mismatched reports cannot support the strong claim.
The capability mark does not prove any product profile or pairwise run. Projection v2
remains internal-only.

The 1.1.0 producer challenge contains raw scenario facts and a transcript prefix without a
completed projection response. The implementation must derive message hashes, evidence
references, canonical fields, and the projection hash. Evidence TCK 1.0.0 is historical,
superseded, and ineligible for a current reproducible claim.

## Pairwise vocabulary is currently instructional only

The manifest schema reserves `pairwise_interop`, `pairwise`, and peer identity fields so
examples and future migration work have a stable vocabulary. They are not currently a
publication path. The validator rejects every real pairwise submission with
`PAIRWISE_JOINT_EVIDENCE_REQUIRED`.

Two independent IUT reports, a co-conformance statement, or a human summary cannot prove
that one shared run named both exact builds and exercised artifacts consumed in every
required direction. A future pairwise format must bind those facts before maintainers can
enable real pairwise publication. The shipped pairwise package is therefore a shape example
only and must not be presented as interoperability evidence.

## Required disclosures

Real submissions should include disclosures that help reviewers avoid over-reading the claim.

Common disclosures include:
- whether the submission is self-published by one side,
- whether any peer-oriented material is an instructional example rather than publishable evidence,
- whether any evidence files are summaries rather than raw runner output,
- whether the claim is limited to a single shipped profile/version.

## What evidence files are expected

Expected evidence files are usually JSON artifacts referenced by `report_refs`, for example:
- conformance report outputs,
- profile report outputs,
- contextual summaries that are not treated as machine-verifiable compatibility evidence.

Repository self-test reports identify `execution_subject.kind=reference_corpus` and cannot
support a real external claim. Use `conformance/iut/aicp_iut_runner.py` against the external
adapter in `full-profile` mode so the v1 report binds implementation/build metadata, the
registered TCK release and runner digest, suite/profile digests, exact mandatory cases, and
input/generated artifact digests. Current consumer cases must also carry structured
execution observations that exactly match registered accounting expectations. Required
checks must pass without run-level degradation or skips.
Full-profile producer output is bound to the requested session, contract, participants,
exact profile, crypto mode, and deterministic seed. Capability overlays are not part of a
product-profile report: strict state-projection evidence must be emitted separately through
`conformance/evidence/aicp_external_evidence_runner.py`. Report v1 remains the profile
family; report v2 is target-oriented.

The validator expects referenced files to exist for real submissions and examples. Templates may intentionally keep placeholder `report_refs` until a real submitter replaces them; the matrix renders those as instructional warnings rather than as failed real-submission evidence.

## How to avoid overstating compatibility

Keep claims:
- profile-scoped,
- evidence-first,
- implementation/version-specific,
- explicit about whether the claim is self-attested or reproducible.

Do **not** publish:
- “supports AICP” without profile scope,
- pairwise claims that imply unnamed third-party compatibility,
- example/template artifacts as if they were real submissions,
- language that implies maintainer endorsement.

## Examples/templates vs real external submissions

The shipped examples and templates under `interop/submissions/examples/` and `interop/submissions/templates/` are instructional only.

They show:
- manifest shape,
- allowed controlled vocabularies,
- folder/reference conventions,
- validator expectations.

They do **not** prove real external interoperability. Real submissions must use non-placeholder package data and truthful disclosures.

## Build a package from existing evidence

Use `interop/tools/build_submission.py` when you already have report JSON files and want the repo to assemble a submission package layout for you.

### Single-implementation example

```bash
python interop/tools/build_submission.py \
  --out-root out/interop-submissions \
  --submission-id fictional-single-impl \
  --implementation-id fictional-impl-a \
  --implementation-version 1.2.3 \
  --profile-id AICP-BASE \
  --profile-ref AICP-BASE@0.1 \
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

### Capability example

```bash
python interop/tools/build_submission.py \
  --out-root out/interop-submissions \
  --submission-id projection-v1-claim \
  --implementation-id replace-implementation-id \
  --implementation-version replace-version \
  --capability-ref aicp.session_state_projection@v1 \
  --claim-type implements_capability \
  --claim-scope self_attested \
  --evidence-status reproducible \
  --report-path out/projection-v1-evidence.json \
  --suite-ref OR-SESSION-STATE-PROJECTION-V1 \
  --disclosure "Capability evidence does not imply product-profile conformance." \
  --with-integrity \
  --validate
```

No real capability submission is checked into this repository. The package under
`interop/submissions/examples/capability_claim/` is fictional and the package under
`interop/submissions/templates/capability_submission/` contains placeholders.

### Pairwise vocabulary example (expected to fail closed)

```bash
python interop/tools/build_submission.py \
  --out-root out/interop-submissions \
  --submission-id fictional-pairwise \
  --implementation-id fictional-impl-a \
  --peer-implementation-id fictional-impl-b \
  --peer-implementation-version 2.0.0 \
  --implementation-version 2.0.0 \
  --profile-id AICP-MEDIATED-BLOCKING \
  --profile-ref AICP-MEDIATED-BLOCKING@0.1 \
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

The pairwise command demonstrates the reserved manifest vocabulary. Its `--validate` step is
expected to fail with `PAIRWISE_JOINT_EVIDENCE_REQUIRED`; that failure is the current safety
contract, not a package-authoring error. The builder still refuses incomplete peer metadata
instead of guessing it.

## Optional bundle integrity manifest

When you are ready to transport or review a package, prefer `--with-integrity` so the builder also writes `bundle-integrity.json`.

Use that file to protect against:
- accidental file drift after packaging,
- mismatched copied reports inside the bundle,
- silent tampering between package creation and review.

Do **not** treat it as:
- signer identity proof,
- endorsement,
- certification, or
- a replacement for the claim semantics already expressed in `submission.json`.

The validators verify `bundle-integrity.json` when present. A package without it is still acceptable; a package with it must match the actual bundled files.

After building a package, validate and inspect it with:

```bash
python scripts/validate_interop_submissions.py
make interop-matrix
```

## Validation, PR path, and matrix entrypoints

Real external submissions should normally be opened as a PR that adds or updates `interop/submissions/<submission_id>/`. If you need maintainer guidance before that PR, open the interop submission intake issue template first.

Before opening a submission PR, run:

```bash
python scripts/validate_interop_submission_examples.py
python scripts/validate_interop_submissions.py
python scripts/review_interop_submission.py interop/submissions/<submission_id>
make interop-validate
```

Only expect public matrix publication after maintainer review confirms that the package is a real submission, the claim remains truthful, and the validators/reviewer summary show it as publication-ready. Examples/templates stay instructional and separate from public external rows.

If you want to rehearse the maintainer flow without creating fake external proof, use the repo-owned dry run documented in `docs/interop/AICP_Interop_Dry_Run_Workflow.md` and exercised by `make interop-dryrun`.

Then run the broader repo verification commands required by the repo's one-command standard.
