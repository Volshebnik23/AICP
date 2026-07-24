# Changelog

All notable repo-backed release metadata changes should be recorded here.

## Unreleased — post-0.1.0-rc.1

### Added
- Canonical repository-truth baseline plus a machine-checked profile/evidence, binding,
  security, governance, release, and registered-message status companion.
- Planned M58–M70 milestone sequence for the work that remains after protocol hardening.

### Changed
- Reconciled product, UAT, profile, interoperability, security, governance, and release
  wording so repository presence/internal conformance is not presented as independent
  external or live-transport evidence.
- Extended planning validation with structured consistency checks and focused regression
  tests.

### Known limitations
- No real external or pairwise interop submission is present.
- Only Base and Authenticated Base have external full-profile IUT targets; only Base can
  currently reach an ordinary external profile mark.
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
