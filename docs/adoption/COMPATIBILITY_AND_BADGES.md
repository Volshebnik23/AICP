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

Read marks from report JSON:

- `report_format_version`
- `execution_subject` (reference corpus versus external implementation/build)
- `runner.source_revision`, suite/profile digest, and input/generated artifact digests
- `compatibility_marks` list
- `passed` boolean
- `degraded`, `degraded_reasons`, and `skipped_checks`

Ordinary repository runs label their subject `reference_corpus`. They prove the checked-in
corpus/runner behavior, not an external product. Use the JSONL IUT path in
`conformance/iut/README.md` for a report bound to an external implementation. File digests
prove artifact integrity, not organizational identity, certification, or endorsement.

## Reusable CI snippet for adopters

Drop this workflow into your repository to publish compatibility evidence:

- [docs/snippets/github-actions/aicp-conformance.yml](../snippets/github-actions/aicp-conformance.yml)
