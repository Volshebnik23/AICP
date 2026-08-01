# AICP Compatibility Claims and Evidence

## Purpose

This document defines the **truthful claim language** implementers should use when describing AICP compatibility and the minimum evidence expected for each claim shape.

Current reachability is narrower than the registered catalog: only Base and Authenticated
Base have full external-IUT targets, both ordinary marks are reachable for complete eligible
implementations. Separately, strict session-state projection v1 has one generalized
`full-capability` external target and one reachable capability evidence mark. No real
external capability, profile, or pairwise submission is present. See
`docs/process/AICP_Repo_Truth_Baseline.md`.

Experimental `AICP-BASE@0.2` has internal conformance only in M60. It has no external-IUT
target, so its repository-owned Core/profile marks are not independent external product
evidence.

Experimental CAPNEG v0.2 has internal composition conformance only in M61. The public
submission schema accepts exact named profile and capability claims, but has no composition claim type,
composition hash, accepted-result hash, or composition evidence object. Because the schema
is closed to additional properties, attempted composition claims fail validation. Do not
translate an internal `AICP-EXT-CAPNEG-0.2` report into external component-profile proof or
an aggregate badge. M62 registers only projection-v1 capability evidence; it does not add
external composition evidence.

M61's internal suite uses a reviewed expectation catalog that is independent of the
production reducer and compares exact message origin, multiplicity, and final state.
That removes a self-confirming test-oracle defect, but the resulting report is still
repository-owned internal evidence rather than an independent external implementation
observation.

It complements:
- `docs/interop/AICP_Public_Interop_Corpus.md` for packaging guidance,
- `docs/interop/AICP_Interop_Submission_Playbook.md` for submitter onboarding,
- `docs/adoption/COMPATIBILITY_AND_BADGES.md` for marks/badge framing,
- `TRADEMARKS.md` for trademark and endorsement boundaries.

## Allowed claim language

Prefer the smallest truthful statement the evidence supports.

### 1) “Implements AICP profile X”

Use this when the implementation has evidence that it implements the named shipped profile target.

Minimum expected evidence:
- the exact shipped profile identifier and version (for example `AICP-BASE@0.1`) in
  `profile_refs`,
- an eligible full-profile external-IUT v1 report bound to the implementation
  ID/version/build digest and a registered TCK release,
- non-degraded report outputs where compatibility marks are being relied on,
- implementation/version identification in the submission manifest.

This is a claim about **what your implementation implements**, not about other implementations.

### 2) “Compatible with AICP profile X”

Use this when the evidence shows compatibility with the named shipped profile target.

Minimum expected evidence:
- the exact shipped profile identifier/version,
- a passed, non-degraded full-profile external-IUT v1 report whose complete mandatory case
  set, suite/profile/input/generated digests, and mark are independently revalidated,
- no skipped mandatory checks, plus explicit disclosures.

This is still a **profile-scoped** claim. It is not equivalent to claiming broad compatibility with every AICP implementation.

### 3) “Implements AICP capability X”

Use this only for an exact capability ID/version registered by the external evidence
framework. M62's only executable target is
`aicp.session_state_projection@v1`.

Minimum expected evidence:
- `claim_type=implements_capability`,
- exact `capability_refs` with capability ID and version,
- `evidence_status=reproducible`,
- a schema-valid report v2 in `full-capability` mode for the exact implementation subject,
- independently validated target, TCK, suite/input, producer/determinism, consumer, and
  no-degradation/no-skip provenance.

The current release is `AICP-EVIDENCE-TCK-1.1.0`. It binds an answer-isolated neutral
producer scenario, registry schema, registered handler, and import-closed runner bundle.
The frozen historical 1.0.0 release cannot support a current strong claim.

The exact eligible mark is `AICP-Evidence-SESSION-STATE-PROJECTION-v1`. It is a capability
evidence mark, not a product-profile mark, certification, composition mark, or pairwise
result. An internal suite report, reference report, smoke report, self-attested package, or
raw mark string cannot substantiate this claim.

### 4) “Pairwise interoperable with implementation Y on profile X”

Use this only when the evidence is specifically about interoperability between two named implementations for a named shipped profile.

