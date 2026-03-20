# AICP Compatibility Claims and Evidence

## Purpose

This document defines the **truthful claim language** implementers should use when describing AICP compatibility and the minimum evidence expected for each claim shape.

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
- the exact shipped profile identifier (for example `AICP-BASE@0.1`),
- reproducible profile/conformance report evidence for the required suites,
- non-degraded report outputs where compatibility marks are being relied on,
- implementation/version identification in the submission manifest.

This is a claim about **what your implementation implements**, not about other implementations.

### 2) “Compatible with AICP profile X”

Use this when the evidence shows compatibility with the named shipped profile target.

Minimum expected evidence:
- the exact shipped profile identifier,
- report evidence from the repo's shipped validation/conformance/profile tooling,
- disclosures if any required checks were skipped, downgraded, synthetic, or limited to examples.

This is still a **profile-scoped** claim. It is not equivalent to claiming broad compatibility with every AICP implementation.

### 3) “Pairwise interoperable with implementation Y on profile X”

Use this only when the evidence is specifically about interoperability between two named implementations for a named shipped profile.

Minimum expected evidence:
- the exact shipped profile identifier,
- `peer_implementation_id` identifying the other implementation,
- pairwise evidence packaging that includes report/transcript references sufficient to review the specific interaction,
- disclosures that explain whether the evidence is joint, mirrored, or assembled from both sides' artifacts.

This claim is narrower than general compatibility. It should not be rephrased into a blanket ecosystem-wide statement.

## What is not allowed

The following are not acceptable public claim forms:
- vague statements such as **“supports AICP”** with no profile scope,
- badge/endorsement language that implies AICP project approval where none exists,
- unsupported marks or logos not backed by shipped repo evidence,
- claims that imply interoperability with unnamed third parties,
- examples/templates presented as if they were real external market evidence.

## Claim / evidence status vocabulary

The interop intake path uses a small `evidence_status` vocabulary to describe package strength without implying endorsement: `example`, `template`, `self_attested`, `reproducible`, and `pairwise`.

The status should stay aligned with the actual package:
- `example` / `template` for instructional artifacts only,
- `self_attested` for a real submitter-published claim package,
- `reproducible` when repo-style conformance/profile outputs are actually included,
- `pairwise` only for named peer interoperability claims.

## Evidence expectations by claim shape

| Claim shape | Minimum evidence expectation |
|---|---|
| Implements profile X | Submission manifest + shipped profile ID + reproducible report references + implementation/version metadata |
| Compatible with profile X | Submission manifest + shipped profile ID + compatible report evidence + disclosures for any limitations |
| Pairwise interoperable with implementation Y on profile X | Submission manifest + peer implementation ID + shipped profile ID + pairwise evidence references + disclosures about evidence provenance |

## Badges, marks, and endorsement boundaries

AICP compatibility evidence is evidence-first, not slogan-first.

That means:
- do not invent new badges,
- do not imply certification unless a formal program exists in-repo,
- do not imply the AICP project endorses a vendor or product,
- do not use compatibility marks without the corresponding evidence.

If compatibility marks are cited, they should trace back to actual report JSON fields such as `compatibility_marks`, together with the associated pass/degraded state.

## Relationship to `TRADEMARKS.md`

`TRADEMARKS.md` governs how AICP names and marks may be used in public-facing materials.

This document adds the evidence-policy layer:
- `TRADEMARKS.md` says **how not to imply endorsement**.
- this document says **how to phrase a truthful compatibility claim**.
- the public interop corpus says **how to package evidence for review**.

All three should be read together before publishing market-facing compatibility language.
