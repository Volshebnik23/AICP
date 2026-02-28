# Security Review Package

This folder contains security-review scaffolding for external and community reviewers of AICP as a protocol.

## Purpose
- Provide concise, review-ready artifacts describing threats, assumptions, and checklists.
- Help external reviewers understand what AICP guarantees vs what platform deployments must add.

## Artifacts in this folder
- `THREAT_MODEL.md`
- `SECURITY_ASSUMPTIONS.md`
- `REVIEW_CHECKLIST.md`
- `REMEDIATION_LOG.md`
- `SELF_REVIEW.md` (internal dry-run against the review checklist)
- `COVERAGE_MAP.md` (threat-to-tests coverage matrix with evidence and gaps)

## How external reviewers should use this package
1. Read threat model and assumptions.
2. Walk the checklist against current docs/schemas/conformance artifacts.
3. Report findings with concrete reproduction where possible.

## Filing findings
- Report vulnerabilities privately first according to `SECURITY.md`.
- Use `ERRATA.md` for public spec/tooling inconsistencies once disclosure timing is agreed.
- Track remediation status in `security_review/REMEDIATION_LOG.md` after coordinated disclosure planning.
