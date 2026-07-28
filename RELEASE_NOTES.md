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
- Roadmap and backlog roles are separated: M58–M60 are shipped, while M61–M70 retain
  the remaining evidence, interop, security, governance, and release work.
- Experimental `AICP-IUT-TCK-1.1.0` introduces explicit case-local execution accounting and
  structured consumer observations; the historical 1.0.0 registry record remains frozen.
- Experimental post-UAT Core v0.2 adds exact contract artifact and active-head agreement
  under `AICP-BASE@0.2`, with separate schemas, suite, fixtures, helpers, and quickstarts.
  Core/Base 0.1 and the UAT target remain unchanged.

### Current evidence limits

- The registry contains 16 product profiles; all have internal profile suites, but only Base
  and Authenticated Base have full external-IUT targets.
- Base 0.2 has internal conformance evidence only. It does not authenticate senders, cannot
  use projection v1 as an exact-head overlay, and has no external-IUT target in M60.
- The authenticated 37-case target can emit its ordinary external mark for a complete
  eligible implementation. Its mandatory unavailable-crypto probe remains exact and
  case-local; real degradation or skipped normal verification remains ineligible.
- The interop matrix has no real independent external submission and pairwise publication
  is fail-closed.
- HTTP/WS/SSE and MCP evidence is based on static case fixtures, not live independent
  endpoint interoperability.
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