Real publication is intentionally fail-closed in this release. The manifest vocabulary and
fictional examples remain available, but validators return `PAIRWISE_JOINT_EVIDENCE_REQUIRED`.
Two independent single-IUT reports, co-conformance, or a prose/JSON summary do not establish
that the named implementations exchanged and consumed each other's artifacts.

A future dedicated joint runner must bind one shared run ID, exact profile/version, both
implementation IDs/versions/build digests, A-to-B and (where bidirectional) B-to-A artifact
digests/results, authenticated-profile verification material, and zero degraded or skipped
mandatory checks.

This claim is narrower than general compatibility. It should not be rephrased into a blanket ecosystem-wide statement.

## What is not allowed

The following are not acceptable public claim forms:
- vague statements such as **“supports AICP”** with no profile scope,
- badge/endorsement language that implies AICP project approval where none exists,
- unsupported marks or logos not backed by shipped repo evidence,
- claims that imply interoperability with unnamed third parties,
- examples/templates presented as if they were real external market evidence.
- a dynamic composition ID, aggregate composition badge, or external composition claim
  inferred from CAPNEG v0.2 internal evidence.

## Claim / evidence status vocabulary

The interop intake path uses a small `evidence_status` vocabulary to describe package strength without implying endorsement: `example`, `template`, `self_attested`, `reproducible`, and `pairwise`.

The status should stay aligned with the actual package:
- `example` / `template` for instructional artifacts only,
- `self_attested` remains a migration/informational packaging status, but it is not eligible
  for an ordinary profile mark or a strong profile claim,
- `reproducible` when repo-style conformance/profile outputs are actually included,
- `pairwise` only for named peer interoperability claims.

## Evidence expectations by claim shape

| Claim shape | Minimum evidence expectation |
|---|---|
| Implements profile X | `evidence_status=reproducible` + exact profile/version + eligible full-profile external-IUT v1 evidence bound to the implementation/build |
| Compatible with profile X | `evidence_status=reproducible` + exact profile/version + eligible full-profile external-IUT v1 evidence + truthful disclosures |
| Implements capability X | `evidence_status=reproducible` + exact capability ID/version + eligible target-oriented full-capability report v2 bound to the implementation/build |
| Pairwise interoperable with implementation Y on profile X | Not currently publishable; reserved manifest vocabulary and instructional examples fail closed until a dedicated joint-execution runner exists |

Repository golden-fixture and profile runs are labelled `reference_corpus`. They verify the
repository's canonical artifacts but cannot substantiate an external implementation claim.
Examples, templates, and dry runs may carry those reports only as instructional evidence.
IUT smoke reports are likewise diagnostic-only and cannot substantiate a real profile claim.
Capability smoke and `reference_corpus` reports are likewise ineligible. Projection v2
remains internal-only and has no external target.

For current TCK reports, every consumer case carries a schema-bound execution observation.
The validator independently compares its accounting scope, accepted result, degraded
state, exact reasons, and exact skipped checks with the registered case catalog. The
Authenticated Base unavailable-crypto probe is the sole current
`case_local_expected` degraded observation; actual run-level degradation remains
ineligible.

## Badges, marks, and endorsement boundaries

AICP compatibility evidence is evidence-first, not slogan-first.

That means:
- do not invent new badges,
- do not imply certification unless a formal program exists in-repo,
- do not imply the AICP project endorses a vendor or product,
- do not use compatibility marks without the corresponding evidence.

If compatibility marks are cited, they must be independently recomputed from eligible
evidence. The public matrix does not trust or promote arbitrary strings found in a report's
`compatibility_marks` field; legacy and instructional raw marks remain audit-only content.

Report and bundle digests prove integrity of the tested artifacts, not organizational
identity. `bundle-integrity.json` is not certification; a self-attested report is not
maintainer endorsement. Publication, signing, and human review of external implementation
identity remain outside the report format.

## Relationship to `TRADEMARKS.md`

`TRADEMARKS.md` governs how AICP names and marks may be used in public-facing materials.

This document adds the evidence-policy layer:
- `TRADEMARKS.md` says **how not to imply endorsement**.
- this document says **how to phrase a truthful compatibility claim**.
- the public interop corpus says **how to package evidence for review**.

All three should be read together before publishing market-facing compatibility language.
