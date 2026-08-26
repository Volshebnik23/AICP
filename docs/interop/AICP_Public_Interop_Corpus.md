# AICP Public Interop Corpus

## Purpose

The AICP public interop corpus is the repo-backed place for packaging **checkable interoperability evidence**.

Its purpose is to let implementers publish narrowly-scoped, machine-readable claims such as:
- an implementation **implements** a shipped AICP profile,
- an implementation is **compatible with** a shipped AICP profile based on conformance evidence,
- an implementation **implements** an exact registered external capability or binding target,
- reserved instructional packaging for a future claim that two implementations were
  **pairwise interoperable** for a specific profile and bound joint evidence set.

The corpus is intentionally conservative. It is for evidence packaging and transparent review, not for marketing shorthand or protocol expansion.

## Current corpus status

The generated matrix currently contains zero real external submissions and therefore zero
externally demonstrated profiles or capabilities. It contains one repo-owned dry run plus
examples/templates, all explicitly
non-promotable. The M66 pairwise publication mechanism is available, but no genuine external
pairwise relation has been submitted; demonstrated relations remain zero. See
`interop/interop_matrix.json` and `docs/process/AICP_Repo_Truth_Baseline.md`.

## Scope

The public interop corpus covers:
- submission manifests under `interop/submissions/`,
- example and template packages that show valid submission structure,
- report references and related evidence files carried with a submission package,
- aggregation tooling such as `interop/tools/interop_matrix.py`,
- validation tooling that checks submission shape against repo truth.

The corpus is grounded in already-shipped repo artifacts such as:
- `registry/aicp_profiles.json`,
- conformance/profile report JSON emitted by repo runners,
- repo documentation for compatibility claims and trademark boundaries,
- the submitter onboarding guidance in `docs/interop/AICP_Interop_Submission_Playbook.md`.

## Explicit non-goals

This corpus is **not**:
- a new certification program,
- a new profile or protocol feature surface,
- a place to publish unverifiable vendor marketing claims,
- a replacement for schemas, registries, conformance suites, or profile definitions,
- a guarantee that every submitted claim has been independently reproduced by AICP maintainers.

## What counts as an interoperability submission

An interoperability submission is a directory-scoped package whose primary manifest is `submission.json` and that includes enough evidence for a third party to inspect the claim.

At minimum, a submission should identify:
- the submitting implementation,
- the implementation version,
- the exact product-profile, capability, or binding references the claim is about,
- the type of claim being made,
- the evidence types included,
- the report references and suite references that support the claim,
- the generation timestamp,
- any notes or disclosures needed to keep the claim truthful.

## Required evidence shape

The public submission manifest schema is `interop/submissions/submission.schema.json`.

A valid submission package should include:
1. `submission.json` manifest.
2. Referenced report files under paths listed in `report_refs` when the package is an example or a real submission.
3. `suite_refs` that identify the suite/profile evidence set the claim depends on.
4. For a profile claim, `profile_ids` and exact `profile_refs` carrying both `profile_id`
   and `profile_version`.
5. For a capability claim, exact `capability_refs` carrying both `capability_id` and
   `capability_version`.
6. For a binding claim, exact `binding_refs` carrying both `binding_id` and
   `binding_version`, plus the binding's exact owning suite.
6. Notes/disclosures when the evidence is limited, synthetic, or example-only.

For real `reproducible` implementation/compatibility claims, at least one report must be a
schema-valid `full-profile` report from the claimed profile's registered mechanism. The
Base and Authenticated Base mechanisms remain external-IUT v1; the M63 Tier-1 mechanisms
use generalized report 2.1. The validator independently checks the
manifest subject, registered TCK release, complete mandatory case set, suite/profile and
every required fixture/vector digest, generated artifacts, non-degraded/no-skip state, and
the exact registered per-consumer execution observations and recomputed mark list. Smoke,
legacy, and `reference_corpus` reports are migration
errors for strong external evidence, not proof of an external product.
Strong `implements_profile` and `compatible_with_profile` claims also require
`evidence_status=reproducible`; `self_attested` cannot bypass this rule.

