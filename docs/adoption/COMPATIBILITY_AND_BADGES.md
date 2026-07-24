# Compatibility and Badges (Conformance as a Contract)

AICP compatibility claims are only credible when backed by reproducible conformance reports.

## Compatibility ladder

### 1) Core compatibility
- Mark: `AICP-Core-0.1`
- Meaning: Core suite checks pass with non-degraded execution.

### 2) Extension compatibility
- Marks: `AICP-EXT-*`
- Meaning: extension suite-specific requirements pass (for example CAPNEG, ENFORCEMENT, ALERTS, RESUME).

### 3) Profile compatibility
- Marks are defined by the exact catalogs under `conformance/profiles/`; do not maintain a
  duplicate hard-coded list here.
- Meaning: all required suites for that named profile pass.

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

Opt-in provenance repository runs label their subject `reference_corpus`. They prove the
checked-in corpus/runner behavior, not an external product. IUT smoke reports also cannot
support an ordinary profile claim. Only a full-profile, complete, non-degraded external-IUT
v1 report with no skipped mandatory checks may carry an external product-profile mark.
Public interop matrix marks are recomputed through the same eligibility validator; they are
never copied from arbitrary report JSON. `self_attested` packaging alone is not eligible for
an ordinary profile mark. File digests prove artifact integrity,
not organizational identity, certification, or endorsement.

## Current external reachability

| Profile target | External full-profile target | Ordinary external mark |
|---|---|---|
| `AICP-BASE@0.1` | Available (21 mandatory cases) | Reachable only for a complete, non-degraded `external_implementation` report |
| `AICP-AUTHENTICATED-BASE@0.1` | Available (37 mandatory cases) | Unreachable: the required unavailable-crypto probe records a skipped mandatory check |
| Other 13 registered profiles | Not available | Unreachable through the current external-IUT runner |

This table is validated against `conformance/iut/cases.json` and
`docs/process/repo_truth_status.json`. Internal profile marks remain repository-owned
conformance evidence, not external product proof.

## Reusable CI snippet for adopters

Drop this workflow into your repository to publish compatibility evidence:

- [docs/snippets/github-actions/aicp-conformance.yml](../snippets/github-actions/aicp-conformance.yml)
