# Release Notes

## Unreleased — post-0.1.0-rc.1 repository work

This section records material repository work after the current RC metadata. It is not a new
tag, package publication, GA declaration, or final RC repackaging.

### Repository changes already present after the documented RC

- Verification gates, conformance cataloging, runner modularization, provenance-rich report
  formats, the experimental external-IUT TCK, authenticated-base profile, and strict
  session-state projection are present in the repository.
- The canonical repository-truth baseline now distinguishes shipped artifacts, registry
  stability, internal verification, external testability, independent evidence, live
  binding evidence, and remaining milestones.
- Roadmap and backlog roles are separated: M58–M67 are shipped, while M68–M70 retain
  the remaining governance, release, and plugfest work.
- M66's current Pairwise TCK 1.3 binds independent client/server role evidence, run-global
  causality, exact MCP cursor progression, and two clean executions in both directions.
  Its peers are repository-owned and establish no external pairwise adoption.
- M67 replaces the manual threat map with a schema-bound 36-component manifest and generated
  view: 24 components are covered, 12 are explicitly deferred to deployment/ecosystem scope,
  and none remain partial. New exact vectors cover signed-flow truncation, stale CAPNEG
  rollback, enforcement target/reference/authority binding, and OBJECT_RESYNC status/hash
  behavior. Current Evidence TCK 1.11 retains report 2.2, trace v4, and six targets while
  expanding Tier-1 consumers to 30/20/32. Evidence TCK 1.10 is frozen historical/eligible;
  Product-IUT and Pairwise TCK 1.3 are unchanged.
- The M67 external-review handoff is reproducible preparation, not a completed independent
  security review or evidence of external adoption.
- The M67 load-bearing correction upgrades the threat manifest to schema 1.1, where each
  suite claim binds an exact case, fixture, pass/fail expectation, and expected-failure set;
  direct evidence must identify an actual top-level pytest definition. New AL-03 and SP-04
  negatives close the ALERT action-registration and selected signed-ALERT gaps without a new
  wire rule. Exact pre-M67 Mediated and Resumable Evidence 1.10 reports remain eligible under
  the current evaluator. Evidence 1.11, Product-IUT, and Pairwise TCK 1.3 are unchanged.
- Experimental `AICP-IUT-TCK-1.1.0` introduces explicit case-local execution accounting and
  structured consumer observations; the historical 1.0.0 registry record remains frozen.
- Experimental post-UAT Core v0.2 adds exact contract artifact and active-head agreement
  under `AICP-BASE@0.2`, with separate schemas, suite, fixtures, helpers, and quickstarts.
  Its M60 correction makes marks fail closed under degraded/skipped execution, verifies
  every present optional signature, blocks state changes from invalid messages, and
  publishes version-selected v0.1/v0.2 schema mappings for the six reused Core IDs.
  Core/Base 0.1 and the UAT target remain unchanged.
- Experimental EXT-CAPNEG v0.2 adds canonical negotiation of exact registered Core
  v0.1-family profile sets, separate composition/result hashes, declaration supersession,
  proposal revisioning, full-participant acceptance, Authenticated Base Ed25519 acceptance,
  contract binding, and internal composition-aware session-state projection v2. Stable
  CAPNEG v0.1, projection v1, profile catalogs/marks, Core, UAT, and IUT surfaces remain
  unchanged.
- The M61 correction separates generated transcripts from a reviewed semantic oracle,
  preserves exact error origin and multiplicity, validates every message and every present
  signature before reduction, binds decisions/replays to exact context and latest
  declarations, makes rejection revision-terminal, enforces participant crypto minimums
  and same-context supersession, aligns Python/TypeScript selection semantics, validates
  bound Core v0.1 contracts, and evaluates projection v2 at its exact transcript prefix.
  The strengthened corpus contains 20 positive and 104 negative CAPNEG cases plus four
  positive and nine negative projection-v2 cases.
- The M61 follow-up executes broken semantic implementations through the real suite
  comparator, enforces one accepted negotiation root per exact context, keeps exact
  successor replay safe after predecessor supersession, makes direct reducers fail closed
  without crypto verification, and replaces copied cross-language/projection evidence with
  compact references to one message source and one reviewed semantic oracle.
- M62 adds a separate target-oriented external evidence report v2 without changing profile
  IUT report v1 or adapter protocol 1.1. The original `AICP-EVIDENCE-TCK-1.0.0` record is
  byte-frozen and superseded because its producer challenge disclosed the reviewed answer;
  no real external submission depended on it. Corrected `AICP-EVIDENCE-TCK-1.1.0` uses a
  neutral raw-fact scenario and response-free transcript prefix, registry-driven handler
  dispatch, kind-appropriate exact target versions, registry-schema provenance, and a
  generated static import-closure runner manifest.
  Its only registered target is experimental
  `aicp.session_state_projection@v1`: one deterministic producer and all 12 owning-suite
  consumers are digest-bound and independently evaluated. Only complete non-degraded
  `full-capability` execution by an `external_implementation` can reach
  `AICP-Evidence-SESSION-STATE-PROJECTION-v1`; reference and smoke runs emit no mark.
- Public submissions now support exact `implements_capability` claims and the matrix keeps
  independently computed profile and capability marks/targets separate. The checked-in
  capability example and external-kind adapter are fictional test artifacts, not real
  external evidence.
- M63 adds report 2.1 and Evidence TCK 1.2.0 for exactly the Mediated Blocking, Resumable
  Sessions, and Delegated Identity product profiles. A shared handler runs 32 neutral
  producer scenarios and 69 suite-derived consumer cases, independently validates returned
  transcripts, and emits an ordinary profile mark only for complete non-degraded external
  execution. Public profile claims accept this path with exact required-suite `suite_refs`;
  reference and test-only adapters do not count as external evidence.