The frozen IUT runner targets `AICP-BASE@0.1` and experimental
`AICP-AUTHENTICATED-BASE@0.1`. Current Evidence TCK 1.4.0 separately targets exactly
`AICP-MEDIATED-BLOCKING@0.1`, `AICP-RESUMABLE-SESSIONS@0.1`, and
`AICP-DELEGATED-IDENTITY@0.1`. All five ordinary marks are reachable for complete eligible
external implementations. The authenticated unavailable-crypto probe remains mandatory,
but its exact simulated result is case-local; any actual degradation elsewhere suppresses
eligibility. No real eligible external submission is currently present.

Experimental `AICP-BASE@0.2` has internal Core/profile conformance only in M60. It is not a
third external-IUT target and cannot support strong external evidence until a later
versioned evidence/TCK milestone explicitly adds that path.

Experimental CAPNEG v0.2 composition reports are also internal-only in M61. The current
submission schema deliberately has no composition claim/evidence fields and rejects
unknown properties. Component profile claims continue to require their own eligible
external evidence for each component; M63 does not add external composition evidence.

M62 adds one separate target-oriented capability path:
`aicp.session_state_projection@v1`, report format `2.0`, `full-capability` execution, and
`AICP-EVIDENCE-TCK-1.1.0`. A strong `implements_capability` package requires exact
`capability_refs`, `evidence_status=reproducible`, `capability_report`, and an independently
eligible external-implementation report whose computed mark is
`AICP-Evidence-SESSION-STATE-PROJECTION-v1`. Capability and profile fields cannot be mixed
in one M62 manifest. Capability evidence cannot prove a product profile. Smoke, reference,
internal, self-attested, incomplete, degraded, skipped, and raw-mark-only evidence is
ineligible. Projection v2 is not registered as an external target.

M63 profile reports contain one exact `product_profile` target and discriminated transcript
artifacts. Their neutral producer requests disclose no case IDs, fixture paths, golden
messages/hashes, or marks. Strong profile manifests must list the exact union of required
suite IDs or paths in `suite_refs`; missing, unrelated, and duplicate suites fail closed.
Reference, smoke, example, and test-only adapter reports do not count as real external
evidence. No real eligible Tier-1 submission is currently present.

Current release 1.4.0 uses answer-isolated raw producer facts, a release-specific registry
snapshot, exact message-owner payload closure, ordinary-conformance semantic parity,
complete required-suite semantics, exact artifact multiplicity, and a self-checked
runner import closure. Exact 1.1.0 projection reports remain strong-eligible; historical
1.0.0, 1.2.0, and 1.3.0 cannot support strong eligibility. The checked-in fictional example uses
1.1.0 and is not counted as independent evidence.

The evidence model is intentionally JSON-based and lightweight. The package should point to concrete repo-backed evidence rather than relying on prose-only claims.

## Optional bundle integrity manifest

Submission bundles may also carry `bundle-integrity.json`, validated against `interop/submissions/integrity.schema.json`.

The integrity manifest is intentionally lightweight. It records:
- `submission_id`,
- a manifest version marker,
- `generated_at`,
- `digest_alg` (currently `sha256`), and
- the tracked package files plus digest for each relative path.

Use it to detect accidental drift or post-packaging tampering of the files actually present inside the bundle. Do **not** treat it as signer identity proof, maintainer endorsement, certification, or a replacement for the claim semantics already carried by `submission.json`.

Validators treat the integrity manifest additively:
- packages **without** `bundle-integrity.json` remain valid when the rest of the submission is valid,
- packages **with** a valid integrity manifest get an extra file-integrity check,
- packages **with** an invalid integrity manifest fail validation clearly.

## Example/template artifacts vs real external submissions

The repository ships **examples** and **templates** to show packaging shape.

