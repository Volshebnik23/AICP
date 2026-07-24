# Productization Definition of Done

Use this checklist before calling a release candidate "ready enough to tag."

## Release metadata
- [ ] `VERSION` matches the intended tag.
- [ ] `RELEASE_NOTES.md` contains a truthful section for the target release.
- [ ] `CHANGELOG.md` contains a concise entry for the target release.
- [ ] `sdk/typescript/package.json` and `sdk/typescript/package-lock.json` match `VERSION` and keep `private: true`.
- [ ] `make release-check` passes.

## Executable verification
- [ ] `make validate` passes.
- [ ] `make test` passes.
- [ ] `make conformance` passes.
- [ ] `make conformance-ext` passes.
- [ ] `make conformance-bindings` passes.
- [ ] `make conformance-profiles` passes.
- [ ] `make template-smoke` passes.
- [ ] `cd sdk/typescript && npm ci && npm test` passes.

## Truthfulness and scope control
- [ ] Release text describes only repo-backed artifacts.
- [ ] `docs/process/AICP_Repo_Truth_Baseline.md` and its machine-readable companion match the
      target checkout.
- [ ] Compatibility claims are grounded in conformance/profile evidence.
- [ ] Internal profile runs are not described as independent external interoperability.
- [ ] Static binding cases are not described as live transport interoperability.
- [ ] Examples, templates, reference adapters, and dry runs are not counted as real external submissions.
- [ ] Any shipped helper/template claims are consistent with current tests/docs.
- [ ] No release text implies package publication or production adapter runtime support that the repo does not ship.

## Maintainer readiness
- [ ] `docs/release/RELEASING.md` still matches the current repo workflow.
- [ ] `GOVERNANCE.md` still reflects the lightweight stewardship model actually used by the repo.
- [ ] README links are sufficient for implementers to find release-readiness guidance.
