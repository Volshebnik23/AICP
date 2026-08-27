# Security Review Checklist

Use this checklist against an immutable revision captured with
[`EXTERNAL_REVIEW_HANDOFF.md`](EXTERNAL_REVIEW_HANDOFF.md). Record findings separately; checking
a box does not change canonical coverage status.

## Repository and authority

- [ ] Record the exact commit, worktree state, and validation environment.
- [ ] Validate `security_review/threat_coverage.json` against its schema and semantic validator.
- [ ] Confirm `COVERAGE_MAP.md` is generated and current.
- [ ] Confirm every covered row resolves to existing registered checks, cases, and referenced fixtures.
- [ ] Confirm every deferred row has a permitted defer class, specific rationale, and owner.
- [ ] Confirm release registries identify exactly one current authority per TCK family.

## Protocol surfaces

- [ ] Core canonicalization, hashes, signatures, chain invariants, and truncation boundaries are unambiguous.
- [ ] Exact-contract proposal, acceptance, active-head, context, and conflict references resist substitution.
- [ ] CAPNEG rejects stale-declaration rollback and profile-composition downgrade.
- [ ] POLICY_EVAL binds decisions to their evaluated context and registry codes.
- [ ] ENFORCEMENT binds authority, target, and verdict references and preserves hard-gate delivery.
- [ ] ALERT registry validation is separated from deployment-specific privacy classification.
- [ ] OBJECT_RESYNC validates object hashes and exposes access, size, and redaction mechanisms without claiming universal policy.
- [ ] RESUME binds request/response state and documents probing and forced-loop boundaries.
- [ ] Delegated identity and multi-profile composition preserve the named signer and profile constraints.
- [ ] Live-transport evidence proves the named runtime behavior and rejects invalid TLS/trust paths.

## Evidence, privacy, and claims

- [ ] Public evidence schemas exclude test-control secrets and private key material.
- [ ] Arbitrary application-secret classification is not overstated as schema coverage.
- [ ] Historical Evidence TCK releases and the current release resolve with their recorded lifecycle and eligibility.
- [ ] Product-IUT and Pairwise TCK release lines are unchanged unless the reviewed scope explicitly changes them.
- [ ] Internal/reference evidence is not described as independent external evidence or adoption.
- [ ] External-review completion, reviewer identity, dates, and findings point to real contracted artifacts.

## Reproduction

- [ ] `make security-coverage-validate`
- [ ] `make security-coverage-test`
- [ ] `make conformance-security`
- [ ] `make conformance-ops`
- [ ] `make conformance-all`
- [ ] `make evidence-target-validate`
- [ ] `make pairwise-target-validate`
- [ ] `make validate`
- [ ] `make test`
- [ ] TypeScript tests and dependency audit complete under the repository's supported commands.

Primary references: [`threat_coverage.json`](threat_coverage.json),
[`THREAT_MODEL.md`](THREAT_MODEL.md), [`SECURITY_ASSUMPTIONS.md`](SECURITY_ASSUMPTIONS.md),
[`../docs/core/AICP_Core_v0.1_Normative.md`](../docs/core/AICP_Core_v0.1_Normative.md), and
[`../conformance/`](../conformance/).
