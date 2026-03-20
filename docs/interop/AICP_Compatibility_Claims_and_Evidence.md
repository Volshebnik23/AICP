# AICP Compatibility Claims and Evidence

> **Status:** practical compatibility-claim guidance for already-shipped AICP profiles and reports. This document does **not** create a certification program.

## 1) Purpose

AICP already distinguishes protocol/profile compatibility from vague marketing language. This document makes the claim model explicit for external interoperability work.

It explains what kinds of claims are acceptable, what evidence must back them, and what must **not** be implied by submitted artifacts.

## 2) What this builds on

This guidance builds on the repo's existing compatibility and badge baseline:
- `docs/adoption/COMPATIBILITY_AND_BADGES.md`
- `docs/ops/COMPATIBILITY_POLICY.md`
- `docs/profiles/AICP_Profiles.md`
- `docs/rfc/RFC_Governance_and_IPR.md`

## 3) Core rule

Compatibility claims MUST stay tied to:
- shipped profile identifiers,
- shipped suite/profile definitions,
- machine-readable report evidence,
- and accurate disclosures about scope.

Avoid broad language that outruns the actual evidence.

## 4) Claim classes

### A) Self-attested implementation statement

Example wording:
- “Implementation X targets `AICP-BASE@0.1`."

Meaning:
- the implementer is stating intent or self-description,
- but no reproducible compatibility evidence has yet been attached.

What it may legitimately imply:
- implementation intent,
- expected target profile.

What it must **not** imply:
- compatibility marks,
- badge eligibility,
- pairwise interoperability,
- ecosystem endorsement.

### B) Reproducibly evidenced profile claim

Example wording:
- “Implementation X implements `AICP-BASE@0.1` with reproducible conformance evidence."
- “Implementation X is compatible with `AICP-MEDIATED-BLOCKING@0.1` based on attached profile reports."

Meaning:
- the claim is anchored to shipped profile IDs,
- required suites/profile reports exist,
- the evidence package can be re-read and revalidated.

Minimum evidence:
- exact `profile_id` / `profile_ids`,
- `suite_refs`,
- `report_refs`,
- implementation version/disclosures,
- non-degraded evidence when compatibility marks or badge-like language is used.

### C) Pairwise interoperability claim

Example wording:
- “Implementation X and implementation Y were pairwise interoperable on `AICP-BASE@0.1`."

Meaning:
- the claim is limited to the named peer pairing and named profile scope,
- it does not automatically generalize to all implementations.

Minimum evidence:
- all evidence required for a reproducibly evidenced profile claim,
- `peer_implementation_id`,
- explicit pairwise disclosures,
- clear scope language saying the claim is pairwise only.

### D) Broader ecosystem statement

Example wording:
- “This implementation has participated in multiple public AICP interop submissions on `AICP-BASE@0.1`."

Meaning:
- this is a higher-level summary over multiple pieces of evidence,
- not a single submission-level truth by itself.

What it requires:
- multiple underlying reproducible submissions,
- careful wording that avoids endorsement or certification implications.

This sprint does **not** create a machine-granted ecosystem seal.

## 5) Truthful claim language

Preferred claim forms:
- **Implements `AICP-BASE@0.1`**
- **Compatible with `AICP-MEDIATED-BLOCKING@0.1`**
- **Pairwise interoperable with `<peer_implementation_id>` on `AICP-BASE@0.1`**

The important part is specificity:
- name the shipped profile,
- name the evidence type,
- name the scope.

## 6) What is not allowed

Do **not** use:
- vague “supports AICP” language with no profile or evidence,
- language implying endorsement by the AICP project,
- unsupported badge or certification language,
- pairwise claims presented as ecosystem-wide proof,
- badge/mark language when the required reports are degraded or absent.

## 7) Claim-to-evidence mapping

| Claim class | Minimum evidence | What it does **not** prove |
|---|---|---|
| Self-attested implementation statement | clear disclosure + named target profile | compatibility mark, reproducible conformance, pairwise interop |
| Reproducibly evidenced profile claim | shipped profile IDs + suite refs + report refs + implementation version/disclosures | ecosystem-wide interoperability |
| Pairwise interoperability claim | all reproducible-evidence requirements + named peer + pairwise disclosures | general ecosystem compatibility |
| Broader ecosystem statement | multiple underlying reproducible submissions summarized honestly | certification, endorsement, universal compatibility |

## 8) Profile evidence anchors

A profile-based claim should always be anchored to:
- `registry/aicp_profiles.json`
- `conformance/profiles/`
- `conformance/extensions/` and `conformance/core/` as required by the profile
- machine-readable reports such as `conformance/report_profile_*.json`

This keeps claims tied to already-shipped repo truth.

## 9) Relationship to badges and degraded mode

Badge or compatibility-mark style wording is only appropriate when:
- the relevant required reports exist,
- the reports are non-degraded,
- the marks come from machine-readable report output,
- and the claim does not imply endorsement beyond that report evidence.

A passed-but-degraded run is **not** enough for badge-style language.

## 10) Relationship to the public interop corpus

The interop corpus defines how a submission is packaged.
Use:
- `docs/interop/AICP_Public_Interop_Corpus.md`
- `interop/submissions/submission.schema.json`

for the submission format itself.

## 11) Conservative summary

The safest rule is simple:
- do not say “supports AICP”,
- say which shipped profile is implemented,
- say what evidence exists,
- say whether the claim is self-attested, reproducibly evidenced, or pairwise,
- and do not imply more than the evidence proves.