- The M63 correction freezes 1.2.0 as strong-ineligible and registers current Evidence TCK
  1.3.0. Release-specific snapshots preserve exact historical registry provenance, current
  executions self-check their actual import-closure bundle, every required producer-suite
  check is machine-accounted and executable, and duplicate/missing/unknown generated
  artifact IDs fail exact `Counter` equality before map construction. Exact 1.1.0
  projection reports remain strong-eligible; report 2.0 support is retained.
- The M63 semantic-closure correction freezes 1.3.0 as strong-ineligible and registers
  current Evidence TCK 1.4.0 without changing report 2.1. Its generated-message router is
  derived from the exact v0.1 `payload_schema_ref`/`payload_schema_map` suite metadata and
  validates Core lifecycle messages inside extension scenarios and extension messages
  inside Core scenarios. Missing or conflicting owner routes fail closed. PE reason codes
  and CAPNEG privacy modes now use the ordinary `vendor:`/`org:` rule, while broader Core
  policy-category and enforcement-sanction namespaces remain unchanged.
- M64 adds live two-role loopback evidence for the exact HTTP and MCP binding targets.
  Current trace v4 proves real HTTP/SSE/WebSocket/WSS or MCP stdio execution, first-seen
  MCP continuation causality, and repository-observed TLS certificate rejection without
  treating reference evidence as an independent external submission.
- M65 completes the registered-message conformance surface: all 132 registered messages
  have one owner, one canonical payload mapping, owning suite coverage, and an actual
  positive suite-referenced fixture. Five orphan paths were reused and strengthened, six
  positive fixtures were newly added, and no new negative fixture, message ID, protocol
  mark, or external target was introduced. The correction removes the separate M65
  semantic engine and non-normative prior-local-state rejections; suite, batch, profile,
  and generalized evidence paths now share the canonical 0.1 semantic boundary. Evidence
  TCK 1.8 remains frozen historical/eligible, TCK 1.9 is frozen historical/ineligible,
  and TCK 1.10 is current with report 2.2, trace v4, and Tier-1 consumer counts 26/16/31.
  Product-IUT v1, IUT TCK 1.1, its targets, case sets, and marks remain unchanged.

### Current evidence limits

- The registry contains 16 product profiles; all have internal profile suites. Base and
  Authenticated Base have profile-IUT v1 targets, while the three Tier-1 profiles have
  generalized report-2.1 targets. No other profile has an external target.
- Base 0.2 has internal conformance evidence only. It does not authenticate senders, cannot
  use projection v1 as an exact-head overlay, and has no external-IUT target in M60.
- CAPNEG v0.2 and projection v2 have internal evidence only. They do not create an
  aggregate profile badge, award component marks, or enable external composition claims;
  M62 does not register either as an external target.
- Projection v1 has one externally testable capability target and one reachable evidence
  mark, but no real independent external capability submission is present.
- The authenticated 37-case target can emit its ordinary external mark for a complete
  eligible implementation. Its mandatory unavailable-crypto probe remains exact and
  case-local; real degradation or skipped normal verification remains ineligible.
- The interop matrix has no real independent external submission and pairwise publication
  is fail-closed.
- HTTP/WS/SSE and MCP have live repository-owned loopback reference evidence, but no real
  independent external binding submission or two-vendor pairwise execution is present.
- The security package contains internal self-review and partial coverage, not a completed
  independent external review.
- Governance remains maintainer/steward based. Snapshot naming, generated report tracking,
  cross-platform bootstrap, and final RC repackaging remain M69 work.

See `docs/process/AICP_Repo_Truth_Baseline.md` for the mechanically checked evidence table.

## 0.1.0-rc.1 — Release candidate

AICP is moving from a pure development posture to a conservative first release candidate posture. This is **not** a GA release. The goal of `0.1.0-rc.1` is to package the repo's already-shipped executable Core/profile/conformance work with clearer release metadata, lightweight maintainer guidance, and a small TypeScript SDK regression guardrail set.

### Highlights
- TypeScript SDK regression coverage now includes transcript chain validation cases for missing, empty, mismatched, and valid `prev_msg_hash` linkage.
- Release metadata is now aligned around a single pre-GA repo version: `0.1.0-rc.1`.
- Lightweight release/governance/productization docs now exist to make tagging and GitHub release preparation easier for maintainers.

### Included in this release candidate
- Core narrative, schemas, fixtures, registries, and conformance suites already shipped in the repository.
- Profile, binding, and extension conformance runners already wired into CI and the repo's one-command validation workflow.
- Minimal TypeScript SDK and Python reference/helper artifacts intended to support implementers rather than redefine normative protocol truth.

### Release-candidate expectations
- Treat this as a stabilization checkpoint for packaging, validation, and release discipline.
- Compatibility claims should continue to be grounded in repo-backed conformance/profile evidence, not generic marketing statements.
- Maintainers should prefer narrow fixes, doc clarifications, and executable proof over new protocol surface during the RC phase.

### Verification baseline
Run the existing repo-backed checks before tagging or publishing a GitHub release:
- `make validate`
- `make test`
- `make conformance`
- `make conformance-ext`
- `make conformance-bindings`
- `make conformance-profiles`
- `make template-smoke`
- `cd sdk/typescript && npm ci && npm test`

### Known limits
- Package publication strategy is intentionally unchanged; the TypeScript SDK remains private in-repo helper tooling.
- Adapter/gateway guidance remains template- and doc-oriented; this release candidate does not introduce a production adapter runtime.
- This RC does not broaden persona/profile positioning or claim GA stability across the full optional ecosystem surface.
