# External Security Review Handoff

This document prepares a reproducible review; it is not a completed external-review report.
It intentionally names no reviewer, engagement date, finding, or completion claim.

## 1. Freeze the reviewed revision

From a fresh checkout, record the outputs of:

```text
git rev-parse HEAD
git status --short
```

The second command must be empty before evidence generation. Retain the commit identifier in
all review notes and artifacts. Inspect the release authorities directly:

- `conformance/evidence/evidence_tck_releases.json` — current Evidence TCK
  `AICP-EVIDENCE-TCK-1.11.0`;
- `conformance/iut/tck_releases.json` — Product-IUT release line, unchanged by M67;
- `interop/pairwise/tck_releases.json` — current Pairwise TCK
  `AICP-PAIRWISE-TCK-1.3.0`, unchanged by M67;
- `security_review/threat_coverage.json` — canonical M67 security coverage authority.

Do not infer authority from a generated report, README, or the newest-looking filename.

## 2. Review scope

Review registered message/schema handling, core hashing/signatures and exact-contract
agreement, profile negotiation/composition, enforcement and alerts, object resync and resume,
delegated identity, evidence generation/evaluation, live transport, Pairwise authority
boundaries, coverage validation, and public-evidence secret exclusions.

Use the `normative_refs`, `executable_evidence`, and `residual_boundary` fields for each
manifest component. Independently verify that the named suite, case, check, and fixture
relationships are real.

## 3. Reproduce repository evidence

Run the repository's supported bootstrap, then execute:

```text
make security-coverage-validate
make security-coverage-test
make conformance-security
make conformance-ops
make conformance-all
make evidence-target-validate
make pairwise-target-validate
make validate
make test
cd sdk/typescript
npm test
npm audit
```

Record command, revision, platform, tool versions, exit status, and the complete unedited
output or its content digest. Generated reports should be preserved outside the source tree or
clearly separated from source modifications.

## 4. Non-goals and claim limits

Internal/reference executions do not prove independent review, certification, product
assurance, participant adoption, policy correctness, secure key custody, arbitrary-secret
classification, endpoint integrity, or universal DoS/rate/size limits. A deferral is an
explicit boundary, not executable mitigation.

## 5. Private reporting and remediation

Report potential vulnerabilities privately according to [`../SECURITY.md`](../SECURITY.md).
Include the frozen commit, affected threat IDs and files, minimal reproduction, observed and
expected behavior, impact, and any proposed mitigation. Do not place secrets or undisclosed
vulnerability details in public fixtures or pull requests.

After coordinated disclosure, maintainers may add an entry to
[`REMEDIATION_LOG.md`](REMEDIATION_LOG.md), update the canonical coverage manifest and tests,
and publish an external-review artifact only if it satisfies the immutable artifact contract
in [`external_reviews/README.md`](external_reviews/README.md). A completed artifact must remain
verifiable at its recorded reviewed revision and must not be fabricated from this template.
