# Security Review Package

This directory is the review entry point for AICP's protocol security surface.

## Current status

M67 completed the internal security-coverage closure recorded in the canonical
[`threat_coverage.json`](threat_coverage.json) manifest. Its generated
[`COVERAGE_MAP.md`](COVERAGE_MAP.md) contains 36 threat components: 24 are `covered`,
12 are `deferred`, and none are `partial`. Covered rows resolve to registered checks,
suites, cases, and fixtures; deferred rows state their scope class, rationale, and owner.

This is internal repository evidence, not an independent security assessment.
`repository_truth.external_independent_review_completed` remains `false`, and the completed
external-review artifact list is empty. A future completion claim must satisfy the
machine-checked [`external_reviews/README.md`](external_reviews/README.md) contract.

## Artifacts

- [`threat_coverage.json`](threat_coverage.json): canonical coverage authority.
- [`threat_coverage.schema.json`](threat_coverage.schema.json): manifest schema.
- [`COVERAGE_MAP.md`](COVERAGE_MAP.md): generated human-readable view; do not edit it directly.
- [`M67_SECURITY_CLOSURE.md`](M67_SECURITY_CLOSURE.md): internal closure record.
- [`THREAT_MODEL.md`](THREAT_MODEL.md): protocol-scope threats and trust boundaries.
- [`SECURITY_ASSUMPTIONS.md`](SECURITY_ASSUMPTIONS.md): explicit assurance boundaries.
- [`REVIEW_CHECKLIST.md`](REVIEW_CHECKLIST.md): reusable review procedure.
- [`EXTERNAL_REVIEW_HANDOFF.md`](EXTERNAL_REVIEW_HANDOFF.md): reproducible handoff package.
- [`REMEDIATION_LOG.md`](REMEDIATION_LOG.md): coordinated-disclosure remediation register.
- [`SELF_REVIEW.md`](SELF_REVIEW.md): historical M9.1 internal dry-run snapshot.
- [`OPS_HARDENING_GUIDE.md`](OPS_HARDENING_GUIDE.md): non-normative operator guidance.

## Reproduce the internal evidence

Run `make security-coverage-validate` to validate the canonical manifest and generated map,
`make security-coverage-test` for focused M67 regressions, and `make conformance-security`
plus `make conformance-ops` for the registered security and operational suites.

## External-review workflow

1. Capture an immutable repository revision and follow
   [`EXTERNAL_REVIEW_HANDOFF.md`](EXTERNAL_REVIEW_HANDOFF.md).
2. Read the threat model, assumptions, canonical coverage manifest, and residual boundaries.
3. Reproduce the named validation commands and inspect the exact referenced artifacts.
4. Report potential vulnerabilities privately according to [`../SECURITY.md`](../SECURITY.md).
5. After coordinated disclosure, record remediation in [`REMEDIATION_LOG.md`](REMEDIATION_LOG.md).
