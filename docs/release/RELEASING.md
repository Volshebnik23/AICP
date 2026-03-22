# Releasing AICP (maintainer playbook)

This is a short maintainer guide for cutting a repo tag and preparing the matching GitHub release.

## 1. Confirm release metadata
- Update `VERSION`.
- Update `RELEASE_NOTES.md` with the target release-candidate summary.
- Update `CHANGELOG.md` with a concise entry for the release.
- Update `sdk/typescript/package.json` and `sdk/typescript/package-lock.json` to match `VERSION` while keeping the SDK private.
- Run `make release-check` to fail fast on version drift before broader verification.

## 2. Run the repo-backed checks
From repo root, run the existing validation and conformance commands already used by CI:
- `make validate`
- `make test`
- `make conformance`
- `make conformance-ext`
- `make conformance-bindings`
- `make conformance-profiles`
- `make template-smoke`
- `make release-check`

Also run the TypeScript SDK test command:
- `cd sdk/typescript && npm ci && npm test`

## 3. Review release readiness
Before tagging, verify that:
- release metadata files are consistent and `make release-check` is green,
- CI is green,
- release notes describe only shipped repo truth,
- compatibility claims remain grounded in conformance/profile evidence,
- no release text implies GA unless the repo has explicitly made that decision.

## 4. Cut the tag
Create an annotated tag that matches `VERSION`.

Example:
```bash
git tag -a v0.1.0-rc.1 -m "AICP 0.1.0-rc.1"
```

## 5. Publish the GitHub release
Use the `RELEASE_NOTES.md` section for the tagged version as the basis for the GitHub release description. Keep the description short, factual, and aligned with the checked-in artifacts.

## 6. After release
- Push the tag.
- Confirm the GitHub release points to the exact tag.
- Continue RC work with small, reviewable follow-up PRs.
