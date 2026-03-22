# Release Notes

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
