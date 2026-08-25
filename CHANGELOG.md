# Changelog

All notable repo-backed release metadata changes should be recorded here.

## Unreleased — post-0.1.0-rc.1

### Added
- Canonical repository-truth baseline plus a machine-checked profile/evidence, binding,
  security, governance, release, and registered-message status companion.
- Completed M58 Repo-Truth Rebaseline through M65 Registered Message Surface Completion;
  M66–M70 remain planned.
- Registered experimental `AICP-IUT-TCK-1.1.0` while preserving the frozen
  `AICP-IUT-TCK-1.0.0` metadata.
- Added separate experimental Core v0.2 schemas, exact-agreement conformance, 9 positive
  and 41 expected-fail lifecycle fixtures, `AICP-BASE@0.2`, Python/TypeScript parity
  helpers, and versioned quickstarts.
- Added separately selected experimental EXT-CAPNEG v0.2 with a generated 16-profile
  composition-rules registry, canonical set/result hashing, declaration/revision/full-
  acceptance state reduction, contract binding, Authenticated Base Ed25519 enforcement,
  20 positive and 104 exact expected-fail cases, and Python/TypeScript shared/direct parity.
- Added composition-aware session-state projection v2 with four positive and nine negative
  cases and an internal-only evidence mark.
- Added target-oriented external evidence report v2, frozen historical
  `AICP-EVIDENCE-TCK-1.0.0`, corrected `AICP-EVIDENCE-TCK-1.1.0`, and the exact
  `aicp.session_state_projection@v1` full-capability target with one producer and all 12
  owning-suite consumer transcripts.
- Added independent capability report evaluation, protocol-1.1 reference/test adapters,
  35 negative adapter modes, report-forgery and mutation controls, and truthful
  missing-dependency handling.
- Corrected M62 producer evidence so adapter requests contain a neutral raw-fact scenario
  and response-free transcript prefix rather than the reviewed projection. Target lookup
  is registry-driven through explicit handlers, target versions are kind-appropriate, the
  registry schema is provenance-bound, and the runner bundle is generated from its static
  runtime import closure. Historical 1.0.0 reports cannot support current strong claims.
- Added typed public `implements_capability` submissions, a fictional example and template,
  independently computed capability marks/targets in the interop matrix, and separate
  profile/capability repo-truth counts.
- Added generalized external report 2.1 and `AICP-EVIDENCE-TCK-1.2.0` for exactly Mediated
  Blocking, Resumable Sessions, and Delegated Identity, with one reusable product-profile
  handler, 32 answer-isolated producer scenarios, and all 69 required-suite consumer cases.
- Added independent in-memory transcript validation, one target-aware reference adapter,
  a test-only external adapter, fail-closed profile-specific/generic negative modes, nine
  focused Make targets, and public report-2.1 strong profile-claim evaluation with exact
  load-bearing `suite_refs`.
- Added corrected `AICP-EVIDENCE-TCK-1.3.0` for all four generalized targets, immutable
  per-release registry snapshots, actual import-closure bundle self-checking, handler-owned
  report-2.1 artifact kinds, dynamically derived producer suite-check inventory, and exact
  generated-artifact ID cardinality enforcement. Frozen 1.1.0 projection reports remain
  strong-eligible; frozen 1.0.0 and 1.2.0 are explicitly strong-ineligible for their
  documented evidence defects.
- Froze `AICP-EVIDENCE-TCK-1.3.0` as strong-ineligible and registered current
  `AICP-EVIDENCE-TCK-1.4.0`. Generated Tier-1 transcripts now route all 26 exercised
  message types to their exact Core/extension v0.1 owner payload schemas, fail closed on
  missing or conflicting routes, and match the ordinary conformance namespace rules.
  Differential coverage compares all 38 canonical transcripts across the 18 semantic
  implementation families represented by the unchanged 95 producer-suite rows.
- Added M64 live loopback HTTP/SSE/WebSocket/WSS and MCP stdio binding evidence, report
  2.2, trace v4, and the exact `BIND-HTTP@0.1` and `BIND-MCP@0.1` external targets.
- Completed M65 with byte-backed positive-fixture accounting for all 132 registered
  messages. Five existing orphan fixture paths were promoted and strengthened, six new
  deterministic positive lifecycle fixtures were added, four focused semantic check IDs
  were introduced, and existing semantic families were extended with hash-valid mutation
  controls. No new negative fixture, registered message ID, compatibility mark, or external
  target was added.
- Froze `AICP-EVIDENCE-TCK-1.8.0` as historical/strong-eligible and registered current
  `AICP-EVIDENCE-TCK-1.9.0` for the expanded conformance corpus. Report 2.2 and trace v4
  remain unchanged; Tier-1 consumer counts are now 26 mediated, 16 resumable, and 31
  delegated.
### Changed
- Reconciled product, UAT, profile, interoperability, security, governance, and release
  wording so repository presence/internal conformance is not presented as independent
  external or live-transport evidence.
- Bound profile maturity, external-evidence eligibility, generated human truth, visible
  milestone status, the complete 132/132 actual-positive message surface, and independent
  security-review claims to structured repository evidence.
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
- Corrected M61 with a reviewed reducer-independent expectation catalog, exact
  `{code,message_index,message_id,exact_count}` observations, a complete per-message
  validity barrier, all-present-signature validation, sender-signature enforcement,
  replay-before-idempotence validation, decision context/latest-declaration binding,
  terminal rejection, participant-required crypto, same-context supersession,
  Python/TypeScript channel/limit parity, prefix-exact projection v2, and frozen Core
  v0.1 contract validation. CAPNEG v0.1, Core, projection v1, UAT, and IUT surfaces were
  not changed.
- Completed the M61 follow-up correction with executable oracle mutation controls, one
  current accepted root per session/contract/participant context, replay-safe successor
  supersession, direct fail-closed no-crypto reducers, reviewed composition expectations,
  and reference-only cross-language/projection manifests. Generated messages and expected
  semantics now each have one canonical representation.
- Preserved external-IUT report v1 and its two profile targets while adding report v2 as a
  separate target-oriented family. Capability evidence cannot prove a profile, and neither
  examples nor raw marks are promoted to external evidence.

### Known limitations
- No real external or pairwise interop submission is present.
- Strict projection v1 has one externally testable capability target and reachable evidence
  mark, but no real independently demonstrated external capability.
- Five profiles have external full-profile targets: Base and Authenticated Base through
  profile-IUT v1, plus the three Tier-1 profiles through generalized evidence v2.1. Their
  ordinary marks are reachable, but none has real independent external evidence here.
- Base 0.2 has internal experimental conformance only; it does not authenticate senders and
  has no external-IUT or independent external evidence.
- Live binding targets have repository-owned loopback reference evidence but no real
  independent external binding submission; the security review is internal, and release
  repackaging remains planned under M69.
- Projection v2 remains internal-only; external composition and pairwise evidence remain
  unavailable.

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
