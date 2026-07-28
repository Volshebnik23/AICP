# Changelog

All notable repo-backed release metadata changes should be recorded here.

## Unreleased — post-0.1.0-rc.1

### Added
- Canonical repository-truth baseline plus a machine-checked profile/evidence, binding,
  security, governance, release, and registered-message status companion.
- Completed M58 Repo-Truth Rebaseline, M59 Authenticated Base Evidence Reachability, and
  M60 Exact Contract Agreement Core; M61–M70 remain planned.
- Registered experimental `AICP-IUT-TCK-1.1.0` while preserving the frozen
  `AICP-IUT-TCK-1.0.0` metadata.
- Added separate experimental Core v0.2 schemas, exact-agreement conformance, 8 positive
  and 30 expected-fail lifecycle fixtures, `AICP-BASE@0.2`, Python/TypeScript parity
  helpers, and versioned quickstarts.

### Changed
- Reconciled product, UAT, profile, interoperability, security, governance, and release
  wording so repository presence/internal conformance is not presented as independent
  external or live-transport evidence.
- Bound profile maturity, external-evidence eligibility, generated human truth, visible
  milestone status, the complete 132-entry message surface, and independent security-review
  claims to structured repository evidence.
- Extended planning validation with deterministic generation plus focused negative
  regression tests.
- Separated expected case-local unavailable-crypto observations from actual run-level IUT
  degradation without weakening normal Authenticated Base Ed25519 verification.
- Added schema-bound consumer execution observations and independent strong-evidence
  comparison against the registered TCK catalog.
- Added exact proposal/acceptance/active-head/conflict binding without changing Core v0.1,
  existing external-IUT targets, state projection v1, or the UAT baseline.

### Known limitations
- No real external or pairwise interop submission is present.
- Only Base and Authenticated Base have external full-profile IUT targets; both ordinary
  marks are reachable, but neither has real independent external evidence in this repository.
- Base 0.2 has internal experimental conformance only; it does not authenticate senders and
  has no external-IUT or independent external evidence.
- Binding suites are static fixtures, the security review is internal, and release
  repackaging remains planned under M69.

## [0.1.0-rc.1] - 2026-03-22

### Added
- TypeScript regression tests for transcript hash-chain validation under `sdk/typescript/test/chain.test.js`.
- Concise maintainer release playbook in `docs/release/RELEASING.md`.
- Lightweight stewardship guidance in `GOVERNANCE.md`.
- Productization definition-of-done checklist in `checklists/productization_dod.md`.

### Changed
- Promoted repo release metadata from `0.1.0-dev` to the conservative first release candidate `0.1.0-rc.1` via `VERSION` and release notes alignment.

### Notes
- This is a release candidate, not a GA release.
- Package publication strategy remains unchanged.
