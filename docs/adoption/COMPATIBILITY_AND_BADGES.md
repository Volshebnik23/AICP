# Compatibility and Badges (Conformance as a Contract)

AICP compatibility claims are only credible when backed by reproducible conformance reports.

## Compatibility ladder

### 1) Core compatibility
- Mark: `AICP-Core-0.1`
- Meaning: Core suite checks pass with non-degraded execution.
- Experimental post-UAT mark: `AICP-Core-0.2`
- Meaning: the separate Core v0.2 exact-agreement suite passes; it does not substantiate
  Core/Base 0.1, sender authentication, or external implementation evidence.

### 2) Extension compatibility
- Marks: `AICP-EXT-*`
- Meaning: extension suite-specific requirements pass (for example CAPNEG, ENFORCEMENT, ALERTS, RESUME).
- Stable CAPNEG v0.1 and experimental CAPNEG v0.2 are separate surfaces and emit
  `AICP-EXT-CAPNEG-0.1` and `AICP-EXT-CAPNEG-0.2`, respectively. A degraded v0.2 run emits
  neither its extension mark nor any component mark.

### 3) Profile compatibility
- Marks are defined by the exact catalogs under `conformance/profiles/`; do not maintain a
  duplicate hard-coded list here.
- Meaning: all required suites for that named profile pass.

CAPNEG v0.2 composition is not another profile tier. The resolver exposes expected
component mark identities for auditing but does not award them. There is no dynamic
composition profile ID, aggregate product mark, or external composition badge. A truthful
composition claim requires CAPNEG v0.2 evidence plus separate evidence for every component;
M62's generalized framework registers only projection-v1 capability evidence and does not
add external composition evidence.

The internal CAPNEG v0.2 mark is eligible only when the reducer-independent reviewed
oracle matches exact error origin/multiplicity and final state, all mandatory message and
signature checks execute, and the run is non-degraded. This strengthens repository-owned
behavioral evidence; it does not make that evidence external or award component marks.

### 4) Security evidence marks
- Mark: `AICP-SECURITY-SIGNED-PATH-0.1`
- Meaning: signed-path evidence suite passed (including signature verification checks when available).

### 5) Operational hardening evidence marks
- Mark: `AICP-OPS-HARDENING-0.1`
- Meaning: deterministic ops-abuse checks passed.
- Note: this is operational evidence, not baseline protocol compatibility by itself.

## Badge eligibility and degraded mode

- If `degraded == true` for any required suite, compatibility marks MUST NOT be awarded for the affected suite/profile.
- Any skipped mandatory check suppresses eligibility even if the adapter declares `degraded=false`.
- A report can be `passed=true` but still non-badge-eligible when critical checks are unavailable.
- The Core v0.2 mark is eligible only when `passed=true`, `degraded=false`,
  `degraded_reasons=[]`, and `skipped_checks=[]`. The Base 0.2 profile applies the same
  rule to every required child suite, aggregates and deduplicates degradation/skipped
  truth, and never synthesizes a missing child mark.
- Missing JSON Schema or Ed25519 verification support makes the affected v0.2 run
  non-badge-eligible. CLI output identifies a behavioral success as `PASSED (DEGRADED)`.
- For `CN_CAPNEG_0.2`, missing JSON Schema support degrades all schema-dependent coverage;
  missing cryptographic support degrades authenticated-composition coverage. In both cases
  `AICP-EXT-CAPNEG-0.2` is suppressed.

## How to verify

Run:

- `make conformance-all`

Common report outputs:

- `conformance/report.json` (Core)
- `conformance/report_ext_*.json` (Extensions)
- `conformance/report_profile_*.json` (Profiles)
- `conformance/report_security_signed_path.json` (Security evidence)
- `conformance/report_ops_hardening.json` (Ops hardening evidence)

The frozen UAT `conformance/report*.json` and ordinary profile reports retain their legacy
report shape. Read their existing `compatibility_marks`, `passed`, `degraded`, and
`skipped_checks` fields as before.

Post-UAT provenance and external-IUT v1 reports additionally provide:

- `report_format_version`
- `execution_subject` (reference corpus versus external implementation/build)
- `runner.source_revision`, suite/profile digest, and input/generated artifact digests
- `compatibility_marks` list
- `passed` boolean
- `degraded`, `degraded_reasons`, and `skipped_checks`
- structured per-consumer `execution_observation` evidence checked against the registered
  IUT case catalog

Opt-in provenance repository runs label their subject `reference_corpus`. They prove the
checked-in corpus/runner behavior, not an external product. IUT smoke reports also cannot
support an ordinary profile claim. Only a full-profile, complete, non-degraded external-IUT
v1 report with no skipped mandatory checks may carry an external product-profile mark.
Public interop matrix marks are recomputed through the same eligibility validator; they are
never copied from arbitrary report JSON. `self_attested` packaging alone is not eligible for
an ordinary profile mark. File digests prove artifact integrity,
not organizational identity, certification, or endorsement.

Generalized external report v2 is a separate target-oriented family. M62 registers only
`aicp.session_state_projection@v1` in `full-capability` mode under
`AICP-EVIDENCE-TCK-1.1.0`. A complete external implementation may be eligible for
`AICP-Evidence-SESSION-STATE-PROJECTION-v1`; reference, smoke, degraded, skipped, incomplete,
or provenance-mismatched reports emit no capability mark. This evidence mark is not an
ordinary product-profile mark and cannot prove profile conformance, certification,
composition, organizational identity, or pairwise interoperability. Projection v2 remains
internal-only.

Evidence TCK 1.0.0 is frozen historical data with superseded-experimental status: its
producer challenge did not isolate the expected answer, and no real external submission
depended on it. A schema-valid 1.0.0 report cannot support the current capability mark.

## Current external reachability

This table describes external-IUT target availability, not repository availability or
registry maturity. Those separate facts are generated from the registry in
[`AICP_Profiles.md`](../profiles/AICP_Profiles.md#2-profile-catalog-and-status).

| Profile target | External full-profile target | Ordinary external mark |
|---|---|---|
| `AICP-BASE@0.1` | Available (21 mandatory cases) | Reachable only for a complete, non-degraded `external_implementation` report |
| `AICP-AUTHENTICATED-BASE@0.1` | Available (37 mandatory cases) | Reachable for a complete eligible external implementation; the unavailable-crypto probe remains mandatory and case-local |
| `AICP-BASE@0.2` | Not available | Internal experimental conformance only in M60 |
| Other 13 registered profiles | Not available | Unreachable through the current external-IUT runner |

This table is validated against `conformance/iut/cases.json` and
`docs/process/repo_truth_status.json`. Internal profile marks remain repository-owned
conformance evidence, not external product proof.

## Reusable CI snippet for adopters

Drop this workflow into your repository to publish compatibility evidence:

- [docs/snippets/github-actions/aicp-conformance.yml](../snippets/github-actions/aicp-conformance.yml)
