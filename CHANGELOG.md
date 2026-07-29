# Changelog

All notable repo-backed release metadata changes should be recorded here.

## Unreleased — post-0.1.0-rc.1

### Added
- Canonical repository-truth baseline plus a machine-checked profile/evidence, binding,
  security, governance, release, and registered-message status companion.
- Completed M58 Repo-Truth Rebaseline, M59 Authenticated Base Evidence Reachability, M60
  Exact Contract Agreement Core, and M61 Multi-Profile Composition and CAPNEG v0.2;
  M62–M70 remain planned.
- Registered experimental `AICP-IUT-TCK-1.1.0` while preserving the frozen
  `AICP-IUT-TCK-1.0.0` metadata.
- Added separate experimental Core v0.2 schemas, exact-agreement conformance, 9 positive
  and 41 expected-fail lifecycle fixtures, `AICP-BASE@0.2`, Python/TypeScript parity
  helpers, and versioned quickstarts.
- Added separately selected experimental EXT-CAPNEG v0.2 with a generated 16-profile
  composition-rules registry, canonical set/result hashing, declaration/revision/full-
  acceptance state reduction, contract binding, Authenticated Base Ed25519 enforcement,
  11 positive and 51 exact expected-fail cases, and Python/TypeScript shared-vector parity.
- Added composition-aware session-state projection v2 with one positive and four negative
  cases and an internal-only evidence mark.

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
- Preserved stable CAPNEG v0.1 as the canonical default for its four message IDs while
  adding machine-checked v0.1/v0.2 selectors; added v1/v2 selection for
  `STATE_SYNC_RESPONSE` without changing the v1 schema, suite, or evidence boundary.
- Kept external composition claims fail-closed: no aggregate profile ID/mark was added, and
  the public submission schema remains closed to unsupported composition fields.
- Corrected M60 so degraded/skipped v0.2 runs emit no marks, present optional signatures
  are cryptographically verified, invalid messages cannot advance agreement state, every
  negative fixture verifies post-rejection state, and six reused Core IDs expose explicit
  v0.1/v0.2 payload-schema variants.

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