- **Examples** are synthetic, fictional, and non-market-facing. They demonstrate what a valid package looks like and include local example evidence files.
- **Templates** are starter artifacts for future submitters. They may contain placeholder references and disclosure text that must be replaced before any real claim is made.
- **Real external submissions** are expected to replace placeholders with actual report outputs and truthful disclosures grounded in the submitter's implementation and test run.

Example and template artifacts must never be presented as proof of external vendor compatibility.

## Pairwise vs self-attested evidence packaging

The corpus supports two common packaging shapes.

### Self-attested / single-implementation claim package

Use this packaging shape for one implementation's material. A strong profile claim remains
publication-ineligible unless its evidence status is `reproducible` and its full-profile
external-IUT v1 report passes independent eligibility validation.

Typical shape:
- one `implementation_id`,
- no `peer_implementation_id`,
- exact `profile_refs`,
- one or more profile/conformance reports in `report_refs`,
- `claim_scope` of `self_attested`.

For a capability package use `claim_type=implements_capability`, exact
`capability_refs`, and one or more `capability_report` files instead of profile fields.
The shipped fictional capability example and template demonstrate only the package shape;
they are not real external evidence.

For a binding package use `claim_type=implements_binding`, exact `binding_refs`,
`binding_report`, and one eligible report-2.2 `full-binding` result per claimed binding.
Both live roles must name the same implementation build. The shipped binding template is
instructional only; it is not a real external implementation or pairwise result.

### Pairwise interoperability claim package (instructional only)

Use this when the claim is specifically about two implementations interoperating for a named profile.

Typical shape:
- one submitting `implementation_id`,
- one `peer_implementation_id`,
- one `peer_implementation_version`,
- `claim_type` of `pairwise_interop`,
- `claim_scope` of `pairwise`,
- example/template evidence illustrating the reserved packaging vocabulary.

Real pairwise publication supports exactly `AICP-BASE@0.1+BIND-MCP@0.1` through
`AICP-PAIRWISE-TCK-1.0.0`. Missing or invalid joint evidence fails closed with
`PAIRWISE_JOINT_EVIDENCE_REQUIRED`. Two independent reports and a summary are insufficient.
The dedicated joint path proves one shared report, both exact builds, cross-consumption in every required direction,
artifact/transcript digests, authenticated-profile verification material, and no degraded or
skipped mandatory checks.

Pairwise claims should be narrower than generic product claims. They should identify the exact peer and profile instead of implying broad ecosystem endorsement.

## Claim / evidence status vocabulary

Submission packages use a small controlled vocabulary in `evidence_status`:
- `example`
- `template`
- `self_attested`
- `reproducible`
- `pairwise`

This vocabulary is about package strength/scope only. It is not a certification level and it does not imply maintainer endorsement. Template packages may retain placeholder `report_refs`; those placeholders are treated as instructional warnings in the matrix, not as real-submission failures or compatibility proof.

The matrix preserves raw legacy/instructional report contents for audit visibility but
computes typed `computed_profile_marks`, `computed_capability_marks`, and
`computed_binding_marks`. `eligible_targets` retains each target kind; `computed_marks`
is their derived union. The matrix never promotes a hand-shaped or legacy
`compatibility_marks` string.

## Review and publication workflow

Real external submissions should arrive as PRs that add or update `interop/submissions/<submission_id>/`. Maintainers review them using the shipped validators plus `docs/interop/AICP_Interop_Review_Workflow.md` and `scripts/review_interop_submission.py`.

Only valid real submissions are eligible for public matrix publication. Examples/templates stay instructional and separate from real external rows, even when they validate as examples/templates. Repo-owned dry-run artifacts also stay separate from real external rows and are rendered only as rehearsal infrastructure.

A valid package in the matrix remains evidence packaging only. Matrix presence does **not** mean endorsement, certification, or automatic trust.

## Truthfulness expectations

Submission packages should use the claim language defined in:
- `docs/interop/AICP_Compatibility_Claims_and_Evidence.md`, and
- `TRADEMARKS.md`.

Do not submit vague claims such as “supports AICP.” Instead, publish the smallest truthful statement the evidence can actually support.
